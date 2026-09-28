"""The Journal is the one public name for /blog (owner direction 2026-09-25).

"Keep the journal ... just use the Journal and do away with blog": every link to
the /blog index, every page title and both feed titles say "Journal", and no
surface calls it the Blog. The addresses stay /blog/... (a URL is not a label),
and schema.org's "BlogPosting" type is vocabulary, not copy.

Scope is derived, never hand-listed (rule 01):
  * served: every GET route without arguments in app.url_map, every page of the
    any(...) routes, and every article in blog/posts.json;
  * source: every HTML file in the site tree, which also covers what the
    file-serving routes (/<path:filename> and the like) can return and the
    legacy pages that now 301.
Excluded, with reasons: site_docs*/ and docs/ are rendered documents, not site
navigation; /learn/<slug> is rendered at deploy time from
docs/marketing/aeo/*.md, outside this tree; /api/demo/* answers JSON.
"""
import html
import json
import re
import unittest

from app import BASE_DIR, app

JOURNAL_INDEX = {
    "/blog", "/blog/", "/blog/index.html", "/blogs", "/blogs/", "/blogs.html",
    "https://mizoki3.com/blog", "https://mizoki3.com/blog/",
}
BLOG_WORD = re.compile(r"\bblogs?\b", re.I)
ANCHOR = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)
HREF = re.compile(r'\bhref="([^"]*)"')
TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
FEED_LINK_TITLE = re.compile(r'<link\b(?=[^>]*\brel="alternate")[^>]*\btitle="([^"]*)"', re.I)
SHARE_TITLE = re.compile(
    r'<meta\b(?=[^>]*\b(?:property="og:(?:title|site_name)"|name="twitter:title"))[^>]*\bcontent="([^"]*)"',
    re.I,
)
EXCLUDED_TREES = {"site_docs", "site_docs_internal", "docs", "archive", "node_modules"}


def _text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def journal_findings(page, *, in_journal=False):
    """Every place a page names the Journal as the Blog.

    in_journal: the page lives under /blog/, where a relative "index.html" or
    "./" link is the Journal index too.
    """
    findings = []
    for attrs, inner in ANCHOR.findall(page):
        href = HREF.search(attrs)
        if not href:
            continue
        target = href.group(1)
        if target in JOURNAL_INDEX or (in_journal and target in ("index.html", "./")):
            if BLOG_WORD.search(_text(inner)):
                findings.append(f"link to the Journal reads {_text(inner)!r}")
    for pattern, where in ((TITLE, "<title>"), (FEED_LINK_TITLE, "feed link title"),
                           (SHARE_TITLE, "share title")):
        for value in pattern.findall(page):
            if BLOG_WORD.search(_text(value)):
                findings.append(f"{where} {_text(value)!r}")
    if "MIZ OKI 3.5 Blog" in html.unescape(page):
        findings.append("names the 'MIZ OKI 3.5 Blog'")
    return findings


def served_pages():
    pages = set()
    for rule in app.url_map.iter_rules():
        if "GET" not in rule.methods:
            continue
        if not rule.arguments:
            pages.add(rule.rule)
            continue
        choice = re.fullmatch(r"(.*)<any\(([^)]*)\):\w+>(.*)", rule.rule)
        if choice:
            for item in choice.group(2).split(","):
                pages.add(choice.group(1) + item.strip().strip("'\"") + choice.group(3))
    catalog = json.loads((BASE_DIR / "blog/posts.json").read_text(encoding="utf-8"))["posts"]
    pages.update(f"/blog/{p['slug']}" for p in catalog)
    return sorted(pages)


class JournalNameTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_finder_fires_in_both_directions(self):
        must_fire = [
            ('<a href="/blog/">Blog</a>', False),
            ('<a href="/blog" class="active">BLOG</a>', False),
            ('<a href="/blogs.html">our blog</a>', False),
            ('<a href="index.html">Blog</a> / Architecture', True),
            ("<title>Blog — MIZ OKI 3.5</title>", False),
            ("<title>Unlocking Meta's Ad Algorithm | MIZ OKI 3.5 Blog</title>", True),
            ('<link rel="alternate" type="application/rss+xml" title="MIZ OKI 3.5 Blog (RSS)" href="/blog/feed.xml">', False),
            ('<meta property="og:title" content="MIZ OKI 3.5 Blog">', False),
            ('<meta name="twitter:title" content="MIZ OKI 3.5 Blog">', False),
            ("<p>Subscribe to the MIZ OKI 3.5 Blog.</p>", False),
        ]
        for page, in_journal in must_fire:
            with self.subTest(page=page):
                self.assertTrue(journal_findings(page, in_journal=in_journal), page)
        stays_legal = [
            ('<a href="/blog/">Journal</a>', False),
            ('<a href="/blog/" class="hide-m">JOURNAL</a>', False),
            ('<a href="index.html">Journal</a> / Architecture', True),
            ('<a href="index.html">Blog</a>', False),  # outside /blog/ that is the homepage
            ('<a href="/blog/doorman-problem">The doorman problem</a>', False),
            ('<a href="/blog#the-next-dollar">The Next Dollar</a>', False),
            ('<script type="application/ld+json">{"@type": "BlogPosting"}</script>', True),
            ('<main class="blog-container"><img src="/assets/img/blog/og.png" alt="chart"></main>', True),
            ('<link rel="alternate icon" href="/assets/img/favicon.ico">', False),
            ('<link rel="alternate" type="application/rss+xml" title="MIZ OKI 3.5 Journal" href="/blog/feed.xml">', True),
            ("<title>Journal — MIZ OKI 3.5</title>", False),
        ]
        for page, in_journal in stays_legal:
            with self.subTest(page=page):
                self.assertEqual(journal_findings(page, in_journal=in_journal), [], page)

    def test_every_served_page_names_the_journal(self):
        checked = 0
        for path in served_pages():
            with self.client.get(path) as response:
                if response.status_code != 200 or not response.mimetype == "text/html":
                    continue
                body = response.get_data(as_text=True)
            checked += 1
            with self.subTest(path=path):
                self.assertEqual(journal_findings(body, in_journal=path.startswith("/blog/")), [])
        # A scope that silently shrinks defends nothing: the Journal's 13 pages
        # plus the site's own pages are well over this floor.
        self.assertGreater(checked, 60)

    def test_every_source_page_names_the_journal(self):
        checked = 0
        for page in sorted(BASE_DIR.rglob("*.html")):
            rel = page.relative_to(BASE_DIR)
            if EXCLUDED_TREES & set(rel.parts):
                continue
            checked += 1
            with self.subTest(page=str(rel)):
                body = page.read_text(encoding="utf-8", errors="replace")
                self.assertEqual(journal_findings(body, in_journal=rel.parts[0] == "blog"), [])
        self.assertGreater(checked, 60)

    def test_feeds_are_the_journal(self):
        with self.client.get("/blog/feed.xml") as response:
            channel = re.search(r"<channel>\s*<title>(.*?)</title>", response.get_data(as_text=True))
        self.assertEqual(channel.group(1), "MIZ OKI 3.5 Journal")
        with self.client.get("/blog/feed.json") as response:
            self.assertEqual(response.get_json()["title"], "MIZ OKI 3.5 Journal")
        crawler_index = (BASE_DIR / "llms.txt").read_text(encoding="utf-8")
        self.assertIn("- [Journal](https://mizoki3.com/blog):", crawler_index)
        self.assertIsNone(BLOG_WORD.search(re.sub(r"https?://\S+", "", crawler_index)))


if __name__ == "__main__":
    unittest.main()
