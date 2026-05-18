"""Train an AI vs real image detector on CIFAKE.

Usage:
    python -m Aperture.ai_detector.train \\
        --data-root data/cifake --epochs 10 --batch-size 32

Saves the best (by val AUC) checkpoint to models/ai_detector_best.pt and
training curves to eval_results/training_curves.png.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader
from tqdm import tqdm

from Aperture.ai_detector.dataset import (
    CIFakeDataset,
    build_eval_transform,
    build_train_transform,
)
from Aperture.ai_detector.model import get_model


@dataclass
class TrainConfig:
    data_root: str = "data/cifake"
    model_name: str = "efficientnet_b0"
    epochs: int = 10
    batch_size: int = 32
    lr: float = 1e-4
    weight_decay: float = 0.01
    num_workers: int = 4
    image_size: int = 224
    output_dir: str = "models"
    plots_dir: str = "eval_results"
    seed: int = 42
    checkpoint_name: str = "ai_detector_best.pt"


def _pick_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _try_wandb(config: TrainConfig):
    try:
        import wandb  # type: ignore
    except ImportError:
        return None
    try:
        wandb.init(project="aperture-ai-detector", config=asdict(config))
        return wandb
    except Exception as exc:  # offline / no creds
        print(f"[wandb] disabled ({exc})")
        return None


def evaluate(model, loader, device, criterion) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    n_seen = 0
    labels_buf, probs_buf, preds_buf = [], [], []
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            logits = model(images)
            loss = criterion(logits, labels)
            total_loss += loss.item() * labels.size(0)
            n_seen += labels.size(0)
            probs = torch.softmax(logits, dim=1)[:, 1]  # P(FAKE)
            preds = logits.argmax(dim=1)
            labels_buf.append(labels.detach().cpu().numpy())
            probs_buf.append(probs.detach().cpu().numpy())
            preds_buf.append(preds.detach().cpu().numpy())
    y_true = np.concatenate(labels_buf)
    y_prob = np.concatenate(probs_buf)
    y_pred = np.concatenate(preds_buf)
    return {
        "loss": total_loss / n_seen,
        "acc": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
        "auc": float(roc_auc_score(y_true, y_prob)),
    }


def plot_curves(history: dict[str, list[float]], out_path: Path) -> None:
    epochs = range(1, len(history["train_loss"]) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(epochs, history["train_loss"], label="train")
    axes[0].plot(epochs, history["val_loss"], label="val")
    axes[0].set_title("Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].legend()

    axes[1].plot(epochs, history["val_acc"], label="acc")
    axes[1].plot(epochs, history["val_f1"], label="f1")
    axes[1].plot(epochs, history["val_auc"], label="auc")
    axes[1].set_title("Validation metrics")
    axes[1].set_xlabel("Epoch")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def train(config: TrainConfig) -> tuple[Path, dict[str, list[float]]]:
    _set_seed(config.seed)
    device = _pick_device()
    print(f"[device] {device}")

    output_dir = Path(config.output_dir)
    plots_dir = Path(config.plots_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    train_ds = CIFakeDataset(
        Path(config.data_root) / "train",
        transform=build_train_transform(config.image_size),
    )
    val_ds = CIFakeDataset(
        Path(config.data_root) / "test",
        transform=build_eval_transform(config.image_size),
    )
    print(f"[data] train={len(train_ds)}  val={len(val_ds)}")
    print(f"[data] train class counts: {train_ds.class_counts()}")

    pin = device.type == "cuda"
    train_loader = DataLoader(
        train_ds, batch_size=config.batch_size, shuffle=True,
        num_workers=config.num_workers, pin_memory=pin, drop_last=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=config.batch_size, shuffle=False,
        num_workers=config.num_workers, pin_memory=pin,
    )

    model = get_model(config.model_name).to(device)
    optimizer = AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=config.epochs)
    criterion = nn.CrossEntropyLoss()

    use_amp = device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    wb = _try_wandb(config)
    history: dict[str, list[float]] = {
        "train_loss": [], "val_loss": [], "val_acc": [], "val_f1": [], "val_auc": [],
    }
    best_auc = -1.0
    best_path = output_dir / config.checkpoint_name

    for epoch in range(1, config.epochs + 1):
        model.train()
        running, n_seen = 0.0, 0
        pbar = tqdm(train_loader, desc=f"epoch {epoch}/{config.epochs}")
        for images, labels in pbar:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=use_amp):
                logits = model(images)
                loss = criterion(logits, labels)
            if use_amp:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
            running += loss.item() * labels.size(0)
            n_seen += labels.size(0)
            pbar.set_postfix(loss=f"{running / n_seen:.4f}")
            if wb is not None:
                wb.log({"train_batch_loss": loss.item()})

        train_loss = running / n_seen
        scheduler.step()
        metrics = evaluate(model, val_loader, device, criterion)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(metrics["loss"])
        history["val_acc"].append(metrics["acc"])
        history["val_f1"].append(metrics["f1"])
        history["val_auc"].append(metrics["auc"])

        print(
            f"epoch {epoch}: train_loss={train_loss:.4f} "
            f"val_loss={metrics['loss']:.4f} val_acc={metrics['acc']:.4f} "
            f"val_f1={metrics['f1']:.4f} val_auc={metrics['auc']:.4f}"
        )
        if wb is not None:
            wb.log({"epoch": epoch, "train_loss": train_loss,
                    **{f"val_{k}": v for k, v in metrics.items()}})

        if metrics["auc"] > best_auc:
            best_auc = metrics["auc"]
            torch.save({
                "model_name": config.model_name,
                "state_dict": model.state_dict(),
                "config": asdict(config),
                "metrics": metrics,
                "epoch": epoch,
            }, best_path)
            print(f"[checkpoint] saved best (auc={best_auc:.4f}) -> {best_path}")

    plot_curves(history, plots_dir / "training_curves.png")
    with (plots_dir / "training_history.json").open("w") as f:
        json.dump(history, f, indent=2)
    if wb is not None:
        wb.finish()
    return best_path, history


def parse_args() -> TrainConfig:
    d = TrainConfig()
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", default=d.data_root)
    p.add_argument("--model-name", default=d.model_name)
    p.add_argument("--epochs", type=int, default=d.epochs)
    p.add_argument("--batch-size", type=int, default=d.batch_size)
    p.add_argument("--lr", type=float, default=d.lr)
    p.add_argument("--weight-decay", type=float, default=d.weight_decay)
    p.add_argument("--num-workers", type=int, default=d.num_workers)
    p.add_argument("--image-size", type=int, default=d.image_size)
    p.add_argument("--output-dir", default=d.output_dir)
    p.add_argument("--plots-dir", default=d.plots_dir)
    p.add_argument("--seed", type=int, default=d.seed)
    p.add_argument("--checkpoint-name", default=d.checkpoint_name)
    return TrainConfig(**vars(p.parse_args()))


if __name__ == "__main__":
    train(parse_args())
