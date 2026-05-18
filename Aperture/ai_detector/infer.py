"""Inference wrapper for the CIFAKE-trained AI vs real detector.

Singleton-per-path: calling AIDetector(path) twice with the same path returns
the same instance, so the model loads once and is reused across requests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
from PIL import Image

from Aperture.ai_detector.dataset import build_eval_transform
from Aperture.ai_detector.model import get_model

_LABELS = {0: "real", 1: "fake"}


def _pick_device(device: Optional[str | torch.device]) -> torch.device:
    if device is not None:
        return torch.device(device)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class AIDetector:
    """Inference wrapper around a trained detector checkpoint.

    Usage:
        det = AIDetector("models/ai_detector_best.pt")
        det.predict(pil_image)  # -> {"label": "fake", "confidence": 0.97, ...}
    """

    _instances: dict[str, "AIDetector"] = {}

    def __new__(cls, model_path, device=None):
        key = str(Path(model_path).resolve())
        if key in cls._instances:
            return cls._instances[key]
        inst = super().__new__(cls)
        cls._instances[key] = inst
        return inst

    def __init__(self, model_path, device: Optional[str | torch.device] = None):
        if getattr(self, "_initialized", False):
            return
        self.model_path = str(Path(model_path).resolve())
        self.device = _pick_device(device)
        ckpt = torch.load(self.model_path, map_location=self.device)
        model_name = ckpt.get("model_name", "efficientnet_b0")
        model = get_model(model_name, pretrained=False)
        model.load_state_dict(ckpt["state_dict"])
        model.eval().to(self.device)
        self.model = model
        self.model_name = model_name
        self.transform = build_eval_transform()
        self._initialized = True

    @torch.no_grad()
    def predict(self, pil_image: Image.Image) -> dict:
        if not isinstance(pil_image, Image.Image):
            raise TypeError("predict() expects a PIL.Image, got " + type(pil_image).__name__)
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        x = self.transform(pil_image).unsqueeze(0).to(self.device)
        logits = self.model(x).squeeze(0)
        probs = torch.softmax(logits, dim=0)
        pred = int(probs.argmax().item())
        return {
            "label": _LABELS[pred],
            "confidence": float(probs[pred].item()),
            "raw_logits": logits.detach().cpu().tolist(),
        }

    @classmethod
    def clear_cache(cls) -> None:
        cls._instances.clear()
