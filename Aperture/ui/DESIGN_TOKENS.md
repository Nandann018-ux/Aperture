# Aperture — Design System (extracted from `Aperture.html`)

Source of truth: `/tmp/aperture-design2/aperture/project/src/{tokens.css,screens.css,*.jsx}`
extracted from the design handoff bundle (`enyzXjKF7VdaztfPGj96Iw`). This
document is the contract between the design and the Streamlit
restyling layer — every value below is what we apply to the existing
Streamlit component tree via CSS injection. We **do not** recreate the
design's DOM.

---

## 1. Color tokens

| Role                | Token             | Value                          | Notes |
|---------------------|-------------------|--------------------------------|-------|
| Background          | `--bg`            | `#0A0E14`                      | Deep blue-black, not pure black |
| Surface (card)      | `--surface-1`     | `#141A22`                      | Cards, sidebar background |
| Surface (raised)    | `--surface-2`     | `#1C242E`                      | Viz tiles, code blocks |
| Surface (highest)   | `--surface-3`     | `#232C38`                      | Scrollbar thumb |
| Border (default)    | `--border`        | `#232C38`                      | Hairlines, card outlines |
| Border (strong)     | `--border-strong` | `#2E3845`                      | Inputs, dashed uploader, focus rim |
| Border (soft)       | `--border-soft`   | `#1A2028`                      | Sub-surface dividers |
| Text primary        | `--text`          | `#ECEFF4`                      | Headings, big numbers |
| Text dim            | `--text-dim`      | `#B5BDC9`                      | Body, lede paragraphs |
| Text muted          | `--text-muted`    | `#7B8593`                      | Card summaries |
| Text faint          | `--text-faint`    | `#4F5867`                      | Labels, micro-copy, ticks |
| Accent              | `--accent`        | `#6FA8DC`                      | Cool electric blue, primary CTAs, verdict-bar |
| Accent dim          | `--accent-dim`    | `#4F7FAB`                      | Toggle "on" background |
| Accent soft         | `--accent-soft`   | `rgba(111,168,220,0.12)`       | Selection, tab-chip active |
| Accent line         | `--accent-line`   | `rgba(111,168,220,0.32)`       | Hover borders |
| Authentic           | `--authentic`     | `#7FB89A`                      | Muted sage; "Likely authentic" verdict |
| Suspicious          | `--suspicious`    | `#E8C57A`                      | Warm amber; "Suspicious" verdict |
| Fake                | `--fake`          | `#E07A5F`                      | Muted coral; "Likely fake" verdict |
| Authentic soft      | `--authentic-soft`| `rgba(127,184,154,0.12)`       | Confidence-zone fill, glow |
| Suspicious soft     | `--suspicious-soft`| `rgba(232,197,122,0.12)`      | Confidence-zone fill, glow |
| Fake soft           | `--fake-soft`     | `rgba(224,122,95,0.12)`        | Confidence-zone fill, glow |

**Heatmap gradient** (Grad-CAM overlay, signal-card AI viz):
fake → suspicious → accent, blending from hot center to cool fade-out.

---

## 2. Typography tokens

| Role         | Family stack                                                                 | Size      | Weight | Tracking      | Notes |
|--------------|------------------------------------------------------------------------------|-----------|--------|---------------|-------|
| Display h1   | `"Source Serif 4", "Source Serif Pro", "Spectral", Georgia, serif`           | 56 px     | 600    | -0.018em      | Hero headline; italic `em` allowed for emphasis |
| Display num  | same                                                                         | 96 px     | 600    | -0.03em       | Verdict probability big number; `font-feature-settings: "tnum"` |
| Display sig  | same                                                                         | 36 px     | 600    | -0.02em       | Signal-card big numbers |
| h2 (section) | same                                                                         | 22 px     | 600    | -0.005em      | Section heads ("Forensic signals", "How it works") |
| h3           | same                                                                         | 17 px     | 600    | -             | Dim-card titles |
| Body lede    | `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`         | 14.5 px   | 400    | -             | Line-height 1.6, max-width 620 px |
| Body         | Inter stack                                                                  | 13 px     | 400    | -             | Default UI text |
| Body small   | Inter stack                                                                  | 12.5 px   | 400    | -             | Card summaries |
| Caption      | Inter stack                                                                  | 12 px     | 500    | -             | Toggle labels |
| Label        | Inter stack                                                                  | 10.5 px   | 600    | +0.14em       | UPPERCASE; section eyebrows, card heads |
| Tracked tiny | `"JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace`                 | 9.5–10 px | 500    | +0.04–0.22em  | UPPERCASE; build IDs, tile labels, tick marks |
| Mono data    | JetBrains Mono stack                                                         | 11 px     | 400    | +0.04em       | File paths, log lines, code chips; `"tnum", "zero"` |
| Kbd badge    | JetBrains Mono stack                                                         | 10 px     | 400    | -             | CTA `↵` hint chip |

CSS variables:
```css
--font-display: "Source Serif 4", "Source Serif Pro", Georgia, serif;
--font-ui:      "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono:    "JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace;
```

---

## 3. Spacing system

Strict **4-pt grid**. Exposed as variables for indirection; raw px is fine
when CSS clarity benefits.

| Token   | Value | Common uses |
|---------|-------|-------------|
| `--s-1` | 4 px  | Inner gaps, brand-mark dot offset |
| `--s-2` | 8 px  | Tile gap, eyebrow gap |
| `--s-3` | 12 px | Card foot padding, button gap |
| `--s-4` | 16 px | Grid gap, card padding-top |
| `--s-6` | 24 px | Section gaps, card column gap |
| `--s-8` | 32 px | Main content padding, between sections |
| `--s-12`| 48 px | Verdict-block column gap |
| `--s-16`| 64 px | Hero-bottom margin, stats trio gap |

Main content padding: **40 px** (between sidebar's right edge and content
gutter). Cards use **22 px** padding internally (slightly under the 24 px
step — keep this exact value, it's been tuned).

---

## 4. Border + radius

- **Border weight**: `1px solid` is default; `0.5px` for sub-divisions in
  charts, `1.5px` for tab underline + final-marker.
- **Border-radius**:
  - `2px` — buttons, tiles, code blocks, slider thumb-track joint
  - `3px` — cards, surface containers, verdict block
  - `4px` — uploader dashed box only
  - `999px` — toggle pill, verdict pill, meter track
- Dashed/striped fills: `repeating-linear-gradient(135deg, transparent 0 6px, rgba(255,255,255,0.012) 6px 7px)` over `--surface-1` for the uploader; `1px dashed --border-strong` for the outer ring.

---

## 5. Shadow + elevation

The design is **flat by default** — no large shadows. Two micro-shadow patterns:

| Where                | Shadow                                                  |
|----------------------|---------------------------------------------------------|
| Active brand-mark dot| `0 0 0 4px rgba(111,168,220,0.10)`                      |
| Slider thumb         | `0 0 0 4px rgba(111,168,220,0.10)`                      |
| Build-status dot     | `0 0 0 3px rgba(127,184,154,0.12)`                      |
| Iris-label running   | `0 0 0 3px rgba(232,197,122,0.15)`                      |
| Iris-label done      | `0 0 0 3px rgba(127,184,154,0.15)`                      |
| Card hover (lift)    | None in design. Use only `border-color` transition + optional `translateY(-2px)` |

The "glow" behind the verdict probability is a `radial-gradient`, not a
shadow — handled in the component CSS.

---

## 6. Motion

| Token         | Value                              | Notes |
|---------------|------------------------------------|-------|
| `--ease`      | `cubic-bezier(0.4, 0, 0.2, 1)`     | Default for everything |
| `--dur-fast`  | `160ms`                            | Micro states |
| `--dur-base`  | `240ms`                            | Button hover, border transition |
| `--dur-reveal`| `400ms`                            | Content fade-in (`.reveal`, `.fade`) |
| `--dur-slow`  | `680ms`                            | Iris-blade rotation, marker slide |

Forbidden: spring/bounce easings; durations under 100 ms or over 800 ms.

---

## 7. Component anatomies

### 7.1 Sidebar

- Width: **320 px**, sticky, full-height.
- Background: `--surface-1`, right border `1px solid --border`.
- Inner padding: `28px 24px 24px`.
- Sections separated by **28 px** gap.
- Brand-mark: `--font-display` 26 px / 600, dot 9 px (accent + soft halo).
- Sub-tagline: mono 9.5 px / +0.22em / UPPERCASE / `--text-faint`.
- Section header (`h4`): mono 10 px / +0.18em / UPPERCASE / `--text-faint`,
  with a flex `:after` 1px rule.
- Foot row: top border, build-status sage dot (3 px soft halo).

### 7.2 Uploader (dashed input slot)

- `1px dashed --border-strong`, radius 4 px.
- Background: `--surface-1` + 135° stripe overlay (`rgba(255,255,255,0.012)`).
- Inner padding `20px 16px`, flex-column, gap 8 px, centered.
- Glyph: 36×36 outer square (`--border-strong`), upload SVG inside.
- Title: 12 px / `--text-dim`.
- Hint: mono 10 px / `--text-faint` / +0.04em.
- Hover: border becomes `--accent-line`.

### 7.3 Example tile

- 1:1 aspect, `1px solid --border`, radius 2 px.
- Background: per-example linear-gradient(135°) between two specified colors.
- Kind-pip dot top-right (5×5, color from `--authentic/--suspicious/--fake`).
- Label bottom-left, mono 8.5 px / +0.05em / UPPERCASE / `rgba(236,239,244,0.85)`.
- Hover: border → `--accent-line`.
- **Selected**: `1px solid --accent` + `0 0 0 1px --accent, 0 0 0 4px rgba(111,168,220,0.10)`.

### 7.4 Button — primary

- Background `--accent`, text `#0a0e14`, border `1px solid --accent`.
- Padding `9–10px 14–18px`, radius 2 px.
- Font: UI 11.5 px / 500 / +0.04em.
- Hover: bg `#8ABBE5` (one-step lighter), border matches.
- Optional `.kbd` chip suffix: mono 10 px, dark bg `rgba(10,14,20,0.18)`.

### 7.5 Button — secondary

- Background `--surface-1`, text `--text`, border `1px solid --border-strong`.
- Same padding/radius/font as primary.
- Hover: bg `--surface-2`, border → `--accent-line`.

### 7.6 Card (generic surface)

- Background `--surface-1`, border `1px solid --border`, radius 3 px.
- Hover (when interactive): border → `--border-strong`. No shadow lift.

### 7.7 Signal card (verdict tab)

- Layout: CSS grid `1fr | 132px`; foot `grid-column: 1 / -1`.
- Outer padding: `22px 22px 18px`.
- Title row: mono 10 px / +0.16em / UPPERCASE; status-dot 7×7 inline.
- Big number: `--font-display` 36 px / 600 / `-0.02em` / `tnum`.
- Unit suffix: mono 14 px / `--text-muted`.
- Summary: 12.5 px / `--text-dim` / line-height 1.5.
- `.viz` tile: aspect-1, `--surface-2`, `1px solid --border`. 132 px wide.
- Foot: top border, mono 9.5 px / +0.06em; "investigate →" right-aligned in `--accent`.

### 7.8 Verdict block

- Border `1px solid --border`, bg `--surface-1`, radius 3 px.
- Padding `36px 40px`.
- Layout: grid `320px | 1fr`, gap 48 px, items centered.
- Glow: absolutely-positioned 380 px circle behind right column,
  radial-gradient(`--verdict-glow`, transparent 70%); positioned
  `right:-120px; top:-120px`.
- Probability: 96 px serif (color `--verdict-color`), `pct` 28 px / `--text-muted`.
- Label: 28 px serif / 600 / +0.04em / UPPERCASE; 8 px tall colored bar before.
- Confidence band: 28 px tall, 3 zones (30%/40%/30%) with dashed dividers, marker triangle.

### 7.9 Factor row

- Grid `140px | 1fr | 90px`, gap 16 px.
- Name col: mono 10.5 px / +0.04em / UPPERCASE / `--text-dim`.
- Bar wrap: 8 px tall, `--surface-2` background, accent at 50% (`.axis`).
- Bar: colored (`--authentic` for +, `--fake` for −), positioned from 50% by signed delta.
- Explanation: 12 px / `--text-muted` below the bar.
- Delta: mono 13 px, right-aligned, color matches bar; `pp` suffix in `--text-faint`.

### 7.10 Factor stack chart

- Padded card (20×24), SVG height ~110.
- Baseline track: 1 px hairline `--border`.
- Tick marks at 0/25/50/75/100; labels mono 9.5 px / `--text-faint`.
- Segments: signed rects (auth/fake fill at 0.75 opacity).
- Final marker: 1.5 px line in `--verdict-color` + small triangle + `FINAL · X%` label.

### 7.11 Tab bar

- Border-bottom `1px solid --border`; tabs flush, gap 0, padding `0 8px` outer.
- Tab button: UI 11 px / 600 / +0.12em / UPPERCASE / `--text-faint`.
- Padding `12px 14px`, gap 8 px (for inline count chip).
- Active: text `--text`, bottom-border `1.5px solid --accent`.
- Count chip: mono 9.5 px, `--surface-2` bg / `--text-muted`; active variant `--accent-soft` / `--accent`.

### 7.12 Pipeline diagram

- Container: `--surface-1`, `1px solid --border`, padding `28px 32px`.
- SVG: 1080×220 viewBox.
- Input rect: 120×52, `--bg` bg, `--border-strong` outline; "image.jpg" mono.
- 4 stage rows at y=40/90/140/190; left tag, right code in mono.
- Σ fuse circle: 70 px radius, `--surface-2` bg, accent outline; dashed inner ring.
- Verdict box: 140×56, `--bg` bg, accent border + arrow.
- All connector paths: cubic Béziers, `--border-strong` 0.7 px.

### 7.13 Stat tile (hero stats trio)

- Background `--surface-1`, `1px solid --border`, padding `20px 22px`.
- Label: mono 10 px / +0.14em / UPPERCASE / `--text-faint`.
- Value: `--font-display` 30 px / 600 / `-0.01em` / `tnum`.
- Sub-label: mono 10 px / +0.04em / `--text-faint`.

### 7.14 Topbar

- Sticky, full-width, `--bg`.
- Padding `18px 40px`, border-bottom `1px solid --border`.
- Breadcrumb left: mono 11 px / +0.04em / `--text-faint`; separator color `--border-strong`; current page `--text-dim`.
- `.grow` filler in middle.
- Session info right: mono 11 px, items separated by 14 px gap; key values bold + `--text-dim`.

### 7.15 Slider (settings)

- Track: 2 px hairline, `--border-strong`.
- Thumb: 10 px circle, `--accent`, soft halo `0 0 0 4px rgba(111,168,220,0.10)`.
- Label row: mono 10 px / +0.14em / UPPERCASE / `--text-faint` on left,
  value right-aligned in mono 11 px / `--text-dim`.

### 7.16 Toggle (iOS pill)

- Track: 28×16, radius 999 px, `--border-strong`.
- Thumb: 12×12, `--text`, offset 2 px, transitions `transform 240ms`.
- "On" state: track → `--accent-dim`, thumb translates +12 px.

### 7.17 Iris (signature element)

- 8 SVG `<g>` blades, each rotates `-42deg` when "open".
- Closed blade: fill `--surface-2`, stroke `--border-strong` (0.7 op).
- Opening blade: fill `--surface-3`, stroke `--accent` (0.45 op).
- Pupil: radial gradient from accent (0.55) → accent (0) at outer.
- Rim circles: `--border-strong` at 0.7 op (inner) and 0.3 op (outer +6 px).
- Glow (on complete): radial from accent (0.20) → 0.

---

## 8. Real metrics (replacing placeholders)

Source: `eval_results/cifake_metrics.json` + `eval_results/meta_classifier_summary.json`.
Inference latency: measured ad-hoc, see comment in `app.py`.

| Where                              | Old placeholder    | Real value                                |
|------------------------------------|--------------------|-------------------------------------------|
| Hero "Held-out accuracy"           | 94.1%              | **98.25%** (`final_val_acc`)              |
| Hero "Out-of-dist accuracy"        | 78.6%              | Not measured — drop tile OR document gap  |
| Hero "Avg. analysis time"          | 8.4 s              | Measure once, hard-code (≈ 4–10 s typical)|
| AI Detection F1                    | —                  | **0.9823**                                |
| AI Detection AUC                   | —                  | **0.9987**                                |
| AI Detection precision             | —                  | **0.9897**                                |
| AI Detection recall                | —                  | **0.9750**                                |
| Verdict ECE footnote               | 0.029              | **N/A — meta-clf has perfect 1.0 on n=120 test split, document as small-sample caveat** |

Plus: drop "5 anomaly rules" hyperbole; real anomaly rule count is the
length of whatever rule-set actually ships (check `Aperture/metadata/`).

---

## 9. What we DON'T attempt (Streamlit limitations — preview)

Detail goes in `Aperture/ui/UI_LIMITATIONS.md` after Step 5.
Spoilers for what will land there:

- BaseWeb tab indicator transitions can't be replaced.
- The native file_uploader's "Browse files" button shape is fixed.
- Streamlit sliders re-render the whole script on every drag (no
  instant CSS-only response).
- `st.tabs()` adds aria-controlled regions we can't easily restyle to
  match the design's sticky tab strip pixel-for-pixel.

Variance from the design in these areas is **expected** and not a
regression.
