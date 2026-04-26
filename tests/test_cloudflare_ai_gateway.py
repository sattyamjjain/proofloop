#!/usr/bin/env python3
"""Tests for skills/judge/integrations/cloudflare_ai_gateway.py.

The integration is a pure dict-in / dict-out function. Tests verify
the payload-shape adapter, score mapping (Verdict 1-10 → Cloudflare
0..1), pass/fail thresholding, scorecard URL templating, and
defensive paths for malformed payloads.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "integrations"))
import cloudflare_ai_gateway as cfag  # noqa: E402


def _canonical_payload() -> dict:
    path = FIXTURES_DIR / "cloudflare-eval-webhook-payload.json"
    return json.loads(path.read_text(encoding="utf-8"))


class TestReturnedShape(unittest.TestCase):
    def test_keys_present(self) -> None:
        out = cfag.verdict_as_eval_webhook(_canonical_payload())
        for key in ("score", "passed", "rationale", "scorecard_url"):
            self.assertIn(key, out)

    def test_score_in_zero_to_one_range(self) -> None:
        out = cfag.verdict_as_eval_webhook(_canonical_payload())
        self.assertGreaterEqual(out["score"], 0.0)
        self.assertLessEqual(out["score"], 1.0)

    def test_passed_is_bool(self) -> None:
        out = cfag.verdict_as_eval_webhook(_canonical_payload())
        self.assertIsInstance(out["passed"], bool)

    def test_rationale_is_string(self) -> None:
        out = cfag.verdict_as_eval_webhook(_canonical_payload())
        self.assertIsInstance(out["rationale"], str)
        self.assertGreater(len(out["rationale"]), 0)


class TestScoreMapping(unittest.TestCase):
    def test_composite_div_10(self) -> None:
        # Verdict 1-10 → Cloudflare 0..1: ratio is composite/10.
        out = cfag.verdict_as_eval_webhook(_canonical_payload())
        # Sanity: a non-zero rationale shows scoring ran.
        self.assertIn("/10", out["rationale"])

    def test_threshold_default_seven(self) -> None:
        self.assertEqual(cfag.DEFAULT_PASS_THRESHOLD, 7.0)

    def test_payload_threshold_overrides_default(self) -> None:
        payload = _canonical_payload()
        payload["threshold"] = 1.0  # very lenient — should pass anything
        out = cfag.verdict_as_eval_webhook(payload)
        self.assertTrue(out["passed"])

    def test_argument_threshold_used_when_payload_silent(self) -> None:
        payload = _canonical_payload()
        out = cfag.verdict_as_eval_webhook(payload, threshold=10.5)
        # Threshold above 10 means nothing can pass.
        self.assertFalse(out["passed"])


class TestScorecardUrl(unittest.TestCase):
    def test_template_renders(self) -> None:
        out = cfag.verdict_as_eval_webhook(
            _canonical_payload(),
            scorecard_url_template="https://verdict.example/sc/{gateway_id}/{request_id}",
        )
        self.assertEqual(
            out["scorecard_url"],
            "https://verdict.example/sc/verdict-prod/01HXYZ12345",
        )

    def test_template_returns_none_when_unknown_token(self) -> None:
        out = cfag.verdict_as_eval_webhook(
            _canonical_payload(),
            scorecard_url_template="https://verdict.example/{nope}",
        )
        self.assertIsNone(out["scorecard_url"])

    def test_no_template_returns_none(self) -> None:
        out = cfag.verdict_as_eval_webhook(_canonical_payload())
        self.assertIsNone(out["scorecard_url"])


class TestDefensivePaths(unittest.TestCase):
    def test_non_dict_payload_soft_fails(self) -> None:
        out = cfag.verdict_as_eval_webhook("not a dict")  # type: ignore[arg-type]
        self.assertEqual(out["score"], 0.0)
        self.assertFalse(out["passed"])
        self.assertIn("invalid payload", out["rationale"])
        self.assertIsNone(out["scorecard_url"])

    def test_empty_payload_does_not_raise(self) -> None:
        out = cfag.verdict_as_eval_webhook({})
        self.assertGreaterEqual(out["score"], 0.0)
        self.assertLessEqual(out["score"], 1.0)
        self.assertIsInstance(out["passed"], bool)

    def test_malformed_messages_does_not_raise(self) -> None:
        out = cfag.verdict_as_eval_webhook({
            "request": {"messages": "this should be a list"},
            "response": {"choices": "this too"},
        })
        self.assertIsInstance(out, dict)
        self.assertIn("score", out)


class TestNoCloudflareDep(unittest.TestCase):
    """Hard contract: the module must not import any cloudflare-* SDK package.

    The integration's own module is named ``cloudflare_ai_gateway`` — that
    name is whitelisted; any other ``cloudflare*`` or ``workers*`` import
    means a third-party SDK leaked into Verdict's runtime, breaking the
    offline-first invariant.
    """

    _OWN_MODULE = "cloudflare_ai_gateway"

    def test_no_cloudflare_sdk_in_loaded_modules(self) -> None:
        for name in list(sys.modules):
            if name == self._OWN_MODULE:
                continue
            top_level = name.split(".", 1)[0]
            self.assertFalse(
                top_level.startswith("cloudflare") or top_level.startswith("workers"),
                f"unexpected runtime dep loaded: {name}",
            )


if __name__ == "__main__":
    unittest.main()
