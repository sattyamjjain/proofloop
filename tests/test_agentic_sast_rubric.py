#!/usr/bin/env python3
"""Tests for Agentic SAST + Brier calibration rubric (AA2)."""
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
        self.assertTrue((RUBRICS_DIR / "agentic-sast-confidence.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "agentic-sast-confidence.weights.json").is_file()
        )

    def test_source_signal_present(self) -> None:
        text = (RUBRICS_DIR / "agentic-sast-confidence.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("source_signal:", text)
        self.assertIn("gitlab-18-11-agentic-ai", text)

    def test_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "agentic-sast-confidence.weights.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


class TestApplyBrierCalibration(unittest.TestCase):
    def test_inactive_for_other_rubrics(self) -> None:
        lines = [
            "[confidence:0.95]",
            "[ground_truth:true]",
        ]
        out = score._apply_brier_calibration(lines, "code-review")
        self.assertIsNone(out["brier_loss"])
        self.assertEqual(out["pair_count"], 0)

    def test_no_pairs_returns_none(self) -> None:
        lines = ["[confidence:0.5]", "no truth here"]
        out = score._apply_brier_calibration(lines, "agentic-sast-confidence")
        self.assertIsNone(out["brier_loss"])

    def test_perfect_calibration_zero_loss(self) -> None:
        lines = [
            "[confidence:1.0]",
            "[ground_truth:true]",
            "[confidence:0.0]",
            "[ground_truth:false]",
        ]
        out = score._apply_brier_calibration(lines, "agentic-sast-confidence")
        self.assertEqual(out["brier_loss"], 0.0)
        self.assertEqual(out["pair_count"], 2)

    def test_worst_calibration_loss_one(self) -> None:
        lines = [
            "[confidence:1.0]",
            "[ground_truth:false]",
            "[confidence:0.0]",
            "[ground_truth:true]",
        ]
        out = score._apply_brier_calibration(lines, "agentic-sast-confidence")
        self.assertEqual(out["brier_loss"], 1.0)
        self.assertEqual(out["pair_count"], 2)

    def test_mid_calibration(self) -> None:
        # confidence 0.5 on a true outcome: (0.5 - 1.0)^2 = 0.25
        lines = [
            "[confidence:0.5]",
            "[ground_truth:true]",
        ]
        out = score._apply_brier_calibration(lines, "agentic-sast-confidence")
        self.assertEqual(out["brier_loss"], 0.25)

    def test_unmatched_confidence_dropped(self) -> None:
        # Two confidence tags before one ground_truth — only the most
        # recent confidence pairs with the truth.
        lines = [
            "[confidence:0.9]",
            "[confidence:0.1]",
            "[ground_truth:true]",
        ]
        out = score._apply_brier_calibration(lines, "agentic-sast-confidence")
        self.assertEqual(out["brier_loss"], (0.1 - 1.0) ** 2)
        self.assertEqual(out["pair_count"], 1)

    def test_invalid_confidence_skipped(self) -> None:
        lines = [
            "[confidence:1.5]",  # out of range; ignored
            "[confidence:0.7]",
            "[ground_truth:true]",
        ]
        out = score._apply_brier_calibration(lines, "agentic-sast-confidence")
        # Only 0.7 paired with true → (0.7 - 1.0)^2 = 0.09
        self.assertAlmostEqual(out["brier_loss"], 0.09, places=4)


class TestEndToEndScoring(unittest.TestCase):
    def test_canonical_fixture_runs(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="agentic-sast-confidence",
                transcript_path=str(FIXTURES_DIR / "agentic-sast-trace.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            brier = card["adjustments"]["brier_calibration"]
            self.assertEqual(brier["pair_count"], 10)
            self.assertIsNotNone(brier["brier_loss"])
            self.assertGreaterEqual(brier["brier_loss"], 0.0)
            self.assertLessEqual(brier["brier_loss"], 1.0)
            self.assertEqual(card["weights_source"], "rubric")
            self.assertEqual(card["rubric_used"], "agentic-sast-confidence")

    def test_fixture_brier_loss_in_calibrated_range(self) -> None:
        """The fixture is constructed so the agent looks reasonably calibrated."""
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="agentic-sast-confidence",
                transcript_path=str(FIXTURES_DIR / "agentic-sast-trace.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            brier = card["adjustments"]["brier_calibration"]["brier_loss"]
            # Fixture was constructed for ~0.05-0.20 calibration band.
            self.assertLess(brier, 0.25,
                            f"fixture should be calibrated; got Brier={brier}")

    def test_brier_inactive_for_other_rubrics(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"[confidence:0.9]"}\n'
                '{"role":"system","content":"[ground_truth:true]"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            self.assertIsNone(
                card["adjustments"]["brier_calibration"]["brier_loss"]
            )


if __name__ == "__main__":
    unittest.main()
