"""EasyOCR text extraction wrapper."""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
from PIL import Image


class TextExtractor:
    """English EasyOCR wrapper.

    EasyOCR downloads its detection and recognition weights on first call;
    subsequent runs hit ``~/.EasyOCR/``.
    """

    def __init__(
        self,
        languages: Iterable[str] = ("en",),
        gpu: Optional[bool] = None,
        min_confidence: float = 0.5,
    ) -> None:
        import easyocr  # type: ignore
        if gpu is None:
            try:
                import torch  # type: ignore
                gpu = bool(torch.cuda.is_available())
            except ImportError:
                gpu = False
        self.reader = easyocr.Reader(list(languages), gpu=bool(gpu), verbose=False)
        self.min_confidence = float(min_confidence)

    def extract(self, pil_image: Image.Image) -> dict:
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        results = self.reader.readtext(np.asarray(pil_image))

        regions: list[dict] = []
        texts: list[str] = []
        for bbox, text, conf in results:
            if conf < self.min_confidence:
                continue
            regions.append({
                "bbox": [[float(x), float(y)] for x, y in bbox],
                "text": str(text),
                "confidence": float(conf),
            })
            texts.append(str(text))

        return {
            "text_found": bool(texts),
            "extracted_text": " ".join(texts),
            "regions": regions,
        }
