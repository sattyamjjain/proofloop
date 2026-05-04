#!/usr/bin/env python3
"""Tests for the opt-in PostToolUse duration_ms efficiency enrichment.

Claude Code v2.1.119 (2026-04-23) added ``duration_ms`` to
``PostToolUse`` and ``PostToolUseFailure`` hook inputs (tool execution
time, excluding permission prompts and PreToolUse hooks). Verdict's
``claude_code`` adapter emits ``[tool_duration_ms: <int>]`` per
record; the efficiency analyzer reports the durations on every
scorecard and optionally docks 0.5 when ≥3 calls exceed the
configurable threshold.

Default threshold ``null`` = report-only; pre-2.0.1 scorecards stay
identical.

Source: https://code.claude.com/docs/en/changelog
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))

import score  # noqa: E402
from adapters import claude_code as cc  # noqa: E402


class TestExtractDurationMs(unittest.TestCase):
    def test_top_level_duration_ms(self) -> None:
        rec = {"role": "assistant", "duration_ms": 1234}
        self.assertEqual(cc._extract_duration_ms(rec), 1234)

    def test_nested_in_hook_specific_output(self) -> None:
        rec = {"role": "assistant", "hookSpecificOutput": {"duration_ms": 500}}
        self.assertEqual(cc._extract_duration_ms(rec), 500)

    def test_top_level_wins_over_nested(self) -> None:
        rec = {
            "role": "assistant",
            "duration_ms": 100,
            "hookSpecificOutput": {"duration_ms": 999},
        }
        self.assertEqual(cc._extract_duration_ms(rec), 100)

    def test_absent_field_returns_none(self) -> None:
        self.assertIsNone(cc._extract_duration_ms({"role": "user"}))

    def test_negative_value_ignored(self) -> None:
        self.assertIsNone(cc._extract_duration_ms({"duration_ms": -1}))

    def test_string_value_ignored(self) -> None:
        self.assertIsNone(cc._extract_duration_ms({"duration_ms": "1234"}))

    def test_bool_value_ignored(self) -> None:
        # bool is a subclass of int but should NOT count.
        self.assertIsNone(cc._extract_duration_ms({"duration_ms": True}))


class TestAdapterEmitsTag(unittest.TestCase):
    def test_marker_appears_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tx.jsonl"
            path.write_text(
                json.dumps({"role": "user", "content": "hi"}) + "\n"
                + json.dumps({
                    "role": "assistant",
                    "content": "calling Bash",
                    "duration_ms": 1500,
                }) + "\n",
                encoding="utf-8",
            )
            lines = cc.extract_lines(str(path))
            joined = "\n".join(lines)
            self.assertIn("[tool_duration_ms: 1500]", joined)

    def test_no_marker_when_field_absent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tx.jsonl"
            path.write_text(
                json.dumps({"role": "assistant", "content": "no duration"}) + "\n",
                encoding="utf-8",
            )
            lines = cc.extract_lines(str(path))
            joined = "\n".join(lines)
            self.assertNotIn("tool_duration_ms", joined)


class TestExtractToolDurations(unittest.TestCase):
    def test_extracts_all_markers_in_order(self) -> None:
        lines = [
            "[tool_duration_ms: 100]",
            "regular line",
            "[tool_duration_ms: 250]",
            "[tool_duration_ms: 50]",
        ]
        self.assertEqual(score._extract_tool_durations(lines), [100, 250, 50])

    def test_no_markers_returns_empty(self) -> None:
        self.assertEqual(
            score._extract_tool_durations(["plain", "text", "lines"]),
            [],
        )


class TestAnalyzeEfficiencyDurationMs(unittest.TestCase):
    def _run(self, lines, threshold=None):
        return score._analyze_efficiency(
            lines, len(lines), tokenizer_baseline=1.0,
            duration_ms_dock_threshold=threshold,
        )

    def test_absent_markers_threshold_none_unchanged(self) -> None:
        # Threshold-null path is identical to v2.0.0: no duration_ms
        # extraction, no field on the result.
        lines = ["assistant: hello", "regular prose line"]
        out = self._run(lines, threshold=None)
        self.assertEqual(out["tool_durations_ms"], [])
        self.assertNotIn("exceeded", out["justification"])

    def test_markers_present_threshold_none_no_dock(self) -> None:
        # Threshold null → durations on the scorecard, no composite
        # delta from duration_ms (other heuristics like tool-call density
        # may still ding; we only assert the duration-specific behavior).
        lines = [
            "[tool_duration_ms: 50000]",
            "[tool_duration_ms: 60000]",
            "[tool_duration_ms: 70000]",
        ]
        out = self._run(lines, threshold=None)
        self.assertEqual(out["tool_durations_ms"], [50000, 60000, 70000])
        self.assertNotIn("exceeded", out["justification"])

    def test_threshold_set_three_slow_calls_dock(self) -> None:
        # 3 calls exceed 30000ms threshold → -0.5 dock + slowest cited.
        lines = [
            "tool_use: Bash [tool_duration_ms: 35000]",
            "tool_use: Bash [tool_duration_ms: 40000]",
            "tool_use: Bash [tool_duration_ms: 45000]",
        ]
        with_dock = self._run(lines, threshold=30000)
        without_dock = self._run(lines, threshold=None)
        self.assertLess(with_dock["score"], without_dock["score"])
        self.assertIn("exceeded 30000ms", with_dock["justification"])
        self.assertIn("45000", with_dock["justification"])

    def test_two_slow_calls_below_floor_no_dock(self) -> None:
        # Floor is 3 calls; 2 slow calls are not enough.
        lines = [
            "tool_use: Bash [tool_duration_ms: 35000]",
            "tool_use: Bash [tool_duration_ms: 40000]",
            "tool_use: Bash [tool_duration_ms: 100]",
        ]
        out = self._run(lines, threshold=30000)
        self.assertNotIn("exceeded", out["justification"])

    def test_post_tool_use_failure_records_also_counted(self) -> None:
        # Adapter emits the tag for both PostToolUse and PostToolUseFailure;
        # this test verifies the marker is detected regardless of source.
        lines = [
            "tool_failure [tool_duration_ms: 35000]",
            "tool_use [tool_duration_ms: 40000]",
            "tool_failure [tool_duration_ms: 45000]",
        ]
        out = self._run(lines, threshold=30000)
        self.assertEqual(len(out["tool_durations_ms"]), 3)
        self.assertIn("exceeded", out["justification"])


class TestEndToEnd(unittest.TestCase):
    def test_scorecard_carries_tool_durations_ms(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            transcript = tdir / "tx.jsonl"
            transcript.write_text(
                json.dumps({"role": "user", "content": "do work"}) + "\n"
                + json.dumps({
                    "role": "assistant",
                    "content": "running Bash",
                    "duration_ms": 800,
                }) + "\n",
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="default",
                transcript_path=str(transcript),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(tdir / "scores"),
            )
            efficiency = card["dimensions"]["efficiency"]
            self.assertIn("tool_durations_ms", efficiency)
            self.assertEqual(efficiency["tool_durations_ms"], [800])


if __name__ == "__main__":
    unittest.main()
