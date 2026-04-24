#!/usr/bin/env python3
"""Tests for prompt-caching support on the LLM second-opinion client.

Verifies that the AnthropicClient wraps the system prompt in a cached
content block when configured, picks up env-var TTL overrides, adds the
extended-cache-ttl-2025-04-11 beta header when TTL=1h, and logs cache
usage counters to stderr.

Uses urllib.request.urlopen monkey-patching so no real HTTP happens.
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))

from analyzers import llm_judge as lj  # noqa: E402


class _FakeResponse:
    """Context-manager shim that mimics urlopen's return value."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _canonical_api_response(
    cache_read: int = 0,
    cache_creation: int = 0,
) -> bytes:
    body: Dict[str, Any] = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5",
        "content": [{"type": "text", "text": json.dumps({
            "correctness": {"score": 8, "justification": "ok"},
        })}],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 40,
        },
    }
    if cache_read:
        body["usage"]["cache_read_input_tokens"] = cache_read
    if cache_creation:
        body["usage"]["cache_creation_input_tokens"] = cache_creation
    return json.dumps(body).encode("utf-8")


class _RequestCapture:
    """Captures the urllib.request.Request object intercepted by patch."""

    def __init__(self, response_bytes: bytes) -> None:
        self.response_bytes = response_bytes
        self.captured: List[Dict[str, Any]] = []

    def __call__(self, req: Any, timeout: Any = None) -> _FakeResponse:
        body = req.data.decode("utf-8") if req.data else ""
        self.captured.append({
            "headers": {k.lower(): v for k, v in req.headers.items()},
            "body": json.loads(body) if body else {},
        })
        return _FakeResponse(self.response_bytes)


class TestResolveCacheTtlFromEnv(unittest.TestCase):
    def test_default_is_5m(self) -> None:
        self.assertEqual(lj.resolve_cache_ttl_from_env(env={}), "5m")

    def test_enable_1h_opts_into_1h(self) -> None:
        self.assertEqual(
            lj.resolve_cache_ttl_from_env(env={"ENABLE_PROMPT_CACHING_1H": "1"}),
            "1h",
        )

    def test_force_5m_wins_over_enable_1h(self) -> None:
        env = {
            "ENABLE_PROMPT_CACHING_1H": "1",
            "FORCE_PROMPT_CACHING_5M": "1",
        }
        self.assertEqual(lj.resolve_cache_ttl_from_env(env=env), "5m")

    def test_zero_disables_env_flag(self) -> None:
        env = {"ENABLE_PROMPT_CACHING_1H": "0"}
        self.assertEqual(lj.resolve_cache_ttl_from_env(env=env), "5m")

    def test_reads_process_environ_when_no_env_arg(self) -> None:
        with patch.dict(os.environ, {"ENABLE_PROMPT_CACHING_1H": "1"}, clear=False):
            self.assertEqual(lj.resolve_cache_ttl_from_env(), "1h")


class TestBuildCachedSystemBlock(unittest.TestCase):
    def test_default_ttl_is_5m(self) -> None:
        block = lj.build_cached_system_block("rubric text")
        self.assertEqual(block["type"], "text")
        self.assertEqual(block["text"], "rubric text")
        self.assertEqual(block["cache_control"], {"type": "ephemeral", "ttl": "5m"})

    def test_explicit_1h_ttl(self) -> None:
        block = lj.build_cached_system_block("x", ttl="1h")
        self.assertEqual(block["cache_control"]["ttl"], "1h")

    def test_invalid_ttl_raises(self) -> None:
        with self.assertRaises(ValueError):
            lj.build_cached_system_block("x", ttl="30m")


class TestAnthropicClientWithCache(unittest.TestCase):
    def test_no_cache_ttl_sends_plain_system_string(self) -> None:
        capture = _RequestCapture(_canonical_api_response())
        client = lj.AnthropicClient(api_key="sk-ant-test", prompt_cache_ttl=None)
        with patch("urllib.request.urlopen", capture):
            client.messages_create("claude-haiku-4-5", "rubric", "prompt")
        body = capture.captured[0]["body"]
        self.assertEqual(body["system"], "rubric")
        self.assertNotIn("anthropic-beta", capture.captured[0]["headers"])

    def test_5m_ttl_wraps_system_in_cached_block(self) -> None:
        capture = _RequestCapture(_canonical_api_response())
        client = lj.AnthropicClient(api_key="sk-ant-test", prompt_cache_ttl="5m")
        with patch("urllib.request.urlopen", capture):
            client.messages_create("claude-haiku-4-5", "rubric text", "prompt")
        body = capture.captured[0]["body"]
        self.assertIsInstance(body["system"], list)
        self.assertEqual(body["system"][0]["type"], "text")
        self.assertEqual(body["system"][0]["text"], "rubric text")
        self.assertEqual(
            body["system"][0]["cache_control"],
            {"type": "ephemeral", "ttl": "5m"},
        )
        # 5m does NOT require the extended-cache beta header.
        self.assertNotIn(
            "extended-cache-ttl-2025-04-11",
            capture.captured[0]["headers"].get("anthropic-beta", ""),
        )

    def test_1h_ttl_adds_extended_cache_beta_header(self) -> None:
        capture = _RequestCapture(_canonical_api_response())
        client = lj.AnthropicClient(api_key="sk-ant-test", prompt_cache_ttl="1h")
        with patch("urllib.request.urlopen", capture):
            client.messages_create("claude-haiku-4-5", "rubric", "prompt")
        header = capture.captured[0]["headers"]["anthropic-beta"]
        self.assertIn("extended-cache-ttl-2025-04-11", header)

    def test_cache_and_task_budget_betas_stack(self) -> None:
        capture = _RequestCapture(_canonical_api_response())
        client = lj.AnthropicClient(
            api_key="sk-ant-test",
            prompt_cache_ttl="1h",
            budget_tokens=50_000,
            log_budget_countdown=False,
        )
        with patch("urllib.request.urlopen", capture):
            client.messages_create("claude-haiku-4-5", "rubric", "prompt")
        header = capture.captured[0]["headers"]["anthropic-beta"]
        self.assertIn("extended-cache-ttl-2025-04-11", header)
        self.assertIn("task_budgets-2026-03-13", header)

    def test_invalid_cache_ttl_on_client_raises(self) -> None:
        with self.assertRaises(ValueError):
            lj.AnthropicClient(api_key="sk-ant-test", prompt_cache_ttl="30m")

    def test_cache_usage_logged_to_stderr(self) -> None:
        capture = _RequestCapture(
            _canonical_api_response(cache_read=85, cache_creation=15)
        )
        client = lj.AnthropicClient(api_key="sk-ant-test", prompt_cache_ttl="5m")
        err = io.StringIO()
        with patch("urllib.request.urlopen", capture), patch("sys.stderr", err):
            client.messages_create("claude-haiku-4-5", "rubric", "prompt")
        log = err.getvalue()
        self.assertIn("cache_hit=85", log)
        self.assertIn("cache_miss=15", log)
        self.assertIn("model=claude-haiku-4-5", log)

    def test_no_cache_usage_log_when_caching_disabled(self) -> None:
        capture = _RequestCapture(
            _canonical_api_response(cache_read=0, cache_creation=0)
        )
        client = lj.AnthropicClient(api_key="sk-ant-test", prompt_cache_ttl=None)
        err = io.StringIO()
        with patch("urllib.request.urlopen", capture), patch("sys.stderr", err):
            client.messages_create("claude-haiku-4-5", "rubric", "prompt")
        self.assertNotIn("cache_hit", err.getvalue())


class TestScoreWithLlmUsesEnvTtl(unittest.TestCase):
    """score_with_llm must default to a cache-aware AnthropicClient."""

    def test_default_client_reads_env_ttl(self) -> None:
        # We intercept urlopen so no real API call happens; assert the
        # request body shows the 1h TTL when the env var is set.
        capture = _RequestCapture(_canonical_api_response())
        env = {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "ENABLE_PROMPT_CACHING_1H": "1",
        }
        with patch.dict(os.environ, env, clear=False), \
                patch("urllib.request.urlopen", capture):
            lj.score_with_llm(
                transcript=["hello"],
                rubric={"criteria": {}},
            )
        body = capture.captured[0]["body"]
        self.assertIsInstance(body["system"], list)
        self.assertEqual(body["system"][0]["cache_control"]["ttl"], "1h")

    def test_default_client_defaults_to_5m(self) -> None:
        capture = _RequestCapture(_canonical_api_response())
        env = {"ANTHROPIC_API_KEY": "sk-ant-test"}
        # Ensure the env-vars are clean for this test.
        with patch.dict(os.environ, env, clear=True), \
                patch("urllib.request.urlopen", capture):
            lj.score_with_llm(
                transcript=["hello"],
                rubric={"criteria": {}},
            )
        body = capture.captured[0]["body"]
        self.assertEqual(body["system"][0]["cache_control"]["ttl"], "5m")


if __name__ == "__main__":
    unittest.main()
