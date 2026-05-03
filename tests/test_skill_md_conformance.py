#!/usr/bin/env python3
"""SKILL.md conformance tests (v4.3 UPDATE-1).

Per the Claude Code skill spec at https://code.claude.com/docs/en/skills,
a SKILL.md file must:

1. Open with a YAML frontmatter block (``---``-delimited).
2. Declare ``name`` (lowercase identifier) and ``description``.
3. Declare ``allowed-tools`` as an explicit list — never ``*`` /
   wildcard, since the plugin is shipped to third parties.
4. Keep the body (everything after the closing ``---``) under
   500 lines so the skill loads quickly into the model context.

These checks gate every SKILL.md edit going forward; failure means
the spec changed (rare) or someone accidentally removed a required
field.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = PROJECT_ROOT / "skills" / "judge" / "SKILL.md"

REQUIRED_FRONTMATTER_KEYS = {"name", "description", "allowed-tools"}
MAX_BODY_LINES = 500


def _split_frontmatter(text: str) -> Tuple[List[str], List[str]]:
    """Return (frontmatter_lines, body_lines).

    Both lists strip the ``---`` delimiters. If the file has no
    frontmatter block, returns ``([], <all-lines>)``.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines
    fm: List[str] = []
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return fm, lines[i + 1 :]
        fm.append(line)
    return [], lines


def _parse_frontmatter(fm_lines: List[str]) -> Dict[str, Any]:
    """Minimal YAML key/value parser.

    Handles ``key: value`` and ``key: [a, b, c]`` (a flat list of
    bare identifiers). Stdlib-only — we explicitly avoid pulling
    PyYAML in just for this conformance check.
    """
    out: Dict[str, Any] = {}
    for raw in fm_lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        if raw.startswith(" "):
            # Skip nested keys; we only need the top-level ones.
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            items = [
                p.strip().strip('"').strip("'")
                for p in inner.split(",")
                if p.strip()
            ]
            out[key] = items
        elif value.startswith('"') and value.endswith('"'):
            out[key] = value[1:-1]
        else:
            out[key] = value
    return out


class TestSkillMdConformance(unittest.TestCase):
    """Pin SKILL.md to the Claude Code skill spec."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SKILL_PATH.read_text(encoding="utf-8")
        cls.fm_lines, cls.body_lines = _split_frontmatter(cls.text)
        cls.fm = _parse_frontmatter(cls.fm_lines)

    def test_frontmatter_block_present(self) -> None:
        self.assertGreater(
            len(self.fm_lines),
            0,
            "SKILL.md must open with a YAML frontmatter block. "
            "See https://code.claude.com/docs/en/skills.",
        )

    def test_required_keys_present(self) -> None:
        missing = REQUIRED_FRONTMATTER_KEYS - set(self.fm.keys())
        self.assertEqual(
            missing,
            set(),
            f"SKILL.md frontmatter is missing required keys: "
            f"{sorted(missing)}. Required: "
            f"{sorted(REQUIRED_FRONTMATTER_KEYS)}.",
        )

    def test_allowed_tools_is_constrained_list(self) -> None:
        allowed = self.fm.get("allowed-tools")
        self.assertIsInstance(
            allowed,
            list,
            "SKILL.md 'allowed-tools' must be a list of tool names, "
            "not a wildcard or string. See the v4.3 scope contract.",
        )
        assert isinstance(allowed, list)
        self.assertGreater(
            len(allowed),
            0,
            "SKILL.md 'allowed-tools' list is empty.",
        )
        for entry in allowed:
            self.assertIsInstance(
                entry,
                str,
                "SKILL.md 'allowed-tools' entries must be strings.",
            )
            self.assertNotEqual(
                entry,
                "*",
                "SKILL.md 'allowed-tools' must not include '*' "
                "(wildcard). Constrain to least-privilege.",
            )

    def test_body_under_500_lines(self) -> None:
        self.assertLessEqual(
            len(self.body_lines),
            MAX_BODY_LINES,
            f"SKILL.md body is {len(self.body_lines)} lines; "
            f"max is {MAX_BODY_LINES}. Trim or split into sibling "
            f"SKILL-*.md files (see SKILL-judge-explain.md).",
        )


if __name__ == "__main__":
    unittest.main()
