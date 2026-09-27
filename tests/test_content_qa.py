"""Truth-discipline gate + link-preview contract (Phase 3, 2026-08-03;
rule E + completion-run scope expansion, 2026-08-08).

Guarantees, permanently in the suite:

1. scripts/content_qa.py both FIRES on seeded violations (a gate that cannot
   fail is not a gate) and passes CLEAN on the real scoped surfaces — banned
   strings (incl. the sub-N-ms observed-performance class), preview framing,
   number labeling, §-sequence, and the rule-E unbacked-claims check.
2. The machinery-claims ledger (docs/marketing/claims-ledger.yaml) parses
   with the gate's stdlib subset parser, agrees with PyYAML whenever PyYAML
   is installed, cites only evidence that exists on disk (code AND tests per
   backed row), and cross-references docs/BUILD_DEBT.md cleanly in both
   directions.
3. Every page of the Signal capability site renders a correct link preview:
   non-empty <title> and meta description, og:title/og:description/og:image
   present, and the og:image asset actually resolves on this site.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

from app import app  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "content_qa", BASE_DIR / "scripts" / "content_qa.py"
)
content_qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(content_qa)

# Marker for BUILD_DEBT rows that are engineering-only deferred items (no
# customer surface, hence no ledger claim to cite them). It must be the FIRST
# text of the row's description cell — a marker buried mid-cell does not
# qualify — so a row cannot smuggle the exemption alongside a real claim.
ENGINEERING_ONLY_MARKER = "(engineering, no customer surface)"


def _engineering_only_debt_ids(debt_text: str, ids: set[str]) -> set[str]:
    """The subset of `ids` whose BUILD_DEBT row opens with the marker."""
    exempt: set[str] = set()
    for debt_id in ids:
        pattern = (
            r"^\|\s*" + re.escape(debt_id) + r"\s*\|\s*"
            + re.escape(ENGINEERING_ONLY_MARKER)
        )
        if re.search(pattern, debt_text, re.MULTILINE):
            exempt.add(debt_id)
    return exempt

SIGNAL_PAGES = (
    "/signal",
    "/signal/thresholds",
    "/signal/budget",
    "/signal/creative",
    "/signal/audiences",
    "/signal/measurement",
    "/shopify",
)

# Dedicated authored copy for the generated /intent application. The built
# bundle does not exist until the deployment workflow runs, so the source is
# the stable customer-facing surface covered by the truth gate.
INTENT_SCOPE = (
    "intent-site/src/Home.tsx",
)

# Letter three updates the doorman article in ROLLOUT_SCOPE.
FOUNDER_LETTER_SCOPE = (
    "blog/the-number-your-bank-account-reports.html",
    "blog/before-you-raise-bids-check-the-checkout.html",
    "blog/when-your-best-seller-loses-money.html",
    "blog/what-the-system-refuses-to-learn.html",
    "blog/the-decision-to-do-nothing.html",
    "blog/your-business-should-remember-why.html",
    "blog/when-media-becomes-a-business-decision.html",
    "blog/autonomy-is-earned.html",
)

# The original 12 rollout surfaces — their scoping is a permanent contract.
ROLLOUT_SCOPE = (
    "signal.html",
    "signal-thresholds.html",
    "signal-budget.html",
    "signal-creative.html",
    "signal-audiences.html",
    "signal-measurement.html",
    "demo.html",
    "demo-signal.html",
    "blog/doorman-problem.html",
    "executive-briefing/js/data.js",
    "shopify.html",
    "docs/marketing/shopify-app-listing-copy.md",
)

# Completion-run scope expansion (2026-08-08). security.html and roi.html were
# dropped by the 2026-08-09 route audit — see REDIRECT_ONLY_PAGES below.
EXPANSION_SCOPE = (
    "index.html",
    "pricing.html",
    "demo-capital.html",
    "demo-estate.html",
    "demo-risk.html",
    "demo-nexus.html",
    "blog/decision-control-plane.html",
    "blog/adc-decision-framework.html",
    "blog/relu-lens-meta-algorithm.html",
    "blog/index.html",
    "marketing/governance.html",
)

# Route audit against app.py (2026-08-09): every remaining SERVED customer
# surface joins the gate. walkthrough.html was the headline gap — served at
# /walkthrough, listed in sitemap.xml, canon-pinned, and unscanned since the
# gate shipped.
SERVED_SCOPE_2026_08_09 = (
    "walkthrough.html",
    "privacy.html",
    "terms.html",
    "executive-briefing/index.html",
    "marketing/capital.html",
    "marketing/counsel.html",
    "marketing/engine.html",
    "marketing/estate.html",
    "marketing/modules.html",
    "marketing/pricing.html",
    "marketing/risk.html",
    "marketing/simulator.html",
    "media/index.html",
    "media/platform.html",
    "media/decision-graph.html",
    "media/how-it-works.html",
    "media/use-cases.html",
    "media/pilot.html",
    "media/trust.html",
    "media/resources.html",
    "media/contact.html",
    "templates/contact.html",
)

# Route-audit CORRECTION (2026-08-09, second pass). The first audit claimed
# "every remaining served customer surface" while these were served by app.py
# and neither scoped nor mentioned: /counsel, /estate(.html), /capital(.html),
# /risk(.html), /demo/counsel (the other five demo desks were scoped), plus
# the console shell (/console) and the generic template route's index entry
# (/templates/index.html). All scan clean, so scoping cost nothing.
SERVED_SCOPE_CORRECTION = (
    "counsel.html",
    "estate.html",
    "capital.html",
    "risk.html",
    "demo-counsel.html",
    "mizoki3-site/console/index.html",
    "templates/index.html",
)

# Scope hold-outs CLOSED (2026-08-09, third pass). These five served pages
# were named in the scope comments but left unscanned. Two DIFFERENT reasons
# were in play and each was closed the way its own reason required — which is
# the point of listing them together:
#   * marketing/index.html, marketing/walkthrough.html — a real unlabeled
#     "40%" in the storyboard poster line. COPY fix.
#   * templates/intelligence.html, templates/vision.html — real unlabeled
#     "89%" figures, plus a "<100ms" query-latency tile with no design-target
#     label on intelligence.html. COPY fix.
#   * marketing/signal.html — a RULE FALSE POSITIVE on the page's own "What
#     we never say" honesty disclaimer. Closed by a bounded exemption, with
#     the arm itself left exactly as strict (see DisclaimerListingTestCase).
# Executive Demo r1.0 (2026-09-12): the single-file presenter surface, served at
# /media/demo (app.py media_subpage; /media/executive-demo from the 2026-09-13
# placement ruling until the 2026-09-14 slug rename); scoped in the same change
# that added its route.
EXEC_DEMO_SCOPE_2026_09_12 = (
    "media/demo.html",
)

SCOPE_HOLDOUTS_CLOSED = (
    "marketing/index.html",
    "marketing/signal.html",
    "marketing/walkthrough.html",
    "templates/intelligence.html",
    "templates/vision.html",
)

# Growth-control v1.3 package draft copy (2026-08-19 gate-gap audit): the
# package tree docs/marketing-growth-control-v1.3/ landed (2242353) with zero
# scope entries, so CI reported green having never opened it. The two
# customer-facing pieces are scoped on the shopify-app-listing-copy precedent
# (draft customer copy is scoped before it is published anywhere). The
# package's master prompt, integration-review memo, and zip are deliberately
# excluded — rulebook / decision-memo / binary classes, reasons documented in
# SCOPE_FILES itself.
DRAFT_COPY_SCOPE_2026_08_19 = (
    "docs/marketing-growth-control-v1.3/MIZOKI3_Growth_Control_Marketing_Visual_v1_3.html",
    "docs/marketing-growth-control-v1.3/MIZOKI3_Growth_Control_Marketing_Package_README_v1_3.md",
)

# The deliberately-excluded package files, pinned in both directions
# (parallel-audit delta, 2026-08-19): the rulebook/decision-memo pair must
# quote the phrases the gate bans in order to ban them, so scoping one later
# is a deliberate decision with its findings dispositioned — never a drift.
PACKAGE_RULEBOOK_UNSCOPED = (
    "docs/marketing-growth-control-v1.3/"
    "CLAUDE_CODE_MASTER_PROMPT_MIZOKI3_MARKETING_GROWTH_CONTROL_v1_3.md",
    "docs/marketing-growth-control-v1.3/"
    "MIZOKI3_Growth_Control_Website_Integration_Review_v1_3.md",
)

# The binary container beside them. The gate cannot read a zip, and the scope
# comment's "sha256-identical members" was true only at scoping time —
# PackageZip coverage below keeps it true.
PACKAGE_ZIP = ("docs/marketing-growth-control-v1.3/"
               "MIZOKI3_Growth_Control_Marketing_Package_v1_3.zip")

# app.py's legacy_marketing_page() 301-redirects these to "/" — no visitor
# ever reads them, so scanning them spends gate budget on dead copy. Their
# ABSENCE is the contract: re-scoping one means it was re-served, which must
# be a deliberate change to the route table first.
REDIRECT_ONLY_PAGES = ("security.html", "roi.html")


class ContentQAGateTestCase(unittest.TestCase):
    def test_gate_fires_on_every_seeded_violation_class(self) -> None:
        findings = content_qa.check_file("signal.html", content_qa.SEEDED_BAD)
        for marker in ("mind-reading", "guaranteed", "deployed-intent",
                       "deployed-net-yield", "Quokka Swarm", "KL-divergence",
                       "preview-framing", "number-label", "sec-sequence"):
            self.assertTrue(
                any(marker in f for f in findings),
                f"gate failed to catch seeded violation class: {marker}",
            )

    def test_gate_fires_on_the_seeded_sub_n_ms_claim(self) -> None:
        # 2026-08-08 hardening: "served sub-100ms" joins the observed-
        # performance class (seed section s6 has no design-target label).
        findings = content_qa.check_file("signal.html", content_qa.SEEDED_BAD)
        self.assertTrue(
            any("design target" in f and "'s6'" in f for f in findings),
            "gate failed to catch the seeded sub-N-ms observed-performance claim",
        )

    def test_gate_stays_quiet_on_the_clean_seed(self) -> None:
        self.assertEqual([], content_qa.check_file("signal.html", content_qa.SEEDED_CLEAN))

    def test_rule_e_fires_on_each_seeded_subclass_and_clean_fixture_passes(self) -> None:
        fired, clean = content_qa.run_rule_e_self_test()
        self.assertEqual(
            5, len(fired),
            "rule-E self-test must seed one violation per sub-class a/b/c/d "
            "plus the banned-string-in-a-claim-field arm",
        )
        for subclass, caught in fired.items():
            self.assertTrue(caught, f"rule E failed to catch seeded sub-class: {subclass}")
        self.assertEqual([], clean, "rule E fired on the seeded CLEAN ledger fixture")

    def test_full_self_test_passes(self) -> None:
        # The exact path CI runs before every scan (--self-test).
        self.assertTrue(content_qa.run_self_test(), "content_qa --self-test is broken")

    def test_scoped_surfaces_hold_the_truth_discipline(self) -> None:
        findings = content_qa.run_scan(BASE_DIR)
        self.assertEqual([], findings, "\n".join(findings))


class ScopeExpansionTestCase(unittest.TestCase):
    def test_rollout_scope_is_intact(self) -> None:
        for rel in ROLLOUT_SCOPE:
            self.assertIn(rel, content_qa.SCOPE_FILES, f"rollout surface descoped: {rel}")

    def test_completion_run_pages_are_scoped(self) -> None:
        for rel in EXPANSION_SCOPE:
            self.assertIn(rel, content_qa.SCOPE_FILES, f"expansion surface missing: {rel}")

    def test_served_surfaces_from_the_route_audit_are_scoped(self) -> None:
        for rel in SERVED_SCOPE_2026_08_09:
            self.assertIn(rel, content_qa.SCOPE_FILES, f"served surface unscanned: {rel}")

    def test_route_audit_correction_surfaces_are_scoped(self) -> None:
        # The five division/demo pages the first audit missed while claiming
        # completeness, plus the two remaining served shells.
        for rel in SERVED_SCOPE_CORRECTION:
            self.assertIn(rel, content_qa.SCOPE_FILES, f"served surface unscanned: {rel}")

    def test_executive_demo_is_scoped(self) -> None:
        # Served at /media/demo (slug renamed 2026-09-14; /media/executive-demo
        # since the 2026-09-13 placement ruling;
        # /demo/executive from 2026-09-12 until then); a silent descope would
        # leave its status chips (LIVE / PARTIAL / IN BUILD / PROPOSED) unread.
        for rel in EXEC_DEMO_SCOPE_2026_09_12:
            self.assertIn(rel, content_qa.SCOPE_FILES, f"executive demo unscanned: {rel}")

    def test_walkthrough_is_scoped(self) -> None:
        # Called out on its own: it is served, sitemapped and canon-pinned, so
        # a silent descope here is the exact regression the audit found.
        self.assertIn("walkthrough.html", content_qa.SCOPE_FILES)

    def test_redirect_only_pages_are_not_scoped(self) -> None:
        for rel in REDIRECT_ONLY_PAGES:
            self.assertNotIn(
                rel, content_qa.SCOPE_FILES,
                f"{rel} 301-redirects to '/' in app.py — scanning it gates dead copy",
            )

    def test_closed_scope_holdouts_are_scoped(self) -> None:
        # The gate had a written list of pages it knew it was not scanning.
        # A gate that does not cover a surface cannot defend it, so the
        # hold-out list is now empty and this test keeps it that way.
        for rel in SCOPE_HOLDOUTS_CLOSED:
            self.assertIn(rel, content_qa.SCOPE_FILES, f"scope hold-out reopened: {rel}")

    def test_growth_control_v13_draft_copy_is_scoped(self) -> None:
        # The v1.3 package tree landed unscanned (a gate that does not cover a
        # surface cannot defend it); a silent descope here reopens that gap.
        for rel in DRAFT_COPY_SCOPE_2026_08_19:
            self.assertIn(rel, content_qa.SCOPE_FILES, f"v1.3 draft copy descoped: {rel}")

    def test_package_rulebook_files_stay_unscoped_deliberately(self) -> None:
        # Both directions of the scope decision: the exclusion is deliberate,
        # so scoping one of these later must be a conscious change here with
        # its rulebook-class findings dispositioned — not a drift.
        for rel in PACKAGE_RULEBOOK_UNSCOPED:
            self.assertNotIn(
                rel, content_qa.SCOPE_FILES,
                f"{rel} is the rulebook/decision memo for this surface — it "
                f"quotes the phrases the gate bans in order to ban them. "
                f"Scoping it must be a deliberate decision, not a drift.",
            )

    def test_growth_control_zip_members_match_the_scanned_sources(self) -> None:
        # The package zip is a binary container the content gate cannot read.
        # Coverage is transitive instead: the member set is pinned — a file
        # added to (or removed from) the container without a scope decision
        # fails here — and every member must stay byte-identical to its loose
        # sibling in the same directory, which is either scanned or
        # deliberately excluded above. A drifted member would be exactly the
        # silent-divergence class the gate exists to catch.
        import zipfile
        expected = {Path(rel).name
                    for rel in DRAFT_COPY_SCOPE_2026_08_19 + PACKAGE_RULEBOOK_UNSCOPED}
        package_dir = (BASE_DIR / PACKAGE_ZIP).parent
        with zipfile.ZipFile(BASE_DIR / PACKAGE_ZIP) as zf:
            names = {n for n in zf.namelist() if not n.endswith("/")}
            self.assertEqual(
                expected, names,
                "package zip member set changed — make the scope decision for "
                "the new/removed member, then update the pinned set",
            )
            for name in sorted(names):
                self.assertEqual(
                    (package_dir / name).read_bytes(), zf.read(name),
                    f"{name}: zip member diverged from the scanned source — "
                    f"rebuild the zip from the tree files",
                )

    def test_no_scope_holdout_remains_in_the_source(self) -> None:
        # Prose contract: the module may DOCUMENT the closed hold-outs, but it
        # must not describe a page it is still choosing not to scan.
        source = (BASE_DIR / "scripts" / "content_qa.py").read_text(encoding="utf-8")
        for phrase in ("stay out of scope", "is held out until",
                       "must be fixed in the copy first"):
            self.assertNotIn(phrase, source, f"scope hold-out language survives: {phrase}")

    def test_scope_list_has_no_duplicates_and_no_drift(self) -> None:
        for rel in FOUNDER_LETTER_SCOPE:
            self.assertIn(rel, content_qa.SCOPE_FILES)
        self.assertEqual(
            len(content_qa.SCOPE_FILES), len(set(content_qa.SCOPE_FILES)),
            "duplicate entry in SCOPE_FILES",
        )
        self.assertEqual(
            len(INTENT_SCOPE) + len(ROLLOUT_SCOPE) + len(EXPANSION_SCOPE) + len(SERVED_SCOPE_2026_08_09)
            + len(SERVED_SCOPE_CORRECTION) + len(SCOPE_HOLDOUTS_CLOSED)
            + len(DRAFT_COPY_SCOPE_2026_08_19) + len(EXEC_DEMO_SCOPE_2026_09_12)
            + len(FOUNDER_LETTER_SCOPE),
            len(content_qa.SCOPE_FILES),
            "SCOPE_FILES drifted from the 1 intent + 12 rollout + 11 expansion + 22 served "
            "+ 7 route-audit-correction + 5 closed-hold-out + 2 growth-control-"
            "v1.3 draft-copy + 1 executive-demo + 8 new founder-letter surfaces",
        )

    def test_every_scoped_file_exists(self) -> None:
        for rel in content_qa.SCOPE_FILES:
            self.assertTrue((BASE_DIR / rel).exists(), f"scoped file missing on disk: {rel}")

    def test_sub_n_ms_joins_the_observed_performance_class(self) -> None:
        for text in ("served sub-100ms", "sub-100 ms responses", "sub 250ms"):
            self.assertTrue(content_qa.OBSERVED_PERF.search(text), text)
        for text in ("subsystems in 100 ms", "the submarine"):
            self.assertFalse(content_qa.OBSERVED_PERF.search(text), text)

    def test_fifteen_minute_arm_fires_on_sight_with_no_context_test(self) -> None:
        # 2026-08-09 (second pass): the cadence-context narrowing is REVERTED.
        # It admitted one meeting-agenda line and, with it, an entire class of
        # real latency claims — none of which name a cycle, refresh or update,
        # so no context window could ever separate them from the agenda. All
        # four went silent under the narrowed arm; the agenda was reworded in
        # walkthrough.html instead.
        for text in ("The full attribution rebuild completes in 15 minutes.",
                     "Your first governed decision lands in under 15 minutes.",
                     "Budget reallocation happens within 15 minutes of a "
                     "threshold breach.",
                     "From signal to spend change: 15 minutes.",
                     "refreshed on 15-minute cycles",
                     "the intent graph updates every 15 minutes",
                     "a 15 minute refresh interval",
                     "Book a 15-minute intro call with the team."):
            self.assertTrue(content_qa._observed_perf_hit(text), text)
        # The other arms are unconditional too.
        for text in ("served sub-100ms", "sub-second responses"):
            self.assertTrue(content_qa._observed_perf_hit(text), text)

    def test_the_arm_has_no_exemption_mechanism(self) -> None:
        # The narrowing existed to admit exactly ONE site-wide line. The fix is
        # in the copy, so there is no cadence-context helper and no allowlist
        # left to reuse — a future "just add it to the exceptions" is not an
        # option the module offers.
        self.assertFalse(hasattr(content_qa, "PERF_CADENCE_CONTEXT"))
        self.assertFalse(hasattr(content_qa, "PERF_CONTEXT_WINDOW"))

    def test_walkthrough_demo_agenda_no_longer_writes_the_figure(self) -> None:
        # The single site-wide false positive, fixed in the copy. If this
        # sentence ever reverts to "15 minutes", the gate must go red rather
        # than the rule go soft.
        raw = (BASE_DIR / "walkthrough.html").read_text(encoding="utf-8")
        self.assertNotRegex(raw, r"(?i)15[\s-]?minutes?\b")
        self.assertIn("the next fifteen showing the platform", raw)

    def test_design_target_is_accepted_but_estimate_vocabulary_is_not(self) -> None:
        self.assertTrue(content_qa.NUMBER_LABEL.search("a design target, not a promise"))
        self.assertTrue(content_qa.NUMBER_LABEL.search("design-target framing"))
        for weasel in ("our estimate", "projected returns", "key assumptions"):
            self.assertFalse(
                content_qa.NUMBER_LABEL.search(weasel),
                f"gate must not accept '{weasel}' as an honesty label",
            )


class HashingTerminologyTestCase(unittest.TestCase):
    """The rails pepper; they do not salt. Copy must say so (rule A, 2026-08-09).

    Evidence: services/measurement-rails/identity.py hashes with a KMS-managed
    pepper — one held-back secret across records — and the claims ledger row
    for M2 says in writing "pepper, not per-record salt — keep that wording
    honest". "Salted SHA-256" therefore claims a property the code lacks.
    """

    AFFIRMATIVE = (
        "salted SHA-256 hashes of first-party identifiers",
        "identities stitch through a salted hash",
        "the SHA-256 hashes are salted before export",
        "each identifier is hashed with a per-record salt",
        # Blind spots closed 2026-08-09 (second pass) — all four passed
        # SILENTLY, and the first is the commonest phrasing of the claim.
        "Emails are hashed and salted before egress.",
        "Identifiers are SHA-256, salted, and shared.",
        "We use a salted digest of the email address.",
        "The salt is applied to every SHA-256 identifier.",
        # ordering/copula variants the same fix covers
        "salted and hashed on the way out",
        "a SHA-256 digest with a secret salt",
    )
    # Negated / contrastive uses are the discipline itself — legal, exactly as
    # "not mind-reading" and "never a guaranteed outcome" are.
    LEGAL = (
        "The outbound match key is deliberately unsalted.",
        "a held-back pepper, not a per-record salt",
        "a salt would silently zero the match rate",
        "keyed by a peppered SHA-256 instead",
        "Our Salt Lake City desk runs the pilot.",
        "salt and pepper on the table",
        # The corrected page copy, whole. The widened arms must not turn the
        # page's own honesty into a violation — this sentence puts "SHA-256"
        # 31 characters from "salt", which is why the arms stay keyed to a
        # connective rather than being a bare proximity test.
        "The outbound match key is deliberately unsalted, because Google and "
        "Meta both match on the SHA-256 of the normalized value and a salt "
        "would silently zero the match rate.",
        "Anything this platform stores or returns is keyed by a peppered "
        "SHA-256 instead — a held-back pepper, not a per-record salt.",
        "Identifiers are hashed with SHA-256 under a KMS-managed pepper.",
    )

    def test_affirmative_salt_claims_are_flagged(self) -> None:
        for text in self.AFFIRMATIVE:
            self.assertTrue(content_qa.HASH_SALT.search(text), text)

    def test_negated_and_unrelated_uses_stay_legal(self) -> None:
        for text in self.LEGAL:
            self.assertFalse(content_qa.HASH_SALT.search(text), text)

    def test_character_reference_evasion_is_decoded(self) -> None:
        # "Salted SHA&#8209;256" is a non-breaking hyphen: it RENDERS as an
        # ordinary "Salted SHA-256" and slipped every arm, because the gate
        # read source bytes where the reader sees a character. The visible-text
        # reducer now decodes references (after tag removal, so decoding can
        # never manufacture a tag).
        for markup in ('<p>Salted SHA&#8209;256 identity stitching.</p>',
                       '<p>Salted SHA&#x2011;256 identity stitching.</p>',
                       '<p>salted <strong>SHA-256</strong> hashes</p>'):
            self.assertTrue(
                any("hashing-terminology" in f
                    for f in content_qa.check_file("probe.html", markup)),
                markup,
            )

    def test_rule_fires_through_check_file(self) -> None:
        findings = content_qa.check_file("signal.html", content_qa.SEEDED_BAD)
        self.assertTrue(
            any("hashing-terminology" in f for f in findings),
            "gate failed to catch the seeded salted-SHA-256 claim",
        )

    def test_live_measurement_page_uses_pepper_language(self) -> None:
        raw = (BASE_DIR / "signal-measurement.html").read_text(encoding="utf-8")
        self.assertEqual([], [f for f in content_qa.check_file("signal-measurement.html", raw)
                              if "hashing-terminology" in f])

    def test_claims_ledger_claim_fields_are_linted_too(self) -> None:
        # The M2 row said "Salted SHA-256" for a full change set AFTER the page
        # it authorizes had been corrected, because the ledger is deliberately
        # outside SCOPE_FILES. The banned-string arms now run over each row's
        # claim: text, so the row that authorizes the copy cannot outlive it.
        self.assertTrue(content_qa.HASH_SALT.search("Salted SHA-256 identity stitching"))
        findings = content_qa.check_claims_ledger(BASE_DIR, REPO_ROOT)
        self.assertEqual([], findings, "\n".join(findings))
        seeded = content_qa.check_banned_strings(
            "docs/marketing/claims-ledger.yaml :: claim 'M2'",
            "Salted SHA-256 identity stitching",
        )
        self.assertTrue(any("hashing-terminology" in f for f in seeded))

    def test_ledger_notes_may_still_state_the_honest_contrast(self) -> None:
        # Only claim: is linted. note: is the honesty commentary and must stay
        # free to write "pepper, not per-record salt" — the same exemption the
        # story bank gets for quoting the phrases it bans.
        self.assertEqual([], content_qa.check_banned_strings(
            "note", "KMS-peppered SHA-256 (pepper, not per-record salt — "
                    "keep that wording honest)."))


class GuaranteeVocabularyTestCase(unittest.TestCase):
    """Story-bank rule 5: never a guaranteed outcome (rule A, F13 2026-08-09).

    The arm matched only "guaranteed", so the two commonest ways to make the
    same promise — "we guarantee X", "a guarantee of X" — were silent.
    """

    AFFIRMATIVE = (
        "We guarantee the lift.",
        "A guarantee of incremental lift.",
        "Results are guaranteed.",
        "Guaranteed incremental revenue.",
    )
    LEGAL = (
        # Story-bank rule 5 verbatim, and the other negations.
        "Never a guaranteed outcome.",
        "not guaranteed",
        "no guarantee of a result",
        # signal-creative.html:270 — bandit theory, a property of a regret
        # bound, not a promise to a customer. This is the ONE exemption and it
        # is a fixed-width lookbehind on the literal preceding word.
        "Creative tests run as bandits — Thompson sampling by default, "
        "upper-confidence-bound where regret guarantees matter — so learning "
        "reallocates impressions continuously.",
    )

    def test_every_inflection_of_the_promise_is_flagged(self) -> None:
        for text in self.AFFIRMATIVE:
            self.assertTrue(content_qa.GUARANTEED.search(text), text)

    def test_negations_and_the_bandit_term_of_art_stay_legal(self) -> None:
        for text in self.LEGAL:
            self.assertFalse(content_qa.GUARANTEED.search(text), text)

    def test_the_live_creative_page_still_passes(self) -> None:
        raw = (BASE_DIR / "signal-creative.html").read_text(encoding="utf-8")
        self.assertEqual([], content_qa.check_file("signal-creative.html", raw))

    def test_the_bare_s_inflection_is_covered(self) -> None:
        # "the platform guarantees X" is the same promise as "guaranteed X".
        self.assertTrue(content_qa.GUARANTEED.search(
            "The platform guarantees incremental lift."))
        self.assertIn("The platform guarantees incremental lift.",
                      content_qa.GUARANTEE_PROBES)


class AttestationClaimTestCase(unittest.TestCase):
    """Rule A: no unattested compliance attestation on a scoped surface.

    Measured 2026-09-25: /blog, /walkthrough and two Journal articles served
    "SOC 2 Type II Certified • GDPR Compliant • HIPAA Ready" in their footers,
    while docs/product/SECURITY_PACKET_v1.md §9 records no SOC 2 report, no ISO
    27001 certificate and no HIPAA scope. #1152 removed it from one page; no arm
    named the family, so the other three stayed.
    """

    FOOTER = ("<footer><div class=\"footer-bottom\"><span>© 2026 MIZ OKI. All "
              "rights reserved.</span><span>SOC 2 Type II Certified • GDPR "
              "Compliant • HIPAA Ready</span></div></footer>")

    @staticmethod
    def _attestations(text: str) -> list[str]:
        return [f for f in content_qa.check_banned_strings("probe.html", text)
                if "unattested compliance attestation" in f]

    def test_every_attestation_form_is_flagged(self) -> None:
        for text in content_qa.ATTESTATION_PROBES:
            self.assertTrue(self._attestations(text), text)

    def test_denials_roadmap_and_mechanism_wording_stay_legal(self) -> None:
        for text in content_qa.ATTESTATION_LEGAL_PROBES:
            self.assertEqual([], self._attestations(text), text)

    def test_the_shipped_footer_fires_through_check_file(self) -> None:
        findings = [f for f in content_qa.check_file("walkthrough.html", self.FOOTER)
                    if "unattested compliance attestation" in f]
        # SOC 2, GDPR Compliant and HIPAA are three separate claims.
        self.assertEqual(3, len(findings), findings)

    def test_a_denial_qualifies_only_its_own_clause(self) -> None:
        # #1156 review (Codex, Copilot): an affirmative claim that shares a
        # sentence with a denial of a DIFFERENT framework must still fire —
        # exactly once, on the unqualified claim.
        for text in content_qa.ATTESTATION_CLAUSE_PROBES:
            self.assertEqual(1, len(self._attestations(text)), text)

    def test_a_qualified_label_keeps_its_colon_answer(self) -> None:
        # #1159 review (Codex): the SOC 2 type or a label noun before the colon
        # is still the framework's label, so the denial after it is honoured.
        for text in ("SOC 2 Type II: not attested.",
                     "ISO 27001 certification: not planned.",
                     "SOC 2 (Type II) report: not attested.",
                     "HIPAA scope: none."):
            self.assertEqual([], self._attestations(text), text)
        # The bound, other direction: an asserting adjective ends the label,
        # and a clean audit outcome is the claim, not a denial.
        for text in ("SOC 2 Type II certified: no HIPAA scope.",
                     "SOC 2 Type II report: no exceptions.",
                     "No exceptions in our SOC 2 Type II report.",
                     "ISO 27001 audit completed without material findings."):
            self.assertEqual(1, len(self._attestations(text)), text)

    def test_iso_42001_is_in_the_family(self) -> None:
        # SECURITY_PACKET_v1.md row 2 records no ISO 27001/42001 certificate.
        self.assertTrue(self._attestations("ISO 42001 certified infrastructure."))
        self.assertEqual([], self._attestations(
            "No ISO 42001 certificate is on file."))

    def test_a_denial_for_one_list_item_does_not_clear_its_neighbours(self) -> None:
        # The shipped footer strung claims together with bullets; a negation
        # attached to one item must not launder the next one.
        self.assertEqual(1, len(self._attestations(
            "No PCI DSS scope • SOC 2 Type II Certified")))

    def test_the_served_footers_no_longer_carry_the_claim(self) -> None:
        for rel in ("walkthrough.html", "blog/index.html",
                    "blog/decision-control-plane.html",
                    "blog/adc-decision-framework.html"):
            raw = (BASE_DIR / rel).read_text(encoding="utf-8")
            self.assertEqual([], [f for f in content_qa.check_file(rel, raw)
                                  if "unattested compliance attestation" in f], rel)

    def test_the_security_packet_absence_row_reads_legal(self) -> None:
        # The packet's own wording is the model of the legal form.
        row = next(line for line in
                   (REPO_ROOT / "docs/product/SECURITY_PACKET_v1.md")
                   .read_text(encoding="utf-8").splitlines()
                   if "No SOC 2" in line)
        self.assertEqual([], self._attestations(row), row)


class DisclaimerListingTestCase(unittest.TestCase):
    """The bounded exemption for "What we never say" honesty strips.

    marketing/signal.html was held out of scope because MIND_READING fired on
    the page's own disclaimer — a list of the phrases the house refuses to
    use. Deleting a disclaimer to satisfy a gate makes the page LESS honest,
    so that was a rule defect, not a copy defect.

    The fix is NOT a longer lookbehind (which would excuse a real claim two
    clauses after any stray "never"). It requires two independent conditions
    at once: the phrase is inside quotation marks AND opens within
    DISCLAIMER_WINDOW characters of a literal disclaimer heading. These tests
    pin BOTH directions — an exemption proven in only one direction is an
    exemption nobody has checked.
    """

    def test_the_live_disclaimer_strip_is_legal(self) -> None:
        raw = (BASE_DIR / "marketing" / "signal.html").read_text(encoding="utf-8")
        findings = content_qa.check_file("marketing/signal.html", raw)
        self.assertEqual([], [f for f in findings if "banned-string" in f],
                         "\n".join(findings))

    def test_the_page_still_carries_the_disclaimer_it_was_held_out_for(self) -> None:
        # The point of the exemption is that the honesty text SURVIVES. If
        # the strip is ever deleted to make a gate quiet, this fails.
        raw = (BASE_DIR / "marketing" / "signal.html").read_text(encoding="utf-8")
        self.assertIn("What we never say", raw)
        self.assertIn("&quot;Mind-reading.&quot;", raw)

    def test_seeded_disclaimer_listings_stay_legal(self) -> None:
        for probe in content_qa.DISCLAIMER_LEGAL_PROBES:
            self.assertEqual(
                [], [f for f in content_qa.check_file("probe.html", probe)
                     if "banned-string" in f], probe)

    def test_the_exemption_cannot_hide_a_real_claim(self) -> None:
        # Same heading present in every probe. Prose under the heading, and a
        # quoted phrase past the window, are both still caught.
        for probe in content_qa.DISCLAIMER_CAUGHT_PROBES:
            self.assertTrue(
                any("banned-string" in f
                    for f in content_qa.check_file("probe.html", probe)), probe)

    def test_the_arms_themselves_were_not_loosened(self) -> None:
        # With no disclaimer heading anywhere, a quoted phrase is still a
        # violation — the quotation marks alone buy nothing.
        self.assertTrue(any(
            "banned-string" in f for f in content_qa.check_file(
                "probe.html", '<p>&quot;Mind-reading.&quot; is our tagline.</p>')))
        self.assertTrue(content_qa.MIND_READING.search("our mind-reading engine"))
        self.assertTrue(content_qa.GUARANTEED.search("guaranteed lift"))


class ObservedPerformancePerimeterTestCase(unittest.TestCase):
    """The observed-performance arm reads the CLAIM, not one spelling of it.

    Four evasions passed silently: the spelled cardinal, the abbreviated
    unit, "quarter hour", and a bare millisecond figure with no sub-/< prefix.
    This is a WIDENING — nothing the arm caught before is excused, and no
    exemption mechanism is introduced.
    """

    CAUGHT = (
        "Your first governed decision lands in under fifteen minutes.",
        "Median responses under 100ms.",
        "Signals are re-ranked on 15min cycles.",
        "Reallocation lands within a quarter hour of a breach.",
        "The rebuild completes in a quarter of an hour.",
        "Every intent vector arrives in 100ms.",
        "100ms p95 on the scoring path.",
        "fifteen-minute refresh interval",
        "15 min cycles",
    )
    LEGAL = (
        # The reworded walkthrough demo agenda: "fifteen" with no unit.
        "The standard demo is 30 minutes: the first ten minutes understanding "
        "your challenges, the next fifteen showing the platform, and the last "
        "five discussing next steps.",
        # The two negative probes that have guarded the sub-N-ms arm since it
        # shipped. A cue list containing the bare preposition "in" would have
        # turned the first into a violation — which is why it does not.
        "subsystems in 100 ms",
        "the submarine",
        "Fifteen analysts reviewed the ledger.",
        "The board meets for a quarter of the year on this.",
        "We closed 15 minor findings this quarter.",
    )

    def test_every_evasion_is_caught(self) -> None:
        for text in self.CAUGHT:
            self.assertTrue(content_qa._observed_perf_hit(text), text)

    def test_legal_copy_stays_legal(self) -> None:
        for text in self.LEGAL:
            self.assertFalse(content_qa._observed_perf_hit(text), text)

    def test_the_original_arms_remain_unconditional(self) -> None:
        # The context test lives ONLY on the bare-milliseconds arm, which
        # previously caught nothing at all. Everything the arm caught before
        # still fires on sight, with no cue word anywhere.
        for text in ("The full attribution rebuild completes in 15 minutes.",
                     "From signal to spend change: 15 minutes.",
                     "sub-second",
                     "served sub-100ms",
                     "gated in &lt;100ms"):
            self.assertTrue(content_qa._observed_perf_hit(text), text)


class NumberLabelScopeTestCase(unittest.TestCase):
    """One label no longer clears a whole section (rule C, 2026-08-09).

    A section on these pages runs 2.4k–4.4k visible characters, so a single
    "operating default" anywhere in it was a very large blast radius: any
    figure added elsewhere in that section was invisible to the gate.
    """

    def test_a_figure_beyond_the_window_is_caught(self) -> None:
        findings = content_qa.check_file("probe.html", content_qa.NUMBER_SCOPE_CAUGHT)
        self.assertTrue(any("number-label" in f and "34%" in f for f in findings),
                        f"section-wide label still clears a distant figure: {findings}")

    def test_a_figure_inside_the_window_is_legal(self) -> None:
        self.assertEqual([], [f for f in content_qa.check_file(
            "probe.html", content_qa.NUMBER_SCOPE_LEGAL_NEAR) if "number-label" in f])

    def test_an_explicit_scope_banner_covers_the_section(self) -> None:
        # A sentence that actually declares the numbers illustrative is what a
        # whole-section label ought to be, and it still works past the window.
        self.assertEqual([], [f for f in content_qa.check_file(
            "probe.html", content_qa.NUMBER_SCOPE_LEGAL_BANNER) if "number-label" in f])

    def test_bare_parameter_words_do_not_act_as_banners(self) -> None:
        # "operating default" / "design target" describe ONE figure. They must
        # not scope a section the way an explicit banner does.
        for weak in ("The 10% cap is an operating default.",
                     "Latency is a design target.",
                     "composite"):
            self.assertIsNone(content_qa.LABEL_BANNER.search(weak), weak)
        for banner in ("what follows is a composite scenario",
                       "the numbers in it are illustrative",
                       "illustrative numbers"):
            self.assertIsNotNone(content_qa.LABEL_BANNER.search(banner), banner)

    def test_the_window_is_a_stated_bound_not_a_section(self) -> None:
        self.assertEqual(1300, content_qa.NUMBER_LABEL_WINDOW)


class DeadInternalLinkTestCase(unittest.TestCase):
    """Rule F — no scoped page links to a path that dead-ends at "/".

    app.py 301-redirects ten legacy page URLs to the homepage. Links to them
    never 404, so nothing flagged them: a "ROI Calculator" button silently
    became a homepage button while the label went on claiming a page that is
    not served. Forty-one such links sat on scoped pages.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.dead = content_qa.dead_end_paths(BASE_DIR)

    def test_the_dead_end_set_comes_from_the_route_table(self) -> None:
        # Non-vacuous: an empty set means the extractor broke, and rule F
        # would then silently defend nothing.
        self.assertTrue(self.dead, "no redirect-to-homepage routes extracted from app.py")
        for rel in REDIRECT_ONLY_PAGES:
            self.assertIn(f"/{rel}", self.dead)

    def test_legitimate_301s_are_not_in_the_dead_end_set(self) -> None:
        # These redirect to their OWN canonical view, not to home, so they can
        # never be flagged. /logout is a 302 action endpoint, not a moved page.
        for path in ("/blogs.html", "/blog/", "/blog/index.html",
                     "/blog/decision-control-plane.html", "/media-buying",
                     "/logout", "/"):
            self.assertNotIn(path, self.dead, path)

    def test_seeded_dead_links_are_caught_absolute_and_relative(self) -> None:
        findings = content_qa.check_dead_links(
            "blog/probe.html", content_qa.DEAD_LINK_CAUGHT_PROBE,
            content_qa.DEAD_LINK_SEEDED_PATHS)
        self.assertTrue(any("/roi.html" in f for f in findings), findings)
        self.assertTrue(any("/case-studies.html" in f for f in findings), findings)

    def test_live_routes_anchors_and_offsite_links_stay_legal(self) -> None:
        self.assertEqual([], content_qa.check_dead_links(
            "blog/probe.html", content_qa.DEAD_LINK_LEGAL_PROBE,
            content_qa.DEAD_LINK_SEEDED_PATHS))

    def test_no_scoped_page_dead_ends_at_the_homepage(self) -> None:
        findings = [f for f in content_qa.run_scan(BASE_DIR) if "dead-link" in f]
        self.assertEqual([], findings, "\n".join(findings))

    def test_the_repaired_links_resolve_on_the_live_app(self) -> None:
        # The repointed destinations must actually be served — a repoint to
        # another dead end would satisfy rule F and still strand the reader.
        app.config["TESTING"] = True
        client = app.test_client()
        for path in ("/", "/demo", "/pricing", "/blog", "/executive-briefing/",
                     "/walkthrough"):
            self.assertEqual(200, client.get(path, follow_redirects=True).status_code, path)


class SectionSequenceDeviceTestCase(unittest.TestCase):
    """Rule D reads all three filing devices: .sec-mark, .filing, .folio."""

    def test_index_html_is_under_rule_d(self) -> None:
        self.assertIn("index.html", content_qa.SEC_MARK_PAGES)

    def test_extractor_reads_folio_and_filing_in_document_order(self) -> None:
        marks = content_qa.extract_sec_marks(content_qa.SEEDED_DEVICE_CLEAN)
        self.assertEqual([1, 2, 3, 4], marks)

    def test_duplicate_section_number_is_caught(self) -> None:
        findings = content_qa.check_file("index.html", content_qa.SEEDED_DUP_SECTIONS)
        self.assertTrue(
            any("sec-sequence" in f and "duplicated: [1]" in f for f in findings),
            f"duplicate §01 not detected: {findings}",
        )

    def test_every_sec_mark_page_extracts_a_strict_sequence(self) -> None:
        # Non-vacuous: each page must yield marks AND they must be 1..N.
        for rel in content_qa.SEC_MARK_PAGES:
            marks = content_qa.extract_sec_marks(
                (BASE_DIR / rel).read_text(encoding="utf-8"))
            self.assertTrue(marks, f"no §-marks extracted from {rel}")
            self.assertEqual(list(range(1, len(marks) + 1)), marks, rel)


class ClaimsLedgerTestCase(unittest.TestCase):
    """The machinery-claims ledger is well-formed, backed, and cross-checked."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger_path = BASE_DIR / content_qa.LEDGER_REL
        cls.text = cls.ledger_path.read_text(encoding="utf-8")
        cls.doc = content_qa._parse_simple_yaml(cls.text)
        cls.claims = cls.doc["claims"]

    def test_ledger_parses_and_has_the_machinery_rows(self) -> None:
        self.assertIn("meta", self.doc)
        self.assertIn("claims", self.doc)
        self.assertGreaterEqual(len(self.claims), 30, "machinery rows went missing")
        ids = [row["id"] for row in self.claims]
        self.assertEqual(len(ids), len(set(ids)), "duplicate claim ids")
        for required in ("M1", "M9", "A10", "A13", "C20", "C38", "C46", "C47"):
            self.assertIn(required, ids)

    def test_subset_parser_agrees_with_pyyaml_when_available(self) -> None:
        try:
            import yaml  # type: ignore
        except ImportError:  # pragma: no cover - CI runs stdlib-only
            self.skipTest("PyYAML not installed; stdlib subset parser stands alone")
        self.assertEqual(
            yaml.safe_load(self.text), self.doc,
            "ledger drifted outside the documented YAML subset — the stdlib "
            "parser and PyYAML disagree",
        )

    def test_every_backed_row_cites_existing_code_and_tests(self) -> None:
        for row in self.claims:
            rid = row["id"]
            self.assertIn(row["status"], ("backed", "debt"), rid)
            evidence = row.get("evidence", [])
            if row["status"] == "backed":
                self.assertTrue(evidence, f"{rid}: backed row without evidence")
            for ev in evidence:
                self.assertTrue((REPO_ROOT / ev).exists(),
                                f"{rid}: evidence missing on disk: {ev}")
            if row["status"] == "backed":
                names = [Path(ev).name.lower() for ev in evidence]
                self.assertTrue(any("test" in n for n in names),
                                f"{rid}: backed row cites no test evidence")
                self.assertTrue(any("test" not in n for n in names),
                                f"{rid}: backed row cites no code/config evidence")

    def test_debt_ids_cross_check_in_both_directions(self) -> None:
        debt_text = (REPO_ROOT / content_qa.BUILD_DEBT_REL).read_text(encoding="utf-8")
        table_ids = set(content_qa.DEBT_ROW.findall(debt_text))
        self.assertTrue(table_ids, "docs/BUILD_DEBT.md has no debt table rows")
        cited = {row["debt_id"] for row in self.claims if row.get("debt_id")}
        self.assertEqual(set(), cited - table_ids,
                         f"ledger cites debt ids missing from BUILD_DEBT.md: {cited - table_ids}")
        # Engineering-only debt rows carry no customer-facing claim, so there
        # is no ledger row that could honestly cite them. The class is bounded
        # by an explicit in-row marker (first words of the row's second cell)
        # introduced with F4-SEAL-1 (landed 2026-08-24, 291f4d06); an
        # uncited row WITHOUT the marker still fails, so the exemption cannot
        # absorb a real claim gap. Both directions are seeded in
        # test_engineering_only_marker_is_bounded below.
        uncited = table_ids - cited
        engineering_only = _engineering_only_debt_ids(debt_text, uncited)
        self.assertEqual(set(), uncited - engineering_only,
                         "BUILD_DEBT.md rows cited by no ledger claim and not "
                         f"marked engineering-only: {uncited - engineering_only}")
        for row in self.claims:
            if row["status"] == "debt":
                self.assertTrue(row.get("debt_id"),
                                f"{row['id']}: debt row without a debt_id")

    def test_engineering_only_marker_is_bounded(self) -> None:
        # Seeds for the exemption above, both directions: the marker row is
        # exempt; the same row without the marker is not; the marker anywhere
        # but the start of the description cell does not count.
        marked = "| X-1 | (engineering, no customer surface) internal seal fix | why | exit |"
        unmarked = "| X-2 | growth-scheduler seal fix with no marker | why | exit |"
        late_marker = "| X-3 | seal fix (engineering, no customer surface) later | why | exit |"
        text = "\n".join([marked, unmarked, late_marker])
        self.assertEqual({"X-1"},
                         _engineering_only_debt_ids(text, {"X-1", "X-2", "X-3"}))

    def test_page_coverage_pages_are_scoped_and_ids_resolve(self) -> None:
        coverage = self.doc["meta"]["page_coverage"]
        ids = {row["id"] for row in self.claims}
        self.assertTrue(coverage)
        for page, required in coverage.items():
            self.assertIn(page, content_qa.SCOPE_FILES,
                          f"page_coverage names an unscoped page: {page}")
            self.assertTrue(required, f"page_coverage for {page} is empty")
            for cid in required:
                self.assertIn(cid, ids, f"{page} requires unknown claim id {cid}")

    def test_rule_e_is_clean_on_the_real_tree(self) -> None:
        findings = content_qa.check_claims_ledger(BASE_DIR)
        self.assertEqual([], findings, "\n".join(findings))


class StatTileBasisTestCase(unittest.TestCase):
    """C45 — the homepage stat tiles match their recorded, in-tree basis.

    Pins the two count tiles the ledger row C45 covers: "Connector gateway"
    (17 chipped surfaces — 11 LIVE, Shopify + GA4 IN BUILD, Klaviyo + The
    Trade Desk + Amazon Ads + Walmart Connect ROADMAP; 15 → 17 on 2026-09-08
    when the two W3-S8-7 chips landed under the owner's in-session gate) and "Governed agent actions" (79 — the
    execute_action dispatch-table handler count, re-counted here from
    miz-oki-adk-agents/boss/boss_agent_core.py so the tile can never drift
    from the source silently). Chip count must equal the stat number
    (punch-list P3 acceptance rule). Counts are recorded basis, never
    performance claims (claim_label: built, pre-benchmark).
    """

    def test_stat_tiles_match_the_recorded_basis(self) -> None:
        page = (BASE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            '<div class="k">Connector gateway</div>'
            '<div class="v">17 surfaces · 11 live</div>',
            page, "connector tile drifted from the ledgered basis (C45)")
        self.assertIn(
            '<div class="k">Governed agent actions</div>'
            '<div class="v">79</div>',
            page, "action-count tile drifted from the ledgered basis (C45)")
        self.assertEqual(
            17, page.count('class="cstat'),
            "connector chip count no longer equals the 17-surface stat (C45)")
        self.assertEqual(
            11, page.count("cstat live"),
            "LIVE chip count no longer equals the 11-live stat (C45)")

    def test_action_count_matches_the_dispatch_table(self) -> None:
        core = (REPO_ROOT / "miz-oki-adk-agents" / "boss"
                / "boss_agent_core.py").read_text(encoding="utf-8")
        block = core[core.index("action_handlers = {"):]
        depth = 0
        for pos, ch in enumerate(block):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    block = block[:pos]
                    break
        handlers = re.findall(r'"([a-z0-9_]+)":', block)
        self.assertEqual(
            79, len(handlers),
            "the governed-agent-actions tile no longer matches the "
            "execute_action dispatch-table count — update the tile, ledger "
            "row C45, and this pin together")


class LinkPreviewTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def _meta(self, body: str, prop: str) -> str:
        m = re.search(
            r'<meta[^>]+(?:property|name)="' + re.escape(prop) + r'"[^>]+content="([^"]*)"',
            body,
        ) or re.search(
            r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="' + re.escape(prop) + r'"',
            body,
        )
        return m.group(1) if m else ""

    def test_every_signal_page_renders_a_complete_link_preview(self) -> None:
        for path in SIGNAL_PAGES:
            body = self.client.get(path).get_data(as_text=True)
            title = re.search(r"<title>([^<]+)</title>", body)
            self.assertTrue(title and title.group(1).strip(), f"{path}: empty <title>")
            self.assertTrue(self._meta(body, "description").strip(), f"{path}: empty description")
            self.assertTrue(self._meta(body, "og:title").strip(), f"{path}: missing og:title")
            self.assertTrue(self._meta(body, "og:description").strip(), f"{path}: missing og:description")
            og_image = self._meta(body, "og:image")
            self.assertTrue(og_image, f"{path}: missing og:image")
            asset = urlparse(og_image).path
            self.assertEqual(
                200, self.client.get(asset).status_code,
                f"{path}: og:image does not resolve on this site: {asset}",
            )

    def test_sitemap_carries_lastmod_for_the_rollout_pages(self) -> None:
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        for path in SIGNAL_PAGES:
            entry = re.search(
                r"<loc>https://mizoki3\.com" + re.escape(path) + r"</loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>",
                sitemap,
            )
            self.assertIsNotNone(entry, f"{path}: sitemap entry lacks lastmod")


if __name__ == "__main__":
    unittest.main()


class EvidenceClassLedgerTestCase(unittest.TestCase):
    """WS-4 (Strategy Resolution Plan v1.0, ruling S5): the ledger carries an
    `evidence_class` provenance axis, and a Preview-label flip is authorized
    only by DESIGN-PARTNER-or-better evidence.

    Every assertion here runs against SEEDED ledgers in a temp tree — never
    the real one — and covers both directions (rule 01: a rule ships with the
    violation it must catch and the legal shape it must not flag).
    """

    def _findings(self, ledger_text: str, readout: bool = True) -> list[str]:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            site = content_qa._seed_evidence_class_tree(repo, ledger_text, readout=readout)
            return content_qa.check_claims_ledger(site, repo)

    def _ledger(self, rows: str, sources: str | None = None) -> str:
        meta = "meta:\n  version: 1\n  page_coverage:\n    signal-measurement.html: [SEED-OK]\n"
        if sources is not None:
            meta += "  evidence_sources:\n" + sources
        return meta + (
            "claims:\n"
            "  - id: SEED-OK\n"
            "    page: signal-measurement.html\n"
            "    claim: \"seed: healthy backed row\"\n"
            "    status: backed\n"
            "    evidence:\n"
            "      - seed_module.py\n"
            "      - seed_module_test.py\n"
        ) + rows

    _READOUT_ROW = (
        "  - id: SEED-X\n"
        "    page: signal-measurement.html\n"
        "    claim: \"seed: row under test\"\n"
        "    status: backed\n"
        "    evidence:\n"
        "      - seed_module.py\n"
        "      - seed_module_test.py\n"
        "      - " + content_qa.SEEDED_READOUT_REL + "\n"
    )
    _MYCOCOONS = (
        "    mycocoons:\n"
        "      class: SELF-PILOT\n"
        "      provenance: inference-2026-09-01-part-a-finding-5-owner-confirmation-pending\n"
    )

    # (i) vocabulary ---------------------------------------------------------
    def test_vocabulary_is_closed_and_ranked(self) -> None:
        self.assertEqual(("SELF-PILOT", "DESIGN-PARTNER", "CUSTOMER"),
                         content_qa.VALID_EVIDENCE_CLASS)
        rank = content_qa.EVIDENCE_CLASS_RANK
        self.assertLess(rank["SELF-PILOT"], rank["DESIGN-PARTNER"])
        self.assertLess(rank["DESIGN-PARTNER"], rank["CUSTOMER"])
        self.assertEqual("DESIGN-PARTNER", content_qa.PUBLIC_CLAIM_MIN_CLASS)

    def test_each_class_parses_and_is_clean(self) -> None:
        for cls in content_qa.VALID_EVIDENCE_CLASS:
            row = self._READOUT_ROW + f"    evidence_class: {cls}\n"
            findings = [f for f in self._findings(self._ledger(row)) if "rule-E(e)" in f]
            self.assertEqual([], findings, cls)

    def test_unknown_class_names_the_closed_vocabulary(self) -> None:
        row = self._READOUT_ROW + "    evidence_class: PILOT\n"
        findings = [f for f in self._findings(self._ledger(row)) if "rule-E(e)" in f]
        self.assertEqual(1, len(findings), findings)
        for cls in content_qa.VALID_EVIDENCE_CLASS:
            self.assertIn(cls, findings[0])
        self.assertIn("SEED-X", findings[0])

    # (ii) flip rule ---------------------------------------------------------
    def test_flip_from_self_pilot_is_refused(self) -> None:
        row = self._READOUT_ROW + "    evidence_class: SELF-PILOT\n    preview_flip: true\n"
        findings = [f for f in self._findings(self._ledger(row)) if "rule-E(f)" in f]
        self.assertTrue(any("SEED-X" in f and "SELF-PILOT" in f for f in findings), findings)

    def test_flip_without_a_class_is_refused(self) -> None:
        row = self._READOUT_ROW + "    preview_flip: true\n"
        findings = [f for f in self._findings(self._ledger(row)) if "rule-E(f)" in f]
        self.assertTrue(any("SEED-X" in f for f in findings), findings)

    def test_flip_from_design_partner_or_customer_with_readout_is_clean(self) -> None:
        for cls in ("DESIGN-PARTNER", "CUSTOMER"):
            row = self._READOUT_ROW + f"    evidence_class: {cls}\n    preview_flip: true\n"
            self.assertEqual([], self._findings(self._ledger(row)), cls)

    def test_flip_requires_a_readout_evidence_path(self) -> None:
        row = (
            "  - id: SEED-X\n"
            "    page: signal-measurement.html\n"
            "    claim: \"seed: flip with code evidence only\"\n"
            "    status: backed\n"
            "    evidence:\n"
            "      - seed_module.py\n"
            "      - seed_module_test.py\n"
            "    evidence_class: CUSTOMER\n"
            "    preview_flip: true\n"
        )
        findings = [f for f in self._findings(self._ledger(row)) if "rule-E(f)" in f]
        self.assertTrue(any("SEED-X" in f and "readout" in f.lower() for f in findings), findings)

    def test_flip_requires_backed_status(self) -> None:
        row = (
            "  - id: SEED-X\n"
            "    page: signal-measurement.html\n"
            "    claim: \"seed: flip on a debt row\"\n"
            "    status: debt\n"
            "    debt_id: XY-1\n"
            "    evidence:\n"
            "      - " + content_qa.SEEDED_READOUT_REL + "\n"
            "    evidence_class: CUSTOMER\n"
            "    preview_flip: true\n"
        )
        findings = [f for f in self._findings(self._ledger(row)) if "rule-E(f)" in f]
        self.assertTrue(any("SEED-X" in f and "backed" in f for f in findings), findings)

    def test_flip_must_be_a_boolean(self) -> None:
        row = self._READOUT_ROW + "    evidence_class: CUSTOMER\n    preview_flip: maybe\n"
        findings = [f for f in self._findings(self._ledger(row)) if "rule-E(f)" in f]
        self.assertTrue(any("SEED-X" in f for f in findings), findings)

    def test_explicit_false_flip_carries_no_obligation(self) -> None:
        row = self._READOUT_ROW + "    preview_flip: false\n"
        self.assertEqual([], self._findings(self._ledger(row)))

    def test_readout_requirement_is_a_path_shape(self) -> None:
        ok = ("docs/pilot/F4_PILOT_READOUT_2026-10-01.md",
              "docs/reports/GC_PILOT_READOUT_R1.md",
              "docs/pilot/readout.md")
        bad = ("docs/pilot/PLAYBOOK.md", "docs/readout.md",
               "services/x/readout.py", "docs/reports/PILOT_READINESS_FINAL_2026-08-24.md")
        for path in ok:
            self.assertTrue(content_qa._is_readout_evidence(path), path)
        for path in bad:
            self.assertFalse(content_qa._is_readout_evidence(path), path)

    # (iii) tenant → class resolution ---------------------------------------
    def test_mycocoons_source_is_self_pilot_by_inference_and_flip_is_refused(self) -> None:
        row = (self._READOUT_ROW
               + "    tenant: mycocoons\n    evidence_class: SELF-PILOT\n    preview_flip: true\n")
        findings = self._findings(self._ledger(row, self._MYCOCOONS))
        self.assertTrue(any("rule-E(f)" in f and "SEED-X" in f for f in findings), findings)

    def test_tenant_class_cannot_be_overridden_upward_on_the_row(self) -> None:
        # A row that names a SELF-PILOT source but claims CUSTOMER on its own
        # line is a disagreement (E-g) AND the flip is still refused (E-f):
        # the effective class is the LOWER of the two — fail-closed.
        row = (self._READOUT_ROW
               + "    tenant: mycocoons\n    evidence_class: CUSTOMER\n    preview_flip: true\n")
        findings = self._findings(self._ledger(row, self._MYCOCOONS))
        self.assertTrue(any("rule-E(g)" in f and "SEED-X" in f for f in findings), findings)
        self.assertTrue(any("rule-E(f)" in f and "SEED-X" in f for f in findings), findings)

    def test_tenant_row_without_a_class_is_a_finding(self) -> None:
        row = self._READOUT_ROW + "    tenant: mycocoons\n"
        findings = [f for f in self._findings(self._ledger(row, self._MYCOCOONS))
                    if "rule-E(g)" in f]
        self.assertTrue(any("SEED-X" in f for f in findings), findings)

    def test_tenant_row_agreeing_with_its_source_is_clean(self) -> None:
        row = self._READOUT_ROW + "    tenant: mycocoons\n    evidence_class: SELF-PILOT\n"
        self.assertEqual([], self._findings(self._ledger(row, self._MYCOCOONS)))

    def test_unknown_tenant_source_is_refused(self) -> None:
        row = self._READOUT_ROW + "    tenant: nobody\n    evidence_class: CUSTOMER\n"
        findings = [f for f in self._findings(self._ledger(row, self._MYCOCOONS))
                    if "rule-E(g)" in f]
        self.assertTrue(any("SEED-X" in f and "nobody" in f for f in findings), findings)

    def test_unknown_class_in_evidence_sources_is_a_finding(self) -> None:
        sources = self._MYCOCOONS + "    ghost:\n      class: VENDOR\n      provenance: seed\n"
        findings = [f for f in self._findings(self._ledger("", sources)) if "rule-E(g)" in f]
        self.assertTrue(any("ghost" in f and "VENDOR" in f for f in findings), findings)

    def test_source_without_provenance_is_a_finding(self) -> None:
        sources = self._MYCOCOONS + "    silent:\n      class: CUSTOMER\n"
        findings = [f for f in self._findings(self._ledger("", sources)) if "rule-E(g)" in f]
        self.assertTrue(any("silent" in f and "provenance" in f for f in findings), findings)

    def test_bare_booleans_parse_like_pyyaml(self) -> None:
        text = "a: true\nb: false\nc: SELF-PILOT\n"
        parsed = content_qa._parse_simple_yaml(text)
        self.assertEqual({"a": True, "b": False, "c": "SELF-PILOT"}, parsed)
        try:
            import yaml  # type: ignore
        except ImportError:  # pragma: no cover
            self.skipTest("PyYAML not installed")
        self.assertEqual(yaml.safe_load(text), parsed)

    def test_self_test_arms_fire_and_clean_fixture_passes(self) -> None:
        expected, legal, clean = content_qa.run_evidence_class_self_test()
        for name in ("rule-E(e)", "rule-E(f)", "rule-E(g)", "rule-G"):
            self.assertTrue(any(name in k for k in expected), f"no seeded arm for {name}")
            self.assertTrue(any(name in k for k in legal), f"no legal probe for {name}")
        for name, fired in expected.items():
            self.assertTrue(fired, f"seeded violation MISSED: {name}")
        for name, quiet in legal.items():
            self.assertTrue(quiet, f"legal shape flagged: {name}")
        self.assertEqual([], clean, "\n".join(clean))


class EvidenceClassPageRuleTestCase(unittest.TestCase):
    """Rule G (`:: evidence-class ::`): a public figure labeled as a pilot /
    verified / benchmark RESULT needs a ledger row for that page whose
    evidence class is DESIGN-PARTNER or better. Self-pilot data drives
    calibration, never public claims (ruling S5)."""

    def test_result_labeled_figures_are_findings_without_partner_evidence(self) -> None:
        for probe in content_qa.EVIDENCE_CLASS_CAUGHT_PROBES:
            for pages in (None, set(), {"other.html"}):
                findings = [f for f in content_qa.check_file(
                    "probe.html", probe, evidence_pages=pages) if "evidence-class" in f]
                self.assertTrue(findings, f"pages={pages!r}: {probe}")

    def test_each_result_label_is_covered(self) -> None:
        for label in ("pilot result", "verified result", "benchmark result"):
            probe = f'<section id="s"><p>Merchants saw a 12% lift ({label}).</p></section>'
            findings = [f for f in content_qa.check_file("probe.html", probe)
                        if "evidence-class" in f]
            self.assertTrue(findings, label)

    def test_partner_or_customer_row_for_the_page_clears_the_figure(self) -> None:
        for probe in content_qa.EVIDENCE_CLASS_CAUGHT_PROBES:
            findings = [f for f in content_qa.check_file(
                "probe.html", probe, evidence_pages={"probe.html"}) if "evidence-class" in f]
            self.assertEqual([], findings, probe)

    def test_scenario_and_target_labels_are_not_rule_g_business(self) -> None:
        for probe in content_qa.EVIDENCE_CLASS_LEGAL_PROBES:
            findings = [f for f in content_qa.check_file("probe.html", probe)
                        if "evidence-class" in f]
            self.assertEqual([], findings, probe)

    def test_rule_g_reuses_the_number_label_window(self) -> None:
        far = ('<section id="s"><p>A pilot result.</p><p>'
               + content_qa._FILLER * 24 + 'Merchants saw a 12% lift.</p></section>')
        near = ('<section id="s"><p>A pilot result.</p><p>'
                + content_qa._FILLER * 4 + 'Merchants saw a 12% lift.</p></section>')
        self.assertEqual([], [f for f in content_qa.check_file("probe.html", far)
                              if "evidence-class" in f])
        self.assertTrue([f for f in content_qa.check_file("probe.html", near)
                         if "evidence-class" in f])

    def test_public_evidence_pages_resolve_through_class_and_tenant(self) -> None:
        doc = {
            "meta": {"evidence_sources": {
                "mycocoons": {"class": "SELF-PILOT", "provenance": "inference"},
                "partner1": {"class": "DESIGN-PARTNER", "provenance": "seed"}}},
            "claims": [
                {"id": "A", "page": "a.html", "evidence_class": "CUSTOMER"},
                {"id": "B", "page": "b.html", "evidence_class": "SELF-PILOT"},
                {"id": "C", "page": "c.html", "tenant": "partner1",
                 "evidence_class": "DESIGN-PARTNER"},
                {"id": "D", "page": "d.html", "tenant": "mycocoons",
                 "evidence_class": "CUSTOMER"},   # disagreement → lower wins
                {"id": "E", "page": "e.html"},
            ],
        }
        self.assertEqual({"a.html", "c.html"}, content_qa._public_evidence_pages(doc))


class EvidenceClassRealTreeTestCase(unittest.TestCase):
    """The real ledger and the real scoped surfaces under the new arms."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = (BASE_DIR / content_qa.LEDGER_REL).read_text(encoding="utf-8")
        cls.doc = content_qa._parse_simple_yaml(cls.text)

    def test_schema_block_documents_the_new_keys(self) -> None:
        head = "\n".join(self.text.splitlines()[:80])
        for key in ("evidence_class", "preview_flip", "tenant", "evidence_sources",
                    "SELF-PILOT", "DESIGN-PARTNER", "CUSTOMER"):
            self.assertIn(key, head, key)

    def test_mycocoons_is_recorded_as_an_inference_pending_owner_confirmation(self) -> None:
        sources = self.doc["meta"]["evidence_sources"]
        self.assertIn("mycocoons", sources)
        entry = sources["mycocoons"]
        self.assertIn(entry["class"], content_qa.VALID_EVIDENCE_CLASS)
        self.assertTrue(str(entry["provenance"]).strip(), "provenance must be stated")
        # Owner input pending confirmation (Part A finding 5): while the
        # provenance still says "inference", the class must be SELF-PILOT —
        # an inferred source never authorizes a public claim.
        if str(entry["provenance"]).startswith("inference"):
            self.assertEqual("SELF-PILOT", entry["class"])

    def test_no_real_row_flips_preview_from_below_the_floor(self) -> None:
        floor = content_qa.EVIDENCE_CLASS_RANK[content_qa.PUBLIC_CLAIM_MIN_CLASS]
        for row in self.doc["claims"]:
            if row.get("preview_flip") is True:
                cls = row.get("evidence_class")
                self.assertIn(cls, content_qa.VALID_EVIDENCE_CLASS, row["id"])
                self.assertGreaterEqual(content_qa.EVIDENCE_CLASS_RANK[cls], floor, row["id"])

    def test_machinery_rows_carry_no_evidence_class(self) -> None:
        # The 50 code/test-backed machinery rows are capability claims, not
        # pilot evidence; a class on one of them would be a claim about
        # provenance nobody measured. New rows may carry one when they are
        # pilot-evidence rows (preview_flip / tenant), never these.
        machinery = [r for r in self.doc["claims"]
                     if "preview_flip" not in r and "tenant" not in r]
        self.assertGreaterEqual(len(machinery), 50)
        for row in machinery:
            self.assertNotIn("evidence_class", row, row["id"])

    def test_no_scoped_surface_carries_a_result_labeled_figure_yet(self) -> None:
        findings = [f for f in content_qa.run_scan(BASE_DIR) if "evidence-class" in f]
        self.assertEqual([], findings, "\n".join(findings))

    def test_no_page_qualifies_for_public_result_claims_today(self) -> None:
        # Honest state on 2026-09-02: zero DESIGN-PARTNER / CUSTOMER rows, so
        # zero pages may carry a pilot/verified/benchmark-result figure. When a
        # partner readout lands, this assertion is expected to be UPDATED with
        # the citing row — never deleted.
        self.assertEqual(set(), content_qa.ledger_public_evidence_pages(BASE_DIR))
