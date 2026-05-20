"""Aperture — Streamlit entry point.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(
    page_title="Aperture — Image Forensic Analysis",
    layout="wide",
    page_icon="◉",
    initial_sidebar_state="expanded",
)

from Aperture.ui.components import (
    TILE_DROPDOWN_MAP, dim_card, divider_or, example_tile_button_css,
    example_tile_grid, example_tile_grid_iframe, html, image_chip,
    iris_labels_html, iris_stage_html, log_block_html, pipeline_diagram_doc,
    section_eyebrow, section_head, sidebar_foot, sidebar_section_head,
    topbar,
)
from Aperture.ui.tabs import (
    render_ai_tab,
    render_metadata_tab,
    render_performance_tab,
    render_scene_tab,
    render_tampering_tab,
    render_verdict_tab,
)
from Aperture.ui.theme import (
    ACCENT, BORDER, BG_CARD, PRIMARY, TEXT, TEXT_DIM, TEXT_FAINT, TEXT_MUTED,
    inject_design_system,
)

inject_design_system()

# ----- Page-load splash --------------------------------------------------
# Brand splash that fades over the page on first mount (and on every
# fresh reload). Avoids the "is the app dead?" perception while
# Streamlit's bundle and our CSS finish wiring up. Implemented as
# CSS-only — auto-fades after 900ms, then auto-hides via animation.
# We always render it (not session-state-gated) so reloads also show it;
# users mid-session don't see it again because reruns reuse the same
# DOM (the .ap-splash element animates once and then stays hidden).
st.markdown(
    """
    <div class="ap-splash" aria-hidden="true">
      <div class="ap-splash-inner">
        <span class="ap-splash-mark"></span>
        <div class="ap-splash-text">
          <span class="ap-splash-name">Aperture</span>
          <span class="ap-splash-sub">initializing forensic pipelines…</span>
        </div>
        <div class="ap-splash-bar"><div class="ap-splash-bar-fill"></div></div>
      </div>
    </div>
    <style>
    .ap-splash {
      position: fixed; inset: 0; z-index: 9998;
      background: var(--bg);
      display: grid; place-items: center;
      animation: ap-splash-out 600ms var(--ease-out) 900ms both;
    }
    @keyframes ap-splash-out {
      to { opacity: 0; visibility: hidden; pointer-events: none; }
    }
    .ap-splash-inner {
      display: flex; flex-direction: column; align-items: center; gap: 18px;
    }
    .ap-splash-mark {
      width: 18px; height: 18px; border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 0 6px var(--accent-soft),
                  0 0 0 14px color-mix(in srgb, var(--accent) 6%, transparent);
      animation: ap-splash-pulse 1.6s var(--ease) infinite;
    }
    @keyframes ap-splash-pulse {
      0%, 100% { transform: scale(1);    opacity: 1;   }
      50%      { transform: scale(0.86); opacity: 0.7; }
    }
    .ap-splash-text {
      display: flex; flex-direction: column; align-items: center; gap: 4px;
    }
    .ap-splash-name {
      font-family: var(--font-display);
      font-size: 22px; font-weight: 600; color: var(--text);
      letter-spacing: -0.005em;
    }
    .ap-splash-sub {
      font-family: var(--font-mono);
      font-size: 10.5px; letter-spacing: 0.18em; text-transform: uppercase;
      color: var(--text-faint);
    }
    .ap-splash-bar {
      width: 180px; height: 1px; background: var(--border);
      overflow: hidden; border-radius: 1px;
    }
    .ap-splash-bar-fill {
      width: 30%; height: 100%; background: var(--accent);
      animation: ap-splash-bar 1.4s var(--ease) infinite;
    }
    @keyframes ap-splash-bar {
      0%   { transform: translateX(-100%); }
      100% { transform: translateX(380%);  }
    }
    @media (prefers-reduced-motion: reduce) {
      .ap-splash { animation: ap-splash-out 200ms ease 100ms both; }
      .ap-splash-mark, .ap-splash-bar-fill { animation: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

EXAMPLES_DIR = Path("examples")
MODELS_DIR = Path("models")
AI_CHECKPOINT = MODELS_DIR / "ai_detector_best.pt"
META_CHECKPOINT = MODELS_DIR / "meta_classifier.pkl"

# GitHub Release asset URL for ai_detector_best.pt. The repo's first
# tagged release should publish ai_detector_best.pt as a release asset
# at this exact path. If the release does not yet exist, the AI
# Detection tab will surface a friendly "checkpoint unavailable"
# message in load_weights_if_missing(...) below.
#
# ACTION REQUIRED before deploy: create a GitHub Release at the URL
# below (or update this constant to point at the actual asset URL).
AI_DETECTOR_WEIGHTS_URL = (
    "https://github.com/Nandann018-ux/Aperture/releases/download/"
    "v0.1.0/ai_detector_best.pt"
)

EXAMPLE_FILES = [
    ("Authentic landscape", "authentic_landscape.jpg"),
    ("Authentic portrait", "authentic_portrait.jpg"),
    ("Tampered composite", "tampered_composite.jpg"),
    ("Copy-move", "copy_move_obvious.jpg"),
    ("AI — Midjourney-style", "ai_midjourney.jpg"),
    ("AI — realistic", "ai_realistic.jpg"),
    ("Metadata: Photoshop edit", "photoshopped_photo.jpg"),
    ("Metadata: date drift", "date_drift_photo.jpg"),
    ("Metadata: low JPEG quality", "low_quality_jpeg.jpg"),
    ("Metadata: AI-tool signature", "ai_generated_metadata.jpg"),
]


# --------------------------------------------------------------------------
# Meta-classifier bootstrap
# --------------------------------------------------------------------------
# The pickle isn't checked into git for the deployed build — it must be
# rebuilt against the runtime's numpy / sklearn so old-version pickles
# don't crash on unpickle (numpy 1.26-saved arrays won't load under
# numpy 2.x). Training is ~2 s against the bundled CSV. Cached so we
# train at most once per container lifecycle.

@st.cache_resource(show_spinner=False)
def _ensure_meta_classifier() -> bool:
    if META_CHECKPOINT.exists():
        return True
    csv_path = Path("data") / "meta_classifier_training.csv"
    if not csv_path.exists():
        return False
    try:
        with st.spinner("Calibrating meta-classifier — first run only…"):
            from Aperture.verdict.meta_classifier import train_and_save
            train_and_save(csv_path, META_CHECKPOINT, Path("eval_results"))
        return True
    except Exception as exc:  # noqa: BLE001
        st.warning(
            f"Could not train meta-classifier: {type(exc).__name__}: {exc}"
        )
        return False


_ensure_meta_classifier()


# --------------------------------------------------------------------------
# Cached model loaders + analyses
# --------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _load_object_detector():
    from Aperture.scene import get_object_detector
    return get_object_detector()


@st.cache_resource(show_spinner=False)
def _load_clip_classifier():
    from Aperture.scene import get_clip_classifier
    return get_clip_classifier()


@st.cache_resource(show_spinner=False)
def _load_text_extractor():
    from Aperture.scene import get_text_extractor
    return get_text_extractor()


@st.cache_resource(show_spinner=False)
def load_weights_if_missing(url: str, dest_str: str) -> bool:
    """Download AI detector weights from a GitHub Release if not already on disk.

    Returns True iff the weights file is present after this call. Cached via
    ``st.cache_resource`` so we attempt the download at most once per container
    lifecycle; the cache key includes both ``url`` and ``dest_str`` so swapping
    the release URL invalidates and re-fetches.
    """
    import urllib.request

    dest = Path(dest_str)
    if dest.exists():
        return True
    if not url:
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with st.spinner(f"Downloading AI detector weights ({dest.name}) — first run only…"):
            req = urllib.request.Request(url, headers={"User-Agent": "aperture-app"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 20)  # 1 MiB
                    if not chunk:
                        break
                    fh.write(chunk)
        tmp.replace(dest)
        return True
    except Exception as exc:  # noqa: BLE001 — surface any download failure to the UI
        tmp.unlink(missing_ok=True)
        st.warning(
            f"Could not fetch AI detector weights from {url}: "
            f"{type(exc).__name__}: {exc}"
        )
        return False


@st.cache_resource(show_spinner=False)
def _load_ai_detector(path: str):
    from Aperture.ai_detector.infer import AIDetector
    return AIDetector(path)


# `bytes` is hashable by Streamlit's cache_data; key analyses by image content.

@st.cache_data(show_spinner=False)
def _run_tampering(image_bytes: bytes) -> dict:
    from Aperture.tampering.combine import compute_tampering_verdict
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return compute_tampering_verdict(img)


@st.cache_data(show_spinner=False)
def _run_metadata(image_bytes: bytes) -> dict:
    from Aperture.metadata import analyze_metadata
    img = Image.open(io.BytesIO(image_bytes))
    return analyze_metadata(img, file_bytes=image_bytes)


@st.cache_data(show_spinner=False)
def _run_scene(image_bytes: bytes) -> dict:
    """Object detection + CLIP + OCR. Heavy first call; cached thereafter."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    objects = _load_object_detector().detect(img)
    clip = _load_clip_classifier().classify(img)
    ocr = _load_text_extractor().extract(img)
    return {"objects": objects, "scene": clip, "ocr": ocr}


@st.cache_data(show_spinner=False)
def _run_ai_detector(image_bytes: bytes, checkpoint_path: str) -> dict:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    det = _load_ai_detector(checkpoint_path)
    result = det.predict_with_explanation(img)
    fake_idx = 1
    p_fake = float(result["raw_logits"][fake_idx]) if "raw_logits" in result else 0.0
    # Convert label/confidence into a clean P(fake)
    if result["label"] == "fake":
        p_fake = float(result["confidence"])
    else:
        p_fake = 1.0 - float(result["confidence"])
    return {
        "status": "ok",
        "label": result["label"],
        "confidence": result["confidence"],
        "ai_probability": p_fake,
        "heatmap": result["heatmap"],
        "overlay": result["overlay"],
    }


def _run_verdict(features: dict) -> Optional[dict]:
    if not META_CHECKPOINT.exists():
        return None
    from Aperture.verdict import compute_verdict
    return compute_verdict(features, model_path=META_CHECKPOINT)


def _safe(fn, *args, **kwargs):
    """Run an analysis, return (result, error_str)."""
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

with st.sidebar:
    # Brand — wordmark + radar-pulse accent dot
    html(
        f"<div style='display:flex;align-items:center;gap:11px;"
        f"font-family:\"Source Serif 4\",serif;font-size:26px;font-weight:600;"
        f"color:var(--text);letter-spacing:0.005em;margin-bottom:2px;'>"
        f"  <span class='ap-brand-dot'></span>"
        f"  Aperture"
        f"</div>"
        f"<div class='ap-tagline'>image forensic analysis</div>"
    )

    # ANALYZE section
    html(sidebar_section_head("Analyze"))
    # NOTE: do NOT pass help="…" here. Streamlit would render a tippy.js
    # tooltip target inside the widget label, but our CSS hides that label
    # (so the design's compact dropzone renders cleanly). Tippy then crashes
    # on mount with "First argument must be a String, HTMLElement, …".
    uploaded = st.file_uploader(
        "Drop an image or click to browse",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

    # Clickable example tile grid — pixel-accurate clone of the design,
    # rendered as a self-contained iframe (Streamlit's button styling
    # otherwise leaks through). Tile clicks navigate the parent to
    # ``?example=<label>``; we read that back below.
    html(divider_or("or try an example"))

    # Selection state — first read the URL query param (set by the tile
    # iframe on click), then mirror into session_state.
    if "_example_dropdown" not in st.session_state:
        st.session_state["_example_dropdown"] = "(none)"

    try:
        _qp = dict(st.query_params)
        _ex_qp = _qp.get("example")
        if _ex_qp and _ex_qp != st.session_state["_example_dropdown"]:
            st.session_state["_example_dropdown"] = _ex_qp
    except Exception:
        pass

    components.html(
        example_tile_grid_iframe(st.session_state["_example_dropdown"]),
        height=190,
        scrolling=False,
    )

    # Backing selectbox — collapsed and visually hidden via CSS marker,
    # but kept in the DOM so callers can still pick examples not in the
    # 6-tile primary set if they want to extend the UI later.
    example_choice = st.session_state["_example_dropdown"]

    # SETTINGS section — labels with right-aligned values matching the design
    html(sidebar_section_head("Settings"))
    html(
        f"<div class='ap-mono' style='font-size:10px;color:{TEXT_FAINT};"
        f"letter-spacing:0.14em;text-transform:uppercase;margin-bottom:6px;'>"
        f"detector model</div>"
    )
    ai_model = st.selectbox(
        "AI detector model", ["EfficientNet-B0 (default)"],
        index=0, label_visibility="collapsed",
    )

    # Slider with value-on-right label (rendered manually; slider hidden-label)
    if "_sens" not in st.session_state:
        st.session_state["_sens"] = 0.50
    html(
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"margin:12px 0 4px;'>"
        f"  <span class='ap-mono' style='font-size:10px;color:{TEXT_FAINT};"
        f"       letter-spacing:0.14em;text-transform:uppercase;'>"
        f"    tampering sensitivity</span>"
        f"  <span class='ap-mono' style='color:{TEXT_DIM};font-size:11px;"
        f"       letter-spacing:0.02em;'>{st.session_state['_sens']:.2f}</span>"
        f"</div>"
    )
    tampering_sensitivity = st.slider(
        "Tampering sensitivity", 0.0, 1.0,
        step=0.01, key="_sens",
        label_visibility="collapsed",
    )

    # Toggle row — st.toggle gives the design's iOS-style pill switch
    run_scene_analysis = st.toggle("Run scene analysis", value=True)

    # Footer
    html(sidebar_foot("v1.0", "0a3f"))


# --------------------------------------------------------------------------
# Resolve which image to analyze
# --------------------------------------------------------------------------

def _resolve_bytes() -> tuple[Optional[bytes], Optional[str]]:
    """Pick the active image. Example-tile selection wins over a
    previously-uploaded file so clicking a tile always switches the view
    (UX intent: "show me this sample"). A real upload-then-tile flow
    would otherwise leave the uploaded file's analysis stuck on screen.
    """
    if example_choice and example_choice != "(none)":
        fname = dict(EXAMPLE_FILES).get(example_choice)
        if fname:
            path = EXAMPLES_DIR / fname
            if path.exists():
                return path.read_bytes(), fname
            st.sidebar.error(
                f"Example file missing on disk: {path.name}"
            )
    if uploaded is not None:
        data = uploaded.getvalue()
        if len(data) > 24 * 1024 * 1024:
            st.sidebar.error(
                "Image exceeds 24 MB. Please upload a smaller file."
            )
            return None, None
        return data, uploaded.name
    return None, None


image_bytes, image_name = _resolve_bytes()

# Cold-start hint is deferred until AFTER the topbar emits below, so the
# banner doesn't push the topbar away from the viewport top. We mark the
# need-to-show flag here and consume it after the topbar.
_show_cold_start = image_bytes is not None and "warm" not in st.session_state
if _show_cold_start:
    st.session_state["warm"] = True


# --------------------------------------------------------------------------
# Welcome screen (no image selected)
# --------------------------------------------------------------------------

if image_bytes is None:
    # Topbar breadcrumb
    html(topbar(["Aperture"], "home"))

    # Hero — eyebrow with bar + live blip, italic gradient "underneath"
    html(
        f"<section class='ap-hero ap-reveal'>"
        f"  <div class='eyebrow'>"
        f"    <span class='bar'></span>"
        f"    <span>Forensic image analysis · v1.0</span>"
        f"    <span class='blip'></span>"
        f"  </div>"
        f"  <h1>See what's <em>underneath</em><br/>the pixels.</h1>"
        f"  <p class='lede'>Aperture runs four independent forensic pipelines on any "
        f"image — AI-generation detection, classical tampering analysis, scene "
        f"understanding, and metadata inspection — then fuses them into a single "
        f"calibrated authenticity verdict with ranked, plain-language explanations.</p>"
        f"</section>"
    )

    # Hero CTAs — primary "Run a sample analysis" + secondary "Read the methodology"
    # The trailing kbd badge (↵) is rendered via ::after in the CSS so it sits
    # in its own bordered chip rather than as inline text. Buttons hug their
    # content (use_container_width=False) so spacing matches the design's
    # inline-flex .btn recipe.
    html("<div class='ap-hero-cta-anchor'></div>")
    cta_cols = st.columns([1.3, 1.5, 6], gap="small")
    with cta_cols[0]:
        if st.button("Run a sample analysis", key="hero_run_sample",
                     type="primary", use_container_width=False):
            st.session_state["_example_dropdown"] = "Authentic portrait"
            st.rerun()
    with cta_cols[1]:
        if st.button("Read the methodology", key="hero_methodology",
                     use_container_width=False):
            st.session_state["_example_dropdown"] = "Authentic landscape"
            st.rerun()
    html("<div style='margin-top:40px;'></div>")

    # [01] Four independent signals — dim-card grid
    html(section_head("[01]", "Four independent signals", right="04 / 04"))
    dim_cols = st.columns(4, gap="small")
    dims = [
        ("01", "gen",   "Generative origin",
         "Fine-tuned EfficientNet-B0 with JPEG-augmented training, hardened against "
         "re-encoding. Grad-CAM exposes the regions the model attends to.",
         "model · efficientnet-b0"),
        ("02", "manip", "Manipulation",
         "Error Level Analysis, noise-residual statistics, and copy-move detection "
         "fused with calibrated weights. Surfaces spliced regions as a heatmap.",
         "cv · ela + noise + copy-move"),
        ("03", "prov",  "Provenance",
         "EXIF parsing, JPEG quantization-table fingerprinting, and timestamp "
         "consistency. Flags 28 known anomaly classes.",
         "exif · 28 anomaly classes"),
        ("04", "comp",  "Composition",
         "Object detection (YOLOv8n), zero-shot scene classification (CLIP), and "
         "on-image OCR. Contextual cross-checks against the verdict signals.",
         "yolo · scene · ocr"),
    ]
    for col, d in zip(dim_cols, dims):
        with col:
            html(dim_card(*d))

    # [02] How it works — pipeline diagram (iframe-isolated to dodge
    # Streamlit's markdown-component SVG quirk)
    html("<div style='margin-top:56px;'></div>")
    html(section_head("[02]", "How it works", right="pipeline · 4 → 1"))
    components.html(pipeline_diagram_doc(), height=280, scrolling=False)

    # Stats trio — bound to real eval values from eval_results/cifake_metrics.json
    # (no placeholders). The design's third "OOD accuracy" tile isn't measured
    # in this repo, so we surface Test AUC instead — same column count, real
    # number, honest framing.
    import json as _json
    _metrics_path = Path("eval_results") / "cifake_metrics.json"
    try:
        _m = _json.loads(_metrics_path.read_text())
    except Exception:
        _m = {}
    _test_acc = _m.get("test_accuracy")
    _test_auc = _m.get("test_auc")
    _test_n   = _m.get("test_n_samples")
    html("<div style='margin-top:64px;'></div>")
    stats_cols = st.columns(3, gap="small")
    stats = [
        ("Avg. analysis time",
         "~8s",
         "warm-cache · 1024² input"),
        ("Held-out accuracy",
         f"{_test_acc*100:.2f}%" if _test_acc is not None else "—",
         f"CIFAKE test · n={_test_n:,}" if _test_n else "CIFAKE test split"),
        ("Test AUC",
         f"{_test_auc:.3f}" if _test_auc is not None else "—",
         "ROC · CIFAKE held-out"),
    ]
    for col, (k, v, sub) in zip(stats_cols, stats):
        with col:
            html(
                f"<div style='background:{BG_CARD};border:1px solid {BORDER};"
                f"padding:20px 22px;border-radius:3px;'>"
                f"  <div class='ap-label'>{k}</div>"
                f"  <div style='font-family:\"Source Serif 4\",serif;font-weight:600;"
                f"       font-size:30px;margin-top:8px;letter-spacing:-0.01em;"
                f"       color:{TEXT};font-feature-settings:\"tnum\";'>{v}</div>"
                f"  <div class='ap-mono' style='font-size:10px;color:{TEXT_FAINT};"
                f"       letter-spacing:0.04em;margin-top:4px;'>{sub}</div>"
                f"</div>"
            )
    st.stop()


# --------------------------------------------------------------------------
# Analyzing screen — iris animation while pipelines run
# --------------------------------------------------------------------------

import base64
import time as _time

# Guard the PIL.open call — non-image bytes (PDF, .docx) and truncated
# files raise here. We surface a friendly error and stop, instead of
# leaking a raw traceback.
try:
    img = Image.open(io.BytesIO(image_bytes))
    img.load()  # force decode so truncated files fail here, not later
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGB")
except Exception as _img_err:
    html(topbar(["Aperture"], "analyze"))
    st.error(
        f"**Could not read this image.** {type(_img_err).__name__}: "
        f"{_img_err}\n\nTry a different file (JPG, PNG, or WEBP under 24 MB)."
    )
    if st.button("← Pick a different image", key="bad_image_reset"):
        st.session_state["_example_dropdown"] = "(none)"
        try: st.query_params.clear()
        except Exception: pass
        st.rerun()
    st.stop()

# Cache key uniquely identifies this image. Skip the analyzing-screen
# replay on cache hits so it doesn't flash every rerun.
_session_key = hashlib.sha1(image_bytes).hexdigest()[:12]
_already_analyzed = st.session_state.get("_analyzed_key") == _session_key

# Topbar with session info — Aperture / session · <id> / analyze; on the
# right: filename · WxH · mode. Matches design's .topbar + .session pattern.
_size_kb = max(1, len(image_bytes) // 1024)
html(topbar(
    ["Aperture", f"session · {_session_key[:6]}"],
    "analyze",
    session_info=[
        (image_name or "uploaded", True),
        (f"{img.size[0]}×{img.size[1]}", False),
        (f"{img.format or img.mode} · {_size_kb} kb", False),
        (f"session 0a3f-{_session_key[:4]}", True),
    ],
))

# Cold-start hint — surfaced once per session, AFTER the topbar so it
# doesn't push the topbar away from the viewport top.
if _show_cold_start:
    st.info(
        "**First-time setup:** downloading and loading the YOLOv8, CLIP "
        "ViT-B/32, and EasyOCR backbones (~250 MB combined). This typically "
        "takes 30-60 seconds on first launch. Subsequent images are instant — "
        "all analyses are cached by image content."
    )

# Header chip (always shown above the active image)
html(image_chip(img, image_name or "uploaded"))
html("<div style='margin-top:18px;'></div>")

# 8 blades — 5 real pipelines + 3 decorative companions so the iris ends
# fully open. The decorative ones mirror progress (one opens per real
# completion) so the animation feels alive without overpromising.
_real = [
    ("tamp",  "Manipulation analysis"),
    ("meta",  "Metadata extraction"),
    ("scene", "Scene parsing"),
    ("ai",    "Generative analysis"),
    ("ver",   "Verdict synthesis"),
]
_decor = [
    ("comp", "Compression analysis"),
    ("prov", "Provenance check"),
    ("fp",   "Statistical fingerprint"),
]


def _img_data_uri(im: Image.Image, max_dim: int = 720) -> str:
    """Inline data URI for the analyzing-screen image preview."""
    preview = im.copy().convert("RGB")
    preview.thumbnail((max_dim, max_dim))
    bio = io.BytesIO()
    preview.save(bio, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(bio.getvalue()).decode("ascii")


def _analyzing_iframe_doc(img_uri: str, image_name: str) -> str:
    """Self-contained analyzing screen — image + scan line + iris animation
    + status text. Rendered as ``components.html(...)`` so Streamlit's
    React reconciler doesn't choke on inline ``<img data:>`` tags getting
    swapped under tippy.js tooltip targets.

    This is purely cosmetic: it animates on its own (CSS keyframes) while
    Python runs the real pipelines in a single ``st.spinner`` block.
    """
    safe_name = _html_lib_escape(image_name or "image")
    return f"""<!doctype html><html><head><meta charset='utf-8'>
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:wght@500;600;700&display=swap' rel='stylesheet'>
<style>
:root {{
  --bg: #F4F2EC; --surface-1: #FFFFFF; --border: #DEDACE; --border-strong: #C9C4B6;
  --text: #14181F; --text-dim: #3D4654; --text-muted: #6C7585; --text-faint: #99A0AC;
  --accent: #2F6FB1; --accent-soft: rgba(47,111,177,0.10);
  --accent-line: rgba(47,111,177,0.32); --accent-glow: rgba(47,111,177,0.16);
  --authentic: #3F8A66; --suspicious: #B58527; --fake: #B5462B;
  --ease: cubic-bezier(0.4,0,0.2,1);
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: Inter, -apple-system, sans-serif;
}}
.wrap {{
  display: grid; grid-template-columns: 1.1fr 1fr; gap: 48px;
  align-items: start; padding: 8px 0;
}}
.head {{
  display: flex; align-items: baseline; gap: 14px; margin: 0 0 18px;
}}
.head .kicker {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--text-faint); font-weight: 600;
}}
.head h2 {{
  margin: 0; font-family: 'Source Serif 4', serif;
  font-size: 22px; font-weight: 600; color: var(--text);
}}
.head .rule {{ flex: 1; height: 1px; background: var(--border); }}
.head .right {{
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent);
}}

.imgbox {{
  position: relative; border: 1px solid var(--border);
  overflow: hidden; background: var(--surface-1);
}}
.imgbox img {{ width: 100%; max-width: 600px; display: block; }}
.scanline {{
  position: absolute; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  box-shadow: 0 0 12px var(--accent-glow);
  animation: scan 2.4s var(--ease) infinite;
}}
@keyframes scan {{
  0%   {{ top: 0%;   opacity: 0;   }}
  10%  {{ opacity: 0.7; }}
  50%  {{ top: 100%; opacity: 0.7; }}
  60%  {{ opacity: 0; }}
  100% {{ top: 0%;   opacity: 0;   }}
}}
.caption {{
  position: absolute; left: 0; right: 0; bottom: 0;
  background: linear-gradient(180deg, transparent, color-mix(in srgb, var(--bg) 80%, transparent));
  padding: 14px 16px;
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  letter-spacing: 0.04em; color: var(--text);
  display: flex; align-items: center; gap: 8px;
}}
.caption .dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-soft);
  animation: pulse 1.4s var(--ease) infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1;   transform: scale(1);    }}
  50%      {{ opacity: 0.4; transform: scale(0.75); }}
}}

.iris-stage {{
  display: grid; place-items: center;
  padding: 20px 0 16px;
  position: relative;
}}
.iris-stage::before {{
  content: ""; position: absolute;
  width: 240px; height: 240px; border-radius: 50%;
  background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
  opacity: 0.45;
  animation: breath 4s var(--ease) infinite;
  pointer-events: none;
}}
@keyframes breath {{
  0%, 100% {{ opacity: 0.35; transform: scale(0.95); }}
  50%      {{ opacity: 0.60; transform: scale(1.05); }}
}}
.iris {{ animation: spin 24s linear infinite; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}

.stages {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px;
}}
.stage {{
  display: flex; align-items: center; gap: 10px;
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--text-muted); letter-spacing: 0.02em; padding: 4px 0;
}}
.stage .ind {{
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--suspicious);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--suspicious) 18%, transparent);
  animation: stage-pulse 1.4s var(--ease) infinite;
}}
@keyframes stage-pulse {{
  0%, 100% {{ box-shadow: 0 0 0 3px color-mix(in srgb, var(--suspicious) 18%, transparent); }}
  50%      {{ box-shadow: 0 0 0 5px color-mix(in srgb, var(--suspicious) 18%, transparent); }}
}}

.log {{
  background: var(--surface-1); border: 1px solid var(--border);
  padding: 14px 16px; border-radius: 2px;
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--text-muted);
  display: flex; flex-direction: column; gap: 6px;
}}
.log .ts {{ color: var(--text-faint); }}
.log .ok {{ color: var(--authentic); }}
.log .run {{ color: var(--suspicious); }}
</style></head>
<body>
<div class="head">
  <span class="kicker">[analysis]</span>
  <h2>Inspecting <span style="color:var(--accent);">{safe_name}</span></h2>
  <span class="rule"></span>
  <span class="right">8 pipelines running…</span>
</div>

<div class="wrap">
  <div class="imgbox">
    <img src='{img_uri}' alt=''/>
    <div class="scanline" style="top:30%"></div>
    <div class="caption">
      <span class="dot"></span> Capturing forensic signals
    </div>
  </div>
  <div>
    <div class="iris-stage">
      <svg class="iris" width="200" height="200" viewBox="0 0 200 200" style="display:block;">
        <circle cx="100" cy="100" r="90" fill="none" stroke="var(--border-strong)" stroke-width="0.8" opacity="0.7"/>
        <circle cx="100" cy="100" r="96" fill="none" stroke="var(--border)" stroke-width="0.4" opacity="0.45"/>
        <g>
          <!-- 8 blades, evenly spaced -->
          <g transform="rotate(0   100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
          <g transform="rotate(45  100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
          <g transform="rotate(90  100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
          <g transform="rotate(135 100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
          <g transform="rotate(180 100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
          <g transform="rotate(225 100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
          <g transform="rotate(270 100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
          <g transform="rotate(315 100 100)"><path d="M100 100 L114 56 L100 18 L86 56 Z" fill="var(--surface-1)" stroke="var(--accent)" stroke-width="0.5" stroke-opacity="0.6"/></g>
        </g>
        <circle cx="100" cy="100" r="22" fill="var(--accent)" opacity="0.18"/>
        <circle cx="100" cy="100" r="3" fill="var(--accent)"/>
      </svg>
    </div>
    <div class="stages">
      <div class="stage"><span class="ind"></span> Manipulation analysis</div>
      <div class="stage"><span class="ind"></span> Metadata extraction</div>
      <div class="stage"><span class="ind"></span> Scene parsing</div>
      <div class="stage"><span class="ind"></span> Generative analysis</div>
      <div class="stage"><span class="ind"></span> Compression analysis</div>
      <div class="stage"><span class="ind"></span> Provenance check</div>
      <div class="stage"><span class="ind"></span> Statistical fingerprint</div>
      <div class="stage"><span class="ind"></span> Verdict synthesis</div>
    </div>
    <div class="log" style="margin-top:24px;">
      <div><span class="ts">[00:00]</span> <span style="color:var(--text-muted);">input accepted · running pipelines</span></div>
      <div><span class="ts">[00:01]</span> <span class="run">manipulation: running…</span></div>
      <div><span class="ts">[00:02]</span> <span class="run">metadata: running…</span></div>
      <div><span class="ts">[00:04]</span> <span class="run">scene: running…</span></div>
      <div><span class="ts">[00:06]</span> <span class="run">ai: running…</span></div>
    </div>
  </div>
</div>

</body></html>"""


def _html_lib_escape(s: str) -> str:
    import html as _h
    return _h.escape(s)


if not _already_analyzed:
    # Cosmetic iframe — animates on its own while the pipelines run.
    # Single mount (no React-tree churn → no Tippy crash).
    _slot = st.empty()
    _img_uri = _img_data_uri(img)
    with _slot.container():
        components.html(
            _analyzing_iframe_doc(_img_uri, image_name or "uploaded"),
            height=520,
            scrolling=False,
        )

    # Stage-by-stage progress via st.status. Total of 6 stages so the user
    # always sees forward motion (no dead screen perception).
    _status_slot = st.empty()
    stages_total = 5 + (1 if run_scene_analysis else 0)
    with _status_slot.status(
        f"Running forensic pipelines — step 1 / {stages_total}",
        expanded=True,
    ) as _status:
        # Stage 1 — tampering
        _status.update(label=f"Step 1 / {stages_total} · Analyzing for tampering…")
        st.write("• Manipulation detection (ELA, noise residual, copy-move)…")
        tamp_result, tamp_err = _safe(_run_tampering, image_bytes)
        st.write("  ✓ tampering complete" if tamp_err is None else f"  ✕ tampering: {tamp_err}")

        # Stage 2 — metadata
        _status.update(label=f"Step 2 / {stages_total} · Parsing metadata…")
        st.write("• Metadata + EXIF analysis…")
        meta_result, meta_err = _safe(_run_metadata, image_bytes)
        st.write("  ✓ metadata complete" if meta_err is None else f"  ✕ metadata: {meta_err}")

        # Stage 3 — scene (optional)
        if run_scene_analysis:
            _status.update(label=f"Step 3 / {stages_total} · Extracting scene context (YOLO + CLIP + OCR)…")
            st.write("• Scene parsing (this is the slow one on first run — loads YOLOv8 + CLIP + EasyOCR)…")
            scene_result, scene_err = _safe(_run_scene, image_bytes)
            st.write("  ✓ scene complete" if scene_err is None else f"  ✕ scene: {scene_err}")
            ai_stage = 4
        else:
            scene_result, scene_err = None, None
            st.write("• Scene analysis skipped (toggle off in sidebar settings)")
            ai_stage = 3

        # Stage 4 — AI detection
        _status.update(label=f"Step {ai_stage} / {stages_total} · Running AI-detection model…")
        st.write("• Generative-origin detection (EfficientNet-B0 + Grad-CAM)…")
        load_weights_if_missing(AI_DETECTOR_WEIGHTS_URL, str(AI_CHECKPOINT))
        if AI_CHECKPOINT.exists():
            ai_result, ai_err = _safe(_run_ai_detector, image_bytes, str(AI_CHECKPOINT))
            st.write("  ✓ AI detection complete" if ai_err is None else f"  ✕ ai: {ai_err}")
        else:
            ai_result, ai_err = {"status": "unavailable"}, None
            st.write("  ⚠ AI detector checkpoint unavailable — skipping")

        # Stage 5 — verdict synthesis happens below; placeholder message here
        _status.update(label=f"Step {ai_stage + 1} / {stages_total} · Synthesizing verdict…", state="running")
else:
    # Already analyzed this image in this session — results all come from
    # cache so this is effectively instant. No analyzing iframe.
    _slot = None
    tamp_result, tamp_err = _safe(_run_tampering, image_bytes)
    meta_result, meta_err = _safe(_run_metadata, image_bytes)
    if run_scene_analysis:
        scene_result, scene_err = _safe(_run_scene, image_bytes)
    else:
        scene_result, scene_err = None, None
    load_weights_if_missing(AI_DETECTOR_WEIGHTS_URL, str(AI_CHECKPOINT))
    if AI_CHECKPOINT.exists():
        ai_result, ai_err = _safe(_run_ai_detector, image_bytes, str(AI_CHECKPOINT))
    else:
        ai_result, ai_err = {"status": "unavailable"}, None

# Verdict integration
features = {
    "ai_conf": (ai_result or {}).get("ai_probability", 0.5),
    "tampering_score": (tamp_result or {}).get("combined_score", 0.0),
    "metadata_score": (meta_result or {}).get("anomaly_score", 0.0),
    "has_text": 1 if ((scene_result or {}).get("ocr") or {}).get("text_found") else 0,
}

verdict_result, verdict_err = _safe(_run_verdict, features)
if not _already_analyzed and _slot is not None:
    # Tear down the analyzing iframe + finalize the status block in a
    # single rerun-stable cleanup so the user sees one smooth transition
    # to the verdict tabs (no jarring flash).
    try:
        if verdict_err is None and verdict_result is not None:
            _status.update(
                label="Analysis complete — switching to verdict",
                state="complete",
                expanded=False,
            )
        else:
            _status.update(
                label="Analysis complete with warnings — see Verdict tab",
                state="error" if verdict_err else "complete",
                expanded=True,
            )
    except Exception:
        pass
    _slot.empty()
    try:
        _status_slot.empty()
    except Exception:
        pass
    st.session_state["_analyzed_key"] = _session_key

signals = {
    "ai": ai_result,
    "tampering": tamp_result,
    "scene": scene_result,
    "metadata": meta_result,
    "verdict": verdict_result,
    "features": features,
}


# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------

tab_labels = ["Verdict", "AI Detection", "Tampering", "Scene", "Metadata", "Model Performance"]
tabs = st.tabs(tab_labels)


def _tab(idx: int, fn, *args, err: Optional[str] = None, **kwargs):
    with tabs[idx]:
        if err is not None:
            st.error(f"This analysis failed: {err}")
            if st.button("Retry", key=f"retry_{idx}"):
                st.cache_data.clear()
                st.rerun()
            return
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            st.error(f"Rendering failed: {type(exc).__name__}: {exc}")
            if st.button("Retry", key=f"retry_render_{idx}"):
                st.rerun()


_tab(0, render_verdict_tab, img, signals, err=verdict_err)
_tab(1, render_ai_tab, img, ai_result, err=ai_err)
_tab(2, render_tampering_tab, img, tamp_result, err=tamp_err)
_tab(3, render_scene_tab, img, scene_result, err=scene_err)
_tab(4, render_metadata_tab, img, meta_result, err=meta_err)
_tab(5, render_performance_tab)
