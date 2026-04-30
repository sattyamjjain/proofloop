#!/usr/bin/env python3
"""Tests for the claude-code adapter's hook-rewrite tagging (CC1, v1.4.2)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
from adapters import claude_code as cc  # noqa: E402


class TestDetectHookRewrite(unittest.TestCase):
    def test_no_hook_record_returns_none(self) -> None:
        out = cc._detect_hook_rewrite({"role": "user", "content": "hi"}, "raw")
        self.assertIsNone(out)

    def test_canonical_v2_1_121_shape_extracted(self) -> None:
        record = {
            "role": "assistant",
            "tool_use_id": "t1",
            "tool": "Bash",
            "original_tool_output": "hello world",
            "hookSpecificOutput": {"updatedToolOutput": "REDACTED world"},
        }
        out = cc._detect_hook_rewrite(record, "raw")
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out["tool"], "Bash")
        self.assertEqual(out["tool_use_id"], "t1")
        # "REDACTED world" (14 bytes) / "hello world" (11 bytes).
        self.assertAlmostEqual(out["byte_delta"], 14 / 11, places=2)

    def test_no_original_returns_unit_byte_delta(self) -> None:
        record = {
            "role": "assistant",
            "tool": "WebSearch",
            "hookSpecificOutput": {"updatedToolOutput": "rewritten"},
        }
        out = cc._detect_hook_rewrite(record, "raw")
        assert out is not None
        self.assertEqual(out["byte_delta"], 1.0)

    def test_flattened_substring_fallback(self) -> None:
        # No nested object — the raw text carries the field name only.
        record = {"some_other_key": "value"}
        raw = "...hookSpecificOutput.updatedToolOutput..."
        out = cc._detect_hook_rewrite(record, raw)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out["tool"], "unknown")


class TestExtractLinesEmitsTags(unittest.TestCase):
    def test_rewrite_tagged_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            tx.write_text(
                '{"role":"user","content":"hi"}\n'
                '{"role":"assistant","tool":"Bash","original_tool_output":"x","hookSpecificOutput":{"updatedToolOutput":"REDACTED"}}\n',
                encoding="utf-8",
            )
            lines = cc.extract_lines(str(tx))
            joined = "\n".join(lines)
            self.assertIn("[hook-rewrote: Bash]", joined)
            self.assertIn("[hook-byte-delta:", joined)
            self.assertIn("hookSpecificOutput.updatedToolOutput", joined)

    def test_non_hook_records_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            tx.write_text(
                '{"role":"user","content":"hello"}\n'
                '{"role":"assistant","content":"hi"}\n',
                encoding="utf-8",
            )
            lines = cc.extract_lines(str(tx))
            joined = "\n".join(lines)
            self.assertNotIn("[hook-rewrote:", joined)


class TestDetectRoutineTriggered(unittest.TestCase):
    def test_explicit_marker_always_detected(self) -> None:
        lines = ["[routine_trigger: nightly-001]", "step 1"]
        self.assertTrue(cc._detect_routine_triggered(lines))

    def test_heuristic_off_by_default(self) -> None:
        # No human turn in first 5 lines, but env not set.
        lines = ["assistant: doing stuff"] * 5
        # Ensure env is unset for this test.
        import os
        os.environ.pop(cc.ROUTINE_DETECTION_ENV, None)
        self.assertFalse(cc._detect_routine_triggered(lines))

    def test_heuristic_active_with_env(self) -> None:
        import os
        os.environ[cc.ROUTINE_DETECTION_ENV] = "1"
        try:
            self.assertTrue(cc._detect_routine_triggered(
                ["assistant: doing stuff"] * 5,
            ))
            # User turn in head turns it off.
            self.assertFalse(cc._detect_routine_triggered([
                '{"role":"user","content":"hi"}',
                "assistant: doing stuff",
            ]))
        finally:
            os.environ.pop(cc.ROUTINE_DETECTION_ENV, None)

    def test_empty_input_not_routine(self) -> None:
        self.assertFalse(cc._detect_routine_triggered([]))


class TestExtractLinesPrependsTrajectoryKind(unittest.TestCase):
    def test_routine_trigger_marker_prepends_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            tx.write_text(
                '{"role":"system","content":"[routine_trigger: nightly-001]"}\n'
                '{"role":"assistant","content":"running"}\n',
                encoding="utf-8",
            )
            lines = cc.extract_lines(str(tx))
            self.assertEqual(lines[0], cc.TRAJECTORY_KIND_ROUTINE)

    def test_normal_transcript_no_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            tx.write_text(
                '{"role":"user","content":"hi"}\n'
                '{"role":"assistant","content":"hello"}\n',
                encoding="utf-8",
            )
            lines = cc.extract_lines(str(tx))
            joined = "\n".join(lines)
            self.assertNotIn(cc.TRAJECTORY_KIND_ROUTINE, joined)


if __name__ == "__main__":
    unittest.main()
