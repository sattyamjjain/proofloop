#!/usr/bin/env python3
"""Validate .claude-plugin/marketplace.json against the April 2026 schema.

Stdlib-only. Exits 0 when valid, 1 on structural errors, 2 on missing file.

Usage:
    python3 scripts/validate_marketplace.py [path]

If no path is given, defaults to ``.claude-plugin/marketplace.json`` in
the current working directory. Intended for CI gating and local dev.

Schema source: <https://code.claude.com/docs/en/plugin-marketplaces>
(retrieved 2026-04-18; see docs/research-log.md).
"""

# ──────────────────────────────────────────────────────────────────────────────
# Claude Code release audit log (most recent five, newest first)
# ──────────────────────────────────────────────────────────────────────────────
# v2.1.129 (≤2026-05-08) — worktree.baseRef setting (`fresh` | `head`);
#   default flipped back to `fresh` (was local HEAD in v2.1.128); new
#   sandbox.bwrapPath and sandbox.socatPath managed settings (Linux/WSL).
#   Marketplace-schema-irrelevant.
# v2.1.128 (≤2026-05-07) — gateway /v1/models discovery on /model picker
#   is now opt-in via CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1 (was
#   automatic in v2.1.126); Ctrl+R history picker defaults to searching
#   all prompts across all projects (matches pre-v2.1.124 behavior);
#   third-party deployments no longer see spinner tips that point at
#   first-party Anthropic surfaces; skillOverrides setting now respects
#   different visibility options; claude_code.pull_request.count OTel
#   metric now counts PRs/MRs created via MCP tools.
#   Marketplace-schema-irrelevant.
# v2.1.127 (≤2026-05-03) — bridge release between v2.1.126 and v2.1.128
#   per claudefa.st digest; no individually documented surface change
#   that affects proofloop's transcript-shape or safety-allowlist surfaces.
#   Marketplace-schema-irrelevant.
# v2.1.126 (2026-05-01) — /model picker reads gateway /v1/models when
#   ANTHROPIC_BASE_URL is set; claude project purge [path]; the
#   --dangerously-skip-permissions allowlist now also covers .git/,
#   .vscode/, and shell config files (was .claude/{skills,agents,commands}/
#   only). Marketplace-schema-irrelevant. Safety-dim allowlist extension
#   landed in v2.0.2 score.py.
# v2.1.125 (2026-04-30/05-01) — alwaysLoad option for MCP server config;
#   claude plugin prune for orphaned plugin deps; type-to-filter search
#   box on /skills. Marketplace-schema-irrelevant.
# Earlier audited entries (v2.1.124 / v2.1.123 / v2.1.122 / v2.1.121 /
# v2.1.120 / v2.1.119) pruned per the ≤5-release cap. v2.1.121
# safety-allowlist + v2.1.120 marketplace validator keys + v2.1.119
# duration_ms enrichment all landed in v2.0.1 (CHANGELOG [2.0.1] -
# 2026-05-04). v2.1.122–v2.1.124 were marketplace-schema-irrelevant
# bridge / stability releases.
# Source: https://code.claude.com/docs/en/changelog
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, List

# ---------------------------------------------------------------------------
# Schema knobs
# ---------------------------------------------------------------------------

RESERVED_NAMES: set = {
    "claude-code-marketplace",
    "claude-code-plugins",
    "claude-plugins-official",
    "anthropic-marketplace",
    "anthropic-plugins",
    "agent-skills",
    "knowledge-work-plugins",
    "life-sciences",
}

VALID_SOURCE_TYPES: set = {"github", "url", "git-subdir", "npm"}
KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SHA_40 = re.compile(r"^[0-9a-f]{40}$")
# Permissive SemVer (allows pre-release / build suffixes the spec accepts).
SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
MAX_DESCRIPTION_LEN = 500

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _error(errors: List[str], path: str, msg: str) -> None:
    errors.append(f"{path}: {msg}")


def _validate_source(source: Any, path: str, errors: List[str]) -> None:
    """Validate a single plugin's ``source`` field."""
    if isinstance(source, str):
        if not source.startswith("./"):
            _error(errors, path, "relative-string source must start with './'")
        if ".." in Path(source).parts:
            _error(errors, path, "source path must not contain '..'")
        return
    if not isinstance(source, dict):
        _error(errors, path, "source must be a string or object")
        return
    kind = source.get("source")
    if kind not in VALID_SOURCE_TYPES:
        _error(
            errors, path,
            f"source.source must be one of {sorted(VALID_SOURCE_TYPES)}, got {kind!r}",
        )
        return
    if kind == "github" and "repo" not in source:
        _error(errors, path, "github source requires 'repo'")
    if kind == "url" and "url" not in source:
        _error(errors, path, "url source requires 'url'")
    if kind == "git-subdir":
        if "url" not in source:
            _error(errors, path, "git-subdir source requires 'url'")
        if "path" not in source:
            _error(errors, path, "git-subdir source requires 'path'")
    if kind == "npm" and "package" not in source:
        _error(errors, path, "npm source requires 'package'")
    if "sha" in source and not SHA_40.match(str(source["sha"])):
        _error(errors, path, "sha must be a 40-character hex string")


def _validate_plugin(plugin: Any, index: int, errors: List[str]) -> None:
    path = f"plugins[{index}]"
    if not isinstance(plugin, dict):
        _error(errors, path, "must be an object")
        return
    name = plugin.get("name")
    if not isinstance(name, str) or not name:
        _error(errors, path, "missing required 'name'")
    elif not KEBAB_CASE.match(name):
        _error(errors, path, f"name '{name}' is not kebab-case")
    if "source" not in plugin:
        _error(errors, path, "missing required 'source'")
    else:
        _validate_source(plugin["source"], f"{path}.source", errors)
    # Optional field type checks
    if "tags" in plugin and not isinstance(plugin["tags"], list):
        _error(errors, path, "tags must be an array")
    if "keywords" in plugin and not isinstance(plugin["keywords"], list):
        _error(errors, path, "keywords must be an array")
    if "strict" in plugin and not isinstance(plugin["strict"], bool):
        _error(errors, path, "strict must be a boolean")
    # Claude Code 2.1.120 — $schema is now accepted on plugin entries too.
    if "$schema" in plugin and not isinstance(plugin["$schema"], str):
        _error(errors, path, "$schema must be a string URL")
    if "version" in plugin:
        version = plugin["version"]
        if not isinstance(version, str) or not SEMVER_RE.match(version):
            _error(errors, path, f"version {version!r} is not SemVer")


def _validate_top_level_v2_1_120(data: dict, errors: List[str]) -> None:
    """Type-check the v2.1.120 top-level additions (no-op when absent).

    ``$schema``, ``version``, and ``description`` are now accepted by
    ``claude plugin validate`` on ``marketplace.json``. We type-check
    them when present so a typo like ``version: 1`` (int instead of
    SemVer string) surfaces here rather than at install time. Absent
    fields stay backward-compatible with pre-2.1.120 marketplace
    documents.
    """
    if "$schema" in data and not isinstance(data["$schema"], str):
        _error(errors, "$schema", "must be a string URL")
    if "version" in data:
        version = data["version"]
        if not isinstance(version, str) or not SEMVER_RE.match(version):
            _error(errors, "version", f"{version!r} is not SemVer")
    if "description" in data:
        description = data["description"]
        if not isinstance(description, str):
            _error(errors, "description", "must be a string")
        elif len(description) > MAX_DESCRIPTION_LEN:
            _error(
                errors,
                "description",
                f"exceeds {MAX_DESCRIPTION_LEN} chars (got {len(description)})",
            )


def validate_marketplace(data: Any) -> List[str]:
    """Return a list of validation errors for the marketplace document."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["root: must be a JSON object"]

    name = data.get("name")
    if not isinstance(name, str) or not name:
        _error(errors, "name", "missing or empty")
    else:
        if not KEBAB_CASE.match(name):
            _error(errors, "name", f"'{name}' is not kebab-case")
        if name in RESERVED_NAMES:
            _error(errors, "name", f"'{name}' is reserved for Anthropic")

    owner = data.get("owner")
    if not isinstance(owner, dict):
        _error(errors, "owner", "must be an object with at least 'name'")
    else:
        if not isinstance(owner.get("name"), str) or not owner["name"]:
            _error(errors, "owner.name", "missing or empty")

    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        _error(errors, "plugins", "must be an array")
    else:
        if not plugins:
            _error(errors, "plugins", "must contain at least one plugin")
        seen_names: set = set()
        for i, plugin in enumerate(plugins):
            _validate_plugin(plugin, i, errors)
            if isinstance(plugin, dict):
                pname = plugin.get("name")
                if pname in seen_names:
                    _error(errors, f"plugins[{i}]", f"duplicate name '{pname}'")
                elif isinstance(pname, str):
                    seen_names.add(pname)

    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        _error(errors, "metadata", "must be an object if present")

    _validate_top_level_v2_1_120(data, errors)

    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: List[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path(".claude-plugin/marketplace.json")
    if not target.is_file():
        print(f"Error: {target} does not exist.", file=sys.stderr)
        return 2
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: {target} contains invalid JSON — {exc}", file=sys.stderr)
        return 1

    errors = validate_marketplace(data)
    if errors:
        print(f"{target} has {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)
        return 1
    print(f"{target} ✓ valid against the April 2026 marketplace schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
