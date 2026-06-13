#!/usr/bin/env python3
"""v4.3 scope contract — pins the rubric inventory.

Per the 2026-05-03 runbook §scope-reset block, Proofloop is a
Claude Code / Cowork plugin only. Frontier-lab eval-bench rubrics
(SWE-bench, Terminal-Bench, GAIA, OSWorld, MCP attack benches,
etc.) are explicitly out of scope.

This test pins the rubric inventory to ``IN_SCOPE_V43`` (11
plugin-domain rubrics). It is intentionally **failing today** —
v1.4.2 still ships 16 out-of-scope rubrics queued for the v2.0.0
trim. The red CI is the forcing function that motivates the cut;
once REMOVE-1 lands, the test goes green and stays green.

Source of truth:
    ~/Downloads/AboutMe/skill-references/daily-opportunity-radar/runbook.md
    §scope-reset (2026-05-03)
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

# Plugin-scope rubrics (v4.3 contract). Each MUST exist as ``<name>.md``
# in ``skills/judge/rubrics/``. May optionally have a
# ``<name>.weights.json`` sidecar and a ``<name>.example.md`` example.
# Adding a new rubric here is the only way to bring it into scope;
# anything else fails ``test_no_out_of_scope_rubrics`` below.
IN_SCOPE_V43: frozenset = frozenset({
    "code-review",
    "security",
    "devops",
    "data-analysis",
    "frontend-design",
    "testing",
    "documentation",
    "content-writing",
    "research",
    "default",
    "custom-template",
})

_SIDECAR_SUFFIXES = (".weights.json", ".example.md", ".md")


def _rubric_basenames(rubrics_dir: Path) -> Set[str]:
    """Return rubric base names from the rubrics directory.

    Strips known sidecar suffixes (``.md``, ``.weights.json``,
    ``.example.md``) so that, e.g., ``code-review.md`` and
    ``code-review.weights.json`` collapse to ``"code-review"``.
    """
    names: Set[str] = set()
    for entry in rubrics_dir.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        for suffix in _SIDECAR_SUFFIXES:
            if name.endswith(suffix):
                names.add(name[: -len(suffix)])
                break
    return names


class TestV43ScopeContract(unittest.TestCase):
    """Pin the rubric inventory to the v4.3 scope contract."""

    def test_in_scope_rubrics_have_markdown(self) -> None:
        """Every rubric on the v4.3 allowlist MUST have a .md file."""
        for name in sorted(IN_SCOPE_V43):
            self.assertTrue(
                (RUBRICS_DIR / f"{name}.md").is_file(),
                msg=(
                    f"v4.3 scope reset (2026-05-03): in-scope rubric "
                    f"'{name}' is missing its .md file. See "
                    f"AboutMe/skill-references/daily-opportunity-radar/"
                    f"runbook.md §scope-reset and CLAUDE.md "
                    f"§v4.3 Scope Contract."
                ),
            )

    def test_no_out_of_scope_rubrics(self) -> None:
        """Reject every rubric that is not on the v4.3 allowlist.

        Fails today (16 frontier-lab rubrics still present in
        v1.4.2); passes after the v2.0.0 trim PR removes them.
        This is the forcing function for the cut.
        """
        present = _rubric_basenames(RUBRICS_DIR)
        out_of_scope = sorted(present - IN_SCOPE_V43)
        self.assertEqual(
            out_of_scope,
            [],
            msg=(
                "v4.3 scope reset (2026-05-03): rubric(s) {0} are "
                "out-of-scope for verdict-as-plugin. See "
                "AboutMe/skill-references/daily-opportunity-radar/"
                "runbook.md §scope-reset and CLAUDE.md §v4.3 "
                "Scope Contract."
            ).format(out_of_scope),
        )


if __name__ == "__main__":
    unittest.main()
