#!/usr/bin/env python3
"""Tests for the perception-reality drift extension (BB2, v1.4.1)."""
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


class TestComputePerceptionRealityDrift(unittest.TestCase):
    def test_inactive_for_other_rubrics(self) -> None:
        lines = ["perception_value=$100.00", "reality_value=$50.00"]
        out = score._compute_perception_reality_drift(lines, "code-review")
        self.assertEqual(out["drift_magnitude"], 0.0)
        self.assertFalse(out["drift_flag"])

    def test_no_markers_no_drift(self) -> None:
        lines = ["[user] hello", "[seller] sure"]
        out = score._compute_perception_reality_drift(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertEqual(out["perception_value"], 0.0)
        self.assertEqual(out["reality_value"], 0.0)
        self.assertEqual(out["drift_magnitude"], 0.0)
        self.assertFalse(out["drift_flag"])

    def test_only_one_side_no_drift_flag(self) -> None:
        # When only perception is present, drift can't be evaluated.
        lines = ["perception_value=$100.00"]
        out = score._compute_perception_reality_drift(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertEqual(out["perception_value"], 100.0)
        self.assertEqual(out["reality_value"], 0.0)
        self.assertFalse(out["drift_flag"])

    def test_drift_under_threshold_no_flag(self) -> None:
        lines = ["perception_value=$100.00", "reality_value=$99.80"]
        out = score._compute_perception_reality_drift(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertAlmostEqual(out["drift_magnitude"], 0.20, places=2)
        self.assertFalse(out["drift_flag"])

    def test_drift_over_threshold_flagged(self) -> None:
        lines = ["perception_value=$100.00", "reality_value=$95.00"]
        out = score._compute_perception_reality_drift(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertEqual(out["drift_magnitude"], 5.0)
        self.assertTrue(out["drift_flag"])

    def test_threshold_overridable_via_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "project-deal-commerce.weights.json").write_text(
                json.dumps({
                    "correctness": 0.25, "completeness": 0.15,
                    "adherence": 0.15, "actionability": 0.10,
                    "efficiency": 0.05, "safety": 0.20,
                    "consistency": 0.10,
                    "drift_flag_threshold": 0.10,
                }), encoding="utf-8",
            )
            lines = ["perception_value=$100.00", "reality_value=$99.80"]
            out = score._compute_perception_reality_drift(
                lines, "project-deal-commerce", str(tmp),
            )
            # Now 0.20 drift exceeds the lowered 0.10 threshold.
            self.assertEqual(out["drift_magnitude"], 0.20)
            self.assertTrue(out["drift_flag"])

    def test_perception_and_reality_summed_when_multiple_markers(self) -> None:
        lines = [
            "perception_value=$50.00",
            "perception_value=$50.00",
            "reality_value=$95.00",
        ]
        out = score._compute_perception_reality_drift(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertEqual(out["perception_value"], 100.0)
        self.assertEqual(out["reality_value"], 95.0)
        self.assertEqual(out["drift_magnitude"], 5.0)


class TestEndToEndScoring(unittest.TestCase):
    def test_drift_block_present_in_scorecard(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            tx = tmp / "tx.jsonl"
            tx.write_text(
                '{"role":"buyer","content":"perception_value=$100.00"}\n'
                '{"role":"seller","content":"reality_value=$95.00"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="project-deal-commerce",
                transcript_path=str(tx),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            drift = card["adjustments"]["perception_reality_drift"]
            self.assertEqual(drift["drift_magnitude"], 5.0)
            self.assertTrue(drift["drift_flag"])
            self.assertEqual(drift["perception_value"], 100.0)
            self.assertEqual(drift["reality_value"], 95.0)

    def test_drift_block_default_when_no_markers(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            tx = tmp / "tx.jsonl"
            tx.write_text(
                '{"role":"buyer","content":"counter $50"}\n'
                '{"role":"seller","content":"settle"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="project-deal-commerce",
                transcript_path=str(tx),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            drift = card["adjustments"]["perception_reality_drift"]
            self.assertEqual(drift["drift_magnitude"], 0.0)
            self.assertFalse(drift["drift_flag"])

    def test_drift_block_is_default_for_non_commerce_rubrics(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            tx = tmp / "tx.jsonl"
            tx.write_text(
                '{"role":"user","content":"perception_value=$100.00"}\n'
                '{"role":"assistant","content":"reality_value=$50.00"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(tx),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            drift = card["adjustments"]["perception_reality_drift"]
            self.assertEqual(drift["drift_magnitude"], 0.0)
            self.assertFalse(drift["drift_flag"])
            # Inactive — no parsing for non-commerce rubrics.
            self.assertEqual(drift["perception_value"], 0.0)


if __name__ == "__main__":
    unittest.main()
