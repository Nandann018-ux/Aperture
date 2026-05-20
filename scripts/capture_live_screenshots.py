"""Headless screenshot capture against the deployed Hugging Face Space.

Drives the live URL with Playwright, picks the "Copy-move" example (the
most visually-busy one), cycles through every tab, and saves the PNGs
into docs/screenshots/. Longer timeouts than the local-boot capture
script — first-analysis on HF includes CLIP + YOLO + EasyOCR weight
downloads (~250 MB), which adds 60-120 s.

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

EXAMPLE_LABEL = "Copy-move"

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
        # Firefox, not Chromium — Chromium's HTTP/2 client aborts the
        # initial request to *.hf.space (net::ERR_ABORTED) for reasons
        # that aren't worth debugging when Firefox just works.
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1600},
        )
        page = context.new_page()

        print(f"[goto] {LIVE_URL}")
        # ``networkidle`` waits forever on Streamlit pages (the websocket
        # never goes idle). Use ``load`` and let our own selector wait
        # gate the next step.
        page.goto(LIVE_URL, wait_until="load", timeout=120000)
        page.wait_for_selector("[data-testid='stSidebar']", timeout=90000)
        # Give the splash + first-paint reveal animations time to settle.
        time.sleep(4)

        # --- Welcome screen (no image yet) ---
        page.screenshot(path=str(OUT / "welcome.png"), full_page=True)
        print(f"[shot] {OUT / 'welcome.png'}")

        # --- Pick an example via the sidebar tile grid (iframe-rendered) ---
        # The 6 example tiles live inside an iframe (components.html). The
        # canonical short labels we set in components.py are:
        # PORTRAIT / LANDSCAPE / AI-REAL / MJ-MIST / COMP / PHOTOSHOP
        # We pick COMP (Tampered composite) for the visual richness.
        print("[select] choosing example via tile-grid iframe")
        clicked = False
        for frame in page.frames:
            try:
                if frame == page.main_frame:
                    continue
                comp = frame.locator(".ex").filter(has_text="COMP").first
                if comp.count() > 0:
                    comp.click()
                    clicked = True
                    print("[select] clicked COMP tile inside iframe")
                    break
            except Exception:
                continue

        # Fallback: drive the backing selectbox by URL param.
        if not clicked:
            print("[select] fallback to URL param")
            page.goto(f"{LIVE_URL}/?example=Tampered+composite",
                      wait_until="load", timeout=120000)
            time.sleep(3)

        # Wait for analyses: tab strip appears after pipelines finish.
        # HF cold-start can take 60-180s for first analysis.
        print("[wait] analyses running... up to 300s")
        try:
            page.wait_for_selector("button[role='tab']", timeout=300000)
        except Exception:
            page.screenshot(path=str(OUT / "_debug_no_tabs.png"), full_page=True)
            print(f"[debug] saved {OUT / '_debug_no_tabs.png'}")
            raise

        # Wait for spinners + status block to clear.
        try:
            page.wait_for_selector("[data-testid='stSpinner']", state="detached",
                                   timeout=60000)
        except Exception:
            pass
        try:
            page.wait_for_selector("[data-testid='stStatus']", state="detached",
                                   timeout=20000)
        except Exception:
            pass
        time.sleep(4)

        # Hide cold-start info banner + deploy chrome — they add noise.
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
            page.wait_for_timeout(3500)
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
