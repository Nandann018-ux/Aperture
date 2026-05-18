"""Noise residual analysis for spliced-region detection.

Camera sensors leave a characteristic noise fingerprint. Spliced regions
imported from a different camera (or a generator) usually carry different
noise statistics, so the per-block noise variance is more inhomogeneous
across a tampered image than across an authentic one.

We extract the residual via high-pass filtering (image minus Gaussian
blur) — robust, dependency-free, and fast.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def extract_noise_residual(pil_image: Image.Image) -> np.ndarray:
    """Return a grayscale 2D noise residual (image minus Gaussian blur)."""
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    img = np.asarray(pil_image, dtype=np.float32)
    blurred = cv2.GaussianBlur(img, (5, 5), 1.0)
    residual = img - blurred
    # Luminance projection
    gray = residual @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    return gray.astype(np.float32)


def _block_stats(arr: np.ndarray, n_blocks: int) -> tuple[np.ndarray, np.ndarray]:
    h, w = arr.shape
    bh, bw = h // n_blocks, w // n_blocks
    if bh == 0 or bw == 0:
        return (np.array([[arr.mean()]], dtype=np.float32),
                np.array([[arr.std()]], dtype=np.float32))
    means = np.empty((n_blocks, n_blocks), dtype=np.float32)
    stds = np.empty((n_blocks, n_blocks), dtype=np.float32)
    for i in range(n_blocks):
        for j in range(n_blocks):
            block = arr[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]
            means[i, j] = float(block.mean())
            stds[i, j] = float(block.std())
    return means, stds


def noise_inconsistency_score(noise_residual: np.ndarray, n_blocks: int = 8) -> float:
    """Coefficient of variation of block-wise std deviations.

    Low CV = spatially-homogeneous noise (authentic capture).
    High CV = some blocks have anomalous noise stats (likely tampered).
    """
    if noise_residual.ndim != 2:
        raise ValueError("noise_residual must be 2D")
    _, stds = _block_stats(noise_residual, n_blocks)
    mean_std = float(stds.mean())
    if mean_std < 1e-9:
        return 0.0
    return float(stds.std() / mean_std)


def noise_heatmap(noise_residual: np.ndarray, n_blocks: int = 8) -> np.ndarray:
    """Block-wise std map upsampled to image size, normalized to [0, 1]."""
    if noise_residual.ndim != 2:
        raise ValueError("noise_residual must be 2D")
    h, w = noise_residual.shape
    _, stds = _block_stats(noise_residual, n_blocks)
    heat = cv2.resize(stds, (w, h), interpolation=cv2.INTER_NEAREST)
    lo, hi = float(heat.min()), float(heat.max())
    if hi - lo < 1e-12:
        return np.zeros_like(heat, dtype=np.float32)
    return ((heat - lo) / (hi - lo)).astype(np.float32)
