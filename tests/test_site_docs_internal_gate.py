"""The /docs portal must never publish production infrastructure identifiers.

MIZ-SEC 2026-08-21. This repository is PRIVATE, and `mizoki3.com/docs` is the
only path from its source tree to the open internet. Before the internal gate
existed, the portal published the production GCP project id on 132 pages and the
Cloud Run service-URL hash on 83 — reconnaissance material (bucket names,
Artifact Registry paths, `*@<project>.iam.gserviceaccount.com` principals, and
every service URL in the fleet) that no docs reader needs.

These tests pin the gate in BOTH directions, because a rule that withheld
ordinary product copy would quietly empty the portal — the opposite failure, and
just as bad. `.claude/rules/01-verification-discipline.md`: "A rule change ships
with seeded self-test cases in both directions."
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_ROOT.parent
BUILDER = SITE_ROOT / "scripts" / "build_site_docs.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_site_docs", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class InternalGateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = _load_builder()

    # ---------------------------------------------------------------- catches
    def test_gcp_project_id_is_withheld(self):
        self.assertTrue(self.b.find_internal("Deployed to spry-bus-425315-p6."))

    def test_service_account_principal_is_withheld(self):
        self.assertTrue(self.b.find_internal(
            "mizoki-platform@spry-bus-425315-p6.iam.gserviceaccount.com"))

    def test_cloud_run_url_hash_is_withheld(self):
        self.assertTrue(self.b.find_internal(
            "https://service-canonical-ingestion-ehqxake3ia-uc.a.run.app"))

    def test_explicit_marker_is_withheld(self):
        self.assertTrue(self.b.find_internal("# Title\n<!-- mizoki:internal -->\nBody"))

    def test_internal_tree_is_withheld_by_path(self):
        self.assertTrue(self.b.find_internal(
            "No identifiers here at all.", "prompts/MASTER_PROMPT.md"))

    def test_xprovider_skill_pack_is_withheld_by_path(self):
        for rel in ("skills/xprovider-v1/README.md",
                    "skills/xprovider-v1/chatgpt-gemini/inbox-triage-digest.md",
                    "skills/xprovider-v1/boss-agent/boss-agent-skills.json"):
            self.assertTrue(self.b.find_internal("No identifiers here at all.", rel), rel)

    def test_other_skill_reports_still_publish(self):
        # Only the pack tree is internal; the registration reports beside it are not.
        self.assertEqual([], self.b.find_internal(
            "No identifiers here at all.", "skills/BOSS_REGISTRATION.md"))

    def test_binary_path_carries_the_same_gate(self):
        # PDFs are copied verbatim, so they are published too. A PDF carrying the
        # project id is the identical disclosure as a markdown page carrying it.
        self.assertTrue(self.b.find_internal_bytes(
            b"%PDF-1.4 deploy to spry-bus-425315-p6"))

    # ------------------------------------------------------------ stays legal
    def test_ordinary_product_copy_still_publishes(self):
        self.assertEqual([], self.b.find_internal(
            "MIZ OKI Signal prices every order at what it truly nets after returns."))

    def test_approval_ceremony_strings_still_publish(self):
        # Deliberately NOT gated: these are typed into a workflow_dispatch input
        # that already requires repository write access, so knowing the string
        # grants nothing. Gating them would withhold the architecture canon.
        self.assertEqual([], self.b.find_internal(
            "The site ships only when a human types APPROVED: DEPLOY."))
        self.assertEqual([], self.b.find_internal("Land it with APPROVED: MERGE."))

    def test_ai_branch_names_still_publish(self):
        self.assertEqual([], self.b.find_internal(
            "Landed via claude/oracle-preconversion-intent-v1.0 on main."))

    def test_generic_cloud_vocabulary_still_publishes(self):
        self.assertEqual([], self.b.find_internal(
            "Cloud Run, us-central1, BigQuery, and Firestore back the fleet."))

    def test_marketing_tree_still_publishes(self):
        self.assertEqual([], self.b.find_internal(
            "# Shopify offering\nNet contribution, not top line.",
            "marketing/MIZOKI_SHOPIFY_OFFERING_AUG2026.md"))

    def test_clean_binary_still_publishes(self):
        self.assertEqual([], self.b.find_internal_bytes(b"%PDF-1.4 pilot playbook"))

    # ------------------------------------------------- no bypass, and it fires
    def test_self_test_passes(self):
        self.assertTrue(self.b.run_self_test())

    def test_gate_has_no_publish_override(self):
        """A security gate never grows a bypass parameter (CONSTITUTION II.1).

        The remedy for a false positive is to remove the identifier from the
        document, not to add a flag that a later change could reuse to publish
        real disclosure.
        """
        source = BUILDER.read_text(encoding="utf-8")
        for bypass in ("force_publish", "publish_anyway", "allow_internal",
                       "skip_internal", "--no-internal-gate", "IGNORE_INTERNAL"):
            self.assertNotIn(bypass, source, f"internal gate grew a bypass: {bypass}")


class RealTreeTestCase(unittest.TestCase):
    """The live repository state, not a fixture — the thing users actually get."""

    @classmethod
    def setUpClass(cls):
        cls.b = _load_builder()

    def test_no_published_doc_carries_an_infrastructure_identifier(self):
        docs = REPO_ROOT / "docs"
        if not docs.is_dir():
            self.skipTest("docs/ tree not present")
        leaked = []
        for p in docs.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".md", ".html", ".txt"}:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            docrel = p.relative_to(docs).as_posix()
            # Would it publish, and does it disclose? Both must never be true.
            if not self.b.find_internal(text, docrel):
                for pat, _why in self.b.INTERNAL_IDENTIFIERS:
                    if pat.search(text):
                        leaked.append(docrel)
                        break
        self.assertEqual([], leaked,
                         f"{len(leaked)} doc(s) would publish an infrastructure "
                         f"identifier: {leaked[:5]}")

    def test_the_flagship_public_docs_still_publish(self):
        """Guards the opposite failure: a gate so broad it empties the portal."""
        docs = REPO_ROOT / "docs"
        if not docs.is_dir():
            self.skipTest("docs/ tree not present")
        must_publish = [
            "OFFERING_MAP.md",
            "MIZOKI_SIGNAL_GROWTH_CONTROL_UNIFIED_SYSTEM_r2.0.md",
            "marketing/MIZOKI_SHOPIFY_OFFERING_AUG2026.md",
        ]
        # Revision-bumped docs are matched by glob, not by pinned filename: a
        # pinned path turns into a silent skip the moment someone ships r1.2.
        # The platform whitepaper is globbed the same way (WS-1b, 2026-09-02):
        # r3.6 AND the r3.5.x cross-link stubs at the old paths must all publish.
        must_publish += [
            p.relative_to(docs).as_posix()
            for p in sorted((docs / "marketing").glob(
                "MIZOKI_MARKETING_AUTOMATION_WHITEPAPER_*.md"))
        ]
        must_publish += [
            p.relative_to(docs).as_posix()
            for p in sorted(docs.glob("MIZOKI_3.5_WHITEPAPER_r*.md"))
        ]
        for rel in must_publish:
            p = docs / rel
            if not p.is_file():
                continue
            self.assertEqual(
                [], self.b.find_internal(p.read_text(encoding="utf-8"), rel),
                f"{rel} is customer-facing and must stay on the portal")


class InternalDocsAuthBoundaryTestCase(unittest.TestCase):
    """The internal portal is served ONLY to a signed-in session.

    Owner directive 2026-08-21: "put the docs under the same code log in as the
    front end." Withholding kept identifiers off the public web but also cost the
    team its own runbooks; the login restores them without reopening disclosure.

    Both directions again: signed-out must be refused, signed-in must succeed —
    a test that only proved the refusal would also pass if the internal portal
    were broken and served nobody at all.
    """

    USERS = '{"ops@example.test":"pw"}'

    def setUp(self):
        try:
            import flask  # noqa: F401
        except ImportError:
            self.skipTest("flask not installed")
        import os
        import sys
        sys.path.insert(0, str(SITE_ROOT))
        self._prev = os.environ.get("MIZOKI_DEMO_USERS_JSON")
        os.environ["MIZOKI_DEMO_USERS_JSON"] = self.USERS
        from app import create_app
        self.app = create_app()
        # NOTE: TESTING is deliberately NOT set here, so this case exercises the
        # sign-in path exactly as production serves it — CSRF enforced included.
        # (The old WTF_CSRF_ENABLED flag was inert: Flask-WTF is not a
        # dependency; the token is hand-rolled in app.py.)
        self.app.config.update(SECRET_KEY="test-only")
        self.client = self.app.test_client()

    def tearDown(self):
        import os
        if self._prev is None:
            os.environ.pop("MIZOKI_DEMO_USERS_JSON", None)
        else:
            os.environ["MIZOKI_DEMO_USERS_JSON"] = self._prev

    def _login(self):
        """Sign in the way a browser does — fetch the form, submit its token.

        MIZ-SEC 2026-08-22: /admin/login carries a CSRF token. Posting without
        one is refused, so a login helper that skipped it would report this
        gate as broken. Reading the token back out of the rendered form also
        keeps this test honest about the whole flow: form renders a token AND
        the token it renders is the one the POST accepts.
        """
        import re as _re
        form = self.client.get("/admin/login").get_data(as_text=True)
        match = _re.search(r'name="csrf_token" value="([^"]+)"', form)
        self.assertIsNotNone(match, "sign-in form must render a csrf_token field")
        return self.client.post("/admin/login", data={
            "email": "ops@example.test", "password": "pw",
            "csrf_token": match.group(1),
        })

    def test_signed_out_is_refused(self):
        for path in ("/docs/internal", "/docs/internal/BUILD_DEBT.html"):
            r = self.client.get(path)
            self.assertIn(r.status_code, (301, 302),
                          f"{path} must redirect an anonymous visitor to sign-in")
            self.assertNotIn("spry-bus-425315-p6", r.get_data(as_text=True))

    def test_signed_in_is_served(self):
        self._login()
        r = self.client.get("/docs/internal")
        self.assertEqual(200, r.status_code, "a signed-in session must reach the index")

    def test_public_docs_need_no_login(self):
        r = self.client.get("/docs/")
        self.assertEqual(200, r.status_code, "the public portal must stay public")

    def test_public_route_cannot_reach_the_internal_tree(self):
        """Physical separation, not path cleverness, is what makes this safe."""
        for path in (
            "/docs/../site_docs_internal/BUILD_DEBT.html",
            "/docs/%2e%2e/site_docs_internal/BUILD_DEBT.html",
            "/site_docs_internal/BUILD_DEBT.html",
        ):
            r = self.client.get(path)
            self.assertNotIn("spry-bus-425315-p6", r.get_data(as_text=True),
                             f"{path} reached the internal tree")

    def test_fail_closed_when_login_is_disabled(self):
        """Production's current posture: MIZOKI_DEMO_USERS_JSON unset.

        Nobody can establish a session, so the internal portal must be
        unreachable — never open (CONSTITUTION II.11, fail closed).
        """
        import os
        import sys
        sys.path.insert(0, str(SITE_ROOT))
        os.environ.pop("MIZOKI_DEMO_USERS_JSON", None)
        from app import create_app
        app = create_app()
        app.config.update(SECRET_KEY="test-only")
        client = app.test_client()
        client.post("/admin/login", data={"email": "ops@example.test", "password": "pw"})
        for path in ("/docs/internal", "/docs/internal/BUILD_DEBT.html"):
            r = client.get(path)
            self.assertIn(r.status_code, (301, 302), f"{path} passed open")
            self.assertNotIn("spry-bus-425315-p6", r.get_data(as_text=True))


class BuiltPortalsTestCase(unittest.TestCase):
    """The generated artifacts, as they sit in the repo."""

    PUBLIC = SITE_ROOT / "site_docs"
    INTERNAL = SITE_ROOT / "site_docs_internal"

    def test_public_portal_carries_no_identifier(self):
        if not self.PUBLIC.is_dir():
            self.skipTest("site_docs not built")
        leaked = [p.name for p in self.PUBLIC.rglob("*.html")
                  if "spry-bus-425315-p6" in p.read_text("utf-8", "ignore")
                  or "ehqxake3ia" in p.read_text("utf-8", "ignore")]
        self.assertEqual([], leaked, f"public portal leaks: {leaked[:5]}")

    def test_internal_portal_actually_has_the_docs(self):
        """Guards the silent-failure mode: a gate that serves nobody anything."""
        if not self.INTERNAL.is_dir():
            self.skipTest("site_docs_internal not built")
        pages = list(self.INTERNAL.rglob("*.html"))
        self.assertGreater(len(pages), 50,
                           "internal portal should hold the withheld docs, not be empty")


if __name__ == "__main__":
    unittest.main()


class RetiredBackendClaimTestCase(unittest.TestCase):
    """No customer-facing doc may present Neo4j as a current backing store.

    Neo4j was retired by owner decision 2026-08-09 and is not being
    re-provisioned; `docs/architecture/CELL_REGISTRY.md` row 35 is the authority
    (Firestore own-collection). The marketing whitepaper shipped saying "Neo4j
    intent graph" and was corrected on 2026-08-21 with owner approval.

    This test exists because the correction is fragile in a specific way: the
    Drive original still carries the old wording, so re-copying that file over
    the repo copy would silently reintroduce a false claim onto the PUBLIC
    portal. An in-document comment would have been the obvious warning, but the
    markdown renderer passes HTML comments straight through to the served page —
    shipping the very phrase to customers. A test is the right home for the
    warning: it enforces instead of asking, and it never reaches a reader.

    Scope is the customer-facing marketing tree only. Engineering docs may
    legitimately discuss Neo4j as retired history, and the design-vintage docs
    are bannered rather than rewritten (.claude/rules/03-canonical-architecture.md).
    """

    #: Phrases that assert Neo4j is a live component, as opposed to naming it as
    #: retired history. Kept literal so the failure message is self-explaining.
    PRESENT_TENSE = ("Neo4j intent graph", "Neo4j interest graph",
                     "Neo4j knowledge graph", "Neo4j-backed")

    def test_marketing_docs_do_not_claim_neo4j(self):
        marketing = REPO_ROOT / "docs" / "marketing"
        if not marketing.is_dir():
            self.skipTest("docs/marketing not present")
        offenders = []
        for p in sorted(marketing.rglob("*.md")):
            text = p.read_text(encoding="utf-8", errors="ignore")
            for phrase in self.PRESENT_TENSE:
                if phrase in text:
                    offenders.append(f"{p.name}: {phrase!r}")
        self.assertEqual(
            [], offenders,
            "Neo4j was retired 2026-08-09; CELL_REGISTRY row 35 says Firestore. "
            f"Customer-facing copy still claims it: {offenders}")

    def test_the_corrected_line_still_says_firestore(self):
        """The opposite failure: the row silently losing its backing store.

        Version-agnostic ON PURPOSE. This test was first written against the
        r1.1 filename; hours later another session superseded that file with
        r1.2, rebuilt from a source that still carried the old wording, and the
        pinned path made this assertion skip instead of fire. A check that
        answers "skipped" when the thing it guards is renamed is not a check
        (.claude/rules/01-verification-discipline.md). Glob for whichever
        revision is present, and require at least one.
        """
        marketing = REPO_ROOT / "docs" / "marketing"
        if not marketing.is_dir():
            self.skipTest("docs/marketing not present")
        papers = sorted(marketing.glob("MIZOKI_MARKETING_AUTOMATION_WHITEPAPER_*.md"))
        if not papers:
            self.skipTest("no marketing automation whitepaper in tree")
        for p in papers:
            text = p.read_text(encoding="utf-8")
            if "| 35 |" not in text:
                continue
            self.assertIn("Firestore-backed intent graph", text,
                          f"{p.name}: Cell 35's row must name its real backing store")


class PublicPageClaimGuardTestCase(unittest.TestCase):
    """Retired and unshipped capability must not be claimed on the SERVED pages.

    Added 2026-08-21 after the Neo4j guard above — which scanned only
    `docs/marketing/**` — missed the two surfaces that mattered most: the
    homepage carried a connector card reading "Neo4j" badged **LIVE** for a
    backend retired 2026-08-09, and platform.html listed it as a native
    connector. A gate that does not cover a surface cannot defend it
    (.claude/rules/01-verification-discipline.md).

    Scope is the site's own served HTML. `site_docs*/` is generated output and
    `archive/` is preserved history — both excluded, and both are checked by
    their own tests.
    """

    #: Retired 2026-08-09 by owner decision; the KG is Firestore-backed and the
    #: neo4j-uri host is NXDOMAIN by choice.
    RETIRED_BACKENDS = ("Neo4j", "TigerGraph")

    #: Ghost-bid execution has never run against real ad spend (BUILD_DEBT
    #: GB-1). signal-measurement.html states this correctly — "the ghost-bid
    #: execution path ... is in development" — so the ban is on claiming it as
    #: something a customer GETS, not on naming the technique.
    GHOST_BID_AS_DELIVERED = (
        "ghost bids, and matched-market experiments on your actual spend",
        "ghost bids on your spend",
        "ghost bids, matched cities",
    )

    def _served_pages(self):
        for p in sorted(SITE_ROOT.glob("*.html")):
            yield p
        for sub in ("marketing", "media", "blog"):
            d = SITE_ROOT / sub
            if d.is_dir():
                for p in sorted(d.rglob("*.html")):
                    yield p

    def test_no_served_page_claims_a_retired_backend(self):
        offenders = []
        for p in self._served_pages():
            text = p.read_text(encoding="utf-8", errors="ignore")
            for backend in self.RETIRED_BACKENDS:
                if backend in text:
                    offenders.append(f"{p.relative_to(SITE_ROOT)}: {backend}")
        self.assertEqual(
            [], offenders,
            "Retired backends must not appear on served pages "
            "(Neo4j retired 2026-08-09; the KG is Firestore-backed): "
            f"{offenders}")

    def test_no_served_page_sells_ghost_bids_as_delivered(self):
        offenders = []
        for p in self._served_pages():
            text = " ".join(
                re.sub(r"<[^>]+>", " ", p.read_text(encoding="utf-8", errors="ignore")).split())
            for phrase in self.GHOST_BID_AS_DELIVERED:
                if phrase in text:
                    offenders.append(f"{p.relative_to(SITE_ROOT)}: {phrase!r}")
        self.assertEqual(
            [], offenders,
            "No live ghost-bid experiment has run against real ad spend "
            f"(BUILD_DEBT GB-1); do not sell it as delivered: {offenders}")

    def test_the_honest_ghost_bid_qualifier_survives(self):
        """The opposite failure: scrubbing the technique instead of labelling it.

        signal-measurement.html is the page that states the status correctly.
        If a future sweep deletes that sentence, the ban above would still pass
        while the platform silently stopped explaining itself.
        """
        p = SITE_ROOT / "signal-measurement.html"
        if not p.is_file():
            self.skipTest("signal-measurement.html not present")
        text = " ".join(
            re.sub(r"<[^>]+>", " ", p.read_text(encoding="utf-8")).split())
        self.assertIn("Registration is shipped for all three", text)
        self.assertIn("in development", text)


class OutputPathCollisionTestCase(unittest.TestCase):
    """Two sources may never render to one output path.

    `docs/ORACLE_DOCUMENT_INDEX.md` and `.html` both targeted
    `ORACLE_DOCUMENT_INDEX.html`; the walk visited `.html` first and the
    markdown render overwrote the hand-authored page on every build. Nothing
    errored, both files stayed in the repo, and the styled page simply never
    existed on the site for five deploys. Pinned in BOTH directions: the
    collision must fail the build, and an ordinary tree must still build.
    """

    def _build(self, tree: dict):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, body in tree.items():
                f = root / "docs" / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(body, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(BUILDER), "--repo-root", str(root),
                 "--out", "out", "--out-internal", "out_internal"],
                capture_output=True, text=True)

    def test_collision_fails_the_build(self):
        r = self._build({"PAGE.md": "# Page\nbody\n",
                         "PAGE.html": "<title>Page</title><p>hand-authored</p>"})
        self.assertEqual(1, r.returncode,
                         f"a colliding tree must fail the build; stdout={r.stdout[-400:]}")
        self.assertIn("collision", (r.stderr + r.stdout).lower())

    def test_ordinary_tree_still_builds(self):
        """The opposite failure: a guard so eager it refuses a legal tree."""
        r = self._build({"PAGE.md": "# Page\nbody\n",
                         "OTHER.html": "<title>Other</title><p>fine</p>",
                         "sub/THIRD.md": "# Third\nbody\n"})
        self.assertEqual(0, r.returncode,
                         f"a legal tree must build; stderr={r.stderr[-400:]}")


class GatedCrossLinkRoutingTestCase(unittest.TestCase):
    """A link to a sign-in-only doc must resolve to the portal that holds it.

    Measured 2026-08-22: 248 cross-links pointed at `/docs/<x>.html` for a
    target that renders into `/docs/internal/` — every one a 404. Both
    directions again: gated targets must move, public targets must not.
    """

    @classmethod
    def setUpClass(cls):
        cls.b = _load_builder()

    def test_link_to_a_gated_doc_routes_to_the_internal_portal(self):
        self.assertEqual(
            "/docs/internal/runbooks/OPS.html",
            self.b.rewrite_href("runbooks/OPS.md", "docs/INDEX.md", {"runbooks/OPS.md"}))

    def test_link_to_a_public_doc_stays_on_the_public_portal(self):
        self.assertEqual(
            "/docs/runbooks/OPS.html",
            self.b.rewrite_href("runbooks/OPS.md", "docs/INDEX.md", set()))

    def test_anchor_survives_the_rewrite(self):
        self.assertEqual(
            "/docs/internal/OPS.html#step-2",
            self.b.rewrite_href("OPS.md#step-2", "docs/INDEX.md", {"OPS.md"}))

    def test_a_path_outside_docs_still_goes_to_github(self):
        self.assertTrue(
            self.b.rewrite_href("../src/app.py", "docs/INDEX.md", set())
            .startswith(self.b.GH_BLOB))


class InternalTreeWithheldListTestCase(unittest.TestCase):
    """A file the portal cannot render, from a tree that is internal BY PURPOSE,
    is named only behind sign-in, never on the public portal.

    Measured 2026-09-25: the xprovider pack's Claude zips (`docs/skills/
    xprovider-v1/claude/*.zip`) cannot be read as text, so the builder withholds
    them, and the public index and EXCLUSIONS.json would have named all 14. The
    owner's personal workflow skills were among those names, although every
    rendered page of that tree is sign-in-only. Pinned in both directions: the
    same bytes OUTSIDE an internal tree must still be listed on the public
    portal, because that list exists so an operator sees what was withheld.
    """

    ZIP_BYTES = b"PK\x03\x04\x14\x00\x00\x00\x08\x00\xff\xfe\x80\x81binary"

    def _build(self, rel: str) -> dict:
        import json
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir()
            (root / "docs" / "PAGE.md").write_text("# Page\nbody\n", encoding="utf-8")
            f = root / "docs" / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(self.ZIP_BYTES)
            r = subprocess.run(
                [sys.executable, str(BUILDER), "--repo-root", str(root),
                 "--out", "out", "--out-internal", "out_internal"],
                capture_output=True, text=True)
            self.assertEqual(0, r.returncode, r.stderr[-400:])
            out, out_internal = root / "out", root / "out_internal"
            internal_json = out_internal / "EXCLUSIONS.json"   # absent before 2026-09-25
            return {
                "public_json": json.loads((out / "EXCLUSIONS.json").read_text()),
                "public_index": (out / "index.html").read_text(encoding="utf-8"),
                "internal_json": (json.loads(internal_json.read_text())
                                  if internal_json.is_file() else []),
                "internal_index": (out_internal / "index.html").read_text(encoding="utf-8"),
            }

    def test_unreadable_file_in_an_internal_tree_is_not_named_publicly(self):
        got = self._build("skills/xprovider-v1/claude/inbox-triage-digest.zip")
        path = "docs/skills/xprovider-v1/claude/inbox-triage-digest.zip"
        self.assertNotIn(path, [x["path"] for x in got["public_json"]])
        self.assertNotIn("inbox-triage-digest", got["public_index"])
        self.assertIn(path, [x["path"] for x in got["internal_json"]])
        self.assertIn("inbox-triage-digest", got["internal_index"])

    def test_unreadable_file_elsewhere_is_still_listed_publicly(self):
        """The opposite failure: an operator must still see what was withheld."""
        got = self._build("misc/export-bundle.zip")
        self.assertIn("docs/misc/export-bundle.zip", [x["path"] for x in got["public_json"]])
        self.assertIn("export-bundle.zip", got["public_index"])
        self.assertEqual([], got["internal_json"])
