"""Zero-shot scene classification via CLIP ViT-B/32."""
from __future__ import annotations

from typing import Optional

import torch
from PIL import Image

SCENE_LABELS: list[str] = [
    "an indoor scene",
    "an outdoor scene",
    "a portrait of a person",
    "a landscape photograph",
    "an urban street scene",
    "a natural environment",
    "a document or text",
    "a screenshot",
    "an artwork or illustration",
    "a product photograph",
    "a food photograph",
    "an animal photograph",
]


def _pick_device(device: Optional[str | torch.device]) -> torch.device:
    if device is not None:
        return torch.device(device)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class CLIPSceneClassifier:
    """Zero-shot scene classifier. Text features are precomputed at init."""

    def __init__(
        self,
        model_id: str = "openai/clip-vit-base-patch32",
        device: Optional[str | torch.device] = None,
        labels: Optional[list[str]] = None,
    ) -> None:
        from transformers import CLIPModel, CLIPProcessor  # type: ignore
        self.device = _pick_device(device)
        self.labels: list[str] = list(labels) if labels else SCENE_LABELS
        self.processor = CLIPProcessor.from_pretrained(model_id)
        self.model = CLIPModel.from_pretrained(model_id).to(self.device).eval()  # type: ignore[arg-type]
        with torch.no_grad():
            text_inputs = self.processor(
                text=self.labels, return_tensors="pt", padding=True
            ).to(self.device)
            tf = self._text_features(text_inputs)
            self.text_features = tf / tf.norm(dim=-1, keepdim=True)

    def _text_features(self, text_inputs) -> torch.Tensor:
        # transformers <5 returns the projected Tensor directly.
        # transformers >=5 wraps it in BaseModelOutputWithPooling, where
        # pooler_output is the already-projected feature tensor.
        out = self.model.get_text_features(**text_inputs)
        return out if isinstance(out, torch.Tensor) else out.pooler_output

    def _image_features(self, img_inputs) -> torch.Tensor:
        out = self.model.get_image_features(**img_inputs)
        return out if isinstance(out, torch.Tensor) else out.pooler_output

    @torch.no_grad()
    def classify(self, pil_image: Image.Image) -> dict:
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        img_inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)
        img_features = self._image_features(img_inputs)
        img_features = img_features / img_features.norm(dim=-1, keepdim=True)
        logits = (img_features @ self.text_features.T) * self.model.logit_scale.exp()
        probs = logits.softmax(dim=-1).squeeze(0).detach().cpu().tolist()

        scored = sorted(zip(self.labels, probs), key=lambda kv: -kv[1])
        return {
            "primary_scene": scored[0][0],
            "scores": {label: float(p) for label, p in zip(self.labels, probs)},
            "top_3": [{"label": l, "score": float(p)} for l, p in scored[:3]],
        }
