#!/usr/bin/env python3
"""End-to-end tests for the hook shell scripts.

Every hook reads JSON from stdin and emits either JSON on stdout or
nothing (graceful exit 0). These tests invoke the scripts via
subprocess with synthetic payloads to pin the contract that Verdict's
auto-mode relies on.

We deliberately choose skills that are in neither the `always` nor the
`never` allowlist in the shipped ``judge-config.json``. That routes
the hook through the "manual-only" branch, which exits 0 before
touching ``skills/judge/scores/`` — so these tests produce no side
effects on the repo while still exercising the real dispatch logic.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"
CONFIG_PATH = PROJECT_ROOT / "judge-config.json"

# Skills picked to avoid the `always` allowlist in judge-config.json
# so the hooks exit before running score.py.
MANUAL_ONLY_SKILL = "__verdict-hook-test-skill__"
NEVER_SKILL = "commit"           # on the never list → should suppress
ALWAYS_SKILL = "code-review"     # on the always list → should dispatch


def _have_deps() -> bool:
    """Skip hook tests when jq/bc aren't on PATH (hook scripts exit 0)."""
    return all(shutil.which(cmd) for cmd in ("jq", "bc", "python3", "bash"))


def _run_hook(script: Path, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(script)],
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        cwd=str(PROJECT_ROOT),
    )


class TestCommonSh(unittest.TestCase):
    """Pure-bash helpers in hooks/common.sh."""

    def _source(self, fn_call: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", "-c", f"source {HOOKS_DIR}/common.sh && {fn_call}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
            cwd=str(PROJECT_ROOT),
        )

    @unittest.skipUnless(_have_deps(), "jq/bc not available")
    def test_should_auto_judge_always(self) -> None:
        out = self._source(f'should_auto_judge "{ALWAYS_SKILL}" "{CONFIG_PATH}"')
        self.assertEqual(out.stdout.decode().strip(), "true")

    @unittest.skipUnless(_have_deps(), "jq/bc not available")
    def test_should_auto_judge_never(self) -> None:
        out = self._source(f'should_auto_judge "{NEVER_SKILL}" "{CONFIG_PATH}"')
        self.assertEqual(out.stdout.decode().strip(), "false")

    @unittest.skipUnless(_have_deps(), "jq/bc not available")
    def test_should_auto_judge_manual_only(self) -> None:
        out = self._source(f'should_auto_judge "{MANUAL_ONLY_SKILL}" "{CONFIG_PATH}"')
        self.assertEqual(out.stdout.decode().strip(), "false")

    @unittest.skipUnless(_have_deps(), "jq/bc not available")
    def test_get_threshold_returns_float(self) -> None:
        # jq strips trailing zeros from whole numbers, so "5.0" becomes "5".
        # Accept either representation.
        out = self._source(f'get_threshold "{CONFIG_PATH}"')
        value = out.stdout.decode().strip()
        self.assertIn(value, {"5", "5.0"})
        self.assertEqual(float(value), 5.0)

    @unittest.skipUnless(_have_deps(), "jq/bc not available")
    def test_detect_skill_from_transcript_pattern_1(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("User invoked skills/code-review/SKILL.md today.\n")
            path = f.name
        try:
            out = self._source(f'detect_skill_from_transcript "{path}"')
            self.assertEqual(out.stdout.decode().strip(), "code-review")
        finally:
            os.unlink(path)

    @unittest.skipUnless(_have_deps(), "jq/bc not available")
    def test_detect_skill_falls_through_to_empty(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("plain prose, no skill markers at all\n")
            path = f.name
        try:
            out = self._source(f'detect_skill_from_transcript "{path}"')
            self.assertEqual(out.stdout.decode().strip(), "")
        finally:
            os.unlink(path)


@unittest.skipUnless(_have_deps(), "jq/bc not available")
class TestStopHook(unittest.TestCase):
    """hooks/judge-on-stop.sh — fires on Stop event."""

    script = HOOKS_DIR / "judge-on-stop.sh"

    def test_empty_payload_exits_cleanly(self) -> None:
        result = _run_hook(self.script, {})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), b"")

    def test_missing_transcript_path_exits_0(self) -> None:
        result = _run_hook(self.script, {"session_id": "abc"})
        self.assertEqual(result.returncode, 0)

    def test_nonexistent_transcript_exits_0(self) -> None:
        result = _run_hook(self.script, {
            "transcript_path": "/tmp/verdict-nonexistent-transcript-xyz.jsonl",
        })
        self.assertEqual(result.returncode, 0)

    def test_never_skill_short_circuits(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(f"/{NEVER_SKILL}\nsome output\n")
            path = f.name
        try:
            result = _run_hook(self.script, {"transcript_path": path})
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), b"")
        finally:
            os.unlink(path)

    def test_manual_only_skill_short_circuits(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(f"/{MANUAL_ONLY_SKILL}\noutput\n")
            path = f.name
        try:
            result = _run_hook(self.script, {"transcript_path": path})
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), b"")
        finally:
            os.unlink(path)


@unittest.skipUnless(_have_deps(), "jq/bc not available")
class TestSubagentStopHook(unittest.TestCase):
    """hooks/judge-on-subagent-stop.sh — fires on SubagentStop."""

    script = HOOKS_DIR / "judge-on-subagent-stop.sh"

    def test_missing_agent_fields_exits_0(self) -> None:
        result = _run_hook(self.script, {"session_id": "abc"})
        self.assertEqual(result.returncode, 0)

    def test_empty_agent_type_exits_0(self) -> None:
        result = _run_hook(self.script, {
            "agent_type": "",
            "agent_transcript_path": "/tmp/whatever.jsonl",
        })
        self.assertEqual(result.returncode, 0)

    def test_empty_transcript_path_exits_0(self) -> None:
        result = _run_hook(self.script, {
            "agent_type": "Explore",
            "agent_transcript_path": "",
        })
        self.assertEqual(result.returncode, 0)

    def test_manual_only_agent_type_short_circuits(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("some subagent output\n")
            path = f.name
        try:
            result = _run_hook(self.script, {
                "agent_type": MANUAL_ONLY_SKILL,
                "agent_transcript_path": path,
            })
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), b"")
        finally:
            os.unlink(path)


@unittest.skipUnless(_have_deps(), "jq/bc not available")
class TestStopFailureHook(unittest.TestCase):
    """hooks/judge-on-stop-failure.sh — never scores, always exits 0."""

    script = HOOKS_DIR / "judge-on-stop-failure.sh"

    def test_exits_0_with_breadcrumb(self) -> None:
        result = _run_hook(self.script, {
            "session_id": "sess-123",
            "matcher": "rate_limit",
        })
        self.assertEqual(result.returncode, 0)
        # Breadcrumb on stderr, nothing on stdout
        self.assertEqual(result.stdout.strip(), b"")
        self.assertIn(b"skipping auto-judge", result.stderr)
        self.assertIn(b"sess-123", result.stderr)
        self.assertIn(b"rate_limit", result.stderr)

    def test_unknown_matcher_defaults_to_unknown(self) -> None:
        result = _run_hook(self.script, {"session_id": "s1"})
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"unknown", result.stderr)


if __name__ == "__main__":
    unittest.main()
