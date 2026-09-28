"""Site feature flags — literal ``"false"`` defaults, pinned by source-literal tests.

Run 1 item 1.F (Strategic Eval Remediation, 2026-09-02). Shape copied from
``services/net-yield/flags.py``: every flag reads ``os.environ.get(<ENV>,
"false")`` with the string ``"false"`` as the default, and
``tests/test_site_flags.py`` asserts BOTH the source literal (``inspect``) and
the AST default (reformatting cannot dodge it; only a real default flip can).

  SITE_EVENTS  — POST /event and POST /shopify/event accept aggregate,
                 identity-free site events and write them to BigQuery
                 ``unified.site_events_agg``. OFF → the endpoints answer 204
                 and write nothing; the ≤1 KB client script is NOT rendered.
  PILOT_FORM   — the two-field pilot request form (email + store URL) is
                 injected into /shopify and POST /shopify/pilot-request writes
                 an idempotent Firestore document and notifies the owner via
                 SendGrid. OFF → /shopify serves its file bytes unchanged and
                 the endpoint answers 404.
  LEARN_PAGES  — GET /learn/ and GET /learn/<slug> render the AEO/GEO authority
                 pages (repo docs/marketing/aeo/*.md via mizoki_runtime.learn_pages)
                 and GET /llms.txt serves the site's llms.txt. OFF → all three
                 answer 404 (the top-level static catch-all never sees /llms.txt
                 because the explicit route wins the match). Lane 5 S4 (2026-09-02).

Flag ON with its sink un-configured (no client library, no credentials, no
API key) is NOT a healthy stub: the endpoint answers 503 ``not_configured``
and ``/api/health`` reports the flag as ``not_configured`` (Part 0 rule 6).
"""
from __future__ import annotations

import os

SITE_EVENTS_ENV = "SITE_EVENTS"
PILOT_FORM_ENV = "PILOT_FORM"
LEARN_PAGES_ENV = "LEARN_PAGES"

# Values that do NOT enable a flag / that DO (pinned both directions by the tests).
NON_ENABLING_VALUES = ("", "false", "False", "FALSE", "0", "no", "off", "yes", "on", "1")
ENABLING_VALUES = ("true", "True", "TRUE", " true ")


def site_events_enabled() -> bool:
    return os.environ.get(SITE_EVENTS_ENV, "false").strip().lower() == "true"


def pilot_form_enabled() -> bool:
    return os.environ.get(PILOT_FORM_ENV, "false").strip().lower() == "true"


def learn_pages_enabled() -> bool:
    return os.environ.get(LEARN_PAGES_ENV, "false").strip().lower() == "true"


def snapshot() -> dict[str, bool]:
    """Flag state for /api/health (booleans only — never a secret value)."""
    return {
        "site_events": site_events_enabled(),
        "pilot_form": pilot_form_enabled(),
        "learn_pages": learn_pages_enabled(),
    }
