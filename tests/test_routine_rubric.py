#!/usr/bin/env python3
"""Tests for the routine-execution rubric (CC4, v1.4.2)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import score  # noqa: E402


class TestRubricFiles(unittest.TestCase):
    def test_markdown_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "routine-execution.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "routine-execution.weights.json").is_file()
        )

    def test_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "routine-execution.weights.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_completeness_dominates(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "routine-execution.weights.json").read_text(
                encoding="utf-8"
            )
        )
        # Completeness is the load-bearing dimension for autonomous runs.
        self.assertGreaterEqual(weights["completeness"], 0.20)

    def test_research_preview_called_out(self) -> None:
        text = (RUBRICS_DIR / "routine-execution.md").read_text(
            encoding="utf-8"
        )
        # Important honesty correction: Routines is research preview,
        # NOT GA. Rubric must reflect that.
        self.assertIn("research preview", text.lower())
        self.assertNotIn("general availability", text.lower())

    def test_source_signal_to_anthropic(self) -> None:
        text = (RUBRICS_DIR / "routine-execution.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("anthropic.com/news/routines", text)


class TestEndToEndScoring(unittest.TestCase):
    def test_routine_fixture_runs(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="routine-execution",
                transcript_path=str(FIXTURES_DIR / "routine-trace.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            self.assertEqual(card["rubric_used"], "routine-execution")
            self.assertEqual(card["weights_source"], "rubric")

    def test_consistency_routine_aware(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="routine-execution",
                transcript_path=str(FIXTURES_DIR / "routine-trace.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            consistency = card["dimensions"]["consistency"]
            self.assertIn("routine", consistency["justification"].lower())


if __name__ == "__main__":
    unittest.main()
