#!/usr/bin/env python3
"""Tests for scripts/sandbox_caps_check.py (Z5)."""
from __future__ import annotations

import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import sandbox_caps_check as scc  # noqa: E402


class TestParseCaps(unittest.TestCase):
    def test_empty_returns_empty_list(self) -> None:
        self.assertEqual(scc.parse_caps(""), [])

    def test_single_pair(self) -> None:
        self.assertEqual(scc.parse_caps("bash:read"), [("bash", "read")])

    def test_multiple_pairs(self) -> None:
        out = scc.parse_caps("bash:read,fs:read,net:none")
        self.assertEqual(out, [("bash", "read"), ("fs", "read"), ("net", "none")])

    def test_whitespace_tolerant(self) -> None:
        out = scc.parse_caps(" bash:read , fs:read ")
        self.assertEqual(out, [("bash", "read"), ("fs", "read")])

    def test_invalid_resource_dropped(self) -> None:
        # "gpu:write" isn't in VALID_RESOURCES.
        out = scc.parse_caps("bash:read,gpu:write")
        self.assertEqual(out, [("bash", "read")])

    def test_invalid_mode_dropped(self) -> None:
        out = scc.parse_caps("bash:execute")
        self.assertEqual(out, [])

    def test_malformed_token_dropped(self) -> None:
        out = scc.parse_caps("bash,fs:read")
        self.assertEqual(out, [("fs", "read")])


class TestHasRequiredCaps(unittest.TestCase):
    def test_all_present_returns_empty(self) -> None:
        declared = [("bash", "read"), ("fs", "read")]
        required = [("bash", "read"), ("fs", "read")]
        self.assertEqual(scc.has_required_caps(declared, required), [])

    def test_missing_caps_returned(self) -> None:
        declared = [("bash", "read")]
        required = [("bash", "read"), ("fs", "read")]
        self.assertEqual(
            scc.has_required_caps(declared, required), [("fs", "read")]
        )

    def test_extra_declared_caps_ignored(self) -> None:
        # Declaring more than required is fine.
        declared = [("bash", "read"), ("fs", "read"), ("net", "none")]
        required = [("bash", "read")]
        self.assertEqual(scc.has_required_caps(declared, required), [])


class TestEmitRationale(unittest.TestCase):
    def test_no_declaration(self) -> None:
        line = scc.emit_rationale([], [("bash", "read")])
        self.assertIn("no CLAUDE_SANDBOX_CAPS declared", line)

    def test_missing_caps_listed(self) -> None:
        line = scc.emit_rationale(
            [("bash", "read")],
            [("fs", "read"), ("net", "none")],
        )
        self.assertIn("missing required", line)
        self.assertIn("fs:read", line)
        self.assertIn("net:none", line)

    def test_caps_ok(self) -> None:
        line = scc.emit_rationale(
            [("bash", "read"), ("fs", "read")], [],
        )
        self.assertIn("caps OK", line)
        self.assertIn("bash:read", line)


class TestMainCli(unittest.TestCase):
    def test_caps_ok_returns_zero(self) -> None:
        env = {"CLAUDE_SANDBOX_CAPS": "bash:read,fs:read"}
        out = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
                patch("sys.stdout", out):
            rc = scc.main(["--strict"])
        self.assertEqual(rc, 0)
        self.assertIn("caps OK", out.getvalue())

    def test_missing_caps_strict_returns_one(self) -> None:
        env = {"CLAUDE_SANDBOX_CAPS": "bash:read"}
        out = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
                patch("sys.stdout", out):
            rc = scc.main(["--strict"])
        self.assertEqual(rc, 1)

    def test_missing_caps_non_strict_returns_zero(self) -> None:
        env = {"CLAUDE_SANDBOX_CAPS": "bash:read"}
        out = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
                patch("sys.stdout", out):
            rc = scc.main([])  # no --strict
        self.assertEqual(rc, 0)

    def test_custom_required_caps(self) -> None:
        env = {"CLAUDE_SANDBOX_CAPS": "net:none"}
        out = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
                patch("sys.stdout", out):
            rc = scc.main(["--strict", "--require", "net:none"])
        self.assertEqual(rc, 0)

    def test_unset_env_with_strict_fails(self) -> None:
        out = io.StringIO()
        env = dict(os.environ)
        env.pop("CLAUDE_SANDBOX_CAPS", None)
        with patch.dict(os.environ, env, clear=True), \
                patch("sys.stdout", out):
            rc = scc.main(["--strict"])
        self.assertEqual(rc, 1)
        self.assertIn("no CLAUDE_SANDBOX_CAPS declared", out.getvalue())


class TestEnvVarConstant(unittest.TestCase):
    def test_constant_name(self) -> None:
        self.assertEqual(scc.ENV_VAR, "CLAUDE_SANDBOX_CAPS")


class TestWorkflowDeclaresCaps(unittest.TestCase):
    """Pin the workflow file to the script's expected caps."""

    def test_workflow_sets_caps_env(self) -> None:
        wf = (PROJECT_ROOT / ".github" / "workflows" / "self-score.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("CLAUDE_SANDBOX_CAPS", wf)
        self.assertIn("bash:read", wf)
        self.assertIn("fs:read", wf)


if __name__ == "__main__":
    unittest.main()
