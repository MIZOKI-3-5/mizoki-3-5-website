"""Platform-level tests for the flagship-demo build: URL repairs, canonical
host, robots/sitemap, share embedding, signed export, rate limiting,
telemetry, and the contact lead path."""

import hashlib
import json
import re
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime
from mizoki_runtime import demo_telemetry


REPO_ROOT = Path(__file__).resolve().parents[1]

DEMO_PAGES = (
    "/demo", "/demo/signal", "/demo/counsel", "/demo/estate",
    "/demo/capital", "/demo/risk", "/demo/nexus",
)


class _AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=self.data_dir)
        self.app = create_app(runtime=runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()


class UrlRepairTestCase(_AppTestCase):
    """D1/D2/D3/D4/D6 regressions."""

    def test_demo_pages_use_absolute_asset_urls(self) -> None:
        for path in DEMO_PAGES:
            body = self.client.get(path, follow_redirects=True).get_data(as_text=True)
            self.assertIn('href="/assets/css/styles.css"', body, path)
            self.assertNotIn('href="assets/', body, path)
            self.assertNotIn('src="assets/', body, path)

    def test_capital_page_loads_named_demo_js(self) -> None:
        # Part 3.2 requires assets/js/demo-capital.js (not only the shared
        # pipeline player).
        self.assertTrue((REPO_ROOT / "assets" / "js" / "demo-capital.js").is_file())
        body = self.client.get("/demo/capital").get_data(as_text=True)
        self.assertIn('src="/assets/js/demo-capital.js"', body)
        self.assertNotIn('src="assets/js/demo-capital.js"', body)

    def test_no_relative_page_links_in_demo_files(self) -> None:
        for filename in sorted(REPO_ROOT.glob("demo*.html")):
            text = filename.read_text(encoding="utf-8")
            self.assertFalse(
                re.search(r'href="assets/|src="assets/', text), filename.name
            )
            self.assertFalse(
                re.search(r'href="[a-z][a-z0-9-]*\.html', text), filename.name
            )

    def test_demo_scoped_asset_path_is_404_documented(self) -> None:
        # Relative CSS under the pretty route stays a 404 — pages must not
        # depend on it (that was D1).
        response = self.client.get("/demo/assets/css/styles.css")
        self.assertEqual(404, response.status_code)

    def test_trailing_slash_variants_resolve(self) -> None:
        for path in ("/demo/", "/demo/signal/", "/demo/counsel/", "/demo/estate/",
                     "/demo/capital/", "/demo/risk/", "/demo/nexus/"):
            response = self.client.get(path, follow_redirects=True)
            self.assertEqual(200, response.status_code, path)

    def test_walkthrough_serves_with_live_demo_cta(self) -> None:
        for path in ("/walkthrough", "/walkthrough.html"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)
        body = self.client.get("/walkthrough.html").get_data(as_text=True)
        self.assertIn("Try the live demos", body)
        self.assertIn('href="/demo"', body)
        # Nav/footer must not use relative page links (pretty-route trap).
        self.assertNotIn('href="index.html"', body)
        self.assertNotIn('href="platform.html"', body)
        self.assertIn('href="/assets/img/favicon.svg"', body)

    def test_homepage_links_to_live_demos(self) -> None:
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/demo"', body)

    def test_login_redirects_to_admin_login_when_env_unset(self) -> None:
        response = self.client.get("/login")
        self.assertEqual(302, response.status_code)
        self.assertEqual("/admin/login", response.headers["Location"])

    def test_division_pages_wired_to_demos(self) -> None:
        # /signal left this table 2026-08-20: the ORACLE pre-conversion
        # preview (owner-approved replacement, deploy run #63, 2026-08-19)
        # is a standalone noindex page that deliberately links only its own
        # anchors — no /demo wiring by design. Its serving, hygiene, and
        # honesty contract lives in test_signal_capability_site.py. The four
        # remaining divisions keep the full wiring contract.
        for page, demo_href, wants_shared_css in (
                ("/estate", "/demo/estate", True),
                ("/capital", "/demo/capital", True),
                ("/risk", "/demo/risk", True),
                ("/counsel", "/demo/counsel", True)):
            body = self.client.get(page).get_data(as_text=True)
            self.assertIn(f'href="{demo_href}"', body, page)
            self.assertIn('href="/demo"', body, page)
            if wants_shared_css:
                self.assertIn('href="/assets/css/styles.css"', body, page)
            self.assertNotIn('href="assets/', body, page)


class CanonicalHostTestCase(_AppTestCase):
    def test_www_308_redirects_to_apex(self) -> None:
        response = self.client.get("/demo", base_url="http://www.mizoki3.com")
        self.assertEqual(308, response.status_code)
        self.assertEqual("https://mizoki3.com/demo", response.headers["Location"])

    def test_www_redirect_preserves_query_string(self) -> None:
        response = self.client.get(
            "/demo/signal?scenario=leadgen_cpa&seed=7",
            base_url="http://www.mizoki3.com",
        )
        self.assertEqual(308, response.status_code)
        self.assertEqual(
            "https://mizoki3.com/demo/signal?scenario=leadgen_cpa&seed=7",
            response.headers["Location"],
        )

    def test_kill_switch_disables_redirect(self) -> None:
        self.app.config["CANONICAL_REDIRECT_ENABLED"] = False
        response = self.client.get("/demo", base_url="http://www.mizoki3.com")
        self.assertEqual(200, response.status_code)

    def test_apex_host_untouched(self) -> None:
        response = self.client.get("/demo", base_url="http://mizoki3.com")
        self.assertEqual(200, response.status_code)


class RobotsSitemapTestCase(_AppTestCase):
    def test_robots_allows_and_names_sitemap(self) -> None:
        response = self.client.get("/robots.txt")
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Allow: /", body)
        self.assertIn("https://mizoki3.com/sitemap.xml", body)

    def test_sitemap_lists_all_demo_pages(self) -> None:
        response = self.client.get("/sitemap.xml")
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        for path in ("/demo", "/demo/nexus", "/demo/signal", "/demo/counsel",
                     "/demo/estate", "/demo/capital", "/demo/risk",
                     "/walkthrough.html", "/blog", "/signal", "/risk"):
            self.assertIn(f"https://mizoki3.com{path}</loc>", body, path)


class ShareEmbeddingTestCase(_AppTestCase):
    def test_valid_params_are_embedded_on_body(self) -> None:
        body = self.client.get(
            "/demo/signal?scenario=leadgen_cpa&seed=7"
        ).get_data(as_text=True)
        self.assertIn('data-scenario="leadgen_cpa"', body)
        self.assertIn('data-seed="7"', body)

    def test_invalid_scenario_is_not_embedded(self) -> None:
        body = self.client.get(
            '/demo/signal?scenario="><script>alert(1)</script>&seed=x'
        ).get_data(as_text=True)
        self.assertNotIn("data-scenario", body)
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_every_demo_page_supports_embedding(self) -> None:
        cases = {
            "/demo/counsel": "ct_probate_opening",
            "/demo/estate": "basis_step_up",
            "/demo/capital": "growth_reallocation",
            "/demo/risk": "vendor_breach_drill",
            "/demo/nexus": "cpm_shock",
        }
        for path, scenario in cases.items():
            body = self.client.get(
                f"{path}?scenario={scenario}&seed=11"
            ).get_data(as_text=True)
            self.assertIn(f'data-scenario="{scenario}"', body, path)
            self.assertIn('data-seed="11"', body, path)


class ExportTestCase(_AppTestCase):
    def test_export_digest_matches_canonical_trace_json(self) -> None:
        for demo, scenario in (("signal", "ecommerce_roas"),
                               ("risk", "quarterly_close"),
                               ("nexus", "cpm_shock")):
            response = self.client.get(
                f"/api/demo/{demo}/export?scenario={scenario}&seed=42"
            )
            self.assertEqual(200, response.status_code, demo)
            body = response.get_json()
            self.assertEqual("sha256", body["integrity"]["algo"])
            expected = hashlib.sha256(
                json.dumps(body["trace"], sort_keys=True).encode("utf-8")
            ).hexdigest()
            self.assertEqual(expected, body["integrity"]["digest"], demo)
            self.assertIn("generated_at", body["integrity"])

    def test_export_rejects_unknown_scenario(self) -> None:
        response = self.client.get("/api/demo/signal/export?scenario=bogus")
        self.assertEqual(400, response.status_code)


class RateLimiterTestCase(_AppTestCase):
    def test_31st_request_is_429_with_retry_after(self) -> None:
        self.app.config["DEMO_RATE_LIMIT_ENFORCE_IN_TESTS"] = True
        codes = [
            self.client.get(
                "/api/demo/signal/scenarios",
                headers={"X-Forwarded-For": "203.0.113.9"},
            ).status_code
            for _ in range(31)
        ]
        self.assertTrue(all(code == 200 for code in codes[:30]), codes)
        self.assertEqual(429, codes[30])
        response = self.client.get(
            "/api/demo/signal/scenarios", headers={"X-Forwarded-For": "203.0.113.9"}
        )
        self.assertEqual(429, response.status_code)
        self.assertIn("Retry-After", response.headers)
        self.assertGreaterEqual(int(response.headers["Retry-After"]), 1)

    def test_weighted_endpoints_consume_more_tokens(self) -> None:
        self.app.config["DEMO_RATE_LIMIT_ENFORCE_IN_TESTS"] = True
        # Export weight 2 → 15 exports drain a 30-token bucket.
        headers = {"X-Forwarded-For": "203.0.113.77"}
        codes = [
            self.client.get(
                "/api/demo/signal/export?scenario=ecommerce_roas", headers=headers
            ).status_code
            for _ in range(16)
        ]
        self.assertEqual(200, codes[14])
        self.assertEqual(429, codes[15])

    def test_limits_are_per_client_key(self) -> None:
        self.app.config["DEMO_RATE_LIMIT_ENFORCE_IN_TESTS"] = True
        for _ in range(31):
            self.client.get("/api/demo/signal/scenarios",
                            headers={"X-Forwarded-For": "198.51.100.1"})
        other = self.client.get("/api/demo/signal/scenarios",
                                headers={"X-Forwarded-For": "198.51.100.2"})
        self.assertEqual(200, other.status_code)

    def test_disabled_by_default_under_testing(self) -> None:
        codes = [self.client.get("/api/demo/signal/scenarios").status_code
                 for _ in range(35)]
        self.assertTrue(all(code == 200 for code in codes))


class TelemetryTestCase(_AppTestCase):
    def _telemetry_rows(self):
        path = self.data_dir / "demo_telemetry.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def test_valid_event_appends_row_without_ip_or_ua(self) -> None:
        response = self.client.post(
            "/api/demo/telemetry",
            json={"event": "demo_started", "demo": "signal", "scenario": "ecommerce_roas"},
        )
        self.assertEqual(200, response.status_code)
        rows = self._telemetry_rows()
        self.assertEqual(1, len(rows))
        self.assertEqual(
            {"ts", "event", "demo", "scenario"}, set(rows[0].keys())
        )

    def test_unknown_event_rejected(self) -> None:
        response = self.client.post(
            "/api/demo/telemetry",
            json={"event": "pwned", "demo": "signal", "scenario": "x"},
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual([], self._telemetry_rows())

    def test_extra_keys_rejected(self) -> None:
        response = self.client.post(
            "/api/demo/telemetry",
            json={"event": "demo_started", "demo": "signal",
                  "scenario": "x", "ip": "1.2.3.4"},
        )
        self.assertEqual(400, response.status_code)

    def test_missing_field_rejected(self) -> None:
        response = self.client.post(
            "/api/demo/telemetry", json={"event": "demo_started", "demo": "signal"}
        )
        self.assertEqual(400, response.status_code)

    def test_summary_tool_counts_by_demo_and_scenario(self) -> None:
        for event in ("demo_started", "demo_completed", "share_copied"):
            self.client.post(
                "/api/demo/telemetry",
                json={"event": event, "demo": "nexus", "scenario": "cpm_shock"},
            )
        response = self.client.post(
            "/api/mcp/call", json={"name": "demo.telemetry.summary", "arguments": {}}
        )
        self.assertEqual(200, response.status_code)
        summary = response.get_json()["result"]
        self.assertEqual(3, summary["total_events"])
        self.assertEqual(1, summary["by_demo"]["nexus"]["share_copied"])
        self.assertEqual(
            1, summary["by_demo_scenario"]["nexus:cpm_shock"]["demo_completed"]
        )

    def test_all_documented_events_accepted(self) -> None:
        for event in sorted(demo_telemetry.TELEMETRY_EVENTS):
            response = self.client.post(
                "/api/demo/telemetry",
                json={"event": event, "demo": "signal", "scenario": "s"},
            )
            self.assertEqual(200, response.status_code, event)


class ContactTestCase(_AppTestCase):
    def test_contact_serves(self) -> None:
        for path in ("/contact", "/contact.html"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code, path)

    def test_source_param_echoed_into_hidden_field(self) -> None:
        body = self.client.get("/contact?source=demo-nexus").get_data(as_text=True)
        self.assertIn('name="source" value="demo-nexus"', body)

    def test_source_param_is_sanitized(self) -> None:
        body = self.client.get(
            '/contact?source=demo"><script>x</script>'
        ).get_data(as_text=True)
        self.assertNotIn("<script>x</script>", body)
        self.assertIn('name="source" value="demoscriptxscript"', body)


class HomepageLiveTeaserTestCase(_AppTestCase):
    """Teaser machinery stays real (never a mock); the homepage moved on.

    The dossier homepage replaced the embedded live teaser (owner-approved
    swap) — this class's first assertion pinned the pre-swap page and rode
    along as "the 2 pre-existing homepage failures" from July until adapted
    to the served reality on 2026-08-20. The page's interactive proof is now
    the ACT-991 gauge widget; the teaser driver and its engine scenarios
    remain real, served, and pinned by the other two tests.
    """

    def test_homepage_serves_the_dossier_decision_widget(self) -> None:
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("ACT-991", body)
        self.assertIn('id="arc"', body)
        # The swap is complete — the old teaser must not half-return.
        self.assertNotIn('id="liveTeaser"', body)

    def test_home_demo_js_targets_real_endpoints_with_fixed_seed(self) -> None:
        script = (REPO_ROOT / "assets" / "js" / "home-demo.js").read_text(encoding="utf-8")
        self.assertIn('"/api/demo/" + cfg.division + "/run"', script)
        self.assertIn("var SEED = 42;", script)
        # The teaser must never invent numbers client-side.
        self.assertNotIn("Math.random", script)
        served = self.client.get("/assets/js/home-demo.js")
        self.assertEqual(200, served.status_code)

    def test_teaser_scenarios_exist_in_engines(self) -> None:
        script = (REPO_ROOT / "assets" / "js" / "home-demo.js").read_text(encoding="utf-8")
        for division, scenario in (("capital", "dividend_covenant_veto"),
                                   ("capital", "debt_paydown_vs_buyback"),
                                   ("capital", "growth_reallocation"),
                                   ("signal", "ecommerce_roas")):
            self.assertIn(scenario, script)
            response = self.client.post(
                f"/api/demo/{division}/run", json={"scenario": scenario, "seed": 42}
            )
            self.assertEqual(200, response.status_code, scenario)
            card = response.get_json()["decision_card"]
            self.assertIn("causal_truth", card, scenario)
            self.assertTrue(card["causal_truth"], scenario)


class CausalTruthMarkupTestCase(_AppTestCase):
    def test_signal_and_capital_pages_carry_causal_truth_slot(self) -> None:
        for path in ("/demo/signal", "/demo/capital"):
            body = self.client.get(path).get_data(as_text=True)
            self.assertIn('id="dcTruthWrap"', body, path)
            self.assertIn('id="dcTruth"', body, path)
            self.assertIn("Causal truth", body, path)

    def test_players_render_causal_truth(self) -> None:
        for name in ("demo-pipeline.js", "demo-signal.js"):
            script = (REPO_ROOT / "assets" / "js" / name).read_text(encoding="utf-8")
            self.assertIn("causal_truth", script, name)
            self.assertIn("dcTruthWrap", script, name)


class PricingPageTestCase(_AppTestCase):
    def test_pricing_serves_modern_page(self) -> None:
        response = self.client.get("/pricing.html")
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        # Modern design system (accent-numeral logo), not the legacy MIZ OKI shell.
        # Re-pointed by the sitewide wordmark sweep: same `.three` logo, now MIZ OKI 3.5.
        self.assertIn("MIZ&nbsp;OKI&nbsp;<span class=\"three\">3.5</span>", body)
        self.assertNotIn('href="base.css"', body)
        self.assertNotIn('href="style.css"', body)

    def test_tiers_map_to_autonomy_ladder(self) -> None:
        body = self.client.get("/pricing.html").get_data(as_text=True)
        for marker in ("Core Intelligence", "Operational Autonomy",
                       "Full Governance Suite", "approval-first",
                       "Autonomy ladder"):
            self.assertIn(marker, body, marker)

    def test_ctas_are_live_not_placeholders(self) -> None:
        body = self.client.get("/pricing.html").get_data(as_text=True)
        self.assertIn("mailto:briefing@mediaintelligence.ai", body)
        self.assertIn('href="/demo"', body)
        self.assertNotIn('href="#"', body)
        # No fabricated performance claims on the pricing surface.
        for banned in ("ROAS", "CAC", "%_lift"):
            self.assertNotIn(banned, body, banned)


class DemoMetaTestCase(_AppTestCase):
    def test_every_demo_page_has_favicon_canonical_and_og(self) -> None:
        canonical = {
            "/demo": "https://mizoki3.com/demo",
            "/demo/signal": "https://mizoki3.com/demo/signal",
            "/demo/counsel": "https://mizoki3.com/demo/counsel",
            "/demo/estate": "https://mizoki3.com/demo/estate",
            "/demo/capital": "https://mizoki3.com/demo/capital",
            "/demo/risk": "https://mizoki3.com/demo/risk",
            "/demo/nexus": "https://mizoki3.com/demo/nexus",
        }
        for path, url in canonical.items():
            body = self.client.get(path).get_data(as_text=True)
            self.assertIn('href="/assets/img/favicon.svg"', body, path)
            self.assertIn(f'<link rel="canonical" href="{url}" />', body, path)
            self.assertIn('property="og:image"', body, path)
            self.assertIn('content="summary_large_image"', body, path)

    def test_bare_icon_requests_do_not_404(self) -> None:
        """Browsers/crawlers hit these at the root regardless of <link> tags.

        Regression guard: the whole site 404'd on /favicon.ico before 2026-07-27.
        """
        for path, mimetype in (
            ("/favicon.ico", "image/x-icon"),
            ("/apple-touch-icon.png", "image/png"),
            ("/apple-touch-icon-precomposed.png", "image/png"),
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.mimetype, mimetype, path)
            self.assertTrue(response.get_data(), path)

    def test_favicon_assets_exist_on_disk(self) -> None:
        base = Path(__file__).resolve().parent.parent / "assets" / "img"
        for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png"):
            asset = base / name
            self.assertTrue(asset.is_file(), f"missing {name}")
            self.assertGreater(asset.stat().st_size, 0, name)
        # Real multi-size ICO, not an SVG renamed — 3 frames, PNG-encoded.
        ico = (base / "favicon.ico").read_bytes()
        self.assertEqual(ico[:4], b"\x00\x00\x01\x00", "not an ICO container")
        self.assertEqual(int.from_bytes(ico[4:6], "little"), 3, "expected 16/32/48 frames")
        # The SVG must parse. A "--" inside an XML comment silently breaks the
        # whole file, and a browser renders nothing — caught exactly that once.
        xml.dom.minidom.parse(str(base / "favicon.svg"))

    def test_every_page_declares_the_icon_set(self) -> None:
        """Every served page — static file or Flask template — links all three.

        "/" left the list 2026-08-20: the canon-pinned dossier homepage ships
        its own head without the <link> set (owner-approved swap; the test is
        adapted, never the canon-locked page), and app.py serves /favicon.ico
        and /apple-touch-icon.png at the root paths clients request regardless
        of link tags, so browsers still resolve the icons.
        """
        for path in ("/pricing", "/demo", "/demo/capital", "/walkthrough",
                     "/blog", "/counsel", "/admin/login", "/contact"):
            # follow_redirects: /blog/ style paths 302 to their canonical form.
            body = self.client.get(path, follow_redirects=True).get_data(as_text=True)
            self.assertIn('href="/assets/img/favicon.svg"', body, path)
            self.assertIn('href="/assets/img/favicon.ico"', body, path)
            self.assertIn('href="/assets/img/apple-touch-icon.png"', body, path)
            # The pre-2026-07-27 path must not linger anywhere.
            self.assertNotIn("/assets/svg/favicon.svg", body, path)

    def test_og_cards_exist_on_disk(self) -> None:
        for name in ("og-demo", "og-signal", "og-counsel", "og-estate",
                     "og-capital", "og-risk", "og-nexus"):
            self.assertTrue(
                (REPO_ROOT / "assets" / "img" / "og" / f"{name}.svg").is_file(), name
            )


if __name__ == "__main__":
    unittest.main()
