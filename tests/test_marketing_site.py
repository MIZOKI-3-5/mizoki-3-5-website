"""Marketing site contracts.

The /marketing landing is a self-contained Causal Growth Control page. The
existing /marketing/* pages remain the parallel multi-page experience. This
suite locks the landing's exact route, isolation, accessibility, truth, and
governance boundaries without weakening coverage for any nested surface.
"""

from html.parser import HTMLParser
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_FILE = REPO_ROOT / "marketing" / "index.html"
ENGINE_FILE = REPO_ROOT / "assets" / "js" / "media-sim.js"
CSS_FILE = REPO_ROOT / "assets" / "css" / "marketing.css"

MARKETING_LANDING = "/marketing"
MARKETING_SUBPAGES = ("/marketing/engine", "/marketing/modules",
                      "/marketing/simulator", "/marketing/walkthrough",
                      "/marketing/governance", "/marketing/counsel",
                      "/marketing/estate", "/marketing/capital",
                      "/marketing/signal", "/marketing/risk",
                      "/marketing/pricing")
MARKETING_PAGES = (MARKETING_LANDING,) + MARKETING_SUBPAGES

DIVISION_PAGES = ("/marketing/counsel", "/marketing/estate",
                  "/marketing/capital", "/marketing/signal", "/marketing/risk")


class _LandingHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.h1_count = 0
        self.scripts: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.resource_sources: list[tuple[str, str]] = []
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str,
                        attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.tags.append((tag, values))
        if values.get("id"):
            self.ids.append(values["id"])
        if values.get("href") is not None:
            self.hrefs.append(values["href"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "script":
            self.scripts.append(values)
        if tag == "link":
            self.links.append(values)
        if tag in {"img", "iframe", "video", "audio", "source"} and values.get("src"):
            self.resource_sources.append((tag, values["src"]))


class _AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        self.app = create_app(runtime=runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def page(self, path: str = "/marketing") -> str:
        return self.client.get(path).get_data(as_text=True)


class RoutingTestCase(_AppTestCase):
    def test_all_marketing_pages_serve(self) -> None:
        for path in MARKETING_PAGES + ("/marketing/", "/marketing/simulator/",
                                       "/marketing/engine/", "/marketing/governance/"):
            response = self.client.get(path, follow_redirects=True)
            self.assertEqual(200, response.status_code, path)

    def test_media_buying_redirects_permanently_into_the_site(self) -> None:
        for path in ("/media-buying", "/media-buying.html"):
            response = self.client.get(path)
            self.assertEqual(301, response.status_code, path)
            self.assertEqual("/marketing", response.headers["Location"], path)

    def test_sitemap_lists_the_site_not_the_redirect(self) -> None:
        body = self.client.get("/sitemap.xml").get_data(as_text=True)
        # A/B/C test-design fix (2026-08-22): the /marketing LANDING is
        # noindex,follow with canonical → /signal, so listing it would be a
        # contradictory signal — the sub-pages (not test variants) stay.
        for path in MARKETING_SUBPAGES:
            self.assertIn(f"https://mizoki3.com{path}</loc>", body, path)
        self.assertNotIn("https://mizoki3.com/marketing</loc>", body)
        self.assertIn("https://mizoki3.com/signal</loc>", body)
        self.assertNotIn("/media-buying", body)

    def test_shared_assets_are_served(self) -> None:
        for asset in ("/assets/js/media-sim.js", "/assets/css/marketing.css"):
            self.assertEqual(200, self.client.get(asset).status_code, asset)


class ParallelPreviewTestCase(_AppTestCase):
    """Nested pages remain the side-by-side parallel experience."""

    def test_compare_strip_on_every_nested_marketing_page(self) -> None:
        for path in MARKETING_SUBPAGES:
            body = self.page(path)
            self.assertIn('class="compare-strip"', body, path)
            self.assertIn("nothing on the classic site is replaced", body, path)
            self.assertIn('<a href="/">View classic site →</a>', body, path)

    def test_marketing_nav_cross_links_nested_pages(self) -> None:
        for path in MARKETING_SUBPAGES:
            body = self.page(path)
            self.assertIn('href="/marketing/simulator"', body, path)
            self.assertIn('href="/marketing/walkthrough"', body, path)
            self.assertIn('href="/marketing/demo"', body, path)
            self.assertIn('href="/marketing/pricing"', body, path)
            self.assertIn('class="brand">MIZ OKI 3.5</a>', body, path)

    def test_homepage_links_marketing_but_variants_stay_isolated(self) -> None:
        # Baseline moved with the owner-approved unified product experience
        # (#836, 2026-08-25; serving via dispatch run #107): the homepage now
        # deliberately links /marketing from its product nav. What survives of
        # the old one-way rule is A/B/C arm hygiene — the experiment variants
        # (/signal is arm A) and /demo never link into /marketing, so a
        # visitor cannot hop arms from inside the experiment surface.
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/marketing"', home)
        for path in ("/signal", "/demo"):
            body = self.client.get(path).get_data(as_text=True)
            self.assertNotIn('href="/marketing"', body, path)
            self.assertNotIn('href="/marketing/', body, path)


class MarketingLandingTestCase(_AppTestCase):
    """The standalone /marketing landing is isolated, honest, and operable."""

    def setUp(self) -> None:
        super().setUp()
        self.body = self.page()
        self.parser = _LandingHTMLParser()
        self.parser.feed(self.body)
        self.parser.close()

    def test_exact_route_serves_the_authenticated_file(self) -> None:
        response = self.client.get(MARKETING_LANDING)
        self.assertEqual(200, response.status_code)
        self.assertEqual("text/html", response.mimetype)
        self.assertEqual(PAGE_FILE.read_bytes(), response.get_data())

        slash_response = self.client.get("/marketing/")
        self.assertEqual(200, slash_response.status_code)
        self.assertEqual(response.get_data(), slash_response.get_data())

    def test_canonical_and_http_destinations_are_declared_only(self) -> None:
        # A/B/C test-design fix (2026-08-22): this landing is variant B of the
        # /signal test — its canonical and og:url point at the test's ONE
        # indexed URL, its own URL serves noindex,follow, and every CTA rides
        # the tracked /go/pilot redirect (bare mailto: is no longer a legal
        # destination here; the redirect resolves to the approved mailto).
        canonical = "https://mizoki3.com/signal"
        self.assertIn(f'<link rel="canonical" href="{canonical}">', self.body)
        self.assertIn(f'<meta property="og:url" content="{canonical}">', self.body)
        self.assertIn('<meta name="robots" content="noindex,follow">', self.body)
        self.assertNotIn(f'{canonical}/"', self.body)

        http_urls = re.findall(r'https?://[^\s"\'<>]+', self.body)
        self.assertTrue(http_urls)
        # Owner directive 2026-09-16: the public Decision Studio's /marketing page is
        # the one sanctioned off-site destination (exact URL, nav + hero link).
        studio = "https://decisionstudio.mizoki3.com/marketing"
        self.assertEqual({canonical, studio}, set(http_urls))

        for href in self.parser.hrefs:
            allowed = (
                href == canonical
                or href == studio
                or href == "/animation"
                or href.startswith("#")
                or href.startswith("/go/pilot?cta=marketing-")
            )
            self.assertTrue(allowed, f"forbidden landing destination: {href}")

    def test_self_contained_page_has_no_network_or_route_side_effects(self) -> None:
        self.assertFalse(
            [script for script in self.parser.scripts if script.get("src")],
            "landing scripts must stay inline",
        )
        self.assertFalse(
            [link for link in self.parser.links
             if "stylesheet" in (link.get("rel") or "").split()],
            "landing styles must stay inline",
        )
        self.assertFalse(self.parser.resource_sources)
        self.assertFalse(
            [attrs for tag, attrs in self.parser.tags
             if tag == "form" and attrs.get("action")],
            "landing forms must not submit to any route",
        )
        for marker in (
            "fetch(", "XMLHttpRequest", "WebSocket",
            "EventSource", "localStorage", "sessionStorage", "serviceWorker",
            "document.cookie", "indexedDB", "window.location",
        ):
            self.assertNotIn(marker, self.body, marker)
        # A/B/C test-design fix (2026-08-22): the page carries EXACTLY ONE
        # declared network side effect — the tier-3 goal beacon posting to
        # /api/abtest/goal (cross-file byte parity pinned in test_abtest).
        # Everything else above stays forbidden.
        self.assertEqual(
            1, self.body.count('navigator.sendBeacon("/api/abtest/goal"'))
        self.assertEqual(1, self.body.count('"/api/abtest/goal"'))
        self.assertIn('<script data-abtest="goal-beacon">', self.body)
        self.assertNotRegex(
            self.body,
            r'(?:href|src|action)=["\']/(?:signal|media|marketing/|demo|api|admin)',
        )

    def test_landmarks_fragments_and_tabs_are_accessible(self) -> None:
        self.assertEqual(1, self.parser.h1_count)
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        self.assertIn("marketing-main", self.parser.ids)
        self.assertIn('href="#marketing-main"', self.body)

        for href in self.parser.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], self.parser.ids, href)

        tabs = [
            attrs for tag, attrs in self.parser.tags
            if tag == "button" and attrs.get("role") == "tab"
        ]
        panels = [
            attrs for tag, attrs in self.parser.tags
            if attrs.get("role") == "tabpanel"
        ]
        self.assertEqual(6, len(tabs))
        self.assertEqual(1, len(panels))
        self.assertEqual("scenario-panel", tabs[0].get("aria-controls"))
        self.assertEqual("0", panels[0].get("tabindex"))
        for key in (
            "ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End",
        ):
            self.assertIn(key, self.body)

    def test_decision_graph_loop_and_jobs_preserve_the_product_contract(self) -> None:
        for marker in ("Diagnose", "Prove", "Decide", "Govern"):
            self.assertIn(f"<h3>{marker}</h3>", self.body, marker)

        graph = ("Signal", "Entity", "Cause", "Objective",
                 "Policy", "Action", "Outcome")
        graph_positions = [
            self.body.index(f"<strong>{marker}</strong>") for marker in graph
        ]
        self.assertEqual(graph_positions, sorted(graph_positions))

        loop = ("Sense", "Reason", "Plan", "Validate", "Decide", "Act", "Learn")
        loop_positions = [
            self.body.index(f"<h3>{marker}</h3>",
                            self.body.index('class="loop"'))
            for marker in loop
        ]
        self.assertEqual(loop_positions, sorted(loop_positions))
        self.assertEqual(6, self.body.count('<article class="job">'))

        for marker in (
            "SESSION OUTCOME FORECAST", "TREATMENT ASSIGNMENT",
            "TREATMENT EFFECT", "No-action remains eligible.",
        ):
            self.assertIn(marker, self.body)

    def test_intent_privacy_claims_and_authority_stay_bounded(self) -> None:
        for marker in (
            "Preview · in development",
            "DISALLOWED_KEYSTROKE_DYNAMICS",
            "Keystroke dynamics are prohibited.",
            "SHADOW / NO ACTION",
            "RECOMMEND / NO MUTATION",
            "HUMAN APPROVAL REQUIRED",
            "rollback",
            "Illustrative composite scenarios",
            "never a guaranteed outcome",
            "A 90-day Causal Growth Control Pilot.",
        ):
            self.assertIn(marker, self.body, marker)

    def test_six_scenarios_are_deterministic_and_keyboard_wired(self) -> None:
        # v1.3 grew the trace to six governed scenarios (the F3/F4/F5
        # frontiers each demonstrate their gate through one).
        for scenario in ("cpa", "margin", "creative", "inventory", "geo", "treasury"):
            self.assertIn(f'data-scenario="{scenario}"', self.body)
            self.assertRegex(self.body, rf"\b{scenario}:\s*\{{")
        for marker in (
            "scenario-incident", "scenario-evidence", "scenario-hypothesis",
            "scenario-confidence", "scenario-plan", "scenario-verdict",
        ):
            self.assertIn(f'id="{marker}"', self.body)
        self.assertNotIn("Math.random", self.body)
        self.assertNotIn("Date.now", self.body)


POSTURE_RAIL_LABELS = (
    "Current posture · Recommend-only",
    "MEASUREMENT_WRITEBACK · OFF",
    "NET_YIELD_WRITEBACK · OFF",
    "Intent evidence · Shadow / no action",
    "O-1 privacy lock · Enforced",
)

TEN_QUESTIONS = (
    "What changed?", "Which entities?", "What may explain it?",
    "Which objective?", "Which policy applies?", "What could we do?",
    "What could go wrong?", "What did we predict?", "What occurred?",
    "What must change?",
)

FRONTIER_STATUSES = (
    "IN BUILD · PROVISIONAL",
    "IN BUILD · DATA-GATED",
    "IN BUILD · OBSERVE-ONLY",
    "IN BUILD · PER-ACTION APPROVAL",
    "IN BUILD · CONFIG-DECLARED",
)

PASSPORT_FIELDS = (
    "decision_id", "loop_id", "job_id", "signal_refs",
    "action_dispatch_or_veto",
)

# The remaining §6.6 passport fields appear on the page as reader-facing
# prose rather than snake_case tokens — pinned in that form (verifier
# finding 1, 2026-08-19).
PASSPORT_FIELDS_PROSE = (
    "ranked hypotheses", "Selected + rejected plans", "Gate results",
    "DEL breakdown", "autonomy level", "approval record",
    "rollback reference", "Measurement window", "realized outcome",
    "learning-update reference", "tenant",
)

O1_DENIAL_LINE = ("Raw keys · text · cadence · dwell or flight time · typing "
                  "profiles · audio · gaze · fine individual geolocation · "
                  "sensitive-trait inference")


def _v13_contract_violations(body: str) -> list[str]:
    """Named invariant checks for the v1.3 landing, used in BOTH directions:
    the real page must return [], and each seeded §8.2 mutation must return
    its named violation — an invariant proven in only one direction is an
    invariant nobody has checked."""
    violations: list[str] = []
    urls = set(re.findall(r'https?://[^\s"\'<>]+', body))
    # A/B/C test-design fix (2026-08-22): the landing is variant B of the
    # /signal test, so its one permitted absolute URL is the test's canonical
    # (rel=canonical + og:url → /signal). Owner directive 2026-09-16 adds ONE
    # sanctioned destination: the public Decision Studio's own /marketing page,
    # exact URL. Anything else still fires (the seeded cdn.example.com proves it).
    if urls - {"https://mizoki3.com/signal", "https://decisionstudio.mizoki3.com/marketing"}:
        violations.append("external-or-noncanonical-url")
    if re.search(r'(?:href|src|action)=["\']/(?:signal|media|marketing/|demo|api|admin)',
                 body) or 'href="/"' in body:
        violations.append("internal-route-link")
    for flag in ("MEASUREMENT_WRITEBACK · OFF", "NET_YIELD_WRITEBACK · OFF"):
        if flag not in body:
            violations.append(f"writeback-not-visibly-off:{flag.split(' ')[0]}")
    if O1_DENIAL_LINE not in body or "DISALLOWED_KEYSTROKE_DYNAMICS" not in body:
        violations.append("o1-denial-missing")
    if "No F3-originated action can reach a platform adapter" not in body:
        violations.append("f3-dispatch-guard-missing")
    if "Every reservation halts for Level 2 approval" not in body:
        violations.append("f4-approval-guard-missing")
    if "DATA_INSUFFICIENT" not in body:
        violations.append("f2-data-gate-missing")
    if "NOT_CONFIGURED" not in body:
        violations.append("f5-config-gate-missing")
    # Copy checks run on VISIBLE text only — CSS is full of "100%" and the
    # reader never sees a stylesheet (same reduction content_qa applies).
    visible = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    visible = re.sub(r"<style\b.*?</style>", " ", visible, flags=re.S | re.I)
    visible = re.sub(r"<script\b.*?</script>", " ", visible, flags=re.S | re.I)
    visible = re.sub(r"<[^>]+>", " ", visible)
    # Affirmative outcome promises: negated forms ("never a guaranteed
    # outcome" — the discipline itself) stay legal; anything else is not.
    for m in re.finditer(r"\bguarantee(?:s|d)?\b", visible, re.I):
        if not re.search(r"(?:never a|not|no)\s*$",
                         visible[max(0, m.start() - 12):m.start()]):
            violations.append("affirmative-guarantee")
            break
    # Bare performance figures: the visible copy carries ZERO digit-adjacent
    # %/×/$ figures by design — a customer-results number can only arrive as
    # a regression, so any at all is a violation on this surface.
    if re.search(r"\d+(?:\.\d+)?\s?(?:%|×(?!\d))|\$\s?\d", visible):
        violations.append("bare-performance-figure")
    return violations


class GrowthControlV13ContractTestCase(_AppTestCase):
    """The v1.3 growth-control landing contract (master prompt §8.2)."""

    def setUp(self) -> None:
        super().setUp()
        self.body = self.page()

    def test_version_comment_and_resilience_blocks_present(self) -> None:
        self.assertIn("marketing-growth-control-v1.3", self.body)
        self.assertIn("@media print", self.body)
        self.assertIn("<noscript>", self.body)
        self.assertIn("prefers-reduced-motion", self.body)
        self.assertIn(":focus-visible", self.body)
        self.assertIn("@media (max-width", self.body)

    def test_posture_rail_renders_all_five_exact_labels(self) -> None:
        for label in POSTURE_RAIL_LABELS:
            self.assertIn(label, self.body, label)

    def test_required_hero_and_four_loops(self) -> None:
        self.assertIn("Know why performance moved.", self.body)
        self.assertIn("Govern what happens next.", self.body)
        self.assertIn("ranks the most supportable causal hypothesis", self.body)
        for loop in ("Evidence + intent", "Causal measurement",
                     "Decision + passport", "Outcome + learning"):
            self.assertIn(loop, self.body, loop)

    def test_ten_event_contract_questions_in_order(self) -> None:
        positions = [self.body.index(q) for q in TEN_QUESTIONS]
        self.assertEqual(positions, sorted(positions))

    def test_five_frontiers_carry_their_exact_gates(self) -> None:
        for status in FRONTIER_STATUSES:
            self.assertIn(status, self.body, status)
        for gate in (
            "at least two observed quarters per cohort",
            "No F3-originated action can reach a platform adapter",
            "Every reservation halts for Level 2 approval",
            "Two clean cycles",
            "NOT_CONFIGURED",
            "DATA_INSUFFICIENT",
            "Generated creative always requires human approval.",
        ):
            self.assertIn(gate, self.body, gate)

    def test_scenario_traces_end_in_governed_states(self) -> None:
        # §6.5: the frontier scenarios must end exactly where their gates
        # say — recommend, halt, or veto; never a dispatched action.
        for outcome in ("RECOMMEND / NO DISPATCH", "HALT AT APPROVAL",
                        "POLICY VETO"):
            self.assertIn(outcome, self.body, outcome)

    def test_no_fabricated_social_proof(self) -> None:
        for banned in ("testimonial", "Trusted by", "as seen in"):
            self.assertNotRegex(self.body, re.compile(re.escape(banned), re.I),
                                banned)

    def test_validation_passport_is_canonical_and_complete(self) -> None:
        self.assertIn("ValidationPassport", self.body)
        self.assertNotIn("DecisionProof", self.body)
        for field in PASSPORT_FIELDS + PASSPORT_FIELDS_PROSE:
            self.assertIn(field, self.body, field)
        self.assertIn("SHA-256", self.body)
        self.assertIn("a DEL score never overrides a failed hard constraint",
                      self.body)

    def test_intent_engine_modules_retention_and_o1(self) -> None:
        for module in ("PassiveAttentionSequence", "SessionOutcomeForecast",
                       "CreativeSemanticProfile", "IntentHypothesis"):
            self.assertIn(module, self.body, module)
        for marker in (
            "I-01", "I-02", "I-03", "I-04", "I-05",
            "purge when the session ends",
            "strict TTL", "erasure",
            "Consent failure means no processing",
            "Sensitive-category inference is denied at ingest and hypothesis "
            "creation",
            "Probabilistic identities do not enter causal-effect math",
            O1_DENIAL_LINE,
            "No persistent psychological dossier is created.",
        ):
            self.assertIn(marker, self.body, marker)

    def test_measurement_honesty_and_activation_gates(self) -> None:
        for marker in (
            "Forecasting is not incrementality",
            "Prediction never grades itself",
            "registered holdout",
            "Missing required costs leave a row incomplete",
            "at least one observed return cycle",
            "no claim that the platform currently bids on net contribution",
            "Verified pilot numbers—not marketing copy—are what may later "
            "flip Preview labels",
            "ILLUSTRATIVE VALIDATIONPASSPORT",
            "BUILD TARGET",
        ):
            self.assertIn(marker, self.body, marker)

    def test_contract_invariants_hold_and_each_seeded_mutation_fires(self) -> None:
        self.assertEqual([], _v13_contract_violations(self.body))
        seeds = (
            ("external-or-noncanonical-url",
             self.body.replace("</body>",
                               '<img src="https://cdn.example.com/x.png"></body>')),
            ("internal-route-link",
             self.body.replace("</body>", '<a href="/signal">Signal</a></body>')),
            ("writeback-not-visibly-off:NET_YIELD_WRITEBACK",
             self.body.replace("NET_YIELD_WRITEBACK · OFF",
                               "NET_YIELD_WRITEBACK · ON")),
            ("writeback-not-visibly-off:MEASUREMENT_WRITEBACK",
             self.body.replace("MEASUREMENT_WRITEBACK · OFF",
                               "MEASUREMENT_WRITEBACK · ON")),
            ("o1-denial-missing",
             self.body.replace("DISALLOWED_KEYSTROKE_DYNAMICS", "")),
            ("f3-dispatch-guard-missing",
             self.body.replace(
                 "No F3-originated action can reach a platform adapter",
                 "F3 actions dispatch directly to platform adapters")),
            ("f4-approval-guard-missing",
             self.body.replace("Every reservation halts for Level 2 approval",
                               "Reservations execute automatically")),
            ("f2-data-gate-missing",
             self.body.replace("DATA_INSUFFICIENT", "extrapolated")),
            ("f5-config-gate-missing",
             self.body.replace("NOT_CONFIGURED", "always active")),
            ("affirmative-guarantee",
             self.body.replace("</body>",
                               "<p>We guarantee the lift.</p></body>")),
            ("bare-performance-figure",
             self.body.replace("</body>",
                               "<p>Customers see a 34% lift.</p></body>")),
            ("bare-performance-figure",  # the $ form (verifier finding 1)
             self.body.replace("</body>",
                               "<p>Saves $50,000 per quarter.</p></body>")),
        )
        for expected, mutated in seeds:
            self.assertIn(expected, _v13_contract_violations(mutated),
                          f"seeded mutation not caught: {expected}")


class NestedVocabularyTestCase(_AppTestCase):
    """The unchanged nested pages retain their translated vocabulary."""

    RAW_TERMS = (
        "Canonical Event Envelope",
        "Temporal-Causal Knowledge Base",
        "Domain Intelligence Cell",
        "SRPVDAL",
        "Decision Control Plane",
        "Immutable Learning Ledger",
        "Tenant Isolation",
        "No-Action Counterfactual",
    )

    def test_sub_pages_carry_no_raw_jargon_at_all(self) -> None:
        for path in MARKETING_SUBPAGES:
            body = self.page(path)
            for raw in self.RAW_TERMS:
                self.assertNotIn(raw, body, f"{raw} on {path}")


class SimulatorContractTestCase(_AppTestCase):
    """The legacy DemoWidget remains pinned on its dedicated page."""

    SIM_PAGES = ("/marketing/simulator",)

    def test_layout_columns_and_height_spec(self) -> None:
        css = CSS_FILE.read_text(encoding="utf-8")
        self.assertIn("height: 650px", css)
        for path in self.SIM_PAGES:
            body = self.page(path)
            self.assertIn("Interactive Controls", body, path)
            self.assertIn("Execution Monitor", body, path)
            self.assertIn('href="/assets/css/marketing.css', body, path)

    def test_three_scenarios(self) -> None:
        for path in self.SIM_PAGES:
            body = self.page(path)
            for scenario in ("Landing Page Latency Spike",
                             "SKU Out-of-Stock Crisis",
                             "Pixel Attribution Drift"):
                self.assertIn(scenario, body, f"{scenario} on {path}")
            for value in ('value="latency"', 'value="stock"', 'value="pixel"'):
                self.assertIn(value, body, f"{value} on {path}")

    def test_slider_ranges_match_the_spec(self) -> None:
        for path in self.SIM_PAGES:
            body = self.page(path)
            self.assertIn('id="simLatency" min="0.5" max="6.0" step="0.1"', body, path)
            self.assertIn('id="simInventory" min="0" max="1000"', body, path)
            self.assertIn('id="simBudget" min="1000" max="20000"', body, path)

    def test_safety_policy_values(self) -> None:
        for path in self.SIM_PAGES:
            body = self.page(path)
            self.assertIn("2.2×", body, path)
            self.assertIn("$5,000", body, path)
            self.assertIn('id="simFloor"', body, path)
            self.assertIn('id="simCap"', body, path)

    def test_all_seven_phase_blocks_render(self) -> None:
        for path in self.SIM_PAGES:
            body = self.page(path)
            for phase in ("Sense", "Reason", "Plan", "Validate", "Decide", "Act", "Learn"):
                self.assertIn(f'id="ph{phase}"', body, f"{phase} on {path}")

    def test_simulator_is_honestly_labeled_with_noscript_fallback(self) -> None:
        for path in self.SIM_PAGES:
            body = self.page(path)
            self.assertIn("Illustrative scenario", body, path)
            self.assertIn("<noscript>", body, path)
            self.assertIn('href="/marketing/demo"', body, path)


class EngineDisciplineTestCase(unittest.TestCase):
    """The JS engine: deterministic, claims-clean, veto-honest."""

    def setUp(self) -> None:
        self.source = ENGINE_FILE.read_text(encoding="utf-8")
        literals = re.findall(r'"((?:[^"\\\n]|\\.)*)"', self.source)
        literals += re.findall(r"'((?:[^'\\\n]|\\.)*)'", self.source)
        self.strings = "\n".join(literals)

    def test_engine_exists_and_pages_load_it(self) -> None:
        self.assertTrue(ENGINE_FILE.is_file())
        for name in ("simulator.html", "walkthrough.html"):
            page = (REPO_ROOT / "marketing" / name).read_text(encoding="utf-8")
            self.assertIn('src="/assets/js/media-sim.js', page, name)

    def test_deterministic_no_randomness_no_clock_ids(self) -> None:
        self.assertNotIn("Math.random", self.source)
        self.assertNotIn("Date.now", self.source)

    def test_policy_constants_match_the_page(self) -> None:
        self.assertIn("ROAS_FLOOR = 2.2", self.source)
        self.assertIn("MAX_SHIFT = 5000", self.source)

    def test_approve_gate_and_learn_tickers(self) -> None:
        self.assertIn("Approve Strategy", self.source)
        self.assertIn("Wasted Spend Prevented", self.source)
        self.assertIn("ROAS Preserved", self.source)

    def test_veto_is_a_first_class_outcome(self) -> None:
        self.assertIn("VETOED — nothing executed · human override required",
                      self.source)
        # A veto still teaches the system.
        self.assertIn("The veto is recorded too", self.source)

    def test_dispatch_is_marked_simulated(self) -> None:
        self.assertIn("(simulated)", self.strings + self.source)

    def test_banned_claims_vocabulary_absent(self) -> None:
        banned = [
            r"mind[\s-]?reading",
            r"we (?:are )?listen",
            r"will buy",
            r"guarantee",
            r"risk[\s-]?free",
            r"revolutionary",
            r"best[\s-]in[\s-]class",
            r"act now",
            r"limited[\s-]time",
            r"don'?t miss",
        ]
        surfaces = {"engine strings": self.strings}
        for name in ("simulator.html", "walkthrough.html"):
            surfaces[name] = (REPO_ROOT / "marketing" / name).read_text(encoding="utf-8")
        for label, text in surfaces.items():
            for pattern in banned:
                self.assertIsNone(
                    re.search(pattern, text, re.IGNORECASE),
                    f"banned claims phrase in {label}: {pattern}",
                )


class StoryboardTestCase(_AppTestCase):
    """The 90-second walkthrough remains pinned on its dedicated page."""

    VID_PAGES = ("/marketing/walkthrough",)

    SCENES = (
        ("0:00", "The Media Buyer's Nightmare", "0"),
        ("0:15", "Redefining Cross-Stack Signals", "15"),
        ("0:35", "Finding the True Root Cause", "35"),
        ("0:55", "1-Click Governed Approvals", "55"),
        ("1:15", "Compounding Organizational Memory", "75"),
    )

    def test_five_scenes_with_timestamps_and_seek_targets(self) -> None:
        for path in self.VID_PAGES:
            body = self.page(path)
            for stamp, title, seek in self.SCENES:
                self.assertIn(stamp, body, f"{stamp} on {path}")
                self.assertIn(title, body, f"{title} on {path}")
                self.assertIn(f'data-t="{seek}"', body, f"{seek} on {path}")

    def test_transcript_drawer_present(self) -> None:
        for path in self.VID_PAGES:
            body = self.page(path)
            self.assertIn('id="vidTranscript"', body, path)
            self.assertIn('id="vidTransToggle"', body, path)
            self.assertEqual(5, body.count('class="vt-row"'), path)

    def test_player_chrome(self) -> None:
        for path in self.VID_PAGES:
            body = self.page(path)
            for el in ('id="vidPlay"', 'id="vidBar"', 'id="vidTime"', 'id="vidPlate"'):
                self.assertIn(el, body, f"{el} on {path}")


class HygieneTestCase(_AppTestCase):
    """Shared-shell contracts remain enforced on the nested pages."""

    def test_root_absolute_assets_only(self) -> None:
        for path in MARKETING_SUBPAGES:
            body = self.page(path)
            self.assertIn('href="/assets/css/styles.css"', body, path)
            self.assertNotIn('href="assets/', body, path)
            self.assertNotIn('src="assets/', body, path)
            self.assertIsNone(re.search(r'href="[a-z][a-z0-9-]*\.html', body), path)

    def test_icon_set_canonical_and_og(self) -> None:
        canonical = {
            path: f"https://mizoki3.com{path}" for path in MARKETING_SUBPAGES
        }
        for path, url in canonical.items():
            body = self.page(path)
            self.assertIn('href="/assets/img/favicon.svg"', body, path)
            self.assertIn('href="/assets/img/favicon.ico"', body, path)
            self.assertIn('href="/assets/img/apple-touch-icon.png"', body, path)
            self.assertIn(f'<link rel="canonical" href="{url}" />', body, path)
            self.assertIn('property="og:title"', body, path)

    def test_nav_and_shared_scripts(self) -> None:
        for path in MARKETING_SUBPAGES:
            body = self.page(path)
            self.assertIn('src="/assets/js/nav-mobile.js"', body, path)
            self.assertIn('class="nav-links"', body, path)

    def test_no_placeholder_links(self) -> None:
        for path in MARKETING_PAGES:
            self.assertNotIn('href="#"', self.page(path), path)


    def test_contact_linked_pages_are_routed(self) -> None:
        # /contact links /intelligence and /vision; the 2026-08-03 audit found
        # them unrouted (404 in production). The templates exist — serve them.
        for path in ("/intelligence", "/vision"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)
            self.assertIn("MIZ OKI", response.get_data(as_text=True), path)

class FullSiteMirrorTestCase(_AppTestCase):
    """The ENTIRE site is browsable inside /marketing — mirrored from the
    same canon files on disk (never modified), links rewritten to stay in
    the prefix, previews marked noindex."""

    MIRROR_PAGES = (
        "/marketing/demo", "/marketing/demo/signal", "/marketing/demo/counsel",
        "/marketing/demo/estate", "/marketing/demo/capital",
        "/marketing/demo/risk", "/marketing/demo/nexus",
    )

    def test_every_mirror_serves(self) -> None:
        for path in self.MIRROR_PAGES + ("/marketing/executive-briefing/",):
            response = self.client.get(path, follow_redirects=True)
            self.assertEqual(200, response.status_code, path)

    def test_mirrors_carry_strip_and_noindex(self) -> None:
        for path in self.MIRROR_PAGES:
            body = self.page(path)
            self.assertIn('class="compare-strip"', body, path)
            self.assertIn('<a href="/">View classic site →</a>', body, path)
            self.assertIn('<meta name="robots" content="noindex" />', body, path)
            self.assertIn("/assets/css/marketing.css", body, path)

    def test_mirror_links_stay_inside_the_prefix(self) -> None:
        hub = self.page("/marketing/demo")
        for desk in ("signal", "counsel", "estate", "capital", "risk", "nexus"):
            self.assertIn(f'href="/marketing/demo/{desk}"', hub, desk)
        self.assertNotIn('href="/demo', hub.replace('href="/marketing/demo', ""))

    def test_mirror_brand_links_to_marketing_home(self) -> None:
        for path in ("/marketing/demo", "/marketing/demo/capital"):
            body = self.page(path)
            self.assertIn('href="/marketing" class="brand"', body, path)
            self.assertNotIn('href="/" class="brand"', body, path)

    def test_demo_mirrors_keep_seeded_replay_embedding(self) -> None:
        body = self.page("/marketing/demo/signal?scenario=leadgen_cpa&seed=7")
        self.assertIn('data-scenario="leadgen_cpa"', body)
        self.assertIn('data-seed="7"', body)

    def test_briefing_mirror_serves_its_relative_assets(self) -> None:
        for path in ("/marketing/executive-briefing/css/briefing.css",
                     "/marketing/executive-briefing/js/app.js",
                     "/marketing/executive-briefing/js/guide.js"):
            self.assertEqual(200, self.client.get(path).status_code, path)

    def test_root_pages_stay_pristine(self) -> None:
        # Building the redesigned site must never mutate what root serves.
        for path in ("/signal", "/demo", "/pricing", "/counsel", "/risk"):
            body = self.client.get(path).get_data(as_text=True)
            self.assertNotIn("compare-strip", body, path)
            self.assertNotIn('content="noindex"', body, path)
            self.assertNotIn('href="/marketing', body, path)




class FullSitePagesTestCase(_AppTestCase):
    """Pages 2/3/5 of the Master Full-Site prompt, translated to this stack."""

    def test_engine_page_walks_all_seven_stages(self) -> None:
        body = self.page("/marketing/engine")
        self.assertIn("7-Stage Governed Decision System", body)
        for gist in ("Full-Stack Radar", "Root Cause AI", "Actionable Strategy",
                     "Safety Brakes", "1-Click Approvals", "Hands-Free Execution",
                     "Compounding ROI Memory"):
            self.assertIn(gist, body, gist)
        self.assertIn("negative keyword lists", body)
        self.assertIn("Opportunity Cost Check", body)
        self.assertEqual(7, body.count('class="eng-stage"'))

    def test_modules_page_shows_all_four_channel_modules(self) -> None:
        body = self.page("/marketing/modules")
        for module in ("Google Ads Module", "Meta &amp; Paid Social Module",
                       "E-Commerce &amp; Inventory Module",
                       "ESP &amp; Retention Module"):
            self.assertIn(module, body, module)
        for feature in ("SearchStream coverage", "MCC multi-account",
                        "conversion lag", "CAPI pixel lag",
                        "Automated ad pauses for zero-stock products",
                        "Automated suppression updates"):
            self.assertIn(feature.lower(), body.lower(), feature)
        # Modules are the growth mechanism — the not-just-five story.
        self.assertIn("onboards as a new module", body)

    def test_governance_page_modes_and_shield(self) -> None:
        body = self.page("/marketing/governance")
        for mode in ("Observe Mode", "Bounded Autonomy", "Full Autonomy"):
            self.assertIn(mode, body, mode)
        self.assertIn("instant rollback", body)
        for cell in ("Tenant memory isolation", "Customer-managed keys",
                     "No cross-account bleed", "Tamper-evident audit trails"):
            self.assertIn(cell, body, cell)
        self.assertIn("Safety Guardrail Engine", body)

    def test_sitemap_lists_all_six_marketing_pages(self) -> None:
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        # Sub-pages only: the landing left the sitemap with the A/B/C
        # test-design fix (2026-08-22) — see RoutingTestCase's sitemap test.
        for path in MARKETING_SUBPAGES:
            self.assertIn(f"https://mizoki3.com{path}</loc>", sitemap, path)
        self.assertNotIn("https://mizoki3.com/marketing</loc>", sitemap)


class DivisionRedesignTestCase(_AppTestCase):
    """The complete-site redesign: every division rewritten in the
    transparent treatment — not mirrored classic pages."""

    SIGNATURES = {
        "/marketing/counsel": ("conflict", "not a law firm"),
        "/marketing/estate": ("trustee", "before ink"),
        "/marketing/capital": ("covenant", "VETOED"),
        "/marketing/signal": ("causal lift", "Mind-reading"),
        "/marketing/risk": ("veto", "say no to every other division"),
    }

    def test_division_pages_are_redesigned_not_mirrored(self) -> None:
        for path in DIVISION_PAGES:
            body = self.page(path)
            # The transparency devices, on every division page.
            self.assertIn("What we say", body, path)
            self.assertIn("What we never say", body, path)
            self.assertIn("transparent", body, path)
            self.assertIn('class="wdn-grid"', body, path)
            self.assertIn('class="worked-plate"', body, path)
            # Translated vocabulary carries the page.
            self.assertIn("7-Stage Governed Decision System", body, path)
            # No mirror injection markers — these are real pages.
            self.assertNotIn('content="noindex"', body, path)

    def test_division_signatures_stay_truthful(self) -> None:
        for path, (sig_a, sig_b) in self.SIGNATURES.items():
            body = self.page(path)
            self.assertIn(sig_a, body, f"{sig_a} on {path}")
            self.assertIn(sig_b, body, f"{sig_b} on {path}")

    def test_every_division_wires_to_its_live_desk(self) -> None:
        for path in DIVISION_PAGES:
            desk = path.rsplit("/", 1)[-1]
            body = self.page(path)
            self.assertIn(f'href="/marketing/demo/{desk}"', body, path)
            self.assertIn('href="/marketing/demo"', body, path)

    def test_pricing_redesigned_in_translated_vocabulary(self) -> None:
        body = self.page("/marketing/pricing")
        for marker in ("Priced by autonomy, not by seats.", "Core Intelligence",
                       "Operational Autonomy", "Full Governance Suite",
                       "Observe Mode", "Bounded Autonomy", "Full Autonomy",
                       "mailto:briefing@mediaintelligence.ai"):
            self.assertIn(marker, body, marker)
        # The classic pricing page's engineering terms must not leak in.
        for raw in ("SRPVDAL", "Decision Control Plane", "ReLU"):
            self.assertNotIn(raw, body, raw)

class AcquisitionShowcaseTestCase(_AppTestCase):
    """Owner mandate: every number on the acquisition pages is a software
    fact, not marketing memory. The page is generated from the runtime; this
    suite re-imports the runtime and fails if the page drifts from the code."""

    CAPABILITIES = (
        "ReLU threshold intelligence", "ReLU-gated budget reallocation",
        "Value-based bidding", "Creative fatigue", "Uplift pacing",
        "Uplift audiences", "Attribution &amp; measurement",
        "Promotion gates &amp; consent",
    )

    def test_all_named_capabilities_showcased(self) -> None:
        body = self.page("/marketing/signal")
        self.assertIn('id="acquisition"', body)
        self.assertIn('id="parameters"', body)
        for cap in self.CAPABILITIES:
            self.assertIn(cap, body, cap)

    def test_operating_parameters_match_the_runtime(self) -> None:
        from mizoki_runtime import demo_signal as ds
        body = self.page("/marketing/signal")
        self.assertIn("%.0f%%" % (ds.GATE_UPLIFT_FLOOR * 100), body)
        self.assertIn("%.2f" % ds.GATE_CONFIDENCE_FLOOR, body)
        self.assertIn("n = %d" % ds.GATE_SAMPLE_FLOOR, body)
        self.assertIn("±%.0f%%" % ds.GuardrailSet.BUDGET_SWING_CAP_PCT, body)
        self.assertIn("±%.0f%%" % ds.GuardrailSet.BID_SWING_CAP_PCT, body)
        self.assertIn("seed=%d" % ds.DEFAULT_SEED, body)
        winner = ds.SCENARIOS["ecommerce_roas"]["planned_actions"][0]
        self.assertIn(winner[1], body)                      # entity
        self.assertIn("${:,.0f}".format(winner[3]), body)   # expected value
        self.assertIn("n = %d" % winner[5], body)           # support
        self.assertIn("%.2f" % winner[4], body)             # confidence
        blocked = [a for a in ds.SCENARIOS["ecommerce_roas"]["planned_actions"]
                   if a[0].startswith("budget")
                   and a[2] > ds.GuardrailSet.BUDGET_SWING_CAP_PCT][0]
        self.assertIn("+%.0f%%" % blocked[2], body)         # the deliberate block

    def test_simulator_constants_match_engine_file(self) -> None:
        js = ENGINE_FILE.read_text(encoding="utf-8")
        body = self.page("/marketing/signal")
        roas = re.search(r"ROAS_FLOOR = ([0-9.]+)", js).group(1)
        self.assertIn(roas + "×", body)
        shift = int(re.search(r"MAX_SHIFT = ([0-9]+)", js).group(1))
        self.assertIn("${:,}".format(shift), body)
        drop = float(re.search(r"PIXEL_DROP = ([0-9.]+)", js).group(1))
        self.assertIn("%.0f%%" % (drop * 100), body)
        verified = re.search(r"VERIFIED_ROAS = ([0-9.]+)", js).group(1)
        self.assertIn(verified + "×", body)

    def test_demo_deep_links_embed_seeded_scenarios(self) -> None:
        body = self.page("/marketing/signal")
        self.assertIn(
            'href="/marketing/demo/signal?scenario=ecommerce_roas&amp;seed=42"', body)
        self.assertIn(
            'href="/marketing/demo/signal?scenario=email_reengagement&amp;seed=42"', body)
        # ...and the mirrored desk honors them for shared, seeded autoruns.
        for scenario in ("ecommerce_roas", "email_reengagement", "leadgen_cpa"):
            desk = self.page(f"/marketing/demo/signal?scenario={scenario}&seed=42")
            self.assertIn(f'data-scenario="{scenario}"', desk, scenario)
            self.assertIn('data-seed="42"', desk, scenario)

    def test_spec_and_live_labels_stay_honest(self) -> None:
        body = self.page("/marketing/signal")
        self.assertGreaterEqual(body.count('class="chip live"'), 4)
        self.assertGreaterEqual(body.count('class="chip spec"'), 3)
        self.assertIn("observe-only default", body)
        self.assertIn("Brier ≤ 0.20", body)
        self.assertIn("AUC ≥ 0.72", body)
        self.assertIn("never outcome promises", body)

class DriftGuardTestCase(unittest.TestCase):
    """The deploy-gate script must pass on this tree — the same check both
    deploy pipelines run, so losing the marketing site can never ship."""

    def test_marketing_surfaces_check_passes(self) -> None:
        import subprocess
        import sys as _sys
        result = subprocess.run(
            [_sys.executable, str(REPO_ROOT / "scripts" / "check_marketing_surfaces.py"),
             "--root", str(REPO_ROOT)],
            capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
