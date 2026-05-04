#!/usr/bin/env python3
"""Tests for Claude Code v2.1.120 marketplace.json schema additions.

The 2026-04-28 release added ``$schema``, ``version``, and
``description`` at the top level of ``marketplace.json`` plus
``$schema`` on plugin entries. ``scripts/validate_marketplace.py``
now type-checks these when present and stays backward-compatible
when they are absent.

Source: https://code.claude.com/docs/en/changelog
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import validate_marketplace as vm  # noqa: E402


def _minimal_marketplace(**overrides) -> dict:
    base = {
        "name": "verdict",
        "owner": {"name": "Sattyam Jain"},
        "plugins": [{
            "name": "verdict",
            "source": "./",
        }],
    }
    base.update(overrides)
    return base


class TestTopLevelAdditions(unittest.TestCase):
    def test_full_v2_1_120_shape_validates(self) -> None:
        doc = _minimal_marketplace(
            **{
                "$schema": "https://code.claude.com/schemas/marketplace.json",
                "version": "2.0.1",
                "description": "Universal quality evaluator plugin.",
            }
        )
        self.assertEqual(vm.validate_marketplace(doc), [])

    def test_absent_fields_still_validate(self) -> None:
        # Pre-v2.1.120 shape (verdict's own marketplace.json today).
        self.assertEqual(vm.validate_marketplace(_minimal_marketplace()), [])

    def test_version_not_semver_errors(self) -> None:
        doc = _minimal_marketplace(version="not-a-semver")
        errors = vm.validate_marketplace(doc)
        self.assertTrue(
            any("version" in e and "SemVer" in e for e in errors),
            msg=f"expected SemVer error in {errors}",
        )

    def test_version_int_errors(self) -> None:
        doc = _minimal_marketplace(version=1)
        errors = vm.validate_marketplace(doc)
        self.assertTrue(
            any("version" in e for e in errors),
            msg=f"expected version error in {errors}",
        )

    def test_schema_non_string_errors(self) -> None:
        doc = _minimal_marketplace(**{"$schema": 123})
        errors = vm.validate_marketplace(doc)
        self.assertTrue(
            any("$schema" in e for e in errors),
            msg=f"expected $schema error in {errors}",
        )

    def test_description_too_long_errors(self) -> None:
        doc = _minimal_marketplace(description="x" * (vm.MAX_DESCRIPTION_LEN + 1))
        errors = vm.validate_marketplace(doc)
        self.assertTrue(
            any("description" in e and "exceeds" in e for e in errors),
            msg=f"expected description-length error in {errors}",
        )

    def test_description_non_string_errors(self) -> None:
        doc = _minimal_marketplace(description=42)
        errors = vm.validate_marketplace(doc)
        self.assertTrue(
            any("description" in e for e in errors),
            msg=f"expected description-type error in {errors}",
        )


class TestPluginEntrySchema(unittest.TestCase):
    def test_plugin_schema_field_validates(self) -> None:
        doc = _minimal_marketplace()
        doc["plugins"][0]["$schema"] = "https://code.claude.com/schemas/plugin.json"
        self.assertEqual(vm.validate_marketplace(doc), [])

    def test_plugin_schema_non_string_errors(self) -> None:
        doc = _minimal_marketplace()
        doc["plugins"][0]["$schema"] = 123
        errors = vm.validate_marketplace(doc)
        self.assertTrue(
            any("$schema" in e for e in errors),
            msg=f"expected plugin $schema error in {errors}",
        )

    def test_plugin_version_validates(self) -> None:
        doc = _minimal_marketplace()
        doc["plugins"][0]["version"] = "2.0.1"
        self.assertEqual(vm.validate_marketplace(doc), [])

    def test_plugin_version_non_semver_errors(self) -> None:
        doc = _minimal_marketplace()
        doc["plugins"][0]["version"] = "v2"
        errors = vm.validate_marketplace(doc)
        self.assertTrue(
            any("version" in e for e in errors),
            msg=f"expected plugin version error in {errors}",
        )


if __name__ == "__main__":
    unittest.main()
