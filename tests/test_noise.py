"""Unit tests for noise residual analysis."""
from __future__ import annotations

import numpy as np
from PIL import Image

from Aperture.tampering.noise import (
    extract_noise_residual,
    noise_heatmap,
    noise_inconsistency_score,
)


RNG = np.random.default_rng(0)


def _authentic(size: int = 256) -> Image.Image:
    y = np.linspace(0, 1, size, dtype=np.float32)[:, None]
    arr = np.broadcast_to((200 - 80 * y)[..., None], (size, size, 3)).copy()
    arr = np.clip(arr + RNG.normal(0, 3.0, arr.shape), 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _tampered(size: int = 256) -> Image.Image:
    base = np.asarray(_authentic(size)).copy()
    # Foreign region with much higher noise
    foreign = np.random.default_rng(7).normal(120, 50, (80, 80, 3))
    base[80:160, 80:160] = np.clip(foreign, 0, 255).astype(np.uint8)
    return Image.fromarray(base)


def test_residual_shape_and_2d():
    residual = extract_noise_residual(_authentic())
    assert residual.ndim == 2
    assert residual.shape == (256, 256)


def test_inconsistency_score_returns_non_negative_float():
    score = noise_inconsistency_score(extract_noise_residual(_authentic()))
    assert isinstance(score, float)
    assert score >= 0.0


def test_tampered_more_inconsistent_than_authentic():
    s_auth = noise_inconsistency_score(extract_noise_residual(_authentic()))
    s_tamp = noise_inconsistency_score(extract_noise_residual(_tampered()))
    assert s_tamp > s_auth, f"auth={s_auth:.3f} tamp={s_tamp:.3f}"


def test_noise_heatmap_shape_and_range():
    heat = noise_heatmap(extract_noise_residual(_authentic()))
    assert heat.ndim == 2
    assert heat.shape == (256, 256)
    assert heat.min() >= 0.0
    assert heat.max() <= 1.0
