#!/usr/bin/env python3
"""Comprehensive test suite for the Verdict Scoring Engine (score.py).

Tests all public functions across 7 categories:
  1. Grade boundaries
  2. Rubric resolution
  3. Scoring heuristics (per-dimension)
  4. Auto-deductions and bonuses
  5. Composite computation
  6. Config loading
  7. History loading and consistency

Runs with stdlib-only Python 3.9+ via unittest.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so we can import score.py
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "judge" / "scripts"
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

sys.path.insert(0, str(SCRIPTS_DIR))

import score  # noqa: E402  -- must follow sys.path manipulation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lines(text: str) -> List[str]:
    """Split multiline string into non-empty lines (mimics transcript loading)."""
    return [line for line in text.splitlines() if line.strip()]


def _write_temp_file(content: str, suffix: str = ".txt") -> str:
    """Write *content* to a temporary file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


def _make_temp_dir() -> str:
    """Create a temporary directory and return its path."""
    return tempfile.mkdtemp()


# ===================================================================
# 1. Grade boundaries
# ===================================================================


class TestAssignGrade(unittest.TestCase):
    """Verify assign_grade() covers every boundary in GRADE_TABLE."""

    def test_a_plus_at_threshold(self) -> None:
        grade, label = score.assign_grade(9.5)
        self.assertEqual(grade, "A+")
        self.assertEqual(label, "Exceptional")

    def test_a_plus_at_10(self) -> None:
        grade, _ = score.assign_grade(10.0)
        self.assertEqual(grade, "A+")

    def test_a_plus_above_threshold(self) -> None:
        grade, _ = score.assign_grade(9.75)
        self.assertEqual(grade, "A+")

    def test_a_just_below_a_plus(self) -> None:
        grade, label = score.assign_grade(9.49)
        self.assertEqual(grade, "A")
        self.assertEqual(label, "Excellent")

    def test_a_at_threshold(self) -> None:
        grade, _ = score.assign_grade(9.0)
        self.assertEqual(grade, "A")

    def test_a_minus_just_below_a(self) -> None:
        grade, label = score.assign_grade(8.99)
        self.assertEqual(grade, "A-")
        self.assertEqual(label, "Very Good")

    def test_a_minus_at_threshold(self) -> None:
        grade, _ = score.assign_grade(8.5)
        self.assertEqual(grade, "A-")

    def test_b_plus_just_below_a_minus(self) -> None:
        grade, label = score.assign_grade(8.49)
        self.assertEqual(grade, "B+")
        self.assertEqual(label, "Good")

    def test_b_plus_at_threshold(self) -> None:
        grade, _ = score.assign_grade(8.0)
        self.assertEqual(grade, "B+")

    def test_b_just_below_b_plus(self) -> None:
        grade, label = score.assign_grade(7.99)
        self.assertEqual(grade, "B")
        self.assertEqual(label, "Above Average")

    def test_b_at_threshold(self) -> None:
        grade, _ = score.assign_grade(7.5)
        self.assertEqual(grade, "B")

    def test_b_minus_just_below_b(self) -> None:
        grade, label = score.assign_grade(7.49)
        self.assertEqual(grade, "B-")
        self.assertEqual(label, "Satisfactory")

    def test_b_minus_at_threshold(self) -> None:
        grade, _ = score.assign_grade(7.0)
        self.assertEqual(grade, "B-")

    def test_c_plus_just_below_b_minus(self) -> None:
        grade, label = score.assign_grade(6.99)
        self.assertEqual(grade, "C+")
        self.assertEqual(label, "Adequate")

    def test_c_plus_at_threshold(self) -> None:
        grade, _ = score.assign_grade(6.5)
        self.assertEqual(grade, "C+")

    def test_c_just_below_c_plus(self) -> None:
        grade, label = score.assign_grade(6.49)
        self.assertEqual(grade, "C")
        self.assertEqual(label, "Below Average")

    def test_c_at_threshold(self) -> None:
        grade, _ = score.assign_grade(6.0)
        self.assertEqual(grade, "C")

    def test_c_minus_just_below_c(self) -> None:
        grade, label = score.assign_grade(5.99)
        self.assertEqual(grade, "C-")
        self.assertEqual(label, "Poor")

    def test_c_minus_at_threshold(self) -> None:
        grade, _ = score.assign_grade(5.5)
        self.assertEqual(grade, "C-")

    def test_d_just_below_c_minus(self) -> None:
        grade, label = score.assign_grade(5.49)
        self.assertEqual(grade, "D")
        self.assertEqual(label, "Failing")

    def test_d_at_threshold(self) -> None:
        grade, _ = score.assign_grade(4.0)
        self.assertEqual(grade, "D")

    def test_f_just_below_d(self) -> None:
        grade, label = score.assign_grade(3.99)
        self.assertEqual(grade, "F")
        self.assertEqual(label, "Unacceptable")

    def test_f_at_zero(self) -> None:
        grade, _ = score.assign_grade(0.0)
        self.assertEqual(grade, "F")

    def test_f_at_one(self) -> None:
        grade, _ = score.assign_grade(1.0)
        self.assertEqual(grade, "F")

    def test_returns_tuple_of_two_strings(self) -> None:
        result = score.assign_grade(7.5)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], str)
        self.assertIsInstance(result[1], str)


# ===================================================================
# 2. Rubric resolution
# ===================================================================


class TestLoadRubric(unittest.TestCase):
    """Verify rubric resolution: exact match, category prefix, default fallback."""

    def setUp(self) -> None:
        self.rubric_dir = str(RUBRICS_DIR)

    def test_exact_match_code_review(self) -> None:
        name, text = score.load_rubric(self.rubric_dir, "code-review")
        self.assertEqual(name, "code-review")
        self.assertTrue(len(text) > 0)

    def test_exact_match_security(self) -> None:
        name, text = score.load_rubric(self.rubric_dir, "security")
        self.assertEqual(name, "security")
        self.assertTrue(len(text) > 0)

    def test_exact_match_testing(self) -> None:
        name, text = score.load_rubric(self.rubric_dir, "testing")
        self.assertEqual(name, "testing")
        self.assertTrue(len(text) > 0)

    def test_category_prefix_code_review_v2(self) -> None:
        """'code-review-v2' should resolve to code-review.md via prefix match."""
        name, text = score.load_rubric(self.rubric_dir, "code-review-v2")
        self.assertEqual(name, "code-review")
        self.assertTrue(len(text) > 0)

    def test_category_prefix_security_scan(self) -> None:
        """'security-scan' should resolve to security.md via prefix match."""
        name, text = score.load_rubric(self.rubric_dir, "security-scan")
        self.assertEqual(name, "security")
        self.assertTrue(len(text) > 0)

    def test_category_prefix_frontend_design_v3_beta(self) -> None:
        """Multi-part suffix: 'frontend-design-v3-beta' -> frontend-design.md."""
        name, text = score.load_rubric(self.rubric_dir, "frontend-design-v3-beta")
        self.assertEqual(name, "frontend-design")
        self.assertTrue(len(text) > 0)

    def test_default_fallback_unknown_skill(self) -> None:
        """Unknown skill with no prefix match should fall back to default.md."""
        name, text = score.load_rubric(self.rubric_dir, "completely-unknown-xyz")
        self.assertEqual(name, "default")
        self.assertTrue(len(text) > 0)

    def test_missing_rubric_dir_graceful_fallback(self) -> None:
        """Non-existent rubric dir should return default with empty text."""
        name, text = score.load_rubric("/tmp/nonexistent-rubric-dir-xyz", "anything")
        self.assertEqual(name, "default")
        self.assertEqual(text, "")

    def test_empty_rubric_dir_falls_to_default(self) -> None:
        """Rubric dir with no matching files but a default.md should use it."""
        tmp_dir = _make_temp_dir()
        default_path = Path(tmp_dir) / "default.md"
        default_path.write_text("# Default\nFallback rubric.\n", encoding="utf-8")

        name, text = score.load_rubric(tmp_dir, "nonexistent-skill")
        self.assertEqual(name, "default")
        self.assertIn("Fallback rubric", text)

    def test_single_word_skill_no_prefix(self) -> None:
        """Single-word skill like 'debugging' with no exact match should use default."""
        name, _ = score.load_rubric(self.rubric_dir, "debugging")
        # 'debugging.md' does not exist, and single-word has no prefix candidates
        self.assertEqual(name, "default")


# ===================================================================
# 3. Scoring heuristics (per-dimension)
# ===================================================================


class TestCorrectnessHeuristic(unittest.TestCase):
    """Correctness dimension: error and hallucination signals."""

    def test_clean_transcript_scores_high(self) -> None:
        lines = _make_lines(
            "All tests passed.\n" * 100
            + "Deployment successful.\n" * 50
        )
        result = score.analyze_dimension("correctness", lines, {}, [])
        self.assertGreaterEqual(result["score"], 9)

    def test_many_errors_scores_lower(self) -> None:
        lines = _make_lines(
            "error: compilation failed\n" * 20
            + "traceback: NoneType exception\n" * 10
            + "clean line\n" * 70
        )
        result = score.analyze_dimension("correctness", lines, {}, [])
        self.assertLessEqual(result["score"], 7)

    def test_high_error_density_severe_penalty(self) -> None:
        """More than 10% error density should trigger heavy penalty."""
        lines = _make_lines(
            "error occurred\n" * 15
            + "clean line\n" * 85
        )
        result = score.analyze_dimension("correctness", lines, {}, [])
        self.assertLessEqual(result["score"], 6)

    def test_hallucination_signals_reduce_score(self) -> None:
        lines = _make_lines(
            "as an AI I cannot access that\n" * 5
            + "that file doesn't exist but let me continue\n" * 5
            + "normal output line\n" * 90
        )
        result = score.analyze_dimension("correctness", lines, {}, [])
        self.assertLessEqual(result["score"], 8)

    def test_score_clamped_at_minimum_1(self) -> None:
        """Even extreme errors should not produce a score below 1."""
        lines = _make_lines("error failure exception traceback\n" * 100)
        result = score.analyze_dimension("correctness", lines, {}, [])
        self.assertGreaterEqual(result["score"], 1)


class TestSafetyHeuristic(unittest.TestCase):
    """Safety dimension: destructive commands, exposed secrets."""

    def test_safe_transcript_scores_10(self) -> None:
        lines = _make_lines(
            "Created file utils.py\n" * 50
            + "All tests passed\n" * 50
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        self.assertEqual(result["score"], 10)

    def test_rm_rf_root_penalised(self) -> None:
        lines = _make_lines(
            "sudo rm -rf /\n"
            + "normal line\n" * 99
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        self.assertLessEqual(result["score"], 7)

    def test_hardcoded_secret_penalised(self) -> None:
        lines = _make_lines(
            "password= s3cretP4ss\n"
            + "normal line\n" * 99
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        self.assertLessEqual(result["score"], 8)

    def test_password_in_review_context_not_penalised(self) -> None:
        """Discussing passwords in a review/comparison context should NOT penalise."""
        lines = _make_lines(
            "Ensure the password= value is stored in env variables\n"
            "Review comparison of password: handling approaches\n"
            "The password should never be hardcoded\n"
            + "normal review line\n" * 97
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        # Should still score high because discussion_context and env patterns
        # cause the credential check to be skipped
        self.assertGreaterEqual(result["score"], 7)

    def test_env_referenced_credential_not_penalised(self) -> None:
        """Credentials loaded from os.environ should not trigger secret penalty."""
        lines = _make_lines(
            "password= os.environ.get('DB_PASS')\n"
            + "normal line\n" * 99
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        # The env pattern filter should skip this line
        self.assertGreaterEqual(result["score"], 7)

    def test_chmod_777_penalised(self) -> None:
        lines = _make_lines(
            "chmod 777 /var/www\n"
            + "normal line\n" * 99
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        self.assertLessEqual(result["score"], 9)

    def test_no_verify_flag_penalised(self) -> None:
        lines = _make_lines(
            "git commit --no-verify\n"
            + "normal line\n" * 99
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        self.assertLessEqual(result["score"], 9)

    def test_multiple_safety_issues_cumulative(self) -> None:
        lines = _make_lines(
            "sudo rm -rf /\n"
            "chmod 777 /tmp\n"
            "git push --no-verify\n"
            "password= hardcoded123\n"
            + "normal line\n" * 96
        )
        result = score.analyze_dimension("safety", lines, {}, [])
        self.assertLessEqual(result["score"], 5)


class TestCompletenessHeuristic(unittest.TestCase):
    """Completeness dimension: TODO/FIXME signals and transcript length."""

    def test_clean_long_transcript_high_score(self) -> None:
        lines = _make_lines("Implemented feature X.\n" * 100)
        result = score.analyze_dimension("completeness", lines, {}, [])
        self.assertGreaterEqual(result["score"], 9)

    def test_many_todos_lower_score(self) -> None:
        lines = _make_lines(
            "TODO: implement this\n" * 10
            + "FIXME: broken\n" * 10
            + "normal line\n" * 80
        )
        result = score.analyze_dimension("completeness", lines, {}, [])
        self.assertLessEqual(result["score"], 8)

    def test_very_short_transcript_penalty(self) -> None:
        """Transcripts under 10 lines get a -2 penalty."""
        lines = _make_lines("Did the thing.\n" * 5)
        result = score.analyze_dimension("completeness", lines, {}, [])
        self.assertLessEqual(result["score"], 8)

    def test_short_transcript_minor_penalty(self) -> None:
        """Transcripts between 10-30 lines get a -1 penalty."""
        lines = _make_lines("Did the thing.\n" * 20)
        result = score.analyze_dimension("completeness", lines, {}, [])
        self.assertLessEqual(result["score"], 9)

    def test_high_incompleteness_density_heavy_penalty(self) -> None:
        """More than 5% incomplete signals triggers -4."""
        lines = _make_lines(
            "TODO: finish\n" * 8
            + "normal line\n" * 92
        )
        result = score.analyze_dimension("completeness", lines, {}, [])
        self.assertLessEqual(result["score"], 7)


class TestEfficiencyHeuristic(unittest.TestCase):
    """Efficiency dimension: tool call density, retries, length."""

    def test_efficient_transcript_high_score(self) -> None:
        lines = _make_lines(
            "Read file config.json\n"
            "Write file output.py\n"
            + "normal output line\n" * 98
        )
        result = score.analyze_dimension("efficiency", lines, {}, [])
        self.assertGreaterEqual(result["score"], 7)

    def test_many_retries_lower_score(self) -> None:
        lines = _make_lines(
            "retrying the command\n" * 10
            + "trying again\n" * 5
            + "normal line\n" * 85
        )
        result = score.analyze_dimension("efficiency", lines, {}, [])
        self.assertLessEqual(result["score"], 6)

    def test_very_long_transcript_penalty(self) -> None:
        """Transcripts over 2000 lines get a -2 efficiency penalty."""
        lines = _make_lines("line\n" * 2500)
        result = score.analyze_dimension("efficiency", lines, {}, [])
        self.assertLessEqual(result["score"], 7)

    def test_high_tool_density_penalty(self) -> None:
        """Tool call density over 30% triggers -2."""
        lines = _make_lines(
            "Running command ls\n" * 40
            + "normal line\n" * 60
        )
        result = score.analyze_dimension("efficiency", lines, {}, [])
        self.assertLessEqual(result["score"], 7)


class TestAdherenceHeuristic(unittest.TestCase):
    """Adherence dimension: deviation signals and rubric presence."""

    def test_clean_transcript_with_rubric(self) -> None:
        lines = _make_lines("Followed all instructions perfectly.\n" * 100)
        rubric_criteria = {"correctness": "must be correct"}
        result = score.analyze_dimension("adherence", lines, rubric_criteria, [])
        # Base 8, +1 for rubric criteria = 9
        self.assertGreaterEqual(result["score"], 9)

    def test_deviation_signals_reduce_score(self) -> None:
        lines = _make_lines(
            "instead of following the spec, I chose a different approach\n"
            "ignoring the constraint about naming\n"
            "skipping instruction about tests\n"
            + "normal line\n" * 97
        )
        result = score.analyze_dimension("adherence", lines, {}, [])
        self.assertLessEqual(result["score"], 7)


class TestActionabilityHeuristic(unittest.TestCase):
    """Actionability dimension: code blocks, file actions, placeholders."""

    def test_code_blocks_and_file_actions_boost(self) -> None:
        lines = _make_lines(
            "```python\nprint('hello')\n```\n"
            "```bash\necho test\n```\n"
            "Write(output.py)\n"
            + "normal line\n" * 90
        )
        result = score.analyze_dimension("actionability", lines, {}, [])
        self.assertGreaterEqual(result["score"], 8)

    def test_many_placeholders_penalised(self) -> None:
        lines = _make_lines(
            "<YOUR_API_KEY>\n" * 5
            + "INSERT_HERE\n" * 3
            + "normal line\n" * 92
        )
        result = score.analyze_dimension("actionability", lines, {}, [])
        self.assertLessEqual(result["score"], 7)


class TestUnknownDimension(unittest.TestCase):
    """Unknown dimension name returns a neutral score of 5."""

    def test_unknown_dimension(self) -> None:
        result = score.analyze_dimension("nonexistent_dim", [], {}, [])
        self.assertEqual(result["score"], 5)
        self.assertIn("Unknown dimension", result["justification"])


# ===================================================================
# 4. Auto-deductions and bonuses
# ===================================================================


class TestDetectRedFlags(unittest.TestCase):
    """Red flag detection for auto-deductions."""

    def test_hallucination_flagged(self) -> None:
        lines = _make_lines("This data was hallucinated from memory.\n" * 5)
        flags = score.detect_red_flags(lines)
        self.assertTrue(any("Hallucinated" in f for f in flags))

    def test_contradiction_flagged(self) -> None:
        lines = _make_lines(
            "The output contradicts the specification.\n"
            + "normal line\n" * 10
        )
        flags = score.detect_red_flags(lines)
        self.assertTrue(any("contradictory" in f.lower() for f in flags))

    def test_ignored_constraint_flagged(self) -> None:
        lines = _make_lines(
            "ignored explicit constraint about max file size\n"
            + "normal line\n" * 10
        )
        flags = score.detect_red_flags(lines)
        self.assertTrue(any("constraint" in f.lower() for f in flags))

    def test_placeholder_flagged(self) -> None:
        lines = _make_lines("<YOUR_API_KEY> should be replaced\n")
        flags = score.detect_red_flags(lines)
        self.assertTrue(any("Placeholder" in f for f in flags))

    def test_rm_rf_root_flagged(self) -> None:
        lines = _make_lines("rm -rf /\n")
        flags = score.detect_red_flags(lines)
        self.assertTrue(any("rm -rf" in f.lower() or "Destructive" in f for f in flags))

    def test_max_four_flags(self) -> None:
        """Red flag list is capped at 4 entries."""
        lines = _make_lines(
            "hallucinated data\n"
            "contradicts the spec\n"
            "ignored explicit constraint\n"
            "CHANGEME placeholder\n"
            "rm -rf /\n"
        )
        flags = score.detect_red_flags(lines)
        self.assertLessEqual(len(flags), 4)

    def test_clean_transcript_no_flags(self) -> None:
        lines = _make_lines("All good.\n" * 20)
        flags = score.detect_red_flags(lines)
        self.assertEqual(len(flags), 0)


class TestDetectBonuses(unittest.TestCase):
    """Bonus detection for score boosts."""

    def test_edge_case_handling_bonus(self) -> None:
        lines = _make_lines("Handled the edge case where input is empty.\n")
        bonuses = score.detect_bonuses(lines)
        self.assertTrue(any("edge case" in b.lower() for b in bonuses))

    def test_tradeoff_analysis_bonus(self) -> None:
        lines = _make_lines("Considered the trade-off between speed and memory.\n")
        bonuses = score.detect_bonuses(lines)
        self.assertTrue(any("justification" in b.lower() or "trade" in b.lower() for b in bonuses))

    def test_structure_bonus(self) -> None:
        lines = _make_lines("## Section Heading\n- Bullet point\n| Col1 | Col2 |\n")
        bonuses = score.detect_bonuses(lines)
        self.assertTrue(any("structure" in b.lower() for b in bonuses))

    def test_max_four_bonuses(self) -> None:
        lines = _make_lines(
            "edge case covered\n"
            "trade-off analysis\n"
            "## Heading\n"
            "alternative considered\n"
            "pros and cons\n"
        )
        bonuses = score.detect_bonuses(lines)
        self.assertLessEqual(len(bonuses), 4)

    def test_clean_transcript_no_bonuses(self) -> None:
        """Plain transcript with no bonus signals."""
        lines = _make_lines("did the work\n" * 20)
        bonuses = score.detect_bonuses(lines)
        self.assertEqual(len(bonuses), 0)


class TestApplyAdjustments(unittest.TestCase):
    """Verify apply_adjustments() respects caps and floors."""

    def test_no_adjustments(self) -> None:
        final, ded, bon = score.apply_adjustments(8.0, [], [])
        self.assertEqual(final, 8.0)
        self.assertEqual(ded, 0.0)
        self.assertEqual(bon, 0.0)

    def test_single_deduction(self) -> None:
        final, ded, bon = score.apply_adjustments(8.0, ["flag1"], [])
        self.assertEqual(ded, 0.5)
        self.assertEqual(final, 7.5)

    def test_deduction_cap_at_2(self) -> None:
        """Max deduction is 2.0, even with more than 4 flags."""
        final, ded, bon = score.apply_adjustments(8.0, ["f1", "f2", "f3", "f4", "f5"], [])
        self.assertEqual(ded, 2.0)
        self.assertEqual(final, 6.0)

    def test_single_bonus(self) -> None:
        final, ded, bon = score.apply_adjustments(8.0, [], ["bonus1"])
        self.assertEqual(bon, 0.25)
        self.assertEqual(final, 8.25)

    def test_bonus_cap_at_1(self) -> None:
        """Max bonus is 1.0, even with more than 4 bonuses."""
        final, ded, bon = score.apply_adjustments(8.0, [], ["b1", "b2", "b3", "b4", "b5"])
        self.assertEqual(bon, 1.0)
        self.assertEqual(final, 9.0)

    def test_floor_at_1(self) -> None:
        """Final score cannot go below 1.0."""
        final, ded, bon = score.apply_adjustments(1.5, ["f1", "f2", "f3", "f4"], [])
        self.assertGreaterEqual(final, 1.0)

    def test_ceiling_at_10(self) -> None:
        """Final score cannot exceed 10.0."""
        final, ded, bon = score.apply_adjustments(9.8, [], ["b1", "b2", "b3", "b4"])
        self.assertLessEqual(final, 10.0)

    def test_deduction_then_bonus(self) -> None:
        """Deductions applied first, then bonuses."""
        final, ded, bon = score.apply_adjustments(8.0, ["f1", "f2"], ["b1", "b2"])
        # Deduction: 2 * 0.5 = 1.0 -> 8.0 - 1.0 = 7.0
        # Bonus: 2 * 0.25 = 0.5 -> 7.0 + 0.5 = 7.5
        self.assertEqual(ded, 1.0)
        self.assertEqual(bon, 0.5)
        self.assertEqual(final, 7.5)

    def test_extreme_low_composite_floors_before_bonus(self) -> None:
        """With composite 0.5 and deductions, floor kicks in at 1.0 before bonus."""
        final, ded, bon = score.apply_adjustments(0.5, ["f1", "f2", "f3", "f4"], ["b1"])
        # Deduction: min(4*0.5, 2.0) = 2.0 -> max(1.0, 0.5 - 2.0) = 1.0
        # Bonus: 0.25 -> min(10.0, 1.0 + 0.25) = 1.25
        self.assertEqual(final, 1.25)


# ===================================================================
# 5. Composite computation
# ===================================================================


class TestComputeComposite(unittest.TestCase):
    """Verify compute_composite() produces correct weighted sums."""

    def test_uniform_scores(self) -> None:
        """All dimensions at 8.0 -> composite should be 8.0."""
        dims = {d: {"score": 8} for d in score.DEFAULT_WEIGHTS}
        result = score.compute_composite(dims, score.DEFAULT_WEIGHTS)
        self.assertAlmostEqual(result, 8.0, places=2)

    def test_known_weighted_sum(self) -> None:
        """Manual computation of a known weighted sum."""
        dims = {
            "correctness": {"score": 10},
            "completeness": {"score": 9},
            "adherence": {"score": 8},
            "actionability": {"score": 7},
            "efficiency": {"score": 6},
            "safety": {"score": 5},
            "consistency": {"score": 4},
        }
        weights = score.DEFAULT_WEIGHTS
        expected = (
            10 * 0.25
            + 9 * 0.20
            + 8 * 0.15
            + 7 * 0.15
            + 6 * 0.10
            + 5 * 0.10
            + 4 * 0.05
        )
        result = score.compute_composite(dims, weights)
        self.assertAlmostEqual(result, round(expected, 2), places=2)

    def test_all_zeros(self) -> None:
        dims = {d: {"score": 0} for d in score.DEFAULT_WEIGHTS}
        result = score.compute_composite(dims, score.DEFAULT_WEIGHTS)
        self.assertAlmostEqual(result, 0.0, places=2)

    def test_all_tens(self) -> None:
        dims = {d: {"score": 10} for d in score.DEFAULT_WEIGHTS}
        result = score.compute_composite(dims, score.DEFAULT_WEIGHTS)
        self.assertAlmostEqual(result, 10.0, places=2)

    def test_missing_dimension_uses_default_5(self) -> None:
        """Missing dimensions should use a fallback score of 5."""
        dims = {"correctness": {"score": 10}}
        weights = score.DEFAULT_WEIGHTS
        expected = (
            10 * 0.25
            + 5 * 0.20  # completeness missing
            + 5 * 0.15  # adherence missing
            + 5 * 0.15  # actionability missing
            + 5 * 0.10  # efficiency missing
            + 5 * 0.10  # safety missing
            + 5 * 0.05  # consistency missing
        )
        result = score.compute_composite(dims, weights)
        self.assertAlmostEqual(result, round(expected, 2), places=2)

    def test_weights_sum_to_one(self) -> None:
        """DEFAULT_WEIGHTS should sum to 1.0."""
        total = sum(score.DEFAULT_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=10)


# ===================================================================
# 6. Config loading
# ===================================================================


class TestLoadConfig(unittest.TestCase):
    """Config loading: missing, valid, invalid."""

    def test_none_path_returns_empty_dict(self) -> None:
        result = score.load_config(None)
        self.assertEqual(result, {})

    def test_nonexistent_file_returns_empty_dict(self) -> None:
        result = score.load_config("/tmp/nonexistent-config-xyz-abc.json")
        self.assertEqual(result, {})

    def test_valid_config_returns_dict(self) -> None:
        config_data = {"scoring": {"dimensions": {"correctness": 0.3}}}
        path = _write_temp_file(json.dumps(config_data), suffix=".json")
        try:
            result = score.load_config(path)
            self.assertEqual(result["scoring"]["dimensions"]["correctness"], 0.3)
        finally:
            os.unlink(path)

    def test_invalid_json_returns_empty_dict(self) -> None:
        path = _write_temp_file("{ not valid json !!!", suffix=".json")
        try:
            result = score.load_config(path)
            self.assertEqual(result, {})
        finally:
            os.unlink(path)

    def test_real_config_file(self) -> None:
        """Load the actual judge-config.json from the project root."""
        config_path = str(PROJECT_ROOT / "judge-config.json")
        result = score.load_config(config_path)
        self.assertIn("scoring", result)
        self.assertIn("dimensions", result["scoring"])


class TestGetWeights(unittest.TestCase):
    """Verify _get_weights() merges config over defaults."""

    def test_empty_config_returns_defaults(self) -> None:
        weights = score._get_weights({})
        self.assertEqual(weights, score.DEFAULT_WEIGHTS)

    def test_config_overrides_specific_weight(self) -> None:
        config = {"scoring": {"dimensions": {"correctness": 0.50}}}
        weights = score._get_weights(config)
        self.assertEqual(weights["correctness"], 0.50)
        # Other weights remain at defaults
        self.assertEqual(weights["completeness"], 0.20)

    def test_unknown_dimensions_in_config_ignored(self) -> None:
        config = {"scoring": {"dimensions": {"novelty": 0.99}}}
        weights = score._get_weights(config)
        self.assertNotIn("novelty", weights)
        self.assertEqual(weights, score.DEFAULT_WEIGHTS)


# ===================================================================
# 7. History loading and consistency
# ===================================================================


class TestLoadHistory(unittest.TestCase):
    """History loading from scores directory."""

    def test_nonexistent_dir_returns_empty(self) -> None:
        result = score.load_history("/tmp/no-such-scores-dir-xyz", "test-skill")
        self.assertEqual(result, [])

    def test_empty_dir_returns_empty(self) -> None:
        tmp_dir = _make_temp_dir()
        result = score.load_history(tmp_dir, "test-skill")
        self.assertEqual(result, [])

    def test_loads_matching_files(self) -> None:
        tmp_dir = _make_temp_dir()
        card1 = {"skill": "myskill", "timestamp": "2025-01-01T00:00:00Z", "composite_score": 7.5}
        card2 = {"skill": "myskill", "timestamp": "2025-01-02T00:00:00Z", "composite_score": 8.0}
        Path(tmp_dir, "myskill_2025-01-01.json").write_text(json.dumps(card1), encoding="utf-8")
        Path(tmp_dir, "myskill_2025-01-02.json").write_text(json.dumps(card2), encoding="utf-8")
        # Also write a non-matching file
        Path(tmp_dir, "other_2025-01-01.json").write_text('{"skill":"other"}', encoding="utf-8")

        history = score.load_history(tmp_dir, "myskill")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["composite_score"], 7.5)
        self.assertEqual(history[1]["composite_score"], 8.0)

    def test_invalid_json_skipped(self) -> None:
        tmp_dir = _make_temp_dir()
        Path(tmp_dir, "myskill_broken.json").write_text("not json!", encoding="utf-8")
        Path(tmp_dir, "myskill_good.json").write_text(
            json.dumps({"timestamp": "2025-01-01", "composite_score": 6.0}),
            encoding="utf-8",
        )
        history = score.load_history(tmp_dir, "myskill")
        self.assertEqual(len(history), 1)

    def test_sorted_by_timestamp(self) -> None:
        tmp_dir = _make_temp_dir()
        card_late = {"timestamp": "2025-06-15T00:00:00Z", "composite_score": 9.0}
        card_early = {"timestamp": "2025-01-01T00:00:00Z", "composite_score": 5.0}
        Path(tmp_dir, "sk_late.json").write_text(json.dumps(card_late), encoding="utf-8")
        Path(tmp_dir, "sk_early.json").write_text(json.dumps(card_early), encoding="utf-8")

        history = score.load_history(tmp_dir, "sk")
        self.assertEqual(history[0]["composite_score"], 5.0)
        self.assertEqual(history[1]["composite_score"], 9.0)


class TestConsistencyDimension(unittest.TestCase):
    """Consistency dimension: history-based scoring."""

    def test_no_history_neutral_7(self) -> None:
        result = score._analyze_consistency([])
        self.assertEqual(result["score"], 7)
        self.assertIn("No prior history", result["justification"])

    def test_no_composite_in_history_neutral(self) -> None:
        """History entries without composite_score should yield neutral."""
        history = [{"skill": "x", "timestamp": "2025-01-01T00:00:00Z"}]
        result = score._analyze_consistency(history)
        self.assertEqual(result["score"], 7)

    def test_stable_history_high_score(self) -> None:
        """Low variance in historical scores should yield high consistency."""
        history = [
            {"composite_score": 8.0, "timestamp": f"2025-01-0{i}T00:00:00Z"}
            for i in range(1, 6)
        ]
        result = score._analyze_consistency(history)
        # std_dev = 0.0, so +1 bonus -> score 9
        self.assertGreaterEqual(result["score"], 9)

    def test_volatile_history_lower_score(self) -> None:
        """High variance in historical scores should yield lower consistency."""
        history = [
            {"composite_score": 2.0, "timestamp": "2025-01-01T00:00:00Z"},
            {"composite_score": 10.0, "timestamp": "2025-01-02T00:00:00Z"},
            {"composite_score": 3.0, "timestamp": "2025-01-03T00:00:00Z"},
            {"composite_score": 9.0, "timestamp": "2025-01-04T00:00:00Z"},
        ]
        result = score._analyze_consistency(history)
        self.assertLessEqual(result["score"], 6)

    def test_moderate_variance(self) -> None:
        """Moderate variance: std_dev between 0.8 and 1.5."""
        history = [
            {"composite_score": 7.0, "timestamp": "2025-01-01T00:00:00Z"},
            {"composite_score": 8.5, "timestamp": "2025-01-02T00:00:00Z"},
            {"composite_score": 7.5, "timestamp": "2025-01-03T00:00:00Z"},
            {"composite_score": 9.0, "timestamp": "2025-01-04T00:00:00Z"},
        ]
        result = score._analyze_consistency(history)
        # std_dev ~ 0.73, which is < 0.8, so gets +1 bonus -> 9
        # or std_dev ~ 0.73 -> 8+1=9
        self.assertIn(result["score"], [7, 8, 9])


# ===================================================================
# 8. Transcript loading
# ===================================================================


class TestLoadTranscript(unittest.TestCase):
    """Verify transcript loading for plain text and JSON-lines."""

    def test_plain_text(self) -> None:
        content = "line one\nline two\n\nline three\n"
        path = _write_temp_file(content)
        try:
            lines = score.load_transcript(path)
            self.assertEqual(lines, ["line one", "line two", "line three"])
        finally:
            os.unlink(path)

    def test_jsonl_format(self) -> None:
        records = [
            json.dumps({"content": "message one"}),
            json.dumps({"text": "message two"}),
            json.dumps({"message": "message three"}),
        ]
        content = "\n".join(records) + "\n"
        path = _write_temp_file(content)
        try:
            lines = score.load_transcript(path)
            self.assertEqual(lines, ["message one", "message two", "message three"])
        finally:
            os.unlink(path)

    def test_mixed_json_and_text(self) -> None:
        content = '{"content": "json line"}\nplain text line\n'
        path = _write_temp_file(content)
        try:
            lines = score.load_transcript(path)
            self.assertEqual(lines, ["json line", "plain text line"])
        finally:
            os.unlink(path)

    def test_nonexistent_file_exits(self) -> None:
        with self.assertRaises(SystemExit):
            score.load_transcript("/tmp/nonexistent-transcript-xyz.txt")

    def test_empty_file_returns_empty_list(self) -> None:
        path = _write_temp_file("")
        try:
            lines = score.load_transcript(path)
            self.assertEqual(lines, [])
        finally:
            os.unlink(path)


# ===================================================================
# 9. Rubric parsing
# ===================================================================


class TestParseRubricCriteria(unittest.TestCase):
    """Verify _parse_rubric_criteria() extracts dimension sections."""

    def test_parses_headings(self) -> None:
        rubric_text = (
            "# Top-level heading\n"
            "### Correctness\n"
            "Must be factually accurate.\n"
            "### Completeness\n"
            "All items addressed.\n"
        )
        criteria = score._parse_rubric_criteria(rubric_text)
        self.assertIn("correctness", criteria)
        self.assertIn("completeness", criteria)
        self.assertIn("factually accurate", criteria["correctness"])

    def test_empty_text_returns_empty(self) -> None:
        criteria = score._parse_rubric_criteria("")
        self.assertEqual(criteria, {})


# ===================================================================
# 10. Score persistence
# ===================================================================


class TestSaveScore(unittest.TestCase):
    """Verify save_score() creates the file correctly."""

    def test_creates_file(self) -> None:
        tmp_dir = _make_temp_dir()
        scorecard = {
            "skill": "test-skill",
            "timestamp": "2025-01-15T12:00:00Z",
            "composite_score": 8.5,
        }
        path = score.save_score(scorecard, tmp_dir)
        self.assertTrue(Path(path).exists())
        saved = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(saved["composite_score"], 8.5)

    def test_creates_directory_if_missing(self) -> None:
        tmp_dir = Path(_make_temp_dir()) / "nested" / "scores"
        scorecard = {
            "skill": "test",
            "timestamp": "2025-01-01T00:00:00Z",
            "composite_score": 5.0,
        }
        path = score.save_score(scorecard, str(tmp_dir))
        self.assertTrue(Path(path).exists())

    def test_filename_contains_skill_name(self) -> None:
        tmp_dir = _make_temp_dir()
        scorecard = {
            "skill": "my-skill",
            "timestamp": "2025-06-01T10:30:00Z",
            "composite_score": 7.0,
        }
        path = score.save_score(scorecard, tmp_dir)
        self.assertIn("my-skill", Path(path).name)


# ===================================================================
# 11. One-liner generation
# ===================================================================


class TestGenerateOneLiner(unittest.TestCase):
    """Verify _generate_one_liner() for different composite ranges."""

    def _make_dims(self, scores: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        return {d: {"score": s} for d, s in scores.items()}

    def test_excellent_range(self) -> None:
        dims = self._make_dims({d: 10 for d in score.DEFAULT_WEIGHTS})
        result = score._generate_one_liner("code-review", "A+", 9.5, dims)
        self.assertIn("Excellent", result)

    def test_good_range(self) -> None:
        dims = self._make_dims({d: 8 for d in score.DEFAULT_WEIGHTS})
        result = score._generate_one_liner("testing", "B+", 8.0, dims)
        self.assertIn("Good", result)

    def test_acceptable_range(self) -> None:
        dims = self._make_dims({d: 6 for d in score.DEFAULT_WEIGHTS})
        result = score._generate_one_liner("docs", "C", 6.0, dims)
        self.assertIn("Acceptable", result)

    def test_below_par_range(self) -> None:
        dims = self._make_dims({d: 3 for d in score.DEFAULT_WEIGHTS})
        result = score._generate_one_liner("security", "F", 3.0, dims)
        self.assertIn("Below-par", result)


# ===================================================================
# 12. Critical issues and recommendations
# ===================================================================


class TestCriticalIssues(unittest.TestCase):
    """Verify _extract_critical_issues() finds dimensions <= 4."""

    def test_no_critical_issues(self) -> None:
        dims = {d: {"score": 8, "justification": "fine"} for d in score.DEFAULT_WEIGHTS}
        issues = score._extract_critical_issues(dims)
        self.assertEqual(issues, [])

    def test_detects_low_scoring_dimension(self) -> None:
        dims = {
            "correctness": {"score": 3, "justification": "many errors"},
            "safety": {"score": 9, "justification": "safe"},
        }
        issues = score._extract_critical_issues(dims)
        self.assertEqual(len(issues), 1)
        self.assertIn("correctness", issues[0])


class TestRecommendations(unittest.TestCase):
    """Verify _generate_recommendations() for low-scoring dimensions."""

    def test_high_scores_no_recommendations(self) -> None:
        dims = {d: {"score": 9} for d in score.DEFAULT_WEIGHTS}
        recs = score._generate_recommendations(dims)
        self.assertEqual(recs, [])

    def test_low_score_generates_recommendation(self) -> None:
        dims = {d: {"score": 9} for d in score.DEFAULT_WEIGHTS}
        dims["safety"] = {"score": 5}
        recs = score._generate_recommendations(dims)
        self.assertTrue(len(recs) > 0)
        self.assertTrue(any("secret" in r.lower() or "safety" in r.lower() for r in recs))


# ===================================================================
# 13. Integration: build_scorecard()
# ===================================================================


class TestBuildScorecard(unittest.TestCase):
    """Integration test for the full build_scorecard() pipeline."""

    def test_full_pipeline_produces_valid_scorecard(self) -> None:
        """Build a scorecard from a minimal transcript and verify structure."""
        transcript_content = (
            "User asked to review code.\n"
            "Read file main.py\n"
            "The code looks correct with good structure.\n"
            "## Summary\n"
            "All tests pass. No edge case issues found.\n"
            "Write(review.md) -- saved review output.\n"
            + "Additional analysis line.\n" * 50
        )
        transcript_path = _write_temp_file(transcript_content)
        scores_dir = _make_temp_dir()
        rubric_dir = str(RUBRICS_DIR)

        try:
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=transcript_path,
                rubric_dir=rubric_dir,
                scores_dir=scores_dir,
                config_path=None,
            )

            # Verify top-level keys
            self.assertIn("skill", card)
            self.assertIn("composite_score", card)
            self.assertIn("raw_composite", card)
            self.assertIn("grade", card)
            self.assertIn("grade_label", card)
            self.assertIn("dimensions", card)
            self.assertIn("red_flags", card)
            self.assertIn("bonuses", card)
            self.assertIn("adjustments", card)
            self.assertIn("summary", card)
            self.assertIn("one_liner", card)
            self.assertIn("rubric_used", card)
            self.assertIn("timestamp", card)
            self.assertIn("_saved_to", card)

            # Verify dimension structure
            self.assertEqual(len(card["dimensions"]), len(score.DEFAULT_WEIGHTS))
            for dim_name, dim_data in card["dimensions"].items():
                self.assertIn("score", dim_data)
                self.assertIn("weight", dim_data)
                self.assertIn("weighted", dim_data)
                self.assertIn("justification", dim_data)
                self.assertGreaterEqual(dim_data["score"], 1)
                self.assertLessEqual(dim_data["score"], 10)

            # Verify composite is in valid range
            self.assertGreaterEqual(card["composite_score"], 1.0)
            self.assertLessEqual(card["composite_score"], 10.0)

            # Verify file was persisted
            self.assertTrue(Path(card["_saved_to"]).exists())

        finally:
            os.unlink(transcript_path)


# ===================================================================
# 14. CLI argument parsing
# ===================================================================


class TestParseArgs(unittest.TestCase):
    """Verify parse_args() parses CLI arguments correctly."""

    def test_all_required_args(self) -> None:
        args = score.parse_args([
            "--skill", "code-review",
            "--transcript", "/tmp/t.txt",
            "--rubric-dir", "/tmp/rubrics",
            "--scores-dir", "/tmp/scores",
        ])
        self.assertEqual(args.skill, "code-review")
        self.assertEqual(args.transcript, "/tmp/t.txt")
        self.assertEqual(args.rubric_dir, "/tmp/rubrics")
        self.assertEqual(args.scores_dir, "/tmp/scores")
        self.assertIsNone(args.config)

    def test_optional_config(self) -> None:
        args = score.parse_args([
            "--skill", "test",
            "--transcript", "/tmp/t.txt",
            "--rubric-dir", "/tmp/r",
            "--scores-dir", "/tmp/s",
            "--config", "/tmp/config.json",
        ])
        self.assertEqual(args.config, "/tmp/config.json")

    def test_missing_required_arg_exits(self) -> None:
        with self.assertRaises(SystemExit):
            score.parse_args(["--skill", "test"])


# ===================================================================
# 15. Count matches helper
# ===================================================================


class TestCountMatches(unittest.TestCase):
    """Verify _count_matches() counts all regex hits across lines."""

    def test_multiple_matches_per_line(self) -> None:
        lines = ["error and error and failure"]
        count = score._count_matches(score.ERROR_PATTERNS, lines)
        self.assertEqual(count, 3)

    def test_no_matches(self) -> None:
        lines = ["all good here", "nothing wrong"]
        count = score._count_matches(score.ERROR_PATTERNS, lines)
        self.assertEqual(count, 0)

    def test_empty_lines(self) -> None:
        count = score._count_matches(score.ERROR_PATTERNS, [])
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
