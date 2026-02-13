---
name: judge-config
description: "View and manage Verdict auto-judge configuration"
usage: "/judge-config [subcommand] [args]"
---

# /judge-config — Manage Auto-Judge Settings

View and modify the Verdict configuration.

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
Verdict Configuration
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

Scoring Weights:
  Correctness:   25%
  Completeness:  20%
  Adherence:     15%
  Actionability: 15%
  Efficiency:    10%
  Safety:        10%
  Consistency:    5%
```

3. If subcommand provided: modify judge-config.json accordingly
   - Validate inputs (threshold must be 0-10, skill names must be valid)
   - Remove from conflicting lists when adding (e.g., adding to "always" removes from "never")
   - Confirm the change to the user
