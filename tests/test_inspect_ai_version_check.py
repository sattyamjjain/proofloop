#!/usr/bin/env python3
"""Tests for skills/judge/adapters/inspect_ai_log.py version-pin honesty.

Mocks ``inspect_ai.__version__`` to representative values and asserts
the warning fires only when the installed version is outside the
tested range :data:`INSPECT_AI_SUPPORTED_RANGE`.
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))

from adapters import inspect_ai_log  # noqa: E402


class TestParseVersionTuple(unittest.TestCase):
    def test_simple_three_component(self) -> None:
        self.assertEqual(inspect_ai_log._parse_version_tuple("0.3.214"), (0, 3, 214))

    def test_strips_local_suffix(self) -> None:
        self.assertEqual(
            inspect_ai_log._parse_version_tuple("0.3.180+local"), (0, 3, 180)
        )

    def test_pads_two_component(self) -> None:
        self.assertEqual(inspect_ai_log._parse_version_tuple("0.4"), (0, 4, 0))

    def test_invalid_returns_none(self) -> None:
        self.assertIsNone(inspect_ai_log._parse_version_tuple("not.a.version"))
        self.assertIsNone(inspect_ai_log._parse_version_tuple(""))


class TestCheckVersionInjectable(unittest.TestCase):
    """Use the *version* argument to side-step lazy-import."""

    def test_in_range_no_warning(self) -> None:
        self.assertIsNone(inspect_ai_log._check_inspect_ai_version("0.3.214"))

    def test_at_lower_bound_no_warning(self) -> None:
        self.assertIsNone(inspect_ai_log._check_inspect_ai_version("0.3.180"))

    def test_below_lower_bound_warns(self) -> None:
        warning = inspect_ai_log._check_inspect_ai_version("0.3.99")
        self.assertIsNotNone(warning)
        self.assertIn("0.3.99", warning)
        self.assertIn(inspect_ai_log.INSPECT_AI_SUPPORTED_RANGE, warning)

    def test_at_upper_exclusive_warns(self) -> None:
        warning = inspect_ai_log._check_inspect_ai_version("0.4.0")
        self.assertIsNotNone(warning)
        self.assertIn("0.4.0", warning)

    def test_above_upper_warns(self) -> None:
        warning = inspect_ai_log._check_inspect_ai_version("1.0.0")
        self.assertIsNotNone(warning)

    def test_unparseable_returns_none(self) -> None:
        self.assertIsNone(inspect_ai_log._check_inspect_ai_version("garbage"))

    def test_none_when_version_arg_blank(self) -> None:
        # Falls through to lazy-import; on dev hosts inspect_ai may
        # not be installed — function returns None either way.
        result = inspect_ai_log._check_inspect_ai_version("")
        self.assertIsNone(result)


class TestSupportedRangeConstant(unittest.TestCase):
    def test_constant_advertises_range(self) -> None:
        self.assertEqual(
            inspect_ai_log.INSPECT_AI_SUPPORTED_RANGE,
            ">=0.3.180,<0.4.0",
        )


class TestOneShotWarningGate(unittest.TestCase):
    def setUp(self) -> None:
        inspect_ai_log._reset_version_warning_guard()

    def test_warning_emitted_only_once(self) -> None:
        err = io.StringIO()
        with patch.object(
            inspect_ai_log, "_check_inspect_ai_version",
            return_value="[verdict] dummy warning",
        ), patch("sys.stderr", err):
            inspect_ai_log._maybe_warn_inspect_ai_version()
            inspect_ai_log._maybe_warn_inspect_ai_version()
            inspect_ai_log._maybe_warn_inspect_ai_version()
        self.assertEqual(err.getvalue().count("dummy warning"), 1)

    def test_no_warning_when_check_returns_none(self) -> None:
        err = io.StringIO()
        with patch.object(
            inspect_ai_log, "_check_inspect_ai_version", return_value=None,
        ), patch("sys.stderr", err):
            inspect_ai_log._maybe_warn_inspect_ai_version()
        self.assertEqual(err.getvalue(), "")


class TestExtractLinesTriggersWarning(unittest.TestCase):
    def setUp(self) -> None:
        inspect_ai_log._reset_version_warning_guard()

    def test_first_extract_call_consults_version(self) -> None:
        err = io.StringIO()
        # Stub _check_inspect_ai_version so extract_lines prints
        # something deterministic regardless of host environment.
        with patch.object(
            inspect_ai_log, "_check_inspect_ai_version",
            return_value="[verdict] forced-out-of-range",
        ), patch("sys.stderr", err):
            # extract_lines on a missing file still triggers the
            # version check before short-circuiting.
            inspect_ai_log.extract_lines("/tmp/verdict-no-such-inspect.json")
        self.assertIn("forced-out-of-range", err.getvalue())


class TestNoStaleVersionReferenceInChangelog(unittest.TestCase):
    """Z3 honesty audit: no '0.4.0' string anywhere in CHANGELOG."""

    def test_changelog_has_no_0_4_0_reference(self) -> None:
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        # Allow the literal string in the version-pin doc itself if a
        # future entry references it deliberately, but for now nothing
        # should claim Inspect AI 0.4.0 as released.
        self.assertNotIn("inspect_ai 0.4.0", changelog.lower())
        self.assertNotIn("inspect-ai 0.4.0", changelog.lower())


if __name__ == "__main__":
    unittest.main()
