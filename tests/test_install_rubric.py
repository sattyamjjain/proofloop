#!/usr/bin/env python3
"""Tests for scripts/install_rubric.py.

Network calls are stubbed via urllib.request.urlopen monkey-patching so
tests run offline.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import install_rubric  # noqa: E402


VALID_RUBRIC = """# Custom Rubric

### Correctness
Score high when correct.

### Completeness
Score high when all requirements are addressed.

### Adherence
Score high when guidance is followed.
"""


class _MockResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestValidateRubricText(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertIsNone(install_rubric._validate_rubric_text(VALID_RUBRIC))

    def test_missing_correctness(self) -> None:
        bad = VALID_RUBRIC.replace("### Correctness", "### Foo")
        err = install_rubric._validate_rubric_text(bad)
        self.assertIn("Correctness", err)


class TestDeriveName(unittest.TestCase):
    def test_from_url(self) -> None:
        self.assertEqual(
            install_rubric._derive_name(
                "https://example.com/path/code-review.md", None,
            ),
            "code-review",
        )

    def test_override(self) -> None:
        self.assertEqual(
            install_rubric._derive_name("https://example.com/a.md", "b"),
            "b",
        )


class TestInstall(unittest.TestCase):
    def test_installs_valid_rubric(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rubric_dir = Path(tmp)

            responses = {
                "https://example.com/custom.md": _MockResponse(200, VALID_RUBRIC.encode()),
                "https://example.com/custom.weights.json": _MockResponse(404, b""),
            }

            def fake_urlopen(req, timeout=10):
                url = req.full_url if hasattr(req, "full_url") else str(req)
                response = responses.get(url)
                if response is None or response.status != 200:
                    raise urllib.request.HTTPError(url, 404, "not found", {}, io.BytesIO())
                return response

            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                code = install_rubric.install_rubric(
                    "https://example.com/custom.md", rubric_dir,
                )
            self.assertEqual(code, 0)
            self.assertTrue((rubric_dir / "custom.md").is_file())

    def test_rejects_invalid_rubric(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rubric_dir = Path(tmp)

            def fake_urlopen(req, timeout=10):
                return _MockResponse(200, b"# Nothing here")

            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                code = install_rubric.install_rubric(
                    "https://example.com/x.md", rubric_dir,
                )
            self.assertEqual(code, 1)
            self.assertFalse((rubric_dir / "x.md").is_file())

    def test_installs_weights_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rubric_dir = Path(tmp)
            weights = {
                "correctness": 0.2, "completeness": 0.15, "adherence": 0.1,
                "actionability": 0.1, "efficiency": 0.05, "safety": 0.35,
                "consistency": 0.05,
            }

            responses = {
                "https://example.com/custom.md": _MockResponse(200, VALID_RUBRIC.encode()),
                "https://example.com/custom.weights.json": _MockResponse(200, json.dumps(weights).encode()),
            }

            def fake_urlopen(req, timeout=10):
                url = req.full_url if hasattr(req, "full_url") else str(req)
                response = responses.get(url)
                if response is None:
                    raise urllib.request.HTTPError(url, 404, "not found", {}, io.BytesIO())
                return response

            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                code = install_rubric.install_rubric(
                    "https://example.com/custom.md", rubric_dir,
                )
            self.assertEqual(code, 0)
            self.assertTrue((rubric_dir / "custom.weights.json").is_file())


if __name__ == "__main__":
    unittest.main()
