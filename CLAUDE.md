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
- **No tests**: No test suite is currently configured.
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
│   │   └── benchmark.py         # Benchmark comparator — delta analysis vs standards
│   ├── rubrics/
│   │   ├── default.md           # Universal fallback rubric
│   │   ├── code-review.md       # Code review domain rubric
│   │   ├── frontend-design.md   # Frontend design domain rubric
│   │   ├── documentation.md     # Documentation domain rubric
│   │   ├── testing.md           # Testing domain rubric
│   │   ├── security.md          # Security domain rubric
│   │   ├── content-writing.md   # Content writing domain rubric
│   │   ├── data-analysis.md     # Data analysis domain rubric
│   │   └── custom-template.md   # Template for creating new rubrics
│   ├── scores/                  # Persisted score JSON files (gitignored by default)
│   └── references/
│       ├── scoring-methodology.md
│       └── benchmark-standards.md
├── agents/
│   └── judge-agent.md           # Read-only evaluator agent definition
├── hooks/
│   ├── hooks.json               # Hook definitions (Stop, SubagentStop events)
│   ├── common.sh                # Shared shell utilities (skill detection, config)
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
- **Graceful degradation**: All scripts handle missing files, bad JSON, and empty inputs by falling back to defaults rather than crashing. Hooks exit 0 on non-critical failures.
- **Rubric resolution chain**: Exact match → category prefix match → `default.md` fallback.
- **Consistent scorecard structure**: All three scripts (score, report, benchmark) produce Unicode box-drawing output with the same visual style.
- **Config-driven behavior**: `judge-config.json` controls which skills are auto-judged, scoring weights, thresholds, and output preferences. All scripts accept config as optional parameter with sensible defaults.
- **History-aware scoring**: Consistency dimension and trend indicators use historical score files for comparison.

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

Add project-specific notes here. This section is never auto-modified.

<!-- END MANUAL -->
