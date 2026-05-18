"""Reusable Streamlit UI components for Aperture.

All public render functions either return an HTML string (for embedding
via ``st.markdown(..., unsafe_allow_html=True)``) or call ``st`` directly
when they need full Streamlit machinery (image grids, etc.).
"""
from __future__ import annotations

from typing import Iterable, Optional

import streamlit as st
from PIL import Image

from Aperture.ui.theme import BAD, BG_CARD, BORDER, GOOD, PRIMARY, TEXT, TEXT_DIM, WARN

_STATUS_COLOR = {
    "good": GOOD,
    "warn": WARN,
    "bad": BAD,
    "neutral": TEXT_DIM,
}


def signal_card(
    title: str,
    score: str,
    status: str,
    icon_emoji: str,
    sublabel: Optional[str] = None,
) -> str:
    """One-signal summary card. Returns an HTML snippet."""
    status = status if status in _STATUS_COLOR else "neutral"
    sub_html = (
        f"<div style='color:{TEXT_DIM};font-size:0.8rem;margin-top:0.3rem;'>{sublabel}</div>"
        if sublabel else ""
    )
    return (
        f"<div class='ap-card ap-card-accent-{status}'>"
        f"<div class='ap-card-icon'>{icon_emoji}</div>"
        f"<div class='ap-card-title'>{title}</div>"
        f"<div class='ap-card-score'>{score}</div>"
        f"<div class='ap-card-status' style='color:{_STATUS_COLOR[status]};'>{status.upper()}</div>"
        f"{sub_html}"
        f"</div>"
    )


def confidence_meter(probability: float, label: str = "P(authentic)") -> str:
    """SVG donut for the verdict tab. ``probability`` in [0, 1]."""
    p = max(0.0, min(1.0, float(probability)))
    if p >= 0.7:
        color = GOOD
    elif p <= 0.3:
        color = BAD
    else:
        color = WARN
    radius = 80
    circumference = 2 * 3.14159265 * radius
    dash = circumference * p
    return (
        f"<div style='display:flex;justify-content:center;'>"
        f"<svg width='220' height='220' viewBox='0 0 220 220' style='display:block;'>"
        f"  <circle cx='110' cy='110' r='{radius}' stroke='{BORDER}' stroke-width='18' fill='none'/>"
        f"  <circle cx='110' cy='110' r='{radius}' stroke='{color}' stroke-width='18'"
        f"          fill='none' stroke-linecap='round'"
        f"          stroke-dasharray='{dash:.2f} {circumference:.2f}'"
        f"          transform='rotate(-90 110 110)'/>"
        f"  <text x='110' y='108' text-anchor='middle' font-family='Fraunces, serif'"
        f"        font-size='44' fill='{TEXT}'>{p*100:.0f}%</text>"
        f"  <text x='110' y='138' text-anchor='middle' font-family='Inter, sans-serif'"
        f"        font-size='11' fill='{TEXT_DIM}' letter-spacing='2'>"
        f"        {label.upper()}</text>"
        f"</svg></div>"
    )


def anomaly_flag(severity: str, message: str) -> str:
    """Colored pill for a metadata anomaly. severity in {low, medium, high}."""
    sev = (severity or "low").lower()
    color = {"high": BAD, "medium": WARN, "low": GOOD}.get(sev, TEXT_DIM)
    return (
        f"<span class='ap-flag' style='background-color:{color};'>"
        f"  <span style='font-weight:600;text-transform:uppercase;letter-spacing:0.05em;font-size:0.65rem;'>"
        f"    {sev}"
        f"  </span>"
        f"  &nbsp;{message}"
        f"</span>"
    )


def image_comparison(
    img1: Image.Image,
    img2: Image.Image,
    label1: str,
    label2: str,
) -> None:
    """Side-by-side image comparison."""
    cols = st.columns(2)
    with cols[0]:
        st.caption(label1)
        st.image(img1, width="stretch")
    with cols[1]:
        st.caption(label2)
        st.image(img2, width="stretch")


def verdict_banner(label: str) -> str:
    """Big serif headline for the verdict tab."""
    color = {
        "authentic": GOOD,
        "suspicious": WARN,
        "fake": BAD,
        "tampered": BAD,
        "untampered": GOOD,
    }.get((label or "").lower(), TEXT)
    return (
        f"<div class='ap-verdict-banner' style='color:{color};'>"
        f"{label.upper()}"
        f"</div>"
    )


def contribution_row(
    label: str,
    contribution: float,
    explanation: str,
    max_abs: float = 6.0,
) -> str:
    """One row in the 'Why this verdict?' expander.

    ``contribution`` is signed (positive = pulls toward authentic).
    """
    pct = max(0.04, min(1.0, abs(contribution) / max_abs))
    color = GOOD if contribution > 0 else BAD
    sign = "+" if contribution > 0 else "−"
    return (
        f"<div style='margin-bottom:0.9rem;'>"
        f"  <div style='display:flex;justify-content:space-between;align-items:baseline;'>"
        f"    <div style='font-weight:500;'>{label}</div>"
        f"    <div style='font-family:Fraunces,serif;color:{color};'>{sign}{abs(contribution):.2f}</div>"
        f"  </div>"
        f"  <div style='color:{TEXT_DIM};font-size:0.85rem;margin:0.25rem 0 0.4rem 0;'>{explanation}</div>"
        f"  <div class='ap-meter-track'>"
        f"    <div class='ap-meter-fill' style='width:{pct*100:.1f}%;background-color:{color};'></div>"
        f"  </div>"
        f"</div>"
    )


def section_eyebrow(text: str) -> str:
    return f"<div class='ap-eyebrow'>{text}</div>"


def html(snippet: str) -> None:
    """Write a raw HTML snippet to the page."""
    st.markdown(snippet, unsafe_allow_html=True)
