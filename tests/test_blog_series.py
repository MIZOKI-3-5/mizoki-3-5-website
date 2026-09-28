"""Publication contracts: discoverable articles, stable URLs, and share metadata."""
import json
import re
import unittest
from html import unescape
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

from app import BASE_DIR, app


class BlogSeriesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.posts = json.loads((BASE_DIR / "blog/posts.json").read_text())["posts"]
        self.letters = sorted(
            (p for p in self.posts if p.get("series") == "The Next Dollar"),
            key=lambda p: p["series_order"],
        )

    def text(self, path):
        with self.client.get(path) as response:
            self.assertEqual(response.status_code, 200, path)
            return response.get_data(as_text=True)

    def test_all_nine_letters_are_complete_and_discoverable(self):
        self.assertEqual([p["series_order"] for p in self.letters], list(range(1, 10)))
        self.assertEqual(len({p["slug"] for p in self.posts}), len(self.posts))
        index = self.text("/blog")
        for p in self.letters:
            with self.subTest(slug=p["slug"]):
                path = f"/blog/{p['slug']}"
                self.assertIn(f'href="{path}"', index)
                page = self.text(path)
                self.assertEqual(page.count('<h1 '), 1)
                self.assertIn(p["title"], unescape(page))
                self.assertIn("Boris Mizhen", page)
                content = page.split('<div class="article-content">', 1)[1].split('</div>', 1)[0]
                self.assertGreater(len(re.sub('<[^>]+>', '', content).split()), 300)
                self.assertNotIn("publication_status", page)
                for sibling in self.letters:
                    self.assertIn(f'href="/blog/{sibling["slug"]}"', page)

    def test_share_metadata_and_canonical_aliases(self):
        for p in self.letters:
            with self.subTest(slug=p["slug"]):
                path = f"/blog/{p['slug']}"
                url = "https://mizoki3.com" + path
                page = self.text(path)
                self.assertIn(f'<link rel="canonical" href="{url}">', page)
                self.assertIn(f'<meta property="og:url" content="{url}">', page)
                schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page).group(1))
                self.assertEqual(schema["headline"], p["title"])
                self.assertEqual(schema["datePublished"], p["published"])
                self.assertEqual(schema["dateModified"], p["updated"])
                share = unescape(re.search(r'href="(https://www.linkedin.com/sharing/[^\"]+)"', page).group(1))
                self.assertEqual(parse_qs(urlparse(share).query)["url"], [url])
                for suffix in ("/", ".html"):
                    with self.client.get(path + suffix) as response:
                        self.assertEqual(response.status_code, 301)
                        self.assertEqual(response.location, path)
        # Doorman keeps its original publication date; its revision date is the
        # day the revision first went live (2026-09-24), not the merge date of
        # PR #1125 (2026-09-21) — the playbook records the actual update date.
        doorman = next(p for p in self.letters if p["slug"] == "doorman-problem")
        self.assertEqual(doorman["published"], "2026-08-03")
        self.assertEqual(doorman["updated"], "2026-09-24")

    def test_feeds_and_sitemap_resolve_every_published_article(self):
        sitemap = ElementTree.fromstring(self.text("/sitemap.xml"))
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        entries = {row.findtext("s:loc", namespaces=ns): row.findtext("s:lastmod", namespaces=ns)
                   for row in sitemap.findall("s:url", ns)}
        rss = ElementTree.fromstring(self.text("/blog/feed.xml"))
        rss_urls = {row.findtext("link") for row in rss.findall("channel/item")}
        feed = json.loads(self.text("/blog/feed.json"))
        json_urls = {row["url"] for row in feed["items"]}
        for p in self.posts:
            path = f"/blog/{p['slug']}"
            url = "https://mizoki3.com" + path
            with self.subTest(slug=p["slug"]):
                self.assertEqual(entries[url], p["updated"])
                self.assertIn(url, rss_urls)
                self.assertIn(url, json_urls)
                self.text(path)
        self.assertEqual(entries["https://mizoki3.com/blog"], "2026-09-24")

    def test_page_metadata_and_dates_match_the_manifest(self):
        for p in self.letters:
            with self.subTest(slug=p["slug"]):
                page = self.text(f"/blog/{p['slug']}")
                head = page.split("</head>", 1)[0]
                for pattern in (r'<meta name="description" content="([^"]*)">',
                                r'<meta property="og:description" content="([^"]*)">',
                                r'<meta name="twitter:description" content="([^"]*)">'):
                    self.assertEqual(unescape(re.search(pattern, head).group(1)), p["summary"])
                schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page).group(1))
                self.assertEqual(schema["description"], p["summary"])
                self.assertIn(f'<meta property="article:published_time" content="{p["published"]}T00:00:00Z">', head)
                self.assertIn(f'<meta property="article:modified_time" content="{p["updated"]}T00:00:00Z">', head)
                self.assertIn(f'<time datetime="{p["updated"]}">', page)
                if p["published"] != p["updated"]:
                    self.assertIn(f'<time datetime="{p["published"]}">', page)

    def test_decision_graph_letter_summary_stays_qualified(self):
        # The Growth Decision Graph is PARTIAL/observe-only and cross-domain
        # learning is Roadmap (README status table; /media labels it Roadmap).
        # The letter's summary is the design aim, never a present-tense capability.
        qualified = ("MIZ OKI's Decision Graph design aims to preserve why choices were made, "
                     "who approved them and what followed. Cross-domain learning remains on the roadmap.")
        retired = "Decision Graph preserves why"
        letter = next(p for p in self.letters if p["slug"] == "your-business-should-remember-why")
        self.assertEqual(letter["summary"], qualified)
        rss = ElementTree.fromstring(self.text("/blog/feed.xml"))
        rss_summary = {row.findtext("link"): row.findtext("description") for row in rss.findall("channel/item")}
        feed = {row["url"]: row for row in json.loads(self.text("/blog/feed.json"))["items"]}
        url = "https://mizoki3.com/blog/your-business-should-remember-why"
        self.assertEqual(rss_summary[url], qualified)
        self.assertEqual(feed[url]["summary"], qualified)
        self.assertEqual(feed[url]["content_text"], qualified)
        for path in ("/blog", "/blog/your-business-should-remember-why", "/blog/feed.xml",
                     "/blog/feed.json", "/blog/posts.json"):
            with self.subTest(path=path):
                body = unescape(self.text(path))
                self.assertIn(qualified, body)
                self.assertNotIn(retired, body)

    def test_journal_lists_every_article_in_its_section(self):
        # Owner direction 2026-09-25: /blog is the Journal. It lists every
        # article, past and future: the founder letters (The Next Dollar) and
        # the existing research articles, which stay. posts.json is the record
        # of which section each article belongs to. Its keys and the /blog#journal
        # fragment are public addresses published by #1164, so they are kept
        # (AGENTS.md 6.6: a contract migrates, it is never renamed); only the
        # labels a reader sees changed.
        sections = {p["slug"]: p.get("section") for p in self.posts}
        self.assertEqual(set(sections.values()), {"journal", "research"})
        self.assertEqual({s for s, sec in sections.items() if sec == "journal"},
                         {p["slug"] for p in self.letters})
        index = self.text("/blog")
        self.assertIn("<title>Journal — MIZ OKI 3.5</title>", index)
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", index, re.S).group(1)
        self.assertEqual(re.sub(r"<[^>]+>", " ", h1).split(), ["MIZ", "OKI", "3.5", "Journal"])
        self.assertIn('<a href="/blog" class="active">Journal</a>', index)
        self.assertEqual(index.count('<section id="the-next-dollar"'), 1)
        self.assertEqual(index.count('id="journal"'), 1)
        self.assertRegex(index, r'<span id="journal" class="anchor-alias" aria-hidden="true"></span>\s*'
                                r'<section id="the-next-dollar"')
        letters = index.split('<section id="the-next-dollar"', 1)[1].split('<h2 class="research-title">', 1)[0]
        research = index.split('<h2 class="research-title">', 1)[1].split("</main>", 1)[0]

        def linked(html):
            return list(dict.fromkeys(re.findall(r'href="/blog/([a-z0-9-]+)"', html)))

        self.assertEqual(linked(letters), [p["slug"] for p in self.letters])
        self.assertEqual(sorted(linked(research)),
                         sorted(s for s, sec in sections.items() if sec == "research"))

    def test_every_article_leads_back_to_the_journal(self):
        for p in self.letters:
            with self.subTest(slug=p["slug"]):
                page = self.text(f"/blog/{p['slug']}")
                head, body = page.split('<div class="breadcrumb">', 1)
                crumbs = re.findall(r'<a href="([^"]+)">([^<]+)</a>', body.split("</div>", 1)[0])
                self.assertEqual(crumbs, [("/blog", "Journal"), ("/blog#the-next-dollar", "The Next Dollar")])
                self.assertIn('<a href="/blog">Journal</a>', head)
                self.assertIn('title="MIZ OKI 3.5 Journal"', head)
        # The research articles keep their own layouts; their menu and
        # breadcrumb name the Journal too (two use a relative index.html link,
        # which 301s to /blog).
        for p in self.posts:
            if p["section"] == "research":
                with self.subTest(slug=p["slug"]):
                    page = self.text(f"/blog/{p['slug']}")
                    self.assertEqual(len(re.findall(r'<a href="(?:/blog|index\.html)">Journal</a>', page)), 2)

    def test_unknown_article_is_not_published(self):
        for path in ("/blog/a-post-that-does-not-exist", "/blog/a-post-that-does-not-exist.html"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
