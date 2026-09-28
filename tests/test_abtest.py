"""Site A/B/C test contracts (SITE A/B/C TEST — DESIGN FIX r1.0).

Pins the whole measurement fix: one canonical indexed landing at /signal,
dark-by-default randomization, deterministic sticky assignment, the
no-noindex-leak posture rule, tracked CTA redirects with [ref] attribution,
the tier-3 goal beacon, and the structured event log. Seeded checks run in
both directions wherever a rule could silently stop firing.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from mizoki_runtime import abtest, create_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]

# Content markers that identify which variant's file was rendered.
MARKER = {
    "a": "A nervous system for your business.",
    "b": "Know why performance moved.",
    "c": "Causal Growth Control",
}

CANONICAL_TAG = '<link rel="canonical" href="https://mizoki3.com/signal">'
INDEX_TAG = '<meta name="robots" content="index,follow">'
NOINDEX_TAG = '<meta name="robots" content="noindex,follow">'

LANDING_FILES = {
    "a": REPO_ROOT / "signal.html",
    "b": REPO_ROOT / "marketing" / "index.html",
    "c": REPO_ROOT / "media" / "index.html",
}


def _ua_for_variant(want: str) -> str:
    """Find a user-agent whose deterministic assignment is the wanted arm."""
    for i in range(200):
        # Must NOT match the bot classifier — bots are served but never cookied.
        ua = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/127.0.{i} Safari/537.36"
        if abtest.assign(abtest.visitor_key("203.0.113.7", ua)) == want:
            return ua
    raise AssertionError(f"no probe UA found for variant {want}")


class _AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT,
                                 data_dir=Path(self.temp_dir.name))
        self.app = create_app(runtime=runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        abtest.reset_counters()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def get(self, path: str, ua: str = "Mozilla/5.0 (test browser)", **kw):
        return self.client.get(path, headers={"User-Agent": ua}, **kw)


class ModuleUnitTestCase(unittest.TestCase):
    """Framework-free pieces, both directions."""

    def test_cookie_parse_round_trip_and_rejection(self) -> None:
        visitor = "0123456789abcdef"
        for variant in abtest.VARIANTS:
            value = abtest.cookie_value(variant, visitor)
            self.assertEqual((variant, visitor), abtest.parse_cookie(value))
        for bad in (None, "", "d.0123456789abcdef", "a.short", "a.ZZZZZZZZZZZZZZZZ",
                    "a.0123456789abcdef0", "b", "b.", "<script>", "a..deadbeef"):
            self.assertIsNone(abtest.parse_cookie(bad), bad)

    def test_assignment_is_deterministic_and_covers_all_arms(self) -> None:
        seen = {}
        for i in range(200):
            key = abtest.visitor_key("198.51.100.9", f"agent {i}")
            self.assertEqual(abtest.assign(key), abtest.assign(key))
            seen.setdefault(abtest.assign(key), 0)
            seen[abtest.assign(key)] += 1
        self.assertEqual(set(abtest.VARIANTS), set(seen))

    def test_visitor_key_never_echoes_inputs(self) -> None:
        key = abtest.visitor_key("198.51.100.9", "Mozilla/5.0 SecretAgent")
        self.assertRegex(key, r"^[0-9a-f]{16}$")
        self.assertNotIn("198.51.100.9", key)
        self.assertNotIn("SecretAgent", key)

    def test_bot_classifier_both_directions(self) -> None:
        for bot in ("Googlebot/2.1", "bingbot", "curl/8.5", "python-requests/2.32",
                    "HeadlessChrome", "", None, "facebookexternalhit/1.1"):
            self.assertTrue(abtest.is_bot(bot), bot)
        for human in ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Safari/605.1",
                      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/127.0"):
            self.assertFalse(abtest.is_bot(human), human)

    def test_referrer_classes(self) -> None:
        cases = {
            None: "direct",
            "": "direct",
            "https://www.google.com/search?q=causal+growth": "search",
            "https://duckduckgo.com/?q=x": "search",
            "https://www.linkedin.com/feed/": "social",
            "https://t.co/abc": "social",
            "https://mizoki3.com/pricing": "internal",
            "https://www.mizoki3.com/": "internal",
            "https://example.org/article": "external",
        }
        for referrer, expected in cases.items():
            self.assertEqual(expected,
                             abtest.classify_referrer(referrer, "mizoki3.com"),
                             referrer)

    def test_head_posture_strips_and_injects_both_directions(self) -> None:
        seeded = (
            '<html><head>\n'
            '<link rel="canonical" href="https://mizoki3.com/media">\n'
            '<meta name="robots" content="noindex,follow">\n'
            '<meta property="og:url" content="https://mizoki3.com/media">\n'
            '</head><body></body></html>')
        out = abtest.apply_head_posture(seeded, abtest.CANONICAL_URL,
                                        "index,follow")
        self.assertEqual(1, out.count('rel="canonical"'))
        self.assertEqual(1, out.count('name="robots"'))
        self.assertIn(CANONICAL_TAG, out)
        self.assertIn(INDEX_TAG, out)
        self.assertNotIn("noindex", out)
        self.assertIn('property="og:url" content="https://mizoki3.com/signal"',
                      out)
        # Idempotent, and clean injection when no tags exist at all.
        self.assertEqual(out, abtest.apply_head_posture(
            out, abtest.CANONICAL_URL, "index,follow"))
        bare = abtest.apply_head_posture("<head></head>", abtest.CANONICAL_URL,
                                         "index,follow")
        self.assertIn(CANONICAL_TAG, bare)
        with self.assertRaises(ValueError):
            abtest.apply_head_posture("<html>no head close", abtest.CANONICAL_URL,
                                      "index,follow")

    def test_ref_token_marks_off_protocol(self) -> None:
        self.assertEqual("B", abtest.ref_token("b", "b"))
        self.assertEqual("A", abtest.ref_token("a", "c"))
        self.assertEqual("XC", abtest.ref_token(None, "c"))
        self.assertEqual("XB", abtest.ref_token("junk", "b"))

    def test_cta_locations_are_registry_only_mailtos(self) -> None:
        for key, entry in abtest.CTA_REGISTRY.items():
            location = abtest.cta_location(key, "a")
            self.assertTrue(location.startswith(f"mailto:{entry['address']}?subject="),
                            key)
            self.assertIn("%5Bref%20A%5D", location, key)

    def test_goal_page_normalization(self) -> None:
        self.assertEqual("/signal", abtest.normalize_goal_page("/signal"))
        self.assertEqual("/signal", abtest.normalize_goal_page("/signal.html"))
        self.assertEqual("/marketing", abtest.normalize_goal_page("/marketing/"))
        self.assertIsNone(abtest.normalize_goal_page("/pricing"))
        self.assertIsNone(abtest.normalize_goal_page("x" * 65))
        self.assertIsNone(abtest.normalize_goal_page(123))

    def test_srm_check_shape(self) -> None:
        even = abtest.srm_check({"a": 100, "b": 100, "c": 100})
        self.assertEqual(300, even["n"])
        self.assertEqual(1.0, even["p"])
        self.assertEqual({"n": 0, "chi2": None, "p": None},
                         abtest.srm_check({"a": 0, "b": 0, "c": 0}))


class DarkModeTestCase(_AppTestCase):
    """MIZOKI_ABTEST_MODE unset/off: /signal is a plain canonical page."""

    def test_signal_serves_variant_a_with_canonical_posture(self) -> None:
        for path in ("/signal", "/signal.html"):
            response = self.get(path)
            body = response.get_data(as_text=True)
            self.assertEqual(200, response.status_code, path)
            self.assertIn(MARKER["a"], body, path)
            self.assertIn(CANONICAL_TAG, body, path)
            self.assertIn(INDEX_TAG, body, path)
            self.assertNotIn('content="noindex', body, path)
            self.assertEqual(1, body.count('rel="canonical"'), path)
            self.assertEqual(1, body.count('name="robots"'), path)
            self.assertIsNone(response.headers.get("Set-Cookie"), path)
            self.assertEqual("private, no-store",
                             response.headers.get("Cache-Control"), path)
            self.assertIn("Cookie", response.headers.get("Vary", ""), path)

    def test_dark_mode_ignores_a_stale_assignment_cookie(self) -> None:
        self.client.set_cookie("mv", "b.0123456789abcdef")
        body = self.get("/signal").get_data(as_text=True)
        self.assertIn(MARKER["a"], body)

    def test_noncanonical_landings_serve_their_files_byte_identical(self) -> None:
        for path, variant in (("/marketing", "b"), ("/media", "c")):
            response = self.get(path)
            self.assertEqual(200, response.status_code, path)
            self.assertEqual(LANDING_FILES[variant].read_bytes(),
                             response.get_data(), path)
            self.assertEqual("private, no-store",
                             response.headers.get("Cache-Control"), path)

    def test_noncanonical_files_carry_baked_posture(self) -> None:
        for variant in ("b", "c"):
            text = LANDING_FILES[variant].read_text(encoding="utf-8")
            self.assertIn(CANONICAL_TAG, text, variant)
            self.assertIn(NOINDEX_TAG, text, variant)
            self.assertEqual(1, text.count('rel="canonical"'), variant)
            self.assertEqual(1, text.count('name="robots"'), variant)

    def test_sitemap_lists_canonical_not_the_noindexed_landing(self) -> None:
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("https://mizoki3.com/signal</loc>", sitemap)
        self.assertNotIn("https://mizoki3.com/marketing</loc>", sitemap)
        self.assertNotIn("https://mizoki3.com/media</loc>", sitemap)
        # The /marketing SUB-pages are not test variants and stay listed.
        self.assertIn("https://mizoki3.com/marketing/engine</loc>", sitemap)

    def test_dark_mode_logs_exposure_not_assignment(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.get("/signal")
        events = [json.loads(line) for line in buffer.getvalue().splitlines()
                  if line.startswith("{")]
        kinds = {e["kind"] for e in events if e.get("event") == "mizoki_abtest"}
        self.assertEqual({"exposure"}, kinds)
        self.assertEqual({"a": 0, "b": 0, "c": 0}, abtest.counters_snapshot())


class LiveModeTestCase(_AppTestCase):
    """MIZOKI_ABTEST_MODE=on: randomized, sticky, posture-safe serving."""

    def setUp(self) -> None:
        super().setUp()
        patcher = patch.dict("os.environ", {"MIZOKI_ABTEST_MODE": "on"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_first_visit_assigns_pins_and_serves_the_arm(self) -> None:
        ua = _ua_for_variant("b")
        response = self.client.get(
            "/signal", headers={"User-Agent": ua},
            environ_base={"REMOTE_ADDR": "203.0.113.7"})
        body = response.get_data(as_text=True)
        cookie = response.headers.get("Set-Cookie", "")
        match = re.search(r"mv=([abc]\.[0-9a-f]{16})", cookie)
        self.assertIsNotNone(match, cookie)
        self.assertTrue(match.group(1).startswith("b."), match.group(1))
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn(MARKER["b"], body)

    def test_variant_html_at_canonical_url_never_leaks_noindex(self) -> None:
        # THE load-bearing posture rule: variants B and C carry baked noindex
        # in their own files; served at /signal they must be index,follow with
        # the /signal canonical.
        for variant in ("b", "c"):
            ua = _ua_for_variant(variant)
            body = self.client.get(
                "/signal", headers={"User-Agent": ua},
                environ_base={"REMOTE_ADDR": "203.0.113.7"},
            ).get_data(as_text=True)
            self.assertIn(MARKER[variant], body, variant)
            self.assertIn(CANONICAL_TAG, body, variant)
            self.assertIn(INDEX_TAG, body, variant)
            # Tag form only — explanatory comments may mention the word.
            self.assertNotIn('content="noindex', body, variant)
            self.assertEqual(1, body.count('rel="canonical"'), variant)
            self.assertEqual(1, body.count('name="robots"'), variant)

    def test_cookie_pins_the_variant_and_is_not_reissued(self) -> None:
        self.client.set_cookie("mv", "c.0123456789abcdef")
        response = self.get("/signal")
        self.assertIn(MARKER["c"], response.get_data(as_text=True))
        self.assertIsNone(response.headers.get("Set-Cookie"))

    def test_malformed_cookie_is_reassigned(self) -> None:
        self.client.set_cookie("mv", "z.....")
        response = self.get("/signal")
        self.assertIn("mv=", response.headers.get("Set-Cookie", ""))

    def test_same_client_is_sticky_without_cookies(self) -> None:
        ua = "Mozilla/5.0 (consistent client)"
        bodies = set()
        for _ in range(3):
            body = self.client.get(
                "/signal", headers={"User-Agent": ua},
                environ_base={"REMOTE_ADDR": "198.51.100.20"},
            ).get_data(as_text=True)
            bodies.add(next(v for v, marker in MARKER.items() if marker in body))
        self.assertEqual(1, len(bodies))

    def test_bots_get_stable_content_but_no_cookie(self) -> None:
        response = self.get("/signal", ua="Googlebot/2.1 (+http://www.google.com/bot.html)")
        self.assertEqual(200, response.status_code)
        self.assertIsNone(response.headers.get("Set-Cookie"))

    def test_assignment_logged_once_then_exposures(self) -> None:
        ua = _ua_for_variant("a")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            first = self.client.get("/signal", headers={"User-Agent": ua},
                                    environ_base={"REMOTE_ADDR": "203.0.113.7"})
            cookie = re.search(r"mv=([abc]\.[0-9a-f]{16})",
                               first.headers["Set-Cookie"]).group(1)
            self.client.set_cookie("mv", cookie)
            self.client.get("/signal", headers={"User-Agent": ua},
                            environ_base={"REMOTE_ADDR": "203.0.113.7"})
        events = [json.loads(line) for line in buffer.getvalue().splitlines()
                  if line.startswith("{")]
        kinds = [e["kind"] for e in events if e.get("event") == "mizoki_abtest"]
        self.assertEqual(["assignment", "exposure"], kinds)
        for event in events:
            # Privacy posture: never raw ip/ua/referrer in an event line.
            self.assertLessEqual(
                set(event), {"event", "kind", "ts", "page", "variant",
                             "assigned", "visitor", "bot", "ref", "mode",
                             "cta", "goal"})
            self.assertRegex(event["visitor"], r"^[0-9a-f]{16}$")
        self.assertEqual(1, sum(abtest.counters_snapshot().values()))


class TrackedCtaTestCase(_AppTestCase):
    def test_known_cta_redirects_to_registry_mailto_with_ref(self) -> None:
        response = self.get("/go/pilot?cta=marketing-hero")
        self.assertEqual(302, response.status_code)
        location = response.headers["Location"]
        self.assertTrue(location.startswith("mailto:briefing@mediaintelligence.ai?subject="))
        self.assertIn("MIZ%20OKI%20Signal%2090-Day%20Growth%20Pilot", location)
        # Dark mode / no assignment ⇒ off-protocol ref for a B-page CTA.
        self.assertIn("%5Bref%20XB%5D", location)

    def test_assigned_visitor_ref_rides_the_subject(self) -> None:
        with patch.dict("os.environ", {"MIZOKI_ABTEST_MODE": "on"}):
            self.client.set_cookie("mv", "a.0123456789abcdef")
            location = self.get("/go/pilot?cta=media-final").headers["Location"]
        self.assertTrue(location.startswith("mailto:contact@mizoki3.com?subject="))
        self.assertIn("%5Bref%20A%5D", location)

    def test_unknown_cta_404s_and_no_open_redirect(self) -> None:
        self.assertEqual(404, self.get("/go/pilot").status_code)
        self.assertEqual(404, self.get("/go/pilot?cta=nope").status_code)
        # A url/target parameter must never steer the destination.
        location = self.get(
            "/go/pilot?cta=signal-briefing&url=https://evil.example"
        ).headers["Location"]
        self.assertTrue(location.startswith("mailto:briefing@mediaintelligence.ai"))
        self.assertNotIn("evil.example", location)

    def test_cta_click_is_logged(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.get("/go/pilot?cta=signal-briefing")
        events = [json.loads(line) for line in buffer.getvalue().splitlines()
                  if line.startswith("{")]
        clicks = [e for e in events if e.get("kind") == "cta_click"]
        self.assertEqual(1, len(clicks))
        self.assertEqual("signal-briefing", clicks[0]["cta"])
        self.assertEqual("a", clicks[0]["variant"])


class GoalBeaconTestCase(_AppTestCase):
    def _post(self, payload, **kw):
        return self.client.post("/api/abtest/goal", json=payload,
                                headers={"User-Agent": "Mozilla/5.0 (test)"},
                                **kw)

    def test_valid_goal_is_accepted_and_logged(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            response = self._post({"goal": "pilot-view", "page": "/marketing"})
        self.assertEqual(204, response.status_code)
        events = [json.loads(line) for line in buffer.getvalue().splitlines()
                  if line.startswith("{")]
        goals = [e for e in events if e.get("kind") == "goal"]
        self.assertEqual(1, len(goals))
        self.assertEqual("b", goals[0]["variant"])

    def test_bad_payloads_are_rejected(self) -> None:
        self.assertEqual(400, self._post({"goal": "pilot-view",
                                          "page": "/admin"}).status_code)
        self.assertEqual(400, self._post({"goal": "other",
                                          "page": "/signal"}).status_code)
        self.assertEqual(400, self._post(["not", "a", "dict"]).status_code)
        big = self.client.post(
            "/api/abtest/goal", data=b"x" * 600,
            headers={"Content-Type": "application/json"})
        self.assertEqual(400, big.status_code)

    def test_state_endpoint_reports_honestly(self) -> None:
        response = self.client.get("/api/abtest/state")
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual("off", payload["mode"])
        self.assertEqual("/signal", payload["canonical"])
        self.assertIn("per-instance", payload["caveat"])
        self.assertIn("srm", payload)


class PageInstrumentationTestCase(unittest.TestCase):
    """The three landing files carry the instrumentation, in sync."""

    def test_no_bare_mailto_cta_remains_on_any_landing(self) -> None:
        for variant, path in LANDING_FILES.items():
            self.assertNotIn("mailto:", path.read_text(encoding="utf-8"),
                             f"untracked mailto on landing {variant}")

    def test_every_landing_routes_ctas_through_the_tracker(self) -> None:
        expected = {
            "a": ["signal-briefing"],
            "b": ["marketing-header", "marketing-hero", "marketing-pilot",
                  "marketing-final"],
            "c": ["media-final", "media-footer"],
        }
        for variant, keys in expected.items():
            text = LANDING_FILES[variant].read_text(encoding="utf-8")
            for key in keys:
                self.assertIn(f'href="/go/pilot?cta={key}"', text, key)
                self.assertIn(key, abtest.CTA_REGISTRY, key)

    def test_goal_target_and_beacon_present_and_identical(self) -> None:
        blocks = []
        for variant, path in LANDING_FILES.items():
            text = path.read_text(encoding="utf-8")
            self.assertIn("data-abtest-goal", text, variant)
            match = re.search(
                r'<script data-abtest="goal-beacon">.*?</script>', text,
                re.DOTALL)
            self.assertIsNotNone(match, f"beacon missing on {variant}")
            blocks.append(match.group(0))
            # The /media deterministic-JS rule holds everywhere.
            self.assertNotIn("Math.random", match.group(0))
            self.assertNotIn("Date.now", match.group(0))
        self.assertEqual(1, len(set(blocks)),
                         "beacon blocks drifted between landings")

    def test_registry_covers_exactly_the_ctas_on_the_pages(self) -> None:
        on_pages = set()
        for path in LANDING_FILES.values():
            on_pages.update(re.findall(r'/go/pilot\?cta=([a-z-]+)',
                                       path.read_text(encoding="utf-8")))
        self.assertEqual(on_pages, set(abtest.CTA_REGISTRY))


if __name__ == "__main__":
    unittest.main()
