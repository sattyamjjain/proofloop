#!/usr/bin/env python3
"""Tests for scripts/benchmark_pack.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import benchmark_pack as bp  # noqa: E402


class TestGradeOrder(unittest.TestCase):
    def test_rank_A_above_B(self) -> None:
        self.assertGreater(bp._rank("A"), bp._rank("B"))

    def test_rank_A_plus_top(self) -> None:
        for grade in ("A", "A-", "B+", "B", "F"):
            self.assertGreater(bp._rank("A+"), bp._rank(grade))

    def test_rank_unknown_returns_negative_one(self) -> None:
        self.assertEqual(bp._rank("Z"), -1)


class TestCheck(unittest.TestCase):
    def _card(self, composite: float, grade: str, dims: dict = None) -> dict:
        return {
            "composite_score": composite,
            "grade": grade,
            "dimensions": {d: {"score": s} for d, s in (dims or {}).items()},
        }

    def test_composite_min_pass(self) -> None:
        ok, errs = bp._check({"expected_composite_min": 7.0}, self._card(8.0, "B+"))
        self.assertTrue(ok)
        self.assertEqual(errs, [])

    def test_composite_min_fail(self) -> None:
        ok, errs = bp._check({"expected_composite_min": 9.0}, self._card(8.0, "B+"))
        self.assertFalse(ok)
        self.assertTrue(any("expected_min" in e for e in errs))

    def test_composite_max_fail(self) -> None:
        ok, errs = bp._check({"expected_composite_max": 5.0}, self._card(8.0, "B+"))
        self.assertFalse(ok)

    def test_grade_min_pass(self) -> None:
        ok, errs = bp._check({"expected_grade_min": "B"}, self._card(8.5, "A-"))
        self.assertTrue(ok)

    def test_grade_min_fail(self) -> None:
        ok, errs = bp._check({"expected_grade_min": "A"}, self._card(7.0, "B"))
        self.assertFalse(ok)

    def test_dimension_min_pass(self) -> None:
        ok, _ = bp._check(
            {"expected_dimension_min": {"safety": 8}},
            self._card(8.0, "B+", {"safety": 9}),
        )
        self.assertTrue(ok)

    def test_dimension_max_fail(self) -> None:
        ok, errs = bp._check(
            {"expected_dimension_max": {"completeness": 5}},
            self._card(8.0, "B+", {"completeness": 9}),
        )
        self.assertFalse(ok)
        self.assertTrue(any("completeness" in e for e in errs))


class TestShippedManifest(unittest.TestCase):
    """Running the shipped manifest must always succeed (CI gate)."""

    def test_shipped_manifest_passes(self) -> None:
        code = bp.main(["benchmark_pack.py"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
