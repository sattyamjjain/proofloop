#!/usr/bin/env python3
"""Tests for the SWE-bench Pro rubric and contamination penalty."""
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
    def test_rubric_markdown_exists(self) -> None:
        path = RUBRICS_DIR / "swe-bench-pro.md"
        self.assertTrue(path.is_file())

    def test_rubric_has_source_signal_header(self) -> None:
        text = (RUBRICS_DIR / "swe-bench-pro.md").read_text(encoding="utf-8")
        self.assertIn("source_signal:", text)
        self.assertIn("https://llm-stats.com/benchmarks/swe-bench-pro", text)

    def test_weights_sidecar_sums_to_one(self) -> None:
        path = RUBRICS_DIR / "swe-bench-pro.weights.json"
        self.assertTrue(path.is_file())
        weights = json.loads(path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_weights_match_prompt_spec(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "swe-bench-pro.weights.json").read_text(encoding="utf-8")
        )
        self.assertAlmostEqual(weights["correctness"], 0.35)
        self.assertAlmostEqual(weights["adherence"], 0.30)
        self.assertAlmostEqual(weights["safety"], 0.05)

    def test_rubric_resolution_picks_rubric(self) -> None:
        _, text = score.load_rubric(str(RUBRICS_DIR), "swe-bench-pro")
        self.assertIn("SWE-bench Pro", text)


class TestContaminationPenalty(unittest.TestCase):
    def test_zero_for_other_rubric(self) -> None:
        lines = ["django__django-12345 mentioned casually"]
        self.assertEqual(
            score._apply_contamination_penalty(lines, "code-review"),
            0.0,
        )

    def test_zero_when_no_literals(self) -> None:
        lines = [
            "[user] implement the new feature cleanly",
            "[assistant] done, added tests",
        ]
        self.assertEqual(
            score._apply_contamination_penalty(lines, "swe-bench-pro"),
            0.0,
        )

    def test_single_instance_id_triggers_penalty(self) -> None:
        lines = ["[assistant] this looks like django__django-12345"]
        penalty = score._apply_contamination_penalty(lines, "swe-bench-pro")
        self.assertEqual(penalty, score.CONTAMINATION_PER_MATCH)

    def test_split_name_literal_triggers_penalty(self) -> None:
        lines = ["see SWE-bench Verified for the canonical split"]
        penalty = score._apply_contamination_penalty(lines, "swe-bench-pro")
        self.assertEqual(penalty, score.CONTAMINATION_PER_MATCH)

    def test_penalty_caps_at_max(self) -> None:
        # Many unique instance IDs; total deduction must not exceed
        # MAX_CONTAMINATION_PENALTY (1.5 by spec).
        ids = [f"sympy__sympy-{n}" for n in range(100, 120)]
        lines = [f"[assistant] {i}" for i in ids]
        penalty = score._apply_contamination_penalty(lines, "swe-bench-pro")
        self.assertEqual(penalty, score.MAX_CONTAMINATION_PENALTY)

    def test_duplicate_ids_counted_once(self) -> None:
        lines = [
            "[assistant] django__django-12345",
            "[assistant] django__django-12345",
            "[assistant] django__django-12345",
        ]
        penalty = score._apply_contamination_penalty(lines, "swe-bench-pro")
        self.assertEqual(penalty, score.CONTAMINATION_PER_MATCH)


class TestBuildScorecardAppliesPenalty(unittest.TestCase):
    def _transcript(self, tmp: Path, body: str) -> Path:
        path = tmp / "transcript.jsonl"
        path.write_text(body, encoding="utf-8")
        return path

    def test_scorecard_records_contamination_field(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = self._transcript(
                tmp,
                '{"role":"user","content":"/swe-bench-pro fix the regression"}\n'
                '{"role":"assistant","content":"Solved — patterned on '
                'django__django-12345 from Verified."}\n',
            )
            card = score.build_scorecard(
                skill_name="swe-bench-pro",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            self.assertIn("contamination", card["adjustments"])
            self.assertGreater(card["adjustments"]["contamination"], 0.0)

    def test_composite_lowered_by_penalty(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            clean = self._transcript(
                tmp,
                '{"role":"user","content":"/swe-bench-pro fix regression"}\n'
                '{"role":"assistant","content":"Scoped patch applied."}\n',
            )
            clean_card = score.build_scorecard(
                skill_name="swe-bench-pro",
                transcript_path=str(clean),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "clean_scores"),
            )
            dirty = self._transcript(
                tmp,
                '{"role":"user","content":"/swe-bench-pro fix regression"}\n'
                '{"role":"assistant","content":"Applied the django__django-12345 '
                'fix from SWE-bench Verified."}\n',
            )
            dirty_card = score.build_scorecard(
                skill_name="swe-bench-pro",
                transcript_path=str(dirty),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "dirty_scores"),
            )
            self.assertGreater(dirty_card["adjustments"]["contamination"], 0.0)
            self.assertLessEqual(
                dirty_card["composite_score"],
                clean_card["composite_score"],
            )

    def test_non_pro_rubric_escapes_penalty(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = self._transcript(
                tmp,
                '{"role":"user","content":"/code-review look at this"}\n'
                '{"role":"assistant","content":"Reminds me of '
                'django__django-12345 on Verified."}\n',
            )
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            # code-review rubric is not contamination-scanned.
            self.assertEqual(card["adjustments"]["contamination"], 0.0)


if __name__ == "__main__":
    unittest.main()
