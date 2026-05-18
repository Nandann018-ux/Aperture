"""Calibration plot helper for the meta-classifier."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve


def plot_calibration(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    out_path: Path,
    n_bins: int = 10,
    title: str = "Meta-classifier reliability",
) -> Path:
    """Draw a reliability diagram and save it to ``out_path``.

    Bottom panel is a histogram of predicted probabilities, useful for
    spotting confidence collapse (all predictions near 0.5).
    """
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_prob)

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(6, 6), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    frac_pos, mean_pred = calibration_curve(y_true_arr, y_prob_arr, n_bins=n_bins, strategy="quantile")
    ax_top.plot([0, 1], [0, 1], "--", color="gray", alpha=0.6, label="perfectly calibrated")
    ax_top.plot(mean_pred, frac_pos, marker="o", color="#A78BFA", label="meta-classifier")
    ax_top.set_ylabel("Fraction of authentic in bin")
    ax_top.set_title(title)
    ax_top.set_ylim(-0.02, 1.02)
    ax_top.legend(loc="lower right")
    ax_top.grid(alpha=0.2)

    ax_bot.hist(y_prob_arr, bins=20, color="#A78BFA", alpha=0.7)
    ax_bot.set_xlabel("Predicted P(authentic)")
    ax_bot.set_ylabel("Count")
    ax_bot.grid(alpha=0.2)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
