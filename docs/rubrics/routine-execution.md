# `routine-execution` rubric

Tuned for autonomous Claude Code runs triggered by Anthropic
Routines (research preview).

> ℹ️ Anthropic Routines is **research preview** as of 2026-04-29,
> not GA. The rubric reflects that.

## When to use

- You schedule a Routine via cron / API / GitHub webhook and want
  to score the resulting transcript.
- You run nightly triage / housekeeping routines and want
  consistency tracking that doesn't false-flag cron-pattern
  variance.

## Differences from `default`

- **Completeness 0.25** (vs. 0.20) — autonomous runs need to
  finish their goal in one cycle.
- **Consistency 0.10** (vs. 0.05) — step-determinism across cycles
  is load-bearing.
- Human-in-loop is dropped from Actionability (not applicable).
- Adherence (observability) up to 0.15 — on-call needs structured
  logs to debug stuck cycles.

## Trajectory marker

The Verdict claude-code adapter prepends `[trajectory_kind:
routine]` when it detects a Routines-style transcript. Two
detection signals (CC4):

1. **Explicit** — any line carries `[routine_trigger: <id>]`. Always
   honored.
2. **Heuristic** — no human turn in the first 5 lines. Gated by
   `VERDICT_DETECT_ROUTINE_HEURISTIC=1` to avoid false-flagging
   multi-line interactive paste-ins. See Issue O15.

When the sentinel is present, the consistency analyzer relaxes
its std_dev tolerance buckets by ~33% (cron-triggered runs
naturally cluster differently from interactive ones).

## Per-tier daily run caps

Anthropic enforces:

- Pro: 5 runs/day
- Max: 15 runs/day
- Team / Enterprise: 25 runs/day

Cron expressions tighter than once-per-hour are rejected by
Anthropic. Verdict surfaces these caps as informational warnings
but doesn't deduct (the cap is enforced platform-side).

## Issue O15

The heuristic branch ("no human turn in first 5 lines") is opt-in
in v1.4.2 because the false-positive rate is unknown until we
sample real Routines transcripts. v1.4.3 promotes it to default
after sample-set evaluation.

## Sources

- [anthropic.com/news/routines](https://www.anthropic.com/news/routines)
- [code.claude.com/docs/en/routines](https://code.claude.com/docs/en/routines)
