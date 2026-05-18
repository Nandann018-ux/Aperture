# Aperture

Image forensic analysis toolkit deployed as a Streamlit app.

## Quickstart

```bash
pip install -r requirements.txt
streamlit run app.py
```

Requires Python 3.10+.

## Structure

- `app.py` — Streamlit entry point
- `Aperture/` — library code (AI detection, tampering, scene, metadata, verdict, UI, utils)
- `notebooks/` — exploration, training, evaluation notebooks
- `tests/` — pytest suite
- `examples/` — curated example images
- `data/`, `models/`, `eval_results/` — local artifacts
