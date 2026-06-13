---
name: judge-config
description: "View and manage Proofloop auto-judge configuration"
usage: "/judge-config [subcommand] [args]"
---

# /judge-config — Manage Auto-Judge Settings

View and modify the Proofloop configuration.

## Subcommands

- `/judge-config` — View current configuration (pretty-printed)
- `/judge-config add-always SKILL` — Add a skill to the auto-judge "always" list
- `/judge-config add-never SKILL` — Add a skill to the auto-judge "never" list
- `/judge-config remove SKILL` — Remove a skill from both always and never lists
- `/judge-config threshold N` — Set the blocking threshold (0.0-10.0)
- `/judge-config enable` — Enable auto-judging
- `/judge-config disable` — Disable auto-judging

## What to Do

1. Read `judge-config.json` from the project root
2. If no subcommand: display the full config in a readable format:

```
Proofloop Configuration
========================
Auto-Judge: ENABLED
Threshold: 5.0 (skills scoring below this are BLOCKED)

Always Auto-Judge:
  - code-review
  - security-scan
  - feature-dev
  - debugging
  - codebase-analyzer
  - webapp-testing

Never Auto-Judge:
  - format
  - commit
  - fix-imports
  - undo
  - fix-todos
  - remove-comments
  - docs
  - session-start
  - session-end

Manual-Only (not in either list):
  → Everything else requires /judge for evaluation

Scoring Weights (global — per-rubric overrides apply when a
`<rubric>.weights.json` sidecar exists):
  Correctness:   25%
  Completeness:  20%
  Adherence:     15%
  Actionability: 15%
  Efficiency:    10%
  Safety:        10%
  Consistency:    5%

Tokenizer Baselines (efficiency length-threshold multipliers):
  default:            1.0
  claude-opus-4-7:    1.35
  claude-sonnet-4-6:  1.0
  claude-haiku-4-5:   1.0
```

3. If subcommand provided: modify judge-config.json accordingly
   - Validate inputs (threshold must be 0-10, skill names must be valid)
   - Remove from conflicting lists when adding (e.g., adding to "always" removes from "never")
   - Confirm the change to the user

## Weight validation

When the user edits `scoring.dimensions` directly, Proofloop enforces the
weight-sum-to-1.0 invariant at load time. Non-conforming configs are
rejected with a stderr warning and the scorer falls back to default
weights instead of silently producing inflated composites. Run
`python3 skills/judge/scripts/score.py --config judge-config.json ...`
once after an edit to confirm the warning doesn't fire.

## Per-rubric overrides

To weight a specific rubric differently from the global config, drop
a sibling `<rubric>.weights.json` next to `<rubric>.md`:

```json
{
  "correctness": 0.20,
  "completeness": 0.15,
  "adherence": 0.10,
  "actionability": 0.10,
  "efficiency": 0.05,
  "safety": 0.35,
  "consistency": 0.05
}
```

Sum must equal 1.0 (±1e-6). Shipped example:
`skills/judge/rubrics/security.weights.json`.

