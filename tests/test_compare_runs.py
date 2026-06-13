#!/usr/bin/env python3
"""Tests for /judge --compare-runs (N8)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

import compare  # noqa: E402


def _card(
    skill: str = "code-review",
    timestamp: str = "2026-04-20T00:00:00Z",
    composite: float = 8.0,
    grade: str = "B+",
    dim_scores: Dict[str, int] | None = None,
    transcript_lines: int = 50,
) -> Dict[str, Any]:
    base = {dim: 8 for dim in compare.DIMENSIONS}
    if dim_scores:
        base.update(dim_scores)
    return {
        "$schema": "https://proofloop.dev/schemas/scorecard.v1.json",
        "schemaVersion": "1.0.0",
        "skill": skill,
        "timestamp": timestamp,
        "composite_score": composite,
        "grade": grade,
        "dimensions": {dim: {"score": s} for dim, s in base.items()},
        "transcript_lines": transcript_lines,
    }


def _write(card: Dict[str, Any]) -> Path:
    fd, raw = tempfile.mkstemp(suffix=".json")
    with open(fd, "w", encoding="utf-8") as handle:
        json.dump(card, handle)
    return Path(raw)


class TestDiff(unittest.TestCase):
    def test_dimension_deltas(self) -> None:
        a = _card(composite=8.0, dim_scores={"correctness": 9, "safety": 10})
        b = _card(composite=7.0, dim_scores={"correctness": 7, "safety": 9})
        diff = compare.diff_dimensions(a, b)
        self.assertEqual(diff["correctness"], (9, 7, -2))
        self.assertEqual(diff["safety"], (10, 9, -1))

    def test_missing_dimension_yields_none(self) -> None:
        a = {"dimensions": {}}
        b = _card()
        diff = compare.diff_dimensions(a, b)
        for dim in compare.DIMENSIONS:
            self.assertEqual(diff[dim][0], None)
            self.assertEqual(diff[dim][2], None)


class TestNarrative(unittest.TestCase):
    def test_composite_regression_trigger(self) -> None:
        a = _card(composite=8.5)
        b = _card(composite=7.9)  # delta = -0.6
        notes = compare.build_narrative(a, b)
        self.assertTrue(any("composite dropped" in n for n in notes))

    def test_memory_growth_trigger(self) -> None:
        a = _card(transcript_lines=30)   # ~2.4k pseudo-bytes
        b = _card(transcript_lines=600)  # ~48k pseudo-bytes → grew ~45k
        notes = compare.build_narrative(a, b)
        self.assertTrue(any("memory block grew" in n for n in notes))

    def test_consistency_slide_trigger(self) -> None:
        a = _card(dim_scores={"consistency": 9})
        b = _card(dim_scores={"consistency": 5})  # drop of 4
        notes = compare.build_narrative(a, b)
        self.assertTrue(any("consistency slid" in n for n in notes))

    def test_hard_drops_trigger(self) -> None:
        a = _card(dim_scores={"correctness": 10})
        b = _card(dim_scores={"correctness": 5})  # drop of 5
        notes = compare.build_narrative(a, b)
        self.assertTrue(any("hard regressions" in n for n in notes))

    def test_no_regression_neutral_narrative(self) -> None:
        a = _card(composite=8.0)
        b = _card(composite=8.05)
        notes = compare.build_narrative(a, b)
        self.assertTrue(any("no notable regressions" in n for n in notes))


class TestCli(unittest.TestCase):
    def test_exit_zero_on_improvement(self) -> None:
        a = _write(_card(composite=7.0))
        b = _write(_card(composite=8.0))
        try:
            rc = compare.main(["--run-a", str(a), "--run-b", str(b)])
            self.assertEqual(rc, 0)
        finally:
            a.unlink(); b.unlink()

    def test_exit_two_on_regression(self) -> None:
        a = _write(_card(composite=8.0))
        b = _write(_card(composite=7.0))  # delta = -1.0 <= -0.3
        try:
            rc = compare.main(["--run-a", str(a), "--run-b", str(b)])
            self.assertEqual(rc, 2)
        finally:
            a.unlink(); b.unlink()

    def test_missing_file_exits_one(self) -> None:
        a = _write(_card())
        try:
            rc = compare.main(["--run-a", str(a), "--run-b", "/tmp/verdict-compare-missing.json"])
            self.assertEqual(rc, 1)
        finally:
            a.unlink()

    def test_json_format_output(self) -> None:
        import io, contextlib
        a = _write(_card(composite=7.0))
        b = _write(_card(composite=8.0))
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                compare.main([
                    "--run-a", str(a), "--run-b", str(b), "--format", "json",
                ])
            payload = json.loads(buf.getvalue())
            self.assertIn("dimensions", payload)
            self.assertIn("narrative", payload)
            self.assertIn("run_a", payload)
            self.assertIn("run_b", payload)
        finally:
            a.unlink(); b.unlink()


class TestReportRender(unittest.TestCase):
    def test_report_contains_narrative(self) -> None:
        a = _card(composite=8.0, dim_scores={"correctness": 9})
        b = _card(composite=7.0, dim_scores={"correctness": 6})  # composite drop
        report = compare.format_report(a, b)
        self.assertIn("composite dropped", report)
        self.assertIn("dimension", report)
        self.assertIn("correctness", report)


if __name__ == "__main__":
    unittest.main()
