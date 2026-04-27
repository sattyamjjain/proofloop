#!/usr/bin/env python3
"""Tests for skills/judge/scripts/cost_estimator.py (R4)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import cost_estimator as ce  # noqa: E402


class TestEstimateUsd(unittest.TestCase):
    def test_zero_tokens_zero_cost(self) -> None:
        out = ce.estimate_usd(0, 0, "claude-haiku-4-5")
        self.assertEqual(out["total_usd"], 0.0)

    def test_known_model_uses_table_rates(self) -> None:
        # Haiku: $1/Mtok input, $5/Mtok output
        out = ce.estimate_usd(1_000_000, 1_000_000, "claude-haiku-4-5")
        self.assertEqual(out["input_usd"], 1.0)
        self.assertEqual(out["output_usd"], 5.0)
        self.assertEqual(out["total_usd"], 6.0)
        self.assertEqual(out["model_used"], "claude-haiku-4-5")

    def test_unknown_model_falls_back_to_default(self) -> None:
        out = ce.estimate_usd(1000, 1000, "unknown-model-7b")
        self.assertEqual(out["model_used"], "default")
        self.assertEqual(out["model_lookup"], "unknown-model-7b")
        self.assertGreater(out["total_usd"], 0.0)

    def test_negative_tokens_raises(self) -> None:
        with self.assertRaises(ValueError):
            ce.estimate_usd(-1, 0, "claude-haiku-4-5")

    def test_pricing_override_applied(self) -> None:
        custom = {
            "claude-haiku-4-5": {"input": 100.0, "output": 200.0},
            "default": {"input": 50.0, "output": 100.0},
        }
        out = ce.estimate_usd(1_000_000, 1_000_000, "claude-haiku-4-5", custom)
        self.assertEqual(out["total_usd"], 300.0)

    def test_gpt_5_5_pricing(self) -> None:
        # GPT-5.5: $5 / $30 per Mtok
        out = ce.estimate_usd(1_000_000, 1_000_000, "gpt-5-5")
        self.assertEqual(out["input_usd"], 5.0)
        self.assertEqual(out["output_usd"], 30.0)


class TestLoadPricing(unittest.TestCase):
    def test_no_path_returns_default_table(self) -> None:
        out = ce.load_pricing(None)
        self.assertIn("claude-haiku-4-5", out)
        self.assertIn("default", out)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ce.load_pricing("/tmp/verdict-no-such-pricing.json")

    def test_bad_json_raises(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8",
        ) as f:
            f.write("not-json")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                ce.load_pricing(path)
        finally:
            Path(path).unlink()

    def test_custom_pricing_loads(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8",
        ) as f:
            json.dump({"my-model": {"input": 2.0, "output": 8.0}}, f)
            path = f.name
        try:
            table = ce.load_pricing(path)
            self.assertEqual(table["my-model"]["input"], 2.0)
            self.assertIn("default", table)  # auto-injected
        finally:
            Path(path).unlink()


class TestEstimateFromScorecard(unittest.TestCase):
    def test_no_llm_usage_block_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card_path = tmp / "card.json"
            card_path.write_text(
                json.dumps({"skill": "x", "model": "claude-haiku-4-5"}),
                encoding="utf-8",
            )
            out = ce.estimate_from_scorecard(str(card_path))
            self.assertEqual(out["total_usd"], 0.0)
            self.assertIn("heuristics only", out["rationale"])

    def test_with_llm_usage_returns_estimate(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card_path = tmp / "card.json"
            card_path.write_text(
                json.dumps({
                    "skill": "code-review",
                    "model": "claude-haiku-4-5",
                    "llm_usage": {
                        "input_tokens": 100_000,
                        "output_tokens": 50_000,
                    },
                }),
                encoding="utf-8",
            )
            out = ce.estimate_from_scorecard(str(card_path))
            # 100k input @ $1/Mtok = $0.1; 50k output @ $5/Mtok = $0.25
            self.assertAlmostEqual(out["total_usd"], 0.35, places=4)

    def test_missing_scorecard_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ce.estimate_from_scorecard("/tmp/verdict-no-such.json")


class TestCli(unittest.TestCase):
    def test_direct_estimate_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            out_path = tmp / "out.json"
            rc = ce.main([
                "--input-tokens", "1000000",
                "--output-tokens", "0",
                "--model", "claude-haiku-4-5",
                "--out", str(out_path),
            ])
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["total_usd"], 1.0)

    def test_scorecard_mode_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card_path = tmp / "card.json"
            card_path.write_text(
                json.dumps({
                    "skill": "code-review",
                    "model": "claude-haiku-4-5",
                    "llm_usage": {"input_tokens": 1000, "output_tokens": 500},
                }),
                encoding="utf-8",
            )
            out_path = tmp / "out.json"
            rc = ce.main([
                "--scorecard", str(card_path),
                "--out", str(out_path),
            ])
            self.assertEqual(rc, 0)

    def test_no_args_returns_nonzero(self) -> None:
        rc = ce.main([])
        self.assertEqual(rc, 2)

    def test_direct_estimate_without_model_returns_nonzero(self) -> None:
        rc = ce.main(["--input-tokens", "100", "--output-tokens", "50"])
        self.assertEqual(rc, 2)


class TestNoSaaSCoupling(unittest.TestCase):
    """Hard contract: no telemetry / network / dashboard imports."""

    def test_no_requests_loaded(self) -> None:
        for name in list(sys.modules):
            top = name.split(".", 1)[0]
            self.assertFalse(
                top in ("requests", "httpx", "aiohttp"),
                f"unexpected HTTP client loaded: {name}",
            )


if __name__ == "__main__":
    unittest.main()
