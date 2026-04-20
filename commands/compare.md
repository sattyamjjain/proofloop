---
name: compare
description: "Compare two Verdict scorecards of the same skill with a narrative overlay"
usage: "/compare --run-a <path> --run-b <path> [--format text|json]"
---

# /compare — Narrative Delta Between Two Runs

Thin wrapper over `skills/judge/scripts/compare.py`. Takes two
scorecard JSON paths, renders the per-dimension delta table, and
prints a narrative callout flagging Auto Memory-style regressions:

- composite dropped beyond the configured threshold,
- transcript grew enough to suggest memory pollution,
- consistency dimension slid,
- any single dimension lost ≥ 3 points.

## Arguments

- `--run-a <path>` (required): baseline scorecard JSON.
- `--run-b <path>` (required): target scorecard JSON.
- `--format text|json` (optional, default `text`): rendering.

## What to do

1. Invoke the CLI:

   ```shell
   python3 skills/judge/scripts/compare.py \
     --run-a skills/judge/scores/<baseline>.json \
     --run-b skills/judge/scores/<target>.json
   ```

2. Output shape (text):

   ```
   ╭──────────────────────────────────────────────────────╮
   │ /judge --compare-runs · code-review vs code-review   │
   ╰──────────────────────────────────────────────────────╯
   run A: 2026-04-15T12:00:00Z  composite 8.42 / A-
   run B: 2026-04-20T12:00:00Z  composite 7.85 / B

   dimension           A     B     Δ
   ─────────────────────────────────────
   correctness         9     8    -1
   completeness        8     8     0
   adherence           9     7    -2
   actionability       8     8     0
   efficiency          8     7    -1
   safety             10    10     0
   consistency         8     5    -3
   ─────────────────────────────────────

   narrative:
     - composite dropped -0.57 (8.42 → 7.85) — regression threshold -0.30
     - memory block grew ~4k → ~32k bytes — likely memory pollution
     - consistency slid 8 → 5 (-3) — suggests the skill is drifting
     - hard regressions: consistency 8 → 5 (-3)
   ```

3. Exit semantics:
   - Exit 0 — composite improved, flat, or regressed less than 0.3.
   - Exit 1 — either scorecard file is missing or malformed.
   - Exit 2 — composite regressed beyond the threshold. CI gate.

## Relationship to other commands

- `/scorecard` — single-run view.
- `/against` — position-based time-series diff (`HEAD~1` = penultimate).
- `/compare` — **explicit two-file diff**, geared at Auto Memory
  regression detection. Use this when you know exactly which runs to
  compare.
