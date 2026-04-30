#!/usr/bin/env python3
"""Tests for the EU AI Act audit-trail rubric (CC2, v1.4.2).

NOT LEGAL ADVICE. Tests verify rubric *plumbing*, not regulatory
compliance.
"""
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
        self.assertTrue((RUBRICS_DIR / "eu-ai-act-audit-trail.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "eu-ai-act-audit-trail.weights.json").is_file()
        )

    def test_dimension_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "eu-ai-act-audit-trail.weights.json").read_text(
                encoding="utf-8"
            )
        )
        dim_keys = {
            "correctness", "completeness", "adherence", "actionability",
            "efficiency", "safety", "consistency",
        }
        dim_total = sum(v for k, v in weights.items() if k in dim_keys)
        self.assertAlmostEqual(dim_total, 1.0, places=6)

    def test_disclaimer_in_rubric_header(self) -> None:
        text = (RUBRICS_DIR / "eu-ai-act-audit-trail.md").read_text(
            encoding="utf-8"
        )
        # O13 — disclaimer must be in the rubric file itself.
        self.assertIn("NOT LEGAL ADVICE", text)
        self.assertIn("NOT COUNSEL-REVIEWED", text)
        self.assertIn("Issue O13", text)

    def test_primary_law_urls_present(self) -> None:
        text = (RUBRICS_DIR / "eu-ai-act-audit-trail.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("artificialintelligenceact.eu/article/19", text)
        self.assertIn("artificialintelligenceact.eu/article/26", text)


class TestComputeEuAiActAuditEvidence(unittest.TestCase):
    def test_inactive_for_other_rubrics(self) -> None:
        out = score._compute_eu_ai_act_audit_evidence(
            ["[retention: 365d+]"], "code-review",
        )
        self.assertFalse(out["log_retention_attestation"])
        self.assertFalse(out["audit_trail_complete"])

    def test_load_bearing_three_pass_yields_complete(self) -> None:
        lines = [
            "[retention: 365d+]",
            "[reason: Article 26 human-oversight] flagging",
            "[human-in-loop reviewer:dpo-anna] approved",
        ]
        out = score._compute_eu_ai_act_audit_evidence(
            lines, "eu-ai-act-audit-trail",
        )
        self.assertTrue(out["log_retention_attestation"])
        self.assertTrue(out["decision_logic_grounding"])
        self.assertTrue(out["human_intervention_points"])
        self.assertTrue(out["audit_trail_complete"])
        self.assertEqual(out["retention_days_declared"], 365)

    def test_retention_below_floor_fails(self) -> None:
        lines = [
            "[retention: 30d]",
            "[reason: x]",
            "[human-in-loop x]",
        ]
        out = score._compute_eu_ai_act_audit_evidence(
            lines, "eu-ai-act-audit-trail",
        )
        self.assertFalse(out["log_retention_attestation"])
        self.assertFalse(out["audit_trail_complete"])

    def test_missing_decision_logic_fails(self) -> None:
        lines = ["[retention: 200d+]", "[human-in-loop x]"]
        out = score._compute_eu_ai_act_audit_evidence(
            lines, "eu-ai-act-audit-trail",
        )
        self.assertFalse(out["audit_trail_complete"])

    def test_missing_human_intervention_fails(self) -> None:
        lines = ["[retention: 200d+]", "[reason: x]"]
        out = score._compute_eu_ai_act_audit_evidence(
            lines, "eu-ai-act-audit-trail",
        )
        self.assertFalse(out["audit_trail_complete"])

    def test_provenance_attribution_consent_refusal_independent(self) -> None:
        # All three load-bearing fail; the secondary flags still report
        # accurately and don't dock audit_trail_complete (which is
        # gated on the load-bearing three).
        lines = [
            "[source: https://x.example.com retrieved-at: 2026-04-29]",
            "[agent: bob]",
            "[consent: t1]",
            "[refused-out-of-scope]",
        ]
        out = score._compute_eu_ai_act_audit_evidence(
            lines, "eu-ai-act-audit-trail",
        )
        self.assertTrue(out["data_source_provenance"])
        self.assertTrue(out["tool_use_attribution"])
        self.assertTrue(out["no_shadow_decisioning"])
        self.assertTrue(out["refusal_on_out_of_scope_data"])
        self.assertFalse(out["audit_trail_complete"])


class TestEndToEndScoring(unittest.TestCase):
    def test_passing_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="eu-ai-act-audit-trail",
                transcript_path=str(FIXTURES_DIR / "eu-audit-trace.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            self.assertEqual(card["rubric_used"], "eu-ai-act-audit-trail")
            self.assertEqual(card["weights_source"], "rubric")
            audit = card["adjustments"]["eu_ai_act_audit"]
            self.assertTrue(audit["log_retention_attestation"])
            self.assertTrue(audit["decision_logic_grounding"])
            self.assertTrue(audit["human_intervention_points"])
            self.assertTrue(audit["audit_trail_complete"])

    def test_no_legal_compliance_claim_in_summary(self) -> None:
        # Rubric must NOT add anything to the summary that could be
        # mistaken for a compliance attestation.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="eu-ai-act-audit-trail",
                transcript_path=str(FIXTURES_DIR / "eu-audit-trace.jsonl"),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            summary = card["summary"].lower()
            for forbidden in (
                "compliant", "compliance", "legally", "regulator-approved",
                "passes regulation",
            ):
                self.assertNotIn(forbidden, summary)


if __name__ == "__main__":
    unittest.main()
