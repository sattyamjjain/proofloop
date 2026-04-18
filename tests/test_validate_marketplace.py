#!/usr/bin/env python3
"""Tests for scripts/validate_marketplace.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import validate_marketplace as vm  # noqa: E402


def _minimal_valid() -> dict:
    return {
        "name": "my-plugins",
        "owner": {"name": "Alice"},
        "plugins": [{"name": "my-plugin", "source": "./plugins/my-plugin"}],
    }


class TestTopLevel(unittest.TestCase):
    def test_valid_minimal(self) -> None:
        self.assertEqual(vm.validate_marketplace(_minimal_valid()), [])

    def test_missing_name(self) -> None:
        doc = _minimal_valid()
        del doc["name"]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("name" in e for e in errs))

    def test_non_kebab_name(self) -> None:
        doc = _minimal_valid()
        doc["name"] = "MyPlugins"
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("kebab-case" in e for e in errs))

    def test_reserved_name(self) -> None:
        doc = _minimal_valid()
        doc["name"] = "claude-plugins-official"
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("reserved" in e for e in errs))

    def test_root_not_object(self) -> None:
        errs = vm.validate_marketplace("not an object")
        self.assertEqual(errs, ["root: must be a JSON object"])

    def test_missing_owner(self) -> None:
        doc = _minimal_valid()
        del doc["owner"]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("owner" in e for e in errs))

    def test_owner_missing_name(self) -> None:
        doc = _minimal_valid()
        doc["owner"] = {}
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("owner.name" in e for e in errs))


class TestPlugins(unittest.TestCase):
    def test_empty_plugins_rejected(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = []
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("at least one plugin" in e for e in errs))

    def test_plugin_missing_source(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p1"}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("'source'" in e for e in errs))

    def test_plugin_missing_name(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"source": "./p"}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("'name'" in e for e in errs))

    def test_duplicate_names(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [
            {"name": "dup", "source": "./a"},
            {"name": "dup", "source": "./b"},
        ]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("duplicate" in e for e in errs))

    def test_non_kebab_plugin_name(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "MyPlugin", "source": "./p"}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("kebab-case" in e for e in errs))

    def test_relative_source_must_start_with_dot_slash(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p", "source": "plugins/p"}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("'./'" in e for e in errs))

    def test_relative_source_rejects_parent_dir(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p", "source": "./../p"}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("'..'" in e for e in errs))

    def test_github_source_requires_repo(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p", "source": {"source": "github"}}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("'repo'" in e for e in errs))

    def test_github_source_valid(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [
            {"name": "p", "source": {"source": "github", "repo": "o/r"}}
        ]
        self.assertEqual(vm.validate_marketplace(doc), [])

    def test_npm_source_requires_package(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p", "source": {"source": "npm"}}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("'package'" in e for e in errs))

    def test_git_subdir_requires_url_and_path(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [
            {"name": "p", "source": {"source": "git-subdir", "url": "g/r"}}
        ]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("'path'" in e for e in errs))

    def test_unknown_source_type_rejected(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p", "source": {"source": "ftp"}}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("source.source" in e for e in errs))

    def test_bad_sha(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [
            {"name": "p", "source": {"source": "github", "repo": "o/r", "sha": "deadbeef"}}
        ]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("40-character" in e for e in errs))

    def test_tags_must_be_array(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p", "source": "./p", "tags": "single"}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("tags" in e for e in errs))

    def test_strict_must_be_bool(self) -> None:
        doc = _minimal_valid()
        doc["plugins"] = [{"name": "p", "source": "./p", "strict": "yes"}]
        errs = vm.validate_marketplace(doc)
        self.assertTrue(any("strict" in e for e in errs))


class TestProjectMarketplace(unittest.TestCase):
    """The shipped marketplace.json must always validate."""

    def test_shipped_marketplace_is_valid(self) -> None:
        import json

        path = PROJECT_ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(vm.validate_marketplace(data), [])


if __name__ == "__main__":
    unittest.main()
