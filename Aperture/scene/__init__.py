"""Scene understanding: object detection, scene classification, OCR.

Public entry point is :func:`analyze_scene`. The individual loaders are
``@lru_cache``'d so each backbone is loaded exactly once per process; if
you're using Streamlit, wrap these with ``@st.cache_resource`` instead.
"""
from __future__ import annotations

from functools import lru_cache

from PIL import Image


@lru_cache(maxsize=1)
def get_object_detector():
    from Aperture.scene.detection import ObjectDetector
    return ObjectDetector()


@lru_cache(maxsize=1)
def get_clip_classifier():
    from Aperture.scene.clip_scene import CLIPSceneClassifier
    return CLIPSceneClassifier()


@lru_cache(maxsize=1)
def get_text_extractor():
    from Aperture.scene.ocr import TextExtractor
    return TextExtractor()


def analyze_scene(pil_image: Image.Image) -> dict:
    """Run all three scene analyzers and bundle their outputs.

    Returns ``{"objects": ..., "scene": ..., "ocr": ...}``. The first call
    triggers backbone downloads; subsequent calls reuse cached instances.
    """
    return {
        "objects": get_object_detector().detect(pil_image),
        "scene": get_clip_classifier().classify(pil_image),
        "ocr": get_text_extractor().extract(pil_image),
    }


__all__ = [
    "analyze_scene",
    "get_object_detector",
    "get_clip_classifier",
    "get_text_extractor",
]
