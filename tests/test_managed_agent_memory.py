#!/usr/bin/env python3
"""Tests for managed-agents memory stitching in claude_code adapter.

Covers the ``managed-agents-2026-04-01`` beta's shared-memory records
that parallel sub-agents emit into the JSONL transcript.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))

from adapters import claude_code  # noqa: E402
from adapters.claude_code import (  # noqa: E402
    MANAGED_MEMORY_PULL_PREFIX,
    MANAGED_MEMORY_PUSH_PREFIX,
    parse_managed_agent_memory,
)


def _write_jsonl(records: list[dict]) -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    return path


class TestParseManagedAgentMemoryHelper(unittest.TestCase):
    def test_raw_json_pull_gets_tagged(self) -> None:
        record = json.dumps({
            "type": "managed_memory_v1",
            "op": "read",
            "parent_agent_id": "agent-abc",
            "content": "prior findings",
        })
        tagged = parse_managed_agent_memory([record])
        self.assertEqual(len(tagged), 1)
        self.assertTrue(tagged[0].startswith(MANAGED_MEMORY_PULL_PREFIX))
        self.assertIn("prior findings", tagged[0])

    def test_raw_json_push_gets_tagged(self) -> None:
        record = json.dumps({
            "type": "managed_memory_v1",
            "op": "write",
            "parent_agent_id": "agent-abc",
            "content": "new summary",
        })
        tagged = parse_managed_agent_memory([record])
        self.assertTrue(tagged[0].startswith(MANAGED_MEMORY_PUSH_PREFIX))
        self.assertIn("new summary", tagged[0])

    def test_agent_memory_token_triggers_tagging(self) -> None:
        record = json.dumps({
            "event": "agent_memory.push",
            "snippet": "scratch note",
        })
        tagged = parse_managed_agent_memory([record])
        self.assertTrue(tagged[0].startswith(MANAGED_MEMORY_PUSH_PREFIX))
        self.assertIn("scratch note", tagged[0])

    def test_already_tagged_lines_passthrough(self) -> None:
        already = MANAGED_MEMORY_PULL_PREFIX + "already tagged"
        self.assertEqual(parse_managed_agent_memory([already]), [already])

    def test_plain_text_passthrough(self) -> None:
        plain = "assistant says hello"
        self.assertEqual(parse_managed_agent_memory([plain]), [plain])

    def test_non_dict_json_passthrough(self) -> None:
        arr = "[1, 2, 3]"
        self.assertEqual(parse_managed_agent_memory([arr]), [arr])

    def test_unknown_op_defaults_to_pull(self) -> None:
        record = json.dumps({"parent_agent_id": "x", "content": "y"})
        tagged = parse_managed_agent_memory([record])
        self.assertTrue(tagged[0].startswith(MANAGED_MEMORY_PULL_PREFIX))


class TestExtractLinesWiresThrough(unittest.TestCase):
    def test_inline_record_tagged_by_extract_lines(self) -> None:
        path = _write_jsonl([
            {"role": "user", "content": "start"},
            {
                "type": "managed_memory_v1",
                "op": "read",
                "parent_agent_id": "agent-42",
                "content": "shared plan summary",
            },
            {"role": "assistant", "content": "acting on memory"},
            {
                "type": "managed_memory_v1",
                "op": "write",
                "parent_agent_id": "agent-42",
                "content": "progress note",
            },
        ])
        try:
            lines = claude_code.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("start", lines)
        self.assertIn("acting on memory", lines)
        self.assertTrue(any(
            l == MANAGED_MEMORY_PULL_PREFIX + "shared plan summary" for l in lines
        ))
        self.assertTrue(any(
            l == MANAGED_MEMORY_PUSH_PREFIX + "progress note" for l in lines
        ))

    def test_record_without_content_field_still_tagged(self) -> None:
        # No content/text key — the adapter's raw-line fallback emits the
        # whole JSON. The belt-and-braces helper must reclaim the tag.
        path = _write_jsonl([
            {
                "type": "managed_memory_v1",
                "op": "fetch",
                "parent_agent_id": "agent-7",
            },
        ])
        try:
            lines = claude_code.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith(MANAGED_MEMORY_PULL_PREFIX))
        self.assertIn("agent-7", lines[0])

    def test_memory_prefix_does_not_double_up(self) -> None:
        # The adapter's pre-existing [system-memory] tagging must not fire
        # when a record is already identified as managed memory.
        path = _write_jsonl([
            {
                "type": "managed_memory_v1",
                "op": "read",
                "content": "memory_block token coexists here",
            },
        ])
        try:
            lines = claude_code.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith(MANAGED_MEMORY_PULL_PREFIX))
        self.assertNotIn("[system-memory]", lines[0])

    def test_unrelated_memory_block_still_tagged_as_system(self) -> None:
        # Regression: regular Auto Memory preambles must keep their
        # [system-memory] tag and not be reclassified as managed memory.
        path = _write_jsonl([
            {"role": "system", "content": "memory_block begin"},
            {"role": "system", "content": "persisted note"},
            {"role": "user", "content": "new turn"},
        ])
        try:
            lines = claude_code.extract_lines(path)
        finally:
            os.unlink(path)
        has_system_memory = any(
            l.startswith("[system-memory]") for l in lines
        )
        self.assertTrue(has_system_memory)
        self.assertFalse(any(
            l.startswith(MANAGED_MEMORY_PULL_PREFIX) or
            l.startswith(MANAGED_MEMORY_PUSH_PREFIX)
            for l in lines
        ))


if __name__ == "__main__":
    unittest.main()
