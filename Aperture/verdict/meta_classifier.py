"""Meta-classifier combining the four Aperture signals into one verdict.

Features (in this exact order — also persisted on the saved model):
  - ai_conf:           P(image was AI-generated), from the AI detector
  - tampering_score:   weighted ELA+noise+copy-move score, from Phase 3
  - metadata_score:    EXIF / JPEG-anomaly score, from Phase 5
  - has_text:          binary OCR flag from the scene pipeline

Label semantics: ``1 = authentic`` (real and untampered), ``0 = fake or
tampered``.

For interpretability we keep an unwrapped ``LogisticRegression`` whose
``coef_`` we use to compute per-feature contributions. For calibrated
probabilities we wrap a separately-fit LR in ``CalibratedClassifierCV``
(Platt scaling, 5-fold). Both are stored together in :class:`MetaClassifier`
and pickled via joblib.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from Aperture.verdict.calibration import plot_calibration

FEATURE_ORDER: list[str] = ["ai_conf", "tampering_score", "metadata_score", "has_text"]


@dataclass
class MetaClassifier:
    """Container holding both the interpretable LR and the calibrated wrapper."""

    lr: LogisticRegression
    cal: CalibratedClassifierCV
    feature_order: list[str] = field(default_factory=lambda: list(FEATURE_ORDER))

    def _vectorize(self, features: dict) -> np.ndarray:
        missing = [f for f in self.feature_order if f not in features]
        if missing:
            raise KeyError(f"missing features: {missing}")
        return np.asarray([[float(features[f]) for f in self.feature_order]], dtype=np.float64)

    def predict_proba(self, features: dict) -> float:
        """Probability that the image is authentic (label = 1)."""
        x = self._vectorize(features)
        return float(self.cal.predict_proba(x)[0, 1])

    def contributing_factors(self, features: dict) -> list[dict]:
        """coef_i * x_i for each feature, ranked by |contribution| desc.

        Contribution sign points toward authenticity: positive = pulls
        toward authentic, negative = pulls toward fake/tampered.
        """
        x = self._vectorize(features)[0]
        coefs = self.lr.coef_[0]
        contributions = coefs * x
        order = np.argsort(-np.abs(contributions))
        return [
            {
                "factor": self.feature_order[i],
                "value": float(x[i]),
                "coefficient": float(coefs[i]),
                "contribution": float(contributions[i]),
            }
            for i in order
        ]

    def coefficients(self) -> dict:
        return {
            "intercept": float(self.lr.intercept_[0]),
            "coefficients": {f: float(c) for f, c in zip(self.feature_order, self.lr.coef_[0])},
        }


def synthesize_training_data(n_per_class: int = 200, seed: int = 0) -> pd.DataFrame:
    """Plausible per-class feature distributions for bootstrap training.

    Until the AI detector checkpoint + Phase 5 metadata pipeline land, this
    is the training-data substitute. Replace with a real CSV produced by
    running all four pipelines on labeled images, then retrain.
    """
    rng = np.random.default_rng(seed)
    rows: list[tuple[float, float, float, int, int]] = []

    def clip01(arr: np.ndarray) -> np.ndarray:
        return np.clip(arr, 0.0, 1.0)

    # 1. Authentic (label=1): low across all anomaly signals.
    ai = clip01(rng.beta(2, 12, n_per_class))
    tp = clip01(rng.beta(2, 12, n_per_class))
    md = clip01(rng.beta(2, 12, n_per_class))
    ht = (rng.random(n_per_class) < 0.20).astype(int)
    for v in zip(ai, tp, md, ht):
        rows.append((*v, 1))

    # 2. AI-generated (label=0): high ai_conf, low tampering, mixed metadata.
    ai = clip01(rng.beta(8, 2, n_per_class))
    tp = clip01(rng.beta(2, 10, n_per_class))
    md = clip01(rng.beta(3, 6, n_per_class))
    ht = (rng.random(n_per_class) < 0.15).astype(int)
    for v in zip(ai, tp, md, ht):
        rows.append((*v, 0))

    # 3. Tampered (label=0): low ai_conf, high tampering + metadata anomalies.
    ai = clip01(rng.beta(2, 8, n_per_class))
    tp = clip01(rng.beta(8, 3, n_per_class))
    md = clip01(rng.beta(6, 4, n_per_class))
    ht = (rng.random(n_per_class) < 0.25).astype(int)
    for v in zip(ai, tp, md, ht):
        rows.append((*v, 0))

    df = pd.DataFrame(rows, columns=[*FEATURE_ORDER, "label"])
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def train_and_save(
    csv_path: Path,
    out_pkl_path: Path,
    eval_dir: Path,
    test_size: float = 0.2,
    seed: int = 42,
) -> tuple[MetaClassifier, dict]:
    df = pd.read_csv(csv_path)
    missing_cols = [c for c in (*FEATURE_ORDER, "label") if c not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV missing columns: {missing_cols}")

    X = df[FEATURE_ORDER].to_numpy(dtype=np.float64)
    y = df["label"].to_numpy(dtype=int)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed,
    )

    lr_interp = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed)
    lr_interp.fit(X_tr, y_tr)

    lr_for_cal = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed)
    cal = CalibratedClassifierCV(lr_for_cal, method="sigmoid", cv=5)
    cal.fit(X_tr, y_tr)

    y_prob_test = cal.predict_proba(X_te)[:, 1]
    y_pred_test = (y_prob_test >= 0.5).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_te, y_pred_test)),
        "f1": float(f1_score(y_te, y_pred_test)),
        "auc": float(roc_auc_score(y_te, y_prob_test)),
        "n_train": int(X_tr.shape[0]),
        "n_test": int(X_te.shape[0]),
    }

    mc = MetaClassifier(lr=lr_interp, cal=cal, feature_order=list(FEATURE_ORDER))

    out_pkl_path.parent.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(mc, out_pkl_path)

    coefs = mc.coefficients()
    artifact = {
        "metrics": metrics,
        "intercept": coefs["intercept"],
        "coefficients": coefs["coefficients"],
        "feature_order": list(FEATURE_ORDER),
    }
    (eval_dir / "meta_classifier_summary.json").write_text(json.dumps(artifact, indent=2))

    plot_calibration(y_te, y_prob_test, eval_dir / "calibration_meta.png")

    return mc, artifact


def _build_default_csv_if_missing(csv_path: Path) -> None:
    if csv_path.exists():
        return
    df = synthesize_training_data()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/meta_classifier_training.csv")
    parser.add_argument("--out", default="models/meta_classifier.pkl")
    parser.add_argument("--eval-dir", default="eval_results")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    _build_default_csv_if_missing(csv_path)

    mc, artifact = train_and_save(csv_path, Path(args.out), Path(args.eval_dir), seed=args.seed)
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    # When invoked as `python -m Aperture.verdict.meta_classifier`,
    # MetaClassifier would bind to __main__.MetaClassifier and the
    # resulting pickle would be unloadable from any other process. Route
    # through the canonical module namespace so the dataclass pickles
    # under Aperture.verdict.meta_classifier.MetaClassifier.
    import sys as _sys
    _canonical = _sys.modules.get("Aperture.verdict.meta_classifier")
    if _canonical is not None and _canonical is not _sys.modules["__main__"]:
        _canonical.main()
    else:
        main()
