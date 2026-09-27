"""/learn AEO/GEO authority pages + /llms.txt — LEARN_PAGES flag, both directions.
Lane 5 S4 (PROJECT COMPLETION v1.0, 2026-09-02).

* flag literal: the SOURCE default is the string "false" (inspect + ast);
* OFF → 404 on /learn, /learn/, every slug and /llms.txt (the served route
  table answers exactly as before this block existed);
* ON → 200 with a FAQPage JSON-LD <script type="application/ld+json"> per
  page, an index listing every current page, and /llms.txt gaining a Learn
  section derived from the loader; ON with no pages directory → 503
  not_configured, never a healthy stub;
* expiry: every page's expires − last_reviewed ≤ 90 days; a page past its
  expires date is WITHHELD (404) and dropped from the index — both directions;
* content contract per page: direct answer ≤ 60 words, ≥ 5 inline-sourced
  statistics, FAQ ≥ 3 mirrored 1:1 by the JSON-LD, status label repeated,
  no email address anywhere, supported markdown subset only, canon rule V13
  (strict) clean;
* no egress: every rendered page is self-contained (the test_no_egress helper
  is reused so the two sweeps cannot disagree about what "egress" means);
* llms.txt hygiene: every path it links resolves in the live route table,
  and no /learn/ link is hand-listed in the static file.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from app import create_app
from mizoki_runtime import create_runtime, learn_pages, site_flags
from tests.test_no_egress import egress_hosts

SITE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_ROOT.parent
PAGES_DIR = REPO_ROOT / "docs" / "marketing" / "aeo"
EXPECTED_SLUGS = (
    "agent-originated-conversions",
    "brier-auc-promotion-gates",
    "decision-control-plane",
    "del-score",
    "ghost-bids-and-holdouts",
    "governed-ad-autonomy",
    "incrementality-vs-platform-roas",
    "validation-passport",
)
JSONLD_TAG = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LABEL_IN_DIRECT_ANSWER = re.compile(r"\*\*\[(LIVE|PARTIAL|IN BUILD|PROPOSED|ROADMAP)\]\*\*")
# mizoki_canon.py (rule V13 strict on docs/marketing/**) — loaded by path like
# content_qa.py does; a missing module is a hard failure, never a skip.
_CANON_PATH = REPO_ROOT / "scripts" / "mizoki_canon.py"


def _load_canon():
    if not _CANON_PATH.is_file():
        raise AssertionError(f"{_CANON_PATH} missing — the V13 stat-attribution rule cannot run")
    spec = importlib.util.spec_from_file_location("mizoki_canon", _CANON_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("mizoki_canon", module)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _pages() -> list[learn_pages.Page]:
    return learn_pages.load_pages(PAGES_DIR)


class _Today:
    """Patch learn_pages.date so is_overdue() sees a chosen 'today'."""

    def __init__(self, today: date) -> None:
        self.today = today

    def __enter__(self):
        fixed = self.today

        class FakeDate(date):
            @classmethod
            def today(cls):
                return fixed

        self._patch = mock.patch.object(learn_pages, "date", FakeDate)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()


# ------------------------------------------------------------- flag literal

class TestFlagLiteral(unittest.TestCase):
    def test_source_literal_default_is_false(self) -> None:
        src = inspect.getsource(site_flags)
        self.assertIn('os.environ.get(LEARN_PAGES_ENV, "false")', src)
        self.assertEqual(site_flags.LEARN_PAGES_ENV, "LEARN_PAGES")

    def test_ast_default_for_learn_pages_is_the_string_false(self) -> None:
        tree = ast.parse(inspect.getsource(site_flags))
        seen = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get" and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "environ" and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "LEARN_PAGES_ENV"):
                seen.append(node.args[1])
        self.assertEqual(1, len(seen), "exactly one LEARN_PAGES read")
        self.assertIsInstance(seen[0], ast.Constant)
        self.assertEqual("false", seen[0].value)

    def test_unset_is_off(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "LEARN_PAGES"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(site_flags.learn_pages_enabled())
            self.assertFalse(site_flags.snapshot()["learn_pages"])


# --------------------------------------------------------------- the routes

class _AppCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=SITE_ROOT, data_dir=Path(self.temp_dir.name))
        self.app = create_app(runtime=runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.env = mock.patch.dict(os.environ, {"LEARN_PAGES": "false", "LEARN_PAGES_DIR": str(PAGES_DIR)})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.temp_dir.cleanup()

    def on(self) -> None:
        os.environ["LEARN_PAGES"] = "true"


class TestFlagOff(_AppCase):
    def test_every_learn_path_is_404_when_off(self) -> None:
        for path in ("/learn", "/learn/", "/llms.txt") + tuple(f"/learn/{s}" for s in EXPECTED_SLUGS):
            response = self.client.get(path)
            self.assertEqual(404, response.status_code, path)
            self.assertNotIn("application/ld+json", response.get_data(as_text=True))
            response.close()

    def test_sitemap_lists_no_learn_url_when_off(self) -> None:
        # A sitemap URL that answers 404 is a contradictory signal (the same
        # reasoning that keeps /marketing and /media/demo out of it).
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertNotIn("/learn", sitemap)

    def test_static_catch_all_does_not_serve_llms_txt_when_off(self) -> None:
        # The explicit /llms.txt rule wins the match and aborts; the top-level
        # static catch-all (which serves *.txt) is never consulted.
        self.assertTrue((SITE_ROOT / "llms.txt").is_file())
        self.assertEqual(404, self.client.get("/llms.txt").status_code)

    def test_routes_are_registered_in_the_live_table(self) -> None:
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn("/learn", rules)
        self.assertIn("/learn/<slug>", rules)
        self.assertIn("/llms.txt", rules)


class TestFlagOn(_AppCase):
    def test_every_page_serves_with_jsonld(self) -> None:
        self.on()
        for slug in EXPECTED_SLUGS:
            response = self.client.get(f"/learn/{slug}")
            self.assertEqual(200, response.status_code, slug)
            self.assertEqual("text/html", response.mimetype)
            html = response.get_data(as_text=True)
            blocks = JSONLD_TAG.findall(html)
            self.assertEqual(1, len(blocks), f"{slug}: exactly one JSON-LD script")
            data = json.loads(blocks[0].replace("<\\/", "</"))
            self.assertEqual("FAQPage", data["@type"])
            self.assertGreaterEqual(len(data["mainEntity"]), learn_pages.MIN_FAQ_ITEMS)
            self.assertNotIn("</", blocks[0], "JSON-LD payload must escape </ so it cannot close the script")
            self.assertIn(f'<link rel="canonical" href="https://mizoki3.com/learn/{slug}">', html)
            self.assertIn('<h2 id="direct-answer">', html)
            self.assertNotIn("```", html, "no raw fence leaked into the rendered page")
            response.close()

    def test_sitemap_lists_the_index_and_every_current_page_when_on(self) -> None:
        # S4-1 (2026-09-15): the 9 /learn URLs (index + 8 pages), derived from
        # the loader, each with lastmod = last_reviewed; withheld pages absent.
        self.on()
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("<loc>https://mizoki3.com/learn/</loc>", sitemap)
        for slug in EXPECTED_SLUGS:
            self.assertIn(f"<loc>https://mizoki3.com/learn/{slug}</loc>", sitemap, slug)
        self.assertEqual(1 + len(EXPECTED_SLUGS), sitemap.count("mizoki3.com/learn"))
        for page in learn_pages.load_pages(PAGES_DIR):
            self.assertIn(
                f"<loc>https://mizoki3.com/learn/{page.slug}</loc>\n    <lastmod>{page.last_reviewed.isoformat()}</lastmod>",
                sitemap, page.slug)

    def test_index_lists_every_current_page(self) -> None:
        self.on()
        response = self.client.get("/learn/")
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        for slug in EXPECTED_SLUGS:
            self.assertIn(f'href="/learn/{slug}"', html)
        self.assertEqual(200, self.client.get("/learn").status_code)

    def test_unknown_and_malformed_slugs_are_404(self) -> None:
        self.on()
        for path in ("/learn/nope", "/learn/README", "/learn/readme", "/learn/..%2fapp.py", "/learn/a_b"):
            self.assertEqual(404, self.client.get(path).status_code, path)

    def test_flag_on_without_a_pages_directory_is_503_not_configured(self) -> None:
        self.on()
        with mock.patch.dict(os.environ, {"LEARN_PAGES_DIR": str(Path(self.temp_dir.name) / "absent")}):
            for path in ("/learn/", f"/learn/{EXPECTED_SLUGS[0]}"):
                response = self.client.get(path)
                self.assertEqual(503, response.status_code, path)
                self.assertEqual({"status": "not_configured", "flag": "LEARN_PAGES"}, response.get_json())
            # llms.txt is hygiene: the static part still serves, with no Learn section.
            body = self.client.get("/llms.txt").get_data(as_text=True)
            self.assertNotIn("## Learn", body)
            self.assertNotIn("/learn/", body)

    def test_rendered_pages_have_no_egress(self) -> None:
        self.on()
        for path in ("/learn/",) + tuple(f"/learn/{s}" for s in EXPECTED_SLUGS):
            html = self.client.get(path).get_data(as_text=True)
            self.assertEqual(set(), egress_hosts(html), f"{path}: third-party egress")
            self.assertNotIn("<script src", html)
            self.assertNotIn("<link rel=\"stylesheet\"", html)

    def test_rendered_pages_carry_no_email_address(self) -> None:
        self.on()
        for path in ("/learn/", "/llms.txt") + tuple(f"/learn/{s}" for s in EXPECTED_SLUGS):
            self.assertIsNone(EMAIL.search(self.client.get(path).get_data(as_text=True)), path)


# ------------------------------------------------------------------ expiry

class TestExpiry(_AppCase):
    def test_every_page_review_window_is_at_most_90_days(self) -> None:
        for page in _pages():
            self.assertGreater(page.expires, page.last_reviewed, page.slug)
            self.assertLessEqual((page.expires - page.last_reviewed).days, learn_pages.MAX_REVIEW_DAYS, page.slug)

    def test_is_overdue_both_directions(self) -> None:
        page = _pages()[0]
        self.assertFalse(learn_pages.is_overdue(page, today=page.expires))
        self.assertTrue(learn_pages.is_overdue(page, today=page.expires + timedelta(days=1)))

    def test_overdue_page_is_withheld_and_dropped_from_the_index(self) -> None:
        self.on()
        page = _pages()[0]
        with _Today(page.last_reviewed):
            self.assertEqual(200, self.client.get(f"/learn/{page.slug}").status_code)
            self.assertIn(f'href="/learn/{page.slug}"', self.client.get("/learn/").get_data(as_text=True))
            self.assertIn(f"/learn/{page.slug}", self.client.get("/llms.txt").get_data(as_text=True))
        with _Today(page.expires + timedelta(days=1)):
            self.assertEqual(404, self.client.get(f"/learn/{page.slug}").status_code)
            self.assertNotIn(f'href="/learn/{page.slug}"', self.client.get("/learn/").get_data(as_text=True))
            self.assertNotIn(f"/learn/{page.slug}", self.client.get("/llms.txt").get_data(as_text=True))

    def test_loader_refuses_a_window_longer_than_90_days(self) -> None:
        src = (PAGES_DIR / f"{EXPECTED_SLUGS[0]}.md").read_text(encoding="utf-8")
        bad = re.sub(r"^expires: .*$", "expires: 2027-06-01", src, count=1, flags=re.M)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe-page.md"
            path.write_text(bad, encoding="utf-8")
            with self.assertRaises(learn_pages.PageError):
                learn_pages.load_page(path)


# --------------------------------------------------------- content contract

class TestContentContract(unittest.TestCase):
    def setUp(self) -> None:
        self.pages = _pages()

    def test_exactly_the_expected_pages_exist(self) -> None:
        self.assertEqual(sorted(EXPECTED_SLUGS), [p.slug for p in self.pages])

    # The review date is pinned PER PAGE so a bump is a deliberate, dated edit:
    # 2026-09-15 (S4-3 re-fetch, branch claude/aeo-stat-fix-sitemap-0915) moved
    # the five pages whose copy changed (one Gartner citation corrected, the
    # NRF returns figure reworded as the forecast it is); the other three were
    # verified unchanged and keep their 2026-09-02 review date.
    REVIEWED_2026_09_15 = frozenset({
        "brier-auc-promotion-gates", "del-score", "ghost-bids-and-holdouts",
        "incrementality-vs-platform-roas", "validation-passport",
    })

    def test_front_matter_contract(self) -> None:
        for p in self.pages:
            self.assertEqual("MIZ OKI product", p.owner, p.slug)
            expected = date(2026, 9, 15) if p.slug in self.REVIEWED_2026_09_15 else date(2026, 9, 2)
            self.assertEqual(expected, p.last_reviewed, p.slug)
            self.assertIn(p.status_label, learn_pages.STATUS_LABELS, p.slug)
            self.assertTrue(p.title.strip(), p.slug)
            self.assertTrue(p.description.strip(), p.slug)

    def test_direct_answer_is_at_most_60_words(self) -> None:
        for p in self.pages:
            words = learn_pages.word_count(p.direct_answer)
            self.assertGreater(words, 0, p.slug)
            self.assertLessEqual(words, learn_pages.MAX_DIRECT_ANSWER_WORDS, f"{p.slug}: {words} words")

    def test_status_label_is_repeated_in_the_direct_answer(self) -> None:
        for p in self.pages:
            m = LABEL_IN_DIRECT_ANSWER.search(p.direct_answer)
            self.assertIsNotNone(m, f"{p.slug}: direct answer must state its capability label")
            self.assertEqual(p.status_label, m.group(1), p.slug)

    def test_every_page_carries_at_least_five_sourced_statistics(self) -> None:
        for p in self.pages:
            cites = learn_pages.sourced_stat_citations(p.body_md)
            self.assertGreaterEqual(len(cites), learn_pages.MIN_SOURCED_STATS, f"{p.slug}: {cites}")
            for source, _month, year in cites:
                self.assertRegex(source, r"^[A-Z]", p.slug)
                self.assertGreaterEqual(int(year), 1950, p.slug)

    def test_sourced_stat_regex_both_directions(self) -> None:
        ok = "19.3% of online sales were returned in 2025 (NRF / Happy Returns, Oct 2025)."
        bad = "19.3% of online sales were returned in 2025 (industry data, 2025)."
        self.assertEqual([("NRF / Happy Returns", "Oct", "2025")], learn_pages.sourced_stat_citations(ok))
        self.assertEqual([], learn_pages.sourced_stat_citations(bad))

    def test_no_email_addresses_on_any_page(self) -> None:
        for path in PAGES_DIR.glob("*.md"):
            self.assertIsNone(EMAIL.search(path.read_text(encoding="utf-8")), path.name)

    def test_faq_jsonld_mirrors_the_faq_section(self) -> None:
        for p in self.pages:
            faq = learn_pages.extract_faq(p.body_md)
            self.assertGreaterEqual(len(faq), learn_pages.MIN_FAQ_ITEMS, p.slug)
            self.assertIsNotNone(p.faq_jsonld, p.slug)
            self.assertEqual("https://schema.org", p.faq_jsonld["@context"], p.slug)
            entities = p.faq_jsonld["mainEntity"]
            self.assertEqual([q for q, _ in faq], [e["name"] for e in entities], p.slug)
            self.assertEqual([a for _, a in faq], [e["acceptedAnswer"]["text"] for e in entities], p.slug)
            for e in entities:
                self.assertEqual("Question", e["@type"])
                self.assertEqual("Answer", e["acceptedAnswer"]["@type"])

    def test_pages_use_only_the_supported_markdown_subset(self) -> None:
        for p in self.pages:
            for n, line in enumerate(p.body_md.splitlines(), 1):
                self.assertFalse(line.lstrip().startswith("|"), f"{p.slug}:{n}: tables are not in the subset")
                self.assertFalse(line.lstrip().startswith("!["), f"{p.slug}:{n}: images are not in the subset")
                self.assertNotIn("<", line, f"{p.slug}:{n}: raw HTML is never passed through")
            self.assertTrue(p.body_md.lstrip().startswith("## Direct answer"), p.slug)

    def test_pages_pass_the_canon_stat_attribution_rule(self) -> None:
        canon = _load_canon()
        findings = []
        for path in sorted(PAGES_DIR.glob("*.md")):
            rel = str(path.relative_to(REPO_ROOT))
            findings.extend(f"{rel}:{f.line_no} {f.rule_id} {f.title}" for f in canon.check_file(str(path)))
        self.assertEqual([], findings)
        # the rule really is armed on this path shape (both directions)
        seeded = canon.check_text("Returns hit 19.3% of online sales in 2025.\n", path="docs/marketing/aeo/probe.md")
        self.assertTrue(any(f.rule_id == "V13" for f in seeded), "V13 must fire on an unsourced statistic here")

    def test_canon_facts_hold_on_every_page(self) -> None:
        for path in PAGES_DIR.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\bSRDAL\b", path.name)
            self.assertNotRegex(text, r"(?i)neo4j|cypher|tigergraph", path.name)
            self.assertNotRegex(text, r"\b(32|35|37|39)[- ]cells?\b", path.name)
            self.assertNotRegex(text, r"(?i)guarantee", path.name)
            self.assertNotRegex(text, r"\b(0\.66|4\.95|12\.03)\b", path.name)
        ghost = (PAGES_DIR / "ghost-bids-and-holdouts.md").read_text(encoding="utf-8")
        self.assertIn("status_label: PROPOSED", ghost)
        agent = (PAGES_DIR / "agent-originated-conversions.md").read_text(encoding="utf-8")
        self.assertIn("status_label: IN BUILD", agent)


# --------------------------------------------------------------- renderer

class TestRenderer(unittest.TestCase):
    def test_subset_renders_and_escapes(self) -> None:
        md = ("## Head *one*\n\nPara with **bold**, `code`, [site](/learn/) and [ext](https://example.com/x).\n\n"
              "- a\n- b\n\n1. first\n2. second\n\n```json\n{\"k\": 1}\n```\n\n> quoted\n\n"
              "<script>alert(1)</script> and [bad](javascript:alert(1))\n")
        html = learn_pages.render_markdown(md)
        self.assertIn('<h2 id="head-one">Head <em>one</em></h2>', html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn('<a href="/learn/">site</a>', html)
        self.assertIn('<a href="https://example.com/x">ext</a>', html)
        self.assertIn("<ul>\n<li>a</li>\n<li>b</li>\n</ul>", html)
        self.assertIn("<ol>\n<li>first</li>\n<li>second</li>\n</ol>", html)
        self.assertIn('<pre><code class="language-json">{&quot;k&quot;: 1}</code></pre>'.replace("&quot;", '"'), html)
        self.assertIn("<blockquote><p>quoted</p></blockquote>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn("[bad](javascript:alert(1))", html)

    def test_front_matter_parser_both_directions(self) -> None:
        fields, body = learn_pages.parse_front_matter('---\ntitle: "T"\nowner: MIZ OKI product\n---\nbody\n')
        self.assertEqual({"title": "T", "owner": "MIZ OKI product"}, fields)
        self.assertEqual("body\n", body)
        with self.assertRaises(learn_pages.PageError):
            learn_pages.parse_front_matter("no front matter\n")
        with self.assertRaises(learn_pages.PageError):
            learn_pages.parse_front_matter("---\ntitle: a\ntitle: b\n---\n")

    def test_loader_refuses_an_email_owner_and_a_bad_label(self) -> None:
        src = (PAGES_DIR / f"{EXPECTED_SLUGS[0]}.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe-page.md"
            path.write_text(re.sub(r"^owner: .*$", "owner: someone@example.com", src, count=1, flags=re.M))
            with self.assertRaises(learn_pages.PageError):
                learn_pages.load_page(path)
            path.write_text(re.sub(r"^status_label: .*$", "status_label: DONE", src, count=1, flags=re.M))
            with self.assertRaises(learn_pages.PageError):
                learn_pages.load_page(path)


# ---------------------------------------------------------------- llms.txt

class TestLlmsTxt(_AppCase):
    def _resolves(self, path: str) -> bool:
        adapter = self.app.url_map.bind("mizoki3.com")
        try:
            adapter.match(path, method="GET")
            return True
        except Exception:  # NotFound / MethodNotAllowed / RequestRedirect
            return False

    def test_static_file_lists_only_registered_routes_and_no_learn_links(self) -> None:
        text = (SITE_ROOT / "llms.txt").read_text(encoding="utf-8")
        paths = learn_pages.llms_txt_paths(text, "https://mizoki3.com")
        self.assertTrue(paths, "llms.txt links nothing — the check would be vacuous")
        for path in paths:
            self.assertFalse(path.startswith("/learn"), f"{path}: /learn links are never hand-listed")
            self.assertTrue(self._resolves(path) or self._resolves(path.rstrip("/")), f"{path}: not a served route")

    def test_served_body_when_on_adds_the_learn_section_from_the_loader(self) -> None:
        self.on()
        response = self.client.get("/llms.txt")
        self.assertEqual(200, response.status_code)
        self.assertEqual("text/plain", response.mimetype)
        body = response.get_data(as_text=True)
        self.assertIn("## Learn", body)
        for slug in EXPECTED_SLUGS:
            self.assertIn(f"https://mizoki3.com/learn/{slug}", body)
        for path in learn_pages.llms_txt_paths(body, "https://mizoki3.com"):
            self.assertTrue(self._resolves(path) or self._resolves(path.rstrip("/")), f"{path}: not a served route")

    def test_path_extractor_both_directions(self) -> None:
        text = "- [a](https://mizoki3.com/signal): x\n- [b](https://other.example/nope)\n"
        self.assertEqual(["/signal"], learn_pages.llms_txt_paths(text, "https://mizoki3.com"))


if __name__ == "__main__":
    unittest.main()
