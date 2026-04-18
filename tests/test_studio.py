#!/usr/bin/env python3
"""Tests for skills/judge/scripts/studio.py."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

import studio  # noqa: E402


def _card(skill: str, ts: str, composite: float) -> dict:
    return {
        "skill": skill,
        "timestamp": ts,
        "composite_score": composite,
        "grade": "A" if composite >= 9 else "B",
        "dimensions": {
            dim: {"score": 8}
            for dim in (
                "correctness", "completeness", "adherence", "actionability",
                "efficiency", "safety", "consistency",
            )
        },
        "critical_issues": [],
    }


class TestLoadScores(unittest.TestCase):
    def test_missing_dir_returns_empty(self) -> None:
        self.assertEqual(studio._load_scores(Path("/tmp/nonexistent")), [])

    def test_loads_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x_2026-04-01.json"
            path.write_text(json.dumps(_card("x", "2026-04-01T00:00:00Z", 9.0)))
            scores = studio._load_scores(Path(tmp))
            self.assertEqual(len(scores), 1)
            self.assertEqual(scores[0]["skill"], "x")

    def test_skips_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "bad.json").write_text("not json")
            (Path(tmp) / "good.json").write_text(
                json.dumps(_card("good", "2026-04-01T00:00:00Z", 8.0))
            )
            scores = studio._load_scores(Path(tmp))
            self.assertEqual(len(scores), 1)


class TestGroupBySkill(unittest.TestCase):
    def test_groups_and_sorts(self) -> None:
        scores = [
            _card("a", "2026-04-02T00:00:00Z", 9.0),
            _card("a", "2026-04-01T00:00:00Z", 7.0),
            _card("b", "2026-04-01T00:00:00Z", 8.0),
        ]
        grouped = studio._group_by_skill(scores)
        self.assertEqual(set(grouped), {"a", "b"})
        self.assertEqual([s["timestamp"] for s in grouped["a"]],
                         ["2026-04-01T00:00:00Z", "2026-04-02T00:00:00Z"])


class TestSvgRendering(unittest.TestCase):
    def test_radar_has_polygon(self) -> None:
        dims = {dim: {"score": 7} for dim in (
            "correctness", "completeness", "adherence", "actionability",
            "efficiency", "safety", "consistency",
        )}
        svg = studio._radar_svg(dims)
        self.assertIn("<polygon", svg)
        self.assertIn("<svg", svg)

    def test_trend_single_point(self) -> None:
        svg = studio._trend_svg([_card("x", "2026-04-01T00:00:00Z", 8.0)])
        self.assertIn("<circle", svg)

    def test_trend_empty(self) -> None:
        self.assertIn("No history", studio._trend_svg([]))

    def test_grade_letter_defaults(self) -> None:
        self.assertEqual(studio._grade_letter(""), "F")
        self.assertEqual(studio._grade_letter("A-"), "A")


class TestGenerate(unittest.TestCase):
    def test_generates_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scores_dir = Path(tmp) / "scores"
            scores_dir.mkdir()
            (scores_dir / "x.json").write_text(
                json.dumps(_card("x", "2026-04-01T00:00:00Z", 9.0))
            )
            output = Path(tmp) / "out.html"
            studio.generate(scores_dir, output, "2026-04-18 00:00 UTC")
            content = output.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", content)
            self.assertIn("Verdict Studio", content)
            self.assertIn("x", content)


if __name__ == "__main__":
    unittest.main()
