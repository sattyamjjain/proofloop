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

import validate_marketplace as vm  # noqa: E402,F401


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


class TestClaudeCodeReleaseAuditLog(unittest.TestCase):
    """Forcing function: don't silently drop the audit log comment block.

    The block lists every Claude Code release that touched (or
    explicitly did not touch) the marketplace.json / plugin.json
    schema. A future cycle that prunes the comment would lose the
    forward-looking sync visibility — this test surfaces the
    deletion at PR time.
    """

    @classmethod
    def setUpClass(cls) -> None:
        path = PROJECT_ROOT / "scripts" / "validate_marketplace.py"
        cls.source = path.read_text(encoding="utf-8")

    def test_audit_log_lists_most_recent_five(self) -> None:
        for marker in (
            "v2.1.122",
            "v2.1.123",
            "v2.1.124",
            "v2.1.125",
            "v2.1.126",
        ):
            self.assertIn(
                marker,
                self.source,
                msg=(
                    f"validate_marketplace.py audit log is missing "
                    f"{marker}. The comment block at the top of the "
                    f"file is the marketplace-schema sync visibility "
                    f"surface; rotate when a new release lands but "
                    f"never below the most recent five."
                ),
            )

    def test_audit_log_pruned_oldest_three(self) -> None:
        # v2.1.119 / v2.1.120 / v2.1.121 were rotated out in v2.0.2.
        # The footer paragraph names them as "earlier audited entries
        # pruned per the ≤5-release cap" — the markers themselves
        # appear there. Anything earlier should be absent entirely.
        for pruned in ("v2.1.118",):
            self.assertNotIn(
                pruned,
                self.source,
                msg=(
                    f"validate_marketplace.py audit log still references "
                    f"{pruned}. The block must stay at exactly the most "
                    f"recent five and pruned-entries must not linger."
                ),
            )


if __name__ == "__main__":
    unittest.main()
