"""Public entry point for the verdict ensemble.

Use :func:`compute_verdict` with a feature dict (4 keys) to get the
calibrated authenticity probability, a textual verdict, and a ranked
list of contributing factors with plain-English explanations.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import joblib

from Aperture.verdict.meta_classifier import FEATURE_ORDER, MetaClassifier

DEFAULT_MODEL_PATH = Path("models") / "meta_classifier.pkl"

THRESHOLD_FAKE = 0.3
THRESHOLD_AUTHENTIC = 0.7
SIGNIFICANT_CONTRIBUTION = 0.05  # |coef * value| above which we narrate the factor


@lru_cache(maxsize=4)
def _load_classifier(path: str) -> MetaClassifier:
    return joblib.load(path)


VALUE_THRESHOLD = 0.5  # above this, the feature is considered "elevated"


def _explain(factor: str, value: float, contribution: float) -> str:
    """Map (factor name, value) -> one English sentence.

    The sentence describes what the *feature value* says, not the sign of
    its contribution toward authenticity. (With uniformly-negative
    coefficients, even a low value produces a slightly-negative
    contribution; using contribution-sign here would mis-narrate clean
    images. Value-based phrasing is the user-facing source of truth.)
    """
    val_str = f"{value:.2f}"
    elevated = value >= VALUE_THRESHOLD

    if factor == "ai_conf":
        return (
            f"AI detector flagged this with high confidence (P(AI)={val_str})."
            if elevated
            else f"AI detector found no signs of generation (P(AI)={val_str})."
        )
    if factor == "tampering_score":
        return (
            f"Forensic analysis detected manipulation artifacts (score={val_str})."
            if elevated
            else f"Forensic analysis found no manipulation artifacts (score={val_str})."
        )
    if factor == "metadata_score":
        return (
            f"Metadata suggests editing software was used (anomaly={val_str})."
            if elevated
            else f"Metadata appears consistent with authentic capture (anomaly={val_str})."
        )
    if factor == "has_text":
        return (
            "Image contains readable text — verdict less reliable for "
            "text-heavy content; consider manual review."
            if elevated
            else "No readable text detected; OCR signal is neutral."
        )
    return f"{factor}={val_str} (contribution={contribution:+.3f})"


def _label(prob_authentic: float) -> str:
    if prob_authentic >= THRESHOLD_AUTHENTIC:
        return "authentic"
    if prob_authentic <= THRESHOLD_FAKE:
        return "fake"
    return "suspicious"


def compute_verdict(
    features: dict,
    model_path: Optional[Path] = None,
    top_k: Optional[int] = None,
) -> dict:
    """Return the calibrated authenticity verdict for a feature dict.

    Parameters
    ----------
    features
        Dict with keys ``ai_conf``, ``tampering_score``, ``metadata_score``,
        ``has_text``. Values in ``[0, 1]`` (``has_text`` should be 0 or 1).
    model_path
        Optional override for the pickled meta-classifier.
    top_k
        If given, truncate ``contributing_factors`` to the top-k by
        ``|contribution|``. ``None`` returns all four factors.
    """
    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    mc = _load_classifier(str(path.resolve()))

    prob = mc.predict_proba(features)
    factors_raw = mc.contributing_factors(features)
    if top_k is not None:
        factors_raw = factors_raw[:top_k]

    factors_out = []
    for f in factors_raw:
        factors_out.append({
            "factor": f["factor"],
            "value": f["value"],
            "contribution": f["contribution"],
            "explanation": _explain(f["factor"], f["value"], f["contribution"]),
        })

    return {
        "authenticity_probability": prob,
        "verdict": _label(prob),
        "contributing_factors": factors_out,
    }


__all__ = ["compute_verdict", "FEATURE_ORDER", "DEFAULT_MODEL_PATH"]
