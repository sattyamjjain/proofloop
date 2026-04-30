#!/usr/bin/env python3
"""Tests for the routine-trajectory detection in the claude-code adapter (CC4)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
from adapters import claude_code as cc  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import score  # noqa: E402


class TestDetectRoutineTriggered(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop(cc.ROUTINE_DETECTION_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(cc.ROUTINE_DETECTION_ENV, None)

    def test_explicit_marker_anywhere_in_lines(self) -> None:
        self.assertTrue(cc._detect_routine_triggered([
            "first line",
            "[routine_trigger: nightly-001]",
        ]))

    def test_no_marker_no_env_no_routine(self) -> None:
        self.assertFalse(cc._detect_routine_triggered([
            "assistant: doing stuff",
            "assistant: more stuff",
        ]))

    def test_env_one_enables_heuristic(self) -> None:
        os.environ[cc.ROUTINE_DETECTION_ENV] = "1"
        self.assertTrue(cc._detect_routine_triggered([
            "assistant: doing stuff",
            "assistant: more stuff",
        ]))

    def test_user_turn_in_head_blocks_heuristic(self) -> None:
        os.environ[cc.ROUTINE_DETECTION_ENV] = "1"
        self.assertFalse(cc._detect_routine_triggered([
            '{"role":"user","content":"hi"}',
            "assistant: response",
        ]))

    def test_empty_input_not_routine(self) -> None:
        self.assertFalse(cc._detect_routine_triggered([]))


class TestExtractLinesPrependsTrajectoryKindCC4(unittest.TestCase):
    def test_canonical_routine_fixture(self) -> None:
        path = PROJECT_ROOT / "tests" / "fixtures" / "routine-trace.jsonl"
        lines = cc.extract_lines(str(path))
        self.assertEqual(lines[0], cc.TRAJECTORY_KIND_ROUTINE)


class TestConsistencyRelaxesForRoutine(unittest.TestCase):
    def test_routine_lines_recognized_by_helper(self) -> None:
        self.assertTrue(score._is_routine_trajectory([
            cc.TRAJECTORY_KIND_ROUTINE,
            "assistant: doing stuff",
        ]))

    def test_consistency_neutral_score_includes_routine_note(self) -> None:
        out = score._analyze_consistency(
            history=[],
            transcript_lines=[cc.TRAJECTORY_KIND_ROUTINE, "x"],
        )
        self.assertIn("routine", out["justification"])

    def test_high_variance_routine_dings_less(self) -> None:
        # Same history; one with routine sentinel, one without.
        # std_dev with [9, 5, 9, 5, 9] = ~2.0; this hits the
        # interactive "moderate" bucket but the routine "some" bucket.
        history = [
            {"composite_score": 9.0},
            {"composite_score": 5.0},
            {"composite_score": 9.0},
            {"composite_score": 5.0},
            {"composite_score": 9.0},
        ]
        interactive = score._analyze_consistency(
            history, transcript_lines=["assistant: x"],
        )
        routine = score._analyze_consistency(
            history,
            transcript_lines=[cc.TRAJECTORY_KIND_ROUTINE, "assistant: x"],
        )
        self.assertGreaterEqual(routine["score"], interactive["score"])
        self.assertIn("routine", routine["justification"])


if __name__ == "__main__":
    unittest.main()
