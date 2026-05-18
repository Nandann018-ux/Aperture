"""SIFT-based copy-move forgery detection.

Match a SIFT descriptor against the rest of the image; pairs that survive
Lowe's ratio test and a spatial-distance threshold are candidate clone
regions. Many such pairs => the image likely has a duplicated region.
"""
from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw

Point = Tuple[float, float]
MatchPair = Tuple[Point, Point]


def _sift():
    """OpenCV moved SIFT between modules across versions; try both."""
    if hasattr(cv2, "SIFT_create"):
        return cv2.SIFT_create()
    return cv2.xfeatures2d.SIFT_create()  # type: ignore[attr-defined]


def detect_copy_move(
    pil_image: Image.Image,
    min_matches: int = 10,
    min_distance: float = 40.0,
    ratio: float = 0.7,
) -> dict:
    """Find duplicated regions via self-matched SIFT keypoints."""
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    img = np.asarray(pil_image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    sift = _sift()
    kp, desc = sift.detectAndCompute(gray, None)
    if desc is None or len(kp) < 4:
        return {"matches_count": 0, "match_pairs": [], "is_tampered": False}

    bf = cv2.BFMatcher(cv2.NORM_L2)
    # k=3 so [0] is self-match (distance 0) and [1], [2] are real candidates.
    knn = bf.knnMatch(np.asarray(desc, dtype=np.float32), np.asarray(desc, dtype=np.float32), k=3)

    pairs: list[MatchPair] = []
    seen: set[tuple[int, int]] = set()
    for matches in knn:
        if len(matches) < 3:
            continue
        m, n = matches[1], matches[2]
        if n.distance == 0 or m.distance / n.distance > ratio:
            continue
        i, j = m.queryIdx, m.trainIdx
        if i == j:
            continue
        p1 = kp[i].pt
        p2 = kp[j].pt
        if float(np.hypot(p1[0] - p2[0], p1[1] - p2[1])) < min_distance:
            continue
        key = (min(i, j), max(i, j))
        if key in seen:
            continue
        seen.add(key)
        a: Point = (float(p1[0]), float(p1[1]))
        b: Point = (float(p2[0]), float(p2[1]))
        pairs.append((a, b))

    return {
        "matches_count": len(pairs),
        "match_pairs": pairs,
        "is_tampered": len(pairs) >= min_matches,
    }


def visualize_copy_move(
    pil_image: Image.Image,
    match_pairs: list[MatchPair],
) -> Image.Image:
    """Draw lines + endpoints for each matched pair onto a copy of the image."""
    img = pil_image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    for p1, p2 in match_pairs:
        draw.line([p1, p2], fill=(255, 0, 0), width=2)
        for p in (p1, p2):
            r = 3
            draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(0, 255, 0))
    return img
