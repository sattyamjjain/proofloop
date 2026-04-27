#!/usr/bin/env python3
"""Tests for browser_harness adapter (R2)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
import adapters  # noqa: E402
from adapters import browser_harness as bh  # noqa: E402


def _write(content: str, suffix: str = ".json") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


class TestDetect(unittest.TestCase):
    def test_explicit_token(self) -> None:
        self.assertTrue(bh.detect(b'{"creator":{"name":"browser-harness"}}'))

    def test_har_with_entries(self) -> None:
        self.assertTrue(bh.detect(b'{"har_version":"1.2","entries":[]}'))

    def test_unrelated_json(self) -> None:
        self.assertFalse(bh.detect(b'{"messages":[]}'))


class TestDetectionScore(unittest.TestCase):
    def test_explicit_token_high_score(self) -> None:
        path = _write('{"creator":{"name":"browser-harness"},"session":{}}')
        try:
            self.assertGreaterEqual(bh.detection_score(path), 0.85)
        finally:
            os.unlink(path)

    def test_har_only_lower(self) -> None:
        path = _write('{"har_version":"1.2","entries":[]}')
        try:
            score = bh.detection_score(path)
            self.assertGreater(score, 0.0)
            self.assertLess(score, 0.85)
        finally:
            os.unlink(path)

    def test_zero_when_unrelated(self) -> None:
        path = _write('{"messages":[]}')
        try:
            self.assertEqual(bh.detection_score(path), 0.0)
        finally:
            os.unlink(path)


class TestExtractLines(unittest.TestCase):
    def test_missing_file_empty(self) -> None:
        self.assertEqual(bh.extract_lines("/tmp/verdict-bh-missing"), [])

    def test_bad_json_empty(self) -> None:
        path = _write("not-json")
        try:
            self.assertEqual(bh.extract_lines(path), [])
        finally:
            os.unlink(path)

    def test_navigate_event(self) -> None:
        payload = {"session": {"events": [
            {"type": "navigate", "method": "GET", "url": "https://example.com", "status": 200}
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = bh.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[navigate] GET https://example.com -> 200", lines)

    def test_click_event(self) -> None:
        payload = {"session": {"events": [
            {"type": "click", "selector": "button[role='submit']"}
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = bh.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[click] button[role='submit']", lines)

    def test_fill_redacts_password(self) -> None:
        payload = {"session": {"events": [
            {"type": "fill", "selector": "input[name='password']", "value": "hunter2"}
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = bh.extract_lines(path)
        finally:
            os.unlink(path)
        joined = "\n".join(lines)
        self.assertIn("[REDACTED]", joined)
        self.assertNotIn("hunter2", joined)

    def test_fill_passes_non_credential(self) -> None:
        payload = {"session": {"events": [
            {"type": "fill", "selector": "input[name='username']", "value": "alice"}
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = bh.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[fill] input[name='username']=alice", lines)

    def test_assertion_event(self) -> None:
        payload = {"session": {"events": [
            {"type": "assertion", "selector": ".status", "expected": "success"}
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = bh.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[assertion] .status :: success", lines)

    def test_screenshot_event(self) -> None:
        payload = {"session": {"events": [
            {"type": "screenshot", "path": "shots/01.png"}
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = bh.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[screenshot] shots/01.png", lines)

    def test_har_entries_become_navigate(self) -> None:
        payload = {"log": {"entries": [
            {
                "request": {"method": "GET", "url": "https://example.com/a"},
                "response": {"status": 200},
            }
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = bh.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[navigate] GET https://example.com/a -> 200", lines)


class TestCanonicalFixture(unittest.TestCase):
    def test_extracts_every_block(self) -> None:
        path = str(FIXTURES_DIR / "browser-harness-trace.json")
        lines = bh.extract_lines(path)
        joined = "\n".join(lines)
        self.assertIn("[model] claude-sonnet-4-6", lines)
        self.assertTrue(any(l.startswith("[task] log into the dashboard") for l in lines))
        # Every navigate, click, fill, assertion, screenshot represented.
        self.assertEqual(sum(1 for l in lines if l.startswith("[navigate]")), 2)
        self.assertEqual(sum(1 for l in lines if l.startswith("[click]")), 3)
        self.assertEqual(sum(1 for l in lines if l.startswith("[fill]")), 2)
        self.assertEqual(sum(1 for l in lines if l.startswith("[screenshot]")), 4)
        self.assertEqual(sum(1 for l in lines if l.startswith("[assertion]")), 1)
        # Critical: the password value MUST NOT appear in the lines.
        self.assertNotIn("REAL-PASSWORD-DO-NOT-LOG", joined)
        self.assertIn("[REDACTED]", joined)


class TestRegistryIntegration(unittest.TestCase):
    def test_registered_under_two_names(self) -> None:
        self.assertIn("browser-harness", adapters.list_adapters())
        self.assertIn("browser", adapters.list_adapters())
        self.assertIs(
            adapters.get_adapter("browser"),
            adapters.get_adapter("browser-harness"),
        )

    def test_detect_picks_browser_harness(self) -> None:
        path = str(FIXTURES_DIR / "browser-harness-trace.json")
        self.assertEqual(adapters.detect_adapter(path), "browser-harness")


class TestRubricFiles(unittest.TestCase):
    def test_markdown_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "browser-agent.md").is_file())

    def test_weights_sidecar_exists(self) -> None:
        self.assertTrue((RUBRICS_DIR / "browser-agent.weights.json").is_file())

    def test_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "browser-agent.weights.json").read_text(encoding="utf-8")
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
