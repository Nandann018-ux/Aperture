"""Generate synthetic placeholder example images for the tampering pipeline.

These are NOT visually realistic — they're algorithmic test fixtures that
exercise each detector. Replace with real photos / AI images for the demo.

Run from the repo root:
    python examples/generate_synthetic.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent
SIZE = 384
RNG = np.random.default_rng(0)


def _add_camera_noise(arr: np.ndarray, sigma: float = 3.0) -> np.ndarray:
    noise = RNG.normal(0, sigma, arr.shape).astype(np.float32)
    return np.clip(arr.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def authentic_landscape() -> Image.Image:
    """Smooth sky-to-ground gradient with uniform sensor noise."""
    y = np.linspace(0, 1, SIZE, dtype=np.float32)[:, None]
    sky = np.stack([
        135 + 80 * (1 - y) ** 1.4,    # R
        180 + 50 * (1 - y) ** 1.4,    # G
        220 - 40 * y,                  # B
    ], axis=-1)
    sky = np.broadcast_to(sky, (SIZE, SIZE, 3)).copy()
    # Subtle ground band
    sky[int(SIZE * 0.7):] *= 0.6
    return Image.fromarray(_add_camera_noise(sky))


def authentic_portrait() -> Image.Image:
    """Smooth radial vignette over a flesh-tone field, uniform noise."""
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32) - SIZE / 2
    r = np.sqrt(x * x + y * y) / (SIZE / 2)
    vignette = np.clip(1.0 - 0.35 * r, 0.3, 1.0)[..., None]
    skin = np.array([212, 175, 145], dtype=np.float32)
    arr = (skin * vignette).astype(np.float32)
    arr = np.broadcast_to(arr, (SIZE, SIZE, 3)).copy()
    return Image.fromarray(_add_camera_noise(arr))


def tampered_composite() -> Image.Image:
    """Authentic-style base with a noisy, sharply-bounded patch pasted in.

    Different noise sigma and a hard JPEG-misaligned boundary => both
    ELA and noise-inconsistency detectors should fire.
    """
    base = np.asarray(authentic_landscape()).copy()
    foreign_rng = np.random.default_rng(123)
    foreign = foreign_rng.integers(40, 220, size=(120, 120, 3), dtype=np.int16).astype(np.uint8)
    # paste off-grid so JPEG 8x8 blocks misalign
    base[80:200, 100:220] = foreign
    return Image.fromarray(base)


def copy_move_obvious() -> Image.Image:
    """Smooth background with one richly-textured region duplicated.

    SIFT picks keypoints on the texture; the duplicate triggers matches.
    """
    base = np.full((SIZE, SIZE, 3), 200, dtype=np.uint8)
    base = _add_camera_noise(base, sigma=4)
    tex_rng = np.random.default_rng(7)
    texture = tex_rng.integers(20, 235, size=(80, 80, 3), dtype=np.int16).astype(np.uint8)
    base[60:140, 60:140] = texture
    base[220:300, 240:320] = texture  # exact duplicate
    return Image.fromarray(base)


def ai_placeholder(label: str) -> Image.Image:
    """Plain placeholder so the file exists. Replace with a real AI image."""
    img = np.full((SIZE, SIZE, 3), 230, dtype=np.uint8)
    img = _add_camera_noise(img, sigma=1)
    pil = Image.fromarray(img)
    return pil


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "authentic_landscape.jpg": authentic_landscape(),
        "authentic_portrait.jpg":  authentic_portrait(),
        "tampered_composite.jpg":  tampered_composite(),
        "copy_move_obvious.jpg":   copy_move_obvious(),
        "ai_midjourney.jpg":       ai_placeholder("midjourney"),
        "ai_realistic.jpg":        ai_placeholder("realistic"),
    }
    for name, img in files.items():
        path = OUT / name
        img.save(path, format="JPEG", quality=92)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
