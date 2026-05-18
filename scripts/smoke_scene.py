"""One-off smoke driver: run all three scene analyzers on examples/ and
on a rendered-text image. Prints a concise table per analyzer.

Used to verify acceptance criteria 1-4. Not part of the pytest suite.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from Aperture.scene import (
    get_clip_classifier,
    get_object_detector,
    get_text_extractor,
)

EXAMPLES = Path("examples")
files = [
    "authentic_landscape.jpg",
    "authentic_portrait.jpg",
    "tampered_composite.jpg",
    "copy_move_obvious.jpg",
    "ai_midjourney.jpg",
    "ai_realistic.jpg",
]


def render_text_image() -> Image.Image:
    img = Image.new("RGB", (640, 240), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    draw.text((30, 40), "Aperture forensic", fill=(20, 20, 20), font=font)
    draw.text((30, 110), "OCR test 12345", fill=(20, 20, 20), font=font)
    return img


def main() -> None:
    print("[loading] object detector...")
    det = get_object_detector()
    print("[loading] CLIP classifier...")
    clip = get_clip_classifier()
    print("[loading] OCR reader...")
    ocr = get_text_extractor()

    print("\n=== OBJECT DETECTION ===")
    print(f"{'file':<28} {'n':>3}  detections")
    for f in files:
        img = Image.open(EXAMPLES / f)
        out = det.detect(img)
        objs = out["objects"]
        summary = ", ".join(f"{o['label']}({o['confidence']:.2f})" for o in objs[:5])
        print(f"{f:<28} {len(objs):>3}  {summary if summary else '(none)'}")

    print("\n=== CLIP SCENE ===")
    print(f"{'file':<28} primary -> top3")
    for f in files:
        img = Image.open(EXAMPLES / f)
        out = clip.classify(img)
        top3 = ", ".join(f"{t['label']}({t['score']:.2f})" for t in out["top_3"])
        print(f"{f:<28} {out['primary_scene']:<32} | {top3}")

    print("\n=== OCR (rendered text image) ===")
    text_img = render_text_image()
    out = ocr.extract(text_img)
    print(f"text_found = {out['text_found']}")
    print(f"extracted  = {out['extracted_text']!r}")
    print(f"regions    = {len(out['regions'])}")

    print("\n=== OCR (no-text example) ===")
    out = ocr.extract(Image.open(EXAMPLES / "authentic_landscape.jpg"))
    print(f"text_found = {out['text_found']}  regions={len(out['regions'])}")

    # Save one annotated image to verify rendering
    sample = files[0]
    annotated = det.detect(Image.open(EXAMPLES / sample))["annotated_image"]
    annotated.save("eval_results/scene_annotated_sample.jpg", quality=90)
    print(f"\n[saved] eval_results/scene_annotated_sample.jpg")


if __name__ == "__main__":
    main()
