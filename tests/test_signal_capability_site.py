"""Contract tests for the Signal capability site (2026-08-02).

Each capability page must: serve on both its clean URL and .html path, stay
self-contained (inline styles, root-absolute links), keep §-marks strictly
sequential, and hold the truth discipline — operating defaults framed as
defaults, intent content preview-framed, no banned claim vocabulary.

Hub reality since 2026-08-19 (deploy run #63): /signal is the ORACLE
pre-conversion preview — a standalone noindex page linking only its own
anchors. The five capability pages are deliberately unlinked from it
(owner-known orphaning) but MUST keep serving; the route tests below pin
that, and the hub tests pin the preview page's own honesty rails.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import app  # noqa: E402

# The CI gate's §-mark extractor is the single source of truth for the filing
# grammar — a private regex here drifted from it once (the replaced hub writes
# class="secno sec-mark" where the old pattern demanded class="mark sec-mark").
_spec = importlib.util.spec_from_file_location(
    "content_qa", BASE_DIR / "scripts" / "content_qa.py"
)
content_qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(content_qa)

CAPABILITY_SLUGS = ("thresholds", "budget", "creative", "audiences", "measurement")


class _AppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app.config["TESTING"] = True
        cls.client = app.test_client()


class CapabilityRoutesTestCase(_AppTestCase):
    def test_clean_and_html_routes_serve_the_same_page(self) -> None:
        for slug in CAPABILITY_SLUGS:
            clean = self.client.get(f"/signal/{slug}")
            html = self.client.get(f"/signal-{slug}.html")
            self.assertEqual(200, clean.status_code, slug)
            self.assertEqual(200, html.status_code, slug)
            self.assertEqual(clean.get_data(), html.get_data(), slug)

    def test_pages_are_self_contained_with_root_absolute_links(self) -> None:
        for slug in CAPABILITY_SLUGS:
            body = self.client.get(f"/signal/{slug}").get_data(as_text=True)
            self.assertIn("<style>", body, slug)
            self.assertNotIn('rel="stylesheet"', body, slug)
            for href in re.findall(r'href="([^"]+)"', body):
                if href.startswith(("http", "mailto:", "#")):
                    continue
                self.assertTrue(href.startswith("/"), f"{slug}: non-root link {href}")

    def test_sitemap_lists_the_capability_pages(self) -> None:
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        for slug in CAPABILITY_SLUGS:
            self.assertIn(f"https://mizoki3.com/signal/{slug}", sitemap, slug)

    def test_hub_is_the_oracle_preview(self) -> None:
        # Replaced 2026-08-19: the capability-grid hub gave way to the ORACLE
        # pre-conversion preview, which links only its own anchors — the five
        # capability pages are deliberately orphaned from it (owner-known) and
        # their continued serving is pinned by
        # test_clean_and_html_routes_serve_the_same_page above.
        hub = self.client.get("/signal").get_data(as_text=True)
        self.assertIn("ORACLE", hub)
        # A/B/C test-design fix (2026-08-22): /signal is the ONE indexed
        # canonical landing of the variant test — the old IN BUILD noindex
        # flipped under that owner-issued spec (served posture is injected by
        # the /signal route; deploy itself stays owner-dispatched).
        self.assertIn('content="index,follow"', hub)
        self.assertIn('rel="canonical" href="https://mizoki3.com/signal"', hub)
        self.assertNotIn('id="capabilities"', hub)  # the old hub is gone


class SectionMarkSequenceTestCase(_AppTestCase):
    def test_sec_marks_strictly_sequential_on_every_signal_page(self) -> None:
        # Parsed with content_qa.extract_sec_marks — the same extractor the
        # deploy gate runs — so this suite and the gate can never disagree
        # about what a §-mark is (they did once; see the module docstring).
        for path in ["/signal"] + [f"/signal/{s}" for s in CAPABILITY_SLUGS]:
            body = self.client.get(path).get_data(as_text=True)
            nums = content_qa.extract_sec_marks(body)
            self.assertEqual(list(range(1, len(nums) + 1)), nums, path)
            self.assertGreaterEqual(len(nums), 3, path)


class TruthDisciplineTestCase(_AppTestCase):
    BARE_MIND_READING = re.compile(r"(?<!not )(?<!never )(?<!no )mind.reading", re.I)

    def test_banned_vocabulary_absent(self) -> None:
        for path in ["/signal"] + [f"/signal/{s}" for s in CAPABILITY_SLUGS]:
            body = self.client.get(path).get_data(as_text=True)
            self.assertNotIn("guaranteed", body.lower(), path)
            self.assertIsNone(self.BARE_MIND_READING.search(body), path)

    def test_intent_content_carries_preview_framing(self) -> None:
        # Intent/ORACLE appears on the hub (§06) and the audiences page (§04):
        # both must carry the preview tag and the in-development statement.
        for path in ("/signal", "/signal/audiences"):
            body = self.client.get(path).get_data(as_text=True)
            self.assertIn("Preview · in development", body, path)
            self.assertIn("in development", body, path)
        audiences = self.client.get("/signal/audiences").get_data(as_text=True)
        self.assertIn("no microphone or audio signals", audiences)

    def test_operating_defaults_framed_as_defaults_not_outcomes(self) -> None:
        for slug in CAPABILITY_SLUGS:
            body = self.client.get(f"/signal/{slug}").get_data(as_text=True)
            self.assertIn("operating default", body, slug)

    def test_hub_keeps_its_honesty_rails(self) -> None:
        # The old hub's "Illustrative split" ledger left with the 2026-08-19
        # replacement. The ORACLE preview's honesty devices are the preview
        # ribbon, the IN BUILD marker, and illustrative labeling — pin those;
        # full claim discipline additionally runs in scripts/content_qa.py,
        # where signal.html is a scoped SEC_MARK page. The former noindex rail
        # flipped with the A/B/C test-design fix (2026-08-22): /signal is now
        # the test's one indexed canonical landing (the copy honesty rails all
        # stand; indexing was a launch decision, not a claim label).
        hub = self.client.get("/signal").get_data(as_text=True)
        self.assertIn("Illustrative", hub)
        self.assertIn("PREVIEW · IN DEVELOPMENT", hub)
        self.assertIn("IN BUILD", hub)
        self.assertIn('content="index,follow"', hub)


if __name__ == "__main__":
    unittest.main()
