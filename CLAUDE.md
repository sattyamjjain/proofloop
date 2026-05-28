# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- MANUAL: project-description -->
## Overview

**Verdict** is a Claude Code plugin that auto-evaluates skill and agent execution quality. It provides 7-dimension scoring (correctness, completeness, adherence, actionability, efficiency, safety, consistency), configurable rubrics, persistent scorecards, and dual-mode operation (auto via hooks + manual via `/judge` command). Works on both Claude Code and Claude Cowork.

- Author: Sattyam Jain
- License: MIT
- Platforms: `claude-code`, `claude-cowork`

<!-- END MANUAL -->

<!-- MANUAL: v43-scope-contract -->
## v4.3 Scope Contract (2026-05-03)

Verdict is a **Claude Code / Cowork plugin only.** Per the 2026-05-03 v4.3 scope reset (runbook §scope-reset), the rubric and adapter inventory is pinned to plugin-domain quality scoring. Frontier-lab eval-bench scope (SWE-bench, Terminal-Bench, GAIA, OSWorld, MCP attack benches, etc.) is explicitly out of scope and will not be re-added without a runbook spec change.

**In-scope rubrics (11):** `code-review`, `security`, `devops`, `data-analysis`, `frontend-design`, `testing`, `documentation`, `content-writing`, `research`, `default`, `custom-template`.

**Out-of-scope, queued for v2.0.0 trim (16):** `agentic-sast-confidence`, `browser-agent`, `clinical-agentic-workflow`, `code-review-aider-polyglot`, `eu-ai-act-audit-trail`, `function-hijacking-robustness`, `gpt-5-5-differential`, `model-spec-compliance`, `owasp-mcp-top-10-beta`, `project-deal-commerce`, `routine-execution`, `ship-readiness`, `skill-compliance`, `swe-bench-pro`, `terminal-bench`, `tool-output-rewrite`.

**In-scope adapters (4):** `claude_code`, `cowork`, `openai_compatible`, `codex`. Cross-ecosystem adapters (Gemini, MLflow, Inspect-AI, Terminal-Bench, browser-harness) are out of scope.

**Core surfaces (do not regress):** 7-dimension scoring (correctness, completeness, adherence, actionability, efficiency, safety, consistency); auto-hooks (`Stop`, `SubagentStop`, `StopFailure`); `/judge`, `/scorecard`, `/benchmark`, `/judge-config`, `/against`, `/compare` slash commands; per-rubric `<name>.weights.json` sidecar overrides; threshold blocking via `judge-config.json`.

**Enforcement:** `tests/test_v43_scope_contract.py` pins the rubric inventory. The test fails today (16 out-of-scope rubrics still present in v1.4.2) and will go green once the v2.0.0 trim PR removes them — the red CI is the forcing function for the cut.

**Source of truth:** `~/Downloads/AboutMe/skill-references/daily-opportunity-radar/runbook.md` §scope-reset block (2026-05-03).

<!-- END MANUAL -->

<!-- AUTO-MANAGED: build-commands -->
## Build & Development Commands

This project has no build step or package manager. Python scripts use stdlib only (Python 3.9+); the optional LLM second-opinion analyzer uses `urllib.request` rather than pulling in the `anthropic` SDK.

**Core scoring & reporting**
- **Run scoring engine**: `python3 skills/judge/scripts/score.py --skill SKILL --transcript PATH --rubric-dir skills/judge/rubrics --scores-dir skills/judge/scores --config judge-config.json`
- **Run report viewer**: `python3 skills/judge/scripts/report.py --scores-dir skills/judge/scores [--skill NAME] [--last N] [--format text|json]`
- **Run benchmark comparator**: `python3 skills/judge/scripts/benchmark.py --skill NAME --scores-dir skills/judge/scores --references-dir skills/judge/references`

**Newer subcommands**
- **Compare two runs**: `python3 skills/judge/scripts/compare.py --a SCORE_A.json --b SCORE_B.json` (powers `/compare`)
- **Judge against a reference**: `python3 skills/judge/scripts/against.py --skill SKILL --reference REF.json` (powers `/against`)
- **Explain a scorecard**: `python3 skills/judge/scripts/explain.py --score SCORE.json` — human-readable dimension breakdown
- **Estimate LLM-judge cost**: `python3 skills/judge/scripts/cost_estimator.py --transcript PATH --config judge-config.json`
- **Interactive studio**: `python3 skills/judge/scripts/studio.py` — TUI for browsing scores
- **Continuous watch**: `python3 skills/judge/scripts/watch.py --scores-dir skills/judge/scores`
- **Lint hook scripts**: `python3 skills/judge/scripts/hook_lint.py hooks/*.sh`

**Validation & repo tooling (top-level `scripts/`)**
- **Validate marketplace.json**: `python3 scripts/validate_marketplace.py`
- **Install a third-party rubric**: `python3 scripts/install_rubric.py --source PATH_OR_URL`
- **Run benchmark pack**: `python3 scripts/benchmark_pack.py`
- **Sandbox caps check**: `python3 scripts/sandbox_caps_check.py`
- **README release-anchor check**: `python3 scripts/check_readme_release_anchor.py`

**Tests**
- **Run all tests**: `python3 -m unittest discover tests/ -v` (29 test files; pins v4.3 scope contract, schema, adapters, hooks, LLM-judge budget, marketplace shape, version consistency, etc.)
- **Single test**: `python3 -m unittest tests.test_v43_scope_contract -v`

**Linting**: No linter is configured for the codebase. `hook_lint.py` is project-specific shell-hook safety lint, not a general linter.

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
Verdict/  (v2.0.2)
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest (skills, agents, commands, hooks)
│   └── marketplace.json         # Marketplace listing metadata
├── skills/judge/
│   ├── SKILL.md                 # Core skill definition (7-dimension scoring)
│   ├── scripts/                 # All Python entry points (stdlib only)
│   │   ├── score.py             # Scoring engine — heuristic + optional LLM second opinion
│   │   ├── report.py            # Score reporter — Unicode scorecards & trends
│   │   ├── benchmark.py         # Benchmark comparator — delta vs standards
│   │   ├── against.py           # /against — judge a run against a reference
│   │   ├── compare.py           # /compare — diff two scorecards
│   │   ├── explain.py           # /judge-config explain — verbose breakdown
│   │   ├── cost_estimator.py    # Pre-flight LLM-judge token/cost estimate
│   │   ├── studio.py            # Interactive TUI for score browsing
│   │   ├── watch.py             # Long-running watcher over scores/
│   │   ├── hook_lint.py         # Lint hook shell scripts for safety
│   │   └── detect-skill.sh      # Skill-name detection from transcripts
│   ├── analyzers/
│   │   └── llm_judge.py         # Opt-in LLM second-opinion analyzer (urllib only)
│   ├── adapters/                # Cross-platform transcript readers (the 4 in-scope)
│   │   ├── claude_code.py
│   │   ├── cowork.py
│   │   ├── codex.py
│   │   └── openai_compatible.py
│   ├── exporters/               # Scorecard exporters
│   ├── integrations/            # External integration shims
│   ├── rubrics/                 # 11 in-scope rubrics + custom-template + sidecar weights
│   │   ├── default.md           # Universal fallback
│   │   ├── code-review.md, security.md, security.weights.json
│   │   ├── devops.md, data-analysis.md, frontend-design.md
│   │   ├── testing.md, documentation.md, content-writing.md
│   │   ├── research.md
│   │   └── custom-template.md
│   ├── scores/                  # Persisted score JSON (gitignored)
│   └── references/
│       ├── scoring-methodology.md
│       └── benchmark-standards.md
├── schemas/
│   └── scorecard.v1.schema.json # JSON Schema for scorecard documents
├── agents/
│   └── judge-agent.md           # Read-only evaluator agent
├── hooks/
│   ├── hooks.json               # Stop, SubagentStop, StopFailure event bindings
│   ├── common.sh                # Shared shell utilities
│   ├── judge-on-stop.sh
│   ├── judge-on-subagent-stop.sh
│   └── judge-on-stop-failure.sh # Auto-judge on StopFailure
├── commands/                    # 6 slash commands
│   ├── judge.md, scorecard.md, benchmark.md, judge-config.md
│   ├── against.md               # /against
│   └── compare.md               # /compare
├── scripts/                     # Repo tooling (validation, install, sandbox caps)
│   ├── validate_marketplace.py
│   ├── install_rubric.py
│   ├── benchmark_pack.py
│   ├── sandbox_caps_check.py
│   └── check_readme_release_anchor.py
├── benchmarks/                  # Reference benchmark corpus
│   ├── corpus/
│   ├── manifest.json
│   └── README.md
├── routines/
│   └── weekly-team-digest.md
├── releases/                    # Release notes per version
│   └── v1.4.2.md
├── docs/                        # Project docs (followups, metrics, research-log, schema-registry)
│   ├── cli/, launch/
│   └── followups.md, metrics.md, research-log.md, schema-registry.md
├── tests/                       # 29 test files (cli/, fixtures/, schema validators)
├── judge-config.json            # Root config: auto_judge, manual_judge, scoring, tokenizer_baselines, llm_second_opinion
├── README.md
└── CHANGELOG.md
```

### Data Flow

1. **Auto mode**: Skill executes → `Stop` / `SubagentStop` / `StopFailure` hook fires → `judge-on-*.sh` reads transcript via `common.sh` → `detect-skill.sh` resolves skill name → `score.py` runs heuristic pass → if `llm_second_opinion.enabled`, `analyzers/llm_judge.py` adds per-dimension LLM scores → JSON scorecard persisted to `scores/` and validated against `schemas/scorecard.v1.schema.json`.
2. **Manual mode**: User runs `/judge` → Claude reads transcript from conversation context → applies rubric → renders scorecard → persists JSON.
3. **Cross-platform read**: `adapters/{claude_code,cowork,codex,openai_compatible}.py` normalize each platform's transcript shape into the same line stream `score.py` consumes.
4. **Reporting**: `/scorecard` reads `scores/` → `report.py` renders Unicode table with trends. `/compare` runs `compare.py` over two scorecards; `/against` runs `against.py` vs a reference; `/judge-config explain` runs `explain.py`.
5. **Benchmarking**: `/benchmark` reads scores + `benchmark-standards.md` → `benchmark.py` computes deltas. `scripts/benchmark_pack.py` runs the full reference corpus in `benchmarks/`.

<!-- END AUTO-MANAGED -->

<!-- MANUAL: conventions -->
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

<!-- END MANUAL -->

<!-- AUTO-MANAGED: patterns -->
## Detected Patterns

- **Heuristic scoring core, optional LLM second opinion**: `score.py` is regex/heuristic-first against transcripts. `analyzers/llm_judge.py` is opt-in (requires `judge-config.json.llm_second_opinion.enabled = true` *and* `ANTHROPIC_API_KEY`), uses `urllib.request` so no SDK dependency, and merges per-dimension `llm_score` / `llm_justification` into the scorecard. The `task-budgets-2026-03-13` beta header caps spend.
- **Adapter pattern for cross-platform transcripts**: `adapters/{claude_code,cowork,codex,openai_compatible}.py` each normalize their platform's transcript into the same JSONL line stream `score.py` consumes — Claude Code is the reference format.
- **Schema-validated scorecards**: All persisted scores conform to `schemas/scorecard.v1.schema.json`. Evolution rules live in `DEEP_ANALYSIS.md §Schema stability contract` (per the schema's own description).
- **Auto-deductions and bonuses**: Red flags (hallucinations, placeholders, destructive commands) deduct up to 2.0 from composite; bonuses (edge cases, trade-off analysis) add up to 1.0. Applied after weighted composite.
- **Context-aware safety**: Safety regex excludes discussion context (review comments, comparisons) to avoid false positives on transcripts that merely discuss credentials without defining them.
- **Per-rubric weight sidecars**: `<rubric>.weights.json` (e.g. `security.weights.json`) overrides default dimension weights without forking the rubric markdown.
- **Auto Memory aware**: `adapters/claude_code.py` accepts either a single transcript file *or* a directory containing the `~/.claude/history/*.jsonl` shards plus the memory preamble Claude Code injects (Opus 4.7, 2026-04-17+).
- **Graceful degradation**: All scripts handle missing files, bad JSON, and empty inputs by falling back to defaults rather than crashing. Hooks exit 0 on non-critical failures.
- **Rubric resolution chain**: Exact match → category prefix match → `default.md` fallback.
- **Consistent scorecard structure**: `score.py`, `report.py`, `benchmark.py`, `compare.py`, `against.py`, `explain.py` all share Unicode box-drawing output style.
- **Config-driven behavior**: `judge-config.json` keys — `auto_judge`, `manual_judge`, `scoring`, `tokenizer_baselines`, `llm_second_opinion` — control which skills are auto-judged, scoring weights, thresholds, LLM-opinion gating, and output preferences.
- **History-aware scoring**: Consistency dimension and trend indicators use historical score files for comparison.
- **Hook safety lint**: `hook_lint.py` is project-specific lint for shell hooks (separate from general linting, which is not configured).
- **Dependency checking**: Hook scripts verify `jq`, `bc`, and `python3` are available before executing, with install hints on failure.

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: git-insights -->
## Git Insights

- **Main branch**: `main`. Default branch for PRs.
- **Single-contributor** project (Sattyam Jain), but workflow mirrors a team: every change lands via a feature/chore branch + PR (`chore/<date>-<topic>`, `feature/<short-desc>`, `fix/<short-desc>`).
- **v2.0.0 trim shipped**: The `v4.3 Scope Contract` originally described the 16 out-of-scope rubrics as still present in v1.4.2. Current `HEAD` is **v2.0.2** and the trim has happened — only the 11 in-scope rubrics remain under `skills/judge/rubrics/`.
- **Recent work pattern** — disposition discipline: most recent merges are "REJECT-of-record" chores that document *why* a proposed change (held_out_consistency test-gaming heuristic, metis_safety, DELEGATE-52 outcome_corruption 8th dimension) was rejected, so the choice is auditable. See PRs #30–#33.
- **Sync chore**: PR #32 synced the README architecture tree with the actual `scripts/` inventory (added `check_readme_release_anchor.py`). That same drift class is what the AUTO-MANAGED Architecture block above is now defending against in `CLAUDE.md`.

<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: best-practices -->
## Best Practices

- **Keep the stdlib-only constraint** when modifying Python scripts, including the LLM-judge analyzer — use `urllib.request`, not `requests` or `anthropic`. No third-party packages.
- **Honor the v4.3 scope contract** when adding rubrics or adapters. Anything outside the 11 in-scope rubrics or 4 in-scope adapters needs a runbook spec change first; `tests/test_v43_scope_contract.py` will fail you otherwise.
- **New rubrics**: copy `custom-template.md` and follow the existing dimension criteria table format. If the rubric needs non-default weights, add a `<name>.weights.json` sidecar instead of editing scoring defaults.
- **Score JSON files** in `scores/` use the naming pattern `{skill}_{timestamp}.json` and must validate against `schemas/scorecard.v1.schema.json`.
- **Hook scripts must not block user workflow** on non-critical failures (exit 0, not exit 1). Reserve exit 2 for true threshold-breach blocks. Run `hook_lint.py` over them before committing.
- **All dimension weights** in `judge-config.json` and any `<rubric>.weights.json` sidecar must sum to 1.0.
- **LLM second opinion is opt-in and budgeted**: keep `llm_second_opinion.enabled = false` by default; require the `task-budgets-2026-03-13` beta header so spend is hard-capped server-side.
- **When changing the scorecard shape**, bump the schema version under `schemas/` and update the stability contract — never silently mutate `scorecard.v1.schema.json`.
- **Disposition discipline**: record REJECT-of-record outcomes as their own chore PR (see PRs #30–#33) so the decision is auditable later.

<!-- END AUTO-MANAGED -->

<!-- MANUAL -->
## Custom Notes

Add project-specific notes here. This section is never auto-modified.

<!-- END MANUAL -->
