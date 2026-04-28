#!/usr/bin/env python3
"""Tests for the verdict ship-gate CLI (S1, v1.4.1)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import ship_gate  # noqa: E402


def _scorecard(
    composite: float = 8.0,
    ship_ready: bool = True,
    failed_floors: list[str] | None = None,
) -> dict:
    return {
        "skill": "ship-readiness",
        "composite_score": composite,
        "dimensions": {},
        "adjustments": {
            "ship_readiness": {
                "ship_ready": ship_ready,
                "failed_floors": failed_floors or [],
                "floor_evidence": {},
                "deduction": 0.0,
            },
        },
    }


class TestLoadScorecard(unittest.TestCase):
    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ship_gate.load_scorecard("/tmp/verdict-no-such.json")

    def test_malformed_json_raises(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "bad.json"
            p.write_text("not-json", encoding="utf-8")
            with self.assertRaises(ValueError):
                ship_gate.load_scorecard(str(p))

    def test_non_object_raises(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "list.json"
            p.write_text("[1, 2, 3]", encoding="utf-8")
            with self.assertRaises(ValueError):
                ship_gate.load_scorecard(str(p))

    def test_well_formed_returns_dict(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "ok.json"
            p.write_text(json.dumps(_scorecard()), encoding="utf-8")
            data = ship_gate.load_scorecard(str(p))
            self.assertEqual(data["skill"], "ship-readiness")


class TestEvaluateGate(unittest.TestCase):
    def test_all_pass(self) -> None:
        out = ship_gate.evaluate_gate(_scorecard(), floor=7.0)
        self.assertTrue(out["passed"])
        self.assertEqual(out["failures"], [])

    def test_ship_floors_failed(self) -> None:
        out = ship_gate.evaluate_gate(
            _scorecard(ship_ready=False, failed_floors=["cost_bound_honored"]),
            floor=7.0,
        )
        self.assertFalse(out["passed"])
        self.assertEqual(len(out["failures"]), 1)
        self.assertIn("ship_readiness", out["failures"][0])

    def test_composite_below_floor(self) -> None:
        out = ship_gate.evaluate_gate(_scorecard(composite=6.5), floor=7.0)
        self.assertFalse(out["passed"])
        self.assertIn("below floor", out["failures"][0])

    def test_regression_below_threshold(self) -> None:
        out = ship_gate.evaluate_gate(
            candidate := _scorecard(composite=7.6),
            floor=7.0,
            baseline=_scorecard(composite=8.0),
            max_regression_pct=0.10,
        )
        self.assertTrue(out["passed"])
        self.assertEqual(out["composite_delta"], -0.40)
        # Suppress unused-var warning.
        del candidate

    def test_regression_above_threshold(self) -> None:
        out = ship_gate.evaluate_gate(
            _scorecard(composite=7.0),
            floor=6.0,
            baseline=_scorecard(composite=8.0),
            max_regression_pct=0.05,
        )
        self.assertFalse(out["passed"])
        self.assertTrue(any("regressed" in f for f in out["failures"]))

    def test_no_baseline_skips_regression(self) -> None:
        out = ship_gate.evaluate_gate(
            _scorecard(composite=7.0), floor=7.0, baseline=None,
        )
        self.assertTrue(out["passed"])
        self.assertIsNone(out["composite_delta"])


class TestRenderSarif(unittest.TestCase):
    def test_passing_gate_yields_empty_results(self) -> None:
        sc = _scorecard()
        gate = ship_gate.evaluate_gate(sc, floor=7.0)
        sarif = ship_gate.render_sarif(sc, gate, "/tmp/sc.json")
        self.assertEqual(sarif["version"], "2.1.0")
        run = sarif["runs"][0]
        self.assertEqual(run["results"], [])
        self.assertTrue(run["invocations"][0]["executionSuccessful"])

    def test_failing_gate_yields_results(self) -> None:
        sc = _scorecard(ship_ready=False, failed_floors=["cost_bound_honored"])
        gate = ship_gate.evaluate_gate(sc, floor=7.0)
        sarif = ship_gate.render_sarif(sc, gate, "/tmp/sc.json")
        run = sarif["runs"][0]
        self.assertEqual(len(run["results"]), 1)
        self.assertEqual(run["results"][0]["ruleId"], "VERDICT-SHIP-001")
        self.assertFalse(run["invocations"][0]["executionSuccessful"])

    def test_rule_ids_stable(self) -> None:
        sc = _scorecard(composite=6.0)
        gate = ship_gate.evaluate_gate(sc, floor=7.0)
        sarif = ship_gate.render_sarif(sc, gate, "/tmp/sc.json")
        rule_ids = {r["ruleId"] for r in sarif["runs"][0]["results"]}
        self.assertIn("VERDICT-SHIP-002", rule_ids)


class TestCli(unittest.TestCase):
    def test_passing_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "sc.json"
            p.write_text(json.dumps(_scorecard()), encoding="utf-8")
            with patch("sys.stdout", io.StringIO()):
                rc = ship_gate.main(["--scorecard", str(p), "--floor", "7.0"])
            self.assertEqual(rc, 0)

    def test_failing_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "sc.json"
            p.write_text(
                json.dumps(_scorecard(ship_ready=False,
                                       failed_floors=["cost_bound_honored"])),
                encoding="utf-8",
            )
            with patch("sys.stdout", io.StringIO()):
                rc = ship_gate.main(["--scorecard", str(p), "--floor", "7.0"])
            self.assertEqual(rc, 1)

    def test_missing_scorecard_returns_two(self) -> None:
        with patch("sys.stderr", io.StringIO()) as err:
            rc = ship_gate.main(
                ["--scorecard", "/tmp/no-such.json", "--floor", "7.0"]
            )
        self.assertEqual(rc, 2)
        self.assertIn("scorecard not found", err.getvalue())

    def test_sarif_output_is_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "sc.json"
            p.write_text(json.dumps(_scorecard()), encoding="utf-8")
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = ship_gate.main([
                    "--scorecard", str(p),
                    "--floor", "7.0",
                    "--output", "sarif",
                ])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["version"], "2.1.0")

    def test_json_output_emits_failures(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "sc.json"
            p.write_text(
                json.dumps(_scorecard(composite=5.0)), encoding="utf-8",
            )
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = ship_gate.main([
                    "--scorecard", str(p),
                    "--floor", "7.0",
                    "--output", "json",
                ])
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["passed"])
            self.assertTrue(payload["failures"])


if __name__ == "__main__":
    unittest.main()
