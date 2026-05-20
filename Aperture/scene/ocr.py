"""EasyOCR text extraction wrapper.

EasyOCR is heavy (~100 MB of weights, ~500 MB resident RAM) and is
excluded from Streamlit Cloud builds via ``requirements.txt`` to stay
inside the free-tier memory budget. When the package is missing
``TextExtractor`` no-ops and ``extract()`` returns a sentinel dict, so
the rest of the scene / verdict pipeline keeps working.

For local development install it via ``requirements-dev.txt``.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
from PIL import Image

try:
    import easyocr  # type: ignore
    OCR_AVAILABLE = True
except ImportError:
    easyocr = None  # type: ignore[assignment]
    OCR_AVAILABLE = False


_UNAVAILABLE_RESULT = {
    "text_found": False,
    "extracted_text": "",
    "regions": [],
    "note": "OCR temporarily unavailable in deployed version",
}


class TextExtractor:
    """English EasyOCR wrapper.

    EasyOCR downloads its detection and recognition weights on first call;
    subsequent runs hit ``~/.EasyOCR/``. When easyocr isn't installed
    (deployed builds), the constructor no-ops and ``extract()`` returns
    the sentinel result.
    """

    def __init__(
        self,
        languages: Iterable[str] = ("en",),
        gpu: Optional[bool] = None,
        min_confidence: float = 0.5,
    ) -> None:
        self.min_confidence = float(min_confidence)
        if not OCR_AVAILABLE:
            self.reader = None
            return
        if gpu is None:
            try:
                import torch  # type: ignore
                gpu = bool(torch.cuda.is_available())
            except ImportError:
                gpu = False
        self.reader = easyocr.Reader(list(languages), gpu=bool(gpu), verbose=False)

    def extract(self, pil_image: Image.Image) -> dict:
        if self.reader is None:
            return dict(_UNAVAILABLE_RESULT)
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
