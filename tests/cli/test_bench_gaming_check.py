#!/usr/bin/env python3
"""Tests for verdict bench gaming-check CLI (T2, v1.4.2)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import bench_gaming_check as bgc  # noqa: E402


class TestCli(unittest.TestCase):
    def test_clean_run_returns_zero(self) -> None:
        with patch("sys.stdout", io.StringIO()):
            rc = bgc.main([
                "--transcript", str(FIXTURES_DIR / "swe-bench-gaming-trace.jsonl"),
                "--benchmark", "swe-bench-pro",
            ])
        self.assertEqual(rc, 0)

    def test_gaming_run_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            tx.write_text(
                '{"role":"assistant","content":"echo PASSED > /tmp/r"}\n',
                encoding="utf-8",
            )
            with patch("sys.stdout", io.StringIO()):
                rc = bgc.main([
                    "--transcript", str(tx),
                    "--benchmark", "swe-bench-pro",
                ])
        self.assertEqual(rc, 1)

    def test_strict_flag_dings_short_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            # One reasoning turn — well below the default 3-turn strict floor.
            tx.write_text(
                '{"role":"assistant","content":"This is a single multi-word reasoning turn that exceeds 30 chars but is the only one."}\n',
                encoding="utf-8",
            )
            with patch("sys.stdout", io.StringIO()):
                rc = bgc.main([
                    "--transcript", str(tx),
                    "--benchmark", "swe-bench-pro",
                    "--strict",
                ])
        self.assertEqual(rc, 1)

    def test_strict_floor_raises_above_pack_default(self) -> None:
        # The signature pack's built-in floor is 3 reasoning turns;
        # a clean SWE-bench fixture clears it. With --strict and a
        # higher floor (10), even the clean fixture should fail.
        with patch("sys.stdout", io.StringIO()):
            rc = bgc.main([
                "--transcript", str(FIXTURES_DIR / "swe-bench-gaming-trace.jsonl"),
                "--benchmark", "swe-bench-pro",
                "--strict",
                "--strict-min-turns", "10",
            ])
        self.assertEqual(rc, 1)

    def test_missing_transcript_returns_two(self) -> None:
        with patch("sys.stderr", io.StringIO()) as err:
            rc = bgc.main([
                "--transcript", "/tmp/verdict-no-such",
                "--benchmark", "swe-bench-pro",
            ])
        self.assertEqual(rc, 2)
        self.assertIn("transcript not found", err.getvalue())

    def test_json_output_emits_findings(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            tx.write_text(
                '{"role":"assistant","content":"echo PASSED > /tmp/r"}\n',
                encoding="utf-8",
            )
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = bgc.main([
                    "--transcript", str(tx),
                    "--benchmark", "swe-bench-pro",
                    "--output", "json",
                ])
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertGreaterEqual(len(payload["exploits"]), 1)


if __name__ == "__main__":
    unittest.main()
