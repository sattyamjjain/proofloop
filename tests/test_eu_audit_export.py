#!/usr/bin/env python3
"""Tests for eu_audit_export.py (CC2, v1.4.2). NOT LEGAL ADVICE."""
from __future__ import annotations

import csv
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
import eu_audit_export as eae  # noqa: E402


class TestExtractAuditRows(unittest.TestCase):
    def test_empty_input_no_rows(self) -> None:
        self.assertEqual(eae.extract_audit_rows([]), [])

    def test_decision_with_reason_extracted(self) -> None:
        lines = [
            "[retention: 200d+] [agent: bob]",
            "[reason: Article 26 human-oversight] flagging for review",
        ]
        rows = eae.extract_audit_rows(lines)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_id"], "bob")
        self.assertEqual(rows[0]["retention_window"], "200d")
        self.assertIn("Article 26", rows[0]["reason"])

    def test_human_in_loop_paired_within_window(self) -> None:
        lines = [
            "[reason: x] approving",
            "[human-in-loop reviewer:anna]",
        ]
        rows = eae.extract_audit_rows(lines)
        self.assertEqual(rows[0]["human_in_loop"], "true")

    def test_human_in_loop_outside_window_not_paired(self) -> None:
        lines = [
            "[reason: x] approving",
            "no marker",
            "no marker",
            "no marker",
            "[human-in-loop reviewer:anna]",
        ]
        rows = eae.extract_audit_rows(lines)
        self.assertEqual(rows[0]["human_in_loop"], "false")

    def test_source_url_extracted(self) -> None:
        lines = [
            "[reason: y] [source: https://policy.example.com retrieved-at: 2026-04-29] approving",
        ]
        rows = eae.extract_audit_rows(lines)
        self.assertEqual(rows[0]["source_url"], "https://policy.example.com")

    def test_decision_verb_alone_qualifies(self) -> None:
        # No [reason: ...] but verb present.
        lines = ["denying request 12345 due to OOD"]
        rows = eae.extract_audit_rows(lines)
        self.assertEqual(len(rows), 1)
        self.assertIn("denying", rows[0]["decision"].lower())

    def test_scorecard_timestamp_propagates(self) -> None:
        lines = ["[reason: x] approving"]
        rows = eae.extract_audit_rows(lines, scorecard={
            "timestamp": "2026-04-29T12:00:00Z",
        })
        self.assertEqual(rows[0]["timestamp"], "2026-04-29T12:00:00Z")


class TestWriteAuditCsv(unittest.TestCase):
    def test_csv_header_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out_path = Path(t) / "audit.csv"
            eae.write_audit_csv([{
                "timestamp": "2026-04-29T12:00:00Z",
                "agent_id": "bob",
                "decision": "approving",
                "reason": "Article 26",
                "source_url": "https://x.example.com",
                "retention_window": "180d",
                "human_in_loop": "true",
            }], out_path)
            with out_path.open(encoding="utf-8") as fh:
                reader = csv.reader(fh)
                rows = list(reader)
            self.assertEqual(rows[0], [
                "timestamp", "agent_id", "decision", "reason",
                "source_url", "retention_window", "human_in_loop",
            ])
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1][1], "bob")


class TestCli(unittest.TestCase):
    def test_canonical_fixture_yields_rows(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out_path = Path(t) / "audit.csv"
            with patch("sys.stdout", io.StringIO()):
                rc = eae.main([
                    "--transcript", str(FIXTURES_DIR / "eu-audit-trace.jsonl"),
                    "--out", str(out_path),
                ])
            self.assertEqual(rc, 0)
            with out_path.open(encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            self.assertGreaterEqual(len(rows), 1)

    def test_missing_transcript_returns_two(self) -> None:
        with patch("sys.stderr", io.StringIO()) as err:
            rc = eae.main([
                "--transcript", "/tmp/verdict-no-such.jsonl",
                "--out", "/tmp/verdict-out.csv",
            ])
        self.assertEqual(rc, 2)
        self.assertIn("transcript not found", err.getvalue())

    def test_missing_scorecard_returns_two(self) -> None:
        with patch("sys.stderr", io.StringIO()) as err:
            rc = eae.main([
                "--transcript", str(FIXTURES_DIR / "eu-audit-trace.jsonl"),
                "--scorecard", "/tmp/verdict-no-such.json",
                "--out", "/tmp/verdict-out.csv",
            ])
        self.assertEqual(rc, 2)
        self.assertIn("scorecard not found", err.getvalue())

    def test_disclaimer_in_stdout(self) -> None:
        # NOT LEGAL ADVICE banner must appear in CLI output.
        with tempfile.TemporaryDirectory() as t:
            out_path = Path(t) / "audit.csv"
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                eae.main([
                    "--transcript", str(FIXTURES_DIR / "eu-audit-trace.jsonl"),
                    "--out", str(out_path),
                ])
            self.assertIn("NOT LEGAL ADVICE", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
