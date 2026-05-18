"""Metadata analysis entry point."""
from __future__ import annotations

from typing import Optional

from PIL import Image

from Aperture.metadata.anomalies import (
    Anomaly,
    compute_anomaly_score,
    detect_anomalies,
    group_by_severity,
)
from Aperture.metadata.exif import normalized_fields, read_exif
from Aperture.metadata.jpeg_analysis import analyze_jpeg


def analyze_metadata(pil_image: Image.Image, file_bytes: Optional[bytes] = None) -> dict:
    """Run EXIF + JPEG analysis + rule-based anomaly detection.

    Returns a dict shaped for the UI's metadata tab and for the
    meta-classifier's ``metadata_score`` feature.
    """
    exif = read_exif(pil_image)
    jpeg = analyze_jpeg(pil_image, file_bytes=file_bytes)
    flags = detect_anomalies(exif, jpeg)
    score = compute_anomaly_score(flags)
    return {
        "exif": exif,
        "exif_normalized": normalized_fields(exif),
        "jpeg": jpeg,
        "anomalies": [f.to_dict() for f in flags],
        "anomalies_by_severity": {
            sev: [f.to_dict() for f in fs]
            for sev, fs in group_by_severity(flags).items()
        },
        "anomaly_score": score,
    }


__all__ = ["analyze_metadata", "Anomaly"]
