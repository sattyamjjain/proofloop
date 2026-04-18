#!/usr/bin/env python3
"""Tests for skills/judge/scripts/against.py."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

import against  # noqa: E402


def _make_scorecard(
    skill: str,
    timestamp: str,
    composite: float,
    grade: str,
    dim_scores: dict,
) -> dict:
    return {
        "skill": skill,
        "timestamp": timestamp,
        "composite_score": composite,
        "grade": grade,
        "dimensions": {dim: {"score": score} for dim, score in dim_scores.items()},
    }


def _write_scores(tmpdir: Path, scorecards: list) -> None:
    for card in scorecards:
        path = tmpdir / f"{card['skill']}_{card['timestamp'].replace(':', '-')}.json"
        path.write_text(json.dumps(card), encoding="utf-8")


class TestAgainst(unittest.TestCase):
    def test_needs_two_scorecards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = against.main(["--skill", "x", "--scores-dir", tmp])
            self.assertEqual(code, 1)

    def test_improvement_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write_scores(Path(tmp), [
                _make_scorecard("x", "2026-04-01T00:00:00Z", 7.0, "B", {"correctness": 7}),
                _make_scorecard("x", "2026-04-02T00:00:00Z", 8.0, "B+", {"correctness": 8}),
            ])
            self.assertEqual(against.main(["--skill", "x", "--scores-dir", tmp]), 0)

    def test_regression_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write_scores(Path(tmp), [
                _make_scorecard("x", "2026-04-01T00:00:00Z", 9.0, "A", {"correctness": 9}),
                _make_scorecard("x", "2026-04-02T00:00:00Z", 7.5, "B", {"correctness": 7}),
            ])
            self.assertEqual(against.main(["--skill", "x", "--scores-dir", tmp]), 2)

    def test_flat_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write_scores(Path(tmp), [
                _make_scorecard("x", "2026-04-01T00:00:00Z", 8.0, "B+", {"correctness": 8}),
                _make_scorecard("x", "2026-04-02T00:00:00Z", 8.02, "B+", {"correctness": 8}),
            ])
            self.assertEqual(against.main(["--skill", "x", "--scores-dir", tmp]), 0)

    def test_arrow_helpers(self) -> None:
        self.assertEqual(against._arrow(0.1), "↑")
        self.assertEqual(against._arrow(-0.1), "↓")
        self.assertEqual(against._arrow(0.0), "→")

    def test_render_contains_both_timestamps(self) -> None:
        baseline = _make_scorecard("x", "2026-04-01T00:00:00Z", 7.0, "B", {"correctness": 7})
        target = _make_scorecard("x", "2026-04-02T00:00:00Z", 8.0, "B+", {"correctness": 8})
        rendered = against.render(baseline, target)
        self.assertIn("2026-04-01T00:00:00Z", rendered)
        self.assertIn("2026-04-02T00:00:00Z", rendered)
        self.assertIn("IMPROVED", rendered)


if __name__ == "__main__":
    unittest.main()
