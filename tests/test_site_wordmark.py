"""Sitewide wordmark contract — residual sweep after homepage v2 (#1104).

Owner decision (ruled 2026-08-19, executed on `/` by #1104): the wordmark is
MIZ OKI 3.5 everywhere; `MIZOKI3` remains only where it is a code identifier
or the legal-entity name.

Every served route is pinned to the exact number of `MIZOKI3` occurrences that
are left BY DESIGN, with each one named. The count is taken over the raw
response body (a superset of the visible text), so it matches what a
`curl | grep -o MIZOKI3 | wc -l` probe of the live domain measures.

Left-by-design classes:
  D  legal-entity name — copyright lines, the entity line on the policy pages,
     the Terms' IP assertion over "the MIZOKI3 name".
  E  code identifier — the MIZOKI3.COM domain crumb, a CSS comment.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime


REPO_ROOT = Path(__file__).resolve().parents[1]

OLD = "MIZOKI3"
NEW = "MIZ OKI 3.5"

# A logo written as split markup — MIZOKI<span>3</span>, MIZOKI<b>3</b> — is the
# old wordmark to a reader and invisible to a plain `MIZOKI3` grep.
SPLIT_LOGO = re.compile(r"MIZOKI\s*<(?:span|b)\b[^>]*>\s*3\s*<")

COPYRIGHT = "the copyright line"

# route -> (allowed MIZOKI3 count, what each allowed occurrence is)
ALLOWED: dict[str, tuple[int, str]] = {
    # --- the Step 0 table ---------------------------------------------------
    "/": (1, "D: '© 2026 MIZOKI3' legal footer (pinned by test_homepage_v2 too)"),
    "/pricing": (2, "E: '/* MIZOKI3 design tokens */' CSS comment; D: '© 2026 MIZOKI3, Inc.'"),
    "/privacy": (4, "E: 'MIZOKI3.COM' domain crumb; D: 'MIZOKI3 · Media Intelligence' issuer line; "
                    "D: the same entity line in the Contact block; D: '© 2026 MIZOKI3'"),
    "/terms": (4, "E: 'MIZOKI3.COM' domain crumb; D: 'MIZOKI3 · Media Intelligence' issuer line; "
                  "D: IP assertion 'the MIZOKI3 name'; D: '© 2026 MIZOKI3'"),
    "/marketing/pricing": (1, COPYRIGHT),
    "/risk": (1, COPYRIGHT),
    "/counsel": (1, COPYRIGHT),
    "/estate": (1, COPYRIGHT),
    "/capital": (1, COPYRIGHT),
    "/demo": (1, COPYRIGHT),
    "/media": (0, ""),
    "/media/pilot": (0, ""),
    "/media/demo": (0, ""),
    "/media/decision-graph": (0, ""),
    "/signal": (0, ""),
    "/walkthrough": (0, ""),
    "/animation": (0, ""),
    "/executive-briefing/": (0, ""),
    # --- served routes the url_map adds to that table -----------------------
    "/demo/signal": (1, COPYRIGHT),
    "/demo/counsel": (0, ""),
    "/demo/estate": (0, ""),
    "/demo/capital": (1, COPYRIGHT),
    "/demo/risk": (1, COPYRIGHT),
    "/demo/nexus": (1, COPYRIGHT),
    "/marketing": (0, ""),
    "/marketing/demo": (1, COPYRIGHT),
    "/marketing/engine": (1, COPYRIGHT),
    "/marketing/modules": (1, COPYRIGHT),
    "/marketing/governance": (1, COPYRIGHT),
    "/marketing/simulator": (1, COPYRIGHT),
    "/marketing/walkthrough": (1, COPYRIGHT),
    "/marketing/counsel": (1, COPYRIGHT),
    "/marketing/estate": (1, COPYRIGHT),
    "/marketing/capital": (1, COPYRIGHT),
    "/marketing/signal": (1, COPYRIGHT),
    "/marketing/risk": (1, COPYRIGHT),
    "/signal/thresholds": (1, COPYRIGHT),
    "/signal/budget": (1, COPYRIGHT),
    "/signal/creative": (1, COPYRIGHT),
    "/signal/audiences": (1, COPYRIGHT),
    "/signal/measurement": (1, COPYRIGHT),
    "/shopify": (0, ""),
    "/mizuki3": (1, COPYRIGHT),
    "/console": (0, ""),
    "/blog/doorman-problem": (1, COPYRIGHT),
}

# Routes that carried the old wordmark as brand text (classes A/B/C) before the
# sweep; each must now serve the new one. `/` and the zero-count routes above
# never carried it and are covered by their own suites.
CARRIED_OLD_WORDMARK = sorted(
    set(ALLOWED)
    - {"/", "/media", "/media/pilot", "/media/demo", "/media/decision-graph", "/signal",
       "/walkthrough", "/animation", "/executive-briefing/", "/blog/doorman-problem"}
)


class SiteWordmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        app = create_app(runtime=runtime)
        app.testing = True
        self.client = app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _body(self, route: str) -> str:
        response = self.client.get(route)
        self.assertEqual(200, response.status_code, f"{route} must serve 200")
        body = response.get_data(as_text=True)
        response.close()
        return body

    def test_every_served_route_answers_200_without_the_retired_contact(self) -> None:
        for route in ALLOWED:
            with self.subTest(route=route):
                self.assertNotIn("hello@mizoki3.com", self._body(route))

    def test_old_wordmark_survives_only_where_it_is_left_by_design(self) -> None:
        for route, (allowed, what) in ALLOWED.items():
            with self.subTest(route=route):
                count = self._body(route).count(OLD)
                self.assertLessEqual(
                    count, allowed,
                    f"{route} serves {count} x {OLD}; only {allowed} are left by design ({what or 'none'})",
                )

    def test_new_wordmark_is_served_where_the_old_one_was(self) -> None:
        for route in CARRIED_OLD_WORDMARK:
            with self.subTest(route=route):
                self.assertIn(NEW, self._body(route))

    def test_no_split_markup_logo_and_no_old_mailto_subject(self) -> None:
        for route in ALLOWED:
            with self.subTest(route=route):
                body = self._body(route)
                self.assertIsNone(SPLIT_LOGO.search(body), f"{route} still draws the old logo as split markup")
                self.assertNotIn("subject=MIZOKI3", body)

    def test_split_logo_detector_fires_in_both_directions(self) -> None:
        # Seeded violations: the three forms this sweep removed.
        for old_logo in (
            'MIZOKI<span class="three">3</span>',
            "MIZOKI<b>3</b>",
            'MIZOKI<span class="t">3</span>',
        ):
            self.assertIsNotNone(SPLIT_LOGO.search(old_logo), old_logo)
        # Legal phrasing it must not flag: the new logo and the legal lines.
        for legal in (
            'MIZ&nbsp;OKI&nbsp;<span class="three">3.5</span>',
            "MIZ OKI <b>3.5</b>",
            'MIZ OKI <span class="logo-version">3.5</span>',
            "© 2026 MIZOKI3 · <a href=\"/privacy\">Privacy</a>",
            "© 2026 MIZOKI3, Inc. All rights reserved.",
        ):
            self.assertIsNone(SPLIT_LOGO.search(legal), legal)

    def test_intent_source_metadata_carries_the_new_wordmark(self) -> None:
        # /intent is built at deploy time from intent-site/; its index.html is
        # the source of the served <title> and social metadata.
        source = (REPO_ROOT / "intent-site" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(OLD, source)
        self.assertIn(f"<title>{NEW} — Anticipatory Intelligence</title>", source)


if __name__ == "__main__":
    unittest.main()
