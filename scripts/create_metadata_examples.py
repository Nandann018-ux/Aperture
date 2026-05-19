"""Generate demo images that exercise each EXIF anomaly rule.

Each output image carries crafted EXIF that fires exactly one of the
rules in ``Aperture.metadata.anomalies``. Pixel content is pulled from
the public CIFAKE HuggingFace mirror so the images look like real
photos rather than synthetic gradients.

Outputs (under ``examples/``):
    photoshopped_photo.jpg     — editing_software (medium, "Adobe Photoshop")
    date_drift_photo.jpg       — modified_after_capture (medium)
    low_quality_jpeg.jpg       — low_jpeg_quality (low, q=30)
    ai_generated_metadata.jpg  — editing_software (high, "Midjourney")
                                 + camera_unknown (low) — covers HIGH severity

Run from the repo root:
    python scripts/create_metadata_examples.py
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import piexif
import pyarrow.parquet as pq
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "examples"
PARQUET_URL = (
    "https://huggingface.co/datasets/dragonintelligence/CIFAKE-image-dataset/"
    "resolve/main/data/test-00000-of-00001.parquet"
)
TARGET_SIZE = (256, 256)


def _load_real_bases(n: int) -> list[Image.Image]:
    """Pull `n` CIFAKE REAL (label=1) images and upscale to 256x256."""
    req = urllib.request.Request(PARQUET_URL, headers={"User-Agent": "aperture-meta"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    table = pq.read_table(io.BytesIO(data))
    labels = table.column("label").to_pylist()
    images = table.column("image").to_pylist()
    # Stride through the REAL half so chosen images are visually distinct.
    real_indices = [i for i, lbl in enumerate(labels) if lbl == 1]
    step = max(1, len(real_indices) // (n + 1))
    bases: list[Image.Image] = []
    for i in range(n):
        idx = real_indices[(i + 1) * step]
        img = Image.open(io.BytesIO(images[idx]["bytes"])).convert("RGB")
        bases.append(img.resize(TARGET_SIZE, Image.BICUBIC))
    return bases


def _make_exif(
    *,
    software: str | None = None,
    make: str | None = None,
    model: str | None = None,
    datetime_original: str | None = None,
    datetime_modified: str | None = None,
) -> bytes:
    """Build an EXIF byte-string carrying the tags we set."""
    zeroth: dict = {}
    exif: dict = {}
    if software is not None:
        zeroth[piexif.ImageIFD.Software] = software.encode("ascii")
    if make is not None:
        zeroth[piexif.ImageIFD.Make] = make.encode("ascii")
    if model is not None:
        zeroth[piexif.ImageIFD.Model] = model.encode("ascii")
    if datetime_modified is not None:
        zeroth[piexif.ImageIFD.DateTime] = datetime_modified.encode("ascii")
    if datetime_original is not None:
        exif[piexif.ExifIFD.DateTimeOriginal] = datetime_original.encode("ascii")
        exif[piexif.ExifIFD.DateTimeDigitized] = datetime_original.encode("ascii")
    return piexif.dump({"0th": zeroth, "Exif": exif, "GPS": {}, "1st": {}, "thumbnail": None})


def _save(path: Path, img: Image.Image, *, quality: int, exif: bytes) -> None:
    img.save(path, format="JPEG", quality=quality, exif=exif)
    print(f"  wrote {path}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bases = _load_real_bases(4)

    print("Generating metadata example variety set...")

    # 1. Photoshop signature -> MEDIUM editing_software
    _save(
        OUT / "photoshopped_photo.jpg",
        bases[0],
        quality=92,
        exif=_make_exif(
            software="Adobe Photoshop 2024",
            make="Canon",
            model="EOS 5D Mark IV",
            datetime_original="2023:07:15 14:30:00",
            datetime_modified="2023:07:15 14:30:00",  # equal => no date-drift flag
        ),
    )

    # 2. Capture-vs-modify drift -> MEDIUM modified_after_capture
    _save(
        OUT / "date_drift_photo.jpg",
        bases[1],
        quality=92,
        exif=_make_exif(
            software="Camera Firmware 1.0",  # not in editor signatures
            make="Sony",
            model="ILCE-7RM5",
            datetime_original="2023:07:15 14:30:00",
            datetime_modified="2024:03:01 10:00:00",  # ~8 months later
        ),
    )

    # 3. Heavy recompression -> LOW low_jpeg_quality
    _save(
        OUT / "low_quality_jpeg.jpg",
        bases[2],
        quality=30,  # libjpeg estimate will read < 70
        exif=_make_exif(
            software="Camera Firmware 1.0",
            make="Nikon",
            model="NIKON Z 9",
            datetime_original="2023:07:15 14:30:00",
            datetime_modified="2023:07:15 14:30:00",
        ),
    )

    # 4. AI-tool signature -> HIGH editing_software (+ camera_unknown LOW,
    #    since AI generators don't carry camera Make/Model)
    _save(
        OUT / "ai_generated_metadata.jpg",
        bases[3],
        quality=92,
        exif=_make_exif(
            software="Midjourney v6.1",  # 'midjourney' substring triggers HIGH
        ),
    )

    print("Done.")


if __name__ == "__main__":
    main()
