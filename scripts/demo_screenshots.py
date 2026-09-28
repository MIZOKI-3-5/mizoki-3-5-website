#!/usr/bin/env python3
"""Visual QA gate for the demo surface (dev-only; §7 of the v4 build doc).

Boots the Flask app on a test port, then uses the environment's Playwright
(with its bundled Chromium — do NOT add playwright to requirements.txt) to
capture:

- /demo (hub)
- all six demo pages, mid-run (click Start, await the finale/decision card)
- Boardroom mode on /demo/nexus
- /walkthrough.html

at 390 / 768 / 1440 px widths, into scripts/screenshots/ — plus the
Executive Demo (/media/demo, r1.0, 2026-09-12): every act driven to its
interactive state at 1440 px, Act 1 and Act 5 at 400 px, with a hard check
that the 400 px layout has no horizontal scroll and the page logs no
console/page errors.

Review every image before committing; attach the 1440 px set to the PR.
D1 shipped because this step didn't exist — it is now a merge gate.

Usage:
    python3 scripts/demo_screenshots.py [--out scripts/screenshots]
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

PORT = int(os.environ.get("MIZOKI_SCREENSHOT_PORT", "8765"))
BASE_URL = f"http://127.0.0.1:{PORT}"
WIDTHS = (390, 768, 1440)

# (slug, path, ready_selector, start_selector, finale_selector)
PAGES = [
    ("hub", "/demo", ".demo-cards", None, None),
    ("signal", "/demo/signal", "#startBtn", "#startBtn", "#decisionCard.on"),
    ("counsel", "/demo/counsel", "#scenarioGrid .scn-card", "#scenarioGrid .scn-card", "#synthPanel.on"),
    ("estate", "/demo/estate", "#startBtn", "#startBtn", "#finaleCard.on"),
    ("capital", "/demo/capital", "#startBtn", "#startBtn", "#decisionCard.on"),
    ("risk", "/demo/risk", "#startBtn", "#startBtn", "#finaleCard.on"),
    ("nexus", "/demo/nexus", "#startBtn", "#startBtn", "#provenancePanel.on"),
    ("walkthrough", "/walkthrough.html", "h1", None, None),
]

# Executive Demo r1.0: single-file presenter surface. Widths per the landing
# prompt (1440 projector / 400 phone). Each act is driven to the state the
# review checks — Act 1 table (bank view), Act 3 lift chart after the
# refutation battery, Act 4 waterfall + dosage curve at a moved budget,
# Act 5 DEL chart after an action + the three F4 HALTs.
EXEC_PATH = "/media/demo"
EXEC_WIDTHS = (1440, 400)
EXEC_ACTS = (
    # (slug, act index, [(selector, settle_ms), ...])
    ("0-cover", 0, []),
    ("1-the-lie", 1, [("#viewPlatform", 150), ("#viewBank", 300)]),
    ("2-the-signals", 2, [("#playSession", 5300), ("#sendKeys", 400)]),
    ("3-the-proof", 3, [("#registerBtn", 200), ("#refuteBtn", 2400)]),
    ("4-the-profit", 4, []),
    ("5-the-restraint", 5, [("#a1", 2700), ("#f4Btn", 1900)]),
    ("6-the-90-days", 6, []),
)
EXEC_PHONE_ACTS = ("1-the-lie", "5-the-restraint")
EXEC_FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")


def boot_app() -> None:
    from app import create_app

    app = create_app()
    # Keep runs snappy for screenshots: SSE unpaced (finales appear fast).
    app.config.update(TESTING=True)

    thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    import urllib.request

    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=1):
                return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("app did not boot on the test port")


def capture(out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    shots: list[Path] = []
    executable = os.environ.get("MIZOKI_CHROMIUM_PATH")

    with sync_playwright() as p:
        launch_kwargs = {}
        if executable:
            launch_kwargs["executable_path"] = executable
        browser = p.chromium.launch(**launch_kwargs)
        for width in WIDTHS:
            context = browser.new_context(
                viewport={"width": width, "height": 900},
                reduced_motion="reduce",
            )
            page = context.new_page()
            for slug, path, ready, start, finale in PAGES:
                page.goto(BASE_URL + path, wait_until="networkidle")
                page.wait_for_selector(ready, timeout=15000)
                if start:
                    page.wait_for_timeout(500)
                    page.click(start)
                    if finale:
                        page.wait_for_selector(finale, timeout=60000)
                        page.wait_for_timeout(600)
                target = out_dir / f"{slug}-{width}.png"
                page.screenshot(path=str(target), full_page=True)
                shots.append(target)
                print(f"  captured {target}")
                # Boardroom mode — nexus only, once per width.
                if slug == "nexus":
                    page.click("#boardroomBtn")
                    page.wait_for_selector(".nxb-stage .nxb-title", timeout=20000)
                    page.wait_for_timeout(1200)
                    target = out_dir / f"nexus-boardroom-{width}.png"
                    page.screenshot(path=str(target))
                    shots.append(target)
                    print(f"  captured {target}")
                    page.keyboard.press("Escape")
            context.close()
        shots.extend(capture_executive(browser, out_dir))
        browser.close()
    return shots


def capture_executive(browser, out_dir: Path) -> list[Path]:
    """Drive /media/demo act by act; fail on errors or phone overflow."""
    shots: list[Path] = []
    errors: list[str] = []
    failed_requests: list[str] = []
    for width in EXEC_WIDTHS:
        context = browser.new_context(viewport={"width": width, "height": 900},
                                      reduced_motion="reduce")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(f"{width}px pageerror: {e}"))
        # Resource-load failures are judged by URL below (requestfailed), so
        # the console echo of one is not double-counted; every other console
        # error is a real defect.
        page.on("console", lambda m: errors.append(f"{width}px console: {m.text}")
                if m.type == "error" and not m.text.startswith("Failed to load resource") else None)
        page.on("requestfailed", lambda r: failed_requests.append(r.url))
        page.goto(BASE_URL + EXEC_PATH, wait_until="networkidle")
        page.wait_for_selector("#actRail", timeout=15000)
        for slug, act, clicks in EXEC_ACTS:
            if width == 400 and slug not in EXEC_PHONE_ACTS:
                continue
            page.evaluate(f'document.querySelector(\'#actRail [data-go="{act}"]\').click()')
            page.wait_for_timeout(350)
            for selector, settle in clicks:
                page.click(selector)
                page.wait_for_timeout(settle)
            if slug == "4-the-profit":
                page.fill("#budget", "8000")
                page.dispatch_event("#budget", "input")
                page.wait_for_timeout(300)
            # The top bar is position:sticky; a full-page capture otherwise
            # paints it wherever the last click scrolled to.
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(150)
            target = out_dir / f"executive-{slug}-{width}.png"
            page.screenshot(path=str(target), full_page=True)
            shots.append(target)
            print(f"  captured {target}")
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        if scroll_w > width:
            raise RuntimeError(f"/media/demo overflows at {width}px: scrollWidth={scroll_w}")
        print(f"  /media/demo {width}px: scrollWidth={scroll_w} (no horizontal scroll)")
        context.close()
    # The page's only permitted egress is Google Fonts (the landing prompt's
    # "fonts excepted"). A sandbox without egress resets that fetch and the
    # page falls back to system fonts — tolerated, and said so; any OTHER
    # failed request is a foreign dependency and fails the gate.
    foreign = [u for u in failed_requests
               if not any(h in u for h in EXEC_FONT_HOSTS)]
    if foreign:
        errors.append("foreign resource(s) requested: " + ", ".join(sorted(set(foreign))))
    if errors:
        raise RuntimeError("/media/demo logged errors:\n" + "\n".join(errors))
    if failed_requests:
        print("  note: font fetch failed here (no egress) — captures use fallback fonts: "
              + ", ".join(sorted(set(failed_requests))))
    print("  /media/demo: no console or page errors; no foreign resources")
    return shots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(BASE_DIR / "scripts" / "screenshots"))
    args = parser.parse_args()

    print(f"booting app on {BASE_URL} …")
    boot_app()
    print("capturing screenshots …")
    shots = capture(Path(args.out))
    print(f"\n{len(shots)} screenshots in {args.out} — review every image "
          "(overflow, clipped widgets, unstyled states, projector type) before commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
