#!/usr/bin/env python3
"""Auto Memory cross-session transcript stitching tests (N1)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "claude-code-multisession"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
from adapters import claude_code  # noqa: E402
import adapters  # noqa: E402


class TestMultiSessionFixture(unittest.TestCase):
    """The committed fixture must stitch to exactly 2 session breaks."""

    def test_directory_mode_emits_session_breaks(self) -> None:
        lines = claude_code.extract_lines(str(FIXTURES_DIR))
        breaks = [i for i, line in enumerate(lines) if line == claude_code.SESSION_BREAK_MARKER]
        self.assertEqual(len(breaks), 2, f"expected 2 session breaks, got {len(breaks)}")

    def test_memory_block_prefixed(self) -> None:
        lines = claude_code.extract_lines(str(FIXTURES_DIR))
        memory_lines = [line for line in lines if line.startswith(claude_code.MEMORY_PREFIX)]
        self.assertGreaterEqual(len(memory_lines), 1)
        self.assertIn("memory", memory_lines[0].lower())

    def test_every_session_represented(self) -> None:
        lines = claude_code.extract_lines(str(FIXTURES_DIR))
        joined = "\n".join(lines)
        self.assertIn("auth middleware", joined)
        self.assertIn("redis_client.py", joined)
        self.assertIn("Summarise both reviews", joined)

    def test_session_order_by_mtime(self) -> None:
        lines = claude_code.extract_lines(str(FIXTURES_DIR))
        auth_idx = next(i for i, ln in enumerate(lines) if "auth middleware" in ln)
        cache_idx = next(i for i, ln in enumerate(lines) if "redis_client" in ln)
        summary_idx = next(i for i, ln in enumerate(lines) if "Summarise both" in ln)
        self.assertLess(auth_idx, cache_idx)
        self.assertLess(cache_idx, summary_idx)


class TestDirectoryModeTmp(unittest.TestCase):
    def test_empty_directory_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(claude_code.extract_lines(tmp), [])

    def test_single_session_dir_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "01-only.jsonl"
            path.write_text(
                json.dumps({"role": "user", "content": "hi"}) + "\n",
                encoding="utf-8",
            )
            lines = claude_code.extract_lines(tmp)
            self.assertEqual(lines, ["hi"])
            self.assertNotIn(claude_code.SESSION_BREAK_MARKER, lines)

    def test_mtime_ordering_not_filename(self) -> None:
        """Filename z- should sort after a- alphabetically but if mtime
        is reversed, the adapter follows mtime."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            early = root / "z-earliest.jsonl"
            late = root / "a-latest.jsonl"
            early.write_text(json.dumps({"role": "user", "content": "first"}) + "\n", encoding="utf-8")
            late.write_text(json.dumps({"role": "user", "content": "second"}) + "\n", encoding="utf-8")
            base = int(time.time())
            os.utime(early, (base, base))
            os.utime(late, (base + 5, base + 5))
            lines = claude_code.extract_lines(tmp)
            self.assertEqual(lines[0], "first")
            self.assertEqual(lines[-1], "second")


class TestFileModeBackwardCompatible(unittest.TestCase):
    def test_file_path_still_parses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one.jsonl"
            path.write_text(
                json.dumps({"role": "user", "content": "x"}) + "\n"
                + json.dumps({"role": "assistant", "content": "y"}) + "\n",
                encoding="utf-8",
            )
            lines = claude_code.extract_lines(str(path))
            self.assertEqual(lines, ["x", "y"])


class TestMemoryMarkerDetection(unittest.TestCase):
    def test_memory_block_token_flags_preamble(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            path.write_text(
                json.dumps({"memory_block": True, "content": "prior-run summary"}) + "\n"
                + json.dumps({"role": "user", "content": "now the real question"}) + "\n",
                encoding="utf-8",
            )
            lines = claude_code.extract_lines(str(path))
            self.assertTrue(any(ln.startswith(claude_code.MEMORY_PREFIX) for ln in lines))
            self.assertTrue(any(ln == "now the real question" for ln in lines))

    def test_auto_memory_token_flags_preamble(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            path.write_text(
                json.dumps({"auto-memory": True, "content": "auto loaded"}) + "\n"
                + json.dumps({"role": "user", "content": "go"}) + "\n",
                encoding="utf-8",
            )
            lines = claude_code.extract_lines(str(path))
            self.assertIn(claude_code.MEMORY_PREFIX + "auto loaded", lines)

    def test_user_turn_closes_memory_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            path.write_text(
                json.dumps({"memory_block": True, "content": "preamble line"}) + "\n"
                + json.dumps({"role": "user", "content": "real user turn"}) + "\n"
                + json.dumps({"role": "assistant", "content": "normal assistant reply"}) + "\n",
                encoding="utf-8",
            )
            lines = claude_code.extract_lines(str(path))
            prefixed = [ln for ln in lines if ln.startswith(claude_code.MEMORY_PREFIX)]
            self.assertEqual(prefixed, [claude_code.MEMORY_PREFIX + "preamble line"])
            self.assertIn("real user turn", lines)
            self.assertIn("normal assistant reply", lines)


class TestAdapterRegistry(unittest.TestCase):
    def test_claude_code_adapter_still_registered(self) -> None:
        self.assertIs(
            adapters.get_adapter("claude-code"),
            claude_code.extract_lines,
        )


if __name__ == "__main__":
    unittest.main()
