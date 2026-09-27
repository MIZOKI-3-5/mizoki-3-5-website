"""No unattested compliance attestation in text the site serves or could re-serve.

CV-7 (close-out verdict 2026-09-25) found six legacy pages that still carried
attestation copy ("SOC 2 Type II Certified • GDPR Compliant • HIPAA Ready",
"SOC2 Type II compliant cloud", a "HIPAA Compliant" stat) and called them
unserved, because app.py's legacy_marketing_page() 301-redirects their routes.
Measured the same day, that was half true. The site runtime's SiteCorpus loads
security.html, resources.html and investor.html as retrieval documents, and
the graphrag.query tool returns text snippets from them through /api/mcp/call.
Production leaves that path open: deploy-homepage.yml sets
MIZOKI_REQUIRE_AUTH_FOR_APIS=false, and an anonymous GET of /api/mcp/tools
lists the tool. Locally, a query for "SOC 2" returned "managed entirely via
our SOC2 Type II compliant cloud". content_qa's attestation arm (CV-1) never
read these files, because its scope is the route table and the corpus is not a
route.

Two surfaces are held here, with content_qa's own detector (one detector, two
callers):
  * every document the runtime loads, as the runtime holds it, and every
    snippet graphrag.query returns for the attestation names;
  * the pages behind legacy_marketing_page, read from the route table, which a
    route change would re-publish.
Both directions: the copy removed on 2026-09-25 is caught.

Only the attestation class is held here. content_qa's other classes do not
run on corpus documents; that wider gap is recorded separately (OPEN_ITEMS).

This file runs in PR CI only. The same check gates the bot lanes and the
homepage deploy through scripts/check_runtime_corpus.py (stdlib), run by
.github/scripts/content_gates.sh and deploy-homepage.yml (review on #1171).
The last tests here pin that script to the runtime it reads.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import create_app  # noqa: E402
from mizoki_runtime import create_runtime  # noqa: E402
from mizoki_runtime import runtime as runtime_module  # noqa: E402

_gate_spec = importlib.util.spec_from_file_location(
    "check_runtime_corpus", BASE_DIR / "scripts" / "check_runtime_corpus.py")
corpus_gate = importlib.util.module_from_spec(_gate_spec)
_gate_spec.loader.exec_module(corpus_gate)

_spec = importlib.util.spec_from_file_location(
    "content_qa", BASE_DIR / "scripts" / "content_qa.py")
content_qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(content_qa)

# The copy removed on 2026-09-25, verbatim, so the detector is shown to catch it.
REMOVED_COPY = (
    "<span>SOC 2 Type II Certified • GDPR Compliant • HIPAA Ready</span>",
    "<p>Keep your data where it belongs. MIZ OKI can be managed entirely via "
    "our SOC2 Type II compliant cloud.</p>",
    '<h4>Enterprise Compliance Standards</h4><div class="c-tag">SOC 2 Type II</div>'
    '<div class="c-tag">ISO 27001</div><div class="c-tag">HIPAA Compliant</div>',
    "<li>Built for regulated industries (SOC 2, HIPAA-ready)</li>",
    '<div class="stat-value">100%</div><div class="stat-label">HIPAA Compliant</div>',
)

# Queries that name each framework, plus the generic word the old copy used.
ATTESTATION_QUERIES = ("SOC 2", "SOC2 Type II", "ISO 27001", "HIPAA",
                       "GDPR Compliant", "compliance", "certified")


def _hits(text: str) -> list[str]:
    return [m.group(0) for m in content_qa.attestation_hits(text)]


class RuntimeCorpusAttestationsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runtime = create_runtime(base_dir=BASE_DIR, data_dir=Path(self.temp_dir.name))
        self.app = create_app(runtime=self.runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_every_corpus_document_is_free_of_attestations(self) -> None:
        documents = self.runtime.corpus.documents
        # Not vacuous: the three legacy pages that carried the copy are loaded.
        self.assertTrue({"security.html", "resources.html", "investor.html"}
                        <= {d.path for d in documents})
        for document in documents:
            for field in ("text", "title", "summary"):
                with self.subTest(document=document.path, field=field):
                    self.assertEqual([], _hits(getattr(document, field)))

    def test_graphrag_query_returns_no_attestation_snippet(self) -> None:
        served = 0
        for query in ATTESTATION_QUERIES:
            response = self.client.post("/api/mcp/call", json={
                "name": "graphrag.query", "arguments": {"query": query, "top_k": 10}})
            self.assertEqual(200, response.status_code, response.get_data(as_text=True))
            payload = response.get_json()
            result = payload.get("result", payload)
            for match in result.get("matches", []):
                served += 1
                # Every text field a match carries is served (review on #1171).
                for field in ("snippet", "summary", "title"):
                    with self.subTest(query=query, path=match["path"], field=field):
                        self.assertEqual([], _hits(match.get(field) or ""))
        self.assertGreater(served, 0, "no snippet was returned, so nothing was checked")

    def test_legacy_redirect_pages_are_free_of_attestations(self) -> None:
        routes = [rule.rule for rule in self.app.url_map.iter_rules()
                  if rule.endpoint == "legacy_marketing_page"]
        pages = [BASE_DIR / r.lstrip("/") for r in routes if (BASE_DIR / r.lstrip("/")).is_file()]
        # Not vacuous: the six CV-7 pages sit behind this route.
        self.assertTrue({"industries.html", "security.html", "investor.html", "resources.html",
                         "roi.html", "sales-one-pager.html"} <= {p.name for p in pages})
        for page in pages:
            with self.subTest(page=page.name):
                visible = content_qa._strip_invisible_html(page.read_text(encoding="utf-8"))
                self.assertEqual([], _hits(visible))

    def test_the_gate_script_reads_the_corpus_the_runtime_declares(self) -> None:
        self.assertEqual(list(runtime_module.DOCUMENT_SPECS), corpus_gate.document_specs())

    def test_the_gate_script_strips_markup_exactly_as_the_runtime_does(self) -> None:
        """The gate carries a copy (runtime.py cannot be imported there); the
        copy must stay the served text, statement for statement."""
        def body(fn):
            node = ast.parse(inspect.getsource(fn)).body[0]
            statements = [s for s in node.body
                          if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
            return [ast.dump(s) for s in statements]
        self.assertEqual(body(runtime_module._strip_markup), body(corpus_gate._strip_markup))
        for sample in REMOVED_COPY + ("<script>x</script>A &amp; B<style>y</style>",):
            self.assertEqual(runtime_module._strip_markup(sample), corpus_gate._strip_markup(sample))

    def test_the_gate_script_is_clean_here_and_fires_on_seeded_copy(self) -> None:
        self.assertEqual([], corpus_gate.findings(content_qa, corpus_gate.document_specs()))
        seeded_dir = Path(self.temp_dir.name)
        (seeded_dir / "seeded.html").write_text(REMOVED_COPY[0], encoding="utf-8")
        (seeded_dir / "plain.html").write_text("<p>Plain copy.</p>", encoding="utf-8")
        in_text = [{"path": "seeded.html", "title": "Seeded", "summary": "A seeded page."}]
        in_summary = [{"path": "plain.html", "title": "Seeded",
                       "summary": "Managed via our SOC 2 Type II compliant cloud."}]
        in_title = [{"path": "plain.html", "title": "SOC 2 Type II Certified", "summary": "A page."}]
        self.assertTrue(corpus_gate.findings(content_qa, in_text, seeded_dir))
        self.assertTrue(corpus_gate.findings(content_qa, in_summary, seeded_dir))
        self.assertTrue(corpus_gate.findings(content_qa, in_title, seeded_dir))

    def test_the_gate_script_scans_exactly_the_documents_the_runtime_loads(self) -> None:
        """SiteCorpus drops a spec whose file is missing, title and summary
        included, so graphrag.query cannot serve any of it. The gate must skip
        the same specs and scan the rest (Copilot on #1176). Measured against
        the runtime itself, in both directions."""
        seeded_dir = Path(self.temp_dir.name)
        spec = {"document_id": "seeded", "path": "seeded.html",
                "title": "SOC 2 Type II Certified",
                "summary": "Managed via our SOC 2 Type II compliant cloud.",
                "topics": [], "entities": []}
        with mock.patch.object(runtime_module, "DOCUMENT_SPECS", [spec]):
            self.assertEqual([], runtime_module.SiteCorpus(seeded_dir).documents)
            self.assertEqual([], corpus_gate.findings(content_qa, [spec], seeded_dir))
            (seeded_dir / "seeded.html").write_text("<p>Plain copy.</p>", encoding="utf-8")
            self.assertEqual(["seeded"], [d.document_id for d in runtime_module.SiteCorpus(seeded_dir).documents])
            flagged = corpus_gate.findings(content_qa, [spec], seeded_dir)
        self.assertTrue(any("[title]" in line for line in flagged), flagged)
        self.assertTrue(any("[summary]" in line for line in flagged), flagged)

    def test_the_self_test_fails_when_the_stripper_copy_drifts(self) -> None:
        """The deploy and bot paths run --self-test, not this file, so the parity
        check has to live in the script too (Copilot on #1176)."""
        self.assertTrue(corpus_gate.stripper_parity())
        drifted = Path(self.temp_dir.name) / "runtime.py"
        drifted.write_text("def _strip_markup(raw_text):\n    return raw_text\n", encoding="utf-8")
        self.assertFalse(corpus_gate.stripper_parity(runtime_path=drifted))
        drifted.write_text("DOCUMENT_SPECS = []\n", encoding="utf-8")
        self.assertFalse(corpus_gate.stripper_parity(runtime_path=drifted))

    def test_the_removed_copy_is_caught(self) -> None:
        """The copy this file was written for must still fail both text paths."""
        for copy in REMOVED_COPY:
            with self.subTest(copy=copy[:48]):
                self.assertTrue(_hits(runtime_module._strip_markup(copy)))
                self.assertTrue(_hits(content_qa._strip_invisible_html(copy)))


if __name__ == "__main__":
    unittest.main()
