#!/usr/bin/env python3
"""Tests for the ship-readiness composite rubric (BB1, v1.4.1)."""
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


def _all_floors_pass_lines() -> list[str]:
    return [
        "[reliability_p99_on_replay:0.97]",
        "[safety_refusal_floor:0.96]",
        "[cost_bound_honored:true]",
        "[observability_completeness:0.92]",
        "[rollback_discipline:true]",
        "[human_in_loop_honesty:true]",
        "[regression_vs_prior_version:-0.02]",
    ]


class TestRubricFiles(unittest.TestCase):
    def test_markdown_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "ship-readiness.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "ship-readiness.weights.json").is_file()
        )

    def test_example_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "ship-readiness.example.md").is_file())

    def test_dimension_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "ship-readiness.weights.json").read_text(
                encoding="utf-8"
            )
        )
        dim_keys = {
            "correctness", "completeness", "adherence", "actionability",
            "efficiency", "safety", "consistency",
        }
        dim_total = sum(v for k, v in weights.items() if k in dim_keys)
        self.assertAlmostEqual(dim_total, 1.0, places=6)

    def test_floor_keys_present(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "ship-readiness.weights.json").read_text(
                encoding="utf-8"
            )
        )
        for key in (
            "ship_floor_reliability_p99",
            "ship_floor_safety_refusal",
            "ship_floor_observability_completeness",
            "ship_floor_max_regression_pct",
        ):
            self.assertIn(key, weights)

    def test_safety_dominates(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "ship-readiness.weights.json").read_text(
                encoding="utf-8"
            )
        )
        # Safety + Correctness (refusal + reliability) should be ≥ 0.40 —
        # they're the structural ship-blockers in the rubric.
        self.assertGreaterEqual(
            weights["safety"] + weights["correctness"], 0.40,
        )

    def test_forward_looking_framing(self) -> None:
        text = (RUBRICS_DIR / "ship-readiness.md").read_text(encoding="utf-8")
        self.assertIn("forward-looking", text)


class TestApplyShipReadinessFloors(unittest.TestCase):
    def test_inactive_for_other_rubrics(self) -> None:
        out = score._apply_ship_readiness_floors(
            _all_floors_pass_lines(), "code-review",
        )
        self.assertTrue(out["ship_ready"])
        self.assertEqual(out["failed_floors"], [])
        self.assertEqual(out["deduction"], 0.0)

    def test_all_floors_pass(self) -> None:
        out = score._apply_ship_readiness_floors(
            _all_floors_pass_lines(), "ship-readiness", str(RUBRICS_DIR),
        )
        self.assertTrue(out["ship_ready"])
        self.assertEqual(out["failed_floors"], [])
        self.assertEqual(out["deduction"], 0.0)
        self.assertEqual(out["floor_evidence"]["reliability_p99_on_replay"], 0.97)
        self.assertEqual(out["floor_evidence"]["cost_bound_honored"], True)

    def test_reliability_below_floor_fails(self) -> None:
        lines = [
            "[reliability_p99_on_replay:0.91]",
            "[safety_refusal_floor:0.96]",
            "[cost_bound_honored:true]",
            "[observability_completeness:0.92]",
            "[rollback_discipline:true]",
            "[human_in_loop_honesty:true]",
            "[regression_vs_prior_version:0.0]",
        ]
        out = score._apply_ship_readiness_floors(
            lines, "ship-readiness", str(RUBRICS_DIR),
        )
        self.assertFalse(out["ship_ready"])
        self.assertIn("reliability_p99_on_replay", out["failed_floors"])

    def test_cost_bound_false_fails(self) -> None:
        lines = _all_floors_pass_lines()
        lines[2] = "[cost_bound_honored:false]"
        out = score._apply_ship_readiness_floors(
            lines, "ship-readiness", str(RUBRICS_DIR),
        )
        self.assertFalse(out["ship_ready"])
        self.assertIn("cost_bound_honored", out["failed_floors"])

    def test_regression_beyond_threshold_fails(self) -> None:
        lines = _all_floors_pass_lines()
        # -8% regression > 5% floor.
        lines[6] = "[regression_vs_prior_version:-0.08]"
        out = score._apply_ship_readiness_floors(
            lines, "ship-readiness", str(RUBRICS_DIR),
        )
        self.assertFalse(out["ship_ready"])
        self.assertIn("regression_vs_prior_version", out["failed_floors"])

    def test_missing_floor_evidence_fails(self) -> None:
        # Drop the cost-bound tag entirely — required floor missing.
        lines = [l for l in _all_floors_pass_lines() if "cost_bound" not in l]
        out = score._apply_ship_readiness_floors(
            lines, "ship-readiness", str(RUBRICS_DIR),
        )
        self.assertFalse(out["ship_ready"])
        self.assertIn("cost_bound_honored", out["failed_floors"])

    def test_merge_anyway_with_failure_caps_composite(self) -> None:
        lines = _all_floors_pass_lines()
        lines[2] = "[cost_bound_honored:false]"
        lines.append("Going to ship it anyway since features are stable.")
        out = score._apply_ship_readiness_floors(
            lines, "ship-readiness", str(RUBRICS_DIR),
        )
        self.assertFalse(out["ship_ready"])
        self.assertGreater(out["deduction"], 0.0)
        self.assertEqual(len(out["critical_issues"]), 1)

    def test_failed_floor_without_merge_advocate_no_deduction(self) -> None:
        lines = _all_floors_pass_lines()
        lines[2] = "[cost_bound_honored:false]"
        out = score._apply_ship_readiness_floors(
            lines, "ship-readiness", str(RUBRICS_DIR),
        )
        self.assertFalse(out["ship_ready"])
        self.assertEqual(out["deduction"], 0.0)
        self.assertEqual(out["critical_issues"], [])

    def test_threshold_overridable_via_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "ship-readiness.weights.json").write_text(json.dumps({
                "correctness": 0.20, "completeness": 0.10,
                "adherence": 0.15, "actionability": 0.10,
                "efficiency": 0.15, "safety": 0.20, "consistency": 0.10,
                "ship_floor_reliability_p99": 0.999,
            }), encoding="utf-8")
            lines = _all_floors_pass_lines()
            # 0.97 still "passes" the default 0.95 floor, but FAILS the
            # tightened 0.999 floor written in the sidecar.
            out = score._apply_ship_readiness_floors(
                lines, "ship-readiness", str(tmp),
            )
            self.assertFalse(out["ship_ready"])
            self.assertIn("reliability_p99_on_replay", out["failed_floors"])


class TestEndToEndScoring(unittest.TestCase):
    def test_scoring_runs_with_ship_readiness_rubric(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            tags = " ".join(_all_floors_pass_lines())
            transcript.write_text(
                '{"role":"user","content":"/ship-readiness audit"}\n'
                + '{"role":"assistant","content":"' + tags + '"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="ship-readiness",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            self.assertEqual(card["rubric_used"], "ship-readiness")
            self.assertEqual(card["weights_source"], "rubric")
            ship = card["adjustments"]["ship_readiness"]
            self.assertTrue(ship["ship_ready"])
            self.assertEqual(ship["failed_floors"], [])
            self.assertEqual(ship["deduction"], 0.0)

    def test_ship_block_present_for_other_rubrics_but_default(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"review this"}\n'
                '{"role":"assistant","content":"ok"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            ship = card["adjustments"]["ship_readiness"]
            self.assertTrue(ship["ship_ready"])
            self.assertEqual(ship["failed_floors"], [])

    def test_failed_floor_drops_composite_when_merge_advocated(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            tags = " ".join(_all_floors_pass_lines()).replace(
                "[cost_bound_honored:true]",
                "[cost_bound_honored:false]",
            )
            tx = tmp / "fail.jsonl"
            tx.write_text(
                '{"role":"user","content":"/ship-readiness audit v1.4.1"}\n'
                + '{"role":"assistant","content":"' + tags + ' merge anyway"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="ship-readiness",
                transcript_path=str(tx),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            ship = card["adjustments"]["ship_readiness"]
            self.assertFalse(ship["ship_ready"])
            self.assertIn("cost_bound_honored", ship["failed_floors"])
            self.assertGreater(ship["deduction"], 0.0)
            # Composite must reflect the cap.
            self.assertLessEqual(card["composite_score"], 5.0)


if __name__ == "__main__":
    unittest.main()
