"""Headless screenshot capture against the deployed Hugging Face Space.

Drives the live URL with Firefox (Chromium's HTTP/2 client aborts on
*.hf.space for reasons that aren't worth debugging). Welcome shot from
the root URL; tab shots from ``/?example=Tampered+composite`` which the
app reads at startup. Tab screenshots are clipped to the active-tab
viewport so they're not dominated by the file-header strip.

Run:
    .venv/bin/python scripts/capture_live_screenshots.py
"""
from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

LIVE_URL = "https://nandann018-aperture-forensics.hf.space"
OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

# Larger height than the previous local script so the full verdict
# block fits in one shot even on the longest tab (Verdict).
VIEWPORT = {"width": 1440, "height": 1800}

TAB_TARGETS = [
    ("Verdict", "verdict.png"),
    ("AI Detection", "ai_detection.png"),
    ("Tampering", "tampering.png"),
    ("Scene", "scene.png"),
    ("Metadata", "metadata.png"),
    ("Model Performance", "performance.png"),
]


def main() -> None:
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()

        # ---- Welcome (root URL, no example selected) ----
        print(f"[goto] {LIVE_URL}")
        page.goto(LIVE_URL, wait_until="load", timeout=120000)
        page.wait_for_selector("[data-testid='stSidebar']", timeout=90000)
        time.sleep(4)  # let splash + reveal animations settle
        page.screenshot(path=str(OUT / "welcome.png"), full_page=True)
        print(f"[shot] {OUT / 'welcome.png'}")

        # ---- Tab page (use ?example= URL param — bypasses the flaky
        # iframe-tile click). app.py reads ``st.query_params['example']``
        # at startup and runs the full pipeline against that file. ----
        analysis_url = f"{LIVE_URL}/?example=Tampered+composite"
        print(f"[goto] {analysis_url}")
        page.goto(analysis_url, wait_until="load", timeout=120000)

        print("[wait] analyses running... up to 300s")
        page.wait_for_selector("button[role='tab']", timeout=300000)

        # Wait for spinners + status block to clear so screenshots are stable.
        try:
            page.wait_for_selector("[data-testid='stSpinner']",
                                   state="detached", timeout=60000)
        except Exception:
            pass
        try:
            page.wait_for_selector("[data-testid='stStatus']",
                                   state="detached", timeout=20000)
        except Exception:
            pass
        time.sleep(5)

        # Hide cold-start info banner + deploy chrome.
        page.add_style_tag(content="""
            [data-testid='stAlertContainer'] { display: none !important; }
            [data-testid='stStatusWidget'] { display: none !important; }
            [data-testid='stToolbar'] { display: none !important; }
            header { display: none !important; }
        """)

        for tab_label, out_name in TAB_TARGETS:
            print(f"[tab] {tab_label}")
            tab = page.get_by_role("tab", name=tab_label)
            tab.click()
            page.wait_for_timeout(3500)  # paint + plotly render
            # Scroll the tab strip to the top so the active content
            # dominates the viewport, not the file-info chip.
            page.evaluate(
                "document.querySelector('[role=\"tablist\"]')"
                ".scrollIntoView({block: 'start', behavior: 'instant'})"
            )
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / out_name), full_page=False)
            print(f"[shot] {OUT / out_name}")

        context.close()
        browser.close()

    print("[done] live screenshots saved to", OUT)


if __name__ == "__main__":
    main()
