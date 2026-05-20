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

> **Live demo:** <https://nandann018-aperture-forensics.hf.space>

A multi-signal forensic verdict system for images. Four independent pipelines run in
parallel — generative-origin detection, classical tampering analysis, scene
understanding, and metadata inspection — and a Platt-calibrated meta-classifier
fuses them into a single authenticity probability with ranked, plain-English
explanations.

![Aperture welcome screen](docs/screenshots/welcome.png)

---

## Why multi-signal

Single-signal detectors lose on the long tail. An AI detector alone misses
Photoshop composites; EXIF inspection alone is defeated by a single re-encode;
a tampering detector alone misses born-digital generation.

Aperture is built on the premise that **multiple weak signals fused with proper
calibration beat any single strong signal**. Every verdict surfaces which
signals moved it and by how much, so users (and reviewers) can spot
over-reliance on any one pipeline.

---

## Interface

### Verdict and AI detection

| Verdict — fused probability + ranked factors | AI Detection — Grad-CAM heatmap |
|:--:|:--:|
| ![Verdict tab](docs/screenshots/verdict.png) | ![AI Detection heatmap](docs/screenshots/ai_detection.png) |

### Tampering and scene

| Tampering Analysis — ELA, noise, copy-move | Scene Understanding — YOLO + CLIP + OCR |
|:--:|:--:|
| ![Tampering analysis](docs/screenshots/tampering.png) | ![Scene parsing](docs/screenshots/scene.png) |

### Metadata and model performance

| Metadata Forensics — EXIF + JPEG + anomaly rules | Model Performance — held-out metrics |
|:--:|:--:|
| ![Metadata flags](docs/screenshots/metadata.png) | ![Held-out metrics](docs/screenshots/performance.png) |

---

## How it works

![Pipeline diagram](docs/architecture.png)

### 1 · Generative-origin detection

Fine-tuned **EfficientNet-B0** trained on **CIFAKE** (60k real vs. AI-generated
images), hardened with `RandomJPEGCompression(60–95)` against the re-encoding
that happens whenever a generated image passes through a social platform.
**Grad-CAM** on the final conv block exposes the regions the model attended to.

| Metric | CIFAKE held-out (n = 20 000) |
|---|---|
| Accuracy | **98.25 %** |
| F1 | **98.23 %** |
| Precision | **98.97 %** |
| Recall | **97.50 %** |
| AUC | **0.9987** |

### 2 · Classical tampering analysis

Three computer-vision techniques fused with weights `0.4 / 0.4 / 0.2`:

- **Error Level Analysis** — re-encode at JPEG q=90, max-to-mean ratio of
  sliding-window standard deviations. Spliced regions spike against the
  spatially-uniform compression error of authentic captures.
- **Noise residual** — image minus 5×5 Gaussian blur, projected to luminance;
  per-block standard deviation across an 8×8 grid. Spliced regions carry foreign
  noise statistics.
- **Copy-move detection** — SIFT descriptors matched against themselves, filtered
  by Lowe's ratio test (0.7) and a 40 px spatial-distance threshold. Many
  surviving pairs ⇒ likely cloned region.

| Image | ELA | Noise | Copy-move | **Combined** |
|---|---|---|---|---|
| Authentic landscape | 1.29 | 0.65 | 0 | **0.260** |
| Authentic portrait | 1.26 | 0.05 | 0 | **0.096** |
| Tampered composite | 4.47 | 1.54 | 0 | **0.698** |
| Copy-move sample | 4.18 | 1.59 | 28 | **0.879** |

### 3 · Scene understanding

- **YOLOv8 nano** (`ultralytics`) for object detection, confidence floor 0.4.
- **CLIP ViT-B/32** (`transformers`) for zero-shot scene classification across a
  12-label set (indoor/outdoor, portrait, landscape, document, screenshot,
  artwork, product, food, animal, …).
- **EasyOCR** for on-image text extraction, confidence floor 0.5. Surfaces a
  "verdict less reliable" caveat when text-heavy content is detected.

### 4 · Metadata forensics

- EXIF / IPTC parsing via Pillow's `getexif()` (including the Exif IFD).
- JPEG quality reverse-engineered from libjpeg's Annex K quantization-table
  scaling formula.
- Rule-based anomaly flags with severity `{low, medium, high}`: missing EXIF,
  editor-software fingerprints (Photoshop / Lightroom / Midjourney / Stable
  Diffusion / Flux), date-modified drift, missing camera Make/Model, low
  estimated JPEG quality, atypical quantization-table count.
- Anomaly score is a saturating severity-weighted sum, clipped to `[0, 1]`.

### Verdict fusion

- `LogisticRegression(class_weight="balanced")` for interpretable coefficients.
- `CalibratedClassifierCV(method="sigmoid", cv=5)` for calibrated probability
  output (Platt scaling).
- Contributing factor = `coefficient × feature_value`, ranked by absolute
  magnitude.
- A plain-English explanation is rendered per factor, keyed off the feature
  *value* (not the sign of the contribution, which can mis-narrate when all
  coefficients share a sign).

| Feature | Coefficient |
|---|---|
| `ai_conf` | -6.08 |
| `tampering_score` | -4.79 |
| `metadata_score` | -4.68 |
| `has_text` | +0.17 |

Calibration plot: `eval_results/calibration_meta.png` · full metrics dump:
`eval_results/meta_classifier_summary.json`.

---

## Sample verdicts

| Image | P(authentic) | Verdict | Top contributing factor |
|---|---|---|---|
| Authentic landscape | 0.99 | authentic | tampering analysis (low) |
| AI-generated (synthetic) | 0.01 | fake | AI detector (high) |
| Tampered composite | 0.00 | fake | tampering analysis (high) |
| Borderline + text | 0.02 | fake | AI detector (medium) — text caveat surfaced |

---

## Limitations

- **OOD evaluation pending.** Cross-generator metrics on hand-collected
  Midjourney / Flux / DALL-E 3 samples have not been produced. Until they are,
  treat any claim of cross-generator generalization as unvalidated.
- **CIFAKE-trained detector may underperform on newer generators.** CIFAKE is
  primarily older diffusion at 32×32 upsampled to 224×224. Expect degraded
  performance on Flux, Imagen 3, Midjourney v6+, SDXL, and any generator whose
  artifact statistics differ from the CIFAKE training distribution.
- **Metadata pipeline is rule-based, not learned.** It does not cover every
  editor or generator, and *absence* of metadata is treated as a flag, not
  proof — stripping EXIF is trivial.
- **Tampering detection is post-hoc.** It sees only the pixels, so sophisticated
  edits with consistent compression and noise can fool all three methods.
- **The meta-classifier was trained on synthetic distributions.** Once a
  labeled set scored end-to-end by all four pipelines is available, retraining
  is a single command.
- **No video.** A future audio + temporal-consistency module would extend this
  to deepfake video.
- **No attention-based fusion.** Current fusion is linear. A small transformer
  over per-pipeline tokens could learn nonlinear interactions between signals.

---

## Stack

- **ML / CV:** PyTorch 2.1, torchvision, transformers 4.36, ultralytics 8.1
  (YOLOv8), OpenCV 4.9, scikit-learn 1.4, pytorch-grad-cam, EasyOCR.
- **App:** Streamlit 1.31 with a custom light forensic-lab theme (Source Serif 4
  + Inter + JetBrains Mono via Google Fonts).
- **Eval / training:** matplotlib, joblib, tqdm, pandas, numpy.
- **Dev:** pytest, mypy, Playwright (headless screenshot capture).

---

## Run locally

Python 3.10 recommended (matches the deployment runtime).

```bash
git clone https://github.com/Nandann018-ux/Aperture.git
cd Aperture
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py
```

First run downloads YOLOv8n (~6 MB), CLIP ViT-B/32 (~150 MB), and EasyOCR
weights (~100 MB) into the OS cache. Subsequent runs reuse them.

### Retrain the meta-classifier

```bash
python -c "from Aperture.verdict.meta_classifier import main; main()"
```

Reads `data/meta_classifier_training.csv`, fits an LR + Platt-scaled classifier,
and writes `models/meta_classifier.pkl` + `eval_results/calibration_meta.png`.
The deployed app rebuilds this on first cold start, so the pickle does not need
to be checked in.

### Train the AI detector

The CIFAKE detector is trained in `notebooks/02_detector_training.ipynb`
(Colab-aware, T4 GPU). Drop the resulting `models/ai_detector_best.pt` back
into the repo (or publish it as a GitHub Release asset) to unlock the AI
Detection tab end-to-end.

---

## Deployment

The repo ships with a Docker target tuned for **Hugging Face Spaces**
(`python:3.10-slim` base, opencv / torch system libraries, Streamlit on port
7860). The YAML frontmatter at the top of this file is the Space's
configuration.

```bash
docker build -t aperture .
docker run -p 7860:7860 aperture
```

---

## Tests

```bash
pytest tests/                            # 26 unit tests
python scripts/smoke_app.py              # end-to-end UI boot
python scripts/capture_screenshots.py    # regenerate README images
```

---

## Project structure

```
Aperture/
├── app.py                     # Streamlit entry point
├── Dockerfile                 # HF Spaces Docker target
├── Aperture/
│   ├── ai_detector/           # CNN-based AI-generation detector + Grad-CAM
│   ├── tampering/             # ELA, noise, copy-move, weighted fusion
│   ├── scene/                 # YOLO + CLIP + EasyOCR
│   ├── metadata/              # EXIF + JPEG quality + anomaly rules
│   ├── verdict/               # Calibrated meta-classifier + explanations
│   ├── ui/                    # Streamlit theme + components + tab renderers
│   └── utils/                 # Image IO + visualization helpers
├── tests/                     # pytest suite
├── notebooks/                 # Training + evaluation
├── examples/                  # Curated example images
├── eval_results/              # Saved metrics, plots, pipeline diagram
├── docs/                      # README assets (architecture, screenshots)
├── requirements.txt           # Production deps
├── requirements-dev.txt       # Adds pytest, mypy, playwright, seaborn, easyocr
└── runtime.txt                # Python 3.10
```

---

## License

MIT — see [`LICENSE`](LICENSE).
