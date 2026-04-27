#!/usr/bin/env python3
"""Tests for GPT-5.5 differential rubric (AA4) + paired-baseline helper."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import score  # noqa: E402


def _card(scores: Dict[str, int], composite: float) -> Dict[str, Any]:
    return {
        "skill": "code-review",
        "composite_score": composite,
        "dimensions": {
            dim: {"score": scores.get(dim, 7), "weight": 0.15, "weighted": 1.0,
                  "justification": ""}
            for dim in (
                "correctness", "completeness", "adherence", "actionability",
                "efficiency", "safety", "consistency",
            )
        },
    }


class TestRubricFiles(unittest.TestCase):
    def test_markdown_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "gpt-5-5-differential.md").is_file())

    def test_weights_sidecar_sums_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "gpt-5-5-differential.weights.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_source_signal_present(self) -> None:
        text = (RUBRICS_DIR / "gpt-5-5-differential.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("source_signal:", text)
        self.assertIn("cnbc.com", text)


class TestResolvePairedBaseline(unittest.TestCase):
    def test_no_change(self) -> None:
        baseline = _card({}, 7.5)
        candidate = _card({}, 7.5)
        out = score._resolve_paired_baseline(candidate, baseline)
        self.assertEqual(out["composite_delta"], 0.0)
        self.assertEqual(out["regressed_dimensions"], [])
        for dim, vals in out["per_dimension"].items():
            self.assertEqual(vals["delta"], 0.0)

    def test_uniform_improvement(self) -> None:
        baseline = _card({"correctness": 7}, 7.5)
        candidate = _card({"correctness": 9}, 8.5)
        out = score._resolve_paired_baseline(candidate, baseline)
        self.assertEqual(out["composite_delta"], 1.0)
        self.assertEqual(out["per_dimension"]["correctness"]["delta"], 2.0)
        self.assertEqual(out["regressed_dimensions"], [])

    def test_regression_detected(self) -> None:
        baseline = _card({"safety": 9}, 8.5)
        candidate = _card({"safety": 6}, 7.5)
        out = score._resolve_paired_baseline(candidate, baseline)
        self.assertIn("safety", out["regressed_dimensions"])
        self.assertEqual(out["per_dimension"]["safety"]["delta"], -3.0)

    def test_minor_regression_below_threshold_not_flagged(self) -> None:
        # Delta = -1.0, threshold = -1.5; should not be flagged.
        baseline = _card({"safety": 9}, 8.5)
        candidate = _card({"safety": 8}, 8.0)
        out = score._resolve_paired_baseline(candidate, baseline)
        self.assertEqual(out["regressed_dimensions"], [])

    def test_cohen_d_zero_when_no_variance(self) -> None:
        baseline = _card({}, 7.5)
        candidate = _card({}, 7.5)
        out = score._resolve_paired_baseline(candidate, baseline)
        # All deltas are 0; pooled stddev 0; cohen_d falls back to None.
        self.assertIsNone(out["cohen_d"])

    def test_cohen_d_present_with_variance(self) -> None:
        baseline = _card({"correctness": 6, "safety": 8}, 7.0)
        candidate = _card({"correctness": 9, "safety": 7}, 8.0)
        out = score._resolve_paired_baseline(candidate, baseline)
        self.assertIsNotNone(out["cohen_d"])

    def test_missing_dimension_in_baseline_skipped(self) -> None:
        baseline = {"composite_score": 7.0, "dimensions": {
            "correctness": {"score": 7},
            # other dims missing
        }}
        candidate = _card({"correctness": 8}, 8.0)
        out = score._resolve_paired_baseline(candidate, baseline)
        # Only correctness can be paired; the rest are silently skipped.
        self.assertIn("correctness", out["per_dimension"])
        self.assertEqual(len(out["per_dimension"]), 1)


class TestRubricResolves(unittest.TestCase):
    def test_load_rubric_picks_up_text(self) -> None:
        name, text = score.load_rubric(str(RUBRICS_DIR), "gpt-5-5-differential")
        self.assertEqual(name, "gpt-5-5-differential")
        self.assertIn("paired-comparison", text.lower())

    def test_load_rubric_weights_picks_up_sidecar(self) -> None:
        weights = score.load_rubric_weights(
            str(RUBRICS_DIR), "gpt-5-5-differential",
        )
        self.assertIsNotNone(weights)
        self.assertAlmostEqual(weights["correctness"], 0.25)


if __name__ == "__main__":
    unittest.main()
