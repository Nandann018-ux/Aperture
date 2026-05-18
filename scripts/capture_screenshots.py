"""Headless screenshot capture for README demo images.

Boots Streamlit, drives the UI via Playwright, picks an example image,
clicks through each tab, saves PNGs to docs/screenshots/.

Run:
    .venv/bin/python .capture_screenshots.py
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

# Example image to drive the captures. "Copy-move" is the most visually-
# busy example (gives ELA + noise + 28 SIFT matches), so it makes the
# tampering tab actually interesting.
EXAMPLE_LABEL = "Copy-move"

TAB_TARGETS = [
    ("Verdict", "verdict.png"),
    ("AI Detection", "ai_detection.png"),
    ("Tampering", "tampering.png"),
    ("Scene", "scene.png"),
    ("Metadata", "metadata.png"),
    ("Model Performance", "performance.png"),
]


def _pick_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_for_server(port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.4)
    raise TimeoutError(f"streamlit did not start on :{port} within {timeout}s")


def main() -> None:
    port = _pick_port()
    print(f"[boot] streamlit on :{port}")
    proc = subprocess.Popen(
        [
            ".venv/bin/streamlit", "run", "app.py",
            "--server.headless", "true",
            "--server.port", str(port),
            "--browser.gatherUsageStats", "false",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server(port)
        print("[boot] server up — waiting 2s for first render")
        time.sleep(2)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1600},
                device_scale_factor=2,
                color_scheme="dark",
            )
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle", timeout=60000)
            # Streamlit's initial render finishes after the websocket hydrates.
            page.wait_for_selector("[data-testid='stSidebar']", timeout=30000)
            time.sleep(2)

            # --- Welcome screen capture (no image yet) ---
            page.screenshot(path=str(OUT / "welcome.png"), full_page=True)
            print(f"[shot] {OUT / 'welcome.png'}")

            # --- Pick an example via the sidebar selectbox ---
            print(f"[select] choosing example: {EXAMPLE_LABEL}")
            # Streamlit's selectbox renders the trigger as data-baseweb=select
            # and options as role=option in a popover that appears on click.
            selectboxes = page.locator("[data-testid='stSidebar'] [data-baseweb='select']")
            example_box = selectboxes.nth(0)
            example_box.click()
            page.wait_for_timeout(400)
            # Options live in a popover; match by exact text via the option role.
            option = page.locator("[role='option']").filter(has_text=EXAMPLE_LABEL).first
            try:
                option.wait_for(state="visible", timeout=5000)
                option.click()
            except Exception:
                # Fallback: type into the underlying input + Enter.
                page.keyboard.type(EXAMPLE_LABEL, delay=20)
                page.keyboard.press("Enter")
            page.wait_for_timeout(800)

            # Wait for analyses: image header, then the tab strip.
            print("[wait] analyses running... up to 180s")
            try:
                page.wait_for_selector("button[role='tab']", timeout=180000)
            except Exception:
                page.screenshot(path=str(OUT / "_debug_no_tabs.png"), full_page=True)
                print(f"[debug] saved {OUT / '_debug_no_tabs.png'}")
                raise
            # Once tabs exist, wait for any in-flight spinners to clear.
            try:
                page.wait_for_selector("[data-testid='stSpinner']", state="detached", timeout=60000)
            except Exception:
                pass
            time.sleep(3)

            # Hide the cold-start info banner and the deploy chrome — they
            # add noise to every screenshot. Keep the rest of the UI intact.
            page.add_style_tag(content="""
                [data-testid='stAlertContainer'] { display: none !important; }
                [data-testid='stStatusWidget'] { display: none !important; }
                [data-testid='stToolbar'] { display: none !important; }
                header { display: none !important; }
            """)

            # --- Cycle through each tab and screenshot ---
            for tab_label, out_name in TAB_TARGETS:
                print(f"[tab] {tab_label}")
                tab = page.get_by_role("tab", name=tab_label)
                tab.click()
                page.wait_for_timeout(2500)  # allow tab content + plots to paint
                # Scroll the tablist to the top so the active tab content
                # dominates the screenshot, not the file-header strip.
                page.evaluate(
                    "document.querySelector('[role=\"tablist\"]')"
                    ".scrollIntoView({block: 'start', behavior: 'instant'})"
                )
                page.wait_for_timeout(400)
                page.screenshot(path=str(OUT / out_name), full_page=False)
                print(f"[shot] {OUT / out_name}")

            context.close()
            browser.close()

        print("[done] screenshots saved to", OUT)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
