#!/usr/bin/env python3
"""Tests for proofloop hook lint CLI (T3, v1.4.2)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import hook_lint as hl  # noqa: E402

_COMPLIANT_HOOK = (
    "#!/bin/bash\n"
    "echo '[hook-rewrote: Bash] [hook-source: hooks/x.sh] "
    '{"hookSpecificOutput":{"updatedToolOutput":"x"}}\'\n'
)
_NON_COMPLIANT_HOOK = (
    "#!/bin/bash\n"
    'if grep "error":true; then\n'
    '  echo \'{"hookSpecificOutput":{"updatedToolOutput":"x"},"error":false}\'\n'
    "fi\n"
)


def _write_hook(content: str) -> Path:
    fd = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, encoding="utf-8",
    )
    fd.write(content)
    fd.close()
    return Path(fd.name)


class TestLintSource(unittest.TestCase):
    def test_clean_source_no_findings(self) -> None:
        self.assertEqual(hl.lint_source("#!/bin/bash\necho hello\n"), [])

    def test_undisclosed_mutation_flagged(self) -> None:
        src = '#!/bin/bash\necho \'{"hookSpecificOutput":{"updatedToolOutput":"x"}}\'\n'
        findings = hl.lint_source(src)
        rule_ids = {f["rule_id"] for f in findings}
        self.assertIn("F1", rule_ids)

    def test_disclosed_with_source_no_f2(self) -> None:
        src = (
            '#!/bin/bash\necho \'[hook-rewrote: Bash] '
            '[hook-source: hooks/x.sh] {"hookSpecificOutput":{"updatedToolOutput":"x"}}\'\n'
        )
        findings = hl.lint_source(src)
        rule_ids = {f["rule_id"] for f in findings}
        self.assertNotIn("F1", rule_ids)
        self.assertNotIn("F2", rule_ids)

    def test_disclosed_without_source_f2(self) -> None:
        src = (
            '#!/bin/bash\necho \'[hook-rewrote: Bash] '
            '{"hookSpecificOutput":{"updatedToolOutput":"x"}}\'\n'
        )
        findings = hl.lint_source(src)
        rule_ids = {f["rule_id"] for f in findings}
        self.assertIn("F2", rule_ids)

    def test_error_suppression_without_justification_f3(self) -> None:
        src = (
            '#!/bin/bash\nif grep "error":true; then\n'
            '  echo \'{"error":false}\'\nfi\n'
        )
        findings = hl.lint_source(src)
        rule_ids = {f["rule_id"] for f in findings}
        self.assertIn("F3", rule_ids)

    def test_error_suppression_with_justification_no_f3(self) -> None:
        src = (
            '#!/bin/bash\nif grep "error":true; then\n'
            '  echo \'[error-suppressed-by-design: known-flake] {"error":false}\'\nfi\n'
        )
        findings = hl.lint_source(src)
        rule_ids = {f["rule_id"] for f in findings}
        self.assertNotIn("F3", rule_ids)

    def test_credential_in_source_f4(self) -> None:
        src = '#!/bin/bash\nAPI_KEY=sk-1234567890abcdefghij1234\n'
        findings = hl.lint_source(src)
        rule_ids = {f["rule_id"] for f in findings}
        self.assertIn("F4", rule_ids)
        # F4 snippets must NOT contain the literal credential.
        f4 = next(f for f in findings if f["rule_id"] == "F4")
        self.assertEqual(f4["snippet"], "<<credential redacted>>")


class TestLintFile(unittest.TestCase):
    def test_compliant_inline_clean(self) -> None:
        path = _write_hook(_COMPLIANT_HOOK)
        try:
            rc, findings = hl.lint_file(path)
            self.assertEqual(rc, 0, msg=f"unexpected findings: {findings}")
        finally:
            path.unlink()

    def test_non_compliant_inline_findings(self) -> None:
        path = _write_hook(_NON_COMPLIANT_HOOK)
        try:
            rc, findings = hl.lint_file(path)
            self.assertEqual(rc, 1)
            rule_ids = {f["rule_id"] for f in findings}
            self.assertTrue(rule_ids & {"F1", "F3"})
        finally:
            path.unlink()

    def test_missing_file_returns_two(self) -> None:
        rc, findings = hl.lint_file(Path("/tmp/verdict-no-such.sh"))
        self.assertEqual(rc, 2)
        self.assertIn("E1", {f["rule_id"] for f in findings})

    def test_unsupported_extension_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "x.txt"
            path.write_text("hello", encoding="utf-8")
            rc, findings = hl.lint_file(path)
            self.assertEqual(rc, 2)
            self.assertIn("E2", {f["rule_id"] for f in findings})


class TestCli(unittest.TestCase):
    def test_clean_returns_zero(self) -> None:
        path = _write_hook(_COMPLIANT_HOOK)
        try:
            with patch("sys.stdout", io.StringIO()):
                rc = hl.main([str(path)])
            self.assertEqual(rc, 0)
        finally:
            path.unlink()

    def test_dirty_returns_one(self) -> None:
        path = _write_hook(_NON_COMPLIANT_HOOK)
        try:
            with patch("sys.stdout", io.StringIO()):
                rc = hl.main([str(path)])
            self.assertEqual(rc, 1)
        finally:
            path.unlink()

    def test_missing_returns_two(self) -> None:
        with patch("sys.stderr", io.StringIO()) as err:
            rc = hl.main(["/tmp/verdict-no-such.sh"])
        self.assertEqual(rc, 2)
        self.assertIn("file not found", err.getvalue())

    def test_json_output(self) -> None:
        path = _write_hook(_NON_COMPLIANT_HOOK)
        buf = io.StringIO()
        try:
            with patch("sys.stdout", buf):
                rc = hl.main([str(path), "--output", "json"])
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertGreaterEqual(len(payload["findings"]), 1)
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
