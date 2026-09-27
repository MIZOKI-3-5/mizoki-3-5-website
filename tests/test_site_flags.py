"""SITE_EVENTS / PILOT_FORM / LEARN_PAGES default OFF — fail-if-flipped, asserted
on the SOURCE (inspect + ast), not just the runtime value. Run 1 item 1.F
(2026-09-02); shape copied from services/net-yield/test_flags.py.

Baseline moved 2026-09-02 (Lane 5 S4): a third flag, LEARN_PAGES, was added to
site_flags.py, so the exact-count and exact-snapshot assertions below name three
flags instead of two. The intent is unchanged — EXACTLY this many flag reads,
EXACTLY this snapshot — a fourth flag must move this baseline again on purpose
(rule 01 "moving a baseline is not the same as weakening a guard")."""
from __future__ import annotations

import ast
import inspect
import os
import unittest
from unittest import mock

from mizoki_runtime import site_flags


class TestLiteralDefaultPinnedInCode(unittest.TestCase):
    def test_literal_default_pinned_in_source(self) -> None:
        src = inspect.getsource(site_flags)
        self.assertIn('os.environ.get(SITE_EVENTS_ENV, "false")', src)
        self.assertIn('os.environ.get(PILOT_FORM_ENV, "false")', src)
        self.assertIn('os.environ.get(LEARN_PAGES_ENV, "false")', src)
        self.assertEqual(site_flags.SITE_EVENTS_ENV, "SITE_EVENTS")
        self.assertEqual(site_flags.PILOT_FORM_ENV, "PILOT_FORM")
        self.assertEqual(site_flags.LEARN_PAGES_ENV, "LEARN_PAGES")

    def test_ast_default_argument_is_the_string_false(self) -> None:
        """Reformatting cannot dodge this; only a real default flip can."""
        tree = ast.parse(inspect.getsource(site_flags))
        seen = 0
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get" and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "environ"):
                self.assertEqual(len(node.args), 2, ast.dump(node))
                default = node.args[1]
                self.assertIsInstance(default, ast.Constant)
                self.assertEqual(default.value, "false")
                seen += 1
        self.assertEqual(seen, 3, "expected exactly three flag reads (SITE_EVENTS, PILOT_FORM, LEARN_PAGES)")


class TestRuntimeBothDirections(unittest.TestCase):
    def test_non_enabling_values_keep_the_flags_off(self) -> None:
        for value in site_flags.NON_ENABLING_VALUES:
            with mock.patch.dict(os.environ, {"SITE_EVENTS": value, "PILOT_FORM": value, "LEARN_PAGES": value}, clear=False):
                self.assertFalse(site_flags.site_events_enabled(), value)
                self.assertFalse(site_flags.pilot_form_enabled(), value)
                self.assertFalse(site_flags.learn_pages_enabled(), value)

    def test_enabling_values_turn_the_flags_on(self) -> None:
        for value in site_flags.ENABLING_VALUES:
            with mock.patch.dict(os.environ, {"SITE_EVENTS": value, "PILOT_FORM": value, "LEARN_PAGES": value}, clear=False):
                self.assertTrue(site_flags.site_events_enabled(), value)
                self.assertTrue(site_flags.pilot_form_enabled(), value)
                self.assertTrue(site_flags.learn_pages_enabled(), value)

    def test_unset_is_off(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("SITE_EVENTS", "PILOT_FORM", "LEARN_PAGES")}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(site_flags.snapshot(),
                             {"site_events": False, "pilot_form": False, "learn_pages": False})


if __name__ == "__main__":
    unittest.main()
