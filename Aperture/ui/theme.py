"""Aperture — design-system loader for the Streamlit app.

Single source of truth for color/typography/motion tokens lives in
``Aperture/ui/tokens.css`` (extracted from the design handoff).
This module:

1. Re-exports the design's color palette as Python constants for use in
   Python rendering code (SVG generators, Plotly templates, etc.).
2. Defines component-level CSS that restyles Streamlit's native widgets
   using only ``var(--...)`` from ``tokens.css`` — no Python f-string
   interpolation.
3. Exposes ``inject_design_system()`` which loads ``tokens.css`` from
   disk, concatenates the component CSS, and emits a single ``<style>``
   block via ``st.markdown``.

``inject_custom_css`` is kept as a back-compat alias for older callsites.

What we deliberately DON'T do (Streamlit constraints, see
``UI_LIMITATIONS.md`` after Step 5):
- Replace native widgets (file_uploader, slider, selectbox) with custom
  HTML. We restyle them.
- Recreate the design's DOM. We target ``[data-testid]`` selectors only.
- Apply ``!important`` everywhere. Use it surgically on BaseWeb internals.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

# ============================================================
# Python constants — mirror the values in tokens.css so Python
# rendering code (SVG, Plotly) can use them without parsing CSS.
# Keep these in sync if you ever edit tokens.css.
# ============================================================

# Surfaces
BG = "#F4F2EC"
SURFACE_1 = "#FFFFFF"
SURFACE_2 = "#F8F6F0"
SURFACE_3 = "#ECE9E0"
BORDER = "#DEDACE"
BORDER_STRONG = "#C9C4B6"
BORDER_SOFT = "#ECE9E0"

# Text
TEXT = "#14181F"
TEXT_DIM = "#3D4654"
TEXT_MUTED = "#6C7585"
TEXT_FAINT = "#99A0AC"

# Accent
ACCENT = "#2F6FB1"
ACCENT_DIM = "#1F4F84"

# Verdict trio
AUTHENTIC = "#3F8A66"
SUSPICIOUS = "#B58527"
FAKE = "#B5462B"

# Back-compat aliases — older callsites import these names
PRIMARY = ACCENT
BG_CARD = SURFACE_1
GOOD = AUTHENTIC
WARN = SUSPICIOUS
BAD = FAKE


# ============================================================
# Plotly chart theme — applied via ``pio.templates["aperture"] = ...``
# ============================================================

PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": BG,
        "plot_bgcolor": SURFACE_1,
        "font": {
            "family": "Inter, -apple-system, sans-serif",
            "color": TEXT_DIM,
            "size": 12,
        },
        "title": {
            "font": {"family": "Source Serif 4, Georgia, serif",
                     "size": 15, "color": TEXT},
            "x": 0.02, "xanchor": "left",
        },
        "xaxis": {
            "gridcolor": BORDER,
            "linecolor": BORDER_STRONG,
            "tickfont": {"family": "JetBrains Mono, monospace",
                         "size": 10, "color": TEXT_FAINT},
            "title": {"font": {"size": 11, "color": TEXT_MUTED}},
            "zerolinecolor": BORDER_STRONG,
        },
        "yaxis": {
            "gridcolor": BORDER,
            "linecolor": BORDER_STRONG,
            "tickfont": {"family": "JetBrains Mono, monospace",
                         "size": 10, "color": TEXT_FAINT},
            "title": {"font": {"size": 11, "color": TEXT_MUTED}},
            "zerolinecolor": BORDER_STRONG,
        },
        "colorway": [ACCENT, AUTHENTIC, SUSPICIOUS, FAKE, "#8AB6D6", "#A98FCB"],
        "margin": {"l": 56, "r": 24, "t": 32, "b": 48},
    },
}


# ============================================================
# Component CSS — Streamlit widget overrides + .ap-* recipes.
# Uses var(--token) exclusively; no Python interpolation here.
# ``!important`` is used only on selectors that compete with
# Streamlit / BaseWeb internals.
# ============================================================

_COMPONENT_CSS = """
/* Google Fonts — load the three families used by the design. */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,500;0,8..60,600;0,8..60,700;1,8..60,500&display=swap');

/* ----- Global type ----- */
html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stText, .stCaption {
    font-family: var(--font-ui) !important;
    color: var(--text);
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
    font-feature-settings: "ss01", "cv11";
}
h1, h2, h3, h4, h5, h6, .ap-serif {
    font-family: var(--font-display) !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
    color: var(--text);
}
.mono, code, pre, kbd { font-family: var(--font-mono) !important; }

/* App body — radial accent floor + theme-aware bg */
[data-testid="stAppViewContainer"] {
    background:
        var(--bg-radial),
        var(--bg);
    transition: background-color var(--dur-theme) var(--ease);
}

/* ----- Sidebar ----- */
[data-testid="stSidebar"] {
    background-color: var(--surface-1);
    border-right: 1px solid var(--border);
    padding-top: 0.5rem;
}
[data-testid="stSidebar"] hr {
    border-color: var(--border);
    margin: 0.75rem 0;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    margin-bottom: 0.25rem;
    color: var(--text-dim);
}

/* ----- Streamlit metric chips → forensic metric tile ----- */
[data-testid="stMetric"] {
    background-color: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: var(--r-3);
    padding: 16px 20px;
}
[data-testid="stMetricValue"] {
    font-family: var(--font-display) !important;
    font-size: 1.7rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
    color: var(--text);
    font-feature-settings: "tnum";
}
[data-testid="stMetricLabel"] {
    color: var(--text-faint) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.62rem !important;
    text-transform: uppercase;
    letter-spacing: 0.14em;
}

/* ----- Tabs ----- */
[data-baseweb="tab-list"] {
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
    padding: 0 8px !important;
}
button[data-baseweb="tab"] {
    background-color: transparent !important;
    color: var(--text-faint) !important;
    font-family: var(--font-ui) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase;
    padding: 12px 14px !important;
    margin-right: 4px !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
}
button[data-baseweb="tab"]:hover { color: var(--text-dim) !important; }
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--text) !important;
    border-bottom: 1.5px solid var(--accent) !important;
    position: relative;
}
button[data-baseweb="tab"][aria-selected="true"]::after {
    content: "";
    position: absolute;
    left: 14px; right: 14px; bottom: -1.5px;
    height: 1.5px;
    background: var(--accent);
    transform-origin: center;
    animation: ap-tab-slide var(--dur-base) var(--ease) both;
}
.ap-tabchip {
    font-family: var(--font-mono);
    font-size: 9.5px;
    letter-spacing: 0.02em;
    background: var(--surface-2);
    color: var(--text-muted);
    padding: 2px 6px;
    border-radius: var(--r-2);
    margin-left: 8px;
}
.ap-tabchip.active { background: var(--accent-soft); color: var(--accent); }

/* ----- Expanders ----- */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--r-3) !important;
    background-color: var(--surface-1);
}
[data-testid="stExpander"] summary {
    font-family: var(--font-display) !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: var(--text);
}

/* ----- Buttons (default — surgical overrides only) ----- */
.stButton > button {
    border-radius: var(--r-2);
    border: 1px solid var(--border-strong);
    background-color: var(--surface-1);
    color: var(--text);
    font-family: var(--font-ui);
    font-size: 11.5px;
    font-weight: 500;
    letter-spacing: 0.04em;
    padding: 8px 14px;
    transition: border-color var(--dur-base) var(--ease),
                background var(--dur-base) var(--ease),
                transform var(--dur-fast) var(--ease),
                box-shadow var(--dur-base) var(--ease);
}
.stButton > button:hover {
    border-color: var(--accent-line);
    background-color: var(--surface-2);
    color: var(--text);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px -6px var(--accent-glow);
}
.stButton > button:active {
    transform: translateY(0);
}

/* ----- Hero CTA row — primary "Run a sample" + secondary "Read methodology"
   Scoped via .ap-hero-cta-anchor marker.  Padding / weight / spacing match
   the design's ``.btn`` recipe verbatim.  The primary button also carries
   a synthesised ``↵`` kbd-badge as a ::after pseudo-element. ----- */
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button {
    border-radius: var(--r-2) !important;
    padding: 9px 14px !important;
    font-family: var(--font-ui) !important;
    font-size: 11.5px !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    height: auto !important;
    min-height: 0 !important;
    width: auto !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 10px !important;
    transition: border-color var(--dur-base) var(--ease),
                background var(--dur-base) var(--ease),
                transform var(--dur-fast) var(--ease),
                box-shadow var(--dur-base) var(--ease) !important;
    box-shadow: none !important;
}
/* Inner ``<p>`` Streamlit wraps the label in — strip default margin so the
   button hugs the text. */
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button p,
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button > div {
    margin: 0 !important;
    line-height: 1 !important;
}

/* Primary: solid accent, inverse text */
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button[kind='primary'] {
    background: var(--accent) !important;
    color: var(--text-inverse) !important;
    border: 1px solid var(--accent) !important;
    font-weight: 600 !important;
}
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button[kind='primary']:hover {
    background: var(--accent-bright) !important;
    border-color: var(--accent-bright) !important;
    color: var(--text-inverse) !important;
    transform: translateY(-1px);
    box-shadow: 0 8px 20px -8px var(--accent-glow) !important;
}
/* Primary kbd badge — ↵ in a bordered chip, design parity. */
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button[kind='primary']::after {
    content: "↵";
    font-family: var(--font-mono);
    font-size: 10px;
    line-height: 1;
    color: rgba(255,255,255,0.78);
    border: 1px solid rgba(255,255,255,0.22);
    background: rgba(0,0,0,0.18);
    padding: 2px 6px 3px;
    border-radius: 2px;
    margin-left: 4px;
}

/* Secondary: outline ghost button */
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button[kind='secondary'] {
    background: var(--surface-1) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
}
[data-testid='stMain'] [data-testid='element-container']:has(.ap-hero-cta-anchor)
  + [data-testid='stHorizontalBlock'] [data-testid='stButton'] button[kind='secondary']:hover {
    background: var(--surface-2) !important;
    border-color: var(--accent-line) !important;
    color: var(--text) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px -6px var(--accent-glow) !important;
}

/* ----- File uploader — restyled to design's precision-instrument input slot.
   We aggressively HIDE Streamlit's default chrome (headline, sublabel,
   BROWSE FILES button) and synthesize our own with ::before / ::after. ----- */
[data-testid="stFileUploader"] section {
    background:
        repeating-linear-gradient(135deg, transparent 0 6px, var(--border-hairline) 6px 7px),
        var(--surface-1) !important;
    border: 1px dashed var(--border-strong) !important;
    border-radius: var(--r-2) !important;
    padding: 22px 16px !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    text-align: center !important;
    min-height: 0 !important;
    transition: border-color var(--dur-base) var(--ease),
                background    var(--dur-base) var(--ease);
}
[data-testid="stFileUploader"] section:hover {
    border-color: var(--accent-line) !important;
    background:
        repeating-linear-gradient(135deg, transparent 0 6px, var(--accent-soft) 6px 7px),
        var(--surface-1) !important;
}
/* HARD-HIDE every Streamlit-native child (headline, size limit, button) */
[data-testid="stFileUploader"] section [data-testid="stFileDropzoneInstructions"] *,
[data-testid="stFileUploader"] section button {
    display: none !important;
}
[data-testid="stFileUploader"] section [data-testid="stFileDropzoneInstructions"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    padding: 0 !important;
    margin: 0 !important;
    position: relative !important;
    width: 100% !important;
}
/* Synth: upload icon + "Drop an image..." line + size hint, in order */
[data-testid="stFileUploader"] section [data-testid="stFileDropzoneInstructions"]::before {
    content: "";
    width: 38px; height: 38px;
    border: 1px solid var(--border-strong);
    border-radius: var(--r-2);
    background-color: var(--surface-1);
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 28 28' fill='none'><path d='M14 18 L14 5' stroke='%237B8593' stroke-width='1.25' stroke-linecap='round'/><path d='M8 10 L14 4 L20 10' stroke='%237B8593' stroke-width='1.25' stroke-linecap='round' stroke-linejoin='round' fill='none'/><path d='M4 18 L4 24 L24 24 L24 18' stroke='%237B8593' stroke-width='1.25' stroke-linecap='round' fill='none'/></svg>");
    background-repeat: no-repeat;
    background-position: center;
    background-size: 18px 18px;
    transition: color var(--dur-base) var(--ease), border-color var(--dur-base) var(--ease);
}
[data-testid="stFileUploader"] section [data-testid="stFileDropzoneInstructions"]::after {
    content: "Drop an image or click to browse";
    font-family: var(--font-ui);
    font-size: 12px;
    color: var(--text-dim);
    line-height: 1.4;
}
/* Size hint line — outside the instructions div, full-width */
[data-testid="stFileUploader"] section::after {
    content: "JPG · PNG · WEBP · up to 24 MB";
    display: block;
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 0.04em;
    text-align: center;
    margin-top: 4px;
}

/* ----- Selectbox / inputs ----- */
[data-baseweb="select"] > div {
    background-color: var(--bg) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--r-2) !important;
    color: var(--text-dim) !important;
    font-family: var(--font-mono) !important;
    font-size: 11.5px !important;
}

/* ----- Sliders — slim 2px track + 10px accent thumb, matches design ----- */
[data-testid="stSlider"] [role="slider"] {
    background-color: var(--accent) !important;
    box-shadow: var(--halo-accent) !important;
    width: 10px !important;
    height: 10px !important;
    transition: box-shadow var(--dur-base) var(--ease),
                transform var(--dur-fast) var(--ease) !important;
}
[data-testid="stSlider"] [role="slider"]:hover {
    transform: scale(1.15) !important;
    box-shadow: 0 0 0 6px var(--accent-soft) !important;
}
/* Kill Streamlit's value bubble above the thumb (we render our own
   value on the right of the field label). */
[data-testid="stSlider"] [role="slider"] > div,
[data-testid="stSlider"] [data-testid="stThumbValue"] {
    display: none !important;
}

/* ----- Toggle (Run scene analysis) — flip to design's layout:
   label on the LEFT, switch on the RIGHT.
   Streamlit's toggle is rendered as ``<label class="stCheckbox">…<input>…</label>``
   nested inside ``[data-testid="stCheckbox"]``. We target both possible
   wrappers to be future-proof against Streamlit's testid renames. ----- */
[data-testid="stSidebar"] label[data-baseweb="checkbox"],
[data-testid="stSidebar"] [data-testid="stToggle"] label,
[data-testid="stSidebar"] [data-testid="stCheckbox"] label {
    flex-direction: row-reverse !important;
    justify-content: space-between !important;
    align-items: center !important;
    width: 100% !important;
    gap: 12px !important;
    margin: 0 !important;
}
/* Label text — grow to push the switch to the right edge */
[data-testid="stSidebar"] label[data-baseweb="checkbox"] > div:last-child,
[data-testid="stSidebar"] [data-testid="stToggle"] label > div:last-child,
[data-testid="stSidebar"] [data-testid="stCheckbox"] label > div:last-child {
    flex: 1 !important;
    color: var(--text-dim) !important;
    font-size: 12px !important;
    text-align: left !important;
    margin: 0 !important;
}

/* ----- Hide Streamlit's sidebar collapse arrow (top-right "X").
   Safe-hide (visibility) so Tippy can still attach to its tooltip. ----- */
[data-testid="stSidebar"] button[kind="header"],
[data-testid="stSidebar"] button[data-testid="baseButton-header"],
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
    visibility: hidden !important;
    pointer-events: none !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ----- Hide Streamlit's top-right Deploy / hamburger / running badge.
   We want only the theme-toggle pill in that corner.

   IMPORTANT: do NOT use ``display:none`` on the toolbar children —
   Streamlit attaches tippy.js tooltips on these (Deploy button, main
   menu) in componentDidMount, and tippy throws ``"First argument must
   be a String, HTMLElement, HTMLCollection, or NodeList"`` if the
   anchor is detached from layout. We instead collapse the header to
   zero height and clip its children; the elements stay in the DOM so
   tippy can attach without crashing, they're just invisible and
   un-interactable. ----- */
header[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    background: transparent !important;
    overflow: hidden !important;
    pointer-events: none !important;
}
[data-testid="stDecoration"],
[data-testid="stToolbar"],
[data-testid="stDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stStatusWidget"],
button[data-testid="baseButton-header"] {
    visibility: hidden !important;
    pointer-events: none !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ----- File uploader: collapse the aria-hidden widget label that
   Streamlit renders above the dropzone (so the design's compact box
   isn't pushed down). Use visibility instead of display:none so any
   tippy tooltip target inside still has a valid DOM anchor. ----- */
[data-testid="stFileUploader"] > label[data-testid="stWidgetLabel"] {
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div {
    background: var(--border-strong) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div {
    background: var(--accent) !important;
}
[data-testid="stSlider"] [data-testid="stTickBar"],
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stSlider"] {
    margin-top: -4px !important;
}

/* ----- Code blocks ----- */
[data-testid="stCodeBlock"] {
    background-color: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-2);
}

/* ----- Top-area padding ----- */
.main .block-container,
[data-testid="stMain"] .block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    padding-bottom: 4rem;
    max-width: 1400px;
}
/* Streamlit pads the sidebar's top too — bring the brand right up. */
[data-testid="stSidebar"] [data-testid="stSidebarContent"],
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-top: 18px !important;
}
/* And kill the very first vertical-block spacer Streamlit injects. */
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

/* ============================================================
   .ap-* utility recipes (component anatomies from DESIGN_TOKENS.md)
   No !important here — these classes don't compete with Streamlit.
   ============================================================ */

.ap-divider {
    border: 0;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

.ap-section-head {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin: 0 0 18px;
}
.ap-section-head .kicker {
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-faint);
}
.ap-section-head h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.005em;
    color: var(--text);
}
.ap-section-head .rule {
    flex: 1;
    height: 1px;
    background: var(--border);
}

.ap-card {
    background-color: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: var(--r-3);
    padding: 22px 22px 18px;
}

/* Signal card — 2-col grid: 1fr | 132px viz tile; foot spans both. */
.ap-signal {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: var(--r-3);
    padding: 22px 22px 18px;
    transition: border-color var(--dur-base) var(--ease),
                transform var(--dur-base) var(--ease),
                box-shadow var(--dur-base) var(--ease);
    height: 100%;
    display: grid;
    grid-template-columns: 1fr 132px;
    gap: 20px;
    align-items: start;
    position: relative;
    overflow: hidden;
    animation: ap-reveal var(--dur-reveal) var(--ease-out) both;
}
/* Stagger sibling signal cards (column-based; one card per st.column) */
[data-testid="stColumn"]:nth-of-type(1) .ap-signal { animation-delay: 60ms; }
[data-testid="stColumn"]:nth-of-type(2) .ap-signal { animation-delay: 140ms; }
[data-testid="stColumn"]:nth-of-type(3) .ap-signal { animation-delay: 220ms; }
[data-testid="stColumn"]:nth-of-type(4) .ap-signal { animation-delay: 300ms; }
.ap-signal::before {
    content: "";
    position: absolute; top: 0; left: 0; width: 2px; height: 100%;
    background: var(--accent);
    opacity: 0;
    transition: opacity var(--dur-base) var(--ease);
}
.ap-signal:hover {
    border-color: var(--border-strong);
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
}
.ap-signal:hover::before { opacity: 1; }
.ap-signal .viz {
    background: var(--surface-2);
    border: 1px solid var(--border);
    aspect-ratio: 1;
    position: relative;
    overflow: hidden;
    display: block;
}
.ap-signal .head {
    display: flex; align-items: center; gap: 10px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 12px;
}
.ap-signal .head .dot {
    width: 7px; height: 7px; border-radius: 50%;
}
.ap-signal .big {
    font-family: var(--font-display);
    font-size: 36px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.02em;
    margin: 0 0 8px;
    font-feature-settings: "tnum";
    line-height: 1;
}
.ap-signal .big .unit {
    font-size: 14px;
    color: var(--text-muted);
    margin-left: 4px;
    font-family: var(--font-mono);
    font-weight: 400;
}
.ap-signal .summary {
    font-size: 12.5px;
    color: var(--text-dim);
    line-height: 1.5;
}
.ap-signal .foot {
    grid-column: 1 / -1;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 9.5px;
    color: var(--text-faint);
    letter-spacing: 0.06em;
}

/* Verdict block */
.ap-verdict-block {
    border: 1px solid var(--border);
    background: var(--surface-1);
    padding: 36px 40px;
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 48px;
    align-items: center;
    position: relative;
    overflow: hidden;
    border-radius: var(--r-3);
}
.ap-verdict-block::before {
    content: "";
    position: absolute; right: -120px; top: -120px;
    width: 380px; height: 380px; border-radius: 50%;
    background: radial-gradient(circle, var(--verdict-glow, var(--suspicious-soft)) 0%, transparent 70%);
    pointer-events: none;
}
.ap-verdict-prob {
    display: flex; flex-direction: column; gap: 6px;
    position: relative; z-index: 1;
}
.ap-verdict-prob .lbl {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 0.18em;
    text-transform: uppercase;
}
.ap-verdict-prob .num {
    font-family: var(--font-display);
    font-size: 96px;
    font-weight: 600;
    line-height: 0.95;
    color: var(--verdict-color, var(--suspicious));
    letter-spacing: -0.03em;
    font-feature-settings: "tnum";
}
.ap-verdict-prob .pct {
    font-size: 28px;
    vertical-align: top;
    color: var(--text-muted);
    margin-left: 4px;
}
.ap-verdict-meta {
    display: flex; flex-direction: column; gap: 18px;
    position: relative; z-index: 1;
}
.ap-verdict-label {
    font-family: var(--font-display);
    font-size: 28px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 14px;
}
.ap-verdict-label::before {
    content: ""; width: 8px; height: 28px;
    background: var(--verdict-color, var(--suspicious));
}
.ap-verdict-summary {
    max-width: 540px;
    font-size: 13.5px;
    color: var(--text-dim);
    line-height: 1.55;
}

/* Confidence band */
.ap-confidence-bar {
    position: relative;
    height: 28px;
    display: grid;
    grid-template-columns: 30% 40% 30%;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
}
.ap-confidence-bar .zone {
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-faint);
    position: relative;
}
.ap-confidence-bar .zone.fake { background: rgba(224,122,95,0.06); }
.ap-confidence-bar .zone.susp { background: rgba(232,197,122,0.06); }
.ap-confidence-bar .zone.auth { background: rgba(127,184,154,0.06); }
.ap-confidence-bar .zone + .zone { border-left: 1px dashed var(--border); }
.ap-confidence-bar .marker {
    position: absolute; top: -10px; bottom: -10px;
    width: 2px; background: var(--verdict-color, var(--suspicious));
    transition: left var(--dur-slow) var(--ease);
}
.ap-confidence-bar .marker::before {
    content: ""; position: absolute; top: -4px; left: -3px;
    width: 8px; height: 8px; transform: rotate(45deg);
    background: var(--verdict-color, var(--suspicious));
}
.ap-confidence-bar .scale {
    position: absolute; left: 0; right: 0; bottom: -22px;
    display: flex; justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 9.5px;
    color: var(--text-faint);
}

/* Factor row */
.ap-factor {
    display: grid;
    grid-template-columns: 140px 1fr 90px;
    gap: 16px;
    align-items: center;
    padding: 12px 16px;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-bottom: 0;
}
.ap-factor:last-child { border-bottom: 1px solid var(--border); }
.ap-factor .name {
    font-family: var(--font-mono);
    font-size: 10.5px;
    color: var(--text-dim);
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.ap-factor .bar-wrap {
    position: relative; height: 8px;
    background: var(--surface-2);
}
.ap-factor .bar {
    position: absolute; top: 0; bottom: 0;
    background: var(--factor-color, var(--accent));
}
.ap-factor .bar-wrap .axis {
    position: absolute; top: -2px; bottom: -2px; left: 50%;
    width: 1px; background: var(--border-strong);
}
.ap-factor .expl {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 6px;
    line-height: 1.45;
}
.ap-factor .delta {
    font-family: var(--font-mono);
    font-size: 13px;
    text-align: right;
    color: var(--factor-color, var(--text-dim));
    font-feature-settings: "tnum";
}

/* Meter (back-compat) */
.ap-meter-track {
    background-color: var(--surface-2);
    border-radius: var(--r-pill);
    height: 6px;
    overflow: hidden;
}
.ap-meter-fill {
    height: 100%;
    background-color: var(--accent);
    border-radius: var(--r-pill);
}

/* Anomaly flag chip */
.ap-flag {
    display: inline-block;
    padding: 4px 10px;
    border-radius: var(--r-2);
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 500;
    letter-spacing: 0.04em;
    margin-right: 6px;
    margin-bottom: 6px;
    background: var(--surface-1);
    border: 1px solid var(--border);
}
.ap-flag .sev {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 9.5px;
    margin-right: 8px;
}

/* Dim card */
.ap-dim {
    background: var(--surface-1);
    border: 1px solid var(--border);
    padding: 22px 20px 20px;
    display: flex; flex-direction: column; gap: 12px;
    min-height: 200px;
    transition: border-color var(--dur-base) var(--ease),
                background var(--dur-base) var(--ease),
                transform var(--dur-base) var(--ease),
                box-shadow var(--dur-base) var(--ease);
    border-radius: var(--r-3);
    position: relative;
    overflow: hidden;
}
.ap-dim::before {
    content: "";
    position: absolute; left: 0; right: 0; top: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-line), transparent);
    opacity: 0; transition: opacity var(--dur-base) var(--ease);
}
.ap-dim:hover {
    border-color: var(--border-strong);
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
}
.ap-dim:hover::before { opacity: 1; }
.ap-dim .icon { transition: transform var(--dur-base) var(--ease); }
.ap-dim:hover .icon { transform: scale(1.06); }
.ap-dim .num {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 0.08em;
}
.ap-dim .icon {
    width: 44px; height: 44px;
    display: grid; place-items: center;
    color: var(--accent);
}
.ap-dim h3 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 17px;
    font-weight: 600;
    color: var(--text);
}
.ap-dim p {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.55;
    color: var(--text-muted);
}
.ap-dim .foot {
    margin-top: auto;
    font-family: var(--font-mono);
    font-size: 9.5px;
    color: var(--text-faint);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* Image-chip header */
.ap-imgchip {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    padding: 6px 12px 6px 6px;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: var(--r-3);
}

/* Honest-note callout */
.ap-honest {
    padding: 14px 16px;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-left: 2px solid var(--suspicious);
    font-size: 12.5px;
    color: var(--text-dim);
    line-height: 1.55;
    border-radius: 0 var(--r-2) var(--r-2) 0;
}
.ap-honest .tag {
    font-family: var(--font-mono);
    color: var(--suspicious);
    font-size: 10px;
    letter-spacing: 0.14em;
    margin-right: 10px;
    text-transform: uppercase;
}

/* Hero */
.ap-hero {
    display: flex; flex-direction: column; gap: 20px;
    margin: 16px 0 56px;
    position: relative;
}
.ap-hero .eyebrow {
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--accent);
    display: inline-flex;
    align-items: center;
    gap: 10px;
}
.ap-hero .eyebrow .bar {
    width: 24px; height: 1px; background: var(--accent);
}
.ap-hero .eyebrow .blip {
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--authentic);
    box-shadow: 0 0 0 3px var(--authentic-soft);
    animation: ap-live-blip 2.4s var(--ease) infinite;
}
.ap-hero h1 {
    font-family: var(--font-display);
    font-size: 60px;
    font-weight: 600;
    line-height: 1.04;
    letter-spacing: -0.022em;
    margin: 0;
    color: var(--text);
    max-width: 760px;
}
.ap-hero h1 em {
    font-style: italic;
    font-weight: 500;
    color: var(--accent);
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dim) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.ap-hero .lede {
    max-width: 620px;
    font-size: 14.5px;
    line-height: 1.6;
    color: var(--text-dim);
}

/* ----- Topbar — full-viewport bleed, sticky, with breadcrumb + session ----- */
/* The bottom rule must span beyond the .block-container's max-width:
   calc(-1 * (100vw - 100%) / 2) pulls the topbar's outer edges to the
   viewport edges; equal positive padding keeps the inner content
   indented at the design's 40 px gutter. Backdrop-blur lifts the sticky
   bar above the radial background. */
.ap-topbar {
    position: sticky;
    top: 0;
    z-index: 5;
    margin-left: calc(-1 * (100vw - 100%) / 2);
    margin-right: calc(-1 * (100vw - 100%) / 2);
    margin-top: 0;
    margin-bottom: 24px;
    padding: 12px calc(((100vw - 100%) / 2) + 40px);
    background: color-mix(in srgb, var(--bg) 92%, transparent);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 24px;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
    transition: background var(--dur-theme) var(--ease),
                border-color var(--dur-theme) var(--ease);
}
.ap-topbar .crumb {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-faint);
}
.ap-topbar .crumb .sep { color: var(--border-strong); }
.ap-topbar .crumb .cur { color: var(--text-dim); }
.ap-topbar .grow { flex: 1; }
.ap-topbar .session {
    display: inline-flex;
    gap: 14px;
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
}
.ap-topbar .session b {
    color: var(--text-dim);
    font-weight: 500;
}

/* Tagline (small italic on welcome) */
.ap-tagline {
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: 9.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding-left: 19px;
}

/* Iris-stage labels (analyzing screen) */
.iris-label {
    display: flex; align-items: center; gap: 10px;
    font-family: var(--font-mono); font-size: 11px;
    color: var(--text-muted); letter-spacing: 0.02em;
    transition: color var(--dur-base) var(--ease);
    padding: 4px 0;
}
.iris-label .ind {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--border-strong); transition: all var(--dur-base) var(--ease);
}
.iris-label.running .ind {
    background: var(--suspicious);
    box-shadow: 0 0 0 3px var(--suspicious-soft);
    animation: ap-run-pulse 1.4s var(--ease) infinite;
}
.iris-label.done .ind {
    background: var(--authentic);
    box-shadow: var(--halo-authentic);
}
.iris-label.done { color: var(--text-dim); }

/* Iris stage — ambient breath halo behind the SVG */
.ap-iris-stage {
    display: grid; place-items: center;
    padding: 32px 0 24px;
    position: relative;
}
.ap-iris-stage::before {
    content: "";
    position: absolute;
    width: 260px; height: 260px;
    border-radius: 50%;
    background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
    opacity: 0.5;
    animation: ap-iris-breath 6s var(--ease) infinite;
    pointer-events: none;
}

/* Log block — fade-out gradient at bottom for the rolling status feed */
.ap-log {
    background: var(--surface-1);
    border: 1px solid var(--border);
    padding: 14px 16px;
    font-family: var(--font-mono); font-size: 11px;
    color: var(--text-muted);
    display: flex; flex-direction: column; gap: 6px;
    max-height: 200px; overflow: hidden;
    position: relative;
    border-radius: var(--r-2);
}
.ap-log::after {
    content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 36px;
    background: linear-gradient(180deg, transparent, var(--surface-1));
    pointer-events: none;
}
.ap-log .log-line {
    white-space: nowrap;
    animation: ap-reveal var(--dur-base) var(--ease-out) both;
}

/* Brand-mark radar pulse — sidebar wordmark */
.ap-brand-dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 0 4px var(--accent-soft);
    position: relative;
    display: inline-block;
}
.ap-brand-dot::after {
    content: ""; position: absolute; inset: -8px;
    border-radius: 50%;
    border: 1px solid var(--accent-line);
    animation: ap-brand-pulse 3.6s var(--ease) infinite;
}

/* Sidebar foot live-blip */
.ap-sb-foot-blip {
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--authentic);
    box-shadow: 0 0 0 3px var(--authentic-soft);
    animation: ap-live-blip 2.4s var(--ease) infinite;
    display: inline-block;
}

/* Verdict-block — animated accent rule top, soft corner glow */
.ap-verdict-block::after {
    content: "";
    position: absolute; top: 0; left: 40px; right: 40px;
    height: 1px;
    background: linear-gradient(90deg, transparent,
                                var(--verdict-color, var(--suspicious)) 50%,
                                transparent);
    opacity: 0.5;
}
.ap-verdict-block .num {
    animation: ap-reveal var(--dur-slow) var(--ease-out) both;
}

/* Confidence-bar marker — slide in from baseline */
.ap-confidence-bar .marker {
    animation: ap-marker-slide var(--dur-slow) var(--ease-out) both;
}
.ap-confidence-bar .marker::before {
    box-shadow: 0 0 12px var(--verdict-color, var(--suspicious));
}

/* Factor bar — grow-in from origin */
.ap-factor .bar {
    transform-origin: var(--bar-origin, left);
    animation: ap-bar-grow var(--dur-slow) var(--ease-out) both;
    box-shadow: 0 0 8px var(--factor-color, var(--accent));
}

/* Image-chip thumb — soft border swap on theme */
.ap-imgchip .thumb-frame {
    border: 1px solid var(--border);
}

"""


# ============================================================
# Public API
# ============================================================

_TOKENS_CSS_PATH = Path(__file__).resolve().parent / "tokens.css"


def _load_tokens_css() -> str:
    """Read tokens.css from disk. Falls back to a tiny default if missing."""
    try:
        return _TOKENS_CSS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Minimal fallback so the app still renders if the file vanishes
        return f":root {{ --bg: {BG}; --text: {TEXT}; --accent: {ACCENT}; }}"


def inject_design_system() -> None:
    """Inject the Aperture design system into the page.

    Call exactly once near the top of ``app.py``, after ``st.set_page_config``.
    Emits a single ``<style>`` block containing:
      1. The tokens (from ``tokens.css`` on disk — single source of truth)
      2. Component-level overrides for Streamlit widgets, using only the
         tokens from step 1.
    """
    tokens = _load_tokens_css()
    css = f"<style>\n{tokens}\n{_COMPONENT_CSS}\n</style>"
    st.markdown(css, unsafe_allow_html=True)


# Back-compat alias — older callsites still import this name
inject_custom_css = inject_design_system
