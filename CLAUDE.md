# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- AUTO-MANAGED: project-description -->
## Overview

**Verdict** is a Claude Code plugin that auto-evaluates skill and agent execution quality. It provides 7-dimension scoring (correctness, completeness, adherence, actionability, efficiency, safety, consistency), configurable rubrics, persistent scorecards, and dual-mode operation (auto via hooks + manual via `/judge` command). Works on both Claude Code and Claude Cowork.

- Author: Sattyam Jain
- License: MIT
- Platforms: `claude-code`, `claude-cowork`

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: build-commands -->
## Build & Development Commands

This project has no build step or package manager. Python scripts use stdlib only (Python 3.9+).

- **Run scoring engine**: `python3 skills/judge/scripts/score.py --skill SKILL --transcript PATH --rubric-dir skills/judge/rubrics --scores-dir skills/judge/scores --config judge-config.json`
- **Run report viewer**: `python3 skills/judge/scripts/report.py --scores-dir skills/judge/scores [--skill NAME] [--last N] [--format text|json]`
- **Run benchmark comparator**: `python3 skills/judge/scripts/benchmark.py --skill NAME --scores-dir skills/judge/scores --references-dir skills/judge/references`
- **Run tests**: `python3 -m unittest discover tests/ -v`
- **No linter**: No linting or formatting tools are configured.

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
Verdict/
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest (name, version, components)
│   └── marketplace.json         # Marketplace listing metadata
├── skills/judge/
│   ├── SKILL.md                 # Core skill definition (7-dimension scoring system)
│   ├── scripts/
│   │   ├── score.py             # Scoring engine — heuristic transcript analysis
│   │   ├── report.py            # Score reporter — Unicode scorecards & trends
│   │   ├── benchmark.py         # Benchmark comparator — delta analysis vs standards
│   │   └── detect-skill.sh      # Skill name detection from transcripts
│   ├── rubrics/
│   │   ├── default.md           # Universal fallback rubric
│   │   ├── code-review.md       # Code review domain rubric
│   │   ├── frontend-design.md   # Frontend design domain rubric
│   │   ├── documentation.md     # Documentation domain rubric
│   │   ├── testing.md           # Testing domain rubric
│   │   ├── security.md          # Security domain rubric
│   │   ├── content-writing.md   # Content writing domain rubric
│   │   ├── data-analysis.md     # Data analysis domain rubric
│   │   ├── research.md          # Research & exploration domain rubric
│   │   ├── devops.md            # DevOps & infrastructure domain rubric
│   │   └── custom-template.md   # Template for creating new rubrics
│   ├── scores/                  # Persisted score JSON files (gitignored by default)
│   └── references/
│       ├── scoring-methodology.md
│       └── benchmark-standards.md
├── tests/
│   └── test_score.py            # Unit tests for scoring engine
├── agents/
│   └── judge-agent.md           # Read-only evaluator agent definition
├── hooks/
│   ├── hooks.json               # Hook definitions (Stop, SubagentStop events)
│   ├── common.sh                # Shared shell utilities (skill detection, config, deps)
│   ├── judge-on-stop.sh         # Auto-judge hook for Stop events
│   └── judge-on-subagent-stop.sh
├── commands/
│   ├── judge.md                 # /judge slash command
│   ├── scorecard.md             # /scorecard slash command
│   ├── benchmark.md             # /benchmark slash command
│   └── judge-config.md          # /judge-config slash command
├── judge-config.json            # Root configuration (auto_judge, scoring weights)
├── README.md
└── CHANGELOG.md
```

### Data Flow

1. **Auto mode**: Skill executes → `Stop` hook fires → `judge-on-stop.sh` reads transcript → detects skill name → checks config → runs `score.py` → persists JSON scorecard to `scores/`
2. **Manual mode**: User runs `/judge` → Claude reads transcript from conversation context → applies rubric → renders scorecard → persists JSON
3. **Reporting**: `/scorecard` reads from `scores/` directory → renders Unicode table with trends
4. **Benchmarking**: `/benchmark` reads scores + `benchmark-standards.md` → computes deltas → renders comparison report

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Code Conventions

### Python (scripts/)
- Python 3.9+ with `from __future__ import annotations`
- Type hints on all function signatures using `typing` module (`Dict`, `List`, `Optional`, `Tuple`, `Any`)
- Stdlib only — no third-party packages
- Docstrings on all public functions (imperative mood, describes return value)
- `snake_case` for functions and variables, `UPPER_SNAKE_CASE` for module-level constants
- Private helpers prefixed with `_` (e.g., `_analyze_correctness`, `_pad_line`)
- Section separators: `# ---` comment blocks with 75-char dashes between logical sections
- CLI pattern: `parse_args()` + `main()` with `if __name__ == "__main__": main()`
- `argparse` for CLI argument parsing
- `Path` from `pathlib` for all file operations
- `json.loads`/`json.dumps` for serialization (not `json.load`/`json.dump`)

### Shell (hooks/)
- `#!/bin/bash` with `set -euo pipefail`
- `jq` for JSON parsing in shell scripts
- Functions use `local` for all variables
- Exit 0 on non-critical failures (don't block user workflow)
- Exit 2 to signal a blocking failure (score below threshold)

### Markdown (skills/, commands/, agents/)
- YAML frontmatter with `name`, `description`, `usage` fields
- Structured sections with `##` headings
- Tables for dimension/weight/criteria specifications

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: patterns -->
## Detected Patterns

- **Heuristic scoring**: `score.py` uses regex pattern matching against transcripts rather than LLM evaluation. Patterns detect errors, incompleteness, safety issues, hallucinations, and tool call density.
- **Auto-deductions and bonuses**: Red flags (hallucinations, placeholders, destructive commands) deduct up to 2.0 from composite; bonuses (edge cases, trade-off analysis) add up to 1.0. Applied after weighted composite.
- **Context-aware safety**: Safety regex excludes discussion context (review comments, comparisons) to avoid false positives on transcripts that discuss credentials without defining them.
- **Graceful degradation**: All scripts handle missing files, bad JSON, and empty inputs by falling back to defaults rather than crashing. Hooks exit 0 on non-critical failures.
- **Rubric resolution chain**: Exact match → category prefix match → `default.md` fallback.
- **Consistent scorecard structure**: All three scripts (score, report, benchmark) produce Unicode box-drawing output with the same visual style.
- **Config-driven behavior**: `judge-config.json` controls which skills are auto-judged, scoring weights, thresholds, and output preferences. All scripts accept config as optional parameter with sensible defaults.
- **History-aware scoring**: Consistency dimension and trend indicators use historical score files for comparison.
- **Dependency checking**: Hook scripts verify `jq`, `bc`, and `python3` are available before executing, with install hints on failure.

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: git-insights -->
## Git Insights

- Main branch: `main`
- Single-contributor project (Sattyam Jain)

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: best-practices -->
## Best Practices

- When modifying Python scripts, maintain stdlib-only constraint — do not add third-party dependencies.
- When adding new rubrics, copy `custom-template.md` and follow the existing dimension criteria table format.
- Score JSON files in `scores/` use the naming pattern `{skill}_{timestamp}.json`.
- Hook scripts must not block user workflow on non-critical failures (exit 0, not exit 1).
- All dimension weights in `judge-config.json` must sum to 1.0.

<!-- END AUTO-MANAGED -->

<!-- MANUAL -->
## Custom Notes

### v4.3 Scope Contract (2026-05-03)

Verdict is a **Claude Code / Cowork plugin only.** Per the 2026-05-03 v4.3 scope reset (runbook §scope-reset), the rubric and adapter inventory is pinned to plugin-domain quality scoring. Frontier-lab eval-bench scope (SWE-bench, Terminal-Bench, GAIA, OSWorld, MCP attack benches, etc.) is explicitly out of scope and will not be re-added without a runbook spec change.

**In-scope rubrics (11):** `code-review`, `security`, `devops`, `data-analysis`, `frontend-design`, `testing`, `documentation`, `content-writing`, `research`, `default`, `custom-template`.

**Out-of-scope, queued for v2.0.0 trim (16):** `agentic-sast-confidence`, `browser-agent`, `clinical-agentic-workflow`, `code-review-aider-polyglot`, `eu-ai-act-audit-trail`, `function-hijacking-robustness`, `gpt-5-5-differential`, `model-spec-compliance`, `owasp-mcp-top-10-beta`, `project-deal-commerce`, `routine-execution`, `ship-readiness`, `skill-compliance`, `swe-bench-pro`, `terminal-bench`, `tool-output-rewrite`.

**In-scope adapters (4):** `claude_code`, `cowork`, `openai_compatible`, `codex`. Cross-ecosystem adapters (Gemini, MLflow, Inspect-AI, Terminal-Bench, browser-harness) are out of scope.

**Core surfaces (do not regress):** 7-dimension scoring (correctness, completeness, adherence, actionability, efficiency, safety, consistency); auto-hooks (`Stop`, `SubagentStop`, `StopFailure`); `/judge`, `/scorecard`, `/benchmark`, `/judge-config`, `/against`, `/compare` slash commands; per-rubric `<name>.weights.json` sidecar overrides; threshold blocking via `judge-config.json`.

**Enforcement:** `tests/test_v43_scope_contract.py` pins the rubric inventory. Adding a new rubric file fails the test until classified as in-scope (allowlist) or out-of-scope (deprecation list). See the test file for the canonical lists.

**Source of truth:** `~/Downloads/AboutMe/skill-references/daily-opportunity-radar/runbook.md` §scope-reset block (2026-05-03).

### Other notes

Add project-specific notes here. This section is never auto-modified.

<!-- END MANUAL -->
