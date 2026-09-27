#!/usr/bin/env python3
"""Truth-discipline content gate for the Signal rollout surfaces.

Runs in CI (deploy-homepage.yml, beside the design-canon guard) and in the
site test suite (tests/test_content_qa.py). Fails the build when any scoped
file violates the rollout's truth discipline:

  A. BANNED STRINGS — "mind-reading" and the guarantee family
     ("guarantee" / "guarantees" / "guaranteed") as affirmative claims
     (negated uses such as "not mind-reading" / "never a guaranteed outcome"
     are the discipline itself and stay legal), plus any present-tense claim
     that intent prediction / ORACLE — or net-yield pricing/bidding — is
     deployed for customers. Claim-ledger bans (signal-net-yield rollout,
     per docs/marketing/mizoki-shopify-net-yield-positioning.md §2):
     "Quokka Swarm" anywhere; Airbnb's published KL-divergence figures
     (4.95 → 0.66 / 0.04) in a section that does not attribute them to
     Airbnb; 15-minute-cycle / sub-second / sub-N-ms claims in a section
     without a "design target" label — every arm counts on sight, with no
     context test and no exemption list (see OBSERVED_PERF).
     HASHING TERMINOLOGY: identifier hashing described as "salt"/"salted"
     near SHA-256/hash/digest wording, in either order. The measurement
     rails use a KMS-managed pepper, not a per-record salt
     (services/measurement-rails/identity.py; the claims ledger says so in
     writing), so "salted SHA-256" claims a cryptographic property the code
     does not have.
     UNATTESTED COMPLIANCE ATTESTATIONS: SOC 2, ISO 27001/42001, HIPAA,
     PCI DSS and "GDPR compliant/certified" named without a negation or
     roadmap framing in the same clause. docs/product/SECURITY_PACKET_v1.md
     §9 records no SOC 2 report, no ISO certificate and no HIPAA scope, so
     the name alone is the claim (see ATTESTATION).
     The banned-string arms also run over the claims ledger's `claim:`
     text (check E's registry): the ledger row is what authorizes the page
     copy, so a banned phrasing there outlives every page fix.
  B. PREVIEW FRAMING — every section that mentions ORACLE / anticipatory or
     latent intent — or net yield / net contribution — must carry the
     "Preview · in development" framing string in that same section.
  C. NUMBER LABELING — every percentage or multiplier visible in a section
     must carry an honesty label WITHIN REACH of the figure: "illustrative"
     or "composite" for scenario numbers, "operating default" / "operating
     parameter" for real module parameters, or "design target" for intended-
     not-observed figures (TRUTH.md Article 2.4 — the label the B2 content
     pass stamped on blog/decision-control-plane.html and roi.html). "Within
     reach" means inside NUMBER_LABEL_WINDOW characters, or after an explicit
     scope banner that says the numbers which follow are illustrative /
     composite; one label no longer clears a whole section. Numbers inside
     <style>/<script> blocks and tag attributes are not customer-visible and
     are ignored.
  D. SECTION SEQUENCE — pages using the §-mark filing grammar must number
     their marks strictly 1..N with no gaps or duplicates. The grammar is
     rendered by three devices — .sec-mark (signal/shopify family), .filing
     and .folio (index.html) — all read in document order.
  F. DEAD INTERNAL LINKS — no scoped page may link to a path that app.py
     301-redirects to the homepage. Those links do not 404; they dead-end at
     "/", so a reader who clicks "ROI Calculator" lands on the homepage and
     the label is a claim about a page that is not served. The dead-end set
     is DERIVED FROM THE ROUTE TABLE (see dead_end_paths) — a view whose
     whole body is `redirect(url_for("home"), code=301)` — never from a
     hand-maintained list. Legitimate 301s are untouched by construction:
     /blogs.html → /blog and /blog/<slug>.html → /blog/<slug> redirect to
     their own canonical view, not to home, so they are never in the set.
     /logout is excluded on the same principled basis: it is a 302 action
     endpoint, not a permanently-moved content URL.
  E. UNBACKED CLAIMS — the machinery-claims ledger
     (docs/marketing/claims-ledger.yaml) must hold: every evidence path in a
     row exists on disk in the repo (E-a); every cited debt_id has a row in
     docs/BUILD_DEBT.md at the repo root (E-b); every row carries evidence
     or a debt_id — an unbacked machinery claim is illegal (E-c); every
     claim id required by meta.page_coverage exists as a ledger row (E-d).
     The ledger is parsed with a strict stdlib-only YAML-subset parser (CI
     runs this gate without third-party packages); the file stays valid
     YAML and the test suite cross-checks the parser against PyYAML when
     PyYAML is installed.
     EVIDENCE CLASS (WS-4, Strategy Resolution Plan v1.0 ruling S5, 2026-09-02):
     rows may carry `evidence_class` from the closed vocabulary SELF-PILOT /
     DESIGN-PARTNER / CUSTOMER (E-e); a row that AUTHORIZES dropping the
     "Preview · in development" framing (`preview_flip: true`) must be
     backed, must cite a pilot readout under docs/pilot/ or docs/reports/,
     and must carry a class of DESIGN-PARTNER or better — self-pilot data
     drives calibration, never public claims (E-f); a row's `tenant:` must
     name an entry of meta.evidence_sources, whose class it may not exceed,
     and every source entry carries a known class and a stated provenance
     (E-g). The effective class of a row is the LOWER of its own class and
     its source's — fail-closed.
  G. EVIDENCE CLASS ON PUBLIC FIGURES — a percentage / multiplier on a scoped
     page that is labeled as a RESULT ("pilot result", "verified result",
     "benchmark result" within NUMBER_LABEL_WINDOW) is a claim about
     measured provenance. It is a finding unless the ledger holds at least
     one row for that page whose effective evidence class is DESIGN-PARTNER
     or CUSTOMER. Scenario / target labels (illustrative, composite, design
     target, operating default) are rule C's business and are untouched
     here. Today rule C also rejects a result-labeled figure as unlabeled,
     so G is the provenance gate for the day rule C admits result labels —
     it is not a relaxation of C. Fail-closed: a scan that cannot read the
     ledger treats no page as qualified.

Scope is the explicit file list below: the rollout surfaces, the completion-run
expansion (2026-08-08), and the served-surface route audits of 2026-08-09. As
of the third audit pass there are NO scope hold-outs — every page app.py
serves to a customer is scanned. The three pages held out before it were
closed the way each one's own reason required: two by fixing the copy, and
marketing/signal.html (a rule false positive on its own honesty disclaimer) by
a bounded exemption that needs two independent conditions at once. A rule is
never loosened to admit a page.

Usage:
  python3 scripts/content_qa.py               # scan; exit 0 clean / 1 findings
  python3 scripts/content_qa.py --self-test   # prove the gate fires on seeded
                                              # violations and stays quiet on a
                                              # clean sample; exit 0 iff both
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from html import unescape
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]

# --- rule H: stat attribution (Run 1 item 1.D, 2026-09-02) -------------------
# ONE implementation, in scripts/mizoki_canon.py (rule V13), shared with the
# repo-root docs gate (scripts/check_canon_docs.py) so the two surfaces can
# never disagree about what "sourced" means. Loaded by path: this gate runs
# from a full checkout (ci.yaml content-truth-gate, deploy-homepage.yml), never
# from the site image. A missing module is a HARD failure — a gate that
# silently skips a rule defends nothing (rule 01).
import importlib.util as _ilu

_CANON_PATH = SITE_ROOT.parent / "scripts" / "mizoki_canon.py"
if not _CANON_PATH.is_file():
    raise SystemExit(f"content_qa: {_CANON_PATH} missing — rule H (stat attribution) cannot run; "
                     "run this gate from a full repository checkout")
_spec = _ilu.spec_from_file_location("mizoki_canon", _CANON_PATH)
mizoki_canon = _ilu.module_from_spec(_spec)
sys.modules.setdefault("mizoki_canon", mizoki_canon)  # dataclasses resolve the module by name
_spec.loader.exec_module(mizoki_canon)  # type: ignore[union-attr]

# Ratchet baseline for rule H on the served surfaces: pre-existing unsourced
# figures on canon-locked / owner-held copy, keyed by (path, normalized line)
# with a reason and an owner. Only ever shrinks.
STAT_BASELINE_REL = "scripts/stat_attribution_baseline.json"


def _stat_baseline(root: Path) -> dict[str, dict]:
    path = root / STAT_BASELINE_REL
    if not path.is_file():
        return {}
    import json as _json
    data = _json.loads(path.read_text(encoding="utf-8"))
    return {e["key"]: e for e in data.get("entries", [])}


def stat_key(rel_path: str, line: str) -> str:
    import hashlib as _h
    norm = " ".join(line.split()).lower()[:160]
    return f"{rel_path}::{_h.sha256(norm.encode()).hexdigest()[:16]}"


def check_stat_attribution(rel_path: str, visible_whole: str,
                           baseline: dict[str, dict] | None = None) -> list[str]:
    """Rule H — every external statistic on a customer surface carries an
    inline named source + month/year in the same sentence/element, or a
    TRUTH.md label saying it is not an external statistic."""
    findings: list[str] = []
    for f in mizoki_canon.stat_attribution_findings(visible_whole, rel_path, strict=False):
        key = stat_key(rel_path, f.line)
        if baseline and key in baseline:
            continue
        excerpt = " ".join(f.line.split())[:140]
        findings.append(
            f"{rel_path} :: stat-attribution :: line {f.line_no} carries a %/$ figure with no "
            f"inline named source + month/year and no illustrative/composite/design-target "
            f"label in the same sentence: …{excerpt}…")
    return findings


# The rollout's surfaces. Paths are relative to the site root.
SCOPE_FILES = [
    # The Next Dollar founder letters (owner-directed publication 2026-09-21).
    # Letter three revises the already-scoped doorman-problem.html.
    "blog/the-number-your-bank-account-reports.html",
    "blog/before-you-raise-bids-check-the-checkout.html",
    "blog/when-your-best-seller-loses-money.html",
    "blog/what-the-system-refuses-to-learn.html",
    "blog/the-decision-to-do-nothing.html",
    "blog/your-business-should-remember-why.html",
    "blog/when-media-becomes-a-business-decision.html",
    "blog/autonomy-is-earned.html",
    # Dedicated source for the public /intent application. The production
    # bundle is generated during deploy, so scan the authored customer copy.
    "intent-site/src/Home.tsx",
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
    # Customer-facing draft copy is scoped even before it is published anywhere.
    "docs/marketing/shopify-app-listing-copy.md",
    # docs/marketing/signal-story-bank.md is deliberately NOT scoped: it is the
    # rulebook these checks implement, so it must quote banned phrases to define
    # them ("no present-tense deployment claims until ORACLE is live") and is
    # not a served customer surface. The served surfaces it governs are all in
    # scope above.
    #
    # Completion-run scope expansion (2026-08-08): the classic surfaces, demo
    # desks, and blog posts the B2 content pass brought under the discipline.
    # docs/marketing/claims-ledger.yaml itself is NOT scoped — it is registry
    # data for rule E, not customer copy.
    "index.html",
    "pricing.html",
    # Growth-control v1.3 package (2026-08-19 gate-gap audit): the package tree
    # docs/marketing-growth-control-v1.3/ was committed (2242353) with ZERO
    # entries here, so CI reported green having never opened these files. The
    # two customer-facing pieces are scoped on the shopify-app-listing-copy
    # precedent above (draft customer copy is scoped even before it is
    # published anywhere); both scanned clean at scoping time. The other three
    # package files are deliberately NOT scoped, each for a stated reason:
    #   * CLAUDE_CODE_MASTER_PROMPT_MIZOKI3_MARKETING_GROWTH_CONTROL_v1_3.md is
    #     the workstream's rulebook — the signal-story-bank.md class: it must
    #     quote banned phrasings to define its own prohibitions ("guaranteed
    #     outcomes", the mind-reading denial), and scoping it fires check A/B
    #     on those definitions (9 measured false-positive-class findings).
    #   * MIZOKI3_Growth_Control_Website_Integration_Review_v1_3.md is the
    #     claims-integration decision memo — registry/rulebook material in the
    #     claims-ledger.yaml class, not customer copy (2 measured
    #     preview-framing hits on its own rule descriptions).
    #   * MIZOKI3_Growth_Control_Marketing_Package_v1_3.zip is binary; its four
    #     members were sha256-verified byte-identical to the loose files at
    #     scoping time, so the loose-file scans cover its content. Regenerate
    #     or delete the zip whenever a loose file changes — a text gate cannot
    #     see inside it.
    "docs/marketing-growth-control-v1.3/MIZOKI3_Growth_Control_Marketing_Visual_v1_3.html",
    "docs/marketing-growth-control-v1.3/MIZOKI3_Growth_Control_Marketing_Package_README_v1_3.md",
    # security.html and roi.html were scoped by the 2026-08-08 expansion but
    # neither is served: app.py's legacy_marketing_page() 301-redirects
    # /security.html and /roi.html to "/". Scanning a page no visitor can
    # reach spends gate budget on dead copy and lets the scope list drift out
    # of step with the route table, so they are out (2026-08-09 scope audit).
    "demo-capital.html",
    "demo-estate.html",
    "demo-risk.html",
    "demo-nexus.html",
    "blog/decision-control-plane.html",
    "blog/adc-decision-framework.html",
    "blog/relu-lens-meta-algorithm.html",
    "blog/index.html",
    "marketing/governance.html",
    # Scope audit against app.py's route table (2026-08-09): every remaining
    # served customer surface. walkthrough.html is the headline gap — it is
    # served at /walkthrough + /walkthrough.html, listed in sitemap.xml, and
    # canon-pinned, yet went unscanned since the gate shipped.
    "walkthrough.html",
    "privacy.html",
    "terms.html",
    "executive-briefing/index.html",
    # Scope-audit correction (2026-08-09, second pass): the first audit
    # claimed "every remaining served customer surface" while five root
    # division/demo pages served by app.py were neither scoped nor
    # mentioned — /counsel, /estate(.html), /capital(.html), /risk(.html)
    # and /demo/counsel (the other five demo desks WERE scoped). All five
    # scan clean, so there was never a cost to scoping them.
    "counsel.html",
    "estate.html",
    "capital.html",
    "risk.html",
    "demo-counsel.html",
    # Executive Demo r1.0 (2026-09-12), placed under /media r1.1 (2026-09-13):
    # served at /media/demo by app.py media_subpage (slug renamed 2026-09-14) (the closed-world
    # /media/<page> route) — scoped the day it landed, so the route table and
    # this list stay in step (a gate that does not cover a surface cannot
    # defend it). Single-file presenter surface; every status chip on it is
    # a claim this gate must be able to read.
    "media/demo.html",
    # Also served and also clean, scoped here so the route table and this
    # list stay in step: the console shell (app.py console_home, /console)
    # and the generic template route's index entry (app.py serve_template
    # via ALLOWED_TEMPLATES, /templates/index.html). Neither is marketing
    # copy, but "not marketing copy" is a reason to expect zero findings,
    # not a reason to leave a served surface unscanned.
    "mizoki3-site/console/index.html",
    "templates/index.html",
    # The /marketing parallel site (app.py marketing_division / the named
    # marketing_* routes). Scope hold-outs CLOSED 2026-08-09 (third pass) —
    # every served page here is now scanned. The three that were held out
    # were held out for two DIFFERENT reasons, and each was closed the way
    # its own reason required:
    #   * marketing/index.html and marketing/walkthrough.html carried a real
    #     violation — an unlabeled "40%" in their #video storyboard poster
    #     line. Fixed in the COPY ("CPA is up 40% — an illustrative
    #     scenario"), never in the rule.
    #   * marketing/signal.html was a RULE FALSE POSITIVE, not a violation.
    #     Its only hit was inside the page's "What we never say" honesty
    #     strip — &quot;Mind-reading.&quot; &quot;This account will buy.&quot;
    #     — a disclaimer listing the phrases the house refuses to use, where
    #     the negation is the heading above the list rather than the word
    #     before the phrase. Deleting that disclaimer to satisfy the gate
    #     would have made the page less honest. Closed by the bounded
    #     disclaimer-listing exemption (see _disclaimer_listing_spans), NOT
    #     by widening the arm's lookbehind: a lookbehind long enough to reach
    #     a heading would also excuse a real claim two clauses after any
    #     stray "never". The exemption needs BOTH conditions at once — the
    #     phrase must be inside quotation marks AND sit within 120 characters
    #     of a literal disclaimer heading — so prose under the heading, and
    #     quoted text anywhere else, both stay illegal.
    "marketing/index.html",
    "marketing/signal.html",
    "marketing/walkthrough.html",
    "marketing/capital.html",
    "marketing/counsel.html",
    "marketing/engine.html",
    "marketing/estate.html",
    "marketing/modules.html",
    "marketing/pricing.html",
    "marketing/risk.html",
    "marketing/simulator.html",
    # The /media standalone product site (app.py media_home / media_subpage).
    "media/index.html",
    "media/platform.html",
    "media/decision-graph.html",
    "media/how-it-works.html",
    "media/use-cases.html",
    "media/pilot.html",
    "media/trust.html",
    "media/resources.html",
    "media/contact.html",
    # The real lead path (app.py contact_page renders this template at
    # /contact + /contact.html), and the two sibling templates served at
    # /intelligence and /vision. Both of those carried unlabeled figures —
    # an "89%" automation figure on each, plus a "&lt;100ms" query-latency
    # tile on intelligence.html — and both were fixed in the COPY (the
    # metrics now carry TRUTH.md Article 2.4 "design target" labels) before
    # being scoped. A rule is never loosened to admit a page.
    "templates/contact.html",
    "templates/intelligence.html",
    "templates/vision.html",
]

# Pages that use the §-mark filing grammar (check D). index.html joined the
# list on 2026-08-09: it files its sections with the .folio / .filing devices
# rather than .sec-mark, so its sequence went unchecked while the page carried
# a duplicate §01.
SEC_MARK_PAGES = [
    "signal.html",
    "signal-thresholds.html",
    "signal-budget.html",
    "signal-creative.html",
    "signal-audiences.html",
    "signal-measurement.html",
    "shopify.html",
    "index.html",
]

# --- check A: banned strings -------------------------------------------------

# "mind-reading" is only legal when explicitly negated ("not mind-reading").
MIND_READING = re.compile(r"(?<!not )(?<!never )(?<!no )mind[\s-]?reading", re.I)
# The guarantee family is only legal when explicitly negated ("never a
# guaranteed outcome" is story-bank rule 5 verbatim). All three inflections
# count: "We guarantee the lift." and "A guarantee of incremental lift." are
# the same promise as "guaranteed lift" and were silent while the arm matched
# only the -ed form.
#
# ONE technical exemption, spelled out rather than left to a loose pattern:
# "regret guarantees" is the bandit-theory term of art on signal-creative.html
# ("upper-confidence-bound where regret guarantees matter") — a property of an
# algorithm's regret bound, not a promise to a customer. The exemption is a
# fixed-width lookbehind on the literal preceding word, so it cannot stretch to
# cover anything else.
GUARANTEED = re.compile(
    r"(?<!never a )(?<!not )(?<!no )(?<!nothing )(?<!regret )"
    r"\bguarantee(?:s|d)?\b",
    re.I,
)

# --- check A: bounded disclaimer-listing exemption ----------------------------
#
# The house claim strip on the /marketing division pages prints a "What we
# never say" cell that LISTS the phrases the house refuses to use:
#
#     What we never say
#     "Mind-reading."  "This account will buy."  Audio capture — ever.
#
# MIND_READING / GUARANTEED negate only on the word immediately before the
# phrase, so the arm fired on the honesty text itself and marketing/signal.html
# was held out of scope for it. Deleting a disclaimer to satisfy a gate makes
# the page LESS honest, so this is a rule defect, not a copy defect.
#
# It is NOT fixed by widening the lookbehind. A lookbehind long enough to reach
# the heading would also excuse a real claim two clauses after any stray
# "never" — that is the "narrow a rule to admit a false positive" failure the
# 2026-08-09 observed-performance narrowing already cost us once.
#
# The exemption instead requires TWO independent conditions at the same time:
#
#   1. the phrase is inside QUOTATION MARKS — it is a listed phrase, not a
#      sentence the page asserts; and
#   2. the quoted phrase opens within DISCLAIMER_WINDOW characters of a
#      literal disclaimer heading ("What we never say" and its inflections).
#
# Neither alone is enough, so the mechanism cannot be reused to hide a claim:
# prose written under the heading is still caught (condition 1 fails), and a
# quoted phrase anywhere else on the page is still caught (condition 2 fails).
# On the live pages the heading sits ~14 characters from the first quoted
# phrase and the whole disclaimer cell is ~150 characters long, so a 120-char
# window covers the listing and stops well short of the next block.
DISCLAIMER_HEADING = re.compile(
    r"what we (?:never|don't|do not|will never) say"
    r"|(?:things )?we never say"
    r"|what (?:we|this page) (?:never|won't|will not) claim",
    re.I,
)
DISCLAIMER_WINDOW = 120
# A listed phrase, in either quote style. Bounded length: a "quoted phrase"
# that runs on for a paragraph is prose wearing quotation marks.
DISCLAIMER_QUOTED = re.compile(r'"[^"\n]{0,160}"|“[^”\n]{0,160}”')


def _disclaimer_listing_spans(text: str) -> list[tuple[int, int]]:
    """Spans of quoted phrases listed directly under a disclaimer heading."""
    spans: list[tuple[int, int]] = []
    for heading in DISCLAIMER_HEADING.finditer(text):
        stop = min(heading.end() + DISCLAIMER_WINDOW, len(text))
        for quoted in DISCLAIMER_QUOTED.finditer(text, heading.end(), stop):
            spans.append((quoted.start(), quoted.end()))
    return spans
# Present-tense claims that intent prediction is customer-deployed. The intent
# platform runs in shadow, gated, labeled "built, pre-benchmark" — marketing
# copy may not promote it to a live product.
DEPLOYED_INTENT = [
    re.compile(r"intent (?:\w+ ){0,2}is (?:live|deployed|running|in production|shipping)", re.I),
    re.compile(r"ORACLE is (?:live|deployed|running|in production|shipping)", re.I),
    re.compile(r"(?:now|already) predict(?:s|ing) (?:\w+ )?intent", re.I),
    re.compile(r"intent (?:prediction|inference|scoring) (?:is )?(?:deployed|live|in production)", re.I),
]

# Present-tense claims that net-yield pricing/bidding/writeback is customer-
# deployed. The capability is scaffolded behind NET_YIELD_WRITEBACK=false and
# stays "Preview · in development" until a real pilot writes verified numbers.
DEPLOYED_NET_YIELD = [
    re.compile(r"net[\s-]?(?:yield|contribution)(?: \w+){0,2} is "
               r"(?:live|deployed|running|in production|shipping)", re.I),
    re.compile(r"(?:now|already) bid(?:s|ding)? on net[\s-]?contribution", re.I),
]

# O-1 prohibited-signal capability language (growth-control completion,
# 2026-08-19 — vocabulary-ratification ruling's KEEP-banned list). Keystroke
# dynamics, audio capture, gaze tracking, and fine-grained geolocation are
# schema-level prohibitions (O-1 / CONSTITUTION II.7) — copy may DENY them
# (the "What we never say" strips do, and denials stay legal), but may never
# present them as capability. Arm 1 catches an affirmative subject capturing/
# analyzing a prohibited family; arm 2 catches the family presented as a
# signal source ("keystroke dynamics power…"). Denial forms carry no
# capture-verb-before-family shape, so they do not match — proven both
# directions in the seeded probes below.
_O1_FAMILY = (
    r"(?:keystroke(?:s| dynamics| timing)?|typing (?:speed|cadence|rhythm|patterns)|"
    r"audio(?: signals?| streams?)?|microphone|voice input|"
    r"gaze(?:[\s-]tracking| point| direction)?|eye[\s-]tracking|"
    r"fine[\s-]grained (?:geo(?:location)?|location)|precise (?:geo(?:location)?|location))"
)
# The subject→verb and verb→family gaps refuse negation words, so denial copy
# ("we never capture gaze", "we capture no keystroke data") stays legal without
# a lookbehind that a real claim could hide behind.
_O1_NOT_NEGATED = r"(?:\s+(?!never\b|not\b|no\b|don'?t\b|won'?t\b|refus\w+\b|reject\w+\b|prohibit\w+\b)\w+)"
O1_CAPABILITY = [
    re.compile(
        r"(?:we|mizoki|signal|oracle|the (?:platform|system|engine|pixel|collector))"
        + _O1_NOT_NEGATED + r"{0,2}\s+"
        r"(?:captur|collect|record|analyz|track|process|ingest|monitor|listen)\w*"
        + _O1_NOT_NEGATED + r"{0,2}\s+" + _O1_FAMILY,
        re.I),
    re.compile(
        _O1_FAMILY + r"\s+(?:power|driv|fuel|feed|inform|enrich)\w*\s", re.I),
]

# Claim-ledger bans (positioning doc §2). "Quokka Swarm" is an unvalidated
# novelty term — banned outright on customer surfaces. The KL-divergence trio
# is Airbnb's published research: legal only in a section that names Airbnb.
# 15-minute cycles / sub-second / sub-N-ms latency are design targets, never
# observed performance — the section must say "design target". The sub-\d+ms
# arm was added 2026-08-08 (Phase A T6: "served sub-100ms" was invisible to
# the older regex).
QUOKKA = re.compile(r"quokka\s+swarm", re.I)

# Ratified product vocabulary (owner ruling 2026-08-19-A, Growth Control r2.0
# §7.1) — OFFICIAL on every surface, engineering and product copy alike. The
# canon linter carries the machine copy (scripts/mizoki_canon.py
# RATIFIED_VOCABULARY, both-direction guard tests/skills/
# test_canon_vocabulary.py); this served-site gate had NO such regression guard
# (FINISH_IT_STATUS_2026-09-02 §P-2.1). It is here as a REGRESSION GUARD, not a
# new ban: the terms are never flagged by content_qa's arms today, and this
# tuple + the self-test cases below fail the build if a future banned-string
# arm ever catches one — while proving the mirror property that ratification
# never upgrades a claim (a ratified term inside a banned claim is still caught).
RATIFIED_VOCABULARY = (
    "Decision Control Plane",
    "Decision Eligibility Layer",
    "DEL Score",
    "Growth Decision Graph",
    "Intent Engine v2",
    "ValidationPassport",
    "High-Value Decision Jobs",
)
AIRBNB_KL_HEADLINE = re.compile(r"\b4\.95\b")
KL_CONTEXT = re.compile(r"KL[\s-]?divergence", re.I)
KL_SECONDARY = re.compile(r"\b0\.66\b|\b0\.04\b")
AIRBNB_ATTRIBUTION = re.compile(r"airbnb", re.I)
#
# PERIMETER WIDENED 2026-08-09 (third pass). The arm read the claim as a
# STRING, so writing the same claim a different way walked straight past it.
# All four of these were MISSED and are now caught:
#   "Your first governed decision lands in under fifteen minutes."  (spelled)
#   "Median responses under 100ms."          (bare Nms, no sub-/< prefix)
#   "Signals are re-ranked on 15min cycles." (abbreviated unit)
#   "Reallocation lands within a quarter hour of a breach."  (spelled 15 min)
# This is a widening, not a narrowing: nothing the arm caught before is
# excused, and no exemption mechanism is added.
#
# The bare-milliseconds arm is the only one that carries a context test, and
# it carries one because "100ms" alone is a bare quantity that also appears in
# non-claims. It fires when a LATENCY CUE sits within 40 characters before the
# figure, on the same sentence (the [^.<>] bound). The cue list is latency
# nouns/verbs plus the four bounding prepositions that only ever precede a
# latency budget — deliberately NOT the bare preposition "in", which would
# make "subsystems in 100 ms" a violation and is the sort of over-reach that
# gets a rule narrowed later.
_LATENCY_CUE = (
    r"\b(?:latenc(?:y|ies)|respon(?:d|ds|se|ses|ding)|serv(?:e|es|ed|ing)"
    r"|return(?:s|ed|ing)?|answer(?:s|ed|ing)?|deliver(?:s|ed|ing|y)?"
    r"|round[\s-]?trip|p9[59]|decision(?:s)?|decide[sd]?|gate[sd]?"
    r"|arriv(?:e|es|ed|ing)|land(?:s|ed|ing)?|resolv(?:e|es|ed|ing)"
    r"|execut(?:e|es|ed|ion)|scor(?:e|es|ed|ing)"
    r"|complete[sd]?|under|within|below|at most|less than)\b"
)
OBSERVED_PERF = re.compile(
    # 15 minutes, in every spelling a reader actually sees
    r"15[\s-]?(?:minutes?|mins?)\b"
    r"|fifteen[\s-]?(?:minutes?|mins?)\b"
    r"|quarter[\s-](?:of[\s-]an[\s-])?hour\b"
    # sub-second / sub-N-ms / <N ms
    r"|sub[\s-]?second"
    r"|sub[\s-]?\d+\s*ms\b"
    r"|(?:&lt;|<)\s*\d+\s*ms\b"
    # bare "<N>ms" with a latency cue on either side of it, same sentence
    r"|" + _LATENCY_CUE + r"[^.<>]{0,40}?\b\d+\s*ms\b"
    r"|\b\d+\s*ms\b[^.<>]{0,30}?" + _LATENCY_CUE,
    re.I,
)
# EVERY arm counts on sight. There is deliberately no cadence-context test and
# no exemption list.
#
# History (2026-08-09, reverted the same day): the 15-minute arm was once
# narrowed to fire only when a cadence word sat within 80 characters, so that
# walkthrough.html's 30-minute meeting agenda would pass. That bought one
# agenda line at the price of a whole claim class — under the narrowed arm all
# four of these went SILENT:
#   "The full attribution rebuild completes in 15 minutes."
#   "Your first governed decision lands in under 15 minutes."
#   "Budget reallocation happens within 15 minutes of a threshold breach."
#   "From signal to spend change: 15 minutes."
# Every one is a latency claim; none names a cycle, refresh, or update. A
# context window cannot tell a latency promise from an agenda, and any opt-out
# broad enough to excuse the agenda is broad enough to hide those four. The
# agenda was reworded instead (walkthrough.html, the demo-FAQ answer), which is
# what "fix the copy, never the rule" means. Site-wide there is now no
# `15[ -]?minute` string outside this file's own documentation.
DESIGN_TARGET_LABEL = re.compile(r"design\s+target", re.I)


def _observed_perf_hit(text: str) -> bool:
    """True when the text states an unlabeled-performance-eligible figure."""
    return bool(OBSERVED_PERF.search(text))


# --- check A: hashing terminology --------------------------------------------

# The measurement rails hash identifiers with a KMS-managed PEPPER — one
# secret shared across records — not a per-record salt
# (services/measurement-rails/identity.py). The claims ledger says so in
# writing ("pepper, not per-record salt — keep that wording honest"), so
# customer copy that calls the construction "salted SHA-256" describes a
# cryptographic property the code does not have.
#
# Only the AFFIRMATIVE construction offends — "salted SHA-256", "hashed and
# salted", "the hashes are salted", "a salted digest", "hashed with a
# per-record salt". Contrastive and negated uses are the discipline itself and
# stay legal, exactly as the negated arms of MIND_READING / GUARANTEED do:
# "deliberately unsalted" (no word boundary inside "unsalted", so it never
# matches), "a held-back pepper, not a per-record salt", "a salt would zero the
# match rate". Every arm is bounded by [^.<>] so a match cannot span a sentence
# break or a tag — that bound is what keeps the negated forms legal, and it is
# why the arms stay directional/keyed to a connective instead of being a bare
# proximity test. A bare "salt within N chars of a hash word" arm would fire on
# the page's own honest sentence ("...both match on the SHA-256 of the
# normalized value and a salt would silently zero the match rate"), where the
# two words sit 31 characters apart inside a counterfactual.
#
# Blind spots closed 2026-08-09 — all four of these passed SILENTLY before,
# and "hashed and salted" is the single most common phrasing of the claim:
#   "Emails are hashed and salted before egress."      (arm 4)
#   "Identifiers are SHA-256, salted, and shared."     (arm 5)
#   "We use a salted digest of the email address."     (arm 1, digest added)
#   "The salt is applied to every SHA-256 identifier." (arm 1, window 20->40)
_HASHWORD = r"(?:sha[\s-]?-?256|sha256|hash(?:ed|ing|es)?|digest(?:ed|s)?)"
HASH_SALT = re.compile(
    # 1. "salted SHA-256", "salting of the hash", "a salted digest",
    #    "the salt is applied to every SHA-256 identifier"
    r"\bsalt(?:ed|ing)?\b[^.<>]{0,40}?\b" + _HASHWORD + r"\b"
    # 2. "the SHA-256 hashes are salted"
    r"|\b" + _HASHWORD + r"\b[^.<>]{0,40}?"
    r"\b(?:is|are|was|were|gets?|be)\s+(?:then\s+)?salted\b"
    # 3. "hashed with a per-record salt", "SHA-256 with a salt"
    r"|\b" + _HASHWORD + r"\b[^.<>]{0,30}?\bwith\s+(?:an?\s+|the\s+)?"
    r"(?:per[\s-]?record\s+|random\s+|unique\s+|secret\s+)?salt\b"
    # 4. conjunction, either order: "hashed and salted", "salted and hashed"
    r"|\b" + _HASHWORD + r"\b\s*(?:,\s*)?and\s+salted\b"
    r"|\bsalted\s+and\s+" + _HASHWORD + r"\b"
    # 5. appositive list: "SHA-256, salted, and shared"
    r"|\b" + _HASHWORD + r"\b\s*,\s*(?:and\s+)?salted\b",
    re.I,
)

# UNATTESTED COMPLIANCE ATTESTATIONS (2026-09-25, project close-out verdict).
# docs/product/SECURITY_PACKET_v1.md §9 is the platform's "not yet" list: row 2
# records no SOC 2 report (Type I or II) and no ISO 27001/42001 certificate;
# the deny-list keeps health data out of every store, so there is no HIPAA
# scope to be ready for. Yet the served footers of /blog, /walkthrough and two
# Journal articles said "SOC 2 Type II Certified • GDPR Compliant • HIPAA
# Ready" (live-measured 2026-09-25), and #1152 removed it from one page while
# nothing noticed the other three — no arm named the family. An attestation is
# a claim about an auditor's report or a regulated-data scope, so naming the
# framework IS the claim; the legal forms are the ones that say otherwise, a
# negation or a roadmap framing inside the same sentence, within
# ATTESTATION_DENIAL_WINDOW characters of the name.
# Stated scope, not a loosening: "GDPR" alone (subject erasure, the consent
# gate) and "GDPR-ready" describe mechanisms, not an attestation, and are not
# in this arm. Whether "GDPR-ready" is defensible before D-14 (EU residency)
# lands is an owner/counsel question the close-out verdict records; a text
# gate cannot decide it.
ATTESTATION = re.compile(
    r"\bSOC\s?2\b|\bISO(?:/IEC)?\s?(?:27001|42001)\b|\bHIPAA\b|\bPCI[\s-]?DSS\b"
    r"|\bGDPR[\s-](?:compliant|certified)\b",
    re.I,
)
# An audit OUTCOME is not a denial (#1159 review): "no exceptions", "without
# material findings" report a clean audit, which is the attestation claim
# itself. "no" and "without" stop counting as denials before those words.
_ATTESTATION_AUDIT_OUTCOME = (
    r"(?:any\s+)?(?:material\s+)?"
    r"(?:exceptions?|findings?|deviations?|qualifications?|weakness(?:es)?)\b")
ATTESTATION_DENIAL = re.compile(
    r"\b(?:no|without)\b(?!\s+" + _ATTESTATION_AUDIT_OUTCOME + r")"
    r"|\b(?:not|never|none|unattested|roadmap|planned)\b", re.I)
ATTESTATION_DENIAL_WINDOW = 60
# A sentence ends at terminal punctuation, a line break, or a list separator —
# the shipped footer strung three claims together with bullets, and a denial
# for one list item must not clear its neighbours.
_ATTESTATION_BREAKS = ".!?\n•·|"
# 2026-09-25 review follow-up (#1156, Codex + Copilot): inside one sentence a
# denial still qualifies only the framework in its OWN clause. "SOC 2 Type II
# certified, with no HIPAA scope" and "No SOC 2 report; GDPR Compliant" each
# carry one unattested claim that a sentence-wide window excused. A clause ends
# at ";" or ",", and at the conjunctions that join separate predicates. A colon
# ends the clause for a denial written BEFORE it; a denial right after a
# framework's own colon ("SOC 2: not attested") is that framework's label.
# Stated cost, the fail-closed direction: one denial opening a comma list ("No
# SOC 2, ISO 27001 or HIPAA attestation") no longer reaches past the comma, so
# a list of denials negates each item — the packet's own row already does
# ("No SOC 2 report (Type I or II), no ISO 27001/42001 certificate").
_ATTESTATION_CLAUSE = re.compile(r"[;,]|\s(?:and|but|while|whereas|with|plus|yet)\s", re.I)
# #1159 review (Codex): the label can carry a qualifier before its colon —
# "SOC 2 Type II: not attested", "ISO 27001 certification: not planned". Those
# words name the framework, so the colon still opens the label's answer. Only
# the SOC 2 type and label nouns qualify: an adjective that asserts the status
# ("certified", "compliant") ends the label, and the colon then ends the clause
# as before. The bound on this opt-out is _ATTESTATION_AUDIT_OUTCOME above:
# "SOC 2 Type II report: no exceptions" is a claim, not a denial.
_ATTESTATION_LABEL = re.compile(
    r"\s*(?:\(\s*type\s+(?:ii|i|2|1)\s*\)|type\s+(?:ii|i|2|1))?"
    r"(?:\s*\b(?:reports?|audits?|assessments?|certifications?|certificates?"
    r"|attestations?|compliance|scope|status|readiness|program(?:me)?)\b){0,2}\s*",
    re.I)


def attestation_hits(visible_whole: str) -> list[re.Match[str]]:
    """Every attestation name that no denial in its own clause qualifies."""
    hits: list[re.Match[str]] = []
    for m in ATTESTATION.finditer(visible_whole):
        before = visible_whole[max(0, m.start() - ATTESTATION_DENIAL_WINDOW): m.start()]
        after = visible_whole[m.end(): m.end() + ATTESTATION_DENIAL_WINDOW]
        before = before[max(before.rfind(c) for c in _ATTESTATION_BREAKS) + 1:]
        ends = [i for i in (after.find(c) for c in _ATTESTATION_BREAKS) if i != -1]
        if ends:
            after = after[: min(ends)]
        # Clause cut: keep only the text on this framework's side of the
        # nearest clause boundary, in each direction.
        cuts = list(_ATTESTATION_CLAUSE.finditer(before))
        if cuts:
            before = before[cuts[-1].end():]
        before = before[before.rfind(":") + 1:]
        cut = _ATTESTATION_CLAUSE.search(after)
        if cut:
            after = after[: cut.start()]
        colon = after.find(":")
        if colon != -1 and not _ATTESTATION_LABEL.fullmatch(after[:colon]):
            after = after[:colon]
        if ATTESTATION_DENIAL.search(before) or ATTESTATION_DENIAL.search(after):
            continue
        hits.append(m)
    return hits

# --- check B: preview framing ------------------------------------------------

INTENT_TRIGGER = re.compile(
    r"\bORACLE\b|anticipatory[\s-]intent|latent[\s-]intent"
    r"|intent[\s-](?:preview|inference|prediction|scoring|stages?)\b",
    re.I,
)
PREVIEW_FRAMING = re.compile(r"preview\s*(?:[·—–-]|&#183;|&middot;)\s*in development", re.I)

# Net-yield / net-contribution copy carries the same framing obligation as
# intent copy until the pilot flips the label (positioning doc claim ledger).
NET_YIELD_TRIGGER = re.compile(r"net[\s-]?yield|net[\s-]?contribution", re.I)

# --- check C: number labeling ------------------------------------------------

# A multiplier must not be followed by another digit: "2.4×" is a multiplier,
# the "5×" inside a "5×5 risk matrix" is a grid dimension.
NUMBER = re.compile(r"\d+(?:\.\d+)?\s?(?:%|×(?!\d))")
# "design target" joined the accepted vocabulary with the 2026-08-08 scope
# expansion: it is a first-class TRUTH.md Article 2.4 honesty label (already
# the required nearby-label for the observed-performance check above), and it
# is the label the landed B2 fixes stamped on the expanded pages. "estimate" /
# "projected" / "assumption" are deliberately NOT accepted — they are the
# vocabulary unlabeled scenario numbers hide behind.
NUMBER_LABEL = re.compile(
    r"illustrative|composite|operating default|operating parameter|design[\s-]target",
    re.I,
)

# SCOPE TIGHTENED 2026-08-09 (third pass). The label used to be SECTION-wide:
# one "operating default" anywhere in a <section> cleared every % and × in it,
# so an unlabeled figure added anywhere in that section was invisible. A
# section on these pages runs 2.4k–4.4k visible characters, which is a very
# large blast radius for one word.
#
# A figure is now labeled when EITHER:
#
#   (a) a label sits within NUMBER_LABEL_WINDOW characters of visible text on
#       either side of it — the reader takes the label in with the figure; or
#   (b) an explicit SCOPE BANNER appears earlier in the same section — a
#       sentence that actually says the numbers that follow are illustrative
#       or composite ("what follows is a composite scenario … the numbers in
#       it are illustrative", blog/doorman-problem.html; the "(composite
#       scenario · illustrative numbers)" heading on the Shopify listing
#       copy). A banner is a deliberate, reader-visible statement of scope,
#       which is exactly what a whole-section label ought to be.
#
# The bare words "operating default", "operating parameter" and "design
# target" can therefore NO LONGER clear a figure at a distance at all: they
# describe one figure, not a body of copy, so they only work inside the
# window. That is the specific hole this closes.
#
# WINDOW CALIBRATION — measured, not guessed. Across the scoped corpus the
# largest figure→label distance in copy that is already honest is 1257
# characters (executive-briefing/js/data.js, domain:signal, where the
# "(composite)" labels live in the proof array and the scenario figures in
# the signals array). Every scoped HTML page is far tighter: the worst is 459
# (index.html #control). The window is set at 1300 — the smallest value that
# keeps every currently-passing surface passing, so the rule is as tight as
# the corpus allows without rewriting copy that is not lying. It is a real
# reduction from section scope, and it is honestly a loose bound for HTML;
# lowering it to ~500 would fit every HTML page today and is the obvious next
# tightening once data.js carries per-figure labels.
NUMBER_LABEL_WINDOW = 1300
LABEL_BANNER = re.compile(
    r"(?:numbers?|figures?|metrics?)[^.<>\n]{0,80}?\b(?:are|is)\b"
    r"[^.<>\n]{0,40}?(?:illustrative|composite)"
    r"|(?:composite|illustrative)\s+(?:scenario|scenarios|field\s+note|example)"
    r"|illustrative\s+numbers?"
    r"|composite\s*·\s*illustrative",
    re.I,
)


def _unlabeled_numbers(text: str) -> list[str]:
    """Figures in `text` that carry no label within reach and no scope banner."""
    numbers = list(NUMBER.finditer(text))
    if not numbers:
        return []
    labels = [(m.start(), m.end()) for m in NUMBER_LABEL.finditer(text)]
    banners = [m.start() for m in LABEL_BANNER.finditer(text)]
    unlabeled: list[str] = []
    for figure in numbers:
        lo = figure.start() - NUMBER_LABEL_WINDOW
        hi = figure.end() + NUMBER_LABEL_WINDOW
        if any(start < hi and end > lo for start, end in labels):
            continue
        if any(start < figure.start() for start in banners):
            continue
        unlabeled.append(figure.group(0))
    return unlabeled

# --- check F: dead internal links --------------------------------------------
#
# app.py's legacy_marketing_page() 301-redirects ten legacy page URLs to "/".
# Links to them do not 404 and no crawler flags them — they simply dead-end at
# the homepage, so a "ROI Calculator" button silently becomes a homepage
# button and the label goes on claiming a page that is not served. Forty-one
# such links sat on scoped pages when this check was written.
#
# The dead-end set is DERIVED FROM THE ROUTE TABLE, per the gate-scope rule:
# a view whose entire body is `return redirect(url_for("home"), code=301)`.
# Two consequences, both deliberate:
#   * legitimate 301s can never be flagged. /blogs.html → /blog and
#     /blog/<slug>.html → /blog/<slug> redirect to their OWN canonical view,
#     not to home, so they are not in the set and are not findings.
#   * /logout is excluded on a stated basis rather than by accident: it is a
#     302 action endpoint, not a permanently-moved content URL, so requiring
#     `code=301` leaves it out.
APP_REL = "app.py"
_REDIRECT_HOME_301 = re.compile(
    r"((?:[ \t]*@app\.route\(\"[^\"]+\"\)[ \t]*\n)+)"
    r"[ \t]*def\s+\w+\([^)]*\)[^\n]*:\n"
    r"(?:[ \t]*(?:\"\"\".*?\"\"\"|'''.*?''')[ \t]*\n)?"
    r"[ \t]*return\s+redirect\(\s*url_for\(\s*[\"']home[\"']\s*\)\s*,"
    r"\s*code\s*=\s*301\s*\)",
    re.S,
)
_ROUTE_PATH = re.compile(r'@app\.route\("([^"]+)"\)')
HREF = re.compile(r'href="([^"]*)"', re.I)
_URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


def dead_end_paths(root: Path) -> set[str]:
    """Site paths app.py 301-redirects to the homepage (read from app.py)."""
    app_path = Path(root) / APP_REL
    if not app_path.is_file():
        return set()
    source = app_path.read_text(encoding="utf-8")
    dead: set[str] = set()
    for match in _REDIRECT_HOME_301.finditer(source):
        dead.update(_ROUTE_PATH.findall(match.group(1)))
    dead.discard("/")
    return dead


def check_dead_links(rel_path: str, raw: str, dead: set[str]) -> list[str]:
    """Rule F: no scoped page links to a path that dead-ends at the homepage."""
    if not dead or not rel_path.endswith(".html"):
        return []
    base = posixpath.dirname("/" + rel_path)
    findings: list[str] = []
    for match in HREF.finditer(raw):
        href = match.group(1).strip()
        if not href or href.startswith("#") or href.startswith("//"):
            continue
        if _URL_SCHEME.match(href):
            continue
        target = href.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        if not target.startswith("/"):
            target = posixpath.normpath(posixpath.join(base, target))
        if target in dead:
            findings.append(
                f"{rel_path} :: dead-link :: href=\"{href}\" resolves to "
                f"{target}, which app.py 301-redirects to \"/\" — the linked "
                f"page is not served, so the link label claims a page that "
                f"does not exist"
            )
    return findings


SEC_MARK = re.compile(r"§\s*(\d+)")

# The §-mark filing grammar is rendered by three devices. The signal/shopify
# family uses class="mark sec-mark" with the § as the element's own text;
# index.html files with .filing (§ nested one level down, in <span class="fno">)
# and .folio (§ as leading text, followed by a <span class="sub">). Matching
# only .sec-mark left index.html's sequence unchecked — and it carried a
# duplicate §01. The class attribute is multi-valued on the real pages, so the
# device name is matched anywhere inside it.
SEC_DEVICE_OPEN = re.compile(
    r'class="[^"]*\b(?:sec-mark|folio|filing)\b[^"]*"[^>]*>', re.I)
# Look this far past a device's opening tag for its § number. Large enough to
# reach through .filing's nested <span class="fno">, small enough that a device
# carrying no § never borrows the next device's number.
SEC_DEVICE_WINDOW = 240


def extract_sec_marks(raw: str) -> list[int]:
    """§-mark numbers in document order across every filing device."""
    opens = list(SEC_DEVICE_OPEN.finditer(raw))
    marks: list[int] = []
    for i, m in enumerate(opens):
        stop = opens[i + 1].start() if i + 1 < len(opens) else len(raw)
        window = raw[m.end(): min(stop, m.end() + SEC_DEVICE_WINDOW)]
        found = SEC_MARK.search(window)
        if found:
            marks.append(int(found.group(1)))
    return marks

# --- check E: unbacked machinery claims ---------------------------------------

# The ledger lives under the site root; BUILD_DEBT.md and every evidence path
# resolve against the REPO root (the site root's parent — true both when CI
# runs `--root "# MIZ OKI 3.5"` from the checkout and when the suite runs
# from the site directory).
LEDGER_REL = "docs/marketing/claims-ledger.yaml"
BUILD_DEBT_REL = "docs/BUILD_DEBT.md"
VALID_STATUS = {"backed", "debt"}

# --- check E(e)/E(f)/E(g) + check G: evidence class (WS-4, 2026-09-02) --------
#
# Ruling S5 (Strategy Resolution Plan v1.0): the ledger gains an evidence_class
# field; Preview labels flip only on DESIGN-PARTNER or better; self-pilot data
# drives calibration, never public claims. The vocabulary is CLOSED and RANKED
# — rank is what "or better" means, and the floor for any public claim is
# PUBLIC_CLAIM_MIN_CLASS.
VALID_EVIDENCE_CLASS = ("SELF-PILOT", "DESIGN-PARTNER", "CUSTOMER")
EVIDENCE_CLASS_RANK = {name: rank for rank, name in enumerate(VALID_EVIDENCE_CLASS)}
PUBLIC_CLAIM_MIN_CLASS = "DESIGN-PARTNER"
# A Preview-label flip is authorized only by a READOUT — a document under
# docs/pilot/ or docs/reports/ whose file name says so. Measured 2026-09-02:
# the tree holds NO such file (`find docs -iname "*readout*"` → nothing), so
# no flip row can pass today. That is the honest state, not a defect: the F4
# pilot is live-armed with no readout, and it is SELF-PILOT regardless.
_READOUT_DIRS = ("docs/pilot/", "docs/reports/")


def _is_readout_evidence(path: str) -> bool:
    """True when `path` is a pilot readout under docs/pilot/ or docs/reports/."""
    path = str(path).strip()
    if not path.startswith(_READOUT_DIRS):
        return False
    return "readout" in posixpath.basename(path).lower()


# Rule G's label: a figure presented as a measured RESULT. Deliberately does
# not overlap NUMBER_LABEL — scenario / target labels are rule C's business.
EVIDENCE_LABEL = re.compile(r"pilot result|verified result|benchmark result", re.I)


def _effective_evidence_class(row: dict, sources: dict) -> str | None:
    """The row's class, lowered to its tenant source's class when both exist.

    Fail-closed: an unknown class or an unknown source resolves to None, and a
    row that names a source but carries no class of its own resolves to the
    source's class (the source is the measurement; the row cannot outrank it).
    """
    own = row.get("evidence_class")
    own = str(own).strip() if own is not None else None
    if own is not None and own not in EVIDENCE_CLASS_RANK:
        return None
    tenant = row.get("tenant")
    if tenant is None:
        return own
    entry = sources.get(str(tenant).strip()) if isinstance(sources, dict) else None
    src_cls = entry.get("class") if isinstance(entry, dict) else None
    src_cls = str(src_cls).strip() if src_cls is not None else None
    if src_cls not in EVIDENCE_CLASS_RANK:
        return None
    if own is None:
        return src_cls
    return min(own, src_cls, key=EVIDENCE_CLASS_RANK.__getitem__)


def _public_evidence_pages(doc) -> set[str]:
    """Pages with >=1 ledger row whose effective class clears the public floor."""
    if not isinstance(doc, dict):
        return set()
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    sources = meta.get("evidence_sources") if isinstance(meta.get("evidence_sources"), dict) else {}
    floor = EVIDENCE_CLASS_RANK[PUBLIC_CLAIM_MIN_CLASS]
    pages: set[str] = set()
    for row in doc.get("claims") or []:
        if not isinstance(row, dict):
            continue
        cls = _effective_evidence_class(row, sources)
        if cls is not None and EVIDENCE_CLASS_RANK[cls] >= floor:
            page = str(row.get("page", "")).strip()
            if page:
                pages.add(page)
    return pages


def ledger_public_evidence_pages(root: Path) -> set[str]:
    """Rule G's page set, read once per scan. Unreadable ledger => no page
    qualifies (fail-closed); check_claims_ledger reports the parse error."""
    ledger_path = Path(root) / LEDGER_REL
    if not ledger_path.exists():
        return set()
    try:
        return _public_evidence_pages(
            _parse_simple_yaml(ledger_path.read_text(encoding="utf-8")))
    except ValueError:
        return set()


def _evidence_labeled_numbers(text: str) -> list[str]:
    """Figures in `text` with a result label within NUMBER_LABEL_WINDOW."""
    numbers = list(NUMBER.finditer(text))
    if not numbers:
        return []
    labels = [(m.start(), m.end()) for m in EVIDENCE_LABEL.finditer(text)]
    if not labels:
        return []
    labeled: list[str] = []
    for figure in numbers:
        lo = figure.start() - NUMBER_LABEL_WINDOW
        hi = figure.end() + NUMBER_LABEL_WINDOW
        if any(start < hi and end > lo for start, end in labels):
            labeled.append(figure.group(0))
    return labeled
# Debt ids are the first cell of BUILD_DEBT.md table rows: | GB-1 | … |
# Multi-segment ids (EXEC-LI-1, SHOP-DF-3, L5-CERT-1) are rows too — the
# earlier single-segment pattern silently skipped them, which made the
# both-directions cross-check report completeness it did not have.
DEBT_ROW = re.compile(r"^\|\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+)\s*\|", re.M)
_KEY_LINE = re.compile(r"^([A-Za-z0-9_./-]+):(?:\s+(.*))?$")
_INT = re.compile(r"-?\d+")


def _parse_simple_yaml(text: str):
    """Parse the strict YAML subset the claims ledger is written in.

    Stdlib-only by design: the deploy workflow runs this gate with a bare
    python3. Supported grammar — nested mappings on 2-space indents,
    "key: value" / "key:" openers, block lists ("- item", with mapping items
    written "- key: value" and continuation keys two spaces deeper), flow
    lists of bare scalars ("[A, B]"), double-quoted strings (\\" escaped),
    bare scalars (ids / paths / ints / lowercase true|false), and full-line
    comments. Anything
    outside the subset raises ValueError with a line number: a ledger the
    gate cannot fully parse must FAIL the gate, never pass by silence. The
    ledger stays valid YAML — tests/test_content_qa.py cross-checks this
    parser against PyYAML whenever PyYAML is importable.
    """
    entries: list[list] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:indent + 1]:
            raise ValueError(f"line {lineno}: tab indentation is not supported")
        entries.append([lineno, indent, stripped])
    if not entries:
        raise ValueError("ledger is empty")
    pos = 0

    def parse_scalar(token: str, lineno: int):
        token = token.strip()
        if token.startswith('"'):
            if len(token) < 2 or not token.endswith('"'):
                raise ValueError(f"line {lineno}: unterminated double-quoted string")
            body = token[1:-1]
            if re.search(r'(?<!\\)"', body):
                raise ValueError(f"line {lineno}: stray quote inside string")
            return body.replace('\\"', '"')
        if token.startswith("[") and token.endswith("]"):
            inner = token[1:-1].strip()
            if not inner:
                return []
            return [parse_scalar(part, lineno) for part in inner.split(",")]
        if any(ch in token for ch in "{}[]#\"'&*|>@`"):
            raise ValueError(f"line {lineno}: unsupported YAML syntax: {token!r}")
        if _INT.fullmatch(token):
            return int(token)
        # Bare lowercase booleans (WS-4, for `preview_flip: true|false`).
        # PyYAML reads these as bool, so the subset parser must too or the
        # agreement test would fail on the first flip row. Only the exact
        # lowercase spellings: "True"/"yes"/"on" stay plain scalars here and
        # are refused by rule E(f), which insists on a boolean.
        if token == "true":
            return True
        if token == "false":
            return False
        return token

    def parse_block(indent: int):
        if entries[pos][2].startswith("- "):
            return parse_list(indent)
        return parse_map(indent)

    def parse_map(indent: int):
        nonlocal pos
        result: dict = {}
        while pos < len(entries):
            lineno, ind, content = entries[pos]
            if ind < indent:
                break
            if ind > indent:
                raise ValueError(f"line {lineno}: unexpected indent")
            if content.startswith("- "):
                raise ValueError(f"line {lineno}: list item where a mapping key was expected")
            m = _KEY_LINE.match(content)
            if not m:
                raise ValueError(f"line {lineno}: expected 'key: value' or 'key:', got {content!r}")
            key, rest = m.group(1), m.group(2)
            if key in result:
                raise ValueError(f"line {lineno}: duplicate key {key!r}")
            pos += 1
            if rest is None:
                if pos >= len(entries) or entries[pos][1] <= indent:
                    raise ValueError(f"line {lineno}: key {key!r} opens an empty block")
                result[key] = parse_block(entries[pos][1])
            else:
                result[key] = parse_scalar(rest, lineno)
        return result

    def parse_list(indent: int):
        nonlocal pos
        items: list = []
        while pos < len(entries):
            lineno, ind, content = entries[pos]
            if ind < indent:
                break
            if ind > indent or not content.startswith("- "):
                raise ValueError(f"line {lineno}: malformed list item")
            rest = content[2:].strip()
            if not rest:
                raise ValueError(f"line {lineno}: bare '-' items are not supported")
            m = _KEY_LINE.match(rest)
            if m:
                # Mapping item: re-read this line as the item's first key at
                # the item body indent (dash column + 2), then parse the map.
                entries[pos] = [lineno, indent + 2, rest]
                items.append(parse_map(indent + 2))
            else:
                pos += 1
                items.append(parse_scalar(rest, lineno))
        return items

    doc = parse_block(entries[0][1])
    if pos != len(entries):
        raise ValueError(f"line {entries[pos][0]}: trailing unparsed content")
    return doc


def check_claims_ledger(root: Path, repo_root: Path | None = None) -> list[str]:
    """Rule E: every machinery claim is backed (code+tests on disk) or is
    labeled debt with a row in docs/BUILD_DEBT.md. Sub-classes:
      E(a) evidence path missing on disk;
      E(b) cited debt_id absent from BUILD_DEBT.md;
      E(c) row with neither evidence nor debt_id (structurally unbacked);
      E(d) claim id required by meta.page_coverage has no ledger row;
      E(e) evidence_class outside the closed vocabulary (WS-4);
      E(f) preview_flip: true without backed status + a readout evidence
           path + an effective class of DESIGN-PARTNER or better (WS-4);
      E(g) tenant naming an unknown meta.evidence_sources entry, a tenant
           row without its own evidence_class, a row class above its
           source's class, or a source entry with an unknown class or no
           provenance (WS-4).

    Check A's banned-string arms also run over each row's `claim:` text — the
    ledger row is the thing that authorizes the page copy, so a banned
    phrasing there survives the page fix (M2 carried "Salted SHA-256" for a
    full change set after signal-measurement.html had been corrected). Only
    `claim:` is linted, never `note:`: the note is the honesty commentary and
    must stay free to write "pepper, not per-record salt", the same exemption
    docs/marketing/signal-story-bank.md gets for quoting the phrases it bans.
    """
    findings: list[str] = []
    repo_root = repo_root if repo_root is not None else Path(root).resolve().parent
    ledger_path = Path(root) / LEDGER_REL
    if not ledger_path.exists():
        return [f"{LEDGER_REL} :: unbacked-claims :: machinery-claims ledger not found"]
    try:
        doc = _parse_simple_yaml(ledger_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{LEDGER_REL} :: unbacked-claims :: ledger unparseable ({exc})"]
    claims = doc.get("claims") if isinstance(doc, dict) else None
    if not isinstance(claims, list) or not claims:
        return [f"{LEDGER_REL} :: unbacked-claims :: ledger has no claims rows"]

    debt_path = repo_root / BUILD_DEBT_REL
    debt_ids = set(DEBT_ROW.findall(debt_path.read_text(encoding="utf-8"))) \
        if debt_path.exists() else set()

    # E(g) — meta.evidence_sources: source -> {class, provenance}. Read before
    # the row loop because tenant rows resolve against it.
    meta_pre = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    sources = meta_pre.get("evidence_sources")
    if sources is None:
        sources = {}
    elif not isinstance(sources, dict):
        findings.append(
            f"{LEDGER_REL} :: unbacked-claims :: rule-E(g) meta.evidence_sources is not "
            f"a mapping")
        sources = {}
    for src_name, entry in sources.items():
        if not isinstance(entry, dict):
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: rule-E(g) evidence source '{src_name}' "
                f"is not a mapping of class + provenance")
            continue
        src_cls = str(entry.get("class", "")).strip()
        if src_cls not in EVIDENCE_CLASS_RANK:
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: rule-E(g) evidence source '{src_name}' "
                f"has unknown class '{src_cls}' (expected one of "
                f"{'|'.join(VALID_EVIDENCE_CLASS)})")
        if not str(entry.get("provenance", "")).strip():
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: rule-E(g) evidence source '{src_name}' "
                f"states no provenance (how the class was established)")

    seen_ids: set[str] = set()
    for row in claims:
        if not isinstance(row, dict):
            findings.append(f"{LEDGER_REL} :: unbacked-claims :: non-mapping claims row: {row!r}")
            continue
        rid = str(row.get("id", "")).strip()
        if not rid:
            findings.append(f"{LEDGER_REL} :: unbacked-claims :: claims row without an id")
            continue
        if rid in seen_ids:
            findings.append(f"{LEDGER_REL} :: unbacked-claims :: duplicate claim id '{rid}'")
        seen_ids.add(rid)
        for field in ("page", "claim", "status"):
            if not str(row.get(field, "")).strip():
                findings.append(
                    f"{LEDGER_REL} :: unbacked-claims :: claim '{rid}' missing '{field}'")
        findings.extend(check_banned_strings(
            f"{LEDGER_REL} :: claim '{rid}'", str(row.get("claim", ""))))
        status = str(row.get("status", "")).strip()
        if status and status not in VALID_STATUS:
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: claim '{rid}' has unknown status "
                f"'{status}' (expected backed|debt)")
        evidence = row.get("evidence")
        if evidence is not None and not isinstance(evidence, list):
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: claim '{rid}' evidence is not a list")
            evidence = None
        evidence = [str(e) for e in (evidence or [])]
        debt_id = str(row.get("debt_id", "")).strip()

        # E(a) — every cited evidence path must exist in the repo.
        for ev in evidence:
            if not (repo_root / ev).exists():
                findings.append(
                    f"{LEDGER_REL} :: unbacked-claims :: rule-E(a) claim '{rid}' cites "
                    f"evidence missing on disk: {ev}")
        # E(b) — every cited debt id must be a row in BUILD_DEBT.md.
        if debt_id and debt_id not in debt_ids:
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: rule-E(b) claim '{rid}' cites debt id "
                f"'{debt_id}' absent from {BUILD_DEBT_REL}")
        # E(c) — a row must carry evidence or a debt label; and each status
        # must carry its own required field (backed→evidence, debt→debt_id).
        if (not evidence and not debt_id) or (status == "backed" and not evidence) \
                or (status == "debt" and not debt_id):
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: rule-E(c) claim '{rid}' has neither "
                f"required evidence nor a debt id — an unbacked machinery claim")

        # E(e) — evidence_class is a closed vocabulary.
        own_cls = row.get("evidence_class")
        own_cls = str(own_cls).strip() if own_cls is not None else None
        if own_cls is not None and own_cls not in EVIDENCE_CLASS_RANK:
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: rule-E(e) claim '{rid}' has unknown "
                f"evidence_class '{own_cls}' (closed vocabulary: "
                f"{' | '.join(VALID_EVIDENCE_CLASS)})")
        # E(g) — tenant resolves to a known source; the row carries its own
        # class and may not outrank the source's.
        tenant = row.get("tenant")
        if tenant is not None:
            tenant = str(tenant).strip()
            entry = sources.get(tenant)
            if not isinstance(entry, dict):
                findings.append(
                    f"{LEDGER_REL} :: unbacked-claims :: rule-E(g) claim '{rid}' names "
                    f"tenant '{tenant}' absent from meta.evidence_sources")
            elif own_cls is None:
                findings.append(
                    f"{LEDGER_REL} :: unbacked-claims :: rule-E(g) claim '{rid}' names "
                    f"tenant '{tenant}' but carries no evidence_class of its own")
            else:
                src_cls = str(entry.get("class", "")).strip()
                if (own_cls in EVIDENCE_CLASS_RANK and src_cls in EVIDENCE_CLASS_RANK
                        and EVIDENCE_CLASS_RANK[own_cls] > EVIDENCE_CLASS_RANK[src_cls]):
                    findings.append(
                        f"{LEDGER_REL} :: unbacked-claims :: rule-E(g) claim '{rid}' claims "
                        f"evidence_class '{own_cls}' above its tenant '{tenant}' source "
                        f"class '{src_cls}' — the effective class is the lower one")
        # E(f) — a Preview-label flip needs DESIGN-PARTNER or better, a backed
        # row, and a readout. Only `true` obligates; `false` is an explicit
        # non-flip; anything else is not a boolean and is refused.
        if "preview_flip" in row:
            flip = row.get("preview_flip")
            if flip is True:
                effective = _effective_evidence_class(row, sources)
                floor = EVIDENCE_CLASS_RANK[PUBLIC_CLAIM_MIN_CLASS]
                if effective is None:
                    findings.append(
                        f"{LEDGER_REL} :: unbacked-claims :: rule-E(f) claim '{rid}' sets "
                        f"preview_flip: true without a resolvable evidence_class — a "
                        f"Preview label flips only on {PUBLIC_CLAIM_MIN_CLASS} or better")
                elif EVIDENCE_CLASS_RANK[effective] < floor:
                    findings.append(
                        f"{LEDGER_REL} :: unbacked-claims :: rule-E(f) claim '{rid}' sets "
                        f"preview_flip: true from evidence_class '{effective}' — a "
                        f"Preview label flips only on {PUBLIC_CLAIM_MIN_CLASS} or better; "
                        f"self-pilot data drives calibration, never public claims")
                if status != "backed":
                    findings.append(
                        f"{LEDGER_REL} :: unbacked-claims :: rule-E(f) claim '{rid}' sets "
                        f"preview_flip: true on a row whose status is '{status}' — only "
                        f"a backed row can authorize a flip")
                if not any(_is_readout_evidence(ev) for ev in evidence):
                    findings.append(
                        f"{LEDGER_REL} :: unbacked-claims :: rule-E(f) claim '{rid}' sets "
                        f"preview_flip: true without a pilot readout in its evidence "
                        f"(a path under docs/pilot/ or docs/reports/ named *readout*)")
            elif flip is not False:
                findings.append(
                    f"{LEDGER_REL} :: unbacked-claims :: rule-E(f) claim '{rid}' has "
                    f"preview_flip {flip!r} — must be the bare boolean true or false")

    # E(d) — page coverage: every required claim id exists as a ledger row.
    meta = doc.get("meta") if isinstance(doc, dict) else None
    coverage = (meta or {}).get("page_coverage") or {}
    if not isinstance(coverage, dict):
        findings.append(f"{LEDGER_REL} :: unbacked-claims :: meta.page_coverage is not a mapping")
        coverage = {}
    for page, required in coverage.items():
        if not isinstance(required, list):
            findings.append(
                f"{LEDGER_REL} :: unbacked-claims :: page_coverage for '{page}' is not a list")
            continue
        for cid in required:
            if str(cid) not in seen_ids:
                findings.append(
                    f"{LEDGER_REL} :: unbacked-claims :: rule-E(d) page '{page}' requires "
                    f"claim id '{cid}' but the ledger has no such row")
    return findings


# Characters a reader cannot tell from an ASCII hyphen or space. Decoding
# "SHA&#8209;256" only gets as far as U+2011 NON-BREAKING HYPHEN, which the
# arms' ASCII "-" still misses — so the visible-text reducer folds the whole
# family down to what the reader actually sees. Soft hyphen renders as nothing
# at all and is deleted rather than folded. Every rule that cares about a dash
# already accepts "-" (PREVIEW_FRAMING lists it beside · — –), so folding
# cannot make a legal page illegal; it only removes places to hide.
_LOOKALIKES = {
    0x00AD: "",       # SOFT HYPHEN — invisible
    0x200B: "",       # ZERO WIDTH SPACE
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-",
    0x2015: "-", 0x2212: "-",
    0x00A0: " ", 0x202F: " ", 0x2009: " ",
}


def _fold_lookalikes(text: str) -> str:
    return text.translate(_LOOKALIKES)


def _strip_invisible_html(markup: str) -> str:
    """Reduce HTML to customer-visible text: drop style/script/comments/tags.

    Character references are decoded LAST — after tag removal, so decoding can
    never manufacture a tag. Without this step the gate reads the source bytes
    where the reader sees a character, and "Salted SHA&#8209;256" (a
    non-breaking hyphen, which renders as an ordinary "Salted SHA-256") slipped
    every hashing arm. Decoding also folds &quot;/&#183;/&#215; into the forms
    the other arms already match; OBSERVED_PERF keeps its explicit &lt; branch
    so it works on raw text too.
    """
    text = re.sub(r"<!--.*?-->", " ", markup, flags=re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return _fold_lookalikes(unescape(text))


def _sections(rel_path: str, raw: str) -> list[tuple[str, str]]:
    """Split a scoped file into (section_name, visible_text) chunks.

    HTML splits on <section> boundaries, Markdown on headings, and the
    briefing data.js on its top-level domain blocks — so "same section"
    matches how a reader actually encounters the copy.
    """
    if rel_path.endswith(".js"):
        marks = [(m.start(), m.group(1)) for m in re.finditer(r'id:\s*"(\w+)"', raw)]
        # keep only top-level domain ids (they repeat inside signals arrays;
        # the first occurrence of each unique id opens that domain's block)
        seen: dict[str, int] = {}
        for pos, name in marks:
            seen.setdefault(name, pos)
        bounds = sorted((pos, name) for name, pos in seen.items()
                        if re.search(r'\n  \w+: \{\s*\n\s*id: "' + name + '"', raw))
        if not bounds:
            return [("file", raw)]
        chunks: list[tuple[str, str]] = [("prelude", raw[: bounds[0][0]])]
        for i, (pos, name) in enumerate(bounds):
            end = bounds[i + 1][0] if i + 1 < len(bounds) else len(raw)
            chunks.append((f"domain:{name}", raw[pos:end]))
        return chunks
    if rel_path.endswith(".md"):
        parts = re.split(r"(?m)^(#{1,3} .+)$", raw)
        chunks = [("intro", parts[0])]
        for i in range(1, len(parts), 2):
            title = parts[i].strip("# ").strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            # The heading is customer-visible text of the section it opens, so
            # labels/framing carried in the heading count for that section.
            chunks.append((title, f"{title}\n{body}"))
        return chunks
    # HTML: chunk on <section boundaries; the head/nav before the first
    # section is its own chunk.
    pieces = re.split(r"(?=<section\b)", raw, flags=re.I)
    chunks = []
    for idx, piece in enumerate(pieces):
        m = re.search(r'id="([^"]+)"', piece[:200])
        name = m.group(1) if m else ("head" if idx == 0 else f"section-{idx}")
        chunks.append((name, _strip_invisible_html(piece)))
    return chunks


def check_banned_strings(rel_path: str, visible_whole: str) -> list[str]:
    """Check A's banned-string arms over already-visible text.

    Factored out of check_file so the same arms can run over the claims
    ledger's `claim:` text (see check_claims_ledger): the ledger row is what
    authorizes the page copy, so a banned phrasing that survives there
    outlives every page fix — which is exactly how "Salted SHA-256" stayed in
    the M2 row after the page it authorized had been corrected.
    """
    findings: list[str] = []
    # Quoted phrases listed directly under a "What we never say" heading are
    # the disclaimer, not the claim — see _disclaimer_listing_spans for why
    # this is a doubly-bounded exemption and not a loosened lookbehind.
    listed = _disclaimer_listing_spans(visible_whole)
    for pattern, label in ((MIND_READING, 'affirmative "mind-reading"'),
                           (GUARANTEED, 'affirmative "guarantee/guarantees/guaranteed"')):
        for m in pattern.finditer(visible_whole):
            if any(start <= m.start() and m.end() <= end for start, end in listed):
                continue
            ctx = visible_whole[max(0, m.start() - 40): m.end() + 40].strip()
            findings.append(f"{rel_path} :: banned-string :: {label}: …{' '.join(ctx.split())}…")
    for patterns, label in ((DEPLOYED_INTENT, "deployed-intent"),
                            (DEPLOYED_NET_YIELD, "deployed-net-yield")):
        for pattern in patterns:
            for m in pattern.finditer(visible_whole):
                ctx = visible_whole[max(0, m.start() - 40): m.end() + 40].strip()
                findings.append(
                    f"{rel_path} :: banned-string :: present-tense {label} claim: "
                    f"…{' '.join(ctx.split())}…"
                )
    for pattern in O1_CAPABILITY:
        for m in pattern.finditer(visible_whole):
            if any(start <= m.start() and m.end() <= end for start, end in listed):
                continue
            ctx = visible_whole[max(0, m.start() - 40): m.end() + 40].strip()
            findings.append(
                f"{rel_path} :: banned-string :: O-1 prohibited-signal capability "
                f"language (keystroke/audio/gaze/fine-geo presented as capability): "
                f"…{' '.join(ctx.split())}…"
            )
    for m in QUOKKA.finditer(visible_whole):
        ctx = visible_whole[max(0, m.start() - 40): m.end() + 40].strip()
        findings.append(
            f"{rel_path} :: banned-string :: \"Quokka Swarm\" (unvalidated novelty term): "
            f"…{' '.join(ctx.split())}…"
        )
    for m in HASH_SALT.finditer(visible_whole):
        ctx = visible_whole[max(0, m.start() - 40): m.end() + 40].strip()
        findings.append(
            f"{rel_path} :: hashing-terminology :: identifier hashing described as "
            f"salt/salted — the rails use a KMS-managed pepper, not a per-record salt "
            f"(services/measurement-rails/identity.py): …{' '.join(ctx.split())}…"
        )
    for m in attestation_hits(visible_whole):
        if any(start <= m.start() and m.end() <= end for start, end in listed):
            continue
        ctx = visible_whole[max(0, m.start() - 40): m.end() + 40].strip()
        findings.append(
            f"{rel_path} :: banned-string :: unattested compliance attestation — "
            f"docs/product/SECURITY_PACKET_v1.md §9 records no SOC 2 report, no ISO "
            f"27001/42001 certificate and no HIPAA scope: …{' '.join(ctx.split())}…"
        )
    return findings


def check_file(rel_path: str, raw: str,
               dead_paths: set[str] | None = None,
               evidence_pages: set[str] | None = None,
               stat_baseline: dict[str, dict] | None = None) -> list[str]:
    # `evidence_pages` is rule G's page set (ledger_public_evidence_pages).
    # None means "not supplied" and is FAIL-CLOSED: no page qualifies, so a
    # result-labeled figure is a finding — the same default rule F takes for
    # a missing dead-end set is a silent pass, and that is the wrong default
    # for a provenance gate.
    # `stat_baseline` is rule H's (stat attribution, Run 1 item 1.D) ratchet
    # baseline; None means "no held rows", which is the strict default.
    findings: list[str] = []
    visible_whole = _strip_invisible_html(raw) if rel_path.endswith(".html") else raw
    qualified = rel_path in (evidence_pages or set())

    # A — banned strings on visible text
    findings.extend(check_banned_strings(rel_path, visible_whole))

    # H — external statistics need an inline source + date (Run 1 item 1.D)
    findings.extend(check_stat_attribution(rel_path, visible_whole, stat_baseline))

    # F — internal links that dead-end at the homepage. Only run when the
    # caller supplied a route-table-derived set; there is no fallback list.
    if dead_paths:
        findings.extend(check_dead_links(rel_path, raw, dead_paths))

    # B + C — per section
    for name, text in _sections(rel_path, raw):
        if INTENT_TRIGGER.search(text) and not PREVIEW_FRAMING.search(text):
            findings.append(
                f"{rel_path} :: preview-framing :: section '{name}' mentions intent/ORACLE "
                f"without 'Preview · in development' framing"
            )
        if NET_YIELD_TRIGGER.search(text) and not PREVIEW_FRAMING.search(text):
            findings.append(
                f"{rel_path} :: preview-framing :: section '{name}' mentions net yield / "
                f"net contribution without 'Preview · in development' framing"
            )
        if (AIRBNB_KL_HEADLINE.search(text)
                or (KL_CONTEXT.search(text) and KL_SECONDARY.search(text))):
            if not AIRBNB_ATTRIBUTION.search(text):
                findings.append(
                    f"{rel_path} :: claim-ledger :: section '{name}' quotes the KL-divergence "
                    f"figures without attributing them to Airbnb's published research"
                )
        if _observed_perf_hit(text) and not DESIGN_TARGET_LABEL.search(text):
            findings.append(
                f"{rel_path} :: claim-ledger :: section '{name}' states 15-minute / "
                f"sub-second / sub-N-ms performance without a 'design target' label"
            )
        unlabeled = _unlabeled_numbers(text)
        if unlabeled:
            findings.append(
                f"{rel_path} :: number-label :: section '{name}' shows "
                f"{sorted(set(unlabeled))} with no illustrative/composite/"
                f"operating-default/design-target label within "
                f"{NUMBER_LABEL_WINDOW} characters and no scope banner ahead "
                f"of it"
            )
        # G — a figure labeled as a measured RESULT needs partner-or-better
        # evidence in the ledger for this page (WS-4, ruling S5).
        if not qualified:
            result_labeled = _evidence_labeled_numbers(text)
            if result_labeled:
                findings.append(
                    f"{rel_path} :: evidence-class :: section '{name}' presents "
                    f"{sorted(set(result_labeled))} as a pilot/verified/benchmark "
                    f"result, but the claims ledger has no row for this page with "
                    f"evidence_class {PUBLIC_CLAIM_MIN_CLASS} or better — self-pilot "
                    f"data never backs a public number"
                )

    # D — §-mark sequence across every filing device (.sec-mark / .folio /
    # .filing; see extract_sec_marks). Refuses to pass vacuously: a sec-mark
    # page where the extractor finds nothing is a broken extractor or a broken
    # page, never a pass. Duplicates and gaps both break strict 1..N.
    if rel_path in SEC_MARK_PAGES:
        marks = extract_sec_marks(raw)
        if not marks:
            findings.append(f"{rel_path} :: sec-sequence :: no §-marks extracted from a sec-mark page")
        elif marks != list(range(1, len(marks) + 1)):
            dupes = sorted({n for n in marks if marks.count(n) > 1})
            detail = f" (duplicated: {dupes})" if dupes else ""
            findings.append(
                f"{rel_path} :: sec-sequence :: §-marks not strictly 1..N: {marks}{detail}")
    return findings


def run_scan(root: Path = SITE_ROOT, repo_root: Path | None = None) -> list[str]:
    findings: list[str] = []
    # Rule F refuses to pass vacuously: app.py 301-redirects ten legacy page
    # URLs to "/", so an empty set means the extractor broke or the route
    # table moved — either way the check is not defending anything and must
    # say so rather than report a silent pass.
    dead = dead_end_paths(root)
    if not dead:
        findings.append(
            f"{APP_REL} :: dead-link :: no redirect-to-homepage routes extracted "
            f"— rule F cannot defend any surface in this state"
        )
    evidence_pages = ledger_public_evidence_pages(root)
    stat_baseline = _stat_baseline(root)
    for rel in SCOPE_FILES:
        path = root / rel
        if not path.exists():
            findings.append(f"{rel} :: missing :: scoped file not found")
            continue
        findings.extend(check_file(rel, path.read_text(encoding="utf-8"), dead,
                                   evidence_pages, stat_baseline))
    # The baseline only shrinks: a row whose line no longer fires is debris.
    live_keys = set()
    for rel in SCOPE_FILES:
        path = root / rel
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            vis = _strip_invisible_html(raw) if rel.endswith(".html") else raw
            live_keys.update(stat_key(rel, f.line) for f in mizoki_canon.stat_attribution_findings(vis, rel, strict=False))
    for key in sorted(set(stat_baseline) - live_keys):
        findings.append(f"{STAT_BASELINE_REL} :: stat-attribution :: stale baseline row {key} — remove it")
    findings.extend(check_claims_ledger(root, repo_root))
    return findings


# --- self-test ---------------------------------------------------------------

SEEDED_BAD = """<html><head><title>seed</title></head><body>
<section id="s1"><p class="mark sec-mark">§01</p>
<p>Our platform is pure mind-reading with guaranteed results.</p></section>
<section id="s2"><p class="mark sec-mark">§03</p>
<p>ORACLE is live and already predicting intent for every visitor.</p></section>
<section id="s3"><p>Customers see a 37% lift and 2.4× return.</p></section>
<section id="s4"><p>Net-yield bidding is live: our Quokka Swarm inspector
already bids on net-contribution for every store.</p></section>
<section id="s5"><p>KL divergence fell from 4.95 to 0.66 in our tests,
refreshed on 15-minute cycles.</p></section>
<section id="s6"><p>Every intent vector is served sub-100ms from the edge.</p></section>
<section id="s7"><p>Decisions gated in &lt;100ms at the boundary.</p></section>
<section id="s8"><p>Identities stitch across platforms through salted SHA-256
hashes of first-party identifiers.</p></section>
<section id="s9"><p>Emails are hashed and salted before egress.</p></section>
<section id="s10"><p>Identifiers are SHA-256, salted, and shared.</p></section>
<section id="s11"><p>We use a salted digest of the email address.</p></section>
<section id="s12"><p>The salt is applied to every SHA-256 identifier.</p></section>
<section id="s13"><p>We guarantee the lift.</p></section>
<section id="s14"><p>A guarantee of incremental lift.</p></section>
<section id="s15"><p>The full attribution rebuild completes in 15 minutes.</p></section>
<section id="s16"><p>Your first governed decision lands in under 15 minutes.</p></section>
<section id="s17"><p>Budget reallocation happens within 15 minutes of a threshold
breach.</p></section>
<section id="s18"><p>From signal to spend change: 15 minutes.</p></section>
<section id="s19"><p>Signals are re-ranked on 15-minute cycles.</p></section>
<section id="s20"><p>The standard demo is 30 minutes: 10 minutes on your
challenges, 15 minutes showing the platform, and 5 minutes on next steps.</p></section>
</body></html>"""

# F2 proof set, kept as data so the self-test can name each sentence in its
# output. The first four are LATENCY claims with no cadence word anywhere —
# the class the 2026-08-09 context narrowing silently admitted. The fifth is
# the cadence phrasing that always fired. All five must be CAUGHT.
PERF_LATENCY_PROBES = [
    "The full attribution rebuild completes in 15 minutes.",
    "Your first governed decision lands in under 15 minutes.",
    "Budget reallocation happens within 15 minutes of a threshold breach.",
    "From signal to spend change: 15 minutes.",
    "Signals are re-ranked on 15-minute cycles.",
]
# The one line the narrowing was built to admit. It is handled in the COPY —
# walkthrough.html's demo-FAQ answer no longer writes the figure as
# "15 minutes" — so the gate needs no exemption for it. Kept here as a
# regression probe: the reworded sentence must not trip the gate, and the
# original numeral form (in SEEDED_BAD §s20) must still be caught.
AGENDA_PROBE_REWORDED = (
    "The standard demo is 30 minutes: the first ten minutes understanding your "
    "challenges, the next fifteen showing the platform, and the last five "
    "discussing next steps."
)
# F6 proof set — the hashing phrasings that passed silently before, plus the
# negated/contrastive forms of the corrected page copy that must stay LEGAL.
HASH_SALT_PROBES = [
    "Emails are hashed and salted before egress.",
    "Identifiers are SHA-256, salted, and shared.",
    "We use a salted digest of the email address.",
    "The salt is applied to every SHA-256 identifier.",
]
HASH_SALT_LEGAL_PROBES = [
    "The outbound match key is deliberately unsalted, because Google and Meta "
    "both match on the SHA-256 of the normalized value and a salt would "
    "silently zero the match rate.",
    "Anything this platform stores or returns is keyed by a peppered SHA-256 "
    "instead — a held-back pepper, not a per-record salt.",
    "Identifiers are hashed with SHA-256 under a KMS-managed pepper.",
    "Our Salt Lake City desk runs the pilot.",
]
# F13 proof set — the uncovered inflections, and the bandit term of art on
# signal-creative.html that must stay legal.
GUARANTEE_PROBES = [
    "We guarantee the lift.",
    "A guarantee of incremental lift.",
    "Results are guaranteed.",
]
GUARANTEE_LEGAL_PROBES = [
    "Creative tests run as bandits — Thompson sampling by default, "
    "upper-confidence-bound where regret guarantees matter.",
    "Never a guaranteed outcome.",
]
# 2026-09-25 proof set — the attestation copy that shipped (footer and the
# executive-briefing chip), and the wordings that must stay LEGAL: the
# security packet's own absence row, negations, a roadmap framing, and the
# GDPR mechanism statements that are outside this arm by its stated scope.
ATTESTATION_PROBES = [
    "SOC 2 Type II Certified • GDPR Compliant • HIPAA Ready",
    "SOC 2 Type II",
    "Enterprise Compliance Standards: SOC 2 Type II, ISO 27001, HIPAA Compliant",
    "HIPAA-compliant data handling",
    "ISO/IEC 27001 certified infrastructure.",
    "PCI DSS compliant checkout.",
    "GDPR Compliant",
    "ISO 42001 certified infrastructure.",
    # #1159 review: a clean audit outcome is the claim, whichever side it sits.
    "SOC 2 Type II report: no exceptions.",
    "No exceptions in our SOC 2 Type II report.",
]
# The #1156 review counterexamples: an affirmative claim sharing a sentence with
# a denial of a DIFFERENT framework. Each must fire on the unqualified claim.
# The last one is the #1159 bound: "certified" ends the label, so the colon
# ends the clause and the HIPAA denial cannot excuse the SOC 2 claim.
ATTESTATION_CLAUSE_PROBES = [
    "SOC 2 Type II certified, with no HIPAA scope.",
    "No SOC 2 report; GDPR Compliant",
    "SOC 2 certified and no HIPAA scope.",
    "No SOC 2 report: GDPR certified.",
    "SOC 2 Type II certified: no HIPAA scope.",
]
ATTESTATION_LEGAL_PROBES = [
    "No SOC 2 report (Type I or II) and no ISO 27001/42001 certificate is on file.",
    "SOC 2 is not attested.",
    "We never ingest health data, so HIPAA does not apply.",
    "A SOC 2 Type II audit is on the roadmap.",
    "GDPR subject erasure runs through the governed canonical path.",
    "GDPR-ready consent gate.",
    "SOC 2: not attested.",
    "No SOC 2 report or HIPAA scope exists.",
    "HIPAA does not apply: no health data is stored.",
    "No SOC 2 report, no ISO 27001 certificate and no HIPAA scope.",
    # #1159 review (Codex): a qualified label keeps its colon answer.
    "SOC 2 Type II: not attested.",
    "ISO 27001 certification: not planned.",
    "SOC 2 (Type II) report: not attested.",
    "HIPAA scope: none.",
]
# F13 follow-up (2026-08-09, third pass): the bare -s inflection as an
# affirmative promise. GUARANTEE_PROBES covered "guarantee" and "guaranteed"
# as verbs/nouns but not "the platform guarantees X", which is the same claim.
GUARANTEE_PROBES.append("The platform guarantees incremental lift.")

# --- O-1 prohibited-signal capability probes (2026-08-19) ---------------------
# Both directions, per rule 01: the capability claim the arm must catch, and
# the denial/disclosure copy that carries the same family words and must stay
# legal — the live pages SAY "no audio, ever"; a rule that flags the denial
# would delete the honesty to satisfy the gate.
O1_CAPABILITY_PROBES = [
    "We capture keystroke dynamics to sharpen intent scores.",
    "The platform analyzes audio signals from every session.",
    "Signal tracks gaze direction across the viewport.",
    "Oracle collects fine-grained geolocation for household matching.",
    "The pixel records typing cadence during checkout.",
    "Keystroke dynamics power the hesitation model.",
    "Audio signals feed the intent graph.",
]
O1_CAPABILITY_LEGAL_PROBES = [
    "No keystroke dynamics, typing speed, or flight times — permanently prohibited.",
    "No audio, ever. Voice stays output-only on every surface.",
    "We never capture gaze, and fine-grained geolocation is rejected at the schema.",
    "Audio capture — ever.",  # the never-say strip's listed phrase
    "The O-1 lock rejects keystroke dynamics at the collector and at ingestion.",
]

# --- disclaimer-listing probes (2026-08-09, third pass) ----------------------
# The real /marketing claim strip, byte-for-byte from marketing/signal.html.
# It must stay LEGAL: it is the page telling the reader what it refuses to
# say. Deleting it to satisfy the gate would make the page less honest.
DISCLAIMER_LEGAL_PROBES = [
    '<div class="claim-cell never"><span class="tag">What we never say</span>'
    '<p>&quot;Mind-reading.&quot; &quot;This account will buy.&quot; Audio '
    'capture — ever. Predictions are probabilities, not promises.</p></div>',
    '<div class="claim-cell never"><span class="tag">What we never say</span>'
    '<p>&quot;Guaranteed lift.&quot; Targets are labeled targets, everywhere '
    'on this site.</p></div>',
]
# …and the exemption must NOT be reusable to hide a real claim. Each of these
# carries the same disclaimer heading and must still be CAUGHT — the first
# two because the claim is prose rather than a quoted listed phrase, the last
# because the quoted phrase sits outside the heading's 120-character window.
DISCLAIMER_CAUGHT_PROBES = [
    ('<p>What we never say: &quot;Mind-reading.&quot;</p>'
     '<p>Our targeting is mind-reading once the graph warms up.</p>'),
    ('<p>What we never say: &quot;This account will buy.&quot;</p>'
     '<p>We guarantee the lift.</p>'),
    ('<p>What we never say: &quot;Mind-reading.&quot;</p>'
     '<p>' + ('Filler copy that pushes the next quotation well past the '
              'heading window. ') * 4 + '&quot;Mind-reading&quot; is exactly '
     'what our graph does.</p>'),
]

# --- observed-performance perimeter probes (2026-08-09, third pass) ----------
# The four evasions the arm MISSED: the claim written with a spelled cardinal,
# an abbreviated unit, a bare millisecond figure, and "quarter hour".
PERF_EVASION_PROBES = [
    "Your first governed decision lands in under fifteen minutes.",
    "Median responses under 100ms.",
    "Signals are re-ranked on 15min cycles.",
    "Reallocation lands within a quarter hour of a breach.",
    # cue on the trailing side of the figure
    "Every intent vector arrives in 100ms.",
    "100ms p95 on the scoring path.",
]
# Copy that must stay LEGAL. The first is the reworded demo agenda already in
# walkthrough.html (it spells "fifteen" with no unit after it, so the spelled
# arm must not reach it). The rest guard the bare-milliseconds arm's context
# test — including the two negative probes the suite has asserted since the
# sub-N-ms arm shipped, which a cue list containing bare "in" would have
# turned into violations.
PERF_LEGAL_PROBES = [
    AGENDA_PROBE_REWORDED,
    "The board meets for a quarter of the year on this.",
    "subsystems in 100 ms",
    "the submarine",
    "Fifteen analysts reviewed the ledger.",
    "We closed 15 minor findings this quarter.",
]

# --- number-label scope probes (2026-08-09, third pass) ----------------------
# A section whose label sits far from a newly added figure. Under the old
# section-wide scope the "operating default" sentence cleared the 34% no
# matter how far away it was; the figure is now CAUGHT.
_FILLER = ("Filler prose that carries no figure and no honesty label at all, "
           "repeated to push the label out of reach of the number. ")
NUMBER_SCOPE_CAUGHT = (
    '<section id="scope"><p>The 10% daily cap is an operating default.</p>'
    '<p>' + _FILLER * 24 + 'Customers see a 34% lift.</p></section>'
)
# …and the same section with the figure inside the window stays LEGAL.
NUMBER_SCOPE_LEGAL_NEAR = (
    '<section id="scope"><p>The 10% daily cap is an operating default.</p>'
    '<p>' + _FILLER * 4 + 'Customers see a 34% lift.</p></section>'
)
# A scope banner — a sentence that actually declares what follows — covers a
# figure past the window, which is what a whole-section label ought to mean.
NUMBER_SCOPE_LEGAL_BANNER = (
    '<section id="scope"><p>What follows is a composite scenario and the '
    'numbers in it are illustrative.</p>'
    '<p>' + _FILLER * 24 + 'Customers see a 34% lift.</p></section>'
)

# --- stat-attribution probes (Run 1 item 1.D, 2026-09-02) — cases 81–88 ------
# Four must be CAUGHT (an external %/$ figure with no inline source + date and
# no honesty label) and four must stay LEGAL (sourced + dated, or labelled).
STAT_ATTRIBUTION_CAUGHT_PROBES = [
    "19.3% of online sales were returned in 2025.",                                   # 81
    "Retail media will reach $65B this year.",                                        # 82
    "About 40% of queries now begin in an AI answer engine.",                         # 83
    "Returns of 25–40% in apparel are an industry statistic, not a customer result.", # 84
]
STAT_ATTRIBUTION_LEGAL_PROBES = [
    "19.3% of online sales were returned in 2025 (NRF / Happy Returns, Oct 2025).",  # 85
    "Traditional search volume will fall 25% by 2026, according to Gartner (Feb 2024).",  # 86
    "Customers see a 37% lift (illustrative scenario).",                              # 87
    "$849.9B in merchandise was returned in 2025 (NRF, Dec 2025).",                   # 88
]

# --- dead-link probes (2026-08-09, third pass) -------------------------------
# Seeded against a seeded route table, so the probe never depends on app.py.
DEAD_LINK_SEEDED_PATHS = {"/roi.html", "/case-studies.html"}
DEAD_LINK_CAUGHT_PROBE = (
    '<a href="/roi.html">ROI Calculator</a>'
    '<a href="../case-studies.html">Case Studies</a>'
)
# Legitimate 301s (/blogs.html → /blog), live routes, in-page anchors,
# off-site links and non-http schemes must all stay legal.
DEAD_LINK_LEGAL_PROBE = (
    '<a href="/blogs.html">Blog</a><a href="/pricing">Pricing</a>'
    '<a href="/blog/decision-control-plane.html">Field note</a>'
    '<a href="#roi">Jump to ROI</a>'
    '<a href="https://example.com/roi.html">Somebody else\'s calculator</a>'
    '<a href="mailto:hello@mizoki3.com?subject=roi.html">Mail us</a>'
)

# index.html files its sections with .filing and .folio rather than .sec-mark.
# Seeded duplicate: §01 appears twice (the real defect the extractor extension
# was written to catch), so the sequence is [1, 1, 2] — not strictly 1..N.
SEEDED_DUP_SECTIONS = """<html><head><title>seed</title></head><body>
<div class="filing"><span class="fno">§01</span><span class="sep">/</span><span>THE SYSTEM</span></div>
<section id="a"><div class="folio reveal">§01<span class="sub">WHAT IT IS</span></div>
<p>Body copy.</p></section>
<section id="b"><div class="folio reveal">§02<span class="sub">THE REFLEX ARC</span></div>
<p>Body copy.</p></section>
</body></html>"""

# The same devices, correctly numbered: proves the extended extractor reads
# .filing and .folio in document order and passes a well-formed page.
SEEDED_DEVICE_CLEAN = """<html><head><title>seed</title></head><body>
<div class="filing"><span class="fno">§01</span><span class="sep">/</span><span>THE SYSTEM</span></div>
<section id="a"><div class="folio reveal">§02<span class="sub">WHAT IT IS</span></div>
<p>Body copy.</p></section>
<section id="b"><div class="folio reveal">§03<span class="sub">THE REFLEX ARC</span></div>
<p>Body copy.</p></section>
<div class="filing"><span class="fno">§04</span><span class="sep">/</span><span>OUTCOMES</span></div>
</body></html>"""

SEEDED_CLEAN = """<html><head><title>seed</title></head><body>
<section id="s1"><p class="mark sec-mark">§01</p>
<p>Anticipatory intent — not mind-reading. Preview · in development.</p>
<p>Never a guaranteed outcome.</p></section>
<section id="s2"><p class="mark sec-mark">§02</p>
<p>A composite scenario: 37% of spend was non-incremental (illustrative).</p>
<p>The 10% daily cap is an operating default.</p></section>
<section id="s3"><p>Net contribution pricing — Preview · in development —
runs on a 15-minute cycle as a design target, not observed performance,
designed for sub-100 ms responses and &lt;100 ms gating (design target,
not measured serving).
Airbnb's published research reported KL divergence of 4.95 falling to 0.66;
those are Airbnb's figures, never quoted as ours.</p></section>
<section id="s4"><p>The standard demo is 30 minutes: the first ten minutes understanding
your challenges, the next fifteen showing the platform, and the last five
discussing next steps.</p>
<p>Identifiers are hashed with SHA-256 under a KMS-managed pepper.</p>
<p>The outbound match key is deliberately unsalted, because the platforms
match on the SHA-256 of the normalized value and a salt would silently zero
the match rate. Anything stored is keyed by a peppered SHA-256 instead — a
held-back pepper, not a per-record salt.</p>
<p>Our Salt Lake City desk runs the pilot.</p></section>
</body></html>"""

# Rule-E self-test fixtures. Seeded into TEMP COPIES only — the self-test
# never reads or mutates the real ledger / BUILD_DEBT.md. The bad ledger
# carries exactly one violation per sub-class (a/b/c/d) plus one healthy row;
# the clean ledger must produce zero findings against the same temp repo.
RULE_E_SEEDED_BAD_LEDGER = """\
meta:
  version: 1
  page_coverage:
    signal-measurement.html: [SEED-OK, SEED-UNCOVERED]
claims:
  - id: SEED-A
    page: signal-measurement.html
    claim: "seed: backed row citing a nonexistent evidence path"
    status: backed
    evidence:
      - services/does-not-exist/nowhere.py
  - id: SEED-B
    page: signal-measurement.html
    claim: "seed: debt row citing a debt id absent from BUILD_DEBT.md"
    status: debt
    debt_id: ZZ-99
  - id: SEED-C
    page: signal-measurement.html
    claim: "seed: row with neither evidence nor debt id"
    status: backed
  - id: SEED-S
    page: signal-measurement.html
    claim: "Salted SHA-256 identity stitching"
    status: backed
    evidence:
      - seed_module.py
  - id: SEED-OK
    page: signal-measurement.html
    claim: "seed: healthy backed row"
    status: backed
    evidence:
      - seed_module.py
      - seed_module_test.py
"""

RULE_E_SEEDED_CLEAN_LEDGER = """\
meta:
  version: 1
  page_coverage:
    signal-measurement.html: [SEED-OK, SEED-DEBT]
claims:
  - id: SEED-OK
    page: signal-measurement.html
    claim: "seed: backed row with code and test evidence on disk"
    status: backed
    evidence:
      - seed_module.py
      - seed_module_test.py
  - id: SEED-DEBT
    page: signal-measurement.html
    claim: "seed: labeled-debt row listed in BUILD_DEBT.md"
    status: debt
    debt_id: XY-1
"""

RULE_E_SEEDED_BUILD_DEBT = """\
# seeded BUILD_DEBT for --self-test (temp copy)
| debt_id | what is missing |
|---|---|
| XY-1 | seed debt row |
"""


def _seed_rule_e_tree(repo: Path, ledger_text: str) -> Path:
    """Materialize a temp repo+site tree carrying a seeded ledger; return site root."""
    site = repo / "site"
    (site / "docs" / "marketing").mkdir(parents=True)
    (site / LEDGER_REL).write_text(ledger_text, encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / BUILD_DEBT_REL).write_text(RULE_E_SEEDED_BUILD_DEBT, encoding="utf-8")
    (repo / "seed_module.py").write_text("# seed evidence\n", encoding="utf-8")
    (repo / "seed_module_test.py").write_text("# seed evidence test\n", encoding="utf-8")
    return site


def run_rule_e_self_test() -> tuple[dict[str, bool], list[str]]:
    """Prove rule E fires on each seeded sub-class and stays quiet when clean.

    Returns (sub-class -> fired, findings-on-clean-fixture).
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad_repo = Path(td) / "bad"
        bad = check_claims_ledger(_seed_rule_e_tree(bad_repo, RULE_E_SEEDED_BAD_LEDGER),
                                  bad_repo)
        clean_repo = Path(td) / "clean"
        clean = check_claims_ledger(_seed_rule_e_tree(clean_repo, RULE_E_SEEDED_CLEAN_LEDGER),
                                    clean_repo)
    fired = {
        "rule-E(a) evidence path missing on disk": any("rule-E(a)" in f for f in bad),
        "rule-E(b) debt id absent from BUILD_DEBT.md": any("rule-E(b)" in f for f in bad),
        "rule-E(c) neither evidence nor debt id": any("rule-E(c)" in f for f in bad),
        "rule-E(d) required claim id uncovered": any("rule-E(d)" in f for f in bad),
        "banned string in a ledger claim: field": any(
            "hashing-terminology" in f and "SEED-S" in f for f in bad),
    }
    return fired, clean


# --- evidence-class fixtures (WS-4, 2026-09-02) -------------------------------
# Seeded into TEMP COPIES only, like the rule-E fixtures. The bad ledger
# carries one violation per new sub-class (E-e, each E-f arm, each E-g arm)
# on separately named rows so the self-test can name the arm that missed.
SEEDED_READOUT_REL = "docs/pilot/SEED_PILOT_READOUT.md"

_EC_ROW_HEAD = (
    "    page: signal-measurement.html\n"
    "    status: backed\n"
    "    evidence:\n"
    "      - seed_module.py\n"
    "      - seed_module_test.py\n"
    "      - " + SEEDED_READOUT_REL + "\n"
)
EVIDENCE_CLASS_SEEDED_BAD_LEDGER = (
    "meta:\n"
    "  version: 1\n"
    "  page_coverage:\n"
    "    signal-measurement.html: [SEED-OK]\n"
    "  evidence_sources:\n"
    "    mycocoons:\n"
    "      class: SELF-PILOT\n"
    "      provenance: inference-2026-09-01-part-a-finding-5-owner-confirmation-pending\n"
    "    ghost:\n"
    "      class: VENDOR\n"
    "      provenance: seed\n"
    "    silent:\n"
    "      class: CUSTOMER\n"
    "claims:\n"
    "  - id: SEED-OK\n"
    "    page: signal-measurement.html\n"
    "    claim: \"seed: healthy backed row\"\n"
    "    status: backed\n"
    "    evidence:\n"
    "      - seed_module.py\n"
    "      - seed_module_test.py\n"
    "  - id: SEED-E\n"
    "    claim: \"seed: unknown evidence class\"\n"
    + _EC_ROW_HEAD +
    "    evidence_class: PILOT\n"
    "  - id: SEED-F1\n"
    "    claim: \"seed: flip sourced from self-pilot\"\n"
    + _EC_ROW_HEAD +
    "    evidence_class: SELF-PILOT\n"
    "    preview_flip: true\n"
    "  - id: SEED-F2\n"
    "    claim: \"seed: flip with no class at all\"\n"
    + _EC_ROW_HEAD +
    "    preview_flip: true\n"
    "  - id: SEED-F3\n"
    "    page: signal-measurement.html\n"
    "    claim: \"seed: flip without a readout path\"\n"
    "    status: backed\n"
    "    evidence:\n"
    "      - seed_module.py\n"
    "      - seed_module_test.py\n"
    "    evidence_class: CUSTOMER\n"
    "    preview_flip: true\n"
    "  - id: SEED-F4\n"
    "    page: signal-measurement.html\n"
    "    claim: \"seed: flip on a debt row\"\n"
    "    status: debt\n"
    "    debt_id: XY-1\n"
    "    evidence:\n"
    "      - " + SEEDED_READOUT_REL + "\n"
    "    evidence_class: CUSTOMER\n"
    "    preview_flip: true\n"
    "  - id: SEED-F5\n"
    "    claim: \"seed: flip that is not a boolean\"\n"
    + _EC_ROW_HEAD +
    "    evidence_class: CUSTOMER\n"
    "    preview_flip: maybe\n"
    "  - id: SEED-G1\n"
    "    claim: \"seed: tenant absent from evidence_sources\"\n"
    + _EC_ROW_HEAD +
    "    tenant: nobody\n"
    "    evidence_class: CUSTOMER\n"
    "  - id: SEED-G2\n"
    "    claim: \"seed: row class above its self-pilot source, flipping\"\n"
    + _EC_ROW_HEAD +
    "    tenant: mycocoons\n"
    "    evidence_class: CUSTOMER\n"
    "    preview_flip: true\n"
    "  - id: SEED-G3\n"
    "    claim: \"seed: tenant row without its own class\"\n"
    + _EC_ROW_HEAD +
    "    tenant: mycocoons\n"
)

EVIDENCE_CLASS_SEEDED_CLEAN_LEDGER = (
    "meta:\n"
    "  version: 1\n"
    "  page_coverage:\n"
    "    signal-measurement.html: [SEED-OK]\n"
    "  evidence_sources:\n"
    "    mycocoons:\n"
    "      class: SELF-PILOT\n"
    "      provenance: inference-2026-09-01-part-a-finding-5-owner-confirmation-pending\n"
    "    partner1:\n"
    "      class: DESIGN-PARTNER\n"
    "      provenance: seed-signed-readout\n"
    "claims:\n"
    "  - id: SEED-OK\n"
    "    page: signal-measurement.html\n"
    "    claim: \"seed: healthy backed row, no class (machinery)\"\n"
    "    status: backed\n"
    "    evidence:\n"
    "      - seed_module.py\n"
    "      - seed_module_test.py\n"
    "  - id: SEED-SP\n"
    "    claim: \"seed: self-pilot calibration row, no flip\"\n"
    + _EC_ROW_HEAD +
    "    tenant: mycocoons\n"
    "    evidence_class: SELF-PILOT\n"
    "  - id: SEED-DP\n"
    "    claim: \"seed: design-partner readout authorizing a flip\"\n"
    + _EC_ROW_HEAD +
    "    tenant: partner1\n"
    "    evidence_class: DESIGN-PARTNER\n"
    "    preview_flip: true\n"
    "  - id: SEED-CU\n"
    "    claim: \"seed: customer readout authorizing a flip\"\n"
    + _EC_ROW_HEAD +
    "    evidence_class: CUSTOMER\n"
    "    preview_flip: true\n"
    "  - id: SEED-NF\n"
    "    claim: \"seed: explicit non-flip\"\n"
    + _EC_ROW_HEAD +
    "    preview_flip: false\n"
)

# Rule G probes. CAUGHT when the page has no partner-or-better row; the same
# markup is LEGAL once `evidence_pages` names the page.
EVIDENCE_CLASS_CAUGHT_PROBES = [
    '<section id="s1"><p>Merchants saw a 12% lift in the pilot result.</p></section>',
    '<section id="s2"><p>Verified result: 2.4× return on governed spend.</p></section>',
    '<section id="s3"><p>Benchmark result — 31% of spend was non-incremental.</p></section>',
]
# Scenario / target labels are rule C's business, never rule G's.
EVIDENCE_CLASS_LEGAL_PROBES = [
    '<section id="s1"><p>An illustrative scenario: merchants see a 12% lift.</p></section>',
    '<section id="s2"><p>2.4× return is the design target, not observed.</p></section>',
    '<section id="s3"><p>Composite scenario · illustrative numbers: 31% non-incremental.</p></section>',
    '<section id="s4"><p>The pilot result is not yet written; no number here.</p></section>',
]


def _seed_evidence_class_tree(repo: Path, ledger_text: str, readout: bool = True) -> Path:
    """The rule-E temp tree plus a seeded pilot readout file; return site root."""
    site = _seed_rule_e_tree(repo, ledger_text)
    if readout:
        target = repo / SEEDED_READOUT_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# seed pilot readout\n", encoding="utf-8")
    return site


def run_evidence_class_self_test() -> tuple[dict[str, bool], dict[str, bool], list[str]]:
    """Prove E(e)/E(f)/E(g) and G fire on seeds and stay quiet on clean ones.

    Returns (must-FIRE -> fired, must-stay-LEGAL -> quiet, findings on the
    clean ledger fixture).
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad_repo = Path(td) / "bad"
        bad = check_claims_ledger(
            _seed_evidence_class_tree(bad_repo, EVIDENCE_CLASS_SEEDED_BAD_LEDGER), bad_repo)
        clean_repo = Path(td) / "clean"
        clean = check_claims_ledger(
            _seed_evidence_class_tree(clean_repo, EVIDENCE_CLASS_SEEDED_CLEAN_LEDGER),
            clean_repo)

    def fired(sub: str, rid: str, *needles: str) -> bool:
        return any(sub in f and f"'{rid}'" in f and all(n in f for n in needles)
                   for f in bad)

    expected = {
        "rule-E(e) evidence_class outside the closed vocabulary":
            fired("rule-E(e)", "SEED-E", "PILOT", "SELF-PILOT | DESIGN-PARTNER | CUSTOMER"),
        "rule-E(f) preview flip sourced from SELF-PILOT":
            fired("rule-E(f)", "SEED-F1", "SELF-PILOT"),
        "rule-E(f) preview flip with no evidence_class":
            fired("rule-E(f)", "SEED-F2"),
        "rule-E(f) preview flip without a readout path":
            fired("rule-E(f)", "SEED-F3", "readout"),
        "rule-E(f) preview flip on a debt row":
            fired("rule-E(f)", "SEED-F4", "backed"),
        "rule-E(f) preview flip that is not a boolean":
            fired("rule-E(f)", "SEED-F5"),
        "rule-E(g) tenant absent from meta.evidence_sources":
            fired("rule-E(g)", "SEED-G1", "nobody"),
        "rule-E(g) row class above its tenant source":
            fired("rule-E(g)", "SEED-G2", "mycocoons"),
        "rule-E(f) flip refused through a SELF-PILOT tenant (mycocoons)":
            fired("rule-E(f)", "SEED-G2"),
        "rule-E(g) tenant row without its own evidence_class":
            fired("rule-E(g)", "SEED-G3"),
        "rule-E(g) unknown class in meta.evidence_sources":
            any("rule-E(g)" in f and "'ghost'" in f and "VENDOR" in f for f in bad),
        "rule-E(g) source without provenance":
            any("rule-E(g)" in f and "'silent'" in f and "provenance" in f for f in bad),
    }
    legal: dict[str, bool] = {}
    for probe in EVIDENCE_CLASS_CAUGHT_PROBES:
        expected[f"rule-G result-labeled figure, no partner row [{probe[17:60]}…]"] = any(
            "evidence-class" in f for f in check_file("probe.html", probe))
        legal[f"rule-G same figure with a partner row for the page [{probe[17:60]}…]"] = not any(
            "evidence-class" in f
            for f in check_file("probe.html", probe, evidence_pages={"probe.html"}))
    for probe in EVIDENCE_CLASS_LEGAL_PROBES:
        legal[f"rule-G scenario/target label untouched [{probe[17:60]}…]"] = not any(
            "evidence-class" in f for f in check_file("probe.html", probe))
    # One legal entry per arm, each proving ITS arm stays silent on the clean
    # ledger (three classes, a partner flip, a customer flip, a self-pilot
    # calibration row with no flip, an explicit non-flip).
    legal["rule-E(e) all three classes parse clean"] = not any("rule-E(e)" in f for f in clean)
    legal["rule-E(f) DESIGN-PARTNER / CUSTOMER flips with readouts stay legal"] = not any(
        "rule-E(f)" in f for f in clean)
    legal["rule-E(g) tenant rows agreeing with their sources stay legal"] = not any(
        "rule-E(g)" in f for f in clean)
    return expected, legal, clean


def run_self_test() -> bool:
    bad = check_file("signal.html", SEEDED_BAD)  # named so check D applies
    expected = {
        "banned mind-reading": any("mind-reading" in f for f in bad),
        "banned guaranteed": any("guaranteed" in f for f in bad),
        "deployed-intent claim": any("deployed-intent" in f for f in bad),
        "deployed-net-yield claim": any("deployed-net-yield" in f for f in bad),
        "banned quokka-swarm": any("Quokka Swarm" in f for f in bad),
        "unattributed KL figures": any("KL-divergence" in f for f in bad),
        "unlabeled observed-perf": any("design target" in f for f in bad),
        "unlabeled sub-N-ms latency": any(
            "design target" in f and "'s6'" in f for f in bad),
        "unlabeled <N-ms latency": any(
            "design target" in f and "'s7'" in f for f in bad),
        "net-yield preview framing": any(
            "preview-framing" in f and "net" in f for f in bad),
        "preview framing": any("preview-framing" in f for f in bad),
        "number label": any("number-label" in f for f in bad),
        "sec sequence": any("sec-sequence" in f for f in bad),
        "salted-hash terminology": any("hashing-terminology" in f for f in bad),
    }
    # Probed one sentence at a time, so a regression names the exact sentence.
    # `expected` holds "this must FIRE"; `legal` holds "this must stay SILENT"
    # — the two are printed separately, because a gate that reports a legal
    # sentence as CAUGHT is unreadable at exactly the moment it matters.
    legal: dict[str, bool] = {}
    # F2 (2026-08-09): the four latency sentences the context narrowing let
    # through, plus the cadence sentence that always fired.
    for probe in PERF_LATENCY_PROBES:
        expected[f"15-minute claim [{probe}]"] = _observed_perf_hit(probe)
    legal["reworded demo agenda (walkthrough.html demo FAQ)"] = \
        not _observed_perf_hit(AGENDA_PROBE_REWORDED)
    # F6 (2026-08-09): the hashing phrasings that were silent, and the
    # negated/contrastive forms of the page copy that must remain legal.
    for probe in HASH_SALT_PROBES:
        expected[f"salt/hash claim [{probe}]"] = bool(HASH_SALT.search(probe))
    # Character-reference evasion: renders as an ordinary "Salted SHA-256".
    # Probed through check_file, since decoding happens in the visible-text
    # reducer, not in the arm.
    expected["salt/hash claim written with a character reference "
             "(Salted SHA&#8209;256)"] = any(
        "hashing-terminology" in f for f in
        check_file("probe.html", "<p>Salted SHA&#8209;256 identity stitching.</p>"))
    for probe in HASH_SALT_LEGAL_PROBES:
        legal[f"negated/contrastive salt wording [{probe[:52]}…]"] = \
            not HASH_SALT.search(probe)
    # F13 (2026-08-09): guarantee/guarantees were uncovered; "regret
    # guarantees" is the bandit term of art and must stay legal.
    for probe in GUARANTEE_PROBES:
        expected[f"guarantee claim [{probe}]"] = bool(GUARANTEED.search(probe))
    for probe in GUARANTEE_LEGAL_PROBES:
        legal[f"negated / term-of-art guarantee wording [{probe[:52]}…]"] = \
            not GUARANTEED.search(probe)
    # 2026-09-25 — unattested compliance attestations, both directions. Probed
    # through check_banned_strings so the finding label is what is asserted.
    for probe in ATTESTATION_PROBES:
        expected[f"attestation claim [{probe[:52]}…]"] = any(
            "unattested compliance attestation" in f
            for f in check_banned_strings("probe.html", probe))
    for probe in ATTESTATION_CLAUSE_PROBES:
        expected[f"attestation claim, denial in another clause [{probe[:52]}…]"] = any(
            "unattested compliance attestation" in f
            for f in check_banned_strings("probe.html", probe))
    for probe in ATTESTATION_LEGAL_PROBES:
        legal[f"attestation denial / mechanism wording [{probe[:52]}…]"] = not any(
            "unattested compliance attestation" in f
            for f in check_banned_strings("probe.html", probe))
    # 2026-08-19 — O-1 prohibited-signal capability language, both directions
    # (vocabulary-ratification ruling's KEEP-banned list; the families are
    # schema-prohibited, so any capability claim about them is unbackable).
    for probe in O1_CAPABILITY_PROBES:
        expected[f"O-1 capability claim [{probe[:52]}…]"] = any(
            "O-1 prohibited-signal" in f
            for f in check_banned_strings("probe.html", probe))
    for probe in O1_CAPABILITY_LEGAL_PROBES:
        legal[f"O-1 denial/disclosure wording [{probe[:52]}…]"] = not any(
            "O-1 prohibited-signal" in f
            for f in check_banned_strings("probe.html", probe))
    # 2026-08-09 (third pass) — bounded disclaimer-listing exemption. Both
    # directions, because an exemption proven in only one direction is an
    # exemption nobody has checked.
    for probe in DISCLAIMER_LEGAL_PROBES:
        legal[f"\"what we never say\" disclaimer listing "
              f"[{' '.join(_strip_invisible_html(probe).split())[:56]}…]"] = not any(
            "banned-string" in f for f in check_file("probe.html", probe))
    for i, probe in enumerate(DISCLAIMER_CAUGHT_PROBES, 1):
        expected[f"real claim under a disclaimer heading #{i} "
                 f"(exemption must not reach it)"] = any(
            "banned-string" in f for f in check_file("probe.html", probe))
    # 2026-08-09 (third pass) — observed-performance perimeter.
    for probe in PERF_EVASION_PROBES:
        expected[f"observed-performance evasion [{probe}]"] = _observed_perf_hit(probe)
    for probe in PERF_LEGAL_PROBES:
        legal[f"legal non-latency wording [{probe[:52]}…]"] = not _observed_perf_hit(probe)
    # 2026-08-09 (third pass) — per-figure number-label scope.
    expected["figure beyond the label window (was cleared section-wide)"] = any(
        "number-label" in f for f in check_file("probe.html", NUMBER_SCOPE_CAUGHT))
    legal["figure inside the label window"] = not any(
        "number-label" in f for f in check_file("probe.html", NUMBER_SCOPE_LEGAL_NEAR))
    legal["figure past the window but under an explicit scope banner"] = not any(
        "number-label" in f for f in check_file("probe.html", NUMBER_SCOPE_LEGAL_BANNER))
    # Run 1 item 1.D (2026-09-02) — rule H, stat attribution, cases 81–88.
    for i, probe in enumerate(STAT_ATTRIBUTION_CAUGHT_PROBES, 81):
        expected[f"#{i} unsourced external statistic [{probe[:52]}…]"] = any(
            "stat-attribution" in f for f in check_stat_attribution("probe.html", probe))
    for i, probe in enumerate(STAT_ATTRIBUTION_LEGAL_PROBES, 85):
        legal[f"#{i} sourced+dated or labelled figure [{probe[:52]}…]"] = not any(
            "stat-attribution" in f for f in check_stat_attribution("probe.html", probe))
    # 2026-08-09 (third pass) — rule F, dead internal links.
    dead_caught = check_dead_links(
        "blog/probe.html", DEAD_LINK_CAUGHT_PROBE, DEAD_LINK_SEEDED_PATHS)
    expected["dead link to a 301-to-homepage path (root-absolute)"] = any(
        "/roi.html" in f for f in dead_caught)
    expected["dead link to a 301-to-homepage path (relative ../)"] = any(
        "/case-studies.html" in f for f in dead_caught)
    legal["legitimate 301s / live routes / anchors / off-site links"] = not check_dead_links(
        "blog/probe.html", DEAD_LINK_LEGAL_PROBE, DEAD_LINK_SEEDED_PATHS)
    # Non-vacuous: the real route table must still yield a dead-end set.
    expected["route table yields the redirect-to-homepage set from app.py"] = (
        "/roi.html" in dead_end_paths(SITE_ROOT))
    # index.html's filing grammar (.filing / .folio) — the duplicate §01 case.
    dup = check_file("index.html", SEEDED_DUP_SECTIONS)
    expected["duplicate §-mark (folio/filing devices)"] = any(
        "sec-sequence" in f and "duplicated: [1]" in f for f in dup)
    rule_e_fired, rule_e_clean = run_rule_e_self_test()
    expected.update(rule_e_fired)
    # WS-4 (2026-09-02) — evidence class: E(e)/E(f)/E(g) and rule G, both
    # directions, on seeded ledgers and seeded page sections.
    ec_expected, ec_legal, ec_clean = run_evidence_class_self_test()
    expected.update(ec_expected)
    legal.update(ec_legal)
    # Vocabulary ratification (owner ruling 2026-08-19-A) mirrored onto the
    # served-site gate, both directions — mirrors tests/skills/
    # test_canon_vocabulary.py on the content_qa side (FINISH_IT §P-2.1):
    #   LEGAL   — every ratified term in ordinary product copy stays silent;
    #   CAUGHT  — a ratified term wrapped in a banned claim is still flagged,
    #             so ratification never upgrades a claim.
    for term in RATIFIED_VOCABULARY:
        legal[f"ratified vocabulary in product copy [{term}]"] = not check_banned_strings(
            "probe.html", f"{term} is named in the platform's product documentation.")
    expected['ratified term inside a "guarantee" claim still caught'] = any(
        "guarantee" in f for f in check_banned_strings(
            "probe.html", "The ValidationPassport guarantees incremental net contribution."))
    clean = check_file("signal.html", SEEDED_CLEAN)
    device_clean = check_file("index.html", SEEDED_DEVICE_CLEAN)
    ok = (all(expected.values()) and all(legal.values()) and not clean
          and not rule_e_clean and not device_clean and not ec_clean)
    for name, fired in expected.items():
        print(f"  self-test seeded violation [{name}]: {'CAUGHT' if fired else 'MISSED'}")
    for name, quiet in legal.items():
        print(f"  self-test legal wording [{name}]: "
              f"{'STAYS LEGAL' if quiet else 'FALSE POSITIVE'}")
    print(f"  self-test clean sample: {len(clean)} finding(s) (expected 0)")
    for f in clean:
        print(f"    unexpected: {f}")
    print(f"  self-test folio/filing clean sample: {len(device_clean)} finding(s) (expected 0)")
    for f in device_clean:
        print(f"    unexpected: {f}")
    print(f"  self-test rule-E clean fixture: {len(rule_e_clean)} finding(s) (expected 0)")
    for f in rule_e_clean:
        print(f"    unexpected: {f}")
    print(f"  self-test evidence-class clean fixture: {len(ec_clean)} finding(s) (expected 0)")
    for f in ec_clean:
        print(f"    unexpected: {f}")
    print(f"SELF-TEST {'PASS — the gate fires' if ok else 'FAIL — the gate is broken'}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="verify the gate catches seeded violations")
    parser.add_argument("--root", default=str(SITE_ROOT),
                        help="site root (default: the folder above scripts/)")
    args = parser.parse_args()
    if args.self_test:
        return 0 if run_self_test() else 1
    findings = run_scan(Path(args.root))
    if findings:
        print(f"CONTENT QA: {len(findings)} finding(s)")
        for f in findings:
            print(f"  {f}")
        return 1
    print(f"CONTENT QA OK — {len(SCOPE_FILES)} scoped files clean "
          f"(banned strings, preview framing, number labels, §-sequence, "
          f"claims ledger backed, no homepage-dead-end links, "
          f"no public result figure without partner-or-better evidence)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
