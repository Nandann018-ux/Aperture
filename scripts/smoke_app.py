"""Headless E2E smoke test for app.py using Streamlit's AppTest.

Verifies that the app boots, the welcome screen renders, picking an
example loads it, and none of the 6 tab render functions raise.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so app.py's `import Aperture` works
# when this script is invoked as scripts/smoke_app.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest  # noqa: E402

EXAMPLES = [
    "Authentic landscape",
    "Authentic portrait",
    "Tampered composite",
    "Copy-move",
    "AI — Midjourney-style",
    "AI — realistic",
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    print("[1/3] Boot app...")
    at = AppTest.from_file("app.py", default_timeout=180)
    at.run()
    if at.exception:
        fail(f"app raised on initial run: {[str(e) for e in at.exception]}")
    print(f"      OK — welcome screen rendered ({len(at.markdown)} markdown blocks).")

    print(f"[2/3] Iterate through {len(EXAMPLES)} example images...")
    for ex in EXAMPLES:
        sb = at.selectbox(key=None) if False else at.selectbox[0]
        sb.set_value(ex).run()
        if at.exception:
            fail(f"example {ex!r}: {[str(e) for e in at.exception]}")
        # Confirm tabs exist
        n_tabs = len(at.tabs)
        if n_tabs < 6:
            fail(f"example {ex!r}: expected ≥6 tabs, got {n_tabs}")
        print(f"      OK — {ex} loaded, {n_tabs} tabs rendered.")

    print("[3/3] Final state summary:")
    print(f"      markdown blocks: {len(at.markdown)}")
    print(f"      metrics:         {len(at.metric)}")
    print(f"      tabs:            {len(at.tabs)}")
    print(f"      info messages:   {len(at.info)}")
    print(f"      warnings:        {len(at.warning)}")
    print(f"      errors:          {len(at.error)}")
    if at.error:
        for e in at.error:
            print("        - ", e.value[:120])
    print("PASS")


if __name__ == "__main__":
    main()
