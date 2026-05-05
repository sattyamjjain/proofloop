#!/usr/bin/env python3
"""Wraps scripts/check_readme_release_anchor.py for unittest discover.

Keeps the CHANGELOG-vs-README anchor check exercisable in the local
test suite (``python3 -m unittest discover tests/``) without
requiring contributors to know the script lives in scripts/. Pairs
with the CI job ``README release anchor matches CHANGELOG``.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "check_readme_release_anchor.py"


class TestReadmeReleaseAnchor(unittest.TestCase):
    def test_check_script_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr: {result.stderr}\nstdout: {result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
