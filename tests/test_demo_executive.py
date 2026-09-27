"""Executive Demo (/media/demo) coverage — r1.0 (2026-09-12), placed under /media r1.1 (2026-09-13).

A single-file presenter surface: no engine run, no /api/ call, no telemetry.
Mirrors tests/test_executive_briefing.py in shape. The tests pin the route,
the SYNTHETIC watermark, the truth labels the page must keep, and the cross
links from the demo hub and the /media hero.

Owner placement ruling 2026-09-13: the page lives in the /media namespace
only (media/demo.html; slug renamed from /media/executive-demo 2026-09-14,
owner call — the old slug 308s) and nothing outside /media links to it —
the standing media-free rule for the classic site and the A/B/C arms holds,
and the demo hub keeps only the division demos. The old /demo/executive
route must answer 404.

r1.1 finalize (2026-09-14, operator prompt r1.1, inside that ruling): the page
carries the r1.1 rail line (no canonical link: noindex, see the media-contract
waivers test), its two cross links are
same-site root-relative (no target=_blank), every /media/* page's shared nav
carries a Demo entry, the pilot close offers the demo, and the short URL
/media/demo is a 308 into the canonical page. Nothing outside /media links it.

Every label below is the OFFERING_MAP v2.3 §B.6 / docs/CANON_STATUS.md state.
The close's status table is checked against the MACHINE COPY of §B.6
(contracts/mizoki_contracts/canon_status.py), so the page follows canon
mechanically: when a row's status moves there, this page must move with it.
F4 reads LIVE with its earned-authority qualifier (ruling 2026-09-13, owner
delegated — pilot armed 2026-08-24, every reservation L2-approval-gated, bounded
autonomy after two clean cycles); the cells chip carries §B.6's observe-only
qualifier. The negative assertions keep the bare, unqualified forms out.
"""

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]
MONOREPO_ROOT = REPO_ROOT.parent

_spec = importlib.util.spec_from_file_location(
    "content_qa", REPO_ROOT / "scripts" / "content_qa.py"
)
content_qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(content_qa)

# The machine copy of OFFERING_MAP §B.6 (an import-free module, loaded by path
# so the site tests need nothing extra on sys.path).
_cs_spec = importlib.util.spec_from_file_location(
    "canon_status", MONOREPO_ROOT / "contracts" / "mizoki_contracts" / "canon_status.py"
)
canon_status = importlib.util.module_from_spec(_cs_spec)
_cs_spec.loader.exec_module(canon_status)
DECLARED = {row["capability"]: row["status"] for row in canon_status.DECLARED_STATUS}

REQUIRED_STRINGS = (
    "SYNTHETIC TENANT",                      # watermark, top bar
    "demo-fixtures",                         # the synthetic tenant, named in the rail
    "MEASUREMENT_WRITEBACK · OFF",
    "NET_YIELD_WRITEBACK · OFF",
    "Net yield · in build",
    "Cells 33–36 · live · observe-only",     # deployed cells; ORACLE PARTIAL / observe-only (§B.6)
    "Intent Engine v2 · shadow · in build",
    "Privacy lock · live · owner ruling",    # O-1
    "DISALLOWED_KEYSTROKE_DYNAMICS",         # the schema rejection, on screen
    "Causal core · partial",
    "Ghost bid · proposed",
    'id="mGhost" disabled',                  # ghost bids: PROPOSED, button disabled
    "DCP · threshold gate · live",
    "PROPOSED CANON",                        # clipped-ReLU shape, drawn dashed
    "not claimed",
    "F4 · live · armed 2026-08-24",           # §B.6 LIVE (ruling 2026-09-13); pilot armed, L2-gated
    "every reservation L2-approval-gated · bounded autonomy after 2 clean cycles, 0 complete",
    "zero admissible forward labels",        # the honest close: the gate is unscored, not merely missed
    "0.72",
    "OFFERING_MAP v2.3",
    'content="noindex"',
    # Figures from docs/reports/DEMO_FIVE_ACT_TRACE_2026-08-25.json
    "SKU-DEMO-7742",
    "4047.62",
    "80.0",
)

# Labels the page must NOT carry: the bare, unqualified forms. LIVE without
# the earned-authority qualifier overstates F4; IN BUILD understates it.
FORBIDDEN_STRINGS = (
    "F4 · live since",                       # the pack's bare form — no qualifier
    "F4 · in build",                         # the pre-ruling label
    "L2-approved",                           # reads as already approved; the reservation is L2-approval-GATED
)

FORBIDDEN_PATTERNS = (
    r"/api/",                                # zero backend calls
    r"navigator\.sendBeacon",                # zero telemetry
    r"\bfetch\s*\(",                         # no network at all beyond fonts
    r"XMLHttpRequest",
    r"(?<!never )(?<!Never )(?<!Never )mind[- ]reading",   # anticipatory intent: the phrase
                                                            # may only appear negated
    # No third-party host except Google Fonts (the paste's "fonts excepted");
    # w3.org is the SVG namespace, mizoki3.com is same-origin copy.
    r"https?://(?!fonts\.googleapis\.com|fonts\.gstatic\.com|mizoki3\.com|www\.w3\.org)",
)


class ExecutiveDemoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.body = self.client.get("/media/demo").get_data(as_text=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # ---- route ----------------------------------------------------------

    def test_route_serves_html(self) -> None:
        response = self.client.get("/media/demo")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/html")
        self.assertIn("<title>MIZ OKI Media Executive Demo</title>", self.body)

    def test_trailing_slash_and_legacy_filename_tolerated(self) -> None:
        # strict_slashes=False: the slash form is served in place (no
        # redirect); the legacy .html filename serves the same file.
        for path in ("/media/demo/", "/media/demo.html"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.get_data(as_text=True), self.body, path)

    def test_served_bytes_are_the_file_on_disk(self) -> None:
        on_disk = (REPO_ROOT / "media" / "demo.html").read_text(encoding="utf-8")
        self.assertEqual(on_disk, self.body)

    def test_old_demo_namespace_route_is_gone(self) -> None:
        # The /demo namespace carries only the hub card's link (owner ruling
        # 2026-09-13); the page itself is served from /media alone.
        for path in ("/demo/executive", "/demo/executive/", "/demo-executive.html"):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    # ---- truth labels ---------------------------------------------------

    def test_truth_labels_present(self) -> None:
        for needle in REQUIRED_STRINGS:
            self.assertIn(needle, self.body, needle)

    def test_canon_corrections_hold(self) -> None:
        for needle in FORBIDDEN_STRINGS:
            self.assertNotIn(needle, self.body, needle)

    # page row label -> EVERY capability the row groups, in the machine copy
    # of §B.6 (an empty tuple = a PROPOSED item the canon table does not
    # carry; pinned statically). A grouped row is only honest while all of
    # its capabilities share one status — the test fails, and the row must
    # be split, the moment any one of them moves independently.
    FRONTIER = {
        "F1": "F1 creative unbundling",
        "F2": "F2 multi-quarter LTV regimes",
        "F3": "F3 supply-chain / inventory sync",
        "F4": "F4 auto micro-geo calibration",
        "F5": "F5 treasury-gated spend governance",
    }
    B6_ROWS = {
        "SRPVDAL loop · Decision Control Plane": (
            "SRPVDAL state machine, Decision Control Plane, DEL scoring, "
            "autonomy ladder, audit ledger",
        ),
        "Connector gateway · canonical envelope": ("Connector gateway & canonical envelope",),
        "F4 micro-geo calibration": (FRONTIER["F4"],),
        "Causal proof core": ("Causal proof core (meta-learners, refutation, triangulation)",),
        "ORACLE cells 33–36": ("ORACLE intent cells 33–36; Growth Decision Graph intent edges",),
        "Intent Engine v2 · Net Yield lane": (
            "Intent Engine v2 modules I-01…I-05",
            "Net Yield lane (order economics, cohorts, writeback dry-run)",
            FRONTIER["F1"], FRONTIER["F2"], FRONTIER["F3"], FRONTIER["F5"],
        ),
        "Ghost bids · clipped-ReLU authorization shape": (),
    }

    def test_status_table_matches_offering_map_b6(self) -> None:
        # The close's "What is real today" table, row by row, against the
        # MACHINE copy of §B.6 — the page can never carry a status the canon
        # table does not.
        rows = {}
        for label, capabilities in self.B6_ROWS.items():
            if not capabilities:
                rows[label] = "proposed"
                continue
            statuses = {}
            for capability in capabilities:
                self.assertIn(capability, DECLARED, capability)
                statuses[capability] = DECLARED[capability].lower()
            self.assertEqual(
                len(set(statuses.values())), 1,
                f"{label}: grouped capabilities no longer share one status "
                f"({statuses}) — split the page row",
            )
            rows[label] = next(iter(statuses.values()))
        self.assertEqual(rows["F4 micro-geo calibration"], "live")   # ruling 2026-09-13
        for label, status in rows.items():
            match = re.search(re.escape(label) + r'[^\n]*?<span class="chip [a-z]+">([a-z ]+)</span>', self.body)
            self.assertIsNotNone(match, label)
            self.assertEqual(match.group(1), status, label)

    def test_in_build_note_lists_exactly_the_in_build_frontier_surfaces(self) -> None:
        # The note under the table names the IN BUILD frontier surfaces; it
        # is derived from the machine copy so a LIVE surface (F4, ruling
        # 2026-09-13) can never be listed as IN BUILD one line under its
        # own LIVE row.
        in_build = [f for f, capability in self.FRONTIER.items()
                    if DECLARED[capability] == "IN BUILD"]
        self.assertEqual(in_build, ["F1", "F2", "F3", "F5"])
        self.assertIn(
            "IN BUILD rows — Intent Engine v2, the Net Yield lane, "
            + ", ".join(in_build) + " — are Preview · in development.",
            self.body,
        )
        self.assertNotIn("F1–F5", self.body)

    def test_synthetic_watermark_in_top_bar_and_rail(self) -> None:
        self.assertIn("SYNTHETIC TENANT", self.body)
        self.assertGreaterEqual(self.body.count("demo-fixtures"), 2)

    # ---- self-containment -----------------------------------------------

    def test_no_backend_telemetry_or_foreign_hosts(self) -> None:
        for pattern in FORBIDDEN_PATTERNS:
            self.assertIsNone(re.search(pattern, self.body), pattern)

    def test_no_external_script_tags(self) -> None:
        self.assertIsNone(re.search(r"<script[^>]*\bsrc=", self.body))

    # ---- cross links and gates ------------------------------------------

    def test_hub_does_not_reference_the_demo(self) -> None:
        # Owner ruling 2026-09-13 (second reading): the demo hub keeps only
        # the division demos; nothing outside /media links to this page.
        hub = self.client.get("/demo", follow_redirects=True).get_data(as_text=True)
        self.assertNotIn("executive-demo", hub)
        self.assertNotIn('"/media/demo"', hub)
        self.assertNotIn("Executive Demo — Media &amp; Signals", hub)
        # The legacy route must be gone from the hub too (review finding on
        # #1027): a stale href could survive without either string above.
        self.assertNotIn("/demo/executive", hub)
        self.assertNotIn("demo-executive", hub)
        # The evaluator track stays.
        self.assertIn('href="/demo/signal"', hub)

    def test_media_hero_links_the_demo(self) -> None:
        media = self.client.get("/media", follow_redirects=True).get_data(as_text=True)
        self.assertIn('href="/media/demo">Run the executive demo →</a>', media)
        self.assertIn("Explore the 90-Day Pilot", media)

    def test_not_in_sitemap_while_noindexed(self) -> None:
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertNotIn("/media/demo", sitemap)
        self.assertNotIn("/media/executive-demo", sitemap)
        self.assertNotIn("demo.html", sitemap)

    # ---- r1.1 finalize (2026-09-14) --------------------------------------

    MEDIA_NAV_PAGES = ("index", "platform", "decision-graph", "how-it-works",
                       "use-cases", "pilot", "trust", "resources", "contact")

    def test_r1_1_rail_line(self) -> None:
        # The r1.1 prompt's canonical <link> is deliberately NOT carried: the
        # page is robots-noindex and unsitemapped, so a canonical URL would
        # assert an indexed surface that does not exist
        # (test_media_contract_waivers_are_explicit, #1034, pins its absence).
        self.assertIn("EXECUTIVE DEMO · r1.1", self.body)
        self.assertNotIn("EXECUTIVE DEMO · r1.0", self.body)
        self.assertIn('content="noindex"', self.body)   # still a presenter surface

    def test_r1_1_cross_links_are_same_site(self) -> None:
        # The two /media cross links are root-relative and open in place; no
        # absolute mizoki3.com reference remains.
        self.assertNotIn('target="_blank"', self.body)
        self.assertNotIn("https://mizoki3.com/", self.body)
        self.assertGreaterEqual(self.body.count('href="/media/pilot"'), 2)
        self.assertIn('href="/media/decision-graph"', self.body)

    def test_legacy_slug_redirects_into_the_canonical_page(self) -> None:
        # Slug renamed 2026-09-14 (owner call): /media/demo is canonical; the
        # r1.1 slug and its filename form are permanent redirects into it.
        for path in ("/media/executive-demo", "/media/executive-demo/", "/media/executive-demo.html"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 308, path)
            self.assertTrue(response.headers["Location"].endswith("/media/demo"), path)
        followed = self.client.get("/media/executive-demo", follow_redirects=True)
        self.assertEqual(followed.status_code, 200)
        self.assertIn("SYNTHETIC TENANT", followed.get_data(as_text=True))

    def test_media_nav_carries_demo_on_every_page(self) -> None:
        entry = '<a href="/media/demo">Demo</a>'
        for name in self.MEDIA_NAV_PAGES:
            path = "/media" if name == "index" else f"/media/{name}"
            body = self.client.get(path, follow_redirects=True).get_data(as_text=True)
            self.assertEqual(body.count(entry), 1, name)
            # Between "How It Works" and "Use Cases", as specified.
            how = body.index(">How It Works</a>")
            use = body.index(">Use Cases</a>")
            self.assertTrue(how < body.index(entry) < use, name)

    def test_pilot_close_offers_the_demo_first(self) -> None:
        pilot = self.client.get("/media/pilot").get_data(as_text=True)
        self.assertIn('href="/media/demo">See the executive demo first →</a>', pilot)
        self.assertIn('href="/media/contact">Discuss a MIZ OKI Media Pilot</a>', pilot)

    def test_legacy_slug_is_not_in_the_sitemap_either(self) -> None:
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertNotIn("/media/executive-demo", sitemap)

    def test_page_is_in_the_content_gate_scope(self) -> None:
        # A gate that does not cover a surface cannot defend it.
        self.assertIn("media/demo.html", content_qa.SCOPE_FILES)

    # ---- media-namespace contract (review findings on #1027) ------------

    def test_media_contract_applies_where_the_presenter_surface_can_carry_it(self) -> None:
        # The closed-world /media/<page> route serves this page, but
        # tests/test_media_page.py enumerates only the eight product
        # sub-pages, so the shared media contract never ran here. The page is
        # a single-file presenter surface with its own design system: it
        # carries the contract's page-level invariants here and WAIVES the
        # site-chrome ones explicitly in the next test.
        self.assertEqual(1, len(re.findall(r"<h1\b", self.body)), "one h1")
        self.assertIn('lang="en"', self.body)
        self.assertIn("Skip to content", self.body)
        self.assertIn('href="#stage"', self.body)
        self.assertIn('<main class="stage" id="stage" tabindex="-1">', self.body)
        self.assertIn('name="description"', self.body)
        self.assertIn("<title>MIZ OKI Media Executive Demo</title>", self.body)
        self.assertIsNone(re.search(r"<script[^>]*\bsrc=", self.body))
        for img in re.findall(r"<img\b[^>]*>", self.body):
            self.assertIn("alt=", img, img)
            self.assertIn("width=", img, img)
        # Every link the page carries onto this site resolves.
        hrefs = set(re.findall(r'href="(/[^"#?]*)', self.body))
        hrefs |= set(re.findall(r'href="https://mizoki3\.com(/[^"#?]*)', self.body))
        self.assertTrue(hrefs, "the page links back into /media")
        for href in sorted(hrefs):
            self.assertEqual(200, self.client.get(href).status_code, href)

    def test_close_never_cites_the_fallback_seed_auc(self) -> None:
        # LII_BACKTEST_MODEL_QUALITY_2026-08-16 recommendation 1: 0.6884 was the
        # fallback scorer on ONE seed; cite the panel or cite nothing. The close
        # says the gate is unscored (no admissible forward labels) and carries no
        # AUC figure at all, so no TRUTH.md label is owed for one.
        self.assertNotIn("0.6884", self.body)
        self.assertNotIn("measured AUC", self.body)
        self.assertIn("cannot even be scored", self.body)

    def test_run_dcp_clears_the_settled_action_on_start(self) -> None:
        # #1034 review thread: a floor change mid-run must not re-settle the
        # previous action through lastDCP while the new checklist is ticking.
        self.assertIn("var run = ++dcpRun; clearTimeout(dcpTimer); lastDCP = null;", self.body)

    def test_media_contract_waivers_are_explicit(self) -> None:
        # Waived invariants, each with its reason on the record:
        # - canonical / og:url / twitter:card: the page is robots-noindex and
        #   absent from the sitemap by design; a canonical URL would assert an
        #   indexed surface that does not exist.
        self.assertIn('<meta name="robots" content="noindex">', self.body)
        self.assertNotIn('rel="canonical"', self.body)
        self.assertNotIn('property="og:url"', self.body)
        # - the shared /media/assets/media.css: the presenter surface ships its
        #   own self-contained design system (inline styles only).
        self.assertNotIn("/media/assets/media.css", self.body)
        self.assertNotIn("/assets/css/", self.body)
        # - the external-origin clause of the classic-site isolation rule: the
        #   page loads its typography from fonts.googleapis.com; every other
        #   external reference stays on mizoki3.com. A waiver, not a pass.
        for attr, url in re.findall(r'(src|href)="(https?://[^"]+)"', self.body):
            self.assertTrue(
                url.startswith(("https://mizoki3.com", "https://fonts.googleapis.com")),
                f"{attr}: {url}")

    def test_demo_logic_guards_from_the_1027_review_are_present(self) -> None:
        # Review findings on #1027, pinned as source literals (the page runs
        # only in the browser; these are the guards a regression would drop).
        # 1. the lifecycle event honours the consent selector — analytics-only
        #    consent refuses it, exactly as the session replay does.
        handler = self.body.split('$("sendLifecycle").addEventListener', 1)[1].split("});", 1)[0]
        self.assertIn('$("consent").value === "analytics"', handler)
        self.assertIn("REJECTED · CONSENT_SCOPE", handler)
        # 2. a newer DCP run invalidates an older one (run token + timer).
        self.assertIn("var run = ++dcpRun; clearTimeout(dcpTimer);", self.body)
        self.assertIn("if (run !== dcpRun) return;", self.body)
        # 3. action amounts follow the tenant scale like every other figure.
        render_all = self.body.split("function renderAll()", 1)[1].split("\n", 1)[0]
        self.assertIn("renderActionList();", render_all)
        self.assertIn('a.sub.replace("{ev}", money(a.ev_usd))', self.body)
        self.assertNotIn("expected value $", self.body)
        # 4. a floor change re-settles the last verdict instead of leaving a
        #    verdict computed against the old floor on screen.
        self.assertIn(
            "if (lastDCP) settleDCP(lastDCP.a, lastDCP.passes, lastDCP.hardFail); else renderDEL(null, null);",
            self.body)


if __name__ == "__main__":
    unittest.main()
