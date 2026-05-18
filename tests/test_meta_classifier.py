"""Unit tests for the verdict meta-classifier."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from Aperture.verdict import compute_verdict
from Aperture.verdict.meta_classifier import (
    FEATURE_ORDER,
    MetaClassifier,
    synthesize_training_data,
    train_and_save,
)


@pytest.fixture(scope="module")
def trained(tmp_path_factory) -> tuple[Path, MetaClassifier]:
    """Train a meta-classifier once per test module and reuse the pickle."""
    tmp = tmp_path_factory.mktemp("meta")
    csv = tmp / "train.csv"
    synthesize_training_data(n_per_class=200, seed=0).to_csv(csv, index=False)
    out = tmp / "meta_classifier.pkl"
    mc, _ = train_and_save(csv, out, tmp / "eval", seed=0)
    return out, mc


def test_synthetic_data_shape():
    df = synthesize_training_data(n_per_class=50, seed=0)
    assert len(df) == 150  # 3 classes
    assert set(df.columns) == {*FEATURE_ORDER, "label"}
    assert df["label"].nunique() == 2  # only 1 = authentic, 0 = not


def test_train_runs_and_saves_pickle(trained):
    pkl, _ = trained
    assert pkl.exists()


def test_calibration_plot_saved(trained):
    pkl, _ = trained
    plot = pkl.parent / "eval" / "calibration_meta.png"
    assert plot.exists()
    assert plot.stat().st_size > 0


def test_compute_verdict_authentic(trained):
    pkl, _ = trained
    features = {"ai_conf": 0.05, "tampering_score": 0.07, "metadata_score": 0.04, "has_text": 0}
    out = compute_verdict(features, model_path=pkl)
    assert set(out.keys()) == {"authenticity_probability", "verdict", "contributing_factors"}
    assert 0.0 <= out["authenticity_probability"] <= 1.0
    assert out["verdict"] in {"authentic", "suspicious", "fake"}
    assert out["authenticity_probability"] > 0.5, (
        f"strongly-authentic features should land >0.5, got {out['authenticity_probability']}"
    )
    assert out["verdict"] == "authentic"


def test_compute_verdict_ai_generated(trained):
    pkl, _ = trained
    features = {"ai_conf": 0.92, "tampering_score": 0.10, "metadata_score": 0.20, "has_text": 0}
    out = compute_verdict(features, model_path=pkl)
    assert out["authenticity_probability"] < 0.5
    assert out["verdict"] in {"suspicious", "fake"}


def test_compute_verdict_tampered(trained):
    pkl, _ = trained
    features = {"ai_conf": 0.10, "tampering_score": 0.85, "metadata_score": 0.70, "has_text": 0}
    out = compute_verdict(features, model_path=pkl)
    assert out["authenticity_probability"] < 0.5
    assert out["verdict"] in {"suspicious", "fake"}


def test_contributing_factors_ranked_by_abs_contribution(trained):
    pkl, _ = trained
    features = {"ai_conf": 0.85, "tampering_score": 0.20, "metadata_score": 0.30, "has_text": 1}
    out = compute_verdict(features, model_path=pkl)
    contribs = [abs(f["contribution"]) for f in out["contributing_factors"]]
    assert contribs == sorted(contribs, reverse=True), (
        f"factors not sorted by |contribution|: {contribs}"
    )


def test_factors_have_english_explanations(trained):
    pkl, _ = trained
    features = {"ai_conf": 0.90, "tampering_score": 0.05, "metadata_score": 0.10, "has_text": 1}
    out = compute_verdict(features, model_path=pkl)
    for f in out["contributing_factors"]:
        assert isinstance(f["explanation"], str)
        assert len(f["explanation"]) > 10
        assert f["explanation"][0].isupper(), f"non-sentence: {f['explanation']!r}"


def test_explanations_match_sign(trained):
    pkl, _ = trained
    # High AI confidence -> the ai_conf factor should pull toward fake.
    features = {"ai_conf": 0.95, "tampering_score": 0.05, "metadata_score": 0.05, "has_text": 0}
    out = compute_verdict(features, model_path=pkl)
    ai_factor = next(f for f in out["contributing_factors"] if f["factor"] == "ai_conf")
    assert ai_factor["contribution"] < 0
    assert "flagged this with high confidence" in ai_factor["explanation"]


def test_missing_feature_raises(trained):
    pkl, _ = trained
    with pytest.raises(KeyError):
        compute_verdict({"ai_conf": 0.5}, model_path=pkl)
