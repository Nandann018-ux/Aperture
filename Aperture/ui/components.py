"""Reusable Streamlit UI components for Aperture.

All public helpers either return an HTML string (for embedding via
``st.markdown(..., unsafe_allow_html=True)``) or call ``st`` directly when
they need full Streamlit machinery. CSS classes referenced here are
defined in :mod:`Aperture.ui.theme`.
"""
from __future__ import annotations

import html as _html_lib
from typing import Iterable, Optional

import streamlit as st
from PIL import Image

from Aperture.ui.theme import (
    ACCENT, AUTHENTIC, BAD, BG, BG_CARD, BORDER, BORDER_STRONG, FAKE,
    GOOD, PRIMARY, SURFACE_2, SUSPICIOUS, TEXT, TEXT_DIM, TEXT_FAINT,
    TEXT_MUTED, WARN,
)

_STATUS_COLOR = {
    "good": AUTHENTIC,
    "safe": AUTHENTIC,
    "warn": SUSPICIOUS,
    "watch": SUSPICIOUS,
    "bad": FAKE,
    "alert": FAKE,
    "neutral": TEXT_MUTED,
}


# --------------------------------------------------------------------------
# Low-level
# --------------------------------------------------------------------------

def html(snippet: str) -> None:
    """Write a raw HTML snippet to the page."""
    st.markdown(snippet, unsafe_allow_html=True)


def section_eyebrow(text: str) -> str:
    """Small uppercase-tracked label used above sections."""
    return f"<div class='ap-eyebrow'>{_html_lib.escape(text)}</div>"


def section_head(kicker: str, title: str, right: Optional[str] = None) -> str:
    """The design's ``.section-head`` row: kicker + serif title + rule + right kicker."""
    right_html = (
        f"<span class='kicker ap-mono'>{_html_lib.escape(right)}</span>"
        if right else ""
    )
    return (
        f"<div class='ap-section-head'>"
        f"  <span class='kicker'>{_html_lib.escape(kicker)}</span>"
        f"  <h2>{_html_lib.escape(title)}</h2>"
        f"  <span class='rule'></span>"
        f"  {right_html}"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Aperture iris — signature SVG element
# --------------------------------------------------------------------------

def aperture_iris(
    open_count: int = 0,
    total: int = 8,
    size: int = 220,
    glow: bool = False,
) -> str:
    """8-blade aperture SVG. ``open_count`` ∈ [0, total] drives how many
    blades have rotated open (and how much the pupil has dilated)."""
    import math
    cx = cy = size / 2
    rim_r = size * 0.46
    pupil_r = size * 0.08 + (size * 0.20) * min(1.0, open_count / total)
    closed_rot = 0
    open_rot = -42

    blades_svg: list[str] = []
    for i in range(total):
        amt = max(0.0, min(1.0, open_count - i))
        rot = closed_rot + (open_rot - closed_rot) * amt
        angle = (360 / total) * i
        opening = amt > 0.4
        fill = "#232C38" if opening else "#1C242E"
        stroke = "#6FA8DC" if opening else "#2E3845"
        stroke_op = 0.45 if opening else 0.7
        w = size * 0.16
        tip = size * 0.04
        r = size * 0.42
        path = (
            f"M {cx} {cy} "
            f"L {cx + w*0.7} {cy - r*0.25} "
            f"L {cx + tip} {cy - r*0.98} "
            f"L {cx - tip} {cy - r*0.98} "
            f"L {cx - w*0.7} {cy - r*0.25} Z"
        )
        blades_svg.append(
            f"<g style='transform: rotate({angle + rot}deg); "
            f"transform-origin: {cx}px {cy}px; "
            f"transition: transform 680ms cubic-bezier(0.4, 0, 0.2, 1);'>"
            f"<path d='{path}' fill='{fill}' stroke='{stroke}' "
            f"stroke-width='0.6' stroke-opacity='{stroke_op}' "
            f"stroke-linejoin='round'/>"
            f"</g>"
        )

    center_color = ACCENT if open_count >= total else "#2E3845"
    glow_svg = ""
    if glow:
        glow_svg = (
            f"<circle cx='{cx}' cy='{cy}' r='{size*0.52}' "
            f"fill='url(#ap-iris-glow)' />"
        )

    return f"""
    <svg width='{size}' height='{size}' viewBox='0 0 {size} {size}'
         style='display:block;overflow:visible;'>
      <defs>
        <radialGradient id='ap-iris-pupil' cx='50%' cy='50%' r='50%'>
          <stop offset='0%'  stop-color='{ACCENT}' stop-opacity='0.55'/>
          <stop offset='55%' stop-color='{ACCENT}' stop-opacity='0.12'/>
          <stop offset='100%' stop-color='{ACCENT}' stop-opacity='0'/>
        </radialGradient>
        <radialGradient id='ap-iris-glow' cx='50%' cy='50%' r='50%'>
          <stop offset='0%'  stop-color='{ACCENT}' stop-opacity='0.20'/>
          <stop offset='70%' stop-color='{ACCENT}' stop-opacity='0.04'/>
          <stop offset='100%' stop-color='{ACCENT}' stop-opacity='0'/>
        </radialGradient>
      </defs>
      {glow_svg}
      <circle cx='{cx}' cy='{cy}' r='{rim_r}' fill='none'
              stroke='#2E3845' stroke-width='1' opacity='0.7'/>
      <circle cx='{cx}' cy='{cy}' r='{rim_r + 6}' fill='none'
              stroke='#2E3845' stroke-width='0.5' opacity='0.3'/>
      <circle cx='{cx}' cy='{cy}' r='{rim_r - 1}' fill='{BG}'/>
      <circle cx='{cx}' cy='{cy}' r='{pupil_r}' fill='url(#ap-iris-pupil)'
              style='transition: r 680ms cubic-bezier(0.4, 0, 0.2, 1);'/>
      {''.join(blades_svg)}
      <circle cx='{cx}' cy='{cy}' r='2' fill='{center_color}'/>
    </svg>
    """


# --------------------------------------------------------------------------
# Dim icons — simple line-art SVGs for forensic-dimension cards
# --------------------------------------------------------------------------

def dim_icon(name: str, size: int = 32) -> str:
    """Line-art SVG icon. ``name`` ∈ {gen, manip, prov, comp, upload}."""
    stroke = "currentColor"
    sw = 1.25
    paths = {
        "gen": (
            f"<path d='M14 3 L24 9 L24 19 L14 25 L4 19 L4 9 Z' "
            f"stroke='{stroke}' stroke-width='{sw}' fill='none'/>"
            f"<path d='M9 14 L13 18 L19 10' stroke='{stroke}' "
            f"stroke-width='{sw}' stroke-linecap='round' stroke-linejoin='round' fill='none'/>"
        ),
        "manip": (
            f"<rect x='3' y='6' width='14' height='14' stroke='{stroke}' "
            f"stroke-width='{sw}' fill='none'/>"
            f"<rect x='11' y='10' width='14' height='14' stroke='{stroke}' "
            f"stroke-width='{sw}' fill='none'/>"
        ),
        "prov": (
            f"<circle cx='14' cy='14' r='9' stroke='{stroke}' stroke-width='{sw}' fill='none'/>"
            f"<path d='M14 9 L14 14 L18 16' stroke='{stroke}' stroke-width='{sw}' "
            f"stroke-linecap='round' fill='none'/>"
            f"<line x1='2' y1='3' x2='6' y2='3' stroke='{stroke}' stroke-width='{sw}' stroke-linecap='round'/>"
            f"<line x1='2' y1='6' x2='5' y2='6' stroke='{stroke}' stroke-width='{sw}' stroke-linecap='round'/>"
        ),
        "comp": (
            f"<rect x='3' y='3' width='22' height='22' stroke='{stroke}' "
            f"stroke-width='{sw}' stroke-dasharray='2 3' fill='none'/>"
            f"<rect x='6' y='10' width='8' height='8' stroke='{stroke}' stroke-width='{sw}' fill='none'/>"
            f"<rect x='16' y='6' width='6' height='6' stroke='{stroke}' stroke-width='{sw}' fill='none'/>"
        ),
        "upload": (
            f"<path d='M14 18 L14 5' stroke='{stroke}' stroke-width='{sw}' stroke-linecap='round'/>"
            f"<path d='M8 10 L14 4 L20 10' stroke='{stroke}' stroke-width='{sw}' "
            f"stroke-linecap='round' stroke-linejoin='round' fill='none'/>"
            f"<path d='M4 18 L4 24 L24 24 L24 18' stroke='{stroke}' "
            f"stroke-width='{sw}' stroke-linecap='round' fill='none'/>"
        ),
    }
    body = paths.get(name, "")
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 28 28' fill='none' "
        f"style='display:block;'>{body}</svg>"
    )


# --------------------------------------------------------------------------
# Verdict block — the big front-and-center result
# --------------------------------------------------------------------------

_VERDICT_PRESETS = {
    "authentic":  ("Likely authentic", AUTHENTIC, "rgba(127,184,154,0.12)"),
    "real":       ("Likely authentic", AUTHENTIC, "rgba(127,184,154,0.12)"),
    "untampered": ("Likely authentic", AUTHENTIC, "rgba(127,184,154,0.12)"),
    "suspicious": ("Suspicious",       SUSPICIOUS, "rgba(232,197,122,0.12)"),
    "fake":       ("Likely fake",      FAKE,      "rgba(224,122,95,0.12)"),
    "tampered":   ("Likely tampered",  FAKE,      "rgba(224,122,95,0.12)"),
}


def _verdict_classify(prob: float) -> str:
    if prob >= 0.7:
        return "authentic"
    if prob >= 0.3:
        return "suspicious"
    return "fake"


def verdict_block(
    probability: float,
    summary: str,
    label: Optional[str] = None,
    uncertainty: float = 1.8,
) -> str:
    """The big verdict block: probability + label + confidence band.

    ``probability`` is P(authentic) in [0, 1]. ``label`` overrides the
    auto-classified label when supplied (else derives from probability).
    """
    p = max(0.0, min(1.0, float(probability)))
    p_pct = round(p * 100)
    auto_key = _verdict_classify(p)
    key = (label or auto_key).lower()
    if key not in _VERDICT_PRESETS:
        key = auto_key
    title, color, glow = _VERDICT_PRESETS[key]

    return f"""
    <div class='ap-verdict-block' style='--verdict-color:{color};--verdict-glow:{glow};'>
      <div class='ap-verdict-prob'>
        <div class='lbl'>P(authentic)</div>
        <div class='num'>{p_pct}<span class='pct'>%</span></div>
        <div class='ap-mono' style='font-size:10.5px;color:{TEXT_FAINT};
             letter-spacing:0.04em;margin-top:4px;'>
          ±{uncertainty:.1f}% (95% CI · n=4 signals)
        </div>
      </div>
      <div class='ap-verdict-meta'>
        <div class='ap-verdict-label'>{_html_lib.escape(title)}</div>
        <div class='ap-verdict-summary'>{_html_lib.escape(summary)}</div>
        <div style='margin-top:10px;'>
          <div class='ap-confidence-bar'>
            <div class='zone fake'>Fake</div>
            <div class='zone susp'>Suspicious</div>
            <div class='zone auth'>Authentic</div>
            <div class='marker' style='left:{p_pct}%;'></div>
            <div class='scale'>
              <span>0</span><span>30</span><span>70</span><span>100</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    """


# --------------------------------------------------------------------------
# Signal card (verdict-tab 2x2 grid)
# --------------------------------------------------------------------------

def signal_viz(kind: str, status: str = "neutral", value: float = 0.5) -> str:
    """Tiny 132×132 visualization for a signal card. ``kind`` selects the
    visual: ``heatmap`` (AI), ``ela`` (tampering), ``scene`` (objects),
    ``meta`` (anomaly severity). ``value`` ∈ [0, 1] modulates intensity.
    """
    color = _STATUS_COLOR.get(status, ACCENT)
    v = max(0.0, min(1.0, float(value)))

    if kind == "heatmap":
        # Grad-CAM-ish: a soft warm/cool radial blob over a dark grid
        return (
            f"<svg viewBox='0 0 100 100' style='width:100%;height:100%;display:block;'>"
            f"  <defs>"
            f"    <radialGradient id='hm-{status}' cx='55%' cy='42%' r='42%'>"
            f"      <stop offset='0%' stop-color='{FAKE}' stop-opacity='{0.5+v*0.4:.2f}'/>"
            f"      <stop offset='45%' stop-color='{SUSPICIOUS}' stop-opacity='{0.25+v*0.25:.2f}'/>"
            f"      <stop offset='85%' stop-color='{ACCENT}' stop-opacity='0.10'/>"
            f"      <stop offset='100%' stop-color='{ACCENT}' stop-opacity='0'/>"
            f"    </radialGradient>"
            f"  </defs>"
            f"  <rect width='100' height='100' fill='{SURFACE_2}'/>"
            f"  <g stroke='{BORDER}' stroke-width='0.3' opacity='0.6'>"
            + "".join(f"<line x1='{i*10}' y1='0' x2='{i*10}' y2='100'/>"
                      f"<line x1='0' y1='{i*10}' x2='100' y2='{i*10}'/>" for i in range(11))
            + f"  </g>"
            f"  <rect width='100' height='100' fill='url(#hm-{status})'/>"
            f"</svg>"
        )

    if kind == "ela":
        # ELA strip: noise pattern with one bright "hot" patch when v is high
        spots = []
        for i in range(28):
            x = 8 + (i % 7) * 13
            y = 8 + (i // 7) * 22
            o = 0.10 + (0.45 if (i in (10, 11, 17, 18) and v > 0.4) else 0.12) * v
            c = FAKE if (i in (10, 11, 17, 18) and v > 0.5) else TEXT_FAINT
            spots.append(f"<rect x='{x}' y='{y}' width='8' height='12' "
                         f"fill='{c}' opacity='{o:.2f}'/>")
        return (
            f"<svg viewBox='0 0 100 100' style='width:100%;height:100%;display:block;'>"
            f"  <rect width='100' height='100' fill='{SURFACE_2}'/>"
            f"  {''.join(spots)}"
            f"</svg>"
        )

    if kind == "scene":
        # Bounding boxes over a striped placeholder — implies object detection
        return (
            f"<svg viewBox='0 0 100 100' style='width:100%;height:100%;display:block;'>"
            f"  <defs><pattern id='stripe-sc' patternUnits='userSpaceOnUse' "
            f"        width='6' height='6' patternTransform='rotate(135)'>"
            f"    <rect width='6' height='6' fill='{SURFACE_2}'/>"
            f"    <line x1='0' y1='0' x2='0' y2='6' stroke='{BG_CARD}' stroke-width='3'/>"
            f"  </pattern></defs>"
            f"  <rect width='100' height='100' fill='url(#stripe-sc)'/>"
            f"  <rect x='14' y='22' width='34' height='44' fill='none' "
            f"        stroke='{color}' stroke-width='1' stroke-dasharray='2 2'/>"
            f"  <rect x='58' y='14' width='28' height='22' fill='none' "
            f"        stroke='{color}' stroke-width='1' stroke-dasharray='2 2'/>"
            f"  <rect x='62' y='58' width='24' height='20' fill='none' "
            f"        stroke='{color}' stroke-width='1' stroke-dasharray='2 2'/>"
            f"</svg>"
        )

    if kind == "meta":
        # Severity bars: a row of 4 vertical bars, height encodes severity
        bars = []
        heights = [0.85 * v, 0.60 * v + 0.10, 0.40 * v + 0.05, 0.25 * v + 0.05]
        for i, h in enumerate(heights):
            x = 12 + i * 22
            bar_h = max(6, h * 70)
            y = 84 - bar_h
            c = FAKE if i == 0 and v > 0.5 else (SUSPICIOUS if i < 2 else AUTHENTIC)
            bars.append(f"<rect x='{x}' y='{y}' width='14' height='{bar_h}' "
                        f"fill='{c}' opacity='0.7' rx='1'/>")
            # baseline
        return (
            f"<svg viewBox='0 0 100 100' style='width:100%;height:100%;display:block;'>"
            f"  <rect width='100' height='100' fill='{SURFACE_2}'/>"
            f"  <line x1='8' y1='84' x2='92' y2='84' "
            f"        stroke='{BORDER}' stroke-width='0.5'/>"
            f"  {''.join(bars)}"
            f"</svg>"
        )

    # Default fallback: subtle striped placeholder with status dot
    return (
        f"<svg viewBox='0 0 100 100' style='width:100%;height:100%;display:block;'>"
        f"  <rect width='100' height='100' fill='{SURFACE_2}'/>"
        f"  <circle cx='50' cy='50' r='6' fill='{color}'/>"
        f"</svg>"
    )


def signal_card(
    title: str,
    score: str,
    status: str,
    icon_emoji: str = "",
    sublabel: Optional[str] = None,
    summary: Optional[str] = None,
    foot_tag: Optional[str] = None,
    viz_kind: Optional[str] = None,
    viz_value: float = 0.5,
) -> str:
    """Forensic-signal card. ``status`` ∈ {good, warn, bad, neutral}.

    Matches the design's ``.signal-card`` 1fr | 132px grid: title +
    big number + summary on the left, small ``.viz`` tile on the right,
    foot row spans both columns.
    """
    status_key = status if status in _STATUS_COLOR else "neutral"
    dot = _STATUS_COLOR[status_key]
    body = summary or sublabel or ""
    foot = (
        f"<div class='foot'><span>{_html_lib.escape(foot_tag)}</span>"
        f"<span style='color:{ACCENT};'>investigate →</span></div>"
        if foot_tag else ""
    )
    viz = (
        f"<div class='viz'>{signal_viz(viz_kind, status_key, viz_value)}</div>"
        if viz_kind else "<div class='viz'></div>"
    )
    return (
        f"<div class='ap-signal'>"
        f"  <div>"
        f"    <div class='head'>"
        f"      <span class='dot' style='background:{dot};'></span>"
        f"      {_html_lib.escape(title)}"
        f"    </div>"
        f"    <div class='big'>{score}</div>"
        f"    <div class='summary'>{_html_lib.escape(body)}</div>"
        f"  </div>"
        f"  {viz}"
        f"  {foot}"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Confidence meter — kept for back-compat; restyled to the design's bar
# --------------------------------------------------------------------------

def confidence_meter(probability: float, label: str = "P(authentic)") -> str:
    """Compact confidence band. ``probability`` in [0, 1].

    Replaces the old donut with the design's horizontal three-zone bar.
    """
    p = max(0.0, min(1.0, float(probability)))
    p_pct = round(p * 100)
    key = _verdict_classify(p)
    color = {"authentic": AUTHENTIC, "suspicious": SUSPICIOUS, "fake": FAKE}[key]
    return f"""
    <div style='display:flex;align-items:baseline;gap:18px;margin-bottom:12px;'>
      <div style='font-family:"Source Serif 4",serif;font-size:68px;font-weight:600;
                  color:{color};letter-spacing:-0.03em;line-height:1;'>
        {p_pct}<span style='font-size:22px;color:{TEXT_MUTED};margin-left:4px;'>%</span>
      </div>
      <div style='font-family:"JetBrains Mono",monospace;font-size:10px;
                  color:{TEXT_FAINT};letter-spacing:0.18em;text-transform:uppercase;'>
        {_html_lib.escape(label)}
      </div>
    </div>
    <div class='ap-confidence-bar' style='--verdict-color:{color};margin-bottom:32px;'>
      <div class='zone fake'>Fake</div>
      <div class='zone susp'>Suspicious</div>
      <div class='zone auth'>Authentic</div>
      <div class='marker' style='left:{p_pct}%;'></div>
      <div class='scale'>
        <span>0</span><span>30</span><span>70</span><span>100</span>
      </div>
    </div>
    """


# --------------------------------------------------------------------------
# Verdict banner (legacy — kept for any straggling callers)
# --------------------------------------------------------------------------

def verdict_banner(label: str) -> str:
    """Big serif verdict label."""
    key = (label or "").lower()
    title, color, _ = _VERDICT_PRESETS.get(
        key, ("Unknown", TEXT_MUTED, "rgba(0,0,0,0)"),
    )
    return (
        f"<div style='font-family:\"Source Serif 4\",serif;font-size:32px;"
        f"font-weight:600;letter-spacing:0.04em;text-transform:uppercase;"
        f"color:{TEXT};display:flex;align-items:center;gap:14px;margin:8px 0 16px;'>"
        f"  <span style='width:8px;height:32px;background:{color};display:inline-block;'></span>"
        f"  {_html_lib.escape(title)}"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Contribution row (verdict tab — "Why this verdict?")
# --------------------------------------------------------------------------

def contribution_row(
    label: str,
    contribution: float,
    explanation: str,
    max_abs: float = 6.0,
) -> str:
    """A signed-contribution row matching the design's ``.ap-factor`` style."""
    color = AUTHENTIC if contribution > 0 else FAKE
    sign = "+" if contribution > 0 else "−"
    abs_pct = min(50.0, abs(contribution) / max_abs * 50.0)
    left = 50.0 if contribution > 0 else 50.0 - abs_pct
    return (
        f"<div class='ap-factor' style='--factor-color:{color};'>"
        f"  <div class='name'>{_html_lib.escape(label)}</div>"
        f"  <div>"
        f"    <div class='bar-wrap'>"
        f"      <div class='axis'></div>"
        f"      <div class='bar' style='left:{left:.2f}%;width:{abs_pct:.2f}%;'></div>"
        f"    </div>"
        f"    <div class='expl'>{_html_lib.escape(explanation)}</div>"
        f"  </div>"
        f"  <div class='delta'>{sign}{abs(contribution):.2f}"
        f"    <span style='color:{TEXT_FAINT};margin-left:3px;'>pp</span>"
        f"  </div>"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Factor stack waterfall chart (verdict tab)
# --------------------------------------------------------------------------

def factor_stack_chart(
    factors: list[dict],
    baseline: float = 50.0,
    final: float = 50.0,
    verdict_color: Optional[str] = None,
) -> str:
    """SVG waterfall: baseline → contributions → final probability.

    Each factor needs keys: ``name`` (str), ``delta`` (signed float, in
    percentage points).
    """
    color = verdict_color or {
        "authentic": AUTHENTIC, "suspicious": SUSPICIOUS, "fake": FAKE
    }[_verdict_classify(final / 100.0)]
    W, H = 1080, 130
    pad_l, pad_r = 60, 60
    track_y, track_h = 56, 16
    inner = W - pad_l - pad_r

    def scale(v: float) -> float:
        return pad_l + (v / 100.0) * inner

    # Ticks
    ticks = []
    for t in (0, 25, 50, 75, 100):
        x = scale(t)
        ticks.append(
            f"<line x1='{x}' y1='{track_y-4}' x2='{x}' y2='{track_y+track_h+4}' "
            f"stroke='{BORDER}' stroke-width='0.5'/>"
            f"<text x='{x}' y='{track_y+track_h+22}' fill='{TEXT_FAINT}' "
            f"font-family='JetBrains Mono, monospace' font-size='9.5' "
            f"text-anchor='middle'>{t}</text>"
        )

    # Baseline marker
    bx = scale(baseline)
    base_marker = (
        f"<line x1='{bx}' y1='{track_y-14}' x2='{bx}' y2='{track_y+track_h+4}' "
        f"stroke='{TEXT_FAINT}' stroke-width='1' stroke-dasharray='2 2'/>"
        f"<text x='{bx}' y='{track_y-18}' fill='{TEXT_FAINT}' "
        f"font-family='JetBrains Mono, monospace' font-size='9.5' "
        f"text-anchor='middle' letter-spacing='1'>BASELINE</text>"
    )

    # Segments
    running = baseline
    segs = []
    for f in factors:
        start = running
        delta = float(f.get("delta", 0.0))
        end = running + delta
        running = end
        x1 = scale(min(start, end))
        x2 = scale(max(start, end))
        c = AUTHENTIC if delta > 0 else FAKE
        sign = "+" if delta > 0 else ""
        nm = (f.get("name") or "").split()[0].upper()
        segs.append(
            f"<rect x='{x1}' y='{track_y}' width='{max(2, x2-x1):.1f}' height='{track_h}' "
            f"fill='{c}' opacity='0.75'/>"
            f"<text x='{(x1+x2)/2:.1f}' y='{track_y-6}' fill='{c}' "
            f"font-family='JetBrains Mono, monospace' font-size='9.5' "
            f"text-anchor='middle'>{sign}{delta:.1f}</text>"
            f"<text x='{(x1+x2)/2:.1f}' y='{track_y+track_h+38}' fill='{TEXT_FAINT}' "
            f"font-family='JetBrains Mono, monospace' font-size='9' "
            f"text-anchor='middle' letter-spacing='0.4'>{_html_lib.escape(nm)}</text>"
        )

    # Final marker
    fx = scale(final)
    final_marker = (
        f"<line x1='{fx}' y1='{track_y-14}' x2='{fx}' y2='{track_y+track_h+4}' "
        f"stroke='{color}' stroke-width='1.5'/>"
        f"<polygon points='{fx-5},{track_y-18} {fx+5},{track_y-18} {fx},{track_y-10}' "
        f"fill='{color}'/>"
        f"<text x='{fx}' y='{track_y-22}' fill='{color}' "
        f"font-family='JetBrains Mono, monospace' font-size='10' "
        f"text-anchor='middle' letter-spacing='0.4'>FINAL · {final:.0f}%</text>"
    )

    return (
        f"<div style='background:{BG_CARD};border:1px solid {BORDER};"
        f"padding:20px 24px;margin-top:24px;border-radius:3px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:baseline;"
        f"margin-bottom:16px;'>"
        f"  <div class='ap-label'>factor stack · how each signal moved the verdict</div>"
        f"  <div class='ap-mono' style='font-size:10px;color:{TEXT_FAINT};'>"
        f"    baseline 50% → {final:.0f}%</div>"
        f"</div>"
        f"<svg viewBox='0 0 {W} {H}' width='100%' style='display:block;'>"
        f"  <line x1='{pad_l}' y1='{track_y+track_h/2}' x2='{W-pad_r}' y2='{track_y+track_h/2}' "
        f"        stroke='{BORDER}' stroke-width='1'/>"
        f"  {''.join(ticks)}"
        f"  {base_marker}"
        f"  {''.join(segs)}"
        f"  {final_marker}"
        f"</svg>"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Dim card (welcome screen)
# --------------------------------------------------------------------------

def dim_card(num: str, icon: str, title: str, body: str, foot: str) -> str:
    return (
        f"<div class='ap-dim'>"
        f"  <div class='num'>{_html_lib.escape(num)}</div>"
        f"  <div class='icon'>{dim_icon(icon, 32)}</div>"
        f"  <h3>{_html_lib.escape(title)}</h3>"
        f"  <p>{_html_lib.escape(body)}</p>"
        f"  <div class='foot'>{_html_lib.escape(foot)}</div>"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Honest-note callout (used on Performance OOD section)
# --------------------------------------------------------------------------

def honest_note(label: str, message: str) -> str:
    return (
        f"<div class='ap-honest'>"
        f"  <span class='tag'>{_html_lib.escape(label)}</span>"
        f"  {_html_lib.escape(message)}"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Image comparison (kept for back-compat; restyled caption)
# --------------------------------------------------------------------------

def image_comparison(
    img1: Image.Image,
    img2: Image.Image,
    label1: str,
    label2: str,
) -> None:
    cols = st.columns(2)
    with cols[0]:
        st.caption(label1)
        st.image(img1, use_column_width=True)
    with cols[1]:
        st.caption(label2)
        st.image(img2, use_column_width=True)


# --------------------------------------------------------------------------
# Image chip — small thumbnail + filename header for result tabs
# --------------------------------------------------------------------------

def image_chip_html(
    thumb_data_uri: str,
    filename: str,
    meta: str,
) -> str:
    """Compact image-chip header. Matches the design's ``.ap-imgchip``."""
    return (
        f"<div class='ap-imgchip'>"
        f"  <img src='{thumb_data_uri}' alt='' "
        f"       style='width:44px;height:44px;flex-shrink:0;"
        f"       border:1px solid {BORDER};object-fit:cover;display:block;'/>"
        f"  <div style='display:flex;flex-direction:column;gap:2px;'>"
        f"    <span style='font-size:12px;color:{TEXT};font-weight:500;'>"
        f"      {_html_lib.escape(filename)}</span>"
        f"    <span class='ap-mono' style='font-size:10px;color:{TEXT_FAINT};"
        f"          letter-spacing:0.04em;'>{_html_lib.escape(meta)}</span>"
        f"  </div>"
        f"</div>"
    )


def image_chip(image: Image.Image, filename: str, max_thumb: int = 88) -> str:
    """Compact image-chip header. Renders a 44px thumb (via base64 data URI)
    next to the filename + ``W × H · MODE`` meta line.
    """
    import base64
    import io as _io

    thumb = image.copy()
    thumb.thumbnail((max_thumb, max_thumb))
    buf = _io.BytesIO()
    fmt = "PNG" if thumb.mode in ("RGBA", "P") else "JPEG"
    thumb.save(buf, format=fmt, quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    data_uri = f"data:{mime};base64,{b64}"

    meta = f"{image.size[0]} × {image.size[1]} px · {image.mode}"
    return image_chip_html(data_uri, filename, meta)


# --------------------------------------------------------------------------
# Live analysis view — image + iris + labels + log (replaces st.spinner)
# --------------------------------------------------------------------------

ANALYSIS_STAGES: list[tuple[str, str]] = [
    ("tampering",  "Manipulation analysis"),
    ("metadata",   "Metadata extraction"),
    ("scene",      "Scene parsing"),
    ("ai",         "Generative analysis"),
    ("verdict",    "Verdict synthesis"),
]


def iris_labels_html(states: list[tuple[str, str, str]]) -> str:
    """``states`` is a list of (label, state, hint) where state ∈ {queued, running, done}."""
    rows = []
    for label, state, hint in states:
        cls = state if state in ("running", "done") else ""
        hint_html = (
            f"<span style='margin-left:auto;font-size:9.5px;color:{TEXT_FAINT};"
            f"letter-spacing:0.08em;'>{_html_lib.escape(hint)}</span>"
        )
        rows.append(
            f"<div class='iris-label {cls}'>"
            f"  <span class='ind'></span>"
            f"  <span>{_html_lib.escape(label)}</span>"
            f"  {hint_html}"
            f"</div>"
        )
    return (
        f"<div style='display:grid;grid-template-columns:1fr 1fr;"
        f"gap:6px 24px;margin-top:18px;'>{''.join(rows)}</div>"
    )


def log_block_html(lines: list[tuple[str, str, str]]) -> str:
    """``lines`` is a list of (timestamp, kind, text); ``kind`` ∈ {info, run, ok}."""
    rendered = []
    for ts, kind, text in lines[-10:]:
        kind_color = {
            "ok": AUTHENTIC, "run": SUSPICIOUS, "info": TEXT_MUTED,
        }.get(kind, TEXT_MUTED)
        rendered.append(
            f"<div class='log-line'>"
            f"  <span style='color:{TEXT_FAINT};'>[{_html_lib.escape(ts)}]</span> "
            f"  <span style='color:{kind_color};'>{_html_lib.escape(text)}</span>"
            f"</div>"
        )
    return f"<div class='ap-log'>{''.join(rendered)}</div>"


def iris_stage_html(open_count: int, total: int = 8, size: int = 220) -> str:
    """Wraps ``aperture_iris(...)`` in a centered stage block with the
    ambient breath-halo backdrop defined in tokens.css."""
    return (
        f"<div class='ap-iris-stage'>"
        f"{aperture_iris(open_count=open_count, total=total, size=size, glow=open_count>=total)}"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Topbar breadcrumb (Aperture / home)
# --------------------------------------------------------------------------

def topbar(
    crumbs: list[str],
    current: str,
    session_info: Optional[list[tuple[str, str]]] = None,
) -> str:
    """Full-viewport sticky topbar with breadcrumb (left) + optional session
    info (right). All visual rules live on ``.ap-topbar`` in theme.py.

    ``session_info`` is a list of ``(text, mono?)`` pairs; when ``mono`` is
    True the value renders bolder and in ``--text-dim`` (used for filename,
    session id).
    """
    crumb_parts = []
    for c in crumbs:
        crumb_parts.append(f"<span>{_html_lib.escape(c)}</span>")
        crumb_parts.append("<span class='sep'>/</span>")
    crumb_parts.append(f"<span class='cur'>{_html_lib.escape(current)}</span>")

    session_html = ""
    if session_info:
        chips = []
        for text, mono in session_info:
            esc = _html_lib.escape(text)
            chips.append(f"<b>{esc}</b>" if mono else f"<span>{esc}</span>")
        session_html = f"<div class='session'>{''.join(chips)}</div>"

    return (
        f"<div class='ap-topbar'>"
        f"  <div class='crumb'>{''.join(crumb_parts)}</div>"
        f"  <div class='grow'></div>"
        f"  {session_html}"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Pipeline diagram (welcome screen — How it works)
# --------------------------------------------------------------------------

def pipeline_diagram_doc(height: int = 280) -> str:
    """Self-contained HTML doc wrapping ``pipeline_diagram()`` for use with
    ``streamlit.components.v1.html(...)``. Renders the SVG inside an
    isolated iframe so Streamlit's React markdown pipeline can't choke on
    the inline SVG comments/attributes.
    """
    inner = pipeline_diagram()
    # Token definitions duplicated minimally inside the iframe so the
    # SVG's var(--bg) / var(--text) / var(--border) etc. resolve.
    return f"""<!doctype html><html><head><meta charset='utf-8'/>
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:wght@500;600;700&display=swap' rel='stylesheet'>
<style>
:root {{
  --bg: #F4F2EC; --surface-1: #FFFFFF; --surface-2: #F8F6F0;
  --border: #DEDACE; --border-strong: #C9C4B6;
  --text: #14181F; --text-dim: #3D4654; --text-muted: #6C7585; --text-faint: #99A0AC;
  --accent: #2F6FB1; --authentic: #3F8A66; --suspicious: #B58527; --fake: #B5462B;
}}
html, body {{
  margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: Inter, -apple-system, sans-serif;
}}
svg {{ display: block; }}
.diag-wrap {{
  background: var(--surface-1); border: 1px solid var(--border);
  padding: 28px 32px; border-radius: 3px;
}}
</style></head>
<body>
<div class='diag-wrap'>{inner}</div>
</body></html>"""


def pipeline_diagram() -> str:
    """The SVG flow: image input → 4 forensic stages → Σ fuse → Verdict.

    All fills/strokes use CSS variables (``var(--bg)``, ``var(--accent)``,
    etc.) defined in the iframe stylesheet emitted by
    :func:`pipeline_diagram_doc`.
    """
    W, H = 1080, 220
    input_x = 40
    fuse_x = 560
    verdict_x = 920
    cy = H / 2

    stages = [
        {"y": 40,  "label": "Generative analysis",
         "code": "EfficientNet-B0 · Grad-CAM",       "color": "var(--accent)"},
        {"y": 90,  "label": "Tampering analysis",
         "code": "ELA · noise · copy-move",          "color": "var(--fake)"},
        {"y": 140, "label": "Scene + OCR",
         "code": "YOLOv8n · scene-cls · easyocr",    "color": "var(--authentic)"},
        {"y": 190, "label": "Metadata + EXIF",
         "code": "exif · qtable · anomaly-rules",    "color": "var(--suspicious)"},
    ]

    # Branch lines from input → 4 stages (cubic curves to avoid kinks)
    branches = "".join(
        f"<path d='M {input_x+120} {cy} C {(input_x+120+240)/2} {cy}, "
        f"{(input_x+120+240)/2} {s['y']}, 240 {s['y']}' "
        f"stroke='var(--border-strong)' stroke-width='0.7' fill='none'/>"
        for s in stages
    )

    # 4 stage rows
    stage_rows = []
    for s in stages:
        stage_rows.append(
            f"<line x1='240' x2='530' y1='{s['y']}' y2='{s['y']}' "
            f"stroke='{s['color']}' stroke-width='0.4' opacity='0.5'/>"
            f"<rect x='240' y='{s['y']-14}' width='290' height='28' "
            f"fill='var(--bg)' stroke='var(--border)'/>"
            f"<circle cx='258' cy='{s['y']}' r='4' fill='{s['color']}'/>"
            f"<text x='272' y='{s['y']+4}' fill='var(--text-dim)' "
            f"font-family='Inter, sans-serif' font-size='11.5' "
            f"font-weight='500'>{_html_lib.escape(s['label'])}</text>"
            f"<text x='520' y='{s['y']+4}' fill='var(--text-faint)' "
            f"font-family='JetBrains Mono, monospace' font-size='9.5' "
            f"text-anchor='end' letter-spacing='0.4'>{_html_lib.escape(s['code'])}</text>"
        )

    # Converging lines from stages → Σ
    converging = "".join(
        f"<path d='M 530 {s['y']} C 620 {s['y']}, 620 {cy}, "
        f"{fuse_x+20} {cy}' stroke='var(--border-strong)' stroke-width='0.7' fill='none'/>"
        for s in stages
    )

    return f"""
      <svg viewBox='0 0 {W} {H}' width='100%' style='display:block;'>
        <!-- Input -->
        <rect x='{input_x}' y='{cy-26}' width='120' height='52' fill='var(--bg)'
              stroke='var(--border-strong)'/>
        <text x='{input_x+60}' y='{cy-6}' fill='var(--text-dim)'
              font-family='JetBrains Mono, monospace' font-size='11'
              text-anchor='middle'>image.jpg</text>
        <text x='{input_x+60}' y='{cy+10}' fill='var(--text-faint)'
              font-family='JetBrains Mono, monospace' font-size='9'
              text-anchor='middle' letter-spacing='1'>INPUT</text>

        {branches}
        {''.join(stage_rows)}
        {converging}

        <!-- Σ fuse -->
        <circle cx='{fuse_x+70}' cy='{cy}' r='36' fill='var(--surface-2)'
                stroke='var(--accent)' stroke-width='1'/>
        <circle cx='{fuse_x+70}' cy='{cy}' r='28' fill='none'
                stroke='var(--accent)' stroke-width='0.4'
                stroke-dasharray='2 3' opacity='0.6'/>
        <text x='{fuse_x+70}' y='{cy-2}' fill='var(--text)'
              font-family='Source Serif 4, Georgia, serif' font-size='13'
              text-anchor='middle' font-weight='600'>Σ</text>
        <text x='{fuse_x+70}' y='{cy+14}' fill='var(--text-muted)'
              font-family='JetBrains Mono, monospace' font-size='9'
              text-anchor='middle' letter-spacing='1'>META-CLF</text>
        <text x='{fuse_x+70}' y='{cy+60}' fill='var(--text-faint)'
              font-family='JetBrains Mono, monospace' font-size='9.5'
              text-anchor='middle' letter-spacing='1'>PLATT-CALIBRATED LR</text>

        <!-- Σ → Verdict arrow -->
        <path d='M {fuse_x+106} {cy} L {verdict_x-20} {cy}'
              stroke='var(--accent)' stroke-width='1' fill='none'/>
        <polygon points='{verdict_x-20},{cy-4} {verdict_x-20},{cy+4} {verdict_x-12},{cy}'
                 fill='var(--accent)'/>

        <!-- Verdict box -->
        <rect x='{verdict_x-4}' y='{cy-28}' width='140' height='56'
              fill='var(--bg)' stroke='var(--accent)'/>
        <text x='{verdict_x+66}' y='{cy-6}' fill='var(--text)'
              font-family='Source Serif 4, Georgia, serif' font-weight='600'
              font-size='15' text-anchor='middle'>Verdict</text>
        <text x='{verdict_x+66}' y='{cy+12}' fill='var(--accent)'
              font-family='JetBrains Mono, monospace' font-size='9.5'
              text-anchor='middle' letter-spacing='1'>P(AUTHENTIC) · CONTRIBS</text>
      </svg>
    """


# --------------------------------------------------------------------------
# Sidebar pieces
# --------------------------------------------------------------------------

def sidebar_section_head(title: str) -> str:
    """``TITLE ─────`` row with flex rule on the right."""
    return (
        f"<div style='display:flex;align-items:center;gap:8px;margin:18px 0 10px;'>"
        f"  <span class='ap-mono' style='font-size:10px;font-weight:600;"
        f"       letter-spacing:0.18em;text-transform:uppercase;"
        f"       color:{TEXT_FAINT};'>{_html_lib.escape(title)}</span>"
        f"  <span style='flex:1;height:1px;background:{BORDER};'></span>"
        f"</div>"
    )


def divider_or(text: str = "or try an example") -> str:
    """``──── OR TRY AN EXAMPLE ────`` divider."""
    return (
        f"<div style='display:flex;align-items:center;gap:10px;margin:14px 0 10px;"
        f"font-family:JetBrains Mono,monospace;font-size:9.5px;"
        f"color:{TEXT_FAINT};letter-spacing:0.16em;text-transform:uppercase;'>"
        f"  <span style='flex:1;height:1px;background:{BORDER};'></span>"
        f"  <span>{_html_lib.escape(text)}</span>"
        f"  <span style='flex:1;height:1px;background:{BORDER};'></span>"
        f"</div>"
    )


# Example tile color palettes from sidebar.jsx
_TILE_PALETTES = {
    "auth-portrait":  ("#3A4858", "#1A222C", "authentic"),
    "auth-landscape": ("#3F5747", "#1B2620", "authentic"),
    "ai-realistic":   ("#4A3F5A", "#221C2E", "fake"),
    "ai-midjourney":  ("#5A3F4E", "#2A1C28", "fake"),
    "copy-move":      ("#574B3A", "#2A2218", "tampered"),
    "composite":      ("#3A5057", "#172428", "tampered"),
    "metadata-1":     ("#3F4A5A", "#1C2230", "tampered"),  # photoshop
    "metadata-2":     ("#4A4836", "#22201C", "tampered"),  # date drift
    "metadata-3":     ("#3A3F47", "#1A1E22", "tampered"),  # low quality
    "metadata-4":     ("#5A3F4A", "#2A1C25", "fake"),      # ai signature
}
_KIND_DOT = {
    "authentic": AUTHENTIC,
    "fake":      FAKE,
    "tampered":  SUSPICIOUS,
}


def example_tile_button_css() -> str:
    """CSS that turns the 6 sidebar tile buttons into gradient swatch tiles.

    Strategy: inside the sidebar, after a marker ``.ap-tile-row-N-anchor`` div,
    the very next element-container is a horizontal block holding 3 columns
    each with one st.button. We restyle those buttons (per row × column) into
    aspect-1, gradient-filled tiles with a kind-pip and a mono bottom-left
    label. Modern :has() makes the targeting scoped instead of fragile-global.
    """
    # The 6 canonical tiles (matching the design's sidebar.jsx)
    # (col0_c1, col0_c2, col0_pip) per row, scanning left→right top→bottom
    tiles = [
        # Row 1
        [("#3A4858", "#1A222C", AUTHENTIC),
         ("#3F5747", "#1B2620", AUTHENTIC),
         ("#4A3F5A", "#221C2E", FAKE)],
        # Row 2
        [("#5A3F4E", "#2A1C28", FAKE),
         ("#574B3A", "#2A2218", SUSPICIOUS),
         ("#3A5057", "#172428", SUSPICIOUS)],
    ]

    rules: list[str] = []

    # Selector helper: anchor sits inside element-container > stMarkdownContainer.
    # Walk to the element-container that contains it, then to its next-sibling
    # element-container — which holds the columns.
    def row_sel(row_idx: int) -> str:
        return (
            f"[data-testid='stSidebar'] "
            f"[data-testid='element-container']"
            f":has(.ap-tile-row-{row_idx}-anchor) "
            f"+ [data-testid='element-container']"
        )

    # Base style applied to all tile buttons (both rows, all 3 cols each)
    base_buttons = ", ".join(
        f"{row_sel(r)} [data-testid='stButton'] button"
        for r in (1, 2)
    )
    base_before = ", ".join(
        f"{row_sel(r)} [data-testid='stButton'] button::before"
        for r in (1, 2)
    )
    base_hover = ", ".join(
        f"{row_sel(r)} [data-testid='stButton'] button:hover"
        for r in (1, 2)
    )
    base_inner_p = ", ".join(
        f"{row_sel(r)} [data-testid='stButton'] button p"
        for r in (1, 2)
    )
    base_inner_div = ", ".join(
        f"{row_sel(r)} [data-testid='stButton'] button > div"
        for r in (1, 2)
    )
    selected_btn = ", ".join(
        f"{row_sel(r)} [data-testid='stButton'] button[kind='primary']"
        for r in (1, 2)
    )

    rules.append(f"""
        {base_buttons} {{
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            min-height: 0 !important;
            border: 1px solid {BORDER} !important;
            border-radius: 2px !important;
            background: linear-gradient(135deg, var(--ct-c1, #2A3A4A), var(--ct-c2, #1A2028)) !important;
            color: rgba(236,239,244,0.85) !important;
            font-family: var(--font-mono) !important;
            font-size: 8.5px !important;
            font-weight: 500 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
            padding: 0 6px 5px 6px !important;
            display: flex !important;
            align-items: flex-end !important;
            justify-content: flex-start !important;
            text-align: left !important;
            position: relative !important;
            overflow: hidden !important;
            cursor: pointer;
            box-shadow: none !important;
            transition: border-color 150ms cubic-bezier(0.4,0,0.2,1) !important;
        }}
        {base_before} {{
            content: "";
            position: absolute;
            top: 5px;
            right: 5px;
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: var(--ct-pip, {TEXT_MUTED});
        }}
        {base_hover} {{
            border-color: rgba(111,168,220,0.45) !important;
            transform: none !important;
            color: rgba(236,239,244,1) !important;
        }}
        {base_inner_div} {{ width: 100% !important; }}
        {base_inner_p}   {{ margin: 0 !important; line-height: 1 !important; }}
        {selected_btn} {{
            border: 1px solid {ACCENT} !important;
            box-shadow: 0 0 0 1px {ACCENT}, 0 0 0 4px rgba(111,168,220,0.10) !important;
        }}
    """)

    # Per-tile gradients + pip colors via CSS custom properties
    for row_idx, row in enumerate(tiles, start=1):
        for col_idx, (c1, c2, pip) in enumerate(row, start=1):
            sel = (
                f"{row_sel(row_idx)} "
                f"[data-testid='stColumn']:nth-of-type({col_idx}) "
                f"[data-testid='stButton'] button"
            )
            rules.append(
                f"{sel} {{ --ct-c1: {c1}; --ct-c2: {c2}; --ct-pip: {pip}; }}"
            )

    return f"<style>{''.join(rules)}</style>"


# Canonical 6-tile set: (mono_label, full_dropdown_label_to_select).
# Tiles cover all four required categories: 2 authentic photos,
# 2 AI-generated samples (CIFAKE), 1 tampered composite, 1 metadata
# anomaly (Photoshop tag). The 4 other examples in EXAMPLE_FILES
# (Copy-move, date drift, low-quality JPEG, AI-tool signature) are
# reachable via the selectbox/URL but not as primary tiles.
TILE_DROPDOWN_MAP: list[tuple[str, str]] = [
    ("PORTRAIT",  "Authentic portrait"),
    ("LANDSCAPE", "Authentic landscape"),
    ("AI-REAL",   "AI — realistic"),
    ("MJ-MIST",   "AI — Midjourney-style"),
    ("COMP",      "Tampered composite"),
    ("PHOTOSHOP", "Metadata: Photoshop edit"),
]


def example_tile_grid_iframe(selected_label: str = "(none)") -> str:
    """Pixel-accurate clone of the design's example-tile grid.

    Returns a self-contained HTML document for ``components.html(...)``.
    Each tile is a real ``<button>`` matching ``sidebar.jsx`` exactly:
      - dark colored gradient swatch (c1 → c2 at 135deg)
      - kind-colored pip in top-right
      - mono tag in bottom-left
      - subtle hover lift + accent border
    Selection persists across reruns via ``?example=<label>`` URL param
    on the parent page; the click handler navigates the parent to that
    URL so Streamlit picks the selection up on rerun.
    """
    import json as _json

    # Six tiles, same order/colors/labels as the design's ``EXAMPLE_IMAGES``
    # and our :data:`TILE_DROPDOWN_MAP`.
    tiles = [
        {"label": "PORTRAIT",  "full": "Authentic portrait",         "c1": "#3A4858", "c2": "#1A222C", "kind": "authentic"},
        {"label": "LANDSCAPE", "full": "Authentic landscape",        "c1": "#3F5747", "c2": "#1B2620", "kind": "authentic"},
        {"label": "AI-REAL",   "full": "AI — realistic",              "c1": "#4A3F5A", "c2": "#221C2E", "kind": "fake"},
        {"label": "MJ-MIST",   "full": "AI — Midjourney-style",       "c1": "#5A3F4E", "c2": "#2A1C28", "kind": "fake"},
        {"label": "COMP",      "full": "Tampered composite",          "c1": "#3A5057", "c2": "#172428", "kind": "tampered"},
        {"label": "PHOTOSHOP", "full": "Metadata: Photoshop edit",    "c1": "#574B3A", "c2": "#2A2218", "kind": "tampered"},
    ]

    tiles_html = "".join(
        f"""<button class='ex {"sel" if t["full"] == selected_label else ""}'
                    data-full='{_html_lib.escape(t["full"])}'
                    title='{_html_lib.escape(t["full"])}'>
              <span class='swatch' style='--c1:{t["c1"]};--c2:{t["c2"]}'></span>
              <span class='pip' data-kind='{t["kind"]}'></span>
              <span class='tag'>{t["label"]}</span>
            </button>"""
        for t in tiles
    )

    return f"""<!doctype html><html><head><meta charset='utf-8'>
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link href='https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>
<style>
:root {{
  --bg: transparent;
  --border: #DEDACE; --border-strong: #C9C4B6;
  --accent: #2F6FB1; --accent-soft: rgba(47,111,177,0.10); --accent-line: rgba(47,111,177,0.45);
  --authentic: #3F8A66; --fake: #B5462B; --tampered: #B58527;
  --text-muted: #6C7585;
  --dur: 240ms; --ease: cubic-bezier(0.4,0,0.2,1);
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0; background: transparent;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}}
.grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
  padding: 0;
}}
.ex {{
  position: relative;
  aspect-ratio: 1 / 1;
  border: 1px solid var(--border);
  border-radius: 2px;
  overflow: hidden;
  cursor: pointer;
  padding: 0;
  background: transparent;
  transition: border-color var(--dur) var(--ease),
              transform var(--dur) var(--ease),
              box-shadow var(--dur) var(--ease);
}}
.ex:hover {{
  border-color: var(--accent-line);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px -8px var(--accent-soft);
}}
.ex.sel {{
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent), 0 0 0 4px var(--accent-soft);
}}
.swatch {{
  position: absolute; inset: 0;
  background: linear-gradient(135deg, var(--c1), var(--c2));
  transition: transform 680ms var(--ease);
}}
.ex:hover .swatch {{ transform: scale(1.06); }}
.pip {{
  position: absolute; top: 5px; right: 5px;
  width: 5px; height: 5px; border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(0,0,0,0.25);
}}
.pip[data-kind='authentic'] {{ background: var(--authentic); }}
.pip[data-kind='fake']      {{ background: var(--fake); }}
.pip[data-kind='tampered']  {{ background: var(--tampered); }}
.tag {{
  position: absolute; left: 5px; bottom: 4px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 8.5px; font-weight: 500;
  letter-spacing: 0.05em;
  color: rgba(236,239,244,0.92);
  text-shadow: 0 1px 2px rgba(0,0,0,0.4);
  line-height: 1;
  white-space: nowrap;
}}
</style></head>
<body>
<div class='grid'>{tiles_html}</div>
<script>
(function(){{
  // Click → navigate parent to ?example=<full label>.
  document.querySelectorAll('.ex').forEach(function(btn){{
    btn.addEventListener('click', function(){{
      var full = btn.getAttribute('data-full');
      // Optimistic UI: mark this tile as selected immediately so the
      // user sees feedback before the page reload kicks in.
      document.querySelectorAll('.ex.sel').forEach(function(s){{ s.classList.remove('sel'); }});
      btn.classList.add('sel');
      try {{
        var P = window.parent;
        var url = new URL(P.location.href);
        url.searchParams.set('example', full);
        // ``assign`` is a hard navigation; ``href =`` can occasionally
        // be intercepted by SPA history hooks. Use assign for reliability.
        P.location.assign(url.toString());
      }} catch(e) {{
        // Fallback: try iframe-local navigation, then a same-window
        // form post — better than silently doing nothing.
        try {{ window.top.location.assign('?example=' + encodeURIComponent(full)); }} catch(_) {{}}
      }}
    }});
  }});
}})();
</script>
</body></html>"""


def example_tile_grid(items: list[tuple[str, str]]) -> str:
    """Decorative 3-column tile grid for the sidebar.

    ``items`` is a list of ``(palette_key, display_label)`` pairs. Each tile
    renders as a 1:1 swatch with a kind-coded pip in the top-right corner
    and a mono filename label in the bottom-left.
    """
    tiles = []
    for key, label in items:
        c1, c2, kind = _TILE_PALETTES.get(key, ("#3A4858", "#1A222C", "authentic"))
        pip_color = _KIND_DOT[kind]
        tiles.append(
            f"<div style='position:relative;aspect-ratio:1;border-radius:2px;"
            f"overflow:hidden;border:1px solid {BORDER};"
            f"background:linear-gradient(135deg, {c1}, {c2});'>"
            f"  <div style='position:absolute;top:5px;right:5px;width:5px;height:5px;"
            f"       border-radius:50%;background:{pip_color};'></div>"
            f"  <div class='ap-mono' style='position:absolute;left:5px;bottom:4px;"
            f"       font-size:8.5px;color:rgba(236,239,244,0.85);"
            f"       letter-spacing:0.05em;text-transform:uppercase;'>"
            f"    {_html_lib.escape(label)}"
            f"  </div>"
            f"</div>"
        )
    return (
        f"<div style='display:grid;grid-template-columns:repeat(3,1fr);"
        f"gap:6px;margin:0 0 8px;'>"
        f"{''.join(tiles)}"
        f"</div>"
    )


def sidebar_foot(version: str = "v1.0", build: str = "0a3f") -> str:
    return (
        f"<div style='margin-top:18px;padding-top:14px;border-top:1px solid var(--border);"
        f"display:flex;align-items:center;gap:10px;"
        f"font-family:JetBrains Mono,monospace;font-size:10px;"
        f"color:var(--text-faint);letter-spacing:0.04em;'>"
        f"  <span>{_html_lib.escape(version)}</span>"
        f"  <a href='#' style='color:var(--text-faint);text-decoration:none;'>github</a>"
        f"  <a href='#' style='color:var(--text-faint);text-decoration:none;'>about</a>"
        f"  <span style='margin-left:auto;display:inline-flex;gap:6px;align-items:center;'>"
        f"    <span class='ap-sb-foot-blip'></span>"
        f"    build {_html_lib.escape(build)}"
        f"  </span>"
        f"</div>"
    )


# --------------------------------------------------------------------------
# Anomaly flag chip
# --------------------------------------------------------------------------

def anomaly_flag(severity: str, message: str, category: Optional[str] = None) -> str:
    """Severity-coded chip for one metadata anomaly."""
    sev = (severity or "low").lower()
    color = {"high": FAKE, "medium": SUSPICIOUS, "low": AUTHENTIC}.get(sev, TEXT_MUTED)
    cat_html = (
        f"<span style='color:{TEXT_FAINT};margin-right:8px;font-size:9.5px;'>"
        f"  · {_html_lib.escape(category)}</span>"
        if category else ""
    )
    return (
        f"<span class='ap-flag' style='border-left:2px solid {color};'>"
        f"  <span class='sev' style='color:{color};'>{sev}</span>"
        f"  <span style='color:{TEXT_DIM};'>{_html_lib.escape(message)}</span>"
        f"  {cat_html}"
        f"</span>"
    )
