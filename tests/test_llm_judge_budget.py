#!/usr/bin/env python3
"""Verify the task_budgets-2026-03-13 beta header wiring (N2).

Uses a recording subclass of :class:`AnthropicClient` that intercepts
the outbound HTTP request so the tests never touch the network. We
inspect the exact headers and body that would have been sent to
`api.anthropic.com/v1/messages`.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

from analyzers import llm_judge as lj  # noqa: E402
import score as score_mod  # noqa: E402


class FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _canonical_anthropic_response() -> bytes:
    payload = {
        "content": [{"type": "text", "text": json.dumps({
            dim: {"score": 8, "justification": "ok"} for dim in lj.DIMENSIONS
        })}],
    }
    return json.dumps(payload).encode("utf-8")


class _Capture:
    """Intercepts urllib.request.urlopen so tests see the outgoing request."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, req, timeout):
        self.calls.append({
            "url": req.full_url,
            "headers": {k.lower(): v for k, v in req.header_items()},
            "body": json.loads(req.data.decode("utf-8")),
            "timeout": timeout,
        })
        return FakeHTTPResponse(_canonical_anthropic_response())


class TestTaskBudgetHeader(unittest.TestCase):
    def setUp(self) -> None:
        self.capture = _Capture()

    def test_no_budget_omits_beta_header_and_output_config(self) -> None:
        client = lj.AnthropicClient(api_key="sk-test", budget_tokens=None)
        with patch("urllib.request.urlopen", self.capture):
            client.messages_create(model="claude-haiku-4-5", system="s", prompt="p", max_tokens=1024)
        req = self.capture.calls[0]
        self.assertNotIn("anthropic-beta", req["headers"])
        self.assertNotIn("output_config", req["body"])
        self.assertEqual(req["body"]["max_tokens"], 1024)

    def test_budget_sets_beta_header(self) -> None:
        client = lj.AnthropicClient(
            api_key="sk-test", budget_tokens=25_000, log_budget_countdown=False,
        )
        with patch("urllib.request.urlopen", self.capture):
            client.messages_create(model="claude-haiku-4-5", system="s", prompt="p", max_tokens=1024)
        req = self.capture.calls[0]
        self.assertEqual(req["headers"]["anthropic-beta"], lj.TASK_BUDGETS_BETA)
        self.assertEqual(req["headers"]["anthropic-beta"], "task_budgets-2026-03-13")

    def test_budget_sets_output_config_shape(self) -> None:
        client = lj.AnthropicClient(
            api_key="sk-test", budget_tokens=30_000, log_budget_countdown=False,
        )
        with patch("urllib.request.urlopen", self.capture):
            client.messages_create(model="claude-haiku-4-5", system="s", prompt="p", max_tokens=1024)
        body = self.capture.calls[0]["body"]
        self.assertEqual(body["output_config"], {
            "task_budget": {"type": "tokens", "total": 30_000},
        })

    def test_budget_below_minimum_clamped_up(self) -> None:
        client = lj.AnthropicClient(
            api_key="sk-test", budget_tokens=5_000, log_budget_countdown=False,
        )
        with patch("urllib.request.urlopen", self.capture):
            client.messages_create(model="claude-haiku-4-5", system="s", prompt="p", max_tokens=1024)
        body = self.capture.calls[0]["body"]
        self.assertEqual(
            body["output_config"]["task_budget"]["total"],
            lj.TASK_BUDGET_MIN_TOKENS,
        )
        self.assertGreaterEqual(lj.TASK_BUDGET_MIN_TOKENS, 20_000)

    def test_max_tokens_raised_to_hard_ceiling(self) -> None:
        """max_tokens is the hard cap; when budget is higher, max_tokens climbs."""
        client = lj.AnthropicClient(
            api_key="sk-test", budget_tokens=40_000, log_budget_countdown=False,
        )
        with patch("urllib.request.urlopen", self.capture):
            client.messages_create(model="claude-haiku-4-5", system="s", prompt="p", max_tokens=2048)
        body = self.capture.calls[0]["body"]
        expected_ceiling = int(40_000 * lj.TASK_BUDGET_HARD_CEILING_RATIO)
        self.assertEqual(body["max_tokens"], expected_ceiling)

    def test_max_tokens_floor_keeps_caller_value(self) -> None:
        """If caller already asked for more than the hard ceiling, don't shrink it."""
        client = lj.AnthropicClient(
            api_key="sk-test", budget_tokens=20_000, log_budget_countdown=False,
        )
        huge = int(20_000 * lj.TASK_BUDGET_HARD_CEILING_RATIO) + 5_000
        with patch("urllib.request.urlopen", self.capture):
            client.messages_create(model="claude-haiku-4-5", system="s", prompt="p", max_tokens=huge)
        body = self.capture.calls[0]["body"]
        self.assertEqual(body["max_tokens"], huge)

    def test_countdown_emitted_to_stderr(self) -> None:
        import io
        import contextlib
        client = lj.AnthropicClient(
            api_key="sk-test", budget_tokens=25_000, log_budget_countdown=True,
        )
        buf = io.StringIO()
        with patch("urllib.request.urlopen", self.capture), contextlib.redirect_stderr(buf):
            client.messages_create(
                model="claude-haiku-4-5", system="s", prompt="p", max_tokens=1024,
            )
        self.assertIn("task_budget soft=", buf.getvalue())
        self.assertIn("hard_ceiling=", buf.getvalue())


class TestBudgetConfigPlumbing(unittest.TestCase):
    """score.py must forward the config block into the default client."""

    def test_config_task_budget_tokens_read(self) -> None:
        cfg = {"llm_second_opinion": {
            "enabled": True, "model": "claude-haiku-4-5",
            "task_budget_tokens": 30_000,
        }}
        parsed = score_mod._llm_second_opinion_config(cfg)
        self.assertEqual(parsed["task_budget_tokens"], 30_000)

    def test_missing_block_gives_none_budget(self) -> None:
        parsed = score_mod._llm_second_opinion_config({})
        self.assertIsNone(parsed["task_budget_tokens"])


if __name__ == "__main__":
    unittest.main()
