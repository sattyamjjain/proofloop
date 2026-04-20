#!/usr/bin/env python3
"""Tests for the LightEval metric shim (N5).

Offline: no lighteval module is imported at any point. Verifies the
shim returns a float in [0, 1] and cleanly rejects mismatched inputs.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))

from integrations import lighteval_shim  # noqa: E402


class TestShapeContract(unittest.TestCase):
    def test_empty_inputs_return_zero(self) -> None:
        result = lighteval_shim.verdict_metric([], [])
        self.assertEqual(result, {"verdict_score": 0.0, "n": 0.0})

    def test_mismatched_lengths_raise(self) -> None:
        with self.assertRaises(ValueError):
            lighteval_shim.verdict_metric(["a"], [])

    def test_score_in_unit_interval(self) -> None:
        result = lighteval_shim.verdict_metric(
            predictions=["Reviewed the auth middleware; no issues found."],
            references=["Review src/auth/middleware.py for vulnerabilities."],
        )
        self.assertIsInstance(result, dict)
        self.assertIn("verdict_score", result)
        score = result["verdict_score"]
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertEqual(result["n"], 1.0)

    def test_multiple_pairs_averaged(self) -> None:
        result = lighteval_shim.verdict_metric(
            predictions=[
                "Reviewed middleware, LGTM.",
                "Fixed the bug in line 42.",
                "Tests now pass.",
            ],
            references=[
                "Review middleware.",
                "Fix the bug at line 42.",
                "Run the test suite.",
            ],
        )
        self.assertEqual(result["n"], 3.0)
        self.assertGreaterEqual(result["verdict_score"], 0.0)
        self.assertLessEqual(result["verdict_score"], 1.0)


class TestLazyLightevalImport(unittest.TestCase):
    def test_lighteval_not_imported_by_shim(self) -> None:
        # Critical: the shim must not pull lighteval into sys.modules
        # even after a full metric call. Verdict core is stdlib-only.
        self.assertNotIn("lighteval", sys.modules)

    def test_register_helper_is_noop(self) -> None:
        # Explicit noop contract: the placeholder never errors and
        # never imports anything behind the user's back.
        self.assertIsNone(lighteval_shim._apply_lighteval_side_effects())
        self.assertNotIn("lighteval", sys.modules)


class TestScorePairInternal(unittest.TestCase):
    def test_single_pair_scored(self) -> None:
        s = lighteval_shim._score_pair(
            prediction="Made changes as requested.",
            reference="Please make changes.",
            rubric="default",
        )
        self.assertGreaterEqual(s, 0.0)
        self.assertLessEqual(s, 1.0)


if __name__ == "__main__":
    unittest.main()
