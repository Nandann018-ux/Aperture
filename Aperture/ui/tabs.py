"""Per-tab render functions.

Each ``render_*`` function takes ``image`` (the PIL image being analyzed)
and the relevant signal slice from the unified results dict produced in
``app.py``. Tabs degrade gracefully when an artifact is missing (e.g. the
AI detector checkpoint hasn't been trained yet).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import streamlit as st
from PIL import Image

from Aperture.ui.components import (
    anomaly_flag,
    confidence_meter,
    contribution_row,
    html,
    image_comparison,
    section_eyebrow,
    signal_card,
    verdict_banner,
)
from Aperture.ui.theme import BAD, BG_CARD, BORDER, GOOD, PRIMARY, TEXT, TEXT_DIM, WARN

EVAL_DIR = Path("eval_results")


# ----------------------------- VERDICT ------------------------------------

def render_verdict_tab(image: Image.Image, signals: dict) -> None:
    verdict = signals.get("verdict") or {}
    prob = verdict.get("authenticity_probability", 0.5)
    label = verdict.get("verdict", "suspicious")

    col_l, col_r = st.columns([1, 1.2])
    with col_l:
        html(confidence_meter(prob, label="P(authentic)"))
        html(verdict_banner(label))
    with col_r:
        html(section_eyebrow("Signal summary"))
        _render_signal_grid(signals)

    st.markdown("<hr class='ap-divider'/>", unsafe_allow_html=True)

    with st.expander("Why this verdict?", expanded=True):
        factors = verdict.get("contributing_factors") or []
        if not factors:
            st.write("No verdict factors available — meta-classifier did not run.")
            return
        # rank already by |contribution|; show top 3
        for f in factors[:3]:
            human = {
                "ai_conf": "AI detector",
                "tampering_score": "Tampering analysis",
                "metadata_score": "Metadata",
                "has_text": "Text content",
            }.get(f["factor"], f["factor"])
            html(contribution_row(
                label=human,
                contribution=f["contribution"],
                explanation=f["explanation"],
            ))


def _render_signal_grid(signals: dict) -> None:
    ai = signals.get("ai") or {}
    tamp = signals.get("tampering") or {}
    scene = signals.get("scene") or {}
    meta = signals.get("metadata") or {}

    # AI card
    ai_conf = ai.get("ai_probability")
    if ai_conf is None:
        ai_card = signal_card("AI Detection", "—", "neutral", "◈",
                              sublabel="Checkpoint not loaded")
    else:
        status = "bad" if ai_conf > 0.6 else ("warn" if ai_conf > 0.4 else "good")
        ai_card = signal_card("AI Detection", f"{ai_conf*100:.0f}%", status, "◈",
                              sublabel=f"P(AI-generated)")

    # Tampering card
    tamp_score = tamp.get("combined_score")
    if tamp_score is None:
        tamp_card = signal_card("Tampering", "—", "neutral", "◇")
    else:
        status = "bad" if tamp_score > 0.6 else ("warn" if tamp_score > 0.3 else "good")
        tamp_card = signal_card("Tampering", f"{tamp_score*100:.0f}%", status, "◇",
                                sublabel=(tamp.get("verdict") or "").lower())

    # Scene card
    primary_scene = (scene.get("scene") or {}).get("primary_scene", "—")
    n_objects = sum((scene.get("objects") or {}).get("object_counts", {}).values())
    scene_card = signal_card("Scene", str(n_objects), "neutral", "◯",
                             sublabel=primary_scene)

    # Metadata card
    score = meta.get("anomaly_score")
    n_high = len((meta.get("anomalies_by_severity") or {}).get("high", []))
    if score is None:
        meta_card = signal_card("Metadata", "—", "neutral", "◌")
    else:
        status = "bad" if score > 0.6 else ("warn" if score > 0.3 else "good")
        meta_card = signal_card("Metadata", f"{score*100:.0f}%", status, "◌",
                                sublabel=f"{n_high} high-severity flag(s)")

    top = st.columns(2)
    bottom = st.columns(2)
    with top[0]: html(ai_card)
    with top[1]: html(tamp_card)
    with bottom[0]: html(scene_card)
    with bottom[1]: html(meta_card)


# --------------------------- AI DETECTION ---------------------------------

def render_ai_tab(image: Image.Image, ai: Optional[dict]) -> None:
    if ai is None or ai.get("status") == "unavailable":
        st.info(
            "**AI detector not loaded.** Train the EfficientNet-B0 detector "
            "(notebook 02 on Colab) and drop ``models/ai_detector_best.pt`` "
            "into the repo to enable this tab."
        )
        return

    pred_label = ai.get("label", "?")
    confidence = ai.get("confidence", 0.0)
    p_fake = ai.get("ai_probability", 0.0)
    overlay = ai.get("overlay")
    heatmap = ai.get("heatmap")

    cols = st.columns(3)
    with cols[0]:
        st.caption("Original")
        st.image(image, width="stretch")
    with cols[1]:
        st.caption("Grad-CAM heatmap")
        if heatmap is not None:
            st.image(heatmap, width="stretch", clamp=True)
        else:
            st.write("—")
    with cols[2]:
        st.caption("Overlay")
        if overlay is not None:
            st.image(overlay, width="stretch")
        else:
            st.write("—")

    st.markdown("<hr class='ap-divider'/>", unsafe_allow_html=True)

    html(section_eyebrow("Detector confidence"))
    p_real = 1.0 - p_fake
    bar = (
        f"<div style='display:flex;gap:4px;height:36px;border-radius:8px;overflow:hidden;'>"
        f"  <div style='flex:{p_real};background:{GOOD};display:flex;align-items:center;justify-content:center;color:#111;font-weight:600;'>"
        f"    REAL {p_real*100:.0f}%"
        f"  </div>"
        f"  <div style='flex:{p_fake};background:{BAD};display:flex;align-items:center;justify-content:center;color:#111;font-weight:600;'>"
        f"    FAKE {p_fake*100:.0f}%"
        f"  </div>"
        f"</div>"
    )
    html(bar)
    st.caption(
        "The heatmap shows which regions the detector attended to when "
        "predicting this class. Bright red = strong contribution; cool blue = ignored. "
        f"Predicted **{pred_label.upper()}** with confidence {confidence*100:.0f}%."
    )

    if p_fake > 0.7:
        with st.expander("What aperture is looking at"):
            st.write(
                "For AI-generated images, the detector typically attends to "
                "fine-grained texture artifacts: skin pores, hair strands, "
                "eye reflections, fabric weave, and high-frequency edges. "
                "Diffusion-generated regions often have characteristically "
                "smooth gradients with localized texture inconsistencies."
            )


# --------------------------- TAMPERING ------------------------------------

def render_tampering_tab(image: Image.Image, tamp: dict) -> None:
    if not tamp:
        st.warning("Tampering analysis did not run.")
        return
    ela_map = tamp["ela"]["heatmap"]
    noise_map = tamp["noise"]["heatmap"]
    cm_vis = tamp["copy_move"]["visualization"]

    cols = st.columns(4)
    with cols[0]:
        st.caption("Original")
        st.image(image, width="stretch")
    with cols[1]:
        st.caption(f"ELA — score {tamp['ela']['score']:.2f}")
        st.image(ela_map, width="stretch", clamp=True)
    with cols[2]:
        st.caption(f"Noise residual — CV {tamp['noise']['score']:.2f}")
        st.image(noise_map, width="stretch", clamp=True)
    with cols[3]:
        st.caption(f"Copy-move — {tamp['copy_move']['matches_count']} matches")
        st.image(cm_vis, width="stretch")

    st.markdown("<hr class='ap-divider'/>", unsafe_allow_html=True)

    cols = st.columns([1, 2])
    with cols[0]:
        st.metric("Combined score", f"{tamp['combined_score']:.2f}")
        st.metric("Verdict", tamp["verdict"])
    with cols[1]:
        html(section_eyebrow("Component breakdown"))
        for key, label in [("ela", "ELA"), ("noise", "Noise"), ("copy_move", "Copy-move")]:
            sn = tamp[key].get("score_normalized", tamp[key].get("score", 0.0))
            html(
                f"<div style='margin-bottom:0.7rem;'>"
                f"  <div style='display:flex;justify-content:space-between;'>"
                f"    <span>{label}</span><span style='color:{TEXT_DIM};'>{sn:.2f}</span>"
                f"  </div>"
                f"  <div class='ap-meter-track'>"
                f"    <div class='ap-meter-fill' style='width:{min(1.0,sn)*100:.1f}%;'></div>"
                f"  </div>"
                f"</div>"
            )

    if tamp["copy_move"]["matches_count"] > 0:
        with st.expander(f"Suspicious regions ({tamp['copy_move']['matches_count']} match pairs)"):
            for i, (p1, p2) in enumerate(tamp["copy_move"]["matches"][:10]):
                st.write(f"{i+1}. ({p1[0]:.0f}, {p1[1]:.0f}) ↔ ({p2[0]:.0f}, {p2[1]:.0f})")


# ----------------------------- SCENE --------------------------------------

def render_scene_tab(image: Image.Image, scene: dict) -> None:
    if not scene:
        st.warning("Scene analysis did not run (disabled in settings).")
        return
    objects = scene.get("objects") or {}
    clip = scene.get("scene") or {}
    ocr = scene.get("ocr") or {}

    st.image(objects.get("annotated_image") or image, width="stretch",
             caption="Annotated detections")

    cols = st.columns(3)
    with cols[0]:
        html(section_eyebrow("Detected objects"))
        counts = objects.get("object_counts") or {}
        if counts:
            st.table([{"object": k, "count": v} for k, v in sorted(
                counts.items(), key=lambda kv: -kv[1])])
        else:
            st.write("No objects detected.")
    with cols[1]:
        html(section_eyebrow("Scene classification"))
        for entry in clip.get("top_3") or []:
            pct = max(0.04, min(1.0, entry["score"]))
            html(
                f"<div style='margin-bottom:0.6rem;'>"
                f"  <div style='display:flex;justify-content:space-between;'>"
                f"    <span>{entry['label']}</span>"
                f"    <span style='color:{TEXT_DIM};'>{entry['score']*100:.1f}%</span>"
                f"  </div>"
                f"  <div class='ap-meter-track'>"
                f"    <div class='ap-meter-fill' style='width:{pct*100:.1f}%;'></div>"
                f"  </div>"
                f"</div>"
            )
    with cols[2]:
        html(section_eyebrow("Extracted text"))
        if ocr.get("text_found"):
            st.code(ocr.get("extracted_text", ""), language=None)
            st.caption(f"{len(ocr.get('regions', []))} region(s) above confidence 0.5")
        else:
            st.write("No readable text detected.")


# ----------------------------- METADATA -----------------------------------

def render_metadata_tab(image: Image.Image, meta: dict) -> None:
    if not meta:
        st.warning("Metadata analysis did not run.")
        return
    exif = meta.get("exif") or {}
    norm = meta.get("exif_normalized") or {}
    jpeg = meta.get("jpeg") or {}
    flags = meta.get("anomalies") or []
    by_sev = meta.get("anomalies_by_severity") or {}

    with st.expander("Camera & Capture", expanded=True):
        rows = []
        for label, key in [
            ("Make", "camera_make"), ("Model", "camera_model"),
            ("Software", "software"), ("ISO", "iso"),
            ("Focal length", "focal_length"), ("Exposure time", "exposure_time"),
            ("F-number", "f_number"), ("Captured", "datetime_original"),
            ("Modified", "datetime_modified"), ("GPS present", "gps_present"),
        ]:
            v = norm.get(key)
            rows.append({"field": label, "value": "—" if v in (None, "") else str(v)})
        st.table(rows)

    with st.expander("JPEG Analysis"):
        st.json({k: v for k, v in jpeg.items()})

    html(section_eyebrow("Anomalies detected"))
    if not flags:
        st.success("No anomalies flagged.")
    else:
        for sev in ("high", "medium", "low"):
            entries = by_sev.get(sev, [])
            if not entries:
                continue
            html(f"<div style='margin-top:0.5rem;color:{TEXT_DIM};font-size:0.8rem;'>"
                 f"{sev.upper()}</div>")
            chips = "".join(anomaly_flag(e["severity"], e["message"]) for e in entries)
            html(f"<div>{chips}</div>")

    with st.expander("Full raw metadata"):
        st.json({"exif": exif, "jpeg": jpeg})


# ------------------------- MODEL PERFORMANCE ------------------------------

def render_performance_tab() -> None:
    st.markdown("### AI Detector")
    metrics_path = EVAL_DIR / "cifake_metrics.json"
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text())
        cols = st.columns(3)
        cols[0].metric("Accuracy", f"{m.get('accuracy', 0):.3f}")
        cols[1].metric("F1", f"{m.get('f1', 0):.3f}")
        cols[2].metric("AUC", f"{m.get('auc', 0):.3f}")
    else:
        st.info("No CIFAKE metrics yet — run notebook 03 to produce them.")

    plot_cols = st.columns(2)
    for col, name in zip(plot_cols, ["training_curves.png", "confusion_matrix.png"]):
        p = EVAL_DIR / name
        with col:
            st.caption(name)
            if p.exists():
                st.image(str(p), width="stretch")
            else:
                st.write(f"_pending: {name}_")
    plot_cols = st.columns(2)
    for col, name in zip(plot_cols, ["roc_curve.png", "calibration_plot.png"]):
        p = EVAL_DIR / name
        with col:
            st.caption(name)
            if p.exists():
                st.image(str(p), width="stretch")
            else:
                st.write(f"_pending: {name}_")

    ood_path = EVAL_DIR / "ood_metrics.json"
    if ood_path.exists():
        st.markdown("**OOD evaluation**")
        ood = json.loads(ood_path.read_text())
        if "per_generator_accuracy" in ood:
            st.table([
                {"generator": k, "accuracy": v}
                for k, v in ood["per_generator_accuracy"].items()
            ])
        st.json(ood.get("overall", ood))

    st.markdown("<hr class='ap-divider'/>", unsafe_allow_html=True)
    st.markdown("### Meta-classifier")
    summary_path = EVAL_DIR / "meta_classifier_summary.json"
    if summary_path.exists():
        s = json.loads(summary_path.read_text())
        coefs = s.get("coefficients", {})
        cols = st.columns([1.2, 1])
        with cols[0]:
            html(section_eyebrow("Feature coefficients (LR)"))
            max_abs = max((abs(v) for v in coefs.values()), default=1.0) or 1.0
            for k, v in sorted(coefs.items(), key=lambda kv: -abs(kv[1])):
                pct = abs(v) / max_abs
                color = GOOD if v > 0 else BAD
                html(
                    f"<div style='margin-bottom:0.6rem;'>"
                    f"  <div style='display:flex;justify-content:space-between;'>"
                    f"    <span>{k}</span>"
                    f"    <span style='font-family:Fraunces,serif;color:{color};'>{v:+.2f}</span>"
                    f"  </div>"
                    f"  <div class='ap-meter-track'>"
                    f"    <div class='ap-meter-fill'"
                    f"         style='width:{pct*100:.1f}%;background:{color};'></div>"
                    f"  </div>"
                    f"</div>"
                )
        with cols[1]:
            st.metric("Accuracy", f"{s.get('metrics', {}).get('accuracy', 0):.3f}")
            st.metric("AUC", f"{s.get('metrics', {}).get('auc', 0):.3f}")
            st.metric("F1", f"{s.get('metrics', {}).get('f1', 0):.3f}")
    else:
        st.info("Train the meta-classifier (Phase 6) to populate this section.")

    cal_meta = EVAL_DIR / "calibration_meta.png"
    if cal_meta.exists():
        st.image(str(cal_meta), width="stretch",
                 caption="Meta-classifier calibration")

    st.markdown("<hr class='ap-divider'/>", unsafe_allow_html=True)
    st.markdown("### Architecture")
    st.markdown(
        "Aperture combines four independent signals into a single calibrated verdict:\n"
        "- **AI Detection** — EfficientNet-B0 fine-tuned on CIFAKE; outputs P(AI-generated).\n"
        "- **Tampering** — Error Level Analysis + noise-residual inhomogeneity + "
        "SIFT-based copy-move detection, fused with weights 0.4 / 0.4 / 0.2.\n"
        "- **Scene** — YOLOv8n for objects, CLIP ViT-B/32 zero-shot for scene type, "
        "EasyOCR for any embedded text.\n"
        "- **Metadata** — EXIF / IPTC parsing, JPEG quality estimation from quantization "
        "tables, rule-based anomaly flags.\n\n"
        "A Platt-calibrated logistic regression meta-classifier (4 inputs) produces "
        "the final P(authentic) with ranked contributing factors and plain-English "
        "explanations."
    )
    diagram = EVAL_DIR / "pipeline_diagram.png"
    if diagram.exists():
        st.image(str(diagram), width="stretch", caption="Pipeline diagram")
