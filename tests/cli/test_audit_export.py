#!/usr/bin/env python3
"""Tests for verdict audit-export CLI (T1, v1.4.2). NOT LEGAL ADVICE."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import audit_export as ae  # noqa: E402


def _scorecard(
    skill: str = "eu-ai-act-audit-trail",
    timestamp: str = "2026-04-29T12:00:00Z",
    audit_complete: bool = True,
) -> dict:
    return {
        "skill": skill,
        "rubric_used": skill,
        "timestamp": timestamp,
        "composite_score": 8.0,
        "adjustments": {
            "eu_ai_act_audit": {
                "log_retention_attestation": True,
                "decision_logic_grounding": True,
                "human_intervention_points": True,
                "data_source_provenance": True,
                "tool_use_attribution": True,
                "no_shadow_decisioning": True,
                "refusal_on_out_of_scope_data": True,
                "audit_trail_complete": audit_complete,
                "retention_days_declared": 365,
            },
        },
    }


class TestRedactTranscriptLine(unittest.TestCase):
    def test_email_redacted(self) -> None:
        out = ae.redact_transcript_line("contact alice@example.com")
        self.assertIn("<EMAIL>", out)
        self.assertNotIn("alice@example.com", out)

    def test_phone_redacted(self) -> None:
        out = ae.redact_transcript_line("call +1-555-123-4567")
        self.assertIn("<PHONE>", out)

    def test_ssn_redacted(self) -> None:
        out = ae.redact_transcript_line("SSN 123-45-6789")
        self.assertIn("<SSN>", out)

    def test_api_key_redacted(self) -> None:
        out = ae.redact_transcript_line("sk-1234567890abcdefghij")
        self.assertIn("<API_KEY>", out)

    def test_clean_line_unchanged(self) -> None:
        out = ae.redact_transcript_line("hello world")
        self.assertEqual(out, "hello world")


class TestCollectScorecards(unittest.TestCase):
    def test_filter_by_rubric(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "a.json").write_text(json.dumps(
                _scorecard(skill="eu-ai-act-audit-trail")), encoding="utf-8")
            (tmp / "b.json").write_text(json.dumps(
                _scorecard(skill="code-review")), encoding="utf-8")
            cards = ae.collect_scorecards(
                tmp, "eu-ai-act-audit-trail", None, None,
            )
            self.assertEqual(len(cards), 1)

    def test_filter_by_date_window(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "old.json").write_text(json.dumps(
                _scorecard(timestamp="2025-01-01T00:00:00Z")), encoding="utf-8")
            (tmp / "new.json").write_text(json.dumps(
                _scorecard(timestamp="2026-04-29T12:00:00Z")), encoding="utf-8")
            cards = ae.collect_scorecards(
                tmp, None,
                ae._parse_iso_date("2026-01-01"),
                ae._parse_iso_date("2026-12-31"),
            )
            self.assertEqual(len(cards), 1)

    def test_malformed_scorecard_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "bad.json").write_text("{broken", encoding="utf-8")
            (tmp / "good.json").write_text(json.dumps(_scorecard()), encoding="utf-8")
            cards = ae.collect_scorecards(tmp, None, None, None)
            self.assertEqual(len(cards), 1)


class TestBuildBundle(unittest.TestCase):
    def test_bundle_contains_methodology_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            sc_path = tmp / "sc1.json"
            sc_path.write_text(json.dumps(_scorecard()), encoding="utf-8")
            out_zip = tmp / "bundle.zip"
            summary = ae.build_bundle(
                [(sc_path, _scorecard())], out_zip,
            )
            self.assertEqual(summary["rows_written"], 1)
            with zipfile.ZipFile(out_zip) as zf:
                names = zf.namelist()
                self.assertIn("methodology.md", names)
                self.assertIn("manifest.csv", names)
                manifest = zf.read("manifest.csv").decode("utf-8")
                self.assertIn("eu-ai-act-audit-trail", manifest)
                methodology = zf.read("methodology.md").decode("utf-8")
                self.assertIn("NOT LEGAL ADVICE", methodology)
                self.assertIn("Issue O13", methodology)
                self.assertIn("Issue O16", methodology)

    def test_clinical_rubric_refused_per_o16(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            sc = _scorecard(skill="clinical-agentic-workflow")
            sc_path = tmp / "clin.json"
            sc_path.write_text(json.dumps(sc), encoding="utf-8")
            out_zip = tmp / "bundle.zip"
            summary = ae.build_bundle([(sc_path, sc)], out_zip)
            self.assertEqual(summary["rows_written"], 0)
            self.assertIn("clinical-agentic-workflow", summary["refused_rubrics"])

    def test_empty_input_writes_header_only_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            out_zip = tmp / "bundle.zip"
            ae.build_bundle([], out_zip)
            with zipfile.ZipFile(out_zip) as zf:
                manifest = zf.read("manifest.csv").decode("utf-8")
            self.assertIn("scorecard_name", manifest)


class TestCli(unittest.TestCase):
    def test_canonical_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            scores = tmp / "scores"
            scores.mkdir()
            (scores / "a.json").write_text(json.dumps(_scorecard()), encoding="utf-8")
            out_zip = tmp / "audit.zip"
            with patch("sys.stdout", io.StringIO()) as buf:
                rc = ae.main([
                    "--scores-dir", str(scores),
                    "--rubric", "eu-ai-act-audit-trail",
                    "--out", str(out_zip),
                ])
            self.assertEqual(rc, 0)
            self.assertIn("NOT LEGAL ADVICE", buf.getvalue())
            self.assertTrue(out_zip.exists())

    def test_missing_scores_dir_returns_two(self) -> None:
        with patch("sys.stderr", io.StringIO()) as err:
            rc = ae.main([
                "--scores-dir", "/tmp/verdict-no-such",
                "--out", "/tmp/verdict-out.zip",
            ])
        self.assertEqual(rc, 2)
        self.assertIn("scores dir not found", err.getvalue())


if __name__ == "__main__":
    unittest.main()
