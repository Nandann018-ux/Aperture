"""Custom dark-theme CSS injection.

The Streamlit ``.streamlit/config.toml`` covers the base palette; this
module layers on typography (Fraunces + Inter), tighter sidebar chrome,
and styled metric / signal cards.
"""
from __future__ import annotations

import streamlit as st

PRIMARY = "#A78BFA"
BG = "#0A0A0A"
BG_CARD = "#141414"
TEXT = "#F5F5F0"
TEXT_DIM = "#9A9A9A"
BORDER = "#222222"

GOOD = "#7FB069"
WARN = "#F4B860"
BAD = "#E07A5F"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stText {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: {TEXT};
}}

h1, h2, h3, .ap-serif {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 500 !important;
    letter-spacing: -0.01em;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {BG};
    border-right: 1px solid {BORDER};
    padding-top: 0.5rem;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    margin-bottom: 0.25rem;
}}
[data-testid="stSidebar"] hr {{
    border-color: {BORDER};
    margin: 0.75rem 0;
}}

/* Metric chips */
[data-testid="stMetric"] {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1rem 1.25rem;
}}
[data-testid="stMetricValue"] {{
    font-family: 'Fraunces', serif !important;
    font-size: 2rem !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_DIM} !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* Tabs */
button[data-baseweb="tab"] {{
    background-color: transparent !important;
    color: {TEXT_DIM} !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {TEXT} !important;
    border-bottom-color: {PRIMARY} !important;
}}

/* Expanders */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    background-color: {BG_CARD};
}}
[data-testid="stExpander"] summary {{
    font-family: 'Fraunces', serif !important;
    font-size: 1rem !important;
}}

/* Buttons */
.stButton > button {{
    border-radius: 999px;
    border: 1px solid {BORDER};
    background-color: {BG_CARD};
    color: {TEXT};
    padding: 0.4rem 1rem;
    transition: border-color 120ms ease, transform 120ms ease;
}}
.stButton > button:hover {{
    border-color: {PRIMARY};
    color: {TEXT};
    transform: translateY(-1px);
}}

/* Custom card classes (used by components.py) */
.ap-card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1rem 1.25rem;
    height: 100%;
}}
.ap-card-accent-good   {{ border-left: 3px solid {GOOD}; }}
.ap-card-accent-warn   {{ border-left: 3px solid {WARN}; }}
.ap-card-accent-bad    {{ border-left: 3px solid {BAD}; }}
.ap-card-accent-neutral{{ border-left: 3px solid {TEXT_DIM}; }}

.ap-card .ap-card-icon {{
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}}
.ap-card .ap-card-title {{
    font-family: 'Fraunces', serif;
    font-size: 1.05rem;
    color: {TEXT};
    margin-bottom: 0.4rem;
}}
.ap-card .ap-card-score {{
    font-family: 'Fraunces', serif;
    font-size: 1.9rem;
    color: {TEXT};
    line-height: 1.1;
}}
.ap-card .ap-card-status {{
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.35rem;
    color: {TEXT_DIM};
}}

.ap-flag {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    margin-right: 0.4rem;
    margin-bottom: 0.4rem;
    color: #111;
}}

.ap-verdict-banner {{
    font-family: 'Fraunces', serif;
    font-size: 3.5rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-align: center;
    margin: 0.5rem 0;
}}

.ap-tagline {{
    color: {TEXT_DIM};
    font-style: italic;
    font-size: 0.85rem;
}}

.ap-eyebrow {{
    color: {TEXT_DIM};
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

.ap-meter-track {{
    background-color: {BORDER};
    border-radius: 999px;
    height: 6px;
    overflow: hidden;
}}
.ap-meter-fill {{
    height: 100%;
    background-color: {PRIMARY};
    border-radius: 999px;
}}

.ap-divider {{
    border: 0;
    border-top: 1px solid {BORDER};
    margin: 1.25rem 0;
}}

/* Tighter top padding on main area */
.main .block-container {{
    padding-top: 2rem;
    padding-bottom: 4rem;
}}
</style>
"""


def inject_custom_css() -> None:
    """Call exactly once near the top of app.py, after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)
