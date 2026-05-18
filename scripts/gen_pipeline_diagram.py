"""Render a simple boxes-and-arrows diagram of the Aperture pipeline."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BG = "#0A0A0A"
CARD = "#141414"
BORDER = "#222222"
TEXT = "#F5F5F0"
TEXT_DIM = "#9A9A9A"
PRIMARY = "#A78BFA"


def _card(ax, x, y, w, h, title, sub):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=1.2, edgecolor=BORDER, facecolor=CARD,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
            fontsize=12, fontweight="medium", color=TEXT, family="serif")
    ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center",
            fontsize=8.5, color=TEXT_DIM)


def _arrow(ax, x1, y1, x2, y2):
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="->", mutation_scale=14,
        color=PRIMARY, alpha=0.85, lw=1.5,
    )
    ax.add_patch(arrow)


def main(out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # Input
    _card(ax, 0.3, 2.7, 2.0, 1.1, "Input image", "JPEG / PNG / WEBP")

    # Four pipelines
    pipelines = [
        ("AI Detection", "EfficientNet-B0\nCIFAKE-trained"),
        ("Tampering", "ELA · Noise · SIFT\nfused (0.4/0.4/0.2)"),
        ("Scene", "YOLOv8 · CLIP\nEasyOCR"),
        ("Metadata", "EXIF · JPEG\nrule-based flags"),
    ]
    pipe_x = 3.5
    for i, (title, sub) in enumerate(pipelines):
        y = 5.0 - i * 1.3
        _card(ax, pipe_x, y, 2.6, 1.05, title, sub)
        _arrow(ax, 2.3, 3.25, pipe_x, y + 0.5)

    # Feature vector
    _card(ax, 7.0, 2.7, 2.0, 1.1, "Feature vector",
          "ai_conf · tamper\nmeta · has_text")
    for i in range(4):
        y = 5.0 - i * 1.3
        _arrow(ax, pipe_x + 2.6, y + 0.5, 7.0, 3.25)

    # Meta-classifier
    _card(ax, 9.7, 2.7, 2.2, 1.1, "Meta-classifier",
          "Platt-calibrated LR\nP(authentic)")
    _arrow(ax, 9.0, 3.25, 9.7, 3.25)

    # Title
    ax.text(6, 6.2, "Aperture forensic pipeline",
            ha="center", va="center",
            fontsize=15, color=TEXT, family="serif", fontweight="medium")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main(Path("eval_results/pipeline_diagram.png"))
