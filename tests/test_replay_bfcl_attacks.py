#!/usr/bin/env python3
"""Tests for the BFCL attack-vector replay harness (AA3)."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import replay_bfcl_attacks as rba  # noqa: E402


class TestLoadFixture(unittest.TestCase):
    def test_canonical_fixture_loads(self) -> None:
        records = rba.load_fixture(FIXTURES_DIR / "bfcl-attack-vectors.jsonl")
        self.assertEqual(len(records), 8)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            rba.load_fixture(Path("/tmp/verdict-bfcl-missing.jsonl"))

    def test_skips_blank_and_comment_lines(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            path = tmp / "fixture.jsonl"
            path.write_text(
                "# a comment\n\n"
                '{"attack_pattern":"x","attack_succeeded":false}\n'
                "\n"
                '{"attack_pattern":"y","attack_succeeded":true}\n',
                encoding="utf-8",
            )
            records = rba.load_fixture(path)
            self.assertEqual(len(records), 2)

    def test_skips_malformed_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            path = tmp / "fixture.jsonl"
            path.write_text(
                'not-json\n{"attack_pattern":"x","attack_succeeded":true}\n',
                encoding="utf-8",
            )
            records = rba.load_fixture(path)
            self.assertEqual(len(records), 1)


class TestAggregateOffline(unittest.TestCase):
    def test_empty_records(self) -> None:
        out = rba.aggregate_offline([])
        self.assertEqual(out["asr"], 0.0)
        self.assertEqual(out["attack_count"], 0)

    def test_all_succeeded(self) -> None:
        records = [
            {"attack_pattern": "x", "attack_succeeded": True},
            {"attack_pattern": "y", "attack_succeeded": True},
        ]
        out = rba.aggregate_offline(records)
        self.assertEqual(out["asr"], 1.0)
        self.assertEqual(out["succeeded"], 2)
        self.assertEqual(out["failed"], 0)

    def test_all_failed(self) -> None:
        records = [
            {"attack_pattern": "x", "attack_succeeded": False},
            {"attack_pattern": "y", "attack_succeeded": False},
        ]
        out = rba.aggregate_offline(records)
        self.assertEqual(out["asr"], 0.0)

    def test_per_pattern_breakdown(self) -> None:
        records = [
            {"attack_pattern": "name_confusion", "attack_succeeded": True},
            {"attack_pattern": "name_confusion", "attack_succeeded": False},
            {"attack_pattern": "schema_overflow", "attack_succeeded": True},
        ]
        out = rba.aggregate_offline(records)
        self.assertEqual(out["per_pattern"]["name_confusion"]["count"], 2)
        self.assertEqual(out["per_pattern"]["name_confusion"]["succeeded"], 1)
        self.assertEqual(out["per_pattern"]["schema_overflow"]["succeeded"], 1)

    def test_canonical_fixture_asr(self) -> None:
        records = rba.load_fixture(FIXTURES_DIR / "bfcl-attack-vectors.jsonl")
        out = rba.aggregate_offline(records)
        # Fixture: 3 succeeded (schema_overflow, side_channel_naming,
        # provenance_spoofing); 5 failed.
        self.assertEqual(out["succeeded"], 3)
        self.assertEqual(out["failed"], 5)
        self.assertEqual(out["asr"], 0.375)


class TestCli(unittest.TestCase):
    def test_offline_mode_writes_json_to_out(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            out_path = tmp / "asr.json"
            rc = rba.main([
                "--fixture", str(FIXTURES_DIR / "bfcl-attack-vectors.jsonl"),
                "--mode", "offline-fixture",
                "--out", str(out_path),
            ])
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["attack_count"], 8)
            self.assertEqual(payload["asr"], 0.375)

    def test_live_replay_mode_returns_nonzero(self) -> None:
        err = io.StringIO()
        with patch("sys.stderr", err):
            rc = rba.main([
                "--fixture", str(FIXTURES_DIR / "bfcl-attack-vectors.jsonl"),
                "--mode", "live-replay",
            ])
        self.assertEqual(rc, 2)
        self.assertIn("live-replay mode is reserved", err.getvalue())

    def test_missing_fixture_returns_nonzero(self) -> None:
        rc = rba.main([
            "--fixture", "/tmp/verdict-bfcl-no-such",
            "--mode", "offline-fixture",
        ])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
