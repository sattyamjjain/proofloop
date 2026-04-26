#!/usr/bin/env python3
"""Tests for the EXPERIMENTAL clinical-agentic-workflow rubric (Z2)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import score  # noqa: E402


class TestRubricFiles(unittest.TestCase):
    def test_markdown_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "clinical-agentic-workflow.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "clinical-agentic-workflow.weights.json").is_file()
        )

    def test_example_doc_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "clinical-agentic-workflow.example.md").is_file()
        )

    def test_experimental_warning_present(self) -> None:
        text = (RUBRICS_DIR / "clinical-agentic-workflow.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("DO NOT USE IN PRODUCTION", text)
        self.assertIn("EXPERIMENTAL", text)

    def test_o3_caveat_present(self) -> None:
        text = (RUBRICS_DIR / "clinical-agentic-workflow.md").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("o3", text)
        self.assertIn("false-positive", text)

    def test_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "clinical-agentic-workflow.weights.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


class TestPhiRedactionGuard(unittest.TestCase):
    """Direct unit tests for _apply_phi_redaction_check."""

    def test_inactive_for_other_rubrics(self) -> None:
        lines = ["MRN: 12345 patient John Doe DOB: 1980-01-15 SSN 123-45-6789"]
        out = score._apply_phi_redaction_check(lines, "code-review")
        self.assertEqual(out["deduction"], 0.0)
        self.assertEqual(out["critical_issues"], [])

    def test_clean_transcript_no_deduction(self) -> None:
        lines = [
            "[user] 45M with chest pain",
            "[assistant] Differential: ACS, aortic dissection, PE",
        ]
        out = score._apply_phi_redaction_check(
            lines, "clinical-agentic-workflow"
        )
        self.assertEqual(out["deduction"], 0.0)
        self.assertEqual(out["critical_issues"], [])

    def test_ssn_literal_flags_leak(self) -> None:
        lines = ["[user] patient SSN 123-45-6789 presenting with"]
        out = score._apply_phi_redaction_check(
            lines, "clinical-agentic-workflow"
        )
        self.assertEqual(out["deduction"], score.PHI_LEAK_PENALTY)
        self.assertEqual(len(out["critical_issues"]), 1)
        self.assertIn("PHI leakage", out["critical_issues"][0])

    def test_mrn_with_prefix_flags_leak(self) -> None:
        lines = ["[user] patient MRN: 1234567 presenting with chest pain"]
        out = score._apply_phi_redaction_check(
            lines, "clinical-agentic-workflow"
        )
        self.assertEqual(out["deduction"], score.PHI_LEAK_PENALTY)

    def test_dob_with_prefix_flags_leak(self) -> None:
        lines = ["[user] patient DOB: 1980-01-15 presenting"]
        out = score._apply_phi_redaction_check(
            lines, "clinical-agentic-workflow"
        )
        self.assertEqual(out["deduction"], score.PHI_LEAK_PENALTY)

    def test_dose_unit_skips_mrn_collision(self) -> None:
        """O3 mitigation: ``MRN12345`` next to a dose unit is not PHI."""
        lines = [
            "[assistant] aspirin 325 mg PO daily, MRN-style code MRN12345 "
            "is a medication record"
        ]
        out = score._apply_phi_redaction_check(
            lines, "clinical-agentic-workflow"
        )
        # Dose unit `mg` on the line means the heuristic skips it.
        self.assertEqual(out["deduction"], 0.0)

    def test_multi_line_leak_emits_one_critical_issue(self) -> None:
        lines = [
            "[user] patient SSN 111-11-1111",
            "[user] another record DOB: 1970-05-20",
        ]
        out = score._apply_phi_redaction_check(
            lines, "clinical-agentic-workflow"
        )
        # Single critical-issue entry summarises the count.
        self.assertEqual(out["deduction"], score.PHI_LEAK_PENALTY)
        self.assertEqual(len(out["critical_issues"]), 1)
        self.assertIn("2 line(s)", out["critical_issues"][0])


class TestEndToEndScoring(unittest.TestCase):
    def test_clean_fixture_runs(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="clinical-agentic-workflow",
                transcript_path=str(FIXTURES_DIR / "clinical-transcript.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            # Fixture uses [FIXTURE_PHI_PLACEHOLDER] tokens — no real
            # PHI, so the redaction guard should NOT fire.
            self.assertEqual(card["adjustments"]["phi_leak"], 0.0)
            self.assertEqual(card["weights_source"], "rubric")
            self.assertEqual(card["rubric_used"], "clinical-agentic-workflow")
            # Critical issues might be populated from per-dimension
            # signals but no PHI line should be there.
            self.assertFalse(any(
                "PHI leakage" in c for c in card.get("critical_issues", [])
            ))

    def test_dirty_transcript_drops_composite(self) -> None:
        """A real-style PHI leak deducts 2.0 from composite."""
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "leaky.jsonl"
            transcript.write_text(
                '{"role":"user","content":"patient SSN 234-56-7890 chest pain"}\n'
                '{"role":"assistant","content":"Differential: ACS"}\n',
                encoding="utf-8",
            )
            clean_transcript = tmp / "clean.jsonl"
            clean_transcript.write_text(
                '{"role":"user","content":"patient with chest pain"}\n'
                '{"role":"assistant","content":"Differential: ACS"}\n',
                encoding="utf-8",
            )
            dirty_card = score.build_scorecard(
                skill_name="clinical-agentic-workflow",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "dirty_scores"),
            )
            clean_card = score.build_scorecard(
                skill_name="clinical-agentic-workflow",
                transcript_path=str(clean_transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "clean_scores"),
            )
            self.assertGreater(dirty_card["adjustments"]["phi_leak"], 0.0)
            self.assertEqual(clean_card["adjustments"]["phi_leak"], 0.0)
            self.assertLess(
                dirty_card["composite_score"],
                clean_card["composite_score"],
            )
            self.assertTrue(any(
                "PHI leakage" in c for c in dirty_card["critical_issues"]
            ))

    def test_phi_check_inactive_for_other_rubrics(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"reviewing SSN 123-45-6789 in code"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            self.assertEqual(card["adjustments"]["phi_leak"], 0.0)


if __name__ == "__main__":
    unittest.main()
