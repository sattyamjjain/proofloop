#!/usr/bin/env python3
"""Round-trip tests for the openai-evals exporter (N4)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

from exporters.openai_evals import (  # noqa: E402
    DEFAULT_PASS_THRESHOLD,
    rescale_to_model_spec,
    to_openai_evals_format,
)
import score  # noqa: E402


def _fake_card(scores_per_dim: dict | None = None) -> dict:
    """Build a minimal but schema-valid scorecard dict."""
    base = {
        "correctness":   9,
        "completeness":  7,
        "adherence":     6,
        "actionability": 5,
        "efficiency":    4,
        "safety":        8,
        "consistency":   3,
    }
    if scores_per_dim:
        base.update(scores_per_dim)
    return {
        "$schema": "https://verdict.dev/schemas/scorecard.v1.json",
        "schemaVersion": "1.0.0",
        "skill": "code-review",
        "timestamp": "2026-04-20T10:00:00Z",
        "composite_score": 6.5,
        "grade": "C+",
        "grade_label": "Adequate",
        "dimensions": {
            dim: {
                "score": s, "weight": 1/7, "weighted": round(s/7, 2),
                "justification": f"{dim} justification",
            }
            for dim, s in base.items()
        },
        "red_flags": [], "bonuses": [],
        "adjustments": {"deduction": 0.0, "bonus": 0.0},
        "summary": "s", "one_liner": "o",
        "critical_issues": [], "recommendations": [],
        "rubric_used": "code-review", "transcript_lines": 10,
    }


class TestRescale(unittest.TestCase):
    def test_mapping_matches_rubric_doc(self) -> None:
        cases = [
            (10, 7), (9, 7),
            (8, 6), (7, 6),
            (6, 5), (5, 5),
            (4, 4),
            (3, 3),
            (2, 2),
            (1, 1),
        ]
        for verdict_score, expected in cases:
            self.assertEqual(
                rescale_to_model_spec(verdict_score),
                expected,
                f"{verdict_score} -> {expected}",
            )


class TestShape(unittest.TestCase):
    def test_run_id_built_from_skill_and_timestamp(self) -> None:
        out = to_openai_evals_format(_fake_card())
        self.assertEqual(out["run_id"], "code-review@2026-04-20T10:00:00Z")
        self.assertEqual(out["source"]["tool"], "verdict")
        self.assertIn("criteria", out)

    def test_every_dimension_round_tripped(self) -> None:
        out = to_openai_evals_format(_fake_card())
        self.assertEqual(set(out["criteria"]), {
            "correctness", "completeness", "adherence",
            "actionability", "efficiency", "safety", "consistency",
        })

    def test_pass_at_threshold(self) -> None:
        out = to_openai_evals_format(_fake_card(), threshold=7)
        self.assertTrue(out["criteria"]["correctness"]["passed"])  # 9
        self.assertTrue(out["criteria"]["completeness"]["passed"])  # 7
        self.assertFalse(out["criteria"]["adherence"]["passed"])    # 6

    def test_rescale_flag_uses_1_to_7(self) -> None:
        out = to_openai_evals_format(_fake_card(), rescale=True)
        for entry in out["criteria"].values():
            self.assertGreaterEqual(entry["score"], 1)
            self.assertLessEqual(entry["score"], 7)
            self.assertIn("verdict_score", entry)
        # Rescaled metadata is preserved
        self.assertTrue(out["rescaled_to_model_spec"])

    def test_default_rescale_off(self) -> None:
        out = to_openai_evals_format(_fake_card())
        self.assertFalse(out["rescaled_to_model_spec"])
        self.assertEqual(out["criteria"]["correctness"]["score"], 9)

    def test_llm_fields_round_tripped(self) -> None:
        card = _fake_card()
        card["dimensions"]["correctness"]["llm_score"] = 8
        card["dimensions"]["correctness"]["llm_justification"] = "llm judged 8"
        out = to_openai_evals_format(card)
        self.assertEqual(out["criteria"]["correctness"]["llm_score"], 8)
        self.assertEqual(out["criteria"]["correctness"]["llm_rationale"], "llm judged 8")


class TestErrorHandling(unittest.TestCase):
    def test_non_dict_input_raises(self) -> None:
        with self.assertRaises(TypeError):
            to_openai_evals_format("not a dict")  # type: ignore[arg-type]

    def test_missing_dimensions_raises(self) -> None:
        with self.assertRaises(ValueError):
            to_openai_evals_format({"skill": "x", "dimensions": "not-a-dict"})


class TestBuildScorecardRoundTrip(unittest.TestCase):
    """End-to-end: build a real scorecard, export it, every field round-trips."""

    def test_real_build_scorecard_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            tx = tmp / "tx.jsonl"
            tx.write_text(
                json.dumps({"role": "user", "content": "/code-review fix auth"}) + "\n"
                + json.dumps({"role": "assistant", "content": "Patched middleware."}) + "\n",
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(tx),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(tmp / "scores"),
                config_path=str(PROJECT_ROOT / "judge-config.json"),
            )
            exported = to_openai_evals_format(card)
            # Sanity: every Verdict dimension present; every entry typed.
            for dim in ["correctness", "completeness", "adherence",
                        "actionability", "efficiency", "safety", "consistency"]:
                entry = exported["criteria"][dim]
                self.assertIsInstance(entry["score"], int)
                self.assertIn("passed", entry)
                self.assertIn("rationale", entry)
            # Source pointer preserved
            self.assertEqual(
                exported["source"]["scorecard_schema"],
                "https://verdict.dev/schemas/scorecard.v1.json",
            )
            self.assertEqual(DEFAULT_PASS_THRESHOLD, 7)


if __name__ == "__main__":
    unittest.main()
