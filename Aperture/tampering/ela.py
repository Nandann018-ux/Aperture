"""Error Level Analysis (ELA).

The intuition: JPEG re-compression introduces a roughly uniform error
across an authentic image, because the whole image was encoded at the
same quality at capture time. Spliced regions usually have a different
compression history, so when the suspect image is re-encoded at a fixed
quality, those regions exhibit anomalously high error.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image


def compute_ela(pil_image: Image.Image, quality: int = 90) -> np.ndarray:
    """Per-pixel ELA heatmap, normalized to [0, 1].

    Returns a 2D (H, W) float32 array.
    """
    if not 1 <= quality <= 100:
        raise ValueError("quality must be in [1, 100]")
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")

    orig = np.asarray(pil_image, dtype=np.int16)
    re = np.asarray(recompressed, dtype=np.int16)
    diff = np.abs(orig - re).astype(np.float32).max(axis=2)  # collapse channels

    # Robust normalization: clip at the 99th percentile so a few hot pixels
    # don't squash the rest of the heatmap to zero.
    p99 = float(np.percentile(diff, 99))
    if p99 < 1e-9:
        return np.zeros_like(diff, dtype=np.float32)
    return np.clip(diff / p99, 0.0, 1.0).astype(np.float32)


def ela_score(ela_heatmap: np.ndarray, window: int = 32) -> float:
    """Tampering score: max-to-mean ratio of per-patch std deviations.

    Authentic images have spatially-uniform compression error, so all
    patches have similar local std. A spliced region produces one (or a
    few) patches with anomalously high std, so max/mean spikes.

    Returns a non-negative float (>= 1 in non-degenerate cases).
    """
    if ela_heatmap.ndim != 2:
        raise ValueError("ela_heatmap must be a 2D array")
    h, w = ela_heatmap.shape
    if h < window or w < window:
        return float(np.std(ela_heatmap))

    stride = max(1, window // 2)
    samples: list[float] = []
    for y in range(0, h - window + 1, stride):
        for x in range(0, w - window + 1, stride):
            samples.append(float(np.std(ela_heatmap[y:y + window, x:x + window])))
    stds = np.asarray(samples, dtype=np.float32)
    mean_std = float(stds.mean())
    if mean_std < 1e-9:
        return 0.0
    return float(stds.max() / mean_std)
