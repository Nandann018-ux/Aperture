"""End-to-end test for the weighted tampering fusion."""
from __future__ import annotations

import numpy as np
from PIL import Image

from Aperture.tampering.combine import compute_tampering_verdict


RNG = np.random.default_rng(0)


def _authentic(size: int = 256) -> Image.Image:
    y = np.linspace(0, 1, size, dtype=np.float32)[:, None]
    sky = np.stack([
        135 + 80 * (1 - y) ** 1.4,
        180 + 50 * (1 - y) ** 1.4,
        220 - 40 * y,
    ], axis=-1)
    arr = np.broadcast_to(sky, (size, size, 3)).copy()
    arr = np.clip(arr + RNG.normal(0, 3.0, arr.shape), 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _tampered(size: int = 256) -> Image.Image:
    base = np.asarray(_authentic(size)).copy()
    foreign = np.random.default_rng(123).integers(
        40, 220, size=(120, 120, 3), dtype=np.int16
    ).astype(np.uint8)
    base[60:180, 60:180] = foreign
    return Image.fromarray(base)


def test_verdict_output_schema():
    result = compute_tampering_verdict(_authentic())
    assert {"ela", "noise", "copy_move", "combined_score", "verdict"} <= result.keys()
    assert 0.0 <= result["combined_score"] <= 1.0
    assert result["verdict"] in {"untampered", "suspicious", "tampered"}
    assert isinstance(result["ela"]["heatmap"], np.ndarray)
    assert isinstance(result["noise"]["heatmap"], np.ndarray)
    assert isinstance(result["copy_move"]["visualization"], Image.Image)


def test_tampered_scores_higher_than_authentic():
    auth = compute_tampering_verdict(_authentic())
    tamp = compute_tampering_verdict(_tampered())
    assert tamp["combined_score"] > auth["combined_score"], (
        f"auth={auth['combined_score']:.3f} tamp={tamp['combined_score']:.3f}"
    )


def test_authentic_passes_threshold():
    auth = compute_tampering_verdict(_authentic())
    assert auth["combined_score"] < 0.4, (
        f"authentic synthetic should be <0.4, got {auth['combined_score']:.3f}"
    )


def test_tampered_passes_threshold():
    tamp = compute_tampering_verdict(_tampered())
    assert tamp["combined_score"] > 0.5, (
        f"tampered synthetic should be >0.5, got {tamp['combined_score']:.3f}"
    )
