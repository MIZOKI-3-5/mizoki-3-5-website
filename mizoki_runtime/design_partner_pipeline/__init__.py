"""Design-partner pipeline (Strategy S1, Lane 6 — PROJECT COMPLETION v1.0).

Status: IN BUILD, flag-OFF (``DESIGN_PARTNER_PIPELINE`` / ``PIPELINE_DIGEST``
default ``"false"``). Nothing here is LIVE; nothing here contacts anyone.

  stages      ordered stage enum + LEGAL_TRANSITIONS (forward one step; LOST /
              PAUSED side states); a move not in the table raises
  models      PartnerRecord / Consent (fail-closed outreach gate); the
              BigQuery row shape (id hash + categorical facts only)
  store       PartnerStore interface; in-memory impl; Firestore ``partners/{id}``
              + BigQuery ``unified.design_partner_pipeline`` behind the flag
  intake      Lane 3 form submission → SOURCED, idempotent on sha256(email|store)
  milestones  events at 3 and 10 PILOT_SIGNED, emitted once each
  digest      weekly owner digest (counts per stage only) behind PIPELINE_DIGEST
  targets     validator for docs/gtm/DESIGN_PARTNER_TARGETS.yaml
  ddl/        additive DDL for the BigQuery table
"""
from .stages import FORWARD_CHAIN, LEGAL_TRANSITIONS, IllegalTransition, Stage
from .models import (
    Consent, ConsentBasis, ConsentRequired, PartnerRecord, Segment, SizeBand, Source,
    partner_id_for, transition,
)
from .store import (
    InMemoryPartnerStore, NotConfigured, PartnerStore, StaleUpdate, apply_transition, resolve_sink, resolve_store,
)
from .intake import source_from_pilot_request
from .milestones import MILESTONES, check_milestones
from .digest import render_weekly_digest, weekly_digest

__all__ = [
    "FORWARD_CHAIN", "LEGAL_TRANSITIONS", "IllegalTransition", "Stage",
    "Consent", "ConsentBasis", "ConsentRequired", "PartnerRecord", "Segment", "SizeBand", "Source",
    "partner_id_for", "transition",
    "InMemoryPartnerStore", "NotConfigured", "PartnerStore", "StaleUpdate", "apply_transition",
    "resolve_sink", "resolve_store",
    "source_from_pilot_request", "MILESTONES", "check_milestones",
    "render_weekly_digest", "weekly_digest",
]
