---
title: Aperture Forensics
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# Aperture — Image Forensic Analysis

**Live demo:** <https://nandann018-aperture-forensics.hf.space>

A multi-signal forensic verdict system for images. Four independent pipelines —
generative-origin detection, classical tampering analysis, scene understanding,
and metadata inspection — run in parallel, and a Platt-calibrated meta-classifier
fuses them into a single authenticity probability with ranked, plain-English
explanations.

## How it works

Each pipeline runs independently and emits a normalized score in `[0, 1]`. A
logistic-regression meta-classifier, Platt-calibrated via
`CalibratedClassifierCV`, fuses the four scores plus a binary "image-has-text"
flag into the final `P(authentic)` and a ranked list of per-factor contributions
with one-sentence English explanations.

| Pipeline | Approach |
|---|---|
| **Generative-origin** | Fine-tuned EfficientNet-B0 on CIFAKE with JPEG-augmented training; Grad-CAM heatmap |
| **Tampering** | Error Level Analysis + noise residual + SIFT copy-move detection, fused at `0.4 / 0.4 / 0.2` |
| **Scene** | YOLOv8n object detection + CLIP zero-shot scene classification + EasyOCR text extraction |
| **Metadata** | EXIF / IPTC parse, JPEG quality from quantization tables, 28 rule-based anomaly flags |

## Held-out metrics

CIFAKE test split, n = 20 000:

| Metric | Value |
|---|---|
| Accuracy | **98.25 %** |
| F1 | **98.23 %** |
| AUC | **0.9987** |

## Try it

Pick one of the curated examples in the sidebar, or upload your own image
(JPG / PNG / WEBP, up to 24 MB). The first analysis is slow (CLIP + YOLO +
EasyOCR weights are downloaded on cold start); subsequent ones are cached.

## Source

<https://github.com/Nandann018-ux/Aperture> — MIT licensed.

## Limitations

- OOD cross-generator metrics on Midjourney / Flux / DALL-E 3 hand-collected
  samples have not been produced. Treat cross-generator generalization as
  unvalidated.
- CIFAKE-trained detector may underperform on Flux, Imagen 3, Midjourney v6+,
  SDXL.
- Tampering detection is post-hoc and sees only the pixels.
- Metadata anomaly rules are hand-curated, not learned.
