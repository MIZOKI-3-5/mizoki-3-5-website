"""No-egress regression — derived from the LIVE route table, flags OFF and ON.
Run 1 item 1.B.6 (2026-09-02).

Scope is derived from ``app.url_map`` (rule 01: a gate whose scope is a
hand-maintained list drifts): every GET rule under the homepage, ``/shopify``
and ``/shopify/*``, plus every route this run added, is fetched with the two
flags OFF and then ON, and the served HTML must be self-contained — no
external ``<script src>``, ``<link rel=stylesheet>``, ``<img>/<iframe>/<video>``
source, ``@import``, ``fetch()``/``sendBeacon`` to another origin, or web-font
host. The only permitted network side effects are same-origin. Seeded both
directions against a synthetic page.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import create_app
from mizoki_runtime import create_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]
OWN_HOSTS = ("mizoki3.com", "www.mizoki3.com")
EXTERNAL_RESOURCE = re.compile(
    r"<(?:script|img|iframe|video|audio|source|link|embed|object)\b[^>]*?\b(?:src|href|poster|data)=[\"'](https?:)?//([^/\"']+)",
    re.I)
CSS_IMPORT = re.compile(r"@import\s+(?:url\()?[\"']?(https?:)?//([^/\"')]+)", re.I)
JS_EGRESS = re.compile(r"(?:fetch|sendBeacon|XMLHttpRequest|open|WebSocket|EventSource)\s*\(\s*[\"'](https?:)?//([^/\"']+)", re.I)
FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com", "use.typekit.net", "cdnjs.cloudflare.com", "cdn.jsdelivr.net", "unpkg.com")
ANALYTICS_HOSTS = ("google-analytics.com", "googletagmanager.com", "plausible.io", "usefathom.com", "segment.com", "hotjar.com")

# MEASURED 2026-09-02 when this sweep first ran: the canon-locked homepage
# (index.html is pinned in canon.lock.json — v1.5 night-dossier look, owner
# ruling 2026-07-30) loads its web fonts from Google Fonts. That is a real
# third-party egress on the live homepage, pre-existing, and not something a
# session may edit (site-visible + canon lock → owner decision, recorded as
# R-4 in the Run-1 build report). It is held HERE, per path and per host, so the
# sweep stays honest: any OTHER host on these pages, or ANY host on any other
# scoped page, fails. The row is removed when the fonts are self-hosted.
KNOWN_EGRESS: dict[str, frozenset[str]] = {
    "/": frozenset({"fonts.googleapis.com", "fonts.gstatic.com"}),
    "/index.html": frozenset({"fonts.googleapis.com", "fonts.gstatic.com"}),
}


def egress_hosts(html: str) -> set[str]:
    hosts = set()
    for rx in (EXTERNAL_RESOURCE, CSS_IMPORT, JS_EGRESS):
        for m in rx.finditer(html):
            host = m.group(2).lower()
            if host not in OWN_HOSTS:
                hosts.add(host)
    for host in FONT_HOSTS + ANALYTICS_HOSTS:
        if host in html:
            hosts.add(host)
    return hosts


class SeededDirection(unittest.TestCase):
    def test_seeded_external_resources_are_caught(self) -> None:
        page = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">'
                '<script src="//cdn.example.net/x.js"></script>'
                '<script>fetch("https://plausible.io/api/event")</script>')
        self.assertEqual({"fonts.googleapis.com", "cdn.example.net", "plausible.io"}, egress_hosts(page))

    def test_same_origin_and_inline_stay_legal(self) -> None:
        page = ('<script>fetch("/event",{method:"POST"})</script><img src="/assets/x.png">'
                '<a href="https://mizoki3.com/signal">Signal</a><link rel="canonical" href="https://mizoki3.com/shopify">'
                '<style>body{font-family:Inter,system-ui}</style>')
        self.assertEqual(set(), egress_hosts(page))


class LiveRouteSweep(unittest.TestCase):
    NEW_ROUTES = ("/event", "/shopify/event", "/shopify/pilot-request")

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        self.app = create_app(runtime=runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def scoped_get_rules(self) -> list[str]:
        rules = []
        for rule in self.app.url_map.iter_rules():
            if "GET" not in (rule.methods or ()) or "<" in rule.rule:
                continue
            r = rule.rule
            if r in ("/", "/index.html") or r == "/shopify" or r.startswith("/shopify/") or r == "/shopify.html":
                rules.append(r)
        self.assertTrue(rules, "route table yielded no scoped GET rules — the sweep would be vacuous")
        self.assertIn("/shopify", rules)
        self.assertIn("/", rules)
        return sorted(set(rules))

    def sweep(self, label: str) -> None:
        for path in self.scoped_get_rules():
            response = self.client.get(path, headers={"User-Agent": "Mozilla/5.0 (no-egress sweep)"})
            self.assertIn(response.status_code, (200, 301, 302), f"{label} {path}")
            if response.status_code == 200 and response.mimetype == "text/html":
                html = response.get_data(as_text=True)
                hosts = egress_hosts(html)
                known = KNOWN_EGRESS.get(path, frozenset())
                self.assertEqual(set(), hosts - known, f"{label} {path}: third-party egress beyond the held baseline")
                if known:
                    # The baseline only shrinks: a page that stopped loading a
                    # held host must have its row removed, not kept as debris.
                    self.assertEqual(set(known), hosts, f"{label} {path}: KNOWN_EGRESS row is stale — remove it")
            response.close()
        for path in self.NEW_ROUTES:
            # POST-only routes: a GET must not serve anything, and the flag-ON
            # responses are JSON/empty — no HTML, no redirect off-origin.
            response = self.client.get(path)
            self.assertIn(response.status_code, (404, 405), f"{label} {path}")
            self.assertNotIn("Location", response.headers)
            response.close()

    def test_flags_off(self) -> None:
        with mock.patch.dict(os.environ, {"SITE_EVENTS": "false", "PILOT_FORM": "false"}):
            self.sweep("flags OFF")

    def test_flags_on(self) -> None:
        with mock.patch.dict(os.environ, {"SITE_EVENTS": "true", "PILOT_FORM": "true"}):
            self.sweep("flags ON")
            html = self.client.get("/shopify").get_data(as_text=True)
            self.assertIn('data-mizoki="site-events"', html)   # the sweep really saw the injected script
            self.assertIn('fetch("/event"', html)


if __name__ == "__main__":
    unittest.main()
