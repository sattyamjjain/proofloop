#!/usr/bin/env python3
"""Tests for the Terminal-Bench trajectory adapter and rubric."""
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
from adapters import terminal_bench  # noqa: E402


def _write(content: str, suffix: str = ".json") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


class TestDetect(unittest.TestCase):
    def test_detects_steps_plus_exit_code(self) -> None:
        head = b'{"steps":[{"command":"ls","exit_code":0}]}'
        self.assertTrue(terminal_bench.detect(head))

    def test_detects_explicit_terminal_bench_marker(self) -> None:
        head = b'{"terminal_bench":true,"steps":[]}'
        self.assertTrue(terminal_bench.detect(head))

    def test_rejects_steps_without_exit_code(self) -> None:
        head = b'{"steps":[{"role":"user"}]}'
        self.assertFalse(terminal_bench.detect(head))

    def test_empty_bytes(self) -> None:
        self.assertFalse(terminal_bench.detect(b""))

    def test_looks_like_on_file(self) -> None:
        path = _write('{"steps":[{"command":"ls","exit_code":0}]}')
        try:
            self.assertTrue(terminal_bench.looks_like_terminal_bench(path))
        finally:
            os.unlink(path)


class TestExtractLines(unittest.TestCase):
    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(
            terminal_bench.extract_lines("/tmp/verdict-terminal-bench-missing"),
            [],
        )

    def test_bad_json_returns_empty(self) -> None:
        path = _write("not-json")
        try:
            self.assertEqual(terminal_bench.extract_lines(path), [])
        finally:
            os.unlink(path)

    def test_task_and_model_header(self) -> None:
        payload = {"task": "x", "model": "claude-opus-4-7", "steps": []}
        path = _write(json.dumps(payload))
        try:
            lines = terminal_bench.extract_lines(path)
            self.assertIn("[task] x", lines)
            self.assertIn("[model] claude-opus-4-7", lines)
        finally:
            os.unlink(path)

    def test_step_emits_shell_cmd_stdout_stderr(self) -> None:
        payload = {"steps": [
            {
                "command": "ls /tmp",
                "stdout": "foo\nbar\n",
                "stderr": "",
                "exit_code": 0,
            }
        ]}
        path = _write(json.dumps(payload))
        try:
            lines = terminal_bench.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[shell_cmd] ls /tmp", lines)
        self.assertIn("[stdout] foo\nbar\n", lines)
        self.assertIn("[stderr:exit=0]", lines)

    def test_nonzero_exit_code_in_prefix(self) -> None:
        payload = {"steps": [
            {
                "command": "false",
                "stdout": "",
                "stderr": "command failed\n",
                "exit_code": 1,
            }
        ]}
        path = _write(json.dumps(payload))
        try:
            lines = terminal_bench.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertTrue(any(
            l == "[stderr:exit=1] command failed\n" for l in lines
        ))

    def test_missing_exit_code_falls_back_to_question(self) -> None:
        payload = {"steps": [
            {"command": "echo hi", "stdout": "hi\n", "stderr": ""}
        ]}
        path = _write(json.dumps(payload))
        try:
            lines = terminal_bench.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[stderr:exit=?]", lines)

    def test_exit_code_alternate_keys(self) -> None:
        payload = {"steps": [
            {"command": "ls", "stdout": "", "stderr": "", "exitCode": 0}
        ]}
        path = _write(json.dumps(payload))
        try:
            lines = terminal_bench.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[stderr:exit=0]", lines)

    def test_nested_trajectory_envelope(self) -> None:
        payload = {"trajectory": {"steps": [
            {"command": "ls", "stdout": "", "stderr": "", "exit_code": 0}
        ]}}
        path = _write(json.dumps(payload))
        try:
            lines = terminal_bench.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[shell_cmd] ls", lines)

    def test_top_level_array_shape(self) -> None:
        payload = [
            {"command": "whoami", "stdout": "root\n", "stderr": "", "exit_code": 0}
        ]
        path = _write(json.dumps(payload))
        try:
            lines = terminal_bench.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertIn("[shell_cmd] whoami", lines)


class TestCanonicalFixture(unittest.TestCase):
    def test_extracts_every_step(self) -> None:
        path = str(FIXTURES_DIR / "terminal-bench-trajectory.json")
        lines = terminal_bench.extract_lines(path)
        self.assertIn("[task] terminal_bench/tar_extract_and_grep", lines)
        self.assertIn("[model] claude-sonnet-4-6", lines)
        self.assertTrue(any(l.startswith("[shell_cmd] tar -xzf") for l in lines))
        self.assertTrue(any(l.startswith("[shell_cmd] grep -R") for l in lines))
        self.assertTrue(any(l == "[stdout] 42\n" for l in lines))
        # Every step carries an exit-code turn.
        self.assertEqual(
            sum(1 for l in lines if l.startswith("[stderr:exit=0]")),
            3,
        )


class TestRegistry(unittest.TestCase):
    def test_registered_under_two_names(self) -> None:
        self.assertIn("terminal-bench", adapters.list_adapters())
        self.assertIn("terminal", adapters.list_adapters())
        self.assertIs(
            adapters.get_adapter("terminal"),
            adapters.get_adapter("terminal-bench"),
        )

    def test_detect_picks_terminal_bench(self) -> None:
        path = str(FIXTURES_DIR / "terminal-bench-trajectory.json")
        self.assertEqual(adapters.detect_adapter(path), "terminal-bench")


class TestRubricFiles(unittest.TestCase):
    def test_rubric_markdown_exists(self) -> None:
        path = RUBRICS_DIR / "terminal-bench.md"
        self.assertTrue(path.is_file())

    def test_rubric_has_source_signal(self) -> None:
        text = (RUBRICS_DIR / "terminal-bench.md").read_text(encoding="utf-8")
        self.assertIn("source_signal:", text)
        self.assertIn("terminal-bench", text)

    def test_rubric_mentions_each_concern(self) -> None:
        text = (RUBRICS_DIR / "terminal-bench.md").read_text(encoding="utf-8").lower()
        for concern in (
            "command-safety",
            "exit-code-handling",
            "idempotence",
            "filesystem-cleanliness",
            "step-count-efficiency",
            "secret-leakage",
        ):
            self.assertIn(concern, text)

    def test_weights_sum_to_one(self) -> None:
        weights = json.loads(
            (RUBRICS_DIR / "terminal-bench.weights.json").read_text(encoding="utf-8")
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
