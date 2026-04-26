#!/usr/bin/env python3
"""Tests for skills/judge/adapters/gemini_deep_research.py."""
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
from adapters import gemini_deep_research as gdr  # noqa: E402


def _write(content: str, suffix: str = ".json") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


class TestDetect(unittest.TestCase):
    def test_explicit_flag(self) -> None:
        self.assertTrue(gdr.detect(b'{"deep_research_mode": true,"x":1}'))

    def test_compact_explicit_flag(self) -> None:
        self.assertTrue(gdr.detect(b'{"deep_research_mode":true}'))

    def test_research_plan_alone(self) -> None:
        self.assertTrue(gdr.detect(b'{"research_plan":[]}'))

    def test_unrelated_json(self) -> None:
        self.assertFalse(gdr.detect(b'{"messages":[]}'))

    def test_empty_bytes(self) -> None:
        self.assertFalse(gdr.detect(b""))


class TestDetectionScore(unittest.TestCase):
    def test_explicit_flag_high_score(self) -> None:
        path = _write('{"deep_research_mode": true,"research_plan":[]}')
        try:
            self.assertGreaterEqual(gdr.detection_score(path), 0.9)
        finally:
            os.unlink(path)

    def test_structural_only_lower(self) -> None:
        path = _write('{"research_plan":[],"verifier_notes":[]}')
        try:
            score = gdr.detection_score(path)
            self.assertLess(score, 0.9)
            self.assertGreater(score, 0.0)
        finally:
            os.unlink(path)

    def test_zero_when_unrelated(self) -> None:
        path = _write('{"messages":[]}')
        try:
            self.assertEqual(gdr.detection_score(path), 0.0)
        finally:
            os.unlink(path)


class TestExtractLines(unittest.TestCase):
    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(gdr.extract_lines("/tmp/verdict-gdr-missing"), [])

    def test_bad_json_returns_empty(self) -> None:
        path = _write("not-json")
        try:
            self.assertEqual(gdr.extract_lines(path), [])
        finally:
            os.unlink(path)

    def test_plan_steps_emitted(self) -> None:
        payload = {
            "deep_research_mode": True,
            "research_plan": [
                {"step": 1, "query": "first"},
                {"step": 2, "query": "second"},
            ],
        }
        path = _write(json.dumps(payload))
        try:
            lines = gdr.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[plan_step] 1: first", lines)
        self.assertIn("[plan_step] 2: second", lines)

    def test_citations_carry_url_and_retrieved_at(self) -> None:
        payload = {
            "deep_research_mode": True,
            "citations": [
                {"url": "https://example.com/a", "retrieved_at": "2026-04-26T00:00:00Z"},
                {"url": "https://example.com/b"},
            ],
        }
        path = _write(json.dumps(payload))
        try:
            lines = gdr.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn(
            "[citation:https://example.com/a] retrieved_at=2026-04-26T00:00:00Z",
            lines,
        )
        # Missing retrieved_at degrades gracefully.
        self.assertIn("[citation:https://example.com/b]", lines)

    def test_verifier_notes_emitted(self) -> None:
        payload = {
            "deep_research_mode": True,
            "verifier_notes": [
                {"text": "claim X verified"},
                "raw note",
            ],
        }
        path = _write(json.dumps(payload))
        try:
            lines = gdr.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[verifier_note] claim X verified", lines)
        self.assertIn("[verifier_note] raw note", lines)

    def test_assistant_synthesis_string(self) -> None:
        payload = {
            "deep_research_mode": True,
            "assistant_synthesis": "synthesised answer",
        }
        path = _write(json.dumps(payload))
        try:
            lines = gdr.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[assistant] synthesised answer", lines)

    def test_assistant_synthesis_block_list(self) -> None:
        payload = {
            "deep_research_mode": True,
            "assistant_synthesis": [
                {"text": "section A"},
                {"text": "section B"},
            ],
        }
        path = _write(json.dumps(payload))
        try:
            lines = gdr.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[assistant] section A", lines)
        self.assertIn("[assistant] section B", lines)

    def test_emit_order(self) -> None:
        payload = {
            "deep_research_mode": True,
            "research_plan": [{"step": 1, "query": "q"}],
            "citations": [{"url": "https://example.com/a"}],
            "verifier_notes": [{"text": "v"}],
            "assistant_synthesis": "s",
        }
        path = _write(json.dumps(payload))
        try:
            lines = gdr.extract_lines(path)
        finally:
            os.unlink(path)
        plan_idx = next(i for i, l in enumerate(lines) if l.startswith("[plan_step]"))
        cite_idx = next(i for i, l in enumerate(lines) if l.startswith("[citation:"))
        ver_idx = next(i for i, l in enumerate(lines) if l.startswith("[verifier_note]"))
        ass_idx = next(i for i, l in enumerate(lines) if l.startswith("[assistant]"))
        self.assertLess(plan_idx, cite_idx)
        self.assertLess(cite_idx, ver_idx)
        self.assertLess(ver_idx, ass_idx)


class TestCanonicalFixture(unittest.TestCase):
    def test_extracts_every_block(self) -> None:
        path = str(FIXTURES_DIR / "gemini-deep-research.json")
        lines = gdr.extract_lines(path)
        joined = "\n".join(lines)
        self.assertIn("[model] gemini-3-1-pro", lines)
        self.assertIn("[topic] What is the FDA approval status of GLP-1 agonists for non-diabetic obesity?", lines)
        self.assertEqual(sum(1 for l in lines if l.startswith("[plan_step]")), 3)
        self.assertEqual(sum(1 for l in lines if l.startswith("[citation:")), 5)
        self.assertEqual(sum(1 for l in lines if l.startswith("[verifier_note]")), 2)
        self.assertEqual(sum(1 for l in lines if l.startswith("[assistant]")), 1)
        self.assertIn("FDA-approved", joined)


class TestRegistryIntegration(unittest.TestCase):
    def test_registered_under_two_names(self) -> None:
        self.assertIn("gemini-deep-research", adapters.list_adapters())
        self.assertIn("gemini-deep", adapters.list_adapters())
        self.assertIs(
            adapters.get_adapter("gemini-deep"),
            adapters.get_adapter("gemini-deep-research"),
        )

    def test_detect_picks_deep_research(self) -> None:
        path = str(FIXTURES_DIR / "gemini-deep-research.json")
        self.assertEqual(adapters.detect_adapter(path), "gemini-deep-research")


if __name__ == "__main__":
    unittest.main()
