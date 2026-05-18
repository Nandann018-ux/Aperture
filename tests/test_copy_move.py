"""Unit tests for copy-move forgery detection."""
from __future__ import annotations

import numpy as np
from PIL import Image

from Aperture.tampering.copy_move import detect_copy_move, visualize_copy_move


def _clean(size: int = 384) -> Image.Image:
    """Smooth gradient with mild noise — should yield few/no matches."""
    y = np.linspace(0, 1, size, dtype=np.float32)[:, None]
    arr = np.broadcast_to((200 - 80 * y)[..., None], (size, size, 3)).copy()
    arr = np.clip(
        arr + np.random.default_rng(0).normal(0, 3.0, arr.shape), 0, 255
    ).astype(np.uint8)
    return Image.fromarray(arr)


def _with_duplicate(size: int = 384) -> Image.Image:
    """Insert the same richly-textured region into two distant locations."""
    arr = np.asarray(_clean(size)).copy()
    texture = np.random.default_rng(7).integers(
        20, 235, size=(80, 80, 3), dtype=np.int16
    ).astype(np.uint8)
    arr[60:140, 60:140] = texture
    arr[230:310, 250:330] = texture
    return Image.fromarray(arr)


def test_detect_copy_move_output_schema():
    out = detect_copy_move(_clean())
    assert set(out.keys()) == {"matches_count", "match_pairs", "is_tampered"}
    assert isinstance(out["matches_count"], int)
    assert isinstance(out["match_pairs"], list)
    assert isinstance(out["is_tampered"], bool)


def test_detect_copy_move_finds_duplicate():
    clean = detect_copy_move(_clean())
    dup = detect_copy_move(_with_duplicate())
    assert dup["matches_count"] > clean["matches_count"], (
        f"clean={clean['matches_count']} dup={dup['matches_count']}"
    )
    assert dup["matches_count"] >= 5, (
        f"expected the duplicated 80x80 patch to yield multiple matches; "
        f"got {dup['matches_count']}"
    )


def test_visualize_copy_move_returns_pil():
    img = _with_duplicate()
    out = detect_copy_move(img)
    vis = visualize_copy_move(img, out["match_pairs"])
    assert isinstance(vis, Image.Image)
    assert vis.size == img.size
