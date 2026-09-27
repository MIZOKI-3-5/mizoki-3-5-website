"""Decision Studio links on the marketing site (owner directive 2026-09-16).

The standalone MIZOKI3 Decision Studio is PUBLIC at https://decisionstudio.mizoki3.com
(no sign-in, no password). The owner asked for a visible entry in primary and
mobile navigation plus contextual product links, while existing demos and
sign-in links stay. These tests pin every served route that must carry a link,
the exact Studio page each one points at, and the surfaces that must NOT carry
one (the /media executive-demo presenter keeps its same-site-only contract).
Rollback = revert the navigation commit + re-pin canon.lock.json.
"""
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]
STUDIO = "https://decisionstudio.mizoki3.com"

# route -> the Studio page its primary/shared navigation must link
NAV_TARGETS = {
    "/": f"{STUDIO}/",
    "/demo": f"{STUDIO}/decision-tree",
    "/signal": f"{STUDIO}/signal",
    "/signal/thresholds": f"{STUDIO}/signal",
    "/signal/budget": f"{STUDIO}/signal",
    "/signal/creative": f"{STUDIO}/signal",
    "/signal/audiences": f"{STUDIO}/signal",
    "/signal/measurement": f"{STUDIO}/signal",
    "/media": f"{STUDIO}/media",
    "/media/platform": f"{STUDIO}/media",
    "/media/decision-graph": f"{STUDIO}/media",
    "/media/how-it-works": f"{STUDIO}/media",
    "/media/use-cases": f"{STUDIO}/media",
    "/media/pilot": f"{STUDIO}/media",
    "/media/trust": f"{STUDIO}/media",
    "/media/resources": f"{STUDIO}/media",
    "/media/contact": f"{STUDIO}/media",
    "/marketing": f"{STUDIO}/marketing",
    "/marketing/engine": f"{STUDIO}/marketing",
    "/marketing/modules": f"{STUDIO}/marketing",
    "/marketing/simulator": f"{STUDIO}/marketing",
    "/marketing/walkthrough": f"{STUDIO}/marketing",
    "/marketing/governance": f"{STUDIO}/marketing",
    "/marketing/demo": f"{STUDIO}/decision-tree",   # mirrored demo hub keeps the hub's target
    "/marketing/pricing": f"{STUDIO}/marketing",
}
# contextual product links beyond the navigation entry
CONTEXTUAL = {
    "/": f'<a href="{STUDIO}/decision-tree">Decision Studio</a>',
    "/demo": f'<a href="{STUDIO}/decision-tree" class="btn btn-ghost" style="margin-left:12px;">Open the Decision Studio →</a>',
    "/signal": f'<a class="btn btn-ghost" href="{STUDIO}/signal">Open Signal in the Decision Studio</a>',
    "/media": f'<a class="mzm-btn" href="{STUDIO}/media">Open the Decision Studio →</a>',
    "/marketing": f'<a class="button" href="{STUDIO}/marketing">Open the Decision Studio</a>',
}
STUDIO_LINK = re.compile(r'<a[^>]*href="(https://decisionstudio\.mizoki3\.com/[^"#?]*)"[^>]*>', re.I)


class DecisionStudioLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(cls.temp_dir.name))
        cls.app = create_app(runtime=runtime)
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def page(self, path: str) -> str:
        response = self.client.get(path)
        self.assertEqual(200, response.status_code, path)
        body = response.get_data(as_text=True)
        response.close()
        return body

    def test_every_product_route_links_its_studio_page_in_navigation(self) -> None:
        for path, target in NAV_TARGETS.items():
            body = self.page(path)
            with self.subTest(path=path):
                self.assertIn(f'href="{target}"', body, f"{path} must link {target}")
                # Every Studio link on the page points at a real Studio route,
                # the same-site nav is plain (no target=_blank), and labels say what it is.
                links = STUDIO_LINK.findall(body)
                self.assertTrue(links, f"{path}: no Studio link")
                for url in links:
                    self.assertIn(url.removeprefix(STUDIO), ("/", "/decision-tree", "/signal", "/intent", "/media", "/marketing"), url)
                self.assertNotRegex(body, r'href="https://decisionstudio\.mizoki3\.com[^"]*"[^>]*target="_blank"')
                self.assertIn("Decision Studio", body)

    def test_contextual_links_exist_where_the_product_is_explained(self) -> None:
        for path, snippet in CONTEXTUAL.items():
            with self.subTest(path=path):
                self.assertIn(snippet, self.page(path))

    def test_homepage_carries_desktop_nav_footer_and_product_section_entries(self) -> None:
        home = self.page("/")
        self.assertIn(f'<a href="{STUDIO}/" class="hide-m">DECISION STUDIO</a>', home)   # primary nav (desktop)
        self.assertIn(f'<a href="{STUDIO}/">Decision Studio</a>', home)                  # footer Products (mobile-visible)
        self.assertIn('class="product-studio reveal"', home)                              # contextual, mobile-visible
        self.assertIn("No sign-in required", home)
        self.assertIn("illustrative", home.split('class="product-studio reveal"')[1][:400])

    def test_existing_demos_sign_in_and_pilot_links_survive(self) -> None:
        home = self.page("/")
        for kept in ('<a href="/demo" class="hide-m">DEMOS</a>', '<a href="/login">SIGN IN</a>',
                     '<a class="btn primary" href="/media/pilot">EXPLORE A PILOT</a>', 'href="/signal"',
                     'href="/intent"', 'href="/marketing"', 'href="/media"'):
            self.assertIn(kept, home, kept)
        demo = self.page("/demo")
        for kept in ('href="/demo/signal"', 'href="/demo/nexus"', 'href="/walkthrough.html"', 'href="/contact?source=demo-hub"'):
            self.assertIn(kept, demo, kept)

    def test_mobile_navigation_surfaces_carry_the_entry(self) -> None:
        # Pages with the shared hamburger clone their .nav-links into the mobile
        # sheet, so the entry must sit inside .nav-links there.
        for path in ("/demo", "/marketing/engine", "/marketing/modules", "/marketing/governance",
                     "/marketing/simulator", "/marketing/walkthrough"):
            body = self.page(path)
            with self.subTest(path=path):
                self.assertIn('src="/assets/js/nav-mobile.js"', body)
                nav = re.search(r'<ul class="nav-links">(.*?)</ul>', body, re.S)
                self.assertIsNotNone(nav, path)
                self.assertIn("decisionstudio.mizoki3.com", nav.group(1), path)
        # The /media site's nav wraps on phones by its own CSS; the entry sits in that nav.
        media_nav = re.search(r'<div class="mzm-nav-links">(.*?)</div>', self.page("/media"), re.S)
        self.assertIn(f'<a href="{STUDIO}/media">Decision Studio</a>', media_nav.group(1))

    def test_intent_source_links_the_studio_in_nav_and_footer(self) -> None:
        source = (REPO_ROOT / "intent-site" / "src" / "Home.tsx").read_text()
        self.assertEqual(2, source.count(f'<a href="{STUDIO}/intent">Decision Studio</a>'))
        nav = re.search(r'<nav aria-label="Primary navigation">(.*?)</nav>', source, re.S).group(1)
        self.assertIn(f"{STUDIO}/intent", nav)
        footer = re.search(r"<footer>(.*?)</footer>", source, re.S).group(1)
        self.assertIn(f"{STUDIO}/intent", footer)

    def test_presenter_demo_and_legal_pages_stay_studio_free(self) -> None:
        for path in ("/media/demo", "/privacy", "/terms", "/pricing"):
            with self.subTest(path=path):
                self.assertNotIn("decisionstudio.mizoki3.com", self.page(path))

    def test_no_retired_or_wrong_host_spelling(self) -> None:
        for path in NAV_TARGETS:
            body = self.page(path)
            self.assertNotIn("decision.mizoki3.com", body, path)
            self.assertNotIn("mizuki3.com/decision", body, path)
            self.assertNotIn("http://decisionstudio", body, path)


if __name__ == "__main__":
    unittest.main()
