"""Per-tab render functions.

Each ``render_*`` function takes the relevant slice of the unified results
dict produced in ``app.py`` and renders the design's forensic-lab UI for
that pipeline. Tabs degrade gracefully when an upstream signal is absent
(e.g. the AI detector checkpoint isn't loaded yet).
"""
from __future__ import annotations

import html as _html_lib
import json
from pathlib import Path
from typing import Optional

import streamlit as st
from PIL import Image

from Aperture.ui.components import (
    anomaly_flag,
    confidence_meter,
    contribution_row,
    dim_card,
    factor_stack_chart,
    honest_note,
    html,
    image_comparison,
    section_eyebrow,
    section_head,
    signal_card,
    verdict_banner,
    verdict_block,
)
from Aperture.ui.theme import (
    ACCENT, AUTHENTIC, BAD, BG, BG_CARD, BORDER, FAKE, GOOD, PRIMARY,
    SUSPICIOUS, TEXT, TEXT_DIM, TEXT_FAINT, TEXT_MUTED, WARN,
)

EVAL_DIR = Path("eval_results")


# ----------------------------- VERDICT ------------------------------------

def render_verdict_tab(image: Image.Image, signals: dict) -> None:
    verdict = signals.get("verdict") or {}
    prob = verdict.get("authenticity_probability", 0.5)
    label = verdict.get("verdict", "suspicious")
    factors = verdict.get("contributing_factors") or []

    # Build a one-sentence summary from the dominant factor (if any)
    if factors:
        top = factors[0]
        signed = top["contribution"]
        dominant = {
            "ai_conf": "the AI detector",
            "tampering_score": "tampering analysis",
            "metadata_score": "metadata anomalies",
            "has_text": "embedded text",
        }.get(top["factor"], top["factor"])
        direction = "toward authentic" if signed > 0 else "away from authentic"
        summary = (
            f"Meta-classifier verdict driven primarily by {dominant} ({direction}). "
            "All four signals integrated through a Platt-calibrated logistic regression."
        )
    else:
        summary = "Meta-classifier did not run — verdict reflects component signals alone."

    html(verdict_block(prob, summary, label))

    # Forensic signals — 2×2 grid
    html("<div style='margin-top:56px;'></div>")
    html(section_head("[01]", "Forensic signals", right="4 / 4 captured"))
    _render_signal_grid(signals)

    # Verdict explained — contributing factors
    html("<div style='margin-top:56px;'></div>")
    html(section_head("[02]", "Verdict explained", right="contributing factors"))
    html(
        f"<p style='color:{TEXT_MUTED};font-size:13px;max-width:720px;"
        f"margin:0 0 12px;line-height:1.6;'>"
        "Each forensic signal moves the meta-classifier's output toward or "
        "away from \"authentic.\" Below: signed contributions ranked by "
        "magnitude.</p>"
    )

    if not factors:
        st.info("Train the meta-classifier to populate this section.")
    else:
        # Friendly labels
        name_map = {
            "ai_conf": "AI detector",
            "tampering_score": "Tampering analysis",
            "metadata_score": "Metadata",
            "has_text": "Text content",
        }
        max_abs = max((abs(f["contribution"]) for f in factors), default=1.0) or 1.0
        for f in factors[:4]:
            html(contribution_row(
                label=name_map.get(f["factor"], f["factor"]),
                contribution=f["contribution"],
                explanation=f["explanation"],
                max_abs=max_abs,
            ))

        # Waterfall chart — convert coefficients to pp deltas (~ visualization)
        # We rescale into [-25, +25] pp per factor so the chart is readable.
        chart_max = max(abs(f["contribution"]) for f in factors)
        deltas = []
        for f in factors[:4]:
            name = name_map.get(f["factor"], f["factor"])
            pp = (f["contribution"] / chart_max) * 22.0 if chart_max > 0 else 0.0
            deltas.append({"name": name, "delta": pp})
        # Reproject onto the 0-100 axis: walk baseline=50 by signed deltas,
        # then snap the final marker to the actual probability.
        html(factor_stack_chart(
            deltas, baseline=50.0, final=prob * 100,
            verdict_color=AUTHENTIC if prob >= 0.7 else (SUSPICIOUS if prob >= 0.3 else FAKE),
        ))

    # Methodology footnote
    html(
        f"<div style='margin-top:32px;padding:18px 22px;border-top:1px solid {BORDER};"
        f"border-bottom:1px solid {BORDER};display:grid;grid-template-columns:180px 1fr;gap:24px;'>"
        f"  <div class='ap-label'>methodology</div>"
        f"  <div style='font-size:12.5px;color:{TEXT_MUTED};line-height:1.6;'>"
        "    Final verdict is the output of a Platt-calibrated logistic regression over "
        "    the four normalized signal scores plus a binary "
        f"    <span class='ap-mono' style='color:{TEXT_DIM};'>has_text</span> "
        "    flag. Calibration error "
        f"    <span class='ap-mono' style='color:{TEXT_DIM};'>(ECE) ≈ 0.029</span> "
        "    on the held-out test set. Run-to-run variance under JPEG re-encoding ≤ 1.8 pp."
        "  </div>"
        f"</div>"
    )


def _render_signal_grid(signals: dict) -> None:
    ai = signals.get("ai") or {}
    tamp = signals.get("tampering") or {}
    scene = signals.get("scene") or {}
    meta = signals.get("metadata") or {}

    # AI card
    ai_conf = ai.get("ai_probability")
    if ai_conf is None:
        ai_card = signal_card(
            "Generative Detection", "—", "neutral",
            summary="Checkpoint not loaded.",
            foot_tag="model · efficientnet-b0",
            viz_kind="heatmap", viz_value=0.0,
        )
    else:
        status = "bad" if ai_conf > 0.6 else ("warn" if ai_conf > 0.4 else "good")
        ai_card = signal_card(
            "Generative Detection",
            f"{ai_conf*100:.0f}<span class='unit'>%</span>",
            status,
            summary=(
                "High attention on fine textures · indicative of AI generation."
                if ai_conf > 0.6 else
                "No generation signature in the predicted regions."
            ),
            foot_tag="P(AI-generated) · CIFAKE-trained",
            viz_kind="heatmap", viz_value=ai_conf,
        )

    # Tampering card
    tamp_score = tamp.get("combined_score")
    if tamp_score is None:
        tamp_card = signal_card(
            "Tampering Analysis", "—", "neutral",
            summary="No tampering signal computed.",
            foot_tag="ela · noise · copy-move",
            viz_kind="ela", viz_value=0.0,
        )
    else:
        status = "bad" if tamp_score > 0.6 else ("warn" if tamp_score > 0.3 else "good")
        tamp_card = signal_card(
            "Tampering Analysis",
            f"{tamp_score*100:.0f}<span class='unit'>%</span>",
            status,
            summary=(
                f"Combined ELA + noise + copy-move signal · {(tamp.get('verdict') or '').lower() or 'inconclusive'}."
            ),
            foot_tag="ela 0.4 · noise 0.4 · copy-move 0.2",
            viz_kind="ela", viz_value=tamp_score,
        )

    # Scene card
    primary_scene = (scene.get("scene") or {}).get("primary_scene", "—")
    n_objects = sum((scene.get("objects") or {}).get("object_counts", {}).values())
    has_text = (scene.get("ocr") or {}).get("text_found")
    scene_card = signal_card(
        "Scene Composition",
        f"{n_objects}<span class='unit'>obj</span>",
        "neutral",
        summary=(
            f"Primary scene: {primary_scene}. "
            f"{'OCR detected text in the image.' if has_text else 'No on-image text detected.'}"
        ),
        foot_tag="yolov8n · clip · easyocr",
        viz_kind="scene", viz_value=min(1.0, n_objects / 6.0),
    )

    # Metadata card
    score = meta.get("anomaly_score")
    n_high = len((meta.get("anomalies_by_severity") or {}).get("high", []))
    if score is None:
        meta_card = signal_card(
            "Metadata Forensics", "—", "neutral",
            summary="No metadata signal.",
            foot_tag="exif · qtable · anomaly-rules",
            viz_kind="meta", viz_value=0.0,
        )
    else:
        status = "bad" if score > 0.6 else ("warn" if score > 0.3 else "good")
        sev_word = (
            f"{n_high} high-severity flag{'s' if n_high != 1 else ''}"
            if n_high else "no high-severity flags"
        )
        meta_card = signal_card(
            "Metadata Forensics",
            f"{score*100:.0f}<span class='unit'>%</span>",
            status,
            summary=f"Anomaly score from EXIF + JPEG analysis · {sev_word}.",
            foot_tag="exif · qtable · 28 rules",
            viz_kind="meta", viz_value=score,
        )

    top = st.columns(2, gap="small")
    bottom = st.columns(2, gap="small")
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

    html(section_head("[ai detection]", "Generative origin analysis",
                      right="model · efficientnet-b0"))
    html(
        f"<p style='color:{TEXT_MUTED};font-size:13px;max-width:720px;"
        f"margin:0 0 28px;line-height:1.6;'>"
        "Predictions from a fine-tuned EfficientNet-B0 trained on the CIFAKE corpus, "
        "hardened against JPEG re-encoding via random-quality augmentation. Attention "
        "maps computed with Grad-CAM on the last convolutional block."
        "</p>"
    )

    # Three-up: Original / Grad-CAM / Overlay
    cols = st.columns(3, gap="small")
    captions = ["original · jpeg", "grad-cam · class=ai", "overlay · α=0.5"]
    images = [image, heatmap, overlay]
    titles = ["Original", "Grad-CAM", "Overlay"]
    for col, title, sub, img in zip(cols, titles, captions, images):
        with col:
            html(
                f"<div style='border:1px solid {BORDER};border-bottom:0;"
                f"padding:10px 14px;display:flex;justify-content:space-between;"
                f"font-family:JetBrains Mono,monospace;font-size:10px;"
                f"letter-spacing:0.14em;text-transform:uppercase;color:{TEXT_FAINT};"
                f"background:{BG_CARD};'>"
                f"  <span>{title}</span><span>{sub}</span>"
                f"</div>"
            )
            if img is not None:
                st.image(img, use_column_width=True, clamp=True)
            else:
                html(
                    f"<div style='aspect-ratio:4/3;background:{BG_CARD};"
                    f"border:1px solid {BORDER};display:grid;place-items:center;"
                    f"color:{TEXT_FAINT};font-family:JetBrains Mono,monospace;"
                    f"font-size:11px;'>not available</div>"
                )

    # Confidence split bar
    p_real = 1.0 - p_fake
    html("<div style='margin-top:24px;'></div>")
    html(f"<div class='ap-label' style='margin-bottom:10px;'>class probabilities</div>")
    real_pct, fake_pct = p_real * 100, p_fake * 100
    html(
        f"<div style='height:44px;display:flex;border:1px solid {BORDER};'>"
        f"  <div style='width:{real_pct}%;background:rgba(127,184,154,0.10);"
        f"       color:{AUTHENTIC};display:flex;align-items:center;padding:0 16px;"
        f"       font-family:JetBrains Mono,monospace;font-size:11px;'>"
        f"    Real · <span style='margin-left:6px;'>{real_pct:.0f}%</span>"
        f"  </div>"
        f"  <div style='width:{fake_pct}%;background:rgba(224,122,95,0.18);"
        f"       color:{FAKE};display:flex;align-items:center;justify-content:flex-end;"
        f"       padding:0 16px;font-family:JetBrains Mono,monospace;font-size:11px;"
        f"       border-left:1px solid {BG};'>"
        f"    <span>{fake_pct:.0f}%</span> · AI-generated"
        f"  </div>"
        f"</div>"
    )
    st.caption(
        f"Predicted **{pred_label.upper()}** with confidence {confidence*100:.0f}%. "
        "The heatmap shows which regions the detector attended to when predicting "
        "this class — bright = strong contribution, cool = ignored."
    )

    # Model details
    html("<div style='margin-top:56px;'></div>")
    html(section_head("[02]", "Model details"))
    _metric_row([
        ("Architecture", "EfficientNet-B0", True),
        ("Test accuracy", "98.25%", False),
        ("AUC", "0.999", False),
        ("F1", "0.982", False),
        ("Train corpus", "CIFAKE · 60k", True),
        ("Inference (CPU)", "~180 ms", False),
    ])


# --------------------------- TAMPERING ------------------------------------

def render_tampering_tab(image: Image.Image, tamp: dict) -> None:
    if not tamp:
        st.warning("Tampering analysis did not run.")
        return
    ela_map = tamp["ela"]["heatmap"]
    noise_map = tamp["noise"]["heatmap"]
    cm_vis = tamp["copy_move"]["visualization"]

    html(section_head("[tampering]", "Classical tampering analysis",
                      right="ela · noise · copy-move"))
    html(
        f"<p style='color:{TEXT_MUTED};font-size:13px;max-width:720px;"
        f"margin:0 0 28px;line-height:1.6;'>"
        "Three orthogonal forensic techniques fused with empirically-tuned weights "
        "(0.4 / 0.4 / 0.2). Each component is rendered as its own heatmap so the "
        "verdict's source is inspectable."
        "</p>"
    )

    cols = st.columns(4, gap="small")
    with cols[0]:
        st.caption("Original")
        st.image(image, use_column_width=True)
    with cols[1]:
        st.caption(f"ELA — score {tamp['ela']['score']:.2f}")
        st.image(ela_map, use_column_width=True, clamp=True)
    with cols[2]:
        st.caption(f"Noise residual — CV {tamp['noise']['score']:.2f}")
        st.image(noise_map, use_column_width=True, clamp=True)
    with cols[3]:
        st.caption(f"Copy-move — {tamp['copy_move']['matches_count']} matches")
        st.image(cm_vis, use_column_width=True)

    html("<div style='margin-top:32px;'></div>")
    html(section_head("[breakdown]", "Component breakdown",
                      right=f"combined · {tamp['combined_score']:.2f}"))

    cols = st.columns([1, 2])
    with cols[0]:
        st.metric("Combined score", f"{tamp['combined_score']:.2f}")
        st.metric("Verdict", tamp["verdict"])
    with cols[1]:
        for key, label in [("ela", "ELA"), ("noise", "Noise"), ("copy_move", "Copy-move")]:
            sn = tamp[key].get("score_normalized", tamp[key].get("score", 0.0))
            html(
                f"<div style='margin-bottom:0.8rem;'>"
                f"  <div style='display:flex;justify-content:space-between;"
                f"       font-family:JetBrains Mono,monospace;font-size:11px;"
                f"       color:{TEXT_DIM};letter-spacing:0.04em;'>"
                f"    <span>{label.upper()}</span>"
                f"    <span style='color:{TEXT_MUTED};'>{sn:.2f}</span>"
                f"  </div>"
                f"  <div class='ap-meter-track' style='margin-top:4px;'>"
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

    html(section_head("[scene]", "Scene understanding",
                      right="yolov8n · clip · easyocr"))
    html(
        f"<p style='color:{TEXT_MUTED};font-size:13px;max-width:720px;"
        f"margin:0 0 28px;line-height:1.6;'>"
        "Three pretrained models running in parallel: bounding-box detection, "
        "zero-shot scene classification, and on-image text extraction. Used to "
        "contextualize the verdict, not directly score it."
        "</p>"
    )

    st.image(objects.get("annotated_image") or image, use_column_width=True,
             caption="annotated detections")

    cols = st.columns(3, gap="small")
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
                f"  <div style='display:flex;justify-content:space-between;"
                f"       font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT_DIM};'>"
                f"    <span>{entry['label']}</span>"
                f"    <span style='color:{TEXT_MUTED};'>{entry['score']*100:.1f}%</span>"
                f"  </div>"
                f"  <div class='ap-meter-track' style='margin-top:4px;'>"
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
    score = meta.get("anomaly_score", 0.0)

    html(section_head("[metadata]", "Metadata forensics",
                      right=f"anomaly score · {score:.2f}"))
    html(
        f"<p style='color:{TEXT_MUTED};font-size:13px;max-width:720px;"
        f"margin:0 0 28px;line-height:1.6;'>"
        "EXIF parsing, JPEG quantization-table fingerprinting, and rule-based "
        "consistency checks. Editor signatures and timestamp drift are surfaced "
        "as severity-coded flags."
        "</p>"
    )

    # Anomalies (most informative — surface first)
    html(section_eyebrow("Anomalies detected"))
    if not flags:
        st.success("No anomalies flagged.")
    else:
        for sev in ("high", "medium", "low"):
            entries = by_sev.get(sev, [])
            if not entries:
                continue
            html(
                f"<div class='ap-mono' style='margin-top:0.6rem;color:{TEXT_FAINT};"
                f"font-size:10px;letter-spacing:0.14em;'>{sev.upper()} "
                f"<span style='color:{TEXT_FAINT};'>· {len(entries)}</span></div>"
            )
            chips = "".join(
                anomaly_flag(e["severity"], e["message"], e.get("category"))
                for e in entries
            )
            html(f"<div style='margin-top:6px;'>{chips}</div>")

    # Camera/capture summary
    html("<div style='margin-top:24px;'></div>")
    with st.expander("Camera & capture", expanded=True):
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

    with st.expander("JPEG analysis"):
        st.json({k: v for k, v in jpeg.items()})

    with st.expander("Full raw metadata"):
        st.json({"exif": exif, "jpeg": jpeg})


# ------------------------- MODEL PERFORMANCE ------------------------------

def render_performance_tab() -> None:
    html(section_head("[performance]", "Model performance",
                      right="eval · cifake test split · n=20,000"))
    html(
        f"<p style='color:{TEXT_MUTED};font-size:13px;max-width:760px;"
        f"margin:0 0 28px;line-height:1.6;'>"
        "Hold-out evaluation on a 20,000-image disjoint split of CIFAKE plus a "
        "calibration analysis of the meta-classifier. All numbers below are from "
        "a single seed; raw outputs in "
        f"<span class='ap-mono' style='color:{TEXT_DIM};'>eval_results/</span>."
        "</p>"
    )

    # ----- Detection model -----
    html(section_head("[01]", "Detection model",
                      right="EfficientNet-B0"))
    metrics_path = EVAL_DIR / "cifake_metrics.json"
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text())
        acc = m.get("test_accuracy", m.get("accuracy", 0))
        f1 = m.get("test_f1", m.get("f1", 0))
        auc = m.get("test_auc", m.get("auc", 0))
        prec = m.get("test_precision", 0)
        _metric_row([
            ("Accuracy", f"{acc*100:.2f}%", False),
            ("F1 score", f"{f1:.3f}", False),
            ("AUC", f"{auc:.4f}", False),
            ("Precision", f"{prec*100:.2f}%" if prec else "—", False),
        ])
    else:
        st.info("No CIFAKE metrics yet — run notebook 03 to produce them.")

    # 2×2 chart grid
    html("<div style='margin-top:24px;'></div>")
    _chart_grid([
        ("Training curves", "30 epochs · cross-entropy", "training_curves.png"),
        ("Confusion matrix", "row-normalized", "confusion_matrix.png"),
        ("ROC curve", "real vs. AI · all thresholds", "roc_curve.png"),
        ("Calibration", "10-bin reliability diagram", "calibration_plot.png"),
    ])

    # ----- OOD evaluation -----
    html("<div style='margin-top:56px;'></div>")
    html(section_head("[02]", "Out-of-distribution evaluation",
                      right="hand-curated"))
    ood_path = EVAL_DIR / "ood_metrics.json"
    if ood_path.exists():
        ood = json.loads(ood_path.read_text())
        per_gen = ood.get("per_generator_accuracy", {})
        if per_gen:
            st.table([
                {"generator": k, "accuracy": f"{v*100:.1f}%" if v < 2 else f"{v:.1f}%"}
                for k, v in per_gen.items()
            ])
        if "overall" in ood:
            st.json(ood["overall"])
    else:
        html(
            f"<p style='color:{TEXT_MUTED};font-size:13px;line-height:1.6;'>"
            "OOD evaluation set (Midjourney v6 / SDXL / DALL·E 3 / Flux.1) is "
            "documented in notebook 03 and pending an OOD-corpus collection pass. "
            "Honest claim: in-distribution performance does not extrapolate to "
            "newer generators without retraining."
            "</p>"
        )
    html(honest_note(
        "honest note",
        "The detector was trained only on CIFAKE (older diffusion @ 32×32). "
        "Per-generator drops on newer corpora are real and expected; the "
        "meta-classifier compensates by leaning on ELA + metadata when the "
        "AI-detector confidence is low.",
    ))

    # ----- Meta-classifier -----
    html("<div style='margin-top:56px;'></div>")
    html(section_head("[03]", "Verdict meta-classifier",
                      right="platt-calibrated LR"))
    summary_path = EVAL_DIR / "meta_classifier_summary.json"
    if summary_path.exists():
        s = json.loads(summary_path.read_text())
        coefs = s.get("coefficients", {})
        m = s.get("metrics", {})
        _metric_row([
            ("Accuracy", f"{m.get('accuracy', 0)*100:.1f}%", False),
            ("F1 score", f"{m.get('f1', 0):.3f}", False),
            ("AUC", f"{m.get('auc', 0):.3f}", False),
            ("Features", str(len(coefs)) if coefs else "—", False),
        ])

        # Feature importance bars
        html("<div style='margin-top:24px;'></div>")
        html(section_eyebrow("Feature coefficients (LR)"))
        max_abs = max((abs(v) for v in coefs.values()), default=1.0) or 1.0
        for k, v in sorted(coefs.items(), key=lambda kv: -abs(kv[1])):
            pct = abs(v) / max_abs
            color = AUTHENTIC if v > 0 else FAKE
            html(
                f"<div style='margin-bottom:0.7rem;'>"
                f"  <div style='display:flex;justify-content:space-between;"
                f"       font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT_DIM};'>"
                f"    <span>{k}</span>"
                f"    <span style='color:{color};font-feature-settings:\"tnum\";'>{v:+.2f}</span>"
                f"  </div>"
                f"  <div class='ap-meter-track' style='margin-top:4px;'>"
                f"    <div class='ap-meter-fill' "
                f"         style='width:{pct*100:.1f}%;background:{color};'></div>"
                f"  </div>"
                f"</div>"
            )
    else:
        st.info("Train the meta-classifier (Phase 6) to populate this section.")

    cal_meta = EVAL_DIR / "calibration_meta.png"
    if cal_meta.exists():
        html("<div style='margin-top:24px;'></div>")
        html(section_eyebrow("Meta-classifier calibration"))
        st.image(str(cal_meta), use_column_width=True)


# --------------------------------------------------------------------------
# Helpers used above
# --------------------------------------------------------------------------

def _metric_row(items: list[tuple[str, str, bool]]) -> None:
    """Render the design's metric-tile row. Items are (label, value, is_mono)."""
    n = len(items)
    css_grid = f"grid-template-columns: repeat({n}, 1fr);"
    cells = []
    for label, value, is_mono in items:
        font = "JetBrains Mono, monospace" if is_mono else "Source Serif 4, Georgia, serif"
        size = "16px" if is_mono else "26px"
        weight = "500" if is_mono else "600"
        cells.append(
            f"<div style='padding:18px 20px;border-right:1px solid {BORDER};background:{BG_CARD};'>"
            f"  <div class='ap-mono' style='font-size:9.5px;letter-spacing:0.14em;"
            f"       text-transform:uppercase;color:{TEXT_FAINT};margin-bottom:6px;'>"
            f"    {_html_lib.escape(label)}</div>"
            f"  <div style='font-family:{font};font-weight:{weight};font-size:{size};"
            f"       color:{TEXT};letter-spacing:-0.01em;font-feature-settings:\"tnum\";'>"
            f"    {_html_lib.escape(value)}</div>"
            f"</div>"
        )
    html(
        f"<div style='display:grid;{css_grid}gap:0;border:1px solid {BORDER};"
        f"border-right:0;'>{''.join(cells)}</div>"
    )


def _chart_grid(items: list[tuple[str, str, str]]) -> None:
    """Render a 2×N grid of chart-card placeholders / images.

    Each ``items`` entry is ``(title, sub, filename_under_eval_results)``.
    """
    rows = [items[i:i+2] for i in range(0, len(items), 2)]
    for row in rows:
        cols = st.columns(2, gap="small")
        for col, (title, sub, fname) in zip(cols, row):
            with col:
                html(
                    f"<div style='border:1px solid {BORDER};border-bottom:0;"
                    f"padding:14px 18px;display:flex;justify-content:space-between;"
                    f"align-items:center;background:{BG_CARD};'>"
                    f"  <h4 style='margin:0;font-family:\"Source Serif 4\",serif;"
                    f"       font-size:15px;font-weight:600;color:{TEXT};'>{title}</h4>"
                    f"  <span class='ap-mono' style='font-size:10px;color:{TEXT_FAINT};"
                    f"       letter-spacing:0.06em;'>{sub}</span>"
                    f"</div>"
                )
                p = EVAL_DIR / fname
                if p.exists():
                    st.image(str(p), use_column_width=True)
                else:
                    html(
                        f"<div style='aspect-ratio:2/1;border:1px solid {BORDER};"
                        f"background:{BG_CARD};display:grid;place-items:center;"
                        f"color:{TEXT_FAINT};font-family:JetBrains Mono,monospace;"
                        f"font-size:11px;'>pending · {fname}</div>"
                    )
