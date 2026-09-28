"""Contract tests for the /mizuki3 media-buyer landing page.

The page translates platform architecture into plain-English media-buying
value. The vocabulary translation key is MANDATORY and test-enforced here:
internal jargon must never reach the page, its meta tags, or the simulator
script; the plain-English replacements must actually be used.
"""
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]

# jargon -> plain English (the mandatory translation key)
BANNED_JARGON = [
    "srpvdal",
    "canonical event envelope",
    "temporal-causal",
    "domain intelligence cell",
    "immutable learning ledger",
]
REQUIRED_TRANSLATIONS = [
    "Structured Signal Evidence",
    "Cross-Stack Root Cause Engine",
    "Channel Intelligence Modules",
    "7-Stage Decision Control System",
    "Compounding ROI Memory",
]


class Mizuki3LandingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(cls.temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        cls.client = app.test_client()
        response = cls.client.get("/mizuki3")
        cls.status_code = response.status_code
        cls.body = response.get_data(as_text=True)
        response.close()
        cls.js = (REPO_ROOT / "assets" / "js" / "mizuki3-simulator.js").read_text(
            encoding="utf-8"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    # ---- routing -------------------------------------------------------

    def test_page_served_at_pretty_and_html_routes(self) -> None:
        self.assertEqual(200, self.status_code)
        response = self.client.get("/mizuki3.html")
        self.assertEqual(200, response.status_code)
        self.assertIn("text/html", response.content_type)
        response.close()

    def test_sitemap_lists_the_page(self) -> None:
        response = self.client.get("/sitemap.xml")
        self.assertEqual(200, response.status_code)
        self.assertIn("/mizuki3", response.get_data(as_text=True))
        response.close()

    # ---- mandatory vocabulary translation ------------------------------

    def test_no_internal_jargon_reaches_the_page(self) -> None:
        lowered = self.body.lower()
        for term in BANNED_JARGON:
            self.assertNotIn(term, lowered, f"jargon leaked into page: {term!r}")

    def test_no_internal_jargon_reaches_the_simulator_script(self) -> None:
        lowered = self.js.lower()
        for term in BANNED_JARGON:
            self.assertNotIn(term, lowered, f"jargon leaked into JS: {term!r}")

    def test_plain_english_translations_are_used(self) -> None:
        for phrase in REQUIRED_TRANSLATIONS:
            self.assertIn(phrase, self.body, f"missing translated term: {phrase!r}")

    # ---- hero ----------------------------------------------------------

    def test_hero_copy_contract(self) -> None:
        self.assertIn("MIZ OKI 3.5 — Operating Knowledge Intelligence", self.body)
        self.assertIn("Stop Managing Dashboards.", self.body)
        self.assertIn("Start Governing Ad Growth.", self.body)
        self.assertIn(
            "The first autonomous AI control plane built for high-scale media buyers",
            self.body,
        )
        self.assertIn("Launch Interactive Scenario Simulator", self.body)
        self.assertIn("Watch 90-Sec Platform Walkthrough", self.body)

    def test_hero_proof_metrics(self) -> None:
        self.assertIn("$100M+", self.body)
        self.assertIn("Ad Spend Analyzed", self.body)
        self.assertIn("Sub-100ms", self.body)
        self.assertIn("Signal Latency", self.body)
        self.assertIn("100%", self.body)
        self.assertIn("Policy Compliance", self.body)

    # ---- problem vs solution matrix ------------------------------------

    def test_problem_vs_solution_matrix(self) -> None:
        self.assertIn("Dashboard symptom management", self.body)
        self.assertIn("root-cause intelligence", self.body)
        self.assertIn("CPA spikes 40% overnight", self.body)

    # ---- 7-stage interactive section -----------------------------------

    def test_seven_stage_accordion_present(self) -> None:
        self.assertGreaterEqual(self.body.count('<details class="stage"'), 7)
        for name, tag in [
            ("SENSE", "24/7 Full-Stack Radar"),
            ("REASON", "Root Cause AI"),
            ("PLAN", "Actionable Strategy"),
            ("VALIDATE", "Safety Brakes"),
            ("DECIDE", "1-Click Approvals"),
            ("ACT", "Hands-Free Execution"),
            ("LEARN", "Compounding ROI Memory"),
        ]:
            self.assertIn(f'<span class="st-name">{name}</span>', self.body)
            self.assertIn(tag, self.body)

    def test_stage_copy_mentions_monitored_stacks(self) -> None:
        for stack in ("Google Ads", "Meta", "Shopify"):
            self.assertIn(stack, self.body)

    # ---- simulator widget ----------------------------------------------

    def test_simulator_markup_contract(self) -> None:
        self.assertIn('id="mzkSim"', self.body)
        for scenario in ("latency", "inventory", "pixel"):
            self.assertIn(f'name="mzkScenario" value="{scenario}"', self.body)
        for control in ("mzkLat", "mzkInv", "mzkBud", "mzkFloor", "mzkCap",
                        "mzkRun", "mzkApprove", "mzkLog", "mzkPhases",
                        "mzkPrevented", "mzkRoasKept"):
            self.assertIn(f'id="{control}"', self.body)
        # policy values are visible fixed contracts
        self.assertIn("2.2×", self.body)
        self.assertIn("$5,000", self.body)
        # slider ranges from the spec
        self.assertIn('min="0.5" max="6.0"', self.body)
        self.assertIn('min="0" max="1000"', self.body)
        self.assertIn('min="1000" max="20000"', self.body)

    def test_simulator_script_wired_root_absolute(self) -> None:
        self.assertRegex(
            self.body, r'src="/assets/js/mizuki3-simulator\.js\?v=\d+"'
        )

    def test_simulator_js_is_deterministic_and_reactive(self) -> None:
        self.assertIn('"use strict"', self.js)
        self.assertNotIn("Math.random", self.js)
        # live recalculation: sliders re-evaluate on input events
        self.assertIn('addEventListener("input"', self.js)
        # deterministic trace ids derived from run inputs
        self.assertIn("function traceId", self.js)
        # the approve gate and the LEARN ticker exist
        self.assertIn("Approve", self.body)
        self.assertIn("Wasted Spend Prevented", self.body)
        self.assertIn("ROAS Preserved", self.body)

    def test_simulator_labeled_illustrative(self) -> None:
        self.assertIn("illustrative figures", self.body)
        self.assertIn("not customer data", self.body)
        self.assertIn("no live API is called", self.js)

    # ---- 90-second walkthrough -----------------------------------------

    def test_walkthrough_scenes_and_timestamps(self) -> None:
        for stamp in ("0:00", "0:15", "0:35", "0:55", "1:15"):
            self.assertIn(stamp, self.body)
        self.assertRegex(self.body, r"The Media Buyer.{0,6}s Dilemma")
        for title in ("What Are Real Signals?", "Causal Reasoning in Action"):
            self.assertIn(title, self.body)
        self.assertIn("Governed Action &amp; 1-Click Approvals", self.body)

    def test_walkthrough_transcript_drawer(self) -> None:
        self.assertIn('id="mzkTranscript"', self.body)
        self.assertIn('id="mzkTx"', self.body)
        self.assertGreaterEqual(self.body.count("data-seek="), 10)  # chips + transcript

    # ---- page hygiene ---------------------------------------------------

    def test_viewport_theme_and_favicons(self) -> None:
        self.assertIn('name="viewport" content="width=device-width', self.body)
        self.assertIn('content="#0A1418"', self.body)
        self.assertIn('href="/assets/img/favicon.svg"', self.body)
        self.assertIn('href="/assets/img/favicon.ico"', self.body)
        self.assertIn('href="/assets/img/apple-touch-icon.png"', self.body)

    def test_assets_and_links_are_root_absolute(self) -> None:
        self.assertNotRegex(self.body, r'(src|href)="assets/')
        self.assertIn('href="/demo"', self.body)
        self.assertIn('href="/pricing"', self.body)
        self.assertIn("/contact?source=mizuki3-landing", self.body)

    def test_canonical_and_og_urls(self) -> None:
        self.assertIn('rel="canonical" href="https://mizoki3.com/mizuki3"', self.body)
        self.assertIn('property="og:url" content="https://mizoki3.com/mizuki3"', self.body)


if __name__ == "__main__":
    unittest.main()
