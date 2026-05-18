"""Weighted fusion of ELA + noise + copy-move into a single verdict."""
from __future__ import annotations

import numpy as np
from PIL import Image

from Aperture.tampering.copy_move import detect_copy_move, visualize_copy_move
from Aperture.tampering.ela import compute_ela, ela_score
from Aperture.tampering.noise import (
    extract_noise_residual,
    noise_heatmap,
    noise_inconsistency_score,
)

# Empirical normalization constants (raw scores -> [0, 1]).
# Tuned so that authentic images settle near 0.1-0.3 and obvious tampering >= 0.7
# on the synthetic fixtures in tests/. Override via compute_tampering_verdict()
# if you re-tune later.
ELA_NORM = 6.0
NOISE_NORM = 1.5
COPY_MOVE_NORM = 20.0

WEIGHT_ELA = 0.4
WEIGHT_NOISE = 0.4
WEIGHT_COPY_MOVE = 0.2

THRESHOLD_SUSPICIOUS = 0.3
THRESHOLD_TAMPERED = 0.6


def _normalize(value: float, scale: float) -> float:
    return float(min(max(value / scale, 0.0), 1.0))


def compute_tampering_verdict(pil_image: Image.Image) -> dict:
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    ela_map = compute_ela(pil_image)
    e_raw = ela_score(ela_map)
    e_norm = _normalize(e_raw, ELA_NORM)

    residual = extract_noise_residual(pil_image)
    n_raw = noise_inconsistency_score(residual)
    n_map = noise_heatmap(residual)
    n_norm = _normalize(n_raw, NOISE_NORM)

    cm = detect_copy_move(pil_image)
    cm_norm = _normalize(cm["matches_count"], COPY_MOVE_NORM)
    cm_vis = visualize_copy_move(pil_image, cm["match_pairs"])

    combined = (
        WEIGHT_ELA * e_norm
        + WEIGHT_NOISE * n_norm
        + WEIGHT_COPY_MOVE * cm_norm
    )
    if combined < THRESHOLD_SUSPICIOUS:
        verdict = "untampered"
    elif combined < THRESHOLD_TAMPERED:
        verdict = "suspicious"
    else:
        verdict = "tampered"

    return {
        "ela": {"score": float(e_raw), "score_normalized": e_norm, "heatmap": ela_map},
        "noise": {"score": float(n_raw), "score_normalized": n_norm, "heatmap": n_map},
        "copy_move": {
            "score": cm_norm,
            "matches_count": cm["matches_count"],
            "matches": cm["match_pairs"],
            "is_tampered": cm["is_tampered"],
            "visualization": cm_vis,
        },
        "combined_score": float(combined),
        "verdict": verdict,
    }
