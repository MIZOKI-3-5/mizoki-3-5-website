"""The /docs portal must never publish a data table by omission.

WS-0 (Strategy Resolution Plan v1.0, 2026-09-01). The portal's secret scan and
infrastructure-identifier gate look for credential VALUES and project ids. A
Shopify customer export under ``docs/misc/`` — 16,425 rows of names, e-mails,
phones and postal addresses — carried neither, so the builder rendered it to
the PUBLIC portal as a code page. Tabular files are data, not documentation:
they are now withheld from every portal unless their path is listed in
``docs/_inventory/tabular_allowlist.txt``.

Both directions are pinned, because a rule that withheld the legitimate
inventory catalog and the COGS worksheet template would quietly break the
onboarding pack — the opposite failure (`.claude/rules/01-verification-discipline.md`:
"a rule change ships with seeded self-test cases in both directions"). The
real-tree case is the build-failing test the plan asks for: an unlisted table
anywhere under ``docs/`` turns this suite red.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_ROOT.parent
BUILDER = SITE_ROOT / "scripts" / "build_site_docs.py"
ALLOWLIST_REL = "docs/_inventory/tabular_allowlist.txt"
SEEDED_ALLOWLIST = (
    "docs/_inventory/md-catalog.csv",
    "docs/onboarding/cogs_worksheet_template.csv",
)
# A synthetic customer export in the shape the incident file had. No real person.
PII_FIXTURE = (
    "Customer ID,First Name,Last Name,Email,Default Address Address1,Phone,Total Spent\n"
    "1,Test,Person,test.person@example.invalid,1 Example Street,+10000000000,0.00\n"
)
TEMPLATE_FIXTURE = (
    "section,variant_id,sku,landed_unit_cogs,is_bundle,notes\n"
    "cogs,,SKU-EXAMPLE,0.00,false,fill per SKU\n"
)


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_site_docs", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TabularGateUnitTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = _load_builder()

    # ---------------------------------------------------------------- catches
    def test_unlisted_csv_is_withheld(self):
        self.assertTrue(self.b.tabular_gate("docs/misc/customers.csv", set()))

    def test_every_tabular_extension_is_gated(self):
        for ext in (".csv", ".tsv", ".xlsx", ".parquet", ".CSV"):
            self.assertTrue(self.b.tabular_gate(f"docs/x/table{ext}", set()), ext)

    def test_allowlist_is_by_exact_path_not_by_name(self):
        # Listing one file never publishes a same-named file elsewhere.
        allow = {"docs/onboarding/cogs_worksheet_template.csv"}
        self.assertTrue(self.b.tabular_gate("docs/misc/cogs_worksheet_template.csv", allow))

    def test_missing_allowlist_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(set(), self.b.load_tabular_allowlist(Path(td)))

    def test_person_like_header_is_flagged(self):
        hits = self.b.person_like_columns(PII_FIXTURE.splitlines()[0])
        self.assertIn("Email", hits)
        self.assertIn("First Name", hits)
        self.assertIn("Phone", hits)
        self.assertIn("Default Address Address1", hits)

    def test_person_token_is_whole_word(self):
        self.assertTrue(self.b.person_like_columns("id,display_name,created"))
        self.assertEqual([], self.b.person_like_columns("id,filename,hostname,created"))

    # ------------------------------------------------------------ stays legal
    def test_allowlisted_path_publishes(self):
        allow = set(SEEDED_ALLOWLIST)
        for rel in SEEDED_ALLOWLIST:
            self.assertIsNone(self.b.tabular_gate(rel, allow), rel)

    def test_non_tabular_files_are_not_touched(self):
        for rel in ("docs/OFFERING_MAP.md", "docs/misc/requirements.txt",
                    "docs/x/table.json", "docs/x/report.pdf"):
            self.assertIsNone(self.b.tabular_gate(rel, set()), rel)

    def test_economics_header_is_not_flagged(self):
        self.assertEqual([], self.b.person_like_columns(TEMPLATE_FIXTURE.splitlines()[0]))

    def test_prose_and_markup_are_not_headers(self):
        for line in ("Enter the customer name here.",
                     "Enter the name, the email, and the phone number of the contact.",
                     '<!doctype html><html lang="en"><head><meta name="x" content="a,b,c">',
                     '{"name": "x", "email": "y", "phone": "z"}',
                     "| Name | Email | Phone |"):
            self.assertEqual([], self.b.person_like_columns(line), line)

    def test_header_scan_is_limited_to_plain_text_and_tables(self):
        self.assertEqual(self.b.HEADER_SCAN_EXT, {".csv", ".tsv", ".xlsx", ".parquet", ".txt"})

    def test_allowlist_comments_and_blank_lines_are_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs/_inventory").mkdir(parents=True)
            (root / ALLOWLIST_REL).write_text(
                "# comment\n\n  docs/a/b.csv  \n# docs/not/listed.csv\n", encoding="utf-8")
            self.assertEqual({"docs/a/b.csv"}, self.b.load_tabular_allowlist(root))

    # ------------------------------------------------- no bypass, and it fires
    def test_self_test_covers_the_data_gate(self):
        self.assertTrue(self.b.run_self_test())

    def test_gate_has_no_publish_override(self):
        source = BUILDER.read_text(encoding="utf-8")
        for bypass in ("publish_tabular", "allow_tabular", "skip_tabular",
                       "--no-tabular-gate", "IGNORE_TABULAR"):
            self.assertNotIn(bypass, source, f"tabular gate grew a bypass: {bypass}")


class TabularGateBuildTestCase(unittest.TestCase):
    """Run the real builder over a seeded docs/ tree and read what it emitted."""

    def _build(self, root: Path) -> tuple[Path, Path, subprocess.CompletedProcess]:
        out = root / "out" / "site_docs"
        out_internal = root / "out" / "site_docs_internal"
        proc = subprocess.run(
            [sys.executable, str(BUILDER), "--repo-root", str(root),
             "--out", str(out), "--out-internal", str(out_internal)],
            capture_output=True, text=True)
        return out, out_internal, proc

    def _seed(self, root: Path, *, allowlist: str) -> None:
        (root / "docs/misc").mkdir(parents=True)
        (root / "docs/onboarding").mkdir(parents=True)
        (root / "docs/_inventory").mkdir(parents=True)
        (root / "docs/README.md").write_text("# Docs\nOrdinary copy.\n", encoding="utf-8")
        (root / "docs/misc/customers_export.csv").write_text(PII_FIXTURE, encoding="utf-8")
        (root / "docs/onboarding/cogs_worksheet_template.csv").write_text(
            TEMPLATE_FIXTURE, encoding="utf-8")
        (root / ALLOWLIST_REL).write_text(allowlist, encoding="utf-8")

    def test_seeded_pii_file_is_withheld_and_template_is_published(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed(root, allowlist="docs/onboarding/cogs_worksheet_template.csv\n")
            out, out_internal, proc = self._build(root)
            self.assertEqual(0, proc.returncode, proc.stderr)
            # Withheld from BOTH portals, and the operator is told.
            self.assertFalse((out / "misc/customers_export.csv.html").exists())
            self.assertFalse((out_internal / "misc/customers_export.csv.html").exists())
            exclusions = json.loads((out / "EXCLUSIONS.json").read_text(encoding="utf-8"))
            reasons = {x["path"]: x["reason"] for x in exclusions}
            self.assertIn("docs/misc/customers_export.csv", reasons)
            self.assertIn(ALLOWLIST_REL, reasons["docs/misc/customers_export.csv"])
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('href="/docs/misc/customers_export', index)
            # The allowlisted template is published as an ordinary code page.
            self.assertTrue((out / "onboarding/cogs_worksheet_template.csv.html").exists())
            self.assertIn("cogs_worksheet_template.csv", index)
            self.assertNotIn("docs/onboarding/cogs_worksheet_template.csv", reasons)

    def test_empty_allowlist_withholds_every_table(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed(root, allowlist="# nothing listed\n")
            out, _, proc = self._build(root)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertFalse((out / "onboarding/cogs_worksheet_template.csv.html").exists())
            self.assertFalse((out / "misc/customers_export.csv.html").exists())
            self.assertTrue((out / "README.html").exists(), "non-tabular docs still publish")

    def test_person_like_header_on_an_allowlisted_table_warns_but_publishes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed(root, allowlist="docs/misc/customers_export.csv\n")
            out, _, proc = self._build(root)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertTrue((out / "misc/customers_export.csv.html").exists())
            self.assertIn("::warning::person-like columns in docs/misc/customers_export.csv",
                          proc.stderr)


class RealTreeTestCase(unittest.TestCase):
    """The live repository state — the build-failing direction the plan asks for."""

    @classmethod
    def setUpClass(cls):
        cls.b = _load_builder()
        cls.docs = REPO_ROOT / "docs"

    def _tables(self) -> list[str]:
        return sorted(
            p.relative_to(REPO_ROOT).as_posix()
            for p in self.docs.rglob("*")
            if p.is_file() and p.suffix.lower() in self.b.TABULAR_EXT)

    def test_allowlist_exists_and_carries_the_seeds(self):
        allow = self.b.load_tabular_allowlist(REPO_ROOT)
        for rel in SEEDED_ALLOWLIST:
            self.assertIn(rel, allow, f"seed row missing from {ALLOWLIST_REL}")

    def test_every_table_under_docs_is_allowlisted(self):
        if not self.docs.is_dir():
            self.skipTest("docs/ tree not present")
        allow = self.b.load_tabular_allowlist(REPO_ROOT)
        unlisted = [rel for rel in self._tables() if self.b.tabular_gate(rel, allow)]
        self.assertEqual([], unlisted,
                         f"{len(unlisted)} table(s) under docs/ are not on {ALLOWLIST_REL} "
                         f"and would be withheld — remove them from docs/ or, if they hold "
                         f"no person data, list them: {unlisted[:5]}")

    def test_every_allowlist_row_names_a_real_file(self):
        for rel in sorted(self.b.load_tabular_allowlist(REPO_ROOT)):
            self.assertTrue((REPO_ROOT / rel).is_file(), f"stale allowlist row: {rel}")
            self.assertTrue(rel.startswith("docs/"), f"allowlist row outside docs/: {rel}")

    def test_no_allowlisted_table_starts_with_a_person_like_header(self):
        # The heuristic is a warning in the builder; on the tables we have
        # chosen to publish it is a fact we can assert.
        flagged = []
        for rel in sorted(self.b.load_tabular_allowlist(REPO_ROOT)):
            path = REPO_ROOT / rel
            if path.suffix.lower() in {".csv", ".tsv"} and path.is_file():
                head = self.b.first_line(path.read_text(encoding="utf-8", errors="replace"))
                if self.b.person_like_columns(head):
                    flagged.append(rel)
        self.assertEqual([], flagged, f"allowlisted table(s) with person-like columns: {flagged}")

    def test_committed_portal_snapshot_carries_no_unlisted_table(self):
        # `# MIZ OKI 3.5/site_docs` is a committed snapshot of a past build; the
        # incident file's rendered copy lived there too (2.4 MB, committed 2026-08-28).
        allow = self.b.load_tabular_allowlist(REPO_ROOT)
        stale = []
        for portal in ("site_docs", "site_docs_internal"):
            base = SITE_ROOT / portal
            if not base.is_dir():
                continue
            for p in base.rglob("*.html"):
                inner = p.name[:-len(".html")]
                if Path(inner).suffix.lower() in self.b.TABULAR_EXT:
                    rel = "docs/" + p.relative_to(base).as_posix()[:-len(".html")]
                    if self.b.tabular_gate(rel, allow):
                        stale.append(p.relative_to(SITE_ROOT).as_posix())
        self.assertEqual([], stale, f"rendered table(s) in the committed snapshot: {stale}")


if __name__ == "__main__":
    unittest.main()
