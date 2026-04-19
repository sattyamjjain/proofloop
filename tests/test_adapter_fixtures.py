#!/usr/bin/env python3
"""Pin every adapter against its canonical fixture.

When an ecosystem changes its transcript format, these tests lock in
the new shape alongside the adapter update, so future format drift
can't silently break scoring.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
import adapters  # noqa: E402


class TestClaudeCodeFixture(unittest.TestCase):
    def test_extracts_all_turns(self) -> None:
        path = str(FIXTURES_DIR / "claude-code.jsonl")
        lines = adapters.get_adapter("claude-code")(path)
        self.assertGreaterEqual(len(lines), 4)
        joined = "\n".join(lines)
        self.assertIn("middleware.py", joined)
        self.assertIn("Block one", joined)
        self.assertIn("Block two", joined)


class TestCoworkFixture(unittest.TestCase):
    def test_routine_id_preserved_in_output(self) -> None:
        path = str(FIXTURES_DIR / "cowork.jsonl")
        lines = adapters.get_adapter("cowork")(path)
        joined = "\n".join(lines)
        self.assertIn("routine_id", joined)
        self.assertIn("merged PRs", joined)


class TestOpenAICompatibleArray(unittest.TestCase):
    def test_extracts_every_content(self) -> None:
        path = str(FIXTURES_DIR / "openai-compatible-array.json")
        lines = adapters.get_adapter("openai-compatible")(path)
        self.assertEqual(len(lines), 3)
        self.assertIn("senior engineer", "\n".join(lines))


class TestOpenAICompatibleMessages(unittest.TestCase):
    def test_envelope_parsed(self) -> None:
        path = str(FIXTURES_DIR / "openai-compatible-messages.json")
        lines = adapters.get_adapter("openai-compatible")(path)
        self.assertEqual(len(lines), 2)
        self.assertIn("user_id column", "\n".join(lines))


class TestOpenAICompatibleJsonl(unittest.TestCase):
    def test_one_message_per_line(self) -> None:
        path = str(FIXTURES_DIR / "openai-compatible-jsonl.jsonl")
        lines = adapters.get_adapter("openai-compatible")(path)
        self.assertEqual(len(lines), 3)
        self.assertIn("timezone mismatch", "\n".join(lines))


class TestOpenAICompatibleTools(unittest.TestCase):
    def test_tool_calls_flattened(self) -> None:
        path = str(FIXTURES_DIR / "openai-compatible-tools.json")
        lines = adapters.get_adapter("cursor")(path)
        joined = "\n".join(lines)
        self.assertIn("Fetching the release list.", joined)
        self.assertTrue(any(line.startswith("tool_use: github_api(") for line in lines))


class TestCodexMarkdownFixture(unittest.TestCase):
    def test_markdown_lines_extracted(self) -> None:
        path = str(FIXTURES_DIR / "codex.md")
        lines = adapters.get_adapter("codex")(path)
        joined = "\n".join(lines)
        self.assertIn("fetchUser", joined)
        self.assertIn("Tests green", joined)


class TestCodexSidecarFixture(unittest.TestCase):
    def test_sidecar_delegates_to_openai(self) -> None:
        path = str(FIXTURES_DIR / "codex-sidecar.json")
        lines = adapters.get_adapter("codex")(path)
        joined = "\n".join(lines)
        self.assertIn("Benchmark completed", joined)


class TestGeminiCliFixture(unittest.TestCase):
    def test_extracts_every_part(self) -> None:
        path = str(FIXTURES_DIR / "gemini-cli.jsonl")
        lines = adapters.get_adapter("gemini-cli")(path)
        joined = "\n".join(lines)
        self.assertIn("middleware.py", joined)
        self.assertIn("audience validation", joined)
        self.assertTrue(any(line.startswith("tool_use: read_file(") for line in lines))


if __name__ == "__main__":
    unittest.main()
