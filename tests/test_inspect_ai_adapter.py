#!/usr/bin/env python3
"""Tests for skills/judge/adapters/inspect_ai_log.py."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
import adapters  # noqa: E402
from adapters import inspect_ai_log  # noqa: E402


def _write(content: str, suffix: str = ".json") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


class TestDetect(unittest.TestCase):
    def test_detects_samples_fingerprint(self) -> None:
        head = b'{"version":2,"eval": {"task":"x"},"samples":[]}'
        self.assertTrue(inspect_ai_log.detect(head))

    def test_rejects_unrelated_json(self) -> None:
        self.assertFalse(inspect_ai_log.detect(b'{"messages":[]}'))

    def test_empty_bytes(self) -> None:
        self.assertFalse(inspect_ai_log.detect(b""))

    def test_looks_like_on_file(self) -> None:
        path = _write('{"eval": {"task":"x"},"samples":[]}')
        try:
            self.assertTrue(inspect_ai_log.looks_like_inspect_ai_log(path))
        finally:
            os.unlink(path)


class TestExtractLines(unittest.TestCase):
    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(
            inspect_ai_log.extract_lines("/tmp/verdict-inspect-missing"),
            [],
        )

    def test_bad_json_returns_empty(self) -> None:
        path = _write("not-json")
        try:
            self.assertEqual(inspect_ai_log.extract_lines(path), [])
        finally:
            os.unlink(path)

    def test_emits_task_and_model_header(self) -> None:
        payload = {
            "eval": {"task": "demo", "model": "claude-opus-4-7"},
            "samples": [],
        }
        path = _write(json.dumps(payload))
        try:
            lines = inspect_ai_log.extract_lines(path)
            self.assertIn("[task] demo", lines)
            self.assertIn("[model] claude-opus-4-7", lines)
        finally:
            os.unlink(path)

    def test_assistant_tool_call_and_result(self) -> None:
        payload = {
            "eval": {"task": "t"},
            "samples": [{
                "id": "s1",
                "messages": [
                    {"role": "user", "content": "q"},
                    {
                        "role": "assistant",
                        "content": "calling",
                        "tool_calls": [
                            {"function": {"name": "read_file",
                                          "arguments": "{\"path\":\"x\"}"}}
                        ],
                    },
                    {"role": "tool", "content": "contents"},
                ],
                "scores": [{"name": "match", "value": 1.0}],
            }],
        }
        path = _write(json.dumps(payload))
        try:
            lines = inspect_ai_log.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[sample_start] s1", lines)
        self.assertIn("[user] q", lines)
        self.assertIn("[assistant] calling", lines)
        self.assertTrue(any(l.startswith("[tool_call] read_file(") for l in lines))
        self.assertIn("[tool_result] contents", lines)
        self.assertIn("[ground_truth_score] match=1.0", lines)

    def test_content_block_list_flattens(self) -> None:
        payload = {
            "eval": {"task": "t"},
            "samples": [{
                "id": "s2",
                "messages": [
                    {"role": "user",
                     "content": [{"type": "text", "text": "first"},
                                 {"type": "text", "text": "second"}]},
                ],
            }],
        }
        path = _write(json.dumps(payload))
        try:
            lines = inspect_ai_log.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[user] first\nsecond", lines)

    def test_scorer_name_fallback(self) -> None:
        payload = {
            "eval": {"task": "t"},
            "samples": [{
                "id": "s3",
                "messages": [],
                "scores": [{"scorer": "custom", "score": 0.5}],
            }],
        }
        path = _write(json.dumps(payload))
        try:
            lines = inspect_ai_log.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[ground_truth_score] custom=0.5", lines)


class TestCanonicalFixture(unittest.TestCase):
    def test_all_three_samples_extracted(self) -> None:
        path = str(FIXTURES_DIR / "inspect-ai-log.json")
        lines = inspect_ai_log.extract_lines(path)
        joined = "\n".join(lines)
        self.assertIn("[task] security_bench/path_traversal", joined)
        self.assertIn("[model] openai/gpt-4o", joined)
        for sample_id in ("sample-001", "sample-002", "sample-003"):
            self.assertIn(f"[sample_start] {sample_id}", lines)
        self.assertTrue(any(l.startswith("[tool_call] read_file(") for l in lines))
        self.assertTrue(any(l.startswith("[tool_call] edit_file(") for l in lines))
        self.assertTrue(any(l.startswith("[tool_call] append_file(") for l in lines))
        self.assertEqual(
            sum(1 for l in lines if l.startswith("[ground_truth_score] match=")),
            3,
        )


class TestRegistryIntegration(unittest.TestCase):
    def test_inspect_ai_registered(self) -> None:
        self.assertIn("inspect-ai", adapters.list_adapters())
        self.assertTrue(callable(adapters.get_adapter("inspect-ai")))

    def test_detect_adapter_picks_inspect_ai(self) -> None:
        path = str(FIXTURES_DIR / "inspect-ai-log.json")
        self.assertEqual(adapters.detect_adapter(path), "inspect-ai")


if __name__ == "__main__":
    unittest.main()
