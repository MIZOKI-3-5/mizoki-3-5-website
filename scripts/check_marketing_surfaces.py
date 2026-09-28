#!/usr/bin/env python3
"""Marketing-parallel-site drift guard.

Owner directive (2026-08-03): "ensure that we never have issues with losing
proper site online." Two pipelines can deploy the mizoki-website Cloud Run
service (this tree's deploy workflow, and MIZOKICloudRun's deploy-homepage.yml
building from '# MIZ OKI 3.5/'). Two-pipeline drift already bit this project
once (July 2026 homepage drift). This check makes the failure mode structural:
a tree that is missing the /marketing parallel site — or its routes, engine,
or stylesheet — CANNOT deploy from either pipeline.

Stdlib-only on purpose: deploy runners have no Flask installed. Run it the
same way the canon check runs:

    python3 scripts/check_marketing_surfaces.py [--root PATH]
"""
import argparse
import sys
from pathlib import Path

MARKETING_PAGES = (
    "index", "engine", "modules", "simulator", "walkthrough", "governance",
    "counsel", "estate", "capital", "signal", "risk", "pricing",
)

# Files the parallel site cannot serve without, with a content marker that
# proves the file is the real surface, not an empty placeholder.
REQUIRED = {
    "assets/css/marketing.css": "compare-strip",
    "assets/js/media-sim.js": "Wasted Spend Prevented",
    "tests/test_marketing_site.py": "MARKETING_PAGES",
    "marketing/index.html": "Know why performance moved.",
    "marketing/signal.html": 'id="acquisition"',
    # /media (owner-approved 2026-08-03) rides the same guard: a parity copy
    # once dropped its routes — never again.
    "media/index.html": "Causal Growth Control",
    "media/video/mizoki-signal-explainer.mp4": None,
    # /shopify merchant homepage (owner-directed go-live 2026-08-07).
    "shopify.html": "bank account reports",
}

# app.py must still carry the routing layer for the parallel site.
APP_MARKERS = (
    '@app.route("/marketing", strict_slashes=False)',
    "def marketing_division(",
    "def marketing_demo_hub(",
    "def _marketize(",
    '@app.route("/media-buying")',
    '@app.route("/media", strict_slashes=False)',
    '@app.route("/shopify", strict_slashes=False)',
)

MIN_PAGE_BYTES = 2000  # every marketing page is a real page, not a stub


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="site tree root")
    root = Path(parser.parse_args().root).resolve()

    problems: list[str] = []

    for name in MARKETING_PAGES:
        page = root / "marketing" / f"{name}.html"
        if not page.is_file():
            problems.append(f"missing page: marketing/{name}.html")
        elif page.stat().st_size < MIN_PAGE_BYTES:
            problems.append(
                f"stub page: marketing/{name}.html "
                f"({page.stat().st_size} bytes < {MIN_PAGE_BYTES})")

    for rel, marker in REQUIRED.items():
        path = root / rel
        if not path.is_file():
            problems.append(f"missing file: {rel}")
            continue
        if marker is not None and marker not in path.read_text(
                encoding="utf-8", errors="replace"):
            problems.append(f"marker not found in {rel}: {marker!r}")

    app_py = root / "app.py"
    if not app_py.is_file():
        problems.append("missing file: app.py")
    else:
        app_text = app_py.read_text(encoding="utf-8", errors="replace")
        for marker in APP_MARKERS:
            if marker not in app_text:
                problems.append(f"app.py lost a marketing route marker: {marker!r}")

    if problems:
        for problem in problems:
            print(f"MARKETING SITE DRIFT — {problem}", file=sys.stderr)
        print(
            f"\nFAILED — {len(problems)} problem(s). This tree would deploy "
            "WITHOUT the /marketing parallel site (or with a broken one). "
            "Refusing: restore the marketing surfaces or port the latest "
            "parity before deploying.",
            file=sys.stderr,
        )
        return 1

    print(
        f"MARKETING SITE OK — {len(MARKETING_PAGES)} pages + engine, "
        "stylesheet, routes, and tests all present under "
        f"{root}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
