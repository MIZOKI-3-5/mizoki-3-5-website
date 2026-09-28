"""Milestone events at 3 and 10 partners reaching ``PILOT_SIGNED`` — each
emitted ONCE, ever.

Idempotency lives in the store (``record_milestone(key)`` is create-once:
in-memory list / Firestore ``partner_milestones/{key}.create``), so a second
process or a re-run after a crash cannot emit a second event. A partner
counts once it has reached PILOT_SIGNED or any later stage; a PAUSED partner
counts by the stage it was paused from; LOST never counts.
"""
from __future__ import annotations

from typing import Any

from .models import now_iso
from .stages import Stage, reached
from .store import PartnerStore

MILESTONES: tuple[int, ...] = (3, 10)
MILESTONE_STAGE = Stage.PILOT_SIGNED


def milestone_key(threshold: int) -> str:
    return f"{MILESTONE_STAGE.value.lower()}:{threshold}"


def signed_count(store: PartnerStore) -> int:
    return sum(1 for r in store.list_all() if reached(r.stage, MILESTONE_STAGE, r.paused_from))


def check_milestones(store: PartnerStore, at: str | None = None) -> list[dict[str, Any]]:
    """Emit every milestone whose threshold the signed count has reached and
    that has not been emitted before. Returns the NEW events only."""
    count = signed_count(store)
    events: list[dict[str, Any]] = []
    for threshold in MILESTONES:
        if count < threshold:
            continue
        key = milestone_key(threshold)
        if store.record_milestone(key):
            events.append({
                "kind": "milestone",
                "key": key,
                "stage": MILESTONE_STAGE.value,
                "threshold": threshold,
                "count": count,
                "at": at or now_iso(),
            })
    return events
