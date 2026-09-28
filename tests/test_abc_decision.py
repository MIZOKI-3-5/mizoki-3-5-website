"""Site A/B/C decision record — Wave 1 item WS-3 contracts.

The Strategy Resolution Plan v1.0 (Part D row WS-3, ruling S4) closes the
A/B/C item with EXACTLY ONE of two committed artifacts at the repo root:

  * ``docs/product/ABC_PREREGISTRATION.md``    — powered: pre-register and run
  * ``docs/product/ABC_NOT_RUN_DECLARATION.md`` — underpowered / no evidence:
    formally declare not-run and pick one canonical page

This module pins that the decision is one thing (never both, never neither),
that the committed record is an internal governance document (routed to the
signed-in portal, never the public docs index), that what it declares agrees
with the code it describes (``mizoki_runtime.abtest``), that the kill switch
it relies on is still fail-safe off at the SOURCE literal, and that any power
figure it restates keeps its TRUTH.md label on the same line.

Nothing here touches the served site: the record is a repo-root ``docs/``
file and the checks are read-only.
"""

from __future__ import annotations

import inspect
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from mizoki_runtime import abtest

SITE_ROOT = Path(__file__).resolve().parents[1]      # "# MIZ OKI 3.5/"
REPO_ROOT = SITE_ROOT.parent                          # repository root
PRODUCT_DIR = REPO_ROOT / "docs" / "product"
PREREG = PRODUCT_DIR / "ABC_PREREGISTRATION.md"
NOT_RUN = PRODUCT_DIR / "ABC_NOT_RUN_DECLARATION.md"
HOUSE_PREREG = SITE_ROOT / "docs" / "marketing" / "abtest-preregistration-signal-landing.md"

INTERNAL_MARKER = "<!-- mizoki:internal -->"

# Section headings the not-run declaration must carry, in this order.
DECLARATION_SECTIONS = (
    "## 1. Decision",
    "## 2. Basis (measured, not decided)",
    "## 3. What this declaration does NOT do",
    "## 4. Re-open conditions",
    "## 5. Owner decision block",
    "## 6. Evidence",
)

# Figures from the house pre-registration's §3 power table (an illustrative
# scenario by its own label). Restating any of them without the label on the
# same line would launder a placeholder into a measured number.
POWER_FIGURES = re.compile(
    r"(?<![\d.])(3,?826|1,?499|652|11,?478|4,?497|1,?956)(?![\d.%])"
)
POWER_LABEL = "illustrative scenario"

# Arm table rows in the declaration: | A | `/signal` | `signal.html` |
ARM_ROW = re.compile(
    r"^\|\s*\*{0,2}([ABC])\*{0,2}\s*\|\s*`(/[a-z]+)`\s*\|\s*`([a-z/]+\.html)`\s*\|",
    re.M,
)
CANONICAL_ROW = re.compile(r"^\|\s*Canonical page\s*\|\s*(.+?)\s*\|\s*$", re.M)


def _decision_file() -> Path:
    present = [p for p in (PREREG, NOT_RUN) if p.exists()]
    if len(present) != 1:
        raise AssertionError(
            "exactly one A/B/C decision artifact must exist under docs/product/: "
            f"found {[p.name for p in present]}"
        )
    return present[0]


class DecisionIsOneThing(unittest.TestCase):
    """(a) The decision is a single committed artifact, never both or neither."""

    def test_exactly_one_decision_artifact_exists(self) -> None:
        present = [p.name for p in (PREREG, NOT_RUN) if p.exists()]
        self.assertEqual(
            len(present), 1,
            f"WS-3 closes with exactly one of {PREREG.name} / {NOT_RUN.name}; found {present}",
        )

    def test_house_preregistration_untouched(self) -> None:
        # The declaration keeps the house pre-registration in the tree as the
        # template, status unchanged. It is a read-only source for this item.
        text = HOUSE_PREREG.read_text(encoding="utf-8")
        self.assertIn("**Status:** `REGISTERED — NOT COLLECTING`", text)


class DeclarationShape(unittest.TestCase):
    """(b) Governance-record shape: internal marker, status line, sections."""

    def setUp(self) -> None:
        self.path = _decision_file()
        self.text = self.path.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()

    def test_internal_marker_is_first_line(self) -> None:
        # A signed-in-portal record, not a customer page: build_site_docs.py
        # routes on this marker (INTERNAL_MARKER) and it must be line 1.
        self.assertEqual(self.lines[0].strip(), INTERNAL_MARKER)

    def test_status_line_present(self) -> None:
        status = [ln for ln in self.lines if ln.startswith("**Status:**")]
        self.assertEqual(len(status), 1, "exactly one **Status:** line")
        if self.path == NOT_RUN:
            self.assertTrue(
                status[0].startswith("**Status:** DECLARED — NOT RUN"),
                status[0],
            )

    def test_sections_present_in_order(self) -> None:
        if self.path != NOT_RUN:
            self.skipTest("section contract is for the not-run declaration")
        positions = []
        for heading in DECLARATION_SECTIONS:
            self.assertIn(heading, self.text, f"missing section {heading!r}")
            positions.append(self.text.index(heading))
        self.assertEqual(positions, sorted(positions), "sections out of order")

    def test_no_prechecked_owner_decision(self) -> None:
        # The owner types the decision in-session; the record never pre-checks
        # one option (a pre-checked box is an "APPROVED:" string in disguise).
        self.assertNotRegex(self.text, r"^\s*-\s*\[[xX]\]", "pre-checked box")


class DeclarationAgreesWithCode(unittest.TestCase):
    """(c) What the record declares equals what mizoki_runtime.abtest serves."""

    def setUp(self) -> None:
        self.text = _decision_file().read_text(encoding="utf-8")

    def test_canonical_page_matches_module(self) -> None:
        rows = CANONICAL_ROW.findall(self.text)
        self.assertEqual(len(rows), 1, "exactly one 'Canonical page' table row")
        row = rows[0]
        self.assertIn(f"`{abtest.CANONICAL_PATH}`", row)
        self.assertIn(abtest.CANONICAL_URL, row)
        for key, path in abtest.VARIANT_PATHS.items():
            if path != abtest.CANONICAL_PATH:
                self.assertNotIn(f"`{path}`", row, f"arm {key} declared canonical")

    def test_declared_arms_equal_variant_registry(self) -> None:
        rows = ARM_ROW.findall(self.text)
        declared_files = {k.lower(): f for k, _p, f in rows}
        declared_paths = {k.lower(): p for k, p, _f in rows}
        self.assertEqual(declared_files, dict(abtest.VARIANT_FILES))
        self.assertEqual(declared_paths, dict(abtest.VARIANT_PATHS))
        self.assertEqual(tuple(sorted(declared_files)), tuple(abtest.VARIANTS))

    def test_kill_switch_named_and_left_unset(self) -> None:
        self.assertIn("`MIZOKI_ABTEST_MODE`", self.text)
        # The record's OWN prose never carries the arming line. Fenced blocks
        # are verbatim evidence transcripts (register rows, command output)
        # and may quote it; the prose outside them may not.
        prose, in_fence = [], False
        for line in self.text.splitlines():
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                prose.append(line)
        self.assertNotIn("MIZOKI_ABTEST_MODE=on", "\n".join(prose).replace("`", ""),
                         "the declaration's prose must not carry the arming line")
        self.assertRegex("\n".join(prose), r"`MIZOKI_ABTEST_MODE`[^\n]*unset",
                         "the declaration must say the flag stays unset")


class KillSwitchIsFailSafeOff(unittest.TestCase):
    """(d) mode_on() is off unless the env var is exactly 'on' — runtime AND source."""

    def test_unset_is_off(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "MIZOKI_ABTEST_MODE"}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(abtest.mode_on())

    def test_anything_but_on_is_off(self) -> None:
        for value in ("", "off", "0", "1", "true", "yes", "ON_", "on-", " o n "):
            with patch.dict(os.environ, {"MIZOKI_ABTEST_MODE": value}):
                self.assertFalse(abtest.mode_on(), repr(value))

    def test_on_is_on(self) -> None:
        # Both directions: the guard must still be able to fire.
        with patch.dict(os.environ, {"MIZOKI_ABTEST_MODE": "on"}):
            self.assertTrue(abtest.mode_on())

    def test_source_literal_compares_on_with_empty_default(self) -> None:
        # Assert the SOURCE, not just the runtime value: a flipped default
        # (e.g. .get("MIZOKI_ABTEST_MODE", "on")) fails here even if a test
        # environment happened to leave the var unset.
        src = inspect.getsource(abtest.mode_on)
        self.assertRegex(
            src, r'os\.environ\.get\(\s*"MIZOKI_ABTEST_MODE"\s*,\s*""\s*\)',
            "default must be the empty string (fail-safe off)",
        )
        self.assertRegex(src, r'==\s*"on"(?!\w)', "must compare the literal \"on\"")
        self.assertNotRegex(src, r'!=\s*"on"|"on"\s*!=|not\s+.*==\s*"on"',
                            "inverted comparison would make off the exception")


class PowerFiguresStayLabeled(unittest.TestCase):
    """(e) Any restated power-table figure carries 'illustrative scenario' on
    its line; inside a fenced block the label must sit within the three
    non-blank lines before the opening fence."""

    def setUp(self) -> None:
        self.lines = _decision_file().read_text(encoding="utf-8").splitlines()

    def test_every_power_figure_is_labeled(self) -> None:
        in_fence = False
        fence_labeled = False
        for i, line in enumerate(self.lines):
            if line.strip().startswith("```"):
                if not in_fence:
                    before = [ln for ln in self.lines[max(0, i - 6):i] if ln.strip()][-3:]
                    fence_labeled = any(POWER_LABEL in ln.lower() for ln in before)
                in_fence = not in_fence
                continue
            if not POWER_FIGURES.search(line):
                continue
            if in_fence:
                self.assertTrue(fence_labeled, f"unlabeled fenced power figure at line {i + 1}: {line!r}")
            else:
                self.assertIn(POWER_LABEL, line.lower(), f"unlabeled power figure at line {i + 1}: {line!r}")


if __name__ == "__main__":
    unittest.main()
