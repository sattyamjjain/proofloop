#!/usr/bin/env python3
"""Tests for the OWASP MCP Top 10 (beta) coverage rubric.

The rubric is content-only — no scorer changes — so the tests pin:

- Both files exist (markdown + weights sidecar).
- Source-signal header present and points at the OWASP page.
- Every MCP01–MCP10 risk is named in the body.
- Weights sum to 1.0 with Safety dominating per design.
- ``score.load_rubric`` resolves the rubric.
- ``score.build_scorecard`` runs end-to-end against a fabricated
  MCP-server transcript without crashing and applies the sidecar
  weights.
- The rubric carries the BETA caveat so consumers can't miss the
  moving-target risk.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import score  # noqa: E402


class TestRubricFiles(unittest.TestCase):
    def test_markdown_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "owasp-mcp-top-10-beta.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue(
            (RUBRICS_DIR / "owasp-mcp-top-10-beta.weights.json").is_file()
        )

    def test_source_signal_present(self) -> None:
        text = (RUBRICS_DIR / "owasp-mcp-top-10-beta.md").read_text(encoding="utf-8")
        self.assertIn("source_signal:", text)
        self.assertIn("owasp.org/www-project-mcp-top-10", text)

    def test_every_mcp_risk_named(self) -> None:
        text = (RUBRICS_DIR / "owasp-mcp-top-10-beta.md").read_text(encoding="utf-8")
        for n in range(1, 11):
            label = f"MCP{n:02d}"
            self.assertIn(label, text, f"missing risk label {label}")

    def test_beta_caveat_present(self) -> None:
        # Whitespace-normalised: the caveat is wrapped to 60 cols in
        # source, so a literal substring match would fail on a line
        # break inside the phrase.
        text = " ".join(
            (RUBRICS_DIR / "owasp-mcp-top-10-beta.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )
        self.assertIn("beta", text)
        self.assertIn("not yet ratified", text)

    def test_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "owasp-mcp-top-10-beta.weights.json").read_text(encoding="utf-8")
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_safety_dominates(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "owasp-mcp-top-10-beta.weights.json").read_text(encoding="utf-8")
        )
        # Eight of ten risks land on Safety — the weight must reflect that.
        self.assertGreaterEqual(weights["safety"], 0.40)


class TestRubricResolves(unittest.TestCase):
    def test_load_rubric_returns_owasp_text(self) -> None:
        name, text = score.load_rubric(str(RUBRICS_DIR), "owasp-mcp-top-10-beta")
        self.assertEqual(name, "owasp-mcp-top-10-beta")
        self.assertIn("OWASP MCP Top 10", text)

    def test_load_rubric_weights_picks_up_sidecar(self) -> None:
        weights = score.load_rubric_weights(
            str(RUBRICS_DIR), "owasp-mcp-top-10-beta",
        )
        self.assertIsNotNone(weights)
        self.assertAlmostEqual(weights["safety"], 0.50)


class TestEndToEndScoring(unittest.TestCase):
    def test_build_scorecard_with_owasp_rubric(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"/owasp-mcp-top-10-beta scan this server"}\n'
                '{"role":"assistant","content":"Tool call: read_file(path=\\"app.py\\")"}\n'
                '{"role":"tool","content":"file content"}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="owasp-mcp-top-10-beta",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            # The sidecar weights must be applied (weights_source =
            # "rubric" not "config") since the rubric ships its own
            # weight file.
            self.assertEqual(card["weights_source"], "rubric")
            self.assertEqual(card["rubric_used"], "owasp-mcp-top-10-beta")
            # Safety dominates — its weighted contribution should be
            # the largest of the seven dimensions.
            weighted = {
                dim: card["dimensions"][dim]["weighted"]
                for dim in card["dimensions"]
            }
            top_dim = max(weighted, key=lambda d: weighted[d])
            self.assertEqual(top_dim, "safety")


if __name__ == "__main__":
    unittest.main()
