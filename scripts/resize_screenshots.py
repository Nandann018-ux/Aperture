"""Downscale tab screenshots in docs/screenshots/ for README use.

Welcome is left alone (it's the hero shot). Tabs are resized to a
max width of 1100 px and re-saved as optimized PNGs. Typical reduction:
1-2.5 MB → 200-400 KB per file.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

OUT = Path("docs/screenshots")
TAB_FILES = [
    "verdict.png",
    "ai_detection.png",
    "tampering.png",
    "scene.png",
    "metadata.png",
    "performance.png",
]
TARGET_WIDTH = 1100


def main() -> None:
    for fname in TAB_FILES:
        path = OUT / fname
        if not path.exists():
            print(f"[skip] {path} missing")
            continue
        before = path.stat().st_size
        with Image.open(path) as img:
            if img.width <= TARGET_WIDTH:
                print(f"[skip] {fname} already {img.width}px")
                continue
            ratio = TARGET_WIDTH / img.width
            new_h = round(img.height * ratio)
            resized = img.resize((TARGET_WIDTH, new_h), Image.LANCZOS)
            resized.save(path, format="PNG", optimize=True)
        after = path.stat().st_size
        print(f"[resize] {fname}: {before//1024} KB → {after//1024} KB ({TARGET_WIDTH}px)")
    print("[done]")


if __name__ == "__main__":
    main()
