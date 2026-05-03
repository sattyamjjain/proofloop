#!/usr/bin/env python3
"""v4.3 scope contract — pins the rubric inventory.

Per the 2026-05-03 runbook §scope-reset block, Verdict is a
Claude Code / Cowork plugin only. Frontier-lab eval-bench rubrics
(SWE-bench, Terminal-Bench, GAIA, OSWorld, MCP attack benches,
etc.) are explicitly out of scope and queued for the v2.0.0 trim.

Adding a new rubric file requires either:
  - adding it to ``IN_SCOPE_V43`` (plugin-domain quality scoring), or
  - adding it to ``OUT_OF_SCOPE_V43`` (acknowledged frontier-lab
    cruft awaiting deletion in v2.0.0).

Failure of ``test_no_unclassified_rubrics`` is the forcing function
that prevents SWE-bench / Terminal-Bench / etc. from being silently
re-added to the plugin scope.

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

# Frontier-lab / eval-bench rubrics queued for removal in v2.0.0.
# Adding to this list does NOT make a rubric in-scope — it just
# acknowledges the file is present and pending trim under the
# v4.3 scope reset.
OUT_OF_SCOPE_V43: frozenset = frozenset({
    "agentic-sast-confidence",
    "browser-agent",
    "clinical-agentic-workflow",
    "code-review-aider-polyglot",
    "eu-ai-act-audit-trail",
    "function-hijacking-robustness",
    "gpt-5-5-differential",
    "model-spec-compliance",
    "owasp-mcp-top-10-beta",
    "project-deal-commerce",
    "routine-execution",
    "ship-readiness",
    "skill-compliance",
    "swe-bench-pro",
    "terminal-bench",
    "tool-output-rewrite",
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
                    f"v4.3 in-scope rubric '{name}' is missing its "
                    f".md file. See CLAUDE.md §v4.3 Scope Contract."
                ),
            )

    def test_no_unclassified_rubrics(self) -> None:
        """Reject rubrics that are neither in-scope nor known out-of-scope.

        This is the forcing function: if a new rubric file is added
        without updating ``IN_SCOPE_V43`` or ``OUT_OF_SCOPE_V43``,
        the test fails. Update the relevant frozenset above OR
        revisit the v4.3 scope reset.
        """
        present = _rubric_basenames(RUBRICS_DIR)
        unclassified = present - IN_SCOPE_V43 - OUT_OF_SCOPE_V43
        self.assertEqual(
            unclassified,
            set(),
            msg=(
                f"Unclassified rubric(s) present: {sorted(unclassified)}. "
                f"Either add to IN_SCOPE_V43 (plugin-domain) or "
                f"OUT_OF_SCOPE_V43 (queued for v2.0.0 trim). "
                f"See CLAUDE.md §v4.3 Scope Contract and the runbook "
                f"§scope-reset block (2026-05-03)."
            ),
        )

    def test_in_scope_and_out_of_scope_disjoint(self) -> None:
        """A rubric cannot be both in-scope and out-of-scope."""
        overlap = IN_SCOPE_V43 & OUT_OF_SCOPE_V43
        self.assertEqual(
            overlap,
            frozenset(),
            msg=(
                f"Rubric(s) listed in BOTH IN_SCOPE_V43 and "
                f"OUT_OF_SCOPE_V43: {sorted(overlap)}. Pick one."
            ),
        )


if __name__ == "__main__":
    unittest.main()
