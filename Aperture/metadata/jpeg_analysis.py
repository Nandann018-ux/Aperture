"""Lightweight JPEG quality + structural inspection.

Quality estimate is approximate; it matches libjpeg's standard Q-table
scaling formula closely enough to spot heavy re-compression.
"""
from __future__ import annotations

import io

from PIL import Image

# Annex K luminance quantization table at quality 50 — used to back out the
# scaling factor applied by libjpeg.
_STANDARD_LUMA_Q50 = (
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
)


def _estimate_quality_from_qtable(qtable: tuple[int, ...]) -> float | None:
    """Reverse-engineer libjpeg's quality knob from a quantization table."""
    if len(qtable) < 64:
        return None
    # Use the high-frequency DC term ratio for a more stable estimate.
    sums = [q / s for q, s in zip(qtable[:64], _STANDARD_LUMA_Q50) if s]
    if not sums:
        return None
    scale = sum(sums) / len(sums)
    # libjpeg: scale = 50/Q for Q < 50, (200 - 2*Q)/100 for Q >= 50
    if scale >= 1:
        quality = 50.0 / scale
    else:
        quality = 100 - 50.0 * scale
    return float(max(1.0, min(100.0, quality)))


def analyze_jpeg(pil_image: Image.Image, file_bytes: bytes | None = None) -> dict:
    """Inspect quantization tables, format, and an estimated quality knob.

    ``file_bytes`` is optional; if provided we use it directly instead of
    re-encoding the (potentially upstream-decoded) PIL image.
    """
    info: dict = {
        "format": pil_image.format,
        "mode": pil_image.mode,
        "size": list(pil_image.size),
        "is_jpeg": False,
        "estimated_quality": None,
        "quantization_tables": 0,
        "progressive": None,
    }
    img_for_qt = pil_image
    if file_bytes is not None:
        try:
            img_for_qt = Image.open(io.BytesIO(file_bytes))
            img_for_qt.load()
            info["format"] = img_for_qt.format
        except Exception:
            pass

    info["is_jpeg"] = (img_for_qt.format or "").upper() in {"JPEG", "JPG", "MPO"}
    if info["is_jpeg"]:
        qt = getattr(img_for_qt, "quantization", None) or {}
        info["quantization_tables"] = len(qt)
        if 0 in qt:
            info["estimated_quality"] = _estimate_quality_from_qtable(tuple(qt[0]))
        info["progressive"] = bool(img_for_qt.info.get("progression"))
    return info
