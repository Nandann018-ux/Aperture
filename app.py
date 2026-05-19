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
from PIL import Image

st.set_page_config(
    page_title="Aperture — Image Forensic Analysis",
    layout="wide",
    page_icon="◉",
    initial_sidebar_state="expanded",
)

from Aperture.ui.components import html, section_eyebrow
from Aperture.ui.tabs import (
    render_ai_tab,
    render_metadata_tab,
    render_performance_tab,
    render_scene_tab,
    render_tampering_tab,
    render_verdict_tab,
)
from Aperture.ui.theme import PRIMARY, TEXT, TEXT_DIM, inject_custom_css

inject_custom_css()

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

EXAMPLES_DIR = Path("examples")
MODELS_DIR = Path("models")
AI_CHECKPOINT = MODELS_DIR / "ai_detector_best.pt"
META_CHECKPOINT = MODELS_DIR / "meta_classifier.pkl"

# Paste the GitHub Release asset URL for ai_detector_best.pt here once the
# release is published. Leave as-is to keep the AI Detection tab disabled.
# Example: https://github.com/Nandann018-ux/Aperture/releases/download/v0.1/ai_detector_best.pt
AI_DETECTOR_WEIGHTS_URL = ""

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
    html(
        f"<div style='font-family:Fraunces,serif;font-size:2.2rem;line-height:1;"
        f"color:{TEXT};margin-bottom:0.1rem;'>aperture</div>"
        f"<div class='ap-tagline'>Image Forensic Analysis</div>"
    )
    st.markdown("<hr class='ap-divider'/>", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload image",
        type=["jpg", "jpeg", "png", "webp"],
        help="Max 10 MB. JPEG / PNG / WEBP.",
    )

    example_labels = ["(none)"] + [label for label, _ in EXAMPLE_FILES]
    example_choice = st.selectbox("Try an example", example_labels, index=0)

    with st.expander("Analysis Settings"):
        ai_model = st.selectbox("AI detector model", ["efficientnet_b0"], index=0)
        tampering_sensitivity = st.slider(
            "Tampering sensitivity", 0.3, 0.7, 0.5, step=0.05,
            help="Threshold for the 'suspicious' verdict band on the tampering signal.",
        )
        run_scene_analysis = st.checkbox("Run scene analysis", value=True)

    with st.expander("About"):
        st.markdown(
            "Aperture is an image-forensics toolkit that combines an AI-detection "
            "CNN with classical tampering analysis, scene understanding, and "
            "metadata inspection.\n\n"
            "Built as a portfolio project — pipeline + Streamlit UI in one repo.\n\n"
            "- GitHub: _link in your README_\n"
            "- Author: Nandan Acharya"
        )


# --------------------------------------------------------------------------
# Resolve which image to analyze
# --------------------------------------------------------------------------

def _resolve_bytes() -> tuple[Optional[bytes], Optional[str]]:
    if uploaded is not None:
        data = uploaded.getvalue()
        if len(data) > 10 * 1024 * 1024:
            st.sidebar.error("Image exceeds 10 MB. Please upload a smaller file.")
            return None, None
        return data, uploaded.name
    if example_choice != "(none)":
        fname = dict(EXAMPLE_FILES)[example_choice]
        path = EXAMPLES_DIR / fname
        if path.exists():
            return path.read_bytes(), fname
    return None, None


image_bytes, image_name = _resolve_bytes()

# Cold-start hint: the first image in a session triggers ~250 MB of model
# downloads + warm-up (YOLOv8, CLIP, EasyOCR). On Streamlit Community Cloud
# this lands on the user as a 30-60 s wait. Surface it explicitly the first
# time so the page doesn't look hung.
if image_bytes is not None and "warm" not in st.session_state:
    st.session_state["warm"] = True
    st.info(
        "**First-time setup:** downloading and loading the YOLOv8, CLIP "
        "ViT-B/32, and EasyOCR backbones (~250 MB combined). This typically "
        "takes 30-60 seconds on first launch. Subsequent images are instant — "
        "all analyses are cached by image content."
    )


# --------------------------------------------------------------------------
# Welcome screen (no image selected)
# --------------------------------------------------------------------------

if image_bytes is None:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        html(
            f"<div style='text-align:center;margin-top:3rem;'>"
            f"  <div style='font-family:Fraunces,serif;font-size:3.5rem;"
            f"        line-height:1.05;color:{TEXT};'>"
            f"    Upload an image to begin"
            f"  </div>"
            f"  <div style='color:{TEXT_DIM};margin-top:0.6rem;max-width:540px;"
            f"        margin-left:auto;margin-right:auto;'>"
            f"    Aperture inspects each image with four independent pipelines — "
            f"    AI-generation detection, classical tampering forensics, scene "
            f"    understanding, and metadata analysis — and fuses them into a "
            f"    single calibrated authenticity verdict."
            f"  </div>"
            f"</div>"
        )

    st.markdown("<hr class='ap-divider'/>", unsafe_allow_html=True)
    html(section_eyebrow("Or pick a curated example"))

    rows = [EXAMPLE_FILES[i:i + 3] for i in range(0, len(EXAMPLE_FILES), 3)]
    for row in rows:
        cols = st.columns(len(row))
        for col, (label, fname) in zip(cols, row):
            path = EXAMPLES_DIR / fname
            with col:
                if path.exists():
                    st.image(str(path), width="stretch")
                else:
                    st.write("_missing_")
                st.caption(label)
    st.stop()


# --------------------------------------------------------------------------
# Active image — header
# --------------------------------------------------------------------------

img = Image.open(io.BytesIO(image_bytes))

header_cols = st.columns([2, 1])
with header_cols[0]:
    st.image(img, width=600)
with header_cols[1]:
    html(section_eyebrow("File"))
    st.write(image_name or "uploaded")
    html(section_eyebrow("Size"))
    st.write(f"{img.size[0]} × {img.size[1]} px")
    html(section_eyebrow("Mode"))
    st.write(img.mode)


# --------------------------------------------------------------------------
# Run all analyses (each cached on image_bytes content)
# --------------------------------------------------------------------------

with st.spinner("Running tampering analysis..."):
    tamp_result, tamp_err = _safe(_run_tampering, image_bytes)
with st.spinner("Reading metadata..."):
    meta_result, meta_err = _safe(_run_metadata, image_bytes)
if run_scene_analysis:
    with st.spinner("Loading scene models..."):
        scene_result, scene_err = _safe(_run_scene, image_bytes)
else:
    scene_result, scene_err = None, None

# Ensure detector weights are on disk before instantiating the model.
# Cached for the lifetime of the container so the download fires once.
load_weights_if_missing(AI_DETECTOR_WEIGHTS_URL, str(AI_CHECKPOINT))

if AI_CHECKPOINT.exists():
    with st.spinner("Running AI detector..."):
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


_tab(0, render_verdict_tab, img, signals, err=verdict_err if not META_CHECKPOINT.exists() else None)
_tab(1, render_ai_tab, img, ai_result, err=ai_err)
_tab(2, render_tampering_tab, img, tamp_result, err=tamp_err)
_tab(3, render_scene_tab, img, scene_result, err=scene_err)
_tab(4, render_metadata_tab, img, meta_result, err=meta_err)
_tab(5, render_performance_tab)
