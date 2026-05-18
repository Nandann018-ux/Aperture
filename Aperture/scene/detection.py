"""YOLOv8 object detection wrapper."""

from __future__ import annotations
from collections import Counter
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont


class ObjectDetector:
    """Wraps ultralytics YOLOv8 for one-shot detection on a PIL image.

    Heavy imports (ultralytics, torch) are deferred to ``__init__`` so the
    module itself stays cheap to import.
    """

    def __init__(
        self,
        weights: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
    ) -> None:
        from pathlib import Path

        from ultralytics import YOLO  # type: ignore
        # Prefer a cached copy under models/ if present; otherwise let
        # ultralytics download into CWD (its default), which we then look
        # for on the next run.
        candidates = [Path("models") / weights, Path(weights)]
        path = next((str(p) for p in candidates if p.exists()), weights)
        self.model = YOLO(path)
        self.conf_threshold = float(conf_threshold)

    def detect(self, pil_image: Image.Image) -> dict:
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        results = self.model.predict(
            np.asarray(pil_image),
            conf=self.conf_threshold,
            verbose=False,
        )
        r = results[0]
        names = r.names

        objects: list[dict] = []
        if r.boxes is not None and len(r.boxes) > 0:
            for box in r.boxes:  # type: ignore[attr-defined]
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                xyxy = [float(v) for v in box.xyxy[0].tolist()]
                objects.append({
                    "label": names[cls_id],
                    "confidence": conf,
                    "bbox": xyxy,
                })

        return {
            "objects": objects,
            "annotated_image": self._annotate(pil_image, objects),
            "object_counts": Counter(o["label"] for o in objects),
        }

    @staticmethod
    def _annotate(pil_image: Image.Image, objects: list[dict]) -> Image.Image:
        img = pil_image.convert("RGB").copy()
        draw = ImageDraw.Draw(img)
        font: Optional[ImageFont.ImageFont] = None
        try:
            font = ImageFont.load_default()  # type: ignore[assignment]
        except OSError:
            font = None

        for o in objects:
            x1, y1, x2, y2 = o["bbox"]
            label = f"{o['label']} {o['confidence']:.2f}"
            draw.rectangle([x1, y1, x2, y2], outline=(255, 60, 60), width=3)
            try:
                bbox = draw.textbbox((0, 0), label, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                tw, th = 80, 14
            top = max(0, y1 - th - 4)
            draw.rectangle([x1, top, x1 + tw + 6, y1], fill=(255, 60, 60))
            draw.text((x1 + 3, top + 1), label, fill=(255, 255, 255), font=font)
        return img
