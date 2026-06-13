#!/usr/bin/env python3
"""Tests for skills/judge/scripts/watch.py live re-scoring."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

import watch  # noqa: E402


def _card(
    skill: str,
    timestamp: str,
    composite: float,
    dim_scores: Dict[str, int],
) -> Dict[str, Any]:
    return {
        "$schema": "https://proofloop.dev/schemas/scorecard.v1.json",
        "schemaVersion": "1.0.0",
        "skill": skill,
        "timestamp": timestamp,
        "composite_score": composite,
        "grade": "B+",
        "dimensions": {dim: {"score": dim_scores.get(dim, 8)} for dim in watch.DIMENSIONS},
    }


def _write(path: Path, card: Dict[str, Any]) -> None:
    path.write_text(json.dumps(card), encoding="utf-8")


class TestDiffScorecards(unittest.TestCase):
    def test_first_run_counts_all_unchanged(self) -> None:
        card = _card("x", "2026-04-19T00:00:00Z", 8.0, {})
        self.assertEqual(watch.diff_scorecards(None, card), (0, 0, len(watch.DIMENSIONS)))

    def test_improvement_detected(self) -> None:
        prev = _card("x", "2026-04-19T00:00:00Z", 7.0, {"correctness": 7})
        curr = _card("x", "2026-04-19T00:00:01Z", 8.0, {"correctness": 9})
        improved, regressed, _unchanged = watch.diff_scorecards(prev, curr)
        self.assertEqual(improved, 1)
        self.assertEqual(regressed, 0)

    def test_regression_detected(self) -> None:
        prev = _card("x", "2026-04-19T00:00:00Z", 8.0, {"safety": 10})
        curr = _card("x", "2026-04-19T00:00:01Z", 7.0, {"safety": 6})
        improved, regressed, _ = watch.diff_scorecards(prev, curr)
        self.assertEqual(improved, 0)
        self.assertEqual(regressed, 1)

    def test_missing_dimensions_treated_unchanged(self) -> None:
        prev = {"dimensions": {}}
        curr = _card("x", "2026-04-19T00:00:01Z", 8.0, {})
        improved, regressed, unchanged = watch.diff_scorecards(prev, curr)
        self.assertEqual((improved, regressed), (0, 0))
        self.assertEqual(unchanged, len(watch.DIMENSIONS))


class TestFormatDiffHeader(unittest.TestCase):
    def test_first_run_prints_composite_only(self) -> None:
        card = _card("code-review", "2026-04-19T00:00:00Z", 8.42, {})
        text = watch.format_diff_header("code-review", None, card)
        self.assertIn("code-review", text)
        self.assertIn("first run", text)
        self.assertIn("8.42", text)

    def test_improvement_header_uses_up_arrow(self) -> None:
        prev = _card("x", "2026-04-19T00:00:00Z", 7.0, {})
        curr = _card("x", "2026-04-19T00:00:01Z", 8.5, {})
        text = watch.format_diff_header("x", prev, curr)
        self.assertIn("↑", text)
        self.assertIn("+1.50", text)

    def test_regression_header_uses_down_arrow(self) -> None:
        prev = _card("x", "2026-04-19T00:00:00Z", 9.0, {"correctness": 9})
        curr = _card("x", "2026-04-19T00:00:01Z", 7.5, {"correctness": 6})
        text = watch.format_diff_header("x", prev, curr)
        self.assertIn("↓", text)
        self.assertIn("regressed 1", text)


class TestRunPass(unittest.TestCase):
    def test_emits_header_on_first_appearance(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "scores").mkdir()
            _write(tmp / "scores" / "x_a.json",
                   _card("x", "2026-04-19T00:00:00Z", 8.0, {}))
            snapshot, headers = watch.run_pass(
                tmp / "scores", tmp / "out.html", {}, "2026-04-19 00:00 UTC",
            )
            self.assertEqual(len(headers), 1)
            self.assertIn("first run", headers[0])
            self.assertTrue((tmp / "out.html").is_file())
            self.assertEqual(len(snapshot), 1)

    def test_no_change_no_header(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            scores = tmp / "scores"
            scores.mkdir()
            card = _card("x", "2026-04-19T00:00:00Z", 8.0, {})
            _write(scores / "x_a.json", card)
            snapshot = {scores / "x_a.json": card}
            _s2, headers = watch.run_pass(scores, tmp / "out.html", snapshot, "ts")
            self.assertEqual(headers, [])

    def test_change_triggers_header_and_studio_render(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            scores = tmp / "scores"
            scores.mkdir()
            older = _card("x", "2026-04-19T00:00:00Z", 7.0, {"correctness": 7})
            newer = _card("x", "2026-04-19T00:00:01Z", 8.4, {"correctness": 9})
            _write(scores / "x_a.json", older)
            snapshot = {scores / "x_a.json": older}
            _write(scores / "x_a.json", newer)
            output = tmp / "out.html"
            _s2, headers = watch.run_pass(scores, output, snapshot, "ts")
            self.assertEqual(len(headers), 1)
            self.assertIn("↑", headers[0])
            self.assertTrue(output.is_file())

    def test_removed_file_noted(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            scores = tmp / "scores"
            scores.mkdir()
            card = _card("x", "2026-04-19T00:00:00Z", 8.0, {})
            previous = {scores / "deleted.json": card}
            _s2, headers = watch.run_pass(scores, tmp / "out.html", previous, "ts")
            self.assertTrue(any("removed" in h for h in headers))


class TestCliOncePath(unittest.TestCase):
    def test_once_exits_zero_and_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            scores = tmp / "scores"
            scores.mkdir()
            _write(scores / "x_a.json", _card("x", "2026-04-19T00:00:00Z", 8.0, {}))
            output = tmp / "out.html"
            rc = watch.main([
                "--scores-dir", str(scores),
                "--output", str(output),
                "--once", "--quiet",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())
            self.assertIn("Proofloop Studio", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
