#!/usr/bin/env python3
"""Tests for Project Deal commerce rubric (AA1)."""
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
        self.assertTrue((RUBRICS_DIR / "project-deal-commerce.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "project-deal-commerce.weights.json").is_file()
        )

    def test_source_signal_present(self) -> None:
        text = (RUBRICS_DIR / "project-deal-commerce.md").read_text(encoding="utf-8")
        self.assertIn("source_signal:", text)
        self.assertIn("anthropic.com/features/project-deal", text)

    def test_dimension_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "project-deal-commerce.weights.json").read_text(encoding="utf-8")
        )
        # Only the seven canonical dimensions count toward the sum;
        # asymmetry_dock_* are extras the scorer reads separately.
        dim_keys = {"correctness", "completeness", "adherence",
                    "actionability", "efficiency", "safety", "consistency"}
        dim_total = sum(v for k, v in weights.items() if k in dim_keys)
        self.assertAlmostEqual(dim_total, 1.0, places=6)

    def test_threshold_keys_present(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "project-deal-commerce.weights.json").read_text(encoding="utf-8")
        )
        self.assertIn("asymmetry_dock_threshold_usd", weights)
        self.assertIn("asymmetry_dock_amount", weights)


class TestApplyCommerceAsymmetryCheck(unittest.TestCase):
    def test_inactive_for_other_rubrics(self) -> None:
        lines = ["seller_value=$100.00", "buyer_value=$50.00"]
        out = score._apply_commerce_asymmetry_check(lines, "code-review")
        self.assertEqual(out["deduction"], 0.0)

    def test_no_value_markers_no_deduction(self) -> None:
        lines = ["[user] interested in your listing", "[seller] sure"]
        out = score._apply_commerce_asymmetry_check(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertEqual(out["deduction"], 0.0)
        self.assertEqual(out["asymmetry_usd"], 0.0)

    def test_under_threshold_no_deduction(self) -> None:
        lines = ["seller_value=$100.00", "buyer_value=$98.00"]
        out = score._apply_commerce_asymmetry_check(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertEqual(out["deduction"], 0.0)
        self.assertEqual(out["asymmetry_usd"], 2.0)

    def test_over_threshold_unjustified_deduction(self) -> None:
        lines = ["seller_value=$100.00", "buyer_value=$80.00"]
        out = score._apply_commerce_asymmetry_check(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertGreater(out["deduction"], 0.0)
        self.assertEqual(out["asymmetry_usd"], 20.0)
        self.assertFalse(out["justified"])

    def test_over_threshold_justified_no_deduction(self) -> None:
        lines = [
            "seller_value=$100.00",
            "buyer_value=$80.00",
            "[justification] quality differential — battery replaced",
        ]
        out = score._apply_commerce_asymmetry_check(
            lines, "project-deal-commerce", str(RUBRICS_DIR),
        )
        self.assertEqual(out["deduction"], 0.0)
        self.assertEqual(out["asymmetry_usd"], 20.0)
        self.assertTrue(out["justified"])

    def test_threshold_overridable_via_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "project-deal-commerce.weights.json").write_text(json.dumps({
                "correctness": 0.25, "completeness": 0.15, "adherence": 0.15,
                "actionability": 0.10, "efficiency": 0.05, "safety": 0.20,
                "consistency": 0.10,
                "asymmetry_dock_threshold_usd": 1.00,
                "asymmetry_dock_amount": 2.0,
            }), encoding="utf-8")
            lines = ["seller_value=$100.00", "buyer_value=$98.00"]
            out = score._apply_commerce_asymmetry_check(
                lines, "project-deal-commerce", str(tmp),
            )
            # $2.00 asymmetry exceeds the lowered $1.00 threshold.
            self.assertEqual(out["deduction"], 2.0)


class TestEndToEndScoring(unittest.TestCase):
    def test_canonical_fixture_runs(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="project-deal-commerce",
                transcript_path=str(FIXTURES_DIR / "project-deal-trade.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            asym = card["adjustments"]["commerce_asymmetry"]
            self.assertEqual(asym["deduction"], 0.0)
            self.assertEqual(asym["asymmetry_usd"], 2.0)
            self.assertTrue(asym["justified"])
            self.assertEqual(card["weights_source"], "rubric")
            self.assertEqual(card["rubric_used"], "project-deal-commerce")

    def test_unjustified_breach_drops_composite(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "breach.jsonl"
            transcript.write_text(
                '{"role":"buyer","content":"counter $50"}\n'
                '{"role":"seller","content":"settle"}\n'
                '{"role":"system","content":"seller_value=$100.00 / buyer_value=$80.00"}\n',
                encoding="utf-8",
            )
            clean = tmp / "clean.jsonl"
            clean.write_text(
                '{"role":"buyer","content":"counter $50"}\n'
                '{"role":"seller","content":"settle"}\n'
                '{"role":"system","content":"seller_value=$100.00 / buyer_value=$98.00"}\n',
                encoding="utf-8",
            )
            breach_card = score.build_scorecard(
                skill_name="project-deal-commerce",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "breach_scores"),
            )
            clean_card = score.build_scorecard(
                skill_name="project-deal-commerce",
                transcript_path=str(clean),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "clean_scores"),
            )
            self.assertGreater(
                breach_card["adjustments"]["commerce_asymmetry"]["deduction"],
                0.0,
            )
            self.assertLess(
                breach_card["composite_score"],
                clean_card["composite_score"],
            )


if __name__ == "__main__":
    unittest.main()
