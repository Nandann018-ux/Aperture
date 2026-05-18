"""CIFAKE dataset + transforms for the AI vs real detector."""
from __future__ import annotations

import io
import os
import random
from pathlib import Path
from typing import Callable, Optional

from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

CLASS_TO_IDX = {"REAL": 0, "FAKE": 1}
IDX_TO_CLASS = {v: k for k, v in CLASS_TO_IDX.items()}

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


class RandomJPEGCompression:
    """Re-encode a PIL image as JPEG at a random quality in [qmin, qmax].

    Critical for real-world generalization: many AI-generated images leak
    through social platforms that re-encode them, so the model must be
    robust to compression artifacts."""

    def __init__(self, qmin: int = 60, qmax: int = 95):
        if not 1 <= qmin <= qmax <= 100:
            raise ValueError("require 1 <= qmin <= qmax <= 100")
        self.qmin = qmin
        self.qmax = qmax

    def __call__(self, img: Image.Image) -> Image.Image:
        quality = random.randint(self.qmin, self.qmax)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf).convert("RGB")

    def __repr__(self) -> str:
        return f"RandomJPEGCompression(qmin={self.qmin}, qmax={self.qmax})"


def build_train_transform(image_size: int = 224) -> Callable:
    return transforms.Compose([
        transforms.RandomResizedCrop(image_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.RandomApply([RandomJPEGCompression(60, 95)], p=0.5),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def build_eval_transform(image_size: int = 224) -> Callable:
    return transforms.Compose([
        transforms.Resize(image_size + 32),
        transforms.CenterCrop(image_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


class CIFakeDataset(Dataset):
    """CIFAKE binary classifier dataset.

    Expects the standard CIFAKE layout:

        root/REAL/*.jpg
        root/FAKE/*.jpg

    Where `root` is the train/ or test/ folder of the CIFAKE release.
    Labels: 0 = REAL, 1 = FAKE.
    """

    def __init__(
        self,
        root: str | os.PathLike,
        transform: Optional[Callable] = None,
    ) -> None:
        self.root = Path(root)
        self.transform = transform
        self.samples: list[tuple[Path, int]] = []
        for cls_name, label in CLASS_TO_IDX.items():
            cls_dir = self.root / cls_name
            if not cls_dir.is_dir():
                raise FileNotFoundError(
                    f"Expected directory {cls_dir} — is the CIFAKE dataset extracted?"
                )
            for path in sorted(cls_dir.iterdir()):
                if path.suffix.lower() in _IMAGE_EXTS:
                    self.samples.append((path, label))
        if not self.samples:
            raise RuntimeError(f"No images found under {self.root}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform is not None:
            img = self.transform(img)
        return img, label

    def class_counts(self) -> dict[str, int]:
        counts = {name: 0 for name in CLASS_TO_IDX}
        for _, label in self.samples:
            counts[IDX_TO_CLASS[label]] += 1
        return counts
