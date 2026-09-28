"""Design-partner pipeline flags — literal ``"false"`` defaults, pinned by
source-literal tests (``tests/gtm/test_flags.py``: ``inspect`` + ``ast``).

Shape copied from ``# MIZ OKI 3.5/mizoki_runtime/site_flags.py`` (Run 1 item
1.F) and ``services/net-yield/flags.py``: every flag reads
``os.environ.get(<ENV>, "false")`` and only the string ``true`` (any case,
trimmed) enables it.

  DESIGN_PARTNER_PIPELINE — the Firestore ``partners/{id}`` store and the
      BigQuery ``unified.design_partner_pipeline`` sink are constructed from
      the environment. OFF → ``resolve_store()`` returns ``None`` and every
      caller reports ``not_configured``; no client library is imported.
  PIPELINE_DIGEST — the weekly owner digest is rendered. OFF →
      ``weekly_digest()`` returns ``None`` (nothing is rendered, nothing is
      sent). Sending is not built in this wave; see ``digest.py``.

Flag ON with its sink un-configured (no client library, no credentials) is
NOT a healthy stub: ``resolve_store()`` raises ``NotConfigured`` so a health
surface can say ``not_configured`` honestly.
"""
from __future__ import annotations

import os
from typing import Mapping

DESIGN_PARTNER_PIPELINE_ENV = "DESIGN_PARTNER_PIPELINE"
PIPELINE_DIGEST_ENV = "PIPELINE_DIGEST"

# Values that do NOT enable a flag / that DO (pinned both directions by the tests).
NON_ENABLING_VALUES = ("", "false", "False", "FALSE", "0", "no", "off", "yes", "on", "1")
ENABLING_VALUES = ("true", "True", "TRUE", " true ")


def pipeline_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get(DESIGN_PARTNER_PIPELINE_ENV, "false").strip().lower() == "true"


def digest_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get(PIPELINE_DIGEST_ENV, "false").strip().lower() == "true"


def snapshot(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    """Flag state for a health surface (booleans only — never a secret value)."""
    return {
        "design_partner_pipeline": pipeline_enabled(env),
        "pipeline_digest": digest_enabled(env),
    }
