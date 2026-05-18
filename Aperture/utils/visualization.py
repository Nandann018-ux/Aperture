"""Heatmap overlay helpers."""
from __future__ import annotations

import cv2
import numpy as np
from matplotlib import colormaps
from PIL import Image


def overlay_heatmap(
    pil_image: Image.Image,
    heatmap: np.ndarray,
    alpha: float = 0.5,
    colormap: str = "jet",
) -> Image.Image:
    """Blend a [0, 1] heatmap onto a PIL image using the JET colormap.

    The heatmap is resized to the image's spatial dims if needed.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    img_np = np.asarray(pil_image, dtype=np.float32) / 255.0
    h, w = img_np.shape[:2]

    heat = heatmap.astype(np.float32)
    if heat.shape != (h, w):
        heat = cv2.resize(heat, (w, h), interpolation=cv2.INTER_CUBIC)
    lo, hi = float(heat.min()), float(heat.max())
    if hi - lo > 1e-12:
        heat = (heat - lo) / (hi - lo)
    else:
        heat = np.zeros_like(heat)

    cmap = colormaps.get_cmap(colormap)
    colored = cmap(heat)[:, :, :3].astype(np.float32)  # drop alpha channel

    blended = (1.0 - alpha) * img_np + alpha * colored
    blended = np.clip(blended * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(blended)
