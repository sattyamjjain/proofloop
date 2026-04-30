#!/usr/bin/env python3
"""Tests for benchmark_gaming_detector.py (CC3, v1.4.2)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import benchmark_gaming_detector as bgd  # noqa: E402


class TestLoadSignaturePack(unittest.TestCase):
    def test_default_pack_loads(self) -> None:
        pack = bgd.load_signature_pack()
        self.assertEqual(pack["signature_pack"], "berkeley-rdi-2026-04-26")
        self.assertGreaterEqual(len(pack["exploits"]), 4)

    def test_unknown_pack_returns_empty(self) -> None:
        pack = bgd.load_signature_pack("does-not-exist")
        self.assertEqual(pack["exploits"], [])

    def test_pack_carries_source_url(self) -> None:
        pack = bgd.load_signature_pack()
        self.assertIn("rdi.berkeley.edu", pack.get("source_url", ""))


class TestScanTranscript(unittest.TestCase):
    def test_clean_swe_bench_run_no_findings(self) -> None:
        path = FIXTURES_DIR / "swe-bench-gaming-trace.jsonl"
        lines = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            try:
                lines.append(json.loads(raw)["content"])
            except (json.JSONDecodeError, KeyError):
                continue
        out = bgd.scan_transcript(lines, "swe-bench-pro")
        self.assertEqual(out["exploits"], [])

    def test_pytest_self_report_detected(self) -> None:
        lines = [
            "user: solve issue 12345",
            'echo "PASSED" > /tmp/result',
        ]
        out = bgd.scan_transcript(lines, "swe-bench-pro")
        klasses = {hit["exploit_class"] for hit in out["exploits"]}
        self.assertIn("harness-trust-pytest-self-report", klasses)

    def test_reward_file_tamper_detected(self) -> None:
        lines = [
            "assistant: gaming the harness",
            "echo 1.0 > /tmp/reward",
        ]
        out = bgd.scan_transcript(lines, "terminal-bench")
        klasses = {hit["exploit_class"] for hit in out["exploits"]}
        self.assertIn("reward-file-tamper", klasses)

    def test_scoring_grep_target_detected(self) -> None:
        lines = ["PASSED"]
        out = bgd.scan_transcript(lines, "swe-bench-pro")
        klasses = {hit["exploit_class"] for hit in out["exploits"]}
        self.assertIn("scoring-grep-target", klasses)

    def test_short_circuit_trajectory_detected(self) -> None:
        # Minimal trajectory — no reasoning turns.
        lines = ["PASS"]
        out = bgd.scan_transcript(lines, "swe-bench-pro")
        klasses = {hit["exploit_class"] for hit in out["exploits"]}
        self.assertIn("short-circuit-trajectory", klasses)

    def test_benchmark_filter_respected(self) -> None:
        lines = ["echo 1.0 > /tmp/reward"]
        # Reward-tamper is terminal-bench-only; on swe-bench it
        # shouldn't fire (per the signature pack's applies_to).
        out = bgd.scan_transcript(lines, "swe-bench-pro")
        klasses = {hit["exploit_class"] for hit in out["exploits"]}
        self.assertNotIn("reward-file-tamper", klasses)

    def test_unknown_benchmark_only_universal_fires(self) -> None:
        # An unknown benchmark — should match patterns whose applies_to
        # is empty / not set, but our pack scopes everything, so 0.
        lines = ["echo 1.0 > /tmp/reward"]
        out = bgd.scan_transcript(lines, "totally-unknown")
        self.assertEqual(out["exploits"], [])

    def test_dedup_per_class(self) -> None:
        # Two PASSED lines should still produce only one finding for
        # the scoring-grep-target class.
        lines = ["PASSED", "PASSED"]
        out = bgd.scan_transcript(lines, "swe-bench-pro")
        klasses = [hit["exploit_class"] for hit in out["exploits"]]
        self.assertEqual(klasses.count("scoring-grep-target"), 1)


class TestCli(unittest.TestCase):
    def test_clean_returns_zero(self) -> None:
        with patch("sys.stdout", io.StringIO()):
            rc = bgd.main([
                "--transcript", str(FIXTURES_DIR / "swe-bench-gaming-trace.jsonl"),
                "--benchmark", "swe-bench-pro",
            ])
        self.assertEqual(rc, 0)

    def test_gaming_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tx = Path(t) / "tx.jsonl"
            tx.write_text(
                '{"role":"assistant","content":"echo PASSED > /tmp/r"}\n',
                encoding="utf-8",
            )
            with patch("sys.stdout", io.StringIO()):
                rc = bgd.main([
                    "--transcript", str(tx),
                    "--benchmark", "swe-bench-pro",
                ])
        self.assertEqual(rc, 1)

    def test_missing_transcript_returns_two(self) -> None:
        with patch("sys.stderr", io.StringIO()) as err:
            rc = bgd.main([
                "--transcript", "/tmp/verdict-no-such.jsonl",
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
                rc = bgd.main([
                    "--transcript", str(tx),
                    "--benchmark", "swe-bench-pro",
                    "--output", "json",
                ])
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertGreaterEqual(len(payload["exploits"]), 1)


if __name__ == "__main__":
    unittest.main()
