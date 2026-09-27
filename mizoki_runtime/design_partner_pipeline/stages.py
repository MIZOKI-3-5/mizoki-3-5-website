"""Pipeline stages and the legal-transition table (Strategy S1, Lane 6).

The forward chain is strictly ordered and a transition moves ONE step
forward — never two, never backward:

    SOURCED → CONTACTED → CALL → PILOT_SIGNED → LIVE_TRAFFIC
            → CLEAN_CYCLE_1 → CLEAN_CYCLE_2

Two side states exist because a real pipeline has them and a table without
them would force callers to invent one:

  LOST    terminal. Reachable from every forward stage except the last
          (a partner that has completed two clean cycles is not "lost").
          Nothing leaves LOST.
  PAUSED  a side state, reachable from every forward stage except the
          last. Leaving PAUSED is legal only back to the exact stage the
          record was paused from (``paused_from``) or to LOST — a pause
          can never be used to skip a step.

A transition not in this table raises ``IllegalTransition``. Nothing here
touches consent: the consent gate on SOURCED → CONTACTED (contacting is an
outreach action) is enforced by ``models.transition`` because it needs the
record, not just the stage pair.
"""
from __future__ import annotations

from enum import Enum


class Stage(str, Enum):
    SOURCED = "SOURCED"
    CONTACTED = "CONTACTED"
    CALL = "CALL"
    PILOT_SIGNED = "PILOT_SIGNED"
    LIVE_TRAFFIC = "LIVE_TRAFFIC"
    CLEAN_CYCLE_1 = "CLEAN_CYCLE_1"
    CLEAN_CYCLE_2 = "CLEAN_CYCLE_2"
    # side / terminal states
    LOST = "LOST"
    PAUSED = "PAUSED"


#: The ordered forward chain — the ONLY order; index = rank.
FORWARD_CHAIN: tuple[Stage, ...] = (
    Stage.SOURCED,
    Stage.CONTACTED,
    Stage.CALL,
    Stage.PILOT_SIGNED,
    Stage.LIVE_TRAFFIC,
    Stage.CLEAN_CYCLE_1,
    Stage.CLEAN_CYCLE_2,
)
TERMINAL_SUCCESS: Stage = Stage.CLEAN_CYCLE_2
SIDE_STATES: frozenset[Stage] = frozenset({Stage.LOST, Stage.PAUSED})


def _build_table() -> dict[Stage, frozenset[Stage]]:
    table: dict[Stage, set[Stage]] = {s: set() for s in Stage}
    for i, stage in enumerate(FORWARD_CHAIN):
        if stage is TERMINAL_SUCCESS:
            continue  # nothing leaves the terminal success stage
        table[stage].add(FORWARD_CHAIN[i + 1])
        table[stage].add(Stage.LOST)
        table[stage].add(Stage.PAUSED)
    # PAUSED → (the stage it was paused from — checked by `assert_legal`) | LOST
    table[Stage.PAUSED] = {Stage.LOST} | {s for s in FORWARD_CHAIN if s is not TERMINAL_SUCCESS}
    table[Stage.LOST] = set()
    return {k: frozenset(v) for k, v in table.items()}


#: stage → the set of stages it may move to. For PAUSED the forward members
#: are additionally constrained to ``paused_from`` by ``assert_legal``.
LEGAL_TRANSITIONS: dict[Stage, frozenset[Stage]] = _build_table()


class IllegalTransition(ValueError):
    """A stage move that is not in ``LEGAL_TRANSITIONS`` (or a PAUSED resume
    to a stage other than the one paused from)."""


def rank(stage: Stage) -> int:
    """Position in the forward chain; side states have no rank (-1)."""
    return FORWARD_CHAIN.index(stage) if stage in FORWARD_CHAIN else -1


def assert_legal(current: Stage, target: Stage, paused_from: Stage | None = None) -> None:
    current, target = Stage(current), Stage(target)
    if target not in LEGAL_TRANSITIONS[current]:
        raise IllegalTransition(f"{current.value} -> {target.value} is not a legal transition")
    if current is Stage.PAUSED and target is not Stage.LOST:
        if paused_from is None:
            raise IllegalTransition("PAUSED record has no paused_from; cannot resume")
        if Stage(paused_from) is not target:
            raise IllegalTransition(
                f"PAUSED -> {target.value} refused: record was paused from {Stage(paused_from).value}")


def is_legal(current: Stage, target: Stage, paused_from: Stage | None = None) -> bool:
    try:
        assert_legal(current, target, paused_from)
    except IllegalTransition:
        return False
    return True


def reached(stage: Stage, milestone: Stage, paused_from: Stage | None = None) -> bool:
    """True when a record has reached ``milestone`` in the forward chain.

    A PAUSED record counts by the stage it was paused from; a LOST record
    never counts.
    """
    stage = Stage(stage)
    if stage is Stage.LOST:
        return False
    if stage is Stage.PAUSED:
        if paused_from is None:
            return False
        stage = Stage(paused_from)
    return rank(stage) >= rank(Stage(milestone))
