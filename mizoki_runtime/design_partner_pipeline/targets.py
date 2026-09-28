"""Validator for ``docs/gtm/DESIGN_PARTNER_TARGETS.yaml``.

Rules (each pinned by ``tests/gtm/test_targets.py``):
  * exactly 25 ``agency`` slots and 15 ``warm_intro`` slots;
  * every slot carries exactly the schema keys — unknown keys refused (so a
    ``contact_name`` / ``email`` key can never be added);
  * slot ids unique; filled names unique on ``normalize_name``;
  * ``status`` ∈ {EMPTY_SLOT, FILLED}; FILLED requires a non-null ``name``;
  * ``band`` ∈ SizeBand or null; ``consent.basis`` ∈ ConsentBasis or null;
  * ANY scalar anywhere in the document that looks like an e-mail address or
    a phone number is refused — contacts go to Firestore through the
    pipeline, never into git.

CLI (``scripts/`` is outside this lane's scope manifest, so the entry point
is the module — the packet requests the thin ``scripts/`` wrapper)::

    python -m src.shared.design_partner_pipeline.targets [path]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from .models import ConsentBasis, SizeBand, normalize_name

DEFAULT_PATH = Path("docs/gtm/DESIGN_PARTNER_TARGETS.yaml")
EXPECTED = {"agency": 25, "warm_intro": 15}
SEGMENT_SOURCE = {"agency": "agency", "warm_intro": "warm"}
SLOT_KEYS = frozenset({"slot", "segment", "source", "status", "name", "contact_role",
                       "band", "consent", "notes"})
CONSENT_KEYS = frozenset({"basis", "recorded_at"})
STATUSES = frozenset({"EMPTY_SLOT", "FILLED"})

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
# 7+ digits with optional separators / leading + — the shape of a phone number.
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _scalars(node: Any, path: str = "$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _scalars(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _scalars(v, f"{path}[{i}]")
    else:
        yield path, node


def validate(doc: Any) -> list[str]:
    """Return the list of problems (empty ⇒ valid)."""
    problems: list[str] = []
    if not isinstance(doc, dict) or set(doc) != {"version", "slots"}:
        return ["top level must be exactly {version, slots}"]
    if doc["version"] != 1:
        problems.append("version must be 1")
    slots = doc["slots"]
    if not isinstance(slots, list):
        return problems + ["slots must be a list"]

    # PII shape scan over EVERY scalar in the document, before anything else.
    for path, value in _scalars(doc):
        if isinstance(value, str):
            if EMAIL_RE.search(value):
                problems.append(f"{path}: e-mail-shaped value refused")
            if PHONE_RE.search(value):
                problems.append(f"{path}: phone-shaped value refused")

    seen_ids: set[str] = set()
    seen_names: dict[str, str] = {}
    counts = {seg: 0 for seg in EXPECTED}
    for i, slot in enumerate(slots):
        where = f"slots[{i}]"
        if not isinstance(slot, dict):
            problems.append(f"{where}: must be a mapping")
            continue
        keys = set(slot)
        if keys != SLOT_KEYS:
            problems.append(f"{where}: keys must be exactly {sorted(SLOT_KEYS)}; "
                            f"unknown={sorted(keys - SLOT_KEYS)} missing={sorted(SLOT_KEYS - keys)}")
            continue
        sid = slot["slot"]
        if not isinstance(sid, str) or not sid:
            problems.append(f"{where}: slot id must be a non-empty string")
        elif sid in seen_ids:
            problems.append(f"{where}: duplicate slot id {sid!r}")
        else:
            seen_ids.add(sid)
        seg = slot["segment"]
        if seg not in EXPECTED:
            problems.append(f"{where}: segment must be one of {sorted(EXPECTED)}")
        else:
            counts[seg] += 1
            if slot["source"] != SEGMENT_SOURCE[seg]:
                problems.append(f"{where}: source for {seg} must be {SEGMENT_SOURCE[seg]!r}")
        status = slot["status"]
        if status not in STATUSES:
            problems.append(f"{where}: status must be one of {sorted(STATUSES)}")
        name = slot["name"]
        if name is not None and not isinstance(name, str):
            problems.append(f"{where}: name must be a string or null")
        if status == "FILLED" and not (isinstance(name, str) and name.strip()):
            problems.append(f"{where}: FILLED requires a non-null name")
        if status == "EMPTY_SLOT" and name is not None:
            problems.append(f"{where}: EMPTY_SLOT must have name: null")
        if isinstance(name, str) and name.strip():
            key = normalize_name(name)
            if key in seen_names:
                problems.append(f"{where}: duplicate name (normalized {key!r}) also in {seen_names[key]}")
            else:
                seen_names[key] = where
        role = slot["contact_role"]
        if role is not None and not isinstance(role, str):
            problems.append(f"{where}: contact_role must be a string or null")
        band = slot["band"]
        if band is not None and band not in {b.value for b in SizeBand}:
            problems.append(f"{where}: band must be one of {sorted(b.value for b in SizeBand)} or null")
        consent = slot["consent"]
        if not isinstance(consent, dict) or set(consent) != CONSENT_KEYS:
            problems.append(f"{where}: consent must be exactly {{basis, recorded_at}}")
        else:
            basis = consent["basis"]
            if basis is not None and basis not in {b.value for b in ConsentBasis}:
                problems.append(f"{where}: consent.basis must be one of "
                                f"{sorted(b.value for b in ConsentBasis)} or null")
            rec = consent["recorded_at"]
            if rec is not None and not (isinstance(rec, str) and _ISO_RE.match(rec)):
                problems.append(f"{where}: consent.recorded_at must be ISO-8601 Z or null")
        notes = slot["notes"]
        if notes is not None and not isinstance(notes, str):
            problems.append(f"{where}: notes must be a string or null")
    for seg, expected in EXPECTED.items():
        if counts[seg] != expected:
            problems.append(f"expected exactly {expected} {seg} slots, found {counts[seg]}")
    return problems


def validate_file(path: Path = DEFAULT_PATH) -> list[str]:
    import yaml  # PyYAML — present in every environment that runs the suites

    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"{path}: cannot load — {exc}"]
    return validate(doc)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else DEFAULT_PATH
    problems = validate_file(path)
    if problems:
        print(f"DESIGN_PARTNER_TARGETS INVALID — {len(problems)} problem(s) in {path}")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"DESIGN_PARTNER_TARGETS OK — {path}: 25 agency + 15 warm_intro slots, no contact-shaped values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
