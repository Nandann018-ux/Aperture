# UI_LIMITATIONS.md

The Aperture Streamlit UI clones a Claude Design HTML/CSS/JS handoff
(`/tmp/ap-target/`, original `~/Downloads/Aperture.zip`). The brief
target is **~80 % visual fidelity to the design, 100 % functional
integrity**. Streamlit cannot pixel-match an arbitrary HTML prototype;
this file documents every deliberate gap so future readers know what is
intentional vs broken.

If you find yourself reopening this file to make a border 1 px closer
to the design — stop. That's the signal you've hit Streamlit's limit
and you should be documenting the gap, not chasing it.

## What we accept as-is

### 1. The DOM is Streamlit's, not the design's
The design's HTML uses `<aside class="sidebar">`, `<div class="hero">`,
`<button class="btn primary">`, etc. We **do not** rebuild that
structure. We work with Streamlit's emitted DOM and target
`[data-testid="…"]` selectors only. Consequences:

- We can't position elements with `position: absolute` based on a
  parent the design assumes exists.
- Streamlit wraps every widget in `element-container > stMarkdown >
  stMarkdownContainer > p`. Our CSS strips margin/padding off these
  wrappers where it would otherwise add unwanted gaps, but a perfect
  match isn't possible — Streamlit can change those wrappers at any
  point release and we'd need to re-tune.
- Streamlit's `st.columns()` produces `stHorizontalBlock`, not another
  `element-container`. Selectors that walk siblings need to know the
  difference (see `theme.py` hero-CTA block).

### 2. Some widgets render in iframes (`components.html`)
Two pieces use `components.html(...)`:

| Component | Why an iframe |
|-----------|---------------|
| `example_tile_grid_iframe(...)` | Streamlit's `st.button` chrome (BaseWeb internals, primary/secondary states, padding, focus rings) couldn't be reliably overridden into the design's image-thumbnail tile look. The iframe renders 6 styled `<button>` elements; clicks navigate `window.parent` to `?example=<label>`, which Streamlit re-reads via `st.query_params`. |
| `pipeline_diagram_doc()` | The SVG was fragile when inlined via `st.markdown` (Streamlit's React markdown pipeline occasionally choked on comments / attribute order). The iframe ships the same SVG with a minimal self-contained stylesheet. |

These iframes are intentionally non-sandboxed (we use `allow-scripts +
allow-same-origin`) because they need to read/write parent location.
The browser logs an INFO message about this — it's expected.

### 3. File uploader chrome leaks if Streamlit changes testids
We hide Streamlit's native "Drag and drop file here" / "Limit 200MB
per file" / "Browse files" via `display: none !important` on
`[data-testid="stFileDropzoneInstructions"] *` and the dropzone
button. We then synthesise the design's compact "Drop an image or
click to browse" + size hint via `::before` / `::after`.

If Streamlit renames the testid (it already did once —
`stFileUploaderDropzoneInstructions` → `stFileDropzoneInstructions`),
the chrome will reappear until we update the selector. Watch for
Streamlit minor-version bumps.

### 4. Stats tile
The design shows three stats on the landing hero:
**Avg. analysis time**, **Held-out accuracy**, **Out-of-dist accuracy**.

| Slot | Design value | Our value | Source |
|------|--------------|-----------|--------|
| Avg. analysis time | `8.4s` | `~8s` | Operational estimate. Not benchmarked per-image yet. Honest framing: "warm-cache · 1024² input". |
| Held-out accuracy  | `94.1 %` | bound to `test_accuracy` in `eval_results/cifake_metrics.json` (`98.25 %`) | Real |
| Out-of-dist acc.   | `78.6 %` | replaced with **Test AUC** bound to `test_auc` (`0.999`) | Real. OOD-on-MJ/Flux/DALL·E 3 is **not** measured in this repo; we surface a real metric instead of inventing a number. |

### 5. Sidebar can collapse
We hide Streamlit's sidebar `X` collapse button so users can't
accidentally hide the brand wordmark + uploader. If the user
explicitly wants to collapse, the keyboard shortcut still works.

### 6. Slider thumb has no value-bubble
The design slider shows the value to the right of the field label
(e.g. `Tampering sensitivity  0.50`). Streamlit's `st.slider` also
shows the value above the thumb on drag. We hide that bubble (it
duplicates the label). Users still see the value live in the label
because we render it ourselves.

### 7. Toggle pill orientation
The design has the label on the left, switch on the right. Streamlit's
native `st.toggle` puts the switch on the left. We force
`flex-direction: row-reverse` on the wrapper. If Streamlit changes the
testid (we currently target both `stToggle` and `stCheckbox`), the
toggle will revert to switch-left until the selector is updated.

## What we DO NOT do (and why)

- **Don't recreate widgets.** No custom file-uploader, no custom
  slider, no custom selectbox. Restyle, never replace. (Exception:
  the three iframes above, where there is no Streamlit equivalent.)
- **Don't add `!important` everywhere.** Use it surgically on
  selectors that compete with Streamlit / BaseWeb internals.
- **Don't fight Plotly.** Plotly's theming is internal and we accept
  the post-toggle freeze as a known limitation rather than rebuilding
  charts in raw SVG.

## How to verify

```bash
streamlit run app.py --server.port 8501 --server.headless true
```

Open http://localhost:8501. The app is light-only. Click any sidebar
example tile to load that example into the analysis pipeline.

For headless visual diffing:
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=1440,1400 --virtual-time-budget=35000 \
  --user-data-dir=/tmp/cp-light \
  --screenshot=/tmp/app-light.png 'http://localhost:8501/'
```
