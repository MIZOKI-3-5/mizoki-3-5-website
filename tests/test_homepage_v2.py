"""Homepage v2 — lead with MIZ OKI Media / Causal Growth Control (owner rulings
2026-08-19 and 2026-09-08; operator prompt CLAUDE_CODE_HOMEPAGE_V2 r1.1).

Pins the served `/` against the standing decisions this change executes:

  1. the primary "see it" CTA is MIZ OKI Media (`/media`); the secondary CTA is
     the 90-day pilot (`/media/pilot`);
  2. the 2026-09-13 placement ruling — the executive demo lives in `/media`
     only, so `/` never links `/media/demo` (unless the owner lifts the ruling
     in-session with the exact `RULING:` sentence, at which point this test is
     the thing to change);
  3. wordmark MIZ OKI 3.5 in the visible brand text; `MIZOKI3` survives only as
     the legal footer name and in code identifiers;
  4. contact is briefing@mediaintelligence.ai sitewide, never hello@mizoki3.com;
  5. no uncountable stat (`650+`), no `MIZ OKI 3.0`, no "Patented technology"
     (the PCT application is filed — "Patent pending" is the honest badge);
  6. the evidence-maturity ladder and its three gate figures are on the page;
  7. the OFFERING_MAP v2.3 §B.6 status rows the executive demo close uses are
     on the page, verbatim in their labels, and the unscored AUC gate is never
     presented as a live figure.
"""
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = REPO_ROOT / "index.html"

B6_ROWS = (
    "SRPVDAL loop · Decision Control Plane · DEL scoring · audit ledger",
    "Connector gateway · canonical envelope · O-1 privacy lock",
    "F4 micro-geo calibration (pilot armed 2026-08-24 · every reservation L2-approval-gated · bounded autonomy after 2 clean cycles, 0 complete)",
    "Causal proof core · credit ledger · measurement rails",
    "ORACLE cells 33–36 · intent edges (observe-only / shadow)",
    "Intent Engine v2 · Net Yield lane · F1 F2 F3 F5",
    "Ghost bids · clipped-ReLU authorization shape · ad control plane",
)


class HomepageV2TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(cls.temp_dir.name))
        cls.app = create_app(runtime=runtime)
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()
        response = cls.client.get("/")
        assert response.status_code == 200
        cls.home = response.get_data(as_text=True)
        response.close()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    # -- 1. CTAs -------------------------------------------------------------
    def test_primary_cta_is_media_and_secondary_is_the_pilot(self) -> None:
        self.assertIn('<a class="btn primary" href="/media">EXPLORE MIZ OKI MEDIA →</a>', self.home)
        self.assertIn('<a class="btn" href="/media/pilot">DESIGN A 90-DAY PILOT</a>', self.home)
        self.assertIn('href="/media"', self.home)
        self.assertIn('href="/media/pilot"', self.home)
        # Executive Briefing is demoted to a footer link, not removed.
        footer = self.home.split("<footer>")[1]
        self.assertIn('href="/executive-briefing/"', footer)

    # -- 2. placement ruling 2026-09-13 ----------------------------------------
    def test_homepage_never_links_the_executive_demo_directly(self) -> None:
        self.assertNotIn('href="/media/demo"', self.home)
        self.assertNotIn("/media/demo", self.home)
        self.assertNotIn("/demo/executive", self.home)

    # -- 3. wordmark -----------------------------------------------------------
    def test_wordmark_is_miz_oki_3_5_and_legal_name_survives(self) -> None:
        self.assertIn('<a class="logo" href="#top"><span class="dot"></span>MIZ OKI 3.5</a>', self.home)
        self.assertIn("<title>MIZ OKI 3.5 — Media · Causal Growth Control</title>", self.home)
        self.assertIn("© 2026 MIZOKI3", self.home)
        # No visible MIZOKI3 brand text remains outside the legal footer line.
        visible = re.sub(r"<script.*?</script>", "", self.home, flags=re.S)
        visible = re.sub(r"<style.*?</style>", "", visible, flags=re.S)
        visible = re.sub(r"<[^>]+>", " ", visible)
        self.assertEqual(1, visible.count("MIZOKI3"), "MIZOKI3 must appear once (legal footer) in visible text")
        self.assertNotIn("MIZ OKI 3.0", self.home)

    # -- 4. contact ------------------------------------------------------------
    def test_contact_is_briefing_at_mediaintelligence(self) -> None:
        self.assertIn("briefing@mediaintelligence.ai", self.home)
        self.assertIn('href="mailto:briefing@mediaintelligence.ai', self.home)
        self.assertNotIn("hello@mizoki3.com", self.home)

    def test_contact_swept_sitewide_on_served_surfaces(self) -> None:
        for path in ("/", "/pricing", "/privacy", "/terms", "/marketing/pricing"):
            response = self.client.get(path)
            body = response.get_data(as_text=True)
            response.close()
            with self.subTest(path=path):
                self.assertEqual(200, response.status_code)
                self.assertNotIn("hello@mizoki3.com", body)
        # The tracked-CTA registry redirects to the new address too.
        location = self.client.get("/go/pilot?cta=marketing-hero").headers["Location"]
        self.assertTrue(location.startswith("mailto:briefing@mediaintelligence.ai?subject="), location)

    # -- 5. honesty of numbers and badges --------------------------------------
    def test_no_uncountable_stat_stale_version_or_patent_overclaim(self) -> None:
        for banned in ("650+", "MIZ OKI 3.0", "Patented technology", "0.6884"):
            self.assertNotIn(banned, self.home, banned)
        self.assertIn("Patent pending", self.home)
        # The countable C45 tiles survive (pinned separately by test_content_qa).
        self.assertIn('<div class="v">17 surfaces · 11 live</div>', self.home)

    # -- 6. evidence-maturity ladder ------------------------------------------
    def test_maturity_ladder_and_gate_figures_are_promoted(self) -> None:
        for marker in ("Days 1–30", "Days 31–60", "Days 61–90", "Observe", "Validate",
                       "Recommend → bounded control", "Brier ≤ 0.20", "AUC ≥ 0.72", "≥ 2 cycles",
                       "A model that misses any threshold recommends. It does not act.",
                       "not yet scorable"):
            self.assertIn(marker, self.home, marker)
        self.assertIn("0.20", self.home)
        self.assertIn("0.72", self.home)

    # -- 7. §B.6 status rows ----------------------------------------------------
    def test_b6_status_rows_present_with_unmixed_labels(self) -> None:
        for row in B6_ROWS:
            self.assertIn(row, self.home, row)
        self.assertIn("OFFERING_MAP v2.3 · §B.6", self.home)
        for chip in ('<span class="chip live">live</span>', '<span class="chip partial">partial</span>',
                     '<span class="chip build">in build</span>', '<span class="chip proposed">proposed</span>'):
            self.assertIn(chip, self.home, chip)

    # -- structure: the prompt's section order --------------------------------
    def test_section_order_follows_the_prompt(self) -> None:
        order = ['id="top"', 'id="problem"', 'id="jobs"', 'id="how"', 'id="control"',
                 'id="maturity"', 'id="real"', 'id="decision-graph"', 'id="demos"', "<footer>"]
        positions = [self.home.index(marker) for marker in order]
        self.assertEqual(positions, sorted(positions), "sections out of the ruled order")
        # The eleven customer questions from /media, verbatim.
        for q in ("Why did CPA suddenly increase?", "Why did ROAS fall?", "Is creative responsible?",
                  "Is the website responsible?", "Did tracking break?", "Are we inventory constrained?",
                  "Is margin preventing profitable scale?", "Is this seasonal noise?",
                  "Should we increase budget?", "Should we pause campaigns?", "Who should approve the decision?"):
            self.assertIn(q, self.home, q)
        # Demos row: Media first, then the illustrative hub, then the walkthrough.
        demos = self.home.split('id="demos"')[1].split("</section>")[0]
        self.assertLess(demos.index('href="/media"'), demos.index('href="/demo"'))
        self.assertLess(demos.index('href="/demo"'), demos.index('href="/walkthrough"'))
        self.assertIn("illustrative", demos.lower())

    def test_source_matches_served(self) -> None:
        # / is served from index.html byte-for-byte (canon-pinned surface).
        self.assertEqual(INDEX.read_text(encoding="utf-8"), self.home)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
