# GPT-5.5 Differential Rubric

<!--
source_signal: https://www.cnbc.com/2026/04/23/openai-announces-latest-artificial-intelligence-model.html
context:    OpenAI's GPT-5.5 launch (2026-04-23) claimed
            improvements in code tasks and computer use against the
            GPT-5 baseline. Vendor benchmark numbers are vendor
            benchmark numbers — adopters need their own
            paired-comparison runs against their own task surface.
            This rubric scores the *delta* between two scorecards:
            a baseline (GPT-5) and a candidate (GPT-5.5) on the
            same skill/task.
status:     Stable. Not GPT-5.5-exclusive — works for any pairwise
            model comparison; the name is a launch-window signal.
-->

## Overview

Pairwise differential rubric. Consumes **two** scorecards:

- *baseline* — a prior run against the GPT-5 model (or whatever
  comparator you control)
- *candidate* — the new run against GPT-5.5 (or the proposed
  upgrade)

The rubric's seven canonical dimensions are framed as deltas
(`candidate - baseline`):

| Concern                                | Verdict dimension |
| -------------------------------------- | ----------------- |
| Code-task improvement delta            | Correctness       |
| Computer-use improvement delta         | Completeness      |
| Hallucination-rate delta (negative=better) | Adherence     |
| Refusal-rate delta                     | Actionability     |
| Latency / cost-per-task delta normalized | Efficiency      |
| Regression on prior strengths (negative=failure) | Safety  |
| Run-to-run consistency on candidate    | Consistency       |

Weights lean onto **Correctness (0.25)** + **Safety (0.20)** —
the load-bearing question is "did the upgrade improve the thing
adopters were already happy with, *without* regressing on what
already worked?"

## Pairwise comparison helper

When the active rubric is `gpt-5-5-differential`, the scorer
expects a `--baseline-scorecard PATH` flag pointing at the GPT-5
prior scorecard. The `_resolve_paired_baseline()` helper computes:

- Per-dimension delta (`candidate.score - baseline.score`)
- Cohen's d effect size (`mean_delta / pooled_stddev`) when
  multiple historical scorecards are present
- A regression flag (`true` when any dimension drops by ≥ 1.5
  points)

These are surfaced in the scorecard under
`adjustments.paired_baseline`.

The rubric's dimension scores remain on the canonical 1-10 scale —
the delta interpretation is layered *on top* via the adjustments
block, not by changing the scale. A maintainer who runs both
GPT-5 and GPT-5.5 on the same task gets two complete scorecards
plus a delta summary.

## How to use

1. Score the baseline run normally (pick whatever rubric matches
   the task — `code-review`, `swe-bench-pro`, etc.).
2. Score the candidate run with the same task rubric, **also**
   passing `--paired-baseline <baseline.json>`.
3. The candidate scorecard's `adjustments.paired_baseline` block
   tells you whether GPT-5.5 actually moved the needle on *your*
   task surface.

This rubric does **not** require a new adapter — it uses any
existing transcript adapter and operates purely on the resulting
scorecard JSON.

## Dimension Criteria

### Correctness (Weight: 25%)
**Concern:** code-task improvement delta.

| Score | Criteria |
|-------|----------|
| 9-10  | Candidate scores +1.0 or more on Correctness vs baseline; no regression on adjacent dimensions. |
| 7-8   | Candidate up by +0.5 to +1.0. |
| 5-6   | Candidate flat (within ±0.5). |
| 3-4   | Candidate down 0.5–1.5. |
| 1-2   | Candidate down by more than 1.5 — clear code-task regression. |

### Completeness (Weight: 15%)
**Concern:** computer-use / multi-tool improvement delta.

| Score | Criteria |
|-------|----------|
| 9-10  | Candidate completes more sub-tasks per turn than baseline. |
| 7-8   | One additional sub-task per turn. |
| 5-6   | Same coverage. |
| 3-4   | Candidate skips a sub-task baseline completed. |
| 1-2   | Candidate fails at coordination tasks baseline handled. |

### Adherence (Weight: 15%)
**Concern:** hallucination-rate delta (negative is better).

| Score | Criteria |
|-------|----------|
| 9-10  | Hallucination-pattern hit count drops by 50% or more vs baseline. |
| 7-8   | Drops 25%–50%. |
| 5-6   | Within ±25%. |
| 3-4   | Up 25%–50% (worse). |
| 1-2   | Hallucination rate doubles or more. |

### Actionability (Weight: 10%)
**Concern:** refusal-rate delta. Over-refusal is a real
regression class.

| Score | Criteria |
|-------|----------|
| 9-10  | Candidate refuses fewer legitimate tasks than baseline (or rates equal and both low). |
| 7-8   | Refusal rate rises slightly but every refusal carries a rationale. |
| 5-6   | Refusal rate up; one questionable refusal. |
| 3-4   | Multiple refusals on previously-handled task classes. |
| 1-2   | Refusal rate doubles. |

### Efficiency (Weight: 10%)
**Concern:** latency-delta-normalised + cost-per-task delta.

| Score | Criteria |
|-------|----------|
| 9-10  | Latency and cost both improve or stay flat. |
| 7-8   | One improves, other flat. |
| 5-6   | Both flat. |
| 3-4   | One regresses materially. |
| 1-2   | Both regress materially. |

### Safety (Weight: 20%)
**Concern:** regression on prior strengths. Did the upgrade
break something that already worked?

| Score | Criteria |
|-------|----------|
| 9-10  | No dimension regresses by more than 0.5; previously-strong areas (≥ 8/10) hold. |
| 7-8   | One dimension regresses 0.5–1.0; previously-strong areas hold. |
| 5-6   | One dimension regresses 1.0–1.5. |
| 3-4   | Multiple dimensions regress by 1.0+. |
| 1-2   | Hard regression: a previously-9 dimension drops by ≥ 2.0. |

### Consistency (Weight: 5%)
**Concern:** run-to-run variance on the candidate. New model;
new variance signature?

| Score | Criteria |
|-------|----------|
| 9-10  | Candidate's variance ≤ baseline's variance. |
| 7-8   | Within 10% wider. |
| 5-6   | 10–25% wider. |
| 3-4   | 25–50% wider. |
| 1-2   | Variance doubles. |

## Red Flags

- Any dimension that was ≥ 9.0 on baseline drops to ≤ 6.0 on
  candidate → caps Safety at ≤ 2.0.
- Hallucination rate doubles → caps Adherence at ≤ 2.0.

## Domain Bonuses

- +0.5 for an explicit prior-strength preservation note in the
  candidate's first turn (acknowledges the baseline's wins).
- +0.5 for documenting the test-task parity (same fixtures,
  same prompts, same context window).
