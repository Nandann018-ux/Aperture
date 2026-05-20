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

![Architecture](docs/architecture.png)

Aperture inspects an image with four independent forensic pipelines —
AI-generation detection, classical tampering analysis, scene understanding,
and metadata inspection — then fuses them into a single calibrated
authenticity verdict with ranked explanations.

> 🔗 **Live demo:** _coming soon — deploying to Streamlit Community Cloud_

---

## What is Aperture?

AI-generated and manually-tampered images are a 2026 problem. Image
verification used to be a niche journalism / OSINT concern; today it
touches insurance claims, dating profiles, identity-fraud cases, and the
news a reader sees on their phone. Single-signal detectors (AI-only or
EXIF-only) miss the long tail of failure modes — Aperture is built on the
premise that **multiple weak signals fused with proper calibration beat any
single strong signal**.

Each pipeline runs independently and outputs a normalized score in
`[0, 1]`. A Platt-calibrated logistic regression meta-classifier takes the
four scores plus a binary "image-has-text" flag and produces the final
`P(authentic)`, along with per-factor contributions and one-sentence
plain-English explanations of *why* the model called it the way it did.

The system is deliberately **interpretable**: every verdict comes with its
contributing factors ranked by signed contribution and a short narrative
sentence per factor, so users (and reviewers) can see when the model is
over-relying on one signal.

---

## Live Demo

| | |
|---|---|
| Streamlit Community Cloud | _link pending deployment_ |
| Source repo | <https://github.com/Nandann018-ux/Aperture> |

Try it with your own image, or pick one of six curated examples in the
sidebar.

---

## Demo screenshots

| Verdict tab | AI Detection heatmap |
|---|---|
| ![](docs/screenshots/verdict.png) | ![](docs/screenshots/ai_detection.png) |

| Tampering analysis | Model Performance |
|---|---|
| ![](docs/screenshots/tampering.png) | ![](docs/screenshots/performance.png) |

---

## How It Works

![Pipeline diagram](docs/architecture.png)

### 1. AI Image Detection

Fine-tuned **EfficientNet-B0** on the **CIFAKE** dataset (60k real vs. AI-generated
32×32 images upsampled to 224×224).

Training transforms include `RandomResizedCrop`, `RandomHorizontalFlip`,
`ColorJitter`, and — critically for real-world robustness —
`RandomJPEGCompression(60-95)` to harden the detector against the
re-encoding that happens whenever a generated image passes through a
social platform.

Interpretability is provided by Grad-CAM on the last conv block (and
attention rollout for the ViT variant).

| Metric | CIFAKE test (n = 20,000) |
|---|---|
| Accuracy  | **98.25%** |
| F1 score  | **98.23%** |
| Precision | **98.97%** |
| Recall    | **97.50%** |
| AUC       | **0.9987** |

OOD evaluation on hand-collected Midjourney / Flux / DALL-E 3 samples is
honest about generalization drop — see `eval_results/ood_metrics.json`
after running notebook 03.

### 2. Tampering Detection

Three classical computer-vision techniques, fused with weights `0.4 / 0.4 / 0.2`:

- **Error Level Analysis** — re-encode at JPEG q=90, take per-pixel
  absolute difference vs. the original, then compute the
  max-to-mean ratio of sliding-window std deviations. Authentic images
  have spatially-uniform compression error; spliced regions spike.
- **Noise residual analysis** — image minus 5×5 Gaussian blur,
  projected to luminance. Compute per-block std across an 8×8 grid;
  return the coefficient of variation. Spliced regions imported from a
  different camera carry foreign noise statistics.
- **Copy-move detection** — SIFT descriptors matched against themselves,
  filtered by Lowe's ratio test (0.7) and a 40 px spatial-distance
  threshold. Many surviving pairs ⇒ likely cloned region.

Fixture results from `tests/`:

| Image | ELA | Noise | Copy-move | **Combined** | Verdict |
|---|---|---|---|---|---|
| Authentic landscape | 1.29 | 0.65 | 0 | **0.260** | untampered |
| Authentic portrait  | 1.26 | 0.05 | 0 | **0.096** | untampered |
| Tampered composite  | 4.47 | 1.54 | 0 | **0.698** | tampered |
| Copy-move sample    | 4.18 | 1.59 | 28 | **0.879** | tampered |

### 3. Scene Understanding

Three pretrained backbones, each loaded once via `@st.cache_resource`:

- **YOLOv8 nano** (`ultralytics`) for object detection, confidence floor 0.4.
- **CLIP ViT-B/32** (`transformers`) for zero-shot scene classification
  against a 12-label set covering indoor/outdoor, portrait, landscape,
  document, screenshot, artwork, product, food, animal, etc.
- **EasyOCR** for text extraction, confidence floor 0.5.

### 4. Metadata Forensics

- EXIF / IPTC parsing via Pillow's `getexif()` (including the Exif IFD).
- JPEG quality estimate reverse-engineered from libjpeg's Annex K
  quantization-table scaling formula.
- Rule-based anomaly flags with severity `{low, medium, high}`:
  missing EXIF, editor-software fingerprints
  (Photoshop / Lightroom / Midjourney / Stable Diffusion / Flux …),
  date-modified drift, missing camera Make/Model, low estimated JPEG
  quality, atypical quantization-table count.
- Anomaly score is a saturating severity-weighted sum, clipped to `[0, 1]`.

### Verdict Layer

- `LogisticRegression(class_weight="balanced")` for interpretable
  coefficients.
- `CalibratedClassifierCV(method="sigmoid", cv=5)` for calibrated
  probability output (Platt scaling).
- Contributing factor = `coefficient × feature_value`, ranked by
  absolute magnitude.
- Plain-English explanation per factor, keyed off the feature value
  (not the sign of contribution, which can be misleading when all
  coefficients share the same sign).

---

## Results

Per-pipeline numbers above. The meta-classifier was trained on a synthetic
600-row CSV (`data/meta_classifier_training.csv`) sampled from
plausible per-class beta distributions until the AI-detector checkpoint
and richer labeled training data land. Coefficients with the expected
signs:

| Feature | Coefficient |
|---|---|
| `ai_conf` | -6.08 |
| `tampering_score` | -4.79 |
| `metadata_score` | -4.68 |
| `has_text` | +0.17 |

See `eval_results/calibration_meta.png` for the reliability diagram and
`eval_results/meta_classifier_summary.json` for the full metrics dump.

### Sample analyses

| Image | P(authentic) | Verdict | Top contributing factor |
|---|---|---|---|
| Authentic landscape | 0.99 | authentic | tampering analysis (low) |
| Clearly AI (synthetic) | 0.01 | fake | AI detector (high) |
| Clearly tampered (composite) | 0.00 | fake | tampering analysis (high) |
| Borderline + text | 0.02 | fake | AI detector (medium) — text-content caveat surfaced |

---

## Limitations

- **OOD evaluation pending.** The OOD-test split (Midjourney / Flux /
  DALL-E 3 hand-collected samples) and per-generator accuracy table
  documented in notebook 03 have not been produced yet. Until they are,
  treat any claim of cross-generator generalization as unvalidated.
- **Detector trained on CIFAKE — may underperform on newer generators.**
  CIFAKE is mostly older diffusion at 32×32 upsampled to 224×224. Expect
  noticeably degraded performance on Flux, Imagen 3, Midjourney v6+, SDXL,
  and any other generator whose artifact statistics differ from the CIFAKE
  training distribution.
- **Metadata pipeline is rule-based, not exhaustive.** Anomaly detection
  is a hand-curated set of rules (missing EXIF, editor-software
  fingerprints, date drift, low quantization-table quality, etc.). It does
  not learn from data, does not cover every editor or generator, and
  *absence* of metadata is treated as a flag, not proof — stripping EXIF
  is trivial.
- **Tampering detection is post-hoc** — it sees only the pixels, so
  sophisticated edits with consistent compression and noise can fool
  all three methods.
- **The meta-classifier was trained on synthetic distributions.** Once
  the AI detector checkpoint exists and a labeled set of ~100 images
  has been scored by all four pipelines, retraining is a one-command
  refresh (`python -c "from Aperture.verdict.meta_classifier import main; main()"`)
  with no other code changes.
- **No video.** A future audio + temporal-consistency module would
  extend this to deepfake video.
- **No attention-based fusion** — current fusion is linear. A small
  transformer over per-pipeline tokens could learn nonlinear
  interactions between signals.

---

## Stack

- **ML / CV:** PyTorch 2.1, torchvision, transformers 4.36, ultralytics
  8.1 (YOLOv8), OpenCV 4.9, scikit-learn 1.4, pytorch-grad-cam, EasyOCR.
- **App:** Streamlit 1.31 with a custom dark theme (Fraunces + Inter via
  Google Fonts, 12 px rounded cards, SVG confidence donut).
- **Eval / training:** matplotlib, joblib, tqdm, pandas, numpy.
- **Dev:** pytest, mypy, Playwright (for headless screenshot capture).

---

## Run Locally

Python 3.10 recommended (matches deployment runtime).

```bash
git clone https://github.com/Nandann018-ux/Aperture.git
cd Aperture
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

First run downloads YOLOv8n (~6 MB), CLIP ViT-B/32 (~150 MB), and EasyOCR
weights (~100 MB) into your OS caches. Subsequent runs reuse them.

### Optional: train the AI detector

The CIFAKE detector is trained in `notebooks/02_detector_training.ipynb`,
designed to run on Colab with a T4 GPU. Drop the resulting
`models/ai_detector_best.pt` back into the repo to unlock the AI
Detection tab end-to-end.

### Optional: retrain the meta-classifier on real features

```bash
python -c "from Aperture.verdict.meta_classifier import main; main()"
```

Reads `data/meta_classifier_training.csv`, fits an LR + Platt-scaled
classifier, writes `models/meta_classifier.pkl` and
`eval_results/calibration_meta.png`.

---

## Tests

```bash
pytest tests/
```

26 unit tests covering ELA, noise, copy-move, tampering fusion, and the
meta-classifier (including round-tripping the pickle, ranking by
contribution, and explanation coverage).

End-to-end UI smoke (boots Streamlit, cycles through all 6 example
images, asserts all 6 tabs render without exceptions):

```bash
python scripts/smoke_app.py
```

Headless screenshot regeneration (used for the README images above):

```bash
python scripts/capture_screenshots.py
```

---

## Project Structure

```
Aperture/
├── app.py                     # Streamlit entry point
├── Aperture/
│   ├── ai_detector/           # CNN/ViT-based AI generation detector + Grad-CAM
│   ├── tampering/             # ELA, noise, copy-move, weighted fusion
│   ├── scene/                 # YOLO + CLIP + EasyOCR
│   ├── metadata/              # EXIF + JPEG quality + anomaly rules
│   ├── verdict/               # Calibrated meta-classifier + explanations
│   ├── ui/                    # Streamlit theme + components + tab renderers
│   └── utils/                 # Image IO + visualization helpers
├── tests/                     # pytest suite
├── notebooks/                 # Training + evaluation (Colab-aware)
├── examples/                  # Curated example images
├── eval_results/              # Saved metrics, plots, pipeline diagram
├── docs/                      # README assets (architecture, screenshots)
├── requirements.txt           # Production deps (Streamlit Cloud)
├── requirements-dev.txt       # Adds pytest, mypy, playwright, seaborn
└── runtime.txt                # Python 3.10 (Streamlit Cloud)
```

---

## About

**Nandan Acharya** — built as a portfolio project to demonstrate
end-to-end ML system design: from dataset to training to interpretability
to UI to deployment.

- GitHub: <https://github.com/Nandann018-ux>
- LinkedIn: _add your URL here_
