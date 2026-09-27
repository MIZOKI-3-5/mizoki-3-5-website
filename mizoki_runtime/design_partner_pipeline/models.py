"""The partner record (Strategy S1, Lane 6).

Fields and the rules behind them:

  partner_id      64-hex sha256 — a PSEUDONYMOUS id, not an anonymous one.
                  For a form-sourced partner it is the Lane 3 request id
                  (UNSALTED ``sha256(email|store)``, inherited from
                  ``# MIZ OKI 3.5/mizoki_runtime/pilot_requests.py``), which
                  anyone holding the e-mail and store can recompute; for every
                  other source it is ``sha256(source|normalized name)``. It is
                  the only identifier that reaches BigQuery; no DIRECT
                  identifier (name, e-mail, phone, host) ever does.
  display_name    Firestore-only (``partners/{id}``). ``to_bigquery_row()``
                  never emits it — the BigQuery table carries the id hash and
                  categorical facts only (see ``ddl/design_partner_pipeline.sql``).
  segment         agency | brand | warm_intro — the display segment.
  band            an enumerated size band (``SizeBand``), NEVER a revenue or
                  order figure. The mapping from a band to any number lives
                  outside this repository.
  consent         outreach consent basis + recorded_at + opt-out flag.
                  FAIL-CLOSED: ``Consent.outreach_permitted()`` is False unless
                  a basis AND a recorded_at exist and the partner has not opted
                  out; no outreach action (and no SOURCED → CONTACTED
                  transition) is legal without it.
  source          form | agency | warm | outbound.
  agent_originated_share
                  ``None`` and stays ``None`` until Strategy S2 (agent-
                  originated traffic classification) writes measured data.
                  Nothing in this package computes or defaults it.

Stdlib dataclasses on purpose: the package must import with no third-party
dependency so the store can be built without any client library present.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from .stages import FORWARD_CHAIN, Stage, assert_legal

#: Stages a partner cannot enter without a permitted outreach consent.
OUTREACH_STAGES: frozenset[Stage] = frozenset({Stage.CONTACTED, Stage.CALL})


class Segment(str, Enum):
    AGENCY = "agency"
    BRAND = "brand"
    WARM_INTRO = "warm_intro"


class SizeBand(str, Enum):
    """Opaque bands. The band → number mapping is NOT in git."""
    UNKNOWN = "UNKNOWN"
    BAND_S = "S"
    BAND_M = "M"
    BAND_L = "L"
    BAND_XL = "XL"


class Source(str, Enum):
    FORM = "form"
    AGENCY = "agency"
    WARM = "warm"
    OUTBOUND = "outbound"


class ConsentBasis(str, Enum):
    """Closed vocabulary for the OUTREACH consent basis.

    This is the basis on which a person at the partner may be contacted. It
    is unrelated to (and never substitutes for) the per-subject data-
    processing consent that ``evaluate_consent`` enforces at ingest.
    """
    INBOUND_REQUEST = "inbound_request"          # they asked us (Lane 3 form)
    EXPLICIT_OPT_IN = "explicit_opt_in"          # they said yes to outreach
    EXISTING_RELATIONSHIP = "existing_relationship"  # warm intro through a known contact
    LEGITIMATE_INTEREST = "legitimate_interest"  # B2B outbound, documented basis


class ConsentRequired(PermissionError):
    """An outreach action was attempted without recorded consent."""


_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_name(value: str) -> str:
    """Lower-case, punctuation-free, whitespace-collapsed organisation name —
    the dedupe key for every non-form source."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def partner_id_for(source: Source | str, name: str) -> str:
    """``sha256(source|normalized name)`` — deterministic, so a re-import of
    the same organisation is the same partner."""
    key = f"{Source(source).value}|{normalize_name(name)}"
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class Consent:
    basis: ConsentBasis | None = None
    recorded_at: str | None = None
    opted_out: bool = False

    def __post_init__(self) -> None:
        if self.basis is not None:
            self.basis = ConsentBasis(self.basis)
        if self.recorded_at is not None and not _ISO_RE.match(self.recorded_at):
            raise ValueError("consent.recorded_at must be an ISO-8601 UTC timestamp")
        self.opted_out = bool(self.opted_out)

    def outreach_permitted(self) -> bool:
        """Fail-closed: True only with a basis, a timestamp, and no opt-out."""
        return self.basis is not None and bool(self.recorded_at) and not self.opted_out

    def to_dict(self) -> dict[str, Any]:
        return {
            "basis": self.basis.value if self.basis else None,
            "recorded_at": self.recorded_at,
            "opted_out": self.opted_out,
        }


@dataclass
class PartnerRecord:
    partner_id: str
    segment: Segment
    source: Source
    band: SizeBand = SizeBand.UNKNOWN
    consent: Consent = field(default_factory=Consent)
    stage: Stage = Stage.SOURCED
    paused_from: Stage | None = None
    display_name: str | None = None          # Firestore only — never in BigQuery
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    # Stays None until Strategy S2 (agent-originated classification) writes
    # measured data. Nothing in this package assigns it.
    agent_originated_share: float | None = None

    def __post_init__(self) -> None:
        if not _HEX64.match(self.partner_id):
            raise ValueError("partner_id must be a 64-hex sha256 digest")
        self.segment = Segment(self.segment)
        self.source = Source(self.source)
        self.band = SizeBand(self.band)
        self.stage = Stage(self.stage)
        if self.paused_from is not None:
            self.paused_from = Stage(self.paused_from)
        if isinstance(self.consent, Mapping):
            self.consent = Consent(**dict(self.consent))
        if self.agent_originated_share is not None:
            raise ValueError("agent_originated_share stays None until S2 data exists")
        if self.display_name is not None and "@" in self.display_name:
            raise ValueError("display_name must not be an e-mail address")

    # -- consent gate -------------------------------------------------------

    def assert_outreach_permitted(self) -> None:
        if not self.consent.outreach_permitted():
            raise ConsentRequired(
                f"partner {self.partner_id[:12]}…: no outreach without a recorded consent basis")

    # -- serialisation ------------------------------------------------------

    def to_document(self) -> dict[str, Any]:
        """The Firestore ``partners/{id}`` document (includes display_name)."""
        doc = asdict(self)
        doc["segment"] = self.segment.value
        doc["source"] = self.source.value
        doc["band"] = self.band.value
        doc["stage"] = self.stage.value
        doc["paused_from"] = self.paused_from.value if self.paused_from else None
        doc["consent"] = self.consent.to_dict()
        return doc

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "PartnerRecord":
        data = dict(doc)
        data["consent"] = Consent(**dict(data.get("consent") or {}))
        return cls(**data)

    def to_bigquery_row(self, from_stage: Stage | None, to_stage: Stage, occurred_at: str) -> dict[str, Any]:
        """One append-only row in ``unified.design_partner_pipeline`` — a stage
        event. Categorical facts + the id hash only; NO display name, NO
        contact detail. ``insert_id`` is the idempotency key."""
        row = {
            "partner_id": self.partner_id,
            "segment": self.segment.value,
            "band": self.band.value,
            "source": self.source.value,
            "from_stage": Stage(from_stage).value if from_stage else None,
            "to_stage": Stage(to_stage).value,
            "consent_basis": self.consent.basis.value if self.consent.basis else None,
            "consent_opted_out": self.consent.opted_out,
            "agent_originated_share": self.agent_originated_share,   # NULL until S2
            "occurred_at": occurred_at,
        }
        key = f"{row['partner_id']}|{row['from_stage']}|{row['to_stage']}|{occurred_at}"
        row["insert_id"] = hashlib.sha256(key.encode()).hexdigest()
        return row


#: The BigQuery column set — the DDL test holds both directions against this.
BIGQUERY_COLUMNS: tuple[str, ...] = (
    "partner_id", "segment", "band", "source", "from_stage", "to_stage",
    "consent_basis", "consent_opted_out", "agent_originated_share",
    "occurred_at", "insert_id",
)


def transition(record: PartnerRecord, target: Stage, at: str | None = None) -> PartnerRecord:
    """Apply a legal stage move IN PLACE and return the record.

    Raises ``IllegalTransition`` for a move not in the table and
    ``ConsentRequired`` (verifier F-03, 2026-09-02) when:
      * the target is an OUTREACH-BEARING stage — CONTACTED or CALL — and the
        record has no permitted consent (basis + timestamp + no opt-out),
        whatever the current stage, a PAUSED resume included; or
      * the partner has opted out and the target is ANY forward stage. An
        opted-out partner may only be PAUSED or marked LOST.
    """
    target = Stage(target)
    assert_legal(record.stage, target, record.paused_from)
    if target in FORWARD_CHAIN and record.consent.opted_out:
        raise ConsentRequired(
            f"partner {record.partner_id[:12]}…: opted out — no forward move to {target.value}")
    if target in OUTREACH_STAGES:
        record.assert_outreach_permitted()
    if target is Stage.PAUSED:
        record.paused_from = record.stage
    elif record.stage is Stage.PAUSED:
        record.paused_from = None
    record.stage = target
    record.updated_at = at or now_iso()
    return record
