"""Unit tests for ELA tampering detection.

Uses synthetic fixtures (smooth gradient vs. composite with foreign noisy
patch) so the suite runs deterministically without any external image
files. Real example images live under examples/ for the UI demo.
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from Aperture.tampering.ela import compute_ela, ela_score


RNG = np.random.default_rng(0)


def _authentic(size: int = 256) -> Image.Image:
    y = np.linspace(0, 1, size, dtype=np.float32)[:, None]
    sky = np.stack([
        135 + 80 * (1 - y) ** 1.4,
        180 + 50 * (1 - y) ** 1.4,
        220 - 40 * y,
    ], axis=-1)
    arr = np.broadcast_to(sky, (size, size, 3)).copy()
    noise = RNG.normal(0, 3.0, arr.shape).astype(np.float32)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _tampered(size: int = 256) -> Image.Image:
    base = np.asarray(_authentic(size)).copy()
    foreign = np.random.default_rng(123).integers(
        40, 220, size=(80, 80, 3), dtype=np.int16
    ).astype(np.uint8)
    base[60:140, 60:140] = foreign
    return Image.fromarray(base)


def test_compute_ela_shape_and_range():
    heatmap = compute_ela(_authentic())
    assert heatmap.ndim == 2
    assert heatmap.shape == (256, 256)
    assert heatmap.dtype == np.float32
    assert heatmap.min() >= 0.0
    assert heatmap.max() <= 1.0


def test_compute_ela_quality_bounds():
    img = _authentic()
    with pytest.raises(ValueError):
        compute_ela(img, quality=0)
    with pytest.raises(ValueError):
        compute_ela(img, quality=101)


def test_ela_score_returns_non_negative_float():
    score = ela_score(compute_ela(_authentic()))
    assert isinstance(score, float)
    assert score >= 0.0


def test_ela_score_tampered_higher_than_authentic():
    s_auth = ela_score(compute_ela(_authentic()))
    s_tamp = ela_score(compute_ela(_tampered()))
    assert s_tamp > s_auth, f"expected tampered>auth (auth={s_auth:.3f}, tamp={s_tamp:.3f})"


def test_ela_score_handles_uniform_image():
    flat = Image.new("RGB", (256, 256), (128, 128, 128))
    heat = compute_ela(flat)
    score = ela_score(heat)
    # A constant image has zero compression error; score is well-defined and 0.
    assert score == 0.0
