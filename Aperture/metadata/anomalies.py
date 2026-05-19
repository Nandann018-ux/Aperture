"""Rule-based metadata anomaly flags.

Each rule emits a :class:`Anomaly` with severity in {low, medium, high}.
The aggregated anomaly score is a saturating weighted sum of severities,
mapped to [0, 1] for ingestion by the verdict meta-classifier.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

_EDITOR_SIGNATURES = (
    "photoshop", "lightroom", "gimp", "affinity", "pixelmator",
    "luminar", "capture one", "darktable", "snapseed", "facetune",
    "midjourney", "stable diffusion", "dall-e", "dalle", "flux",
    "adobe firefly", "leonardo", "runway",
)

_SEVERITY_WEIGHT = {"low": 0.15, "medium": 0.30, "high": 0.55}


@dataclass
class Anomaly:
    code: str
    severity: str
    message: str
    category: str = "other"

    def to_dict(self) -> dict:
        return asdict(self)


def detect_anomalies(exif: dict, jpeg: dict) -> list[Anomaly]:
    flags: list[Anomaly] = []

    if not exif:
        flags.append(Anomaly(
            code="no_exif",
            category="exif",
            severity="medium",
            message="No EXIF metadata — image was re-encoded or stripped.",
        ))
    else:
        software = (exif.get("Software") or "").lower()
        if software:
            for needle in _EDITOR_SIGNATURES:
                if needle in software:
                    sev = "high" if needle in ("midjourney", "stable diffusion",
                                                "dall-e", "dalle", "flux") else "medium"
                    flags.append(Anomaly(
                        code="editing_software",
                        category="software",
                        severity=sev,
                        message=f"Software tag references '{exif.get('Software')}'.",
                    ))
                    break

        dt_orig = exif.get("DateTimeOriginal")
        dt_mod = exif.get("DateTime") or exif.get("ModifyDate")
        if dt_orig and dt_mod and dt_orig != dt_mod:
            flags.append(Anomaly(
                code="modified_after_capture",
                category="timestamps",
                severity="medium",
                message=f"DateTime differs from DateTimeOriginal "
                        f"({dt_orig} -> {dt_mod}).",
            ))

        if not (exif.get("Make") or exif.get("Model")):
            flags.append(Anomaly(
                code="camera_unknown",
                category="exif",
                severity="low",
                message="No camera Make/Model tag.",
            ))

    if jpeg.get("is_jpeg"):
        q = jpeg.get("estimated_quality")
        if q is not None and q < 70:
            flags.append(Anomaly(
                code="low_jpeg_quality",
                category="compression",
                severity="low",
                message=f"Estimated JPEG quality {q:.0f} suggests aggressive re-compression.",
            ))
        nq = jpeg.get("quantization_tables") or 0
        if nq and nq > 2:
            flags.append(Anomaly(
                code="atypical_qtables",
                category="compression",
                severity="low",
                message=f"Unusual number of quantization tables ({nq}); "
                        "may indicate non-standard encoder.",
            ))

    return flags


def compute_anomaly_score(flags: list[Anomaly]) -> float:
    """Saturating weighted sum of severities, clipped to [0, 1]."""
    score = sum(_SEVERITY_WEIGHT.get(f.severity, 0.0) for f in flags)
    return float(min(1.0, score))


def group_by_severity(flags: list[Anomaly]) -> dict[str, list[Anomaly]]:
    out: dict[str, list[Anomaly]] = {"high": [], "medium": [], "low": []}
    for f in flags:
        out.setdefault(f.severity, []).append(f)
    return out
