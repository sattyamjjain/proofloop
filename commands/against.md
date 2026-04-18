---
name: against
description: "Side-by-side delta between two scorecards of the same skill"
usage: "/against <skill-name> [--baseline-index N] [--target-index N]"
---

# /against — Diff-Aware Score Delta

Renders a Unicode table comparing two scorecards for the same skill
— per-dimension deltas plus a composite verdict (IMPROVED / REGRESSED
/ FLAT). Exits non-zero on composite regression so CI can gate on it.

## Arguments

- `skill-name` (required): Which skill's history to compare.
- `--baseline-index N` (optional, default `-2`): Index into the skill's
  scorecards sorted by timestamp ascending. Negative indices count
  from the end, so `-2` is the penultimate run (one before latest).
- `--target-index N` (optional, default `-1`): Same indexing as the
  baseline. `-1` is the latest run.

## What to Do

1. Invoke the CLI:

   ```shell
   python3 skills/judge/scripts/against.py \
     --skill {skill-name} \
     --scores-dir skills/judge/scores \
     [--baseline-index N] [--target-index N]
   ```

2. The script reads every `{skill-name}_*.json` file from the scores
   directory, sorts by timestamp, selects the two indices, and prints
   a delta table like:

   ```
   ╭────────────────────────────╮
   │ Verdict delta: code-review │
   ╰────────────────────────────╯
   baseline: 2026-04-10T12:00:00Z  composite 7.80/B
   target:   2026-04-18T12:00:00Z  composite 8.60/A-

   dimension        before    after    delta
   ─────────────────────────────────────────────
   correctness          8        9    +1.0 ↑
   completeness         7        8    +1.0 ↑
   adherence            8        9    +1.0 ↑
   actionability        8        8    +0.0 →
   efficiency           7        8    +1.0 ↑
   safety              10       10    +0.0 →
   consistency          5        8    +3.0 ↑
   ─────────────────────────────────────────────
   composite         7.80     8.60   +0.80 ↑

   Verdict: IMPROVED (+0.80)
   ```

3. Exit semantics:
   - Exit 0 — improved or flat (≥ -0.05 composite delta).
   - Exit 1 — fewer than 2 scorecards, or indices out of range.
   - Exit 2 — regression (composite dropped > 0.05). CI gate.

## Examples

```
/against code-review                           # penultimate vs. latest
/against code-review --baseline-index 0        # first-ever vs. latest
/against code-review --baseline-index -5 --target-index -1  # last 5 runs
```

If the skill has fewer than 2 scorecards, inform the user that more
runs are needed before a delta is meaningful.
