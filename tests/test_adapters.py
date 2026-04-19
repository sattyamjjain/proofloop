#!/usr/bin/env python3
"""Tests for transcript adapters."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))

import adapters  # noqa: E402


def _write(content: str, suffix: str = ".jsonl") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


class TestAdapterRegistry(unittest.TestCase):
    def test_list_adapters_includes_ecosystems(self) -> None:
        names = adapters.list_adapters()
        for expected in ("claude-code", "cowork", "codex", "cursor", "continue"):
            self.assertIn(expected, names)

    def test_get_adapter_returns_callable(self) -> None:
        adapter = adapters.get_adapter("claude-code")
        self.assertTrue(callable(adapter))

    def test_get_unknown_adapter_raises(self) -> None:
        with self.assertRaises(KeyError):
            adapters.get_adapter("non-existent-ecosystem")


class TestClaudeCodeAdapter(unittest.TestCase):
    def test_extracts_text_from_jsonl(self) -> None:
        path = _write(
            '{"role":"assistant","content":"hello world"}\n'
            '{"role":"user","content":"more text"}\n'
        )
        try:
            lines = adapters.get_adapter("claude-code")(path)
            self.assertEqual(lines, ["hello world", "more text"])
        finally:
            os.unlink(path)

    def test_extracts_content_blocks(self) -> None:
        path = _write(
            '{"role":"assistant","content":[{"type":"text","text":"block A"},'
            '{"type":"text","text":"block B"}]}\n'
        )
        try:
            lines = adapters.get_adapter("claude-code")(path)
            self.assertEqual(lines, ["block A", "block B"])
        finally:
            os.unlink(path)

    def test_plain_text_passthrough(self) -> None:
        path = _write("no JSON here\njust prose\n", suffix=".txt")
        try:
            lines = adapters.get_adapter("claude-code")(path)
            self.assertEqual(lines, ["no JSON here", "just prose"])
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty(self) -> None:
        lines = adapters.get_adapter("claude-code")("/tmp/verdict-definitely-missing")
        self.assertEqual(lines, [])


class TestOpenAICompatibleAdapter(unittest.TestCase):
    def test_extracts_from_top_level_array(self) -> None:
        payload = [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hey"},
        ]
        path = _write(json.dumps(payload), suffix=".json")
        try:
            lines = adapters.get_adapter("openai-compatible")(path)
            self.assertEqual(lines, ["be helpful", "hi", "hey"])
        finally:
            os.unlink(path)

    def test_extracts_from_messages_object(self) -> None:
        payload = {"messages": [{"role": "user", "content": "q"}]}
        path = _write(json.dumps(payload), suffix=".json")
        try:
            lines = adapters.get_adapter("openai-compatible")(path)
            self.assertEqual(lines, ["q"])
        finally:
            os.unlink(path)

    def test_jsonl_one_message_per_line(self) -> None:
        path = _write(
            '{"role":"user","content":"a"}\n'
            '{"role":"assistant","content":"b"}\n'
        )
        try:
            lines = adapters.get_adapter("openai-compatible")(path)
            self.assertEqual(lines, ["a", "b"])
        finally:
            os.unlink(path)

    def test_tool_calls_flattened(self) -> None:
        payload = [
            {
                "role": "assistant",
                "content": "calling tool",
                "tool_calls": [
                    {
                        "function": {
                            "name": "search",
                            "arguments": '{"q":"verdict"}',
                        }
                    }
                ],
            }
        ]
        path = _write(json.dumps(payload), suffix=".json")
        try:
            lines = adapters.get_adapter("cursor")(path)
            self.assertIn("calling tool", lines)
            self.assertTrue(any(line.startswith("tool_use: search(") for line in lines))
        finally:
            os.unlink(path)

    def test_content_block_list(self) -> None:
        payload = [
            {"role": "assistant", "content": [{"text": "first"}, {"text": "second"}]}
        ]
        path = _write(json.dumps(payload), suffix=".json")
        try:
            lines = adapters.get_adapter("continue")(path)
            self.assertEqual(lines, ["first", "second"])
        finally:
            os.unlink(path)


class TestCodexAdapter(unittest.TestCase):
    def test_markdown_session_plain_lines(self) -> None:
        path = _write("# Codex session\n\nuser: hi\nassistant: hello\n", suffix=".md")
        try:
            lines = adapters.get_adapter("codex")(path)
            self.assertIn("user: hi", lines)
            self.assertIn("assistant: hello", lines)
        finally:
            os.unlink(path)

    def test_json_sidecar_delegates_to_openai(self) -> None:
        payload = [{"role": "user", "content": "x"}]
        path = _write(json.dumps(payload), suffix=".json")
        try:
            lines = adapters.get_adapter("codex")(path)
            self.assertEqual(lines, ["x"])
        finally:
            os.unlink(path)


class TestCoworkAdapter(unittest.TestCase):
    def test_delegates_to_claude_code(self) -> None:
        path = _write('{"content":"routine result"}\n')
        try:
            lines = adapters.get_adapter("cowork")(path)
            self.assertEqual(lines, ["routine result"])
        finally:
            os.unlink(path)


class TestGeminiCliAdapter(unittest.TestCase):
    def test_registered_under_two_names(self) -> None:
        self.assertIn("gemini-cli", adapters.list_adapters())
        self.assertIn("gemini", adapters.list_adapters())
        self.assertIs(
            adapters.get_adapter("gemini"),
            adapters.get_adapter("gemini-cli"),
        )

    def test_parts_shape(self) -> None:
        path = _write(
            '{"role":"user","parts":[{"text":"hello"}]}\n'
            '{"role":"model","parts":[{"text":"hi"},{"text":"again"}]}\n'
        )
        try:
            lines = adapters.get_adapter("gemini-cli")(path)
            self.assertEqual(lines, ["hello", "hi", "again"])
        finally:
            os.unlink(path)

    def test_content_flattened_shape(self) -> None:
        path = _write(
            '{"role":"user","content":"x"}\n'
            '{"role":"model","content":"y"}\n'
        )
        try:
            lines = adapters.get_adapter("gemini-cli")(path)
            self.assertEqual(lines, ["x", "y"])
        finally:
            os.unlink(path)

    def test_function_call_flattened(self) -> None:
        path = _write(
            '{"role":"model","parts":[{"text":"calling search"}],'
            '"functionCall":{"name":"search","args":{"q":"verdict"}}}\n'
        )
        try:
            lines = adapters.get_adapter("gemini-cli")(path)
            self.assertIn("calling search", lines)
            self.assertTrue(any(line.startswith("tool_use: search(") for line in lines))
        finally:
            os.unlink(path)

    def test_function_call_inside_parts(self) -> None:
        path = _write(
            '{"role":"model","parts":['
            '{"text":"invoking tool"},'
            '{"functionCall":{"name":"read_file","args":{"path":"x.py"}}}'
            ']}\n'
        )
        try:
            lines = adapters.get_adapter("gemini-cli")(path)
            self.assertIn("invoking tool", lines)
            self.assertTrue(any(line.startswith("tool_use: read_file(") for line in lines))
        finally:
            os.unlink(path)

    def test_top_level_array(self) -> None:
        payload = (
            '[{"role":"user","parts":[{"text":"q"}]},'
            '{"role":"model","parts":[{"text":"a"}]}]'
        )
        path = _write(payload, suffix=".json")
        try:
            lines = adapters.get_adapter("gemini-cli")(path)
            self.assertEqual(lines, ["q", "a"])
        finally:
            os.unlink(path)

    def test_turns_envelope(self) -> None:
        payload = '{"turns":[{"role":"user","parts":[{"text":"q"}]}]}'
        path = _write(payload, suffix=".json")
        try:
            lines = adapters.get_adapter("gemini-cli")(path)
            self.assertEqual(lines, ["q"])
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(
            adapters.get_adapter("gemini-cli")("/tmp/verdict-gemini-missing"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
