"""EXIF / IPTC extraction via Pillow.

Returns a flat dict of human-readable tag names to string values, plus a
few normalized fields used by the anomaly rules.
"""
from __future__ import annotations

from typing import Any

from PIL import ExifTags, Image

_GPS_TAGS = {v: k for k, v in ExifTags.GPSTAGS.items()}


def _stringify(value: Any) -> str:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace").strip("\x00 ")
        except Exception:
            return repr(value)
    if isinstance(value, tuple) and len(value) == 2 and all(isinstance(x, int) for x in value):
        # IFDRational comes back like (num, den)
        num, den = value
        return f"{num/den:g}" if den else str(num)
    return str(value)


def read_exif(pil_image: Image.Image) -> dict:
    """Extract EXIF as a flat dict of {human_tag_name: str_value}."""
    raw = pil_image.getexif()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for tag_id, value in raw.items():
        name = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
        # Recurse into the Exif IFD where most camera tags actually live
        if name == "ExifOffset":
            try:
                ifd = raw.get_ifd(tag_id)
                for sub_id, sub_val in ifd.items():
                    sub_name = ExifTags.TAGS.get(sub_id, f"Tag_{sub_id}")
                    out[sub_name] = _stringify(sub_val)
            except Exception:
                pass
            continue
        out[name] = _stringify(value)
    return out


def normalized_fields(exif: dict) -> dict:
    """Pick out the fields the anomaly rules and UI care about."""
    return {
        "camera_make": exif.get("Make"),
        "camera_model": exif.get("Model"),
        "software": exif.get("Software"),
        "datetime_original": exif.get("DateTimeOriginal"),
        "datetime_modified": exif.get("DateTime") or exif.get("ModifyDate"),
        "iso": exif.get("ISOSpeedRatings") or exif.get("PhotographicSensitivity"),
        "focal_length": exif.get("FocalLength"),
        "exposure_time": exif.get("ExposureTime"),
        "f_number": exif.get("FNumber"),
        "gps_present": any(k.startswith("GPS") for k in exif.keys()),
    }
