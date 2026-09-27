"""MIZ OKI Media (/media) — route, asset, copy, and isolation contract.

The /media surface is an additive, fully isolated product page (2026-08-03):
one self-contained HTML document in media/ plus local video/poster/storyboard
assets, wired by exactly two routes in app.py. These tests pin that contract:

1. ROUTES — /media and /media/ both serve the page directly (200, no
   redirect hop), and the asset route streams the film as real video/mp4
   with Range support so it can never fall through to an HTML handler.
2. COPY — the approved positioning is present verbatim: product name,
   category descriptor, hero, Decision Graph chain, the knowledge-graph
   distinction, the SRPVDAL order, and the 90-day pilot framing.
3. CLAIMS DISCIPLINE — the page passes the house truth-discipline checker
   (scripts/content_qa.py check_file) even though it is not in that gate's
   CI scope: no affirmative "guaranteed"/"mind-reading", and every visible
   %/× number shares its section with an illustrative-style label.
4. ISOLATION — no existing surface links into /media, the page pulls no
   shared stylesheet and no external origin, and the classic routes
   (/  /marketing  /signal  /demo) still serve unchanged.
5. PART 2 STRUCTURE (owner spec, 2026-08-04) — required section order;
   the customer-problem question wall resolving into "one governed decision
   pathway"; the 5-column x 11-row capability comparison table; interactive
   Decision Graph nodes and four memory layers with their stored fields;
   the seven expandable SENSE→LEARN stages each carrying Purpose / Inputs /
   Outputs / Example / Business value; the reworked scenario (landing page +
   inventory diagnosis, approval routed to Operations, every number labeled
   an illustrative example); the film caption plus a served transcript that
   quotes the preview render's on-screen text verbatim; and the executive
   value proposition converging into one governed recommendation.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import create_app  # noqa: E402
from mizoki_runtime import create_runtime  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "content_qa", BASE_DIR / "scripts" / "content_qa.py"
)
content_qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(content_qa)

MEDIA_HTML = BASE_DIR / "media" / "index.html"
MEDIA_MP4 = BASE_DIR / "media" / "video" / "mizoki-signal-explainer.mp4"
MEDIA_POSTER = BASE_DIR / "media" / "assets" / "mizoki-signal-preview.png"
MEDIA_STORYBOARD = BASE_DIR / "media" / "assets" / "mizoki-signal-storyboard.png"
MEDIA_TRANSCRIPT = BASE_DIR / "media" / "assets" / "mizoki-media-transcript.html"


class MediaPageTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=BASE_DIR, data_dir=Path(cls.temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        cls.client = app.test_client()
        cls.page = cls.client.get("/media").get_data(as_text=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    # ------------------------------------------------------------ routes --

    def test_media_serves_directly_with_and_without_trailing_slash(self) -> None:
        for path in ("/media", "/media/"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)
            self.assertEqual("text/html", response.mimetype, path)
            self.assertIn("MIZ OKI Media", response.get_data(as_text=True), path)
            response.close()

    def test_video_asset_served_as_mp4(self) -> None:
        response = self.client.get("/media/video/mizoki-signal-explainer.mp4")
        self.assertEqual(200, response.status_code)
        self.assertEqual("video/mp4", response.mimetype)
        body = response.get_data()
        self.assertGreater(len(body), 10_000)
        # A real MP4 container, not an HTML page that fell through a fallback.
        self.assertIn(b"ftyp", body[:32])
        self.assertNotIn(b"<!DOCTYPE", body[:200])
        response.close()

    def test_video_asset_supports_byte_range_requests(self) -> None:
        response = self.client.get(
            "/media/video/mizoki-signal-explainer.mp4",
            headers={"Range": "bytes=0-99"},
        )
        self.assertEqual(206, response.status_code)
        self.assertEqual(100, len(response.get_data()))
        self.assertTrue(response.headers.get("Content-Range", "").startswith("bytes 0-99/"))
        response.close()

    def test_image_assets_served_as_png(self) -> None:
        for path in (
            "/media/assets/mizoki-signal-preview.png",
            "/media/assets/mizoki-signal-storyboard.png",
        ):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)
            self.assertEqual("image/png", response.mimetype, path)
            self.assertEqual(b"\x89PNG", response.get_data()[:4], path)
            response.close()

    def test_asset_route_refuses_traversal_and_unknown_files(self) -> None:
        for path in (
            "/media/%2e%2e/app.py",
            "/media/video/%2e%2e/%2e%2e/app.py",
            "/media/no-such-file.png",
            "/media/video/",
        ):
            response = self.client.get(path)
            self.assertEqual(404, response.status_code, path)
            response.close()

    def test_media_assets_exist_on_disk(self) -> None:
        for asset in (MEDIA_HTML, MEDIA_MP4, MEDIA_POSTER, MEDIA_STORYBOARD,
                      MEDIA_TRANSCRIPT):
            self.assertTrue(asset.is_file(), asset.name)
            self.assertGreater(asset.stat().st_size, 0, asset.name)

    # -------------------------------------------------------------- copy --

    def test_approved_positioning_is_verbatim(self) -> None:
        for phrase in (
            "MIZ OKI Media",
            "Causal Growth Control · powered by the MIZ OKI Decision Graph",
            "Know why performance moved. Put the next dollar where it creates profit.",
            "MIZ OKI Media connects media, commerce, customer experience, inventory, "
            "product economics, and policy into one governed decision pathway.",
            "Modern organizations have more commercial data than ever before, yet "
            "the most important decisions are still made through disconnected "
            "dashboards, spreadsheets, intuition, and meetings. MIZ OKI Media "
            "transforms fragmented commercial signals into governed decisions that "
            "people can understand, approve, execute, and continuously improve.",
            "A conventional knowledge graph explains what is connected.",
            "A 90-Day Causal Growth Control Pilot",
            "Begin observe-only. Advance to human-approved actions only after "
            "evidence quality, economics, and policy boundaries are validated.",
            "focused commercial application powered by the broader MIZ OKI "
            "Operating Knowledge Intelligence platform",
            "Explore the 90-Day Pilot",
            "Watch the Explainer",
        ):
            self.assertIn(phrase, self.page, phrase)

    def test_decision_graph_chain_in_order(self) -> None:
        # The hero chain strip carries the seven stages as consecutive items.
        chain = re.search(
            r'<li class="c1">Signal</li><li class="c2">Entity</li>'
            r'<li class="c3">Cause</li><li class="c4">Objective</li>'
            r'<li class="c5">Policy</li><li class="c6">Action</li>'
            r'<li class="c7">Outcome</li>',
            self.page,
        )
        self.assertIsNotNone(chain, "hero Decision Graph chain missing or reordered")

    def test_srpvdal_order_is_exact_and_complete(self) -> None:
        self.assertIn(
            "SENSE → REASON → PLAN → VALIDATE → DECIDE → ACT → LEARN", self.page
        )
        # Each stage carries its own described step, in order.
        order = ["1 · SENSE", "2 · REASON", "3 · PLAN", "4 · VALIDATE",
                 "5 · DECIDE", "6 · ACT", "7 · LEARN"]
        idx = [self.page.find(step) for step in order]
        self.assertNotIn(-1, idx, "a SRPVDAL stage row is missing")
        self.assertEqual(idx, sorted(idx), "SRPVDAL stage rows out of order")

    def test_memory_layers_and_maturity_labels_present(self) -> None:
        for phrase in ("Evidence memory", "Operating context", "Decision memory",
                       "Outcome memory", "Pilot-ready", "Illustrative", "Roadmap",
                       "Illustrative scenario"):
            self.assertIn(phrase, self.page, phrase)

    def test_pilot_phases_present(self) -> None:
        for phrase in ("Days 1–30", "Days 31–60", "Days 61–90",
                       "Connect and observe", "Diagnose and recommend",
                       "Approve, act, and learn"):
            self.assertIn(phrase, self.page, phrase)

    def test_final_cta_uses_mailto_lead_path(self) -> None:
        # The in-repo contact form posts to a placeholder endpoint, so the
        # approved destination is the pilot mailto: link — which, since the
        # A/B/C test-design fix (2026-08-22), rides the tracked /go/pilot
        # redirect so the click is measurable. Both directions pinned: the
        # page links the tracker, AND the tracker still resolves to the
        # approved mailto destination (relocated, not deleted).
        self.assertIn('href="/go/pilot?cta=media-final"', self.page)
        self.assertIn("Discuss a MIZ OKI Media Pilot", self.page)
        redirect = self.client.get("/go/pilot?cta=media-final")
        self.assertEqual(302, redirect.status_code)
        self.assertTrue(redirect.headers["Location"].startswith(
            "mailto:contact@mizoki3.com?subject=MIZ%20OKI%20Media%20Pilot"))

    # ------------------------------------------------ Part 2 structure ---

    def test_required_section_order(self) -> None:
        # Owner-specified homepage order. Sections not in the required list
        # (storyboard, value, maturity) may interleave, but the required
        # sequence itself must hold; the final CTA closes the page.
        markers = [
            'id="mzm-h1"',            # 1 hero
            'id="problem"',           # 2 customer problem
            'id="stop-early"',        # 3 why existing tools stop too early
            'id="decision-graph"',    # 4 the decision graph
            'id="how-it-works"',      # 5 how MIZ OKI Media works
            'id="scenario"',          # 6 live decision scenario
            'id="film"',              # 7 product explainer video
            'id="decision-jobs"',     # 8 decision jobs
            'id="architecture"',      # 9 platform architecture
            'id="pilot"',             # 10 pilot program
            'id="governance"',        # 11 trust & governance
            'id="cta-h"',             # 12 final call to action
        ]
        positions = [self.page.find(m) for m in markers]
        self.assertNotIn(-1, positions, "a required section is missing")
        self.assertEqual(positions, sorted(positions), "required sections out of order")

    def test_customer_problem_section(self) -> None:
        self.assertIn("The Most Expensive Decisions Are Still Guesswork", self.page)
        for question in (
            "Why did CPA suddenly increase?",
            "Why did ROAS fall?",
            "Is creative responsible?",
            "Is the website responsible?",
            "Did tracking break?",
            "Are we inventory constrained?",
            "Is margin preventing profitable scale?",
            "Is this seasonal noise?",
            "Should we increase budget?",
            "Should we pause campaigns?",
            "Who should approve the decision?",
        ):
            self.assertIn(question, self.page, question)
        # The eleven questions resolve into the unified answer.
        self.assertIn("<strong>one governed decision pathway.</strong>", self.page)

    def test_capability_comparison_table(self) -> None:
        table = re.search(r"<table class=\"mzm-compare\">.*?</table>", self.page, re.S)
        self.assertIsNotNone(table, "comparison table missing")
        text = table.group(0)
        for column in ("Dashboards", "Attribution", "CDPs", "Bid Automation",
                       "MIZ OKI Media"):
            self.assertIn(f"<th scope=\"col\"", text)
            self.assertIn(column, text, column)
        for row in (
            "Detect change", "Store customer data", "Estimate attribution",
            "Identify likely causes", "Compare counterfactual actions",
            "Apply financial rules", "Apply policy", "Route approval",
            "Execute governed action", "Measure realized outcome",
            "Learn from every decision",
        ):
            self.assertIn(f"<th scope=\"row\">{row}</th>", text, row)
        self.assertEqual(11, text.count('<th scope="row">'), "expected 11 rows")
        # The MIZ OKI Media column covers every row.
        self.assertEqual(11, text.count('<td class="miz">'))
        # Capability-boundary footnotes stay factual, not adversarial.
        self.assertIn("Within a single ad platform's auction", self.page)
        self.assertIn("complements a CDP", self.page)

    def test_decision_graph_interactive_nodes(self) -> None:
        self.assertIn("Traditional knowledge graphs organize relationships.", self.page)
        for connected in ("evidence", "business context", "objectives",
                          "governing policy", "responsible authority",
                          "action taken", "realized outcome"):
            self.assertIn(f"<li>{connected}</li>", self.page, connected)
        # Seven expandable nodes, one per chain stage, each with a summary.
        nodes = re.findall(r'<details class="mzm-node s(\d)">\s*<summary>([^<]+)</summary>', self.page)
        self.assertEqual(
            [("1", "Signal"), ("2", "Entity"), ("3", "Cause"), ("4", "Objective"),
             ("5", "Policy"), ("6", "Action"), ("7", "Outcome")],
            nodes,
        )

    def test_memory_layers_store_their_fields(self) -> None:
        for field in (
            # evidence memory
            "source", "timestamp", "provenance", "confidence", "quality", "identity",
            # operating context
            "entities", "relationships", "constraints", "policies", "organizational state",
            # decision memory
            "hypotheses", "counterfactuals", "recommendations", "approvals", "vetoes",
            # outcome memory
            "realized impact", "prediction accuracy", "lessons", "future weighting",
            "model improvements",
        ):
            self.assertIn(f"<li>{field}</li>", self.page, field)

    def test_flow_stages_carry_full_contract(self) -> None:
        # Seven expandable stages; each body carries the five required rows.
        stages = re.findall(r'<details class="mzm-flow f\d"[^>]*>', self.page)
        self.assertEqual(7, len(stages))
        for row_label in ("Purpose", "Inputs", "Outputs", "Example", "Business value"):
            self.assertEqual(
                7, self.page.count(f'<span class="t">{row_label}</span>'),
                f"every stage needs a {row_label} row",
            )
        # Spot-check the owner-specified example sets.
        for chip in ("CPA increase", "Tracking anomaly", "Creative fatigue",
                     "Audience saturation", "Shift channels", "Repair tracking",
                     "Operational readiness", "Customer impact",
                     "Delegated approval", "Escalated", "Campaign update",
                     "No action"):
            self.assertIn(f"<span>{chip}</span>", self.page, chip)
        # LEARN closes the loop with the four-step comparison.
        learn = re.search(r'<ol class="mzm-learn-flow">(.*?)</ol>', self.page, re.S)
        self.assertIsNotNone(learn)
        self.assertEqual(
            ["Predicted outcome", "Actual outcome", "Confidence adjustment",
             "Future weighting"],
            re.findall(r"<li>([^<]+)</li>", learn.group(1)),
        )

    def test_scenario_tells_the_specified_story(self) -> None:
        scenario = re.search(r'<section id="scenario".*?</section>', self.page, re.S)
        self.assertIsNotNone(scenario)
        text = scenario.group(0)
        # The one visible number is labeled an illustrative example in-place.
        self.assertIn("+34%", text)
        self.assertIn("Illustrative Example", text)
        # False hypotheses are visibly eliminated; the diagnosis is confirmed.
        self.assertEqual(4, text.count('<span class="mzm-tag no">ruled out</span>'))
        self.assertEqual(2, text.count('<span class="mzm-tag yes">confirmed</span>'))
        for phrase in (
            "Creative CTR", "Landing page latency", "Checkout abandonment",
            "Landing page performance degradation, compounded by inventory constraints",
            "Repair the experience.", "Temporarily rebalance budget",
            "Protect margin", "Routed to Operations",
        ):
            self.assertIn(phrase, text, phrase)

    def test_film_caption_and_transcript(self) -> None:
        self.assertIn(
            "From moved signal to recorded outcome — every stage traced, every constraint enforced, every decision accountable.",
            self.page,
        )
        self.assertIn('href="/media/assets/mizoki-media-transcript.html"', self.page)
        self.assertIn('href="/animation"', self.page)
        # The transcript serves over the asset route and quotes the preview
        # render's on-screen text verbatim.
        response = self.client.get("/media/assets/mizoki-media-transcript.html")
        self.assertEqual(200, response.status_code)
        self.assertEqual("text/html", response.mimetype)
        transcript = response.get_data(as_text=True)
        response.close()
        for line in (
            "Performance moved.",
            "Dashboards report it. Nobody governs the response.",
            "One graph connects the stack.",
            "Constraints before actions.",
            "The right human authorizes.",
            "Only the approved, bounded action dispatches.",
            "Predicted vs. realized.",
            "Every outcome sharpens the next decision.",
            "Know why performance moved.",
            "Placeholder render — final narrated film pending",
        ):
            self.assertIn(line, transcript, line)

    def test_executive_value_proposition(self) -> None:
        for role, line in (
            ("Marketing Leaders", "Know where incremental growth exists."),
            ("Finance", "Know where profitable growth exists."),
            ("Operations", "Know whether execution is possible."),
        ):
            self.assertIn(role, self.page, role)
            self.assertIn(line, self.page, line)
        self.assertIn("All three converge into", self.page)
        self.assertIn("<strong>one governed recommendation</strong>", self.page)

    # ------------------------------------------------------ video markup --

    def test_video_element_contract(self) -> None:
        video = re.search(r"<video\b[^>]*>", self.page)
        self.assertIsNotNone(video, "no <video> element")
        tag = video.group(0)
        self.assertIn("controls", tag)
        self.assertIn("playsinline", tag)
        self.assertIn('preload="metadata"', tag)
        self.assertIn('poster="/media/assets/mizoki-signal-preview.png"', tag)
        self.assertNotIn("autoplay", tag)
        self.assertIn(
            '<source src="/media/video/mizoki-signal-explainer.mp4?v=', self.page
        )
        self.assertIn('type="video/mp4"', self.page)

    # ------------------------------------------------- claims discipline --

    def test_page_passes_house_truth_discipline_checks(self) -> None:
        # Reuse the truth-discipline gate directly (the page is deliberately
        # outside that gate's CI scope, but must still satisfy its rules:
        # no affirmative guaranteed/mind-reading claims, and every visible
        # %/× number shares its section with an illustrative-style label).
        findings = content_qa.check_file("media/index.html", MEDIA_HTML.read_text(encoding="utf-8"))
        self.assertEqual([], findings)

    def test_no_absolute_performance_promises(self) -> None:
        text = re.sub(r"<[^>]+>", " ", self.page).lower()
        for banned in ("100% policy", "guaranteed roi", "guaranteed savings",
                       "fully autonomous execution", "soc 2 certified",
                       "hipaa certified", "patented"):
            self.assertNotIn(banned, text, banned)

    # ------------------------------------------------- metadata & a11y ---

    def test_page_metadata(self) -> None:
        self.assertIn("<title>MIZ OKI Media | Causal Growth Control</title>", self.page)
        # A/B/C test-design fix (2026-08-22): this page is variant C of the
        # /signal test — canonical + og:url point at the ONE indexed landing
        # and this URL serves noindex,follow.
        self.assertIn('<link rel="canonical" href="https://mizoki3.com/signal">', self.page)
        self.assertIn('<meta name="robots" content="noindex,follow">', self.page)
        self.assertIn('property="og:title" content="MIZ OKI Media — Causal Growth Control"', self.page)
        self.assertIn('property="og:image" content="https://mizoki3.com/media/assets/mizoki-signal-preview.png"', self.page)
        self.assertIn('name="twitter:card" content="summary_large_image"', self.page)
        # Favicon set matches the existing site's canonical assets, unchanged.
        self.assertIn('href="/assets/img/favicon.svg"', self.page)
        self.assertIn('href="/assets/img/favicon.ico"', self.page)
        self.assertIn('href="/assets/img/apple-touch-icon.png"', self.page)

    def test_accessibility_basics(self) -> None:
        self.assertEqual(1, len(re.findall(r"<h1\b", self.page)), "exactly one h1")
        self.assertIn('lang="en"', self.page)
        self.assertIn("Skip to content", self.page)
        self.assertIn("prefers-reduced-motion", self.page)
        storyboard_img = re.search(r'<img[^>]*mizoki-signal-storyboard[^>]*>', self.page)
        self.assertIsNotNone(storyboard_img)
        self.assertIn('alt="Storyboard of the MIZ OKI Media explainer film', storyboard_img.group(0))
        self.assertIn('width="1600"', storyboard_img.group(0))
        self.assertIn('loading="lazy"', storyboard_img.group(0))

    # ---------------------------------------------------------- isolation --

    def test_page_is_self_contained(self) -> None:
        # No shared stylesheet, no external stylesheet/font/script origins.
        self.assertNotIn('rel="stylesheet"', self.page)
        self.assertNotIn("/assets/css/", self.page)
        self.assertNotIn("fonts.googleapis.com", self.page)
        self.assertNotIn("fonts.gstatic.com", self.page)
        self.assertNotIn('<script src=', self.page)
        # Every subresource the page loads is site-local (the only absolute
        # URLs are its own canonical/OG metadata and the footer home link).
        # Owner directive 2026-09-16: the one sanctioned off-origin link is the
        # public Decision Studio's own /media page (a plain <a>, never a
        # subresource). Bounded to that exact URL; any other origin still fails.
        for attr, url in re.findall(r'(src|poster|href)="(https?://[^"]+)"', self.page):
            if attr == "href" and url == "https://decisionstudio.mizoki3.com/media":
                continue
            self.assertTrue(
                url.startswith("https://mizoki3.com"),
                f"external origin in {attr}: {url}",
            )

    def test_media_linkage_matches_the_approved_product_nav(self) -> None:
        # Baseline moved with the owner-approved unified product experience
        # (#836, 2026-08-25; serving via dispatch run #107): the homepage now
        # deliberately links /media. The surviving isolation is A/B/C arm
        # hygiene — the experiment variants (/marketing is arm B, /signal is
        # arm A) and /demo never link into /media.
        home = self.client.get("/")
        home_body = home.get_data(as_text=True)
        home.close()
        self.assertIn('href="/media"', home_body)
        for path in ("/marketing", "/signal", "/demo"):
            response = self.client.get(path)
            body = response.get_data(as_text=True)
            response.close()
            self.assertNotIn('href="/media"', body, path)
            self.assertNotIn('href="/media/', body, path)

    def test_existing_surfaces_still_serve(self) -> None:
        for path in ("/", "/marketing", "/signal", "/demo", "/pricing"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)
            response.close()
        # The unrelated legacy redirect beside the new routes is untouched.
        response = self.client.get("/media-buying")
        self.assertEqual(301, response.status_code)
        self.assertTrue(response.headers["Location"].endswith("/marketing"))
        response.close()


SUBPAGES = {
    "platform": "The Commercial Decision Operating System",
    "decision-graph": "This remembers why.",
    "how-it-works": "Seven stages. One record. No gaps.",
    "use-cases": "One decision pathway. Many decision jobs.",
    "pilot": "The 90-Day Causal Growth Control Pilot",
    "trust": "Trust comes from governance, not automation.",
    "resources": "Take the argument with you.",
    "contact": "Discuss a MIZ OKI Media Pilot",
}

DOWNLOADABLES = {
    "mizoki-media-product-overview.html": "text/html",
    "mizoki-media-decision-graph-overview.html": "text/html",
    "mizoki-media-pilot-guide.html": "text/html",
    "mizoki-media-executive-summary.html": "text/html",
    "mizoki-media-architecture.svg": "image/svg+xml",
    "mizoki-media-transcript.html": "text/html",
}


class MediaSiteTestCase(unittest.TestCase):
    """Part 3 contract: /media is a complete standalone product site.

    Eight sub-pages served on clean routes; a shared route-local stylesheet;
    per-page SEO metadata; downloadable resources that exist and serve with
    the right mimetypes; the interactive walkthrough is deterministic; every
    internal link resolves; the whole surface passes the house
    truth-discipline checks; and the classic site remains untouched.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=BASE_DIR, data_dir=Path(cls.temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        cls.client = app.test_client()
        cls.pages = {}
        for slug in SUBPAGES:
            response = cls.client.get(f"/media/{slug}")
            cls.pages[slug] = response.get_data(as_text=True)
            response.close()
        response = cls.client.get("/media")
        cls.home = response.get_data(as_text=True)
        response.close()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    # ------------------------------------------------------------ routes --

    def test_subpages_serve_directly_with_and_without_trailing_slash(self) -> None:
        for slug in SUBPAGES:
            for path in (f"/media/{slug}", f"/media/{slug}/"):
                response = self.client.get(path)
                self.assertEqual(200, response.status_code, path)
                self.assertEqual("text/html", response.mimetype, path)
                response.close()

    def test_unknown_media_paths_404(self) -> None:
        for path in ("/media/nope", "/media/platform2", "/media/platform.html/x"):
            response = self.client.get(path)
            self.assertEqual(404, response.status_code, path)
            response.close()

    def test_shared_stylesheet_served_and_linked(self) -> None:
        response = self.client.get("/media/assets/media.css")
        self.assertEqual(200, response.status_code)
        self.assertEqual("text/css", response.mimetype)
        css = response.get_data(as_text=True)
        response.close()
        self.assertIn("prefers-reduced-motion", css)
        for slug, page in self.pages.items():
            self.assertIn('href="/media/assets/media.css', page, slug)

    # ------------------------------------------------------ SEO & a11y ---

    def test_each_page_has_unique_seo_metadata(self) -> None:
        titles = set()
        for slug, page in self.pages.items():
            title = re.search(r"<title>(.*?)</title>", page)
            self.assertIsNotNone(title, slug)
            titles.add(title.group(1))
            self.assertIn(
                f'<link rel="canonical" href="https://mizoki3.com/media/{slug}">',
                page, slug)
            self.assertIn(
                f'property="og:url" content="https://mizoki3.com/media/{slug}"',
                page, slug)
            self.assertIn('name="twitter:card" content="summary_large_image"', page, slug)
            self.assertIn('name="description"', page, slug)
        self.assertEqual(len(SUBPAGES), len(titles), "titles must be unique")

    def test_each_page_accessibility_basics(self) -> None:
        for slug, page in self.pages.items():
            self.assertEqual(1, len(re.findall(r"<h1\b", page)), f"{slug}: one h1")
            self.assertIn('lang="en"', page, slug)
            self.assertIn("Skip to content", page, slug)
            self.assertIn(SUBPAGES[slug], page, slug)
            for img in re.findall(r"<img\b[^>]*>", page):
                self.assertIn("alt=", img, f"{slug}: image missing alt")
                self.assertIn("width=", img, f"{slug}: image missing dimensions")

    def test_each_page_is_isolated_from_classic_site(self) -> None:
        for slug, page in self.pages.items():
            self.assertNotIn("/assets/css/", page, slug)
            self.assertNotIn("fonts.googleapis.com", page, slug)
            self.assertNotIn("<script src=", page, slug)
            for attr, url in re.findall(r'(src|href)="(https?://[^"]+)"', page):
                # Owner directive 2026-09-16: the shared nav's one off-origin link
                # is the public Decision Studio's /media page (exact URL, <a> only).
                if attr == "href" and url == "https://decisionstudio.mizoki3.com/media":
                    continue
                self.assertTrue(url.startswith("https://mizoki3.com"),
                                f"{slug}: external origin in {attr}: {url}")

    def test_internal_links_resolve(self) -> None:
        # Crawl every /media href on every page (home included): no broken
        # internal links anywhere on the standalone site.
        seen = set()
        for slug, page in list(self.pages.items()) + [("home", self.home)]:
            for href in re.findall(r'href="(/media[^"#?]*)', page):
                if href in seen:
                    continue
                seen.add(href)
                response = self.client.get(href)
                self.assertIn(response.status_code, (200,),
                              f"{slug}: broken link {href}")
                response.close()

    # ------------------------------------------------------ page content --

    def test_platform_capabilities(self) -> None:
        page = self.pages["platform"]
        for capability in ("Commercial Intelligence", "Causal Reasoning",
                           "Counterfactual Planning", "Policy Validation",
                           "Human Approval", "Governed Execution",
                           "Outcome Learning"):
            self.assertIn(capability, page, capability)
        self.assertIn("mizoki-media-architecture.svg", page)

    def test_decision_graph_comparisons_and_pillars(self) -> None:
        page = self.pages["decision-graph"]
        self.assertIn("operating model, not a storage model", page)
        for structure in ("Data warehouse", "Semantic layer", "Knowledge graph",
                          "Vector database", "Agent memory", "Decision Graph"):
            self.assertIn(structure, page, structure)
        for pillar in ("Temporal memory", "Provenance", "Causal relationships",
                       "Approval history", "Replay", "Continuous learning"):
            self.assertIn(pillar, page, pillar)
        # The worked record walks all seven layers.
        records = re.findall(r'<details class="mzm-rec r\d"', page)
        self.assertEqual(7, len(records))

    def test_how_it_works_stage_contract(self) -> None:
        page = self.pages["how-it-works"]
        for label in ("Inputs", "Outputs", "AI responsibilities",
                      "Human responsibilities", "Governance checkpoints",
                      "Example scenario", "Typical metrics"):
            self.assertEqual(
                7, page.count(f'<span class="t">{label}</span>'),
                f"every stage needs a {label} row")
        for stage in ("SENSE", "REASON", "PLAN", "VALIDATE", "DECIDE", "ACT", "LEARN"):
            self.assertIn(f"<h3>{stage}</h3>", page, stage)

    def test_interactive_demo_is_deterministic(self) -> None:
        page = self.pages["how-it-works"]
        for element_id in ("cpaRange", "cpaOut", "hypoBars", "demoVerdict"):
            self.assertIn(f'id="{element_id}"', page, element_id)
        self.assertIn("Illustrative", page)
        self.assertIn("<noscript>", page)
        # Determinism across the whole surface: no randomness, no clocks.
        for slug, source in list(self.pages.items()) + [("home", self.home)]:
            self.assertNotIn("Math.random", source, slug)
            self.assertNotIn("Date.now", source, slug)
            self.assertNotIn("new Date(", source, slug)

    def test_use_cases_complete(self) -> None:
        page = self.pages["use-cases"]
        for section in ('id="marketing"', 'id="commerce"',
                        'id="operations"', 'id="executive"'):
            self.assertIn(section, page, section)
        cases = ("Budget allocation", "Creative diagnosis", "Channel optimization",
                 "Campaign monitoring", "Margin protection", "Inventory-aware spend",
                 "Promotion decisions", "Conversion diagnosis", "Incident routing",
                 "Workflow prioritization", "Cross-functional coordination",
                 "Forecast confidence", "Decision transparency",
                 "Resource allocation", "Strategic planning")
        for case in cases:
            self.assertIn(f"<h3>{case}</h3>", page, case)
        for field in ("Business problem", "Current approach",
                      "MIZ OKI Media approach", "Expected operational benefits",
                      "Required approvals"):
            self.assertEqual(
                len(cases), page.count(f'<span class="t">{field}</span>'),
                f"every use case needs a {field} row")

    def test_pilot_page_structure(self) -> None:
        page = self.pages["pilot"]
        for phrase in ("Days 1–30 · Connect and observe",
                       "Days 31–60 · Diagnose and recommend",
                       "Days 61–90 · Approve, act, and learn",
                       "Success metrics", "Exit criteria",
                       "Governance checkpoint"):
            self.assertIn(phrase, page, phrase)
        for exit_state in ("Expand", "Extend", "Stop"):
            self.assertIn(f'<div class="t">{exit_state}</div>', page, exit_state)

    def test_trust_page_commitments_and_evaluators(self) -> None:
        page = self.pages["trust"]
        for commitment in ("Human authority", "Policy enforcement", "Explainability",
                           "Audit trail", "Rollback capability", "Evidence provenance",
                           "Decision replay", "Confidence scoring", "Security model",
                           "Privacy considerations"):
            self.assertIn(commitment, page, commitment)
        for evaluator in ("The CFO asks", "Legal asks", "Security asks",
                          "Marketing asks", "Operations asks", "Procurement asks"):
            self.assertIn(evaluator, page, evaluator)
        # Maturity labels separate demonstrated capability from roadmap.
        for label in ("Live", "Pilot-ready", "Roadmap"):
            self.assertIn(label, page, label)

    def test_resources_downloadables_exist_and_serve(self) -> None:
        page = self.pages["resources"]
        for filename, mimetype in DOWNLOADABLES.items():
            self.assertTrue((BASE_DIR / "media" / "assets" / filename).is_file(),
                            filename)
            response = self.client.get(f"/media/assets/{filename}")
            self.assertEqual(200, response.status_code, filename)
            self.assertEqual(mimetype, response.mimetype, filename)
            response.close()
            if filename != "mizoki-media-transcript.html":
                self.assertIn(filename, page, f"resources page must link {filename}")
        self.assertIn("mizoki-media-transcript.html", page)
        self.assertIn('href="/media#film"', page)

    def test_contact_page_uses_mailto_not_a_new_backend(self) -> None:
        page = self.pages["contact"]
        self.assertIn(
            'href="mailto:contact@mizoki3.com?subject=MIZ%20OKI%20Media%20Pilot"',
            page)
        self.assertNotIn("<form", page)

    # -------------------------------------------------- claims discipline --

    def test_every_media_page_passes_truth_discipline(self) -> None:
        for slug, page in list(self.pages.items()) + [("index", self.home)]:
            findings = content_qa.check_file(f"media/{slug}.html", page)
            self.assertEqual([], findings, slug)

    def test_no_compliance_or_guarantee_claims_sitewide(self) -> None:
        for slug, page in list(self.pages.items()) + [("index", self.home)]:
            text = re.sub(r"<[^>]+>", " ", page).lower()
            for banned in ("soc 2 certified", "hipaa certified", "iso 27001 certified",
                           "guaranteed roi", "guaranteed savings", "patented"):
                self.assertNotIn(banned, text, f"{slug}: {banned}")

    # ---------------------------------------------------------- homepage --

    def test_homepage_nav_links_the_standalone_site(self) -> None:
        for slug in SUBPAGES:
            self.assertIn(f'href="/media/{slug}"', self.home, slug)
        for section in ('id="architecture"', 'id="governance"'):
            self.assertIn(section, self.home, section)

    def test_classic_surfaces_serve_and_variants_stay_media_free(self) -> None:
        # Same baseline move as above (#836 / run #107): "/" now carries the
        # product nav into /media by design, so it asserts positively; the
        # A/B/C variant and demo surfaces keep the negative pin.
        for path in ("/", "/marketing", "/signal", "/demo", "/pricing"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)
            body = response.get_data(as_text=True)
            response.close()
            if path == "/":
                self.assertIn('href="/media"', body, path)
            else:
                self.assertNotIn('href="/media"', body, path)
                self.assertNotIn('href="/media/', body, path)

    def test_animation_routes_and_navigation(self) -> None:
        for path in ("/animation", "/animation.html", "/ecosystem-animation", "/media/ecosystem"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)
            self.assertIn("text/html", response.mimetype)
            content = response.get_data(as_text=True)
            self.assertIn("EcosystemAnimation", content, path)
            response.close()

        # Nav and caption link in /media
        self.assertIn('<a href="/animation">Animation</a>', self.home)
        self.assertIn('Launch interactive animation player', self.home)

        # Nav and footer link in root /
        root_resp = self.client.get("/")
        root_body = root_resp.get_data(as_text=True)
        root_resp.close()
        self.assertIn('<a href="/animation" class="hide-m">ANIMATION</a>', root_body)
        self.assertIn('<a href="/animation">Animation</a>', root_body)

        # Nav and footer link in /marketing
        mkt_resp = self.client.get("/marketing")
        mkt_body = mkt_resp.get_data(as_text=True)
        mkt_resp.close()
        self.assertIn('<a href="/animation">Animation</a>', mkt_body)

        # Nav and footer link in /signal
        sig_resp = self.client.get("/signal")
        sig_body = sig_resp.get_data(as_text=True)
        sig_resp.close()
        self.assertIn('<a href="/animation">Animation</a>', sig_body)

        # Intent source Home.tsx carries the link
        intent_source = (BASE_DIR / "intent-site" / "src" / "Home.tsx").read_text(encoding="utf-8")
        self.assertIn('href="/animation"', intent_source)

        # Voice-Over audio endpoints and player controller
        for audio_path in ("/animation/audio", "/animation/ecosystem-vo-v1.mp3", "/media/assets/ecosystem-vo-v1.mp3"):
            audio_resp = self.client.get(audio_path)
            self.assertEqual(200, audio_resp.status_code, audio_path)
            self.assertEqual("audio/mpeg", audio_resp.mimetype)
            self.assertGreater(len(audio_resp.data), 100000)
            self.assertEqual("bytes", audio_resp.headers.get("Accept-Ranges"))
            audio_resp.close()

        wav_resp = self.client.get("/animation/ecosystem-vo-v1.wav")
        self.assertEqual(200, wav_resp.status_code)
        self.assertEqual("audio/wav", wav_resp.mimetype)
        self.assertGreater(len(wav_resp.data), 1000000)
        wav_resp.close()

        anim_resp = self.client.get("/animation")
        anim_content = anim_resp.get_data(as_text=True)
        self.assertIn("mzm-vo-controller", anim_content)
        self.assertIn("/animation/audio", anim_content)
        anim_resp.close()



if __name__ == "__main__":
    unittest.main()
