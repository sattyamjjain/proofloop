---
name: scorecard
description: "View score history and trends for skills"
usage: "/scorecard [skill-name] [--last N] [--all]"
---

# /scorecard — Score History & Trends

Display historical scores for skills that have been evaluated by Verdict.

## Arguments

- `skill-name` (optional): Filter to a specific skill. If omitted, show all skills.
- `--last N` (optional): Show only the last N evaluations. Default: 10.
- `--all` (optional): Show all evaluations regardless of limit.

## What to Do

1. Read score files from `skills/judge/scores/` directory
2. Parse each JSON score file
3. Filter by skill name if provided
4. Sort by timestamp (newest first)
5. Limit to last N if specified
6. Display formatted table:

```
┌─────────────────────────────────────────────────────────────┐
│  VERDICT SCORE HISTORY                                   │
├──────────────┬───────┬───────┬────────────┬────────────────┤
│ Skill        │ Score │ Grade │ Date       │ Trend          │
├──────────────┼───────┼───────┼────────────┼────────────────┤
│ code-review  │ 8.2   │ B+    │ 2026-02-13 │ ↑ (+0.4)       │
│ code-review  │ 7.8   │ B     │ 2026-02-12 │ → (+0.0)       │
│ security-scan│ 9.1   │ A     │ 2026-02-13 │ ↑ (+0.6)       │
├──────────────┼───────┼───────┼────────────┼────────────────┤
│ AVERAGES     │ 8.37  │ B+    │            │                │
└──────────────┴───────┴───────┴────────────┴────────────────┘
```

7. Calculate trends:
   - Compare each score to the previous score for the same skill
   - ↑ = improved by 0.3+
   - ↓ = declined by 0.3+
   - → = stable (within 0.3)

8. Show averages per skill and overall

If no scores exist yet, inform the user: "No scores found. Run `/judge` after a skill execution to start building history."

## Related commands

- `/against` — side-by-side delta between two specific runs of the same skill.
- `/benchmark` — delta between a skill's historical average and the reference standards in `skills/judge/references/benchmark-standards.md`.
- `python3 skills/judge/scripts/studio.py --scores-dir skills/judge/scores --output verdict-studio.html` — self-contained HTML dashboard with per-skill radar charts.

