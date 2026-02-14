# Verdict

**The first universal judge for Claude Code & Cowork.** Auto-evaluates skill and agent execution quality with 7-dimension scoring, configurable rubrics, and dual-mode operation.

---

## Features

- **Dual-Mode Operation** -- Runs automatically via hooks after every skill/agent execution, or on-demand with the `/judge` command.
- **Dual-Platform** -- Works on both Claude Code and Claude Cowork.
- **7-Dimension Scoring** -- Every execution is scored across correctness, completeness, adherence, actionability, efficiency, safety, and consistency.
- **Configurable Rubrics** -- Ship with sensible defaults; override per-skill or per-team with custom rubric files.
- **Persistent Scorecards** -- All scores are saved to `skills/judge/scores/` as JSON for historical tracking and benchmarking.
- **Blocking on Critical Failures** -- Optionally block workflow when a score falls below the configured threshold.

## Requirements

- **Python 3.9+** -- Used by the scoring engine (stdlib only, no pip packages needed)
- **jq** -- JSON parsing in hook scripts (`brew install jq` / `apt-get install jq`)
- **bc** -- Float comparison in hook scripts (`brew install bc` / `apt-get install bc`)

## Quick Start

### Install

**Option A: From the official Claude Plugin Directory** (once listed)
```bash
/plugin install verdict
```

**Option B: Direct from GitHub**
```bash
/plugin marketplace add sattyamjjain/verdict
/plugin install verdict@verdict
```

### Configure

Edit `judge-config.json` at the project root to control auto-judge behavior, scoring weights, and defaults.

### Use

**Automatic mode** -- After installing, every skill or agent execution that matches the `auto_judge.always` list is evaluated automatically. No action required.

**Manual mode** -- Run the `/judge` slash command to evaluate any prior execution on demand:

```
/judge                  # Judge the last execution
/judge --rubric strict  # Use a specific rubric
/scorecard              # View cumulative scores
/benchmark              # Run benchmark suite
/judge-config           # View or update configuration
```

## Architecture

```
.claude-plugin/
  plugin.json             # Plugin manifest
  marketplace.json        # Marketplace listing metadata
skills/judge/
  SKILL.md                # Core skill definition
  scripts/                # Python scoring engine and utilities
  rubrics/                # Rubric definitions (default, code-review, security, etc.)
  scores/                 # Persisted score JSON files
  references/             # Benchmark standards and scoring methodology
agents/
  judge-agent.md          # Autonomous judge agent definition
hooks/
  hooks.json              # Hook definitions for auto-judge
  judge-on-stop.sh        # Stop hook script
  judge-on-subagent-stop.sh # SubagentStop hook script
  common.sh               # Shared hook utilities
commands/
  judge.md                # /judge command
  scorecard.md            # /scorecard command
  benchmark.md            # /benchmark command
  judge-config.md         # /judge-config command
judge-config.json         # Root configuration file
LICENSE                   # MIT license
CHANGELOG.md              # Version history
```

## Scoring System

Each execution is scored on 7 weighted dimensions (total weight = 1.0):

| Dimension       | Weight | Description                                      |
|-----------------|--------|--------------------------------------------------|
| Correctness     | 0.25   | Does the output match expected behavior?         |
| Completeness    | 0.20   | Were all requested tasks addressed?              |
| Adherence       | 0.15   | Does it follow the skill/agent instructions?     |
| Actionability   | 0.15   | Are the results directly usable?                 |
| Efficiency      | 0.10   | Was the work done without unnecessary steps?     |
| Safety          | 0.10   | Are there security or correctness risks?         |
| Consistency     | 0.05   | Is the output consistent with prior executions?  |

The **weighted composite score** is computed as the dot product of dimension scores (each 0--10) and their weights, yielding a final score on a 0--10 scale.

### Verdict Grades

| Score Range  | Grade |
|--------------|-------|
| 9.5 -- 10.0  | A+    |
| 9.0 -- 9.4   | A     |
| 8.5 -- 8.9   | A-    |
| 8.0 -- 8.4   | B+    |
| 7.5 -- 7.9   | B     |
| 7.0 -- 7.4   | B-    |
| 6.5 -- 6.9   | C+    |
| 6.0 -- 6.4   | C     |
| 5.5 -- 5.9   | C-    |
| 4.0 -- 5.4   | D     |
| 0.0 -- 3.9   | F     |

## Configuration Reference

All configuration lives in `judge-config.json`:

### `auto_judge`

| Key                | Type     | Description                                                    |
|--------------------|----------|----------------------------------------------------------------|
| `enabled`          | boolean  | Master switch for automatic judging.                           |
| `always`           | string[] | Skill names that are always auto-judged.                       |
| `never`            | string[] | Skill names that are never auto-judged.                        |
| `threshold`        | number   | Minimum composite score to pass (0--10).                       |
| `block_on_critical`| boolean  | If true, block workflow when score is below threshold.         |

### `manual_judge`

| Key              | Type    | Description                                      |
|------------------|---------|--------------------------------------------------|
| `default_rubric` | string  | Name of the default rubric file to use.          |
| `verbose`        | boolean | Show detailed per-dimension breakdown.           |
| `save_scores`    | boolean | Persist scores to disk.                          |

### `scoring.dimensions`

A map of dimension name to weight (float). Weights must sum to 1.0.

## License

MIT -- see [LICENSE](LICENSE) for details.
