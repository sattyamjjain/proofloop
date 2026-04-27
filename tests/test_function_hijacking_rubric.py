#!/usr/bin/env python3
"""Tests for the function-hijacking-robustness rubric (AA3 — rubric files only)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import score  # noqa: E402


class TestRubricFiles(unittest.TestCase):
    def test_markdown_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "function-hijacking-robustness.md").is_file()
        )

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "function-hijacking-robustness.weights.json").is_file()
        )

    def test_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "function-hijacking-robustness.weights.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_safety_dominates(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "function-hijacking-robustness.weights.json").read_text(
                encoding="utf-8"
            )
        )
        # Safety + Adherence carry the structural fix to function-
        # hijacking; together they should be ≥ 40%.
        self.assertGreaterEqual(weights["safety"] + weights["adherence"], 0.40)

    def test_no_arxiv_url_after_user_decision(self) -> None:
        text = (RUBRICS_DIR / "function-hijacking-robustness.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("arxiv.org/abs/2604.20994", text)

    def test_forward_looking_framing(self) -> None:
        text = (RUBRICS_DIR / "function-hijacking-robustness.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("forward-looking", text)


class TestRubricResolves(unittest.TestCase):
    def test_load_rubric_picks_up_text(self) -> None:
        name, text = score.load_rubric(
            str(RUBRICS_DIR), "function-hijacking-robustness",
        )
        self.assertEqual(name, "function-hijacking-robustness")
        self.assertIn("Function Hijacking", text)

    def test_load_rubric_weights_picks_up_sidecar(self) -> None:
        weights = score.load_rubric_weights(
            str(RUBRICS_DIR), "function-hijacking-robustness",
        )
        self.assertIsNotNone(weights)
        self.assertAlmostEqual(weights["safety"], 0.25)


class TestEndToEndScoring(unittest.TestCase):
    def test_scoring_runs_with_fhr_rubric(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"/function-hijacking-robustness audit my agent"}\n'
                '{"role":"assistant","content":"Treating tool descriptions as untrusted."}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="function-hijacking-robustness",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            self.assertEqual(card["rubric_used"], "function-hijacking-robustness")
            self.assertEqual(card["weights_source"], "rubric")


if __name__ == "__main__":
    unittest.main()
