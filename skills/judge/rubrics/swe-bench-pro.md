# SWE-bench Pro Rubric

<!--
source_signal: https://llm-stats.com/benchmarks/swe-bench-pro (Apr 2026)
context:   SWE-bench Pro is the contamination-resistant successor to
           SWE-bench Verified — same shape (repo-scoped issue → patch),
           harder distribution (tighter locality, longer traces,
           private splits). On the 2026-Q2 leaderboard Opus 4.7 scores
           64.3% on Pro vs 87.6% on Verified, a gap consistent with
           Pro's design goal of resisting training-data leakage.
           Verdict rides that wave with a rubric that rewards
           instruction-literal edits on unfamiliar repos and deducts
           composite when a transcript references the Verified split.
-->

## Overview

Evaluates code-edit skill outputs against SWE-bench Pro's stricter
requirements: no cross-file drift, no speculative refactors, and —
critically — no leaning on the Verified split's publicly-indexed
issue IDs. Pro's private evaluation set is the whole point; a skill
that "solves" a Pro issue by pattern-matching a Verified problem
instance should lose credit.

## Source-signal mapping

| SWE-bench Pro concern             | Verdict dimension |
| --------------------------------- | ----------------- |
| Patch applies & tests pass        | Correctness       |
| Cross-file invariants preserved   | Completeness      |
| Follows the issue literally       | Adherence         |
| Diff is reviewable in one pass    | Actionability     |
| Minimal diff for the fix          | Efficiency        |
| No destructive or leakage patterns| Safety            |
| Stable across repeated attempts   | Consistency       |

Weights lean onto **Correctness** (test-pass is the Pro leaderboard's
primary signal) and **Adherence** (instruction-literal edits are what
distinguish Pro winners from Verified-leakers) via the
`swe-bench-pro.weights.json` sidecar.

## Contamination penalty

On top of the weighted composite, Verdict applies a contamination
deduction of up to **1.5 points** when the transcript references
SWE-bench **Verified** instance IDs (e.g. `django__django-12345`) or
the literal string `SWE-bench Verified`. This catches the most common
cheating pattern — a skill that recognises a Pro task as a
near-duplicate of a Verified task and copies the Verified patch. The
deduction is additive to any red-flag deductions and capped so a
thoughtful citation of Verified in a rationale doesn't wipe a whole
scorecard.

The contamination signal only fires when the active rubric is
`swe-bench-pro`; other rubrics may cite Verified literals (e.g. a
benchmarking write-up) without penalty.

## Dimension Criteria

### Correctness (Weight: 35%)
**Pro concern:** does the patch apply cleanly and does the hidden
test suite go green?

| Score | Criteria |
|-------|----------|
| 9-10  | Patch applies; all hidden tests pass; no regressions in existing suite. |
| 7-8   | Patch applies; one hidden test flakes or requires a trivial re-run. |
| 5-6   | Patch applies; a visible fraction of hidden tests fail but the direction is right. |
| 3-4   | Patch applies but the fix target is wrong; most hidden tests fail. |
| 1-2   | Patch does not apply, or applies and breaks unrelated tests in the existing suite. |

### Completeness (Weight: 10%)
**Pro concern:** cross-file coherence. Pro tasks often span a
feature module plus its test file plus a migration; a complete patch
updates all three.

| Score | Criteria |
|-------|----------|
| 9-10  | Every call site / test / migration that follows from the fix is updated. |
| 7-8   | One or two follow-ups missed but trivial to complete. |
| 5-6   | Implementation file updated; tests or migrations left stale. |
| 3-4   | Multiple files out of sync after the patch. |
| 1-2   | Each file edited in isolation; cross-file invariants broken. |

### Adherence (Weight: 30%)
**Pro concern:** follow the issue literally, without opportunistic
refactors. Pro's difficulty comes from the issues being narrow; a
skill that broadens scope almost always drifts off-target.

| Score | Criteria |
|-------|----------|
| 9-10  | Patch addresses exactly what the issue asks for, touching only the files the issue names. No while-I'm-here cleanups. |
| 7-8   | Minor drift (import reorder, whitespace) that doesn't change behaviour. |
| 5-6   | Patch partly re-scopes the problem or fixes an adjacent issue silently. |
| 3-4   | Patch bundles an unprompted refactor with the asked change. |
| 1-2   | Skill rewrote the problem or refactored files the issue never named. |

### Actionability (Weight: 10%)
**Pro concern:** reviewer-minute efficiency. Can a maintainer land
the patch without asking follow-up questions?

| Score | Criteria |
|-------|----------|
| 9-10  | Every hunk is self-explanatory; no placeholders or TODOs. |
| 7-8   | One hunk needs a one-line clarification. |
| 5-6   | Several hunks need inline explanation before a reviewer can act. |
| 3-4   | Patch contains TODOs, placeholders, or "fill this in" markers. |
| 1-2   | Output is a plan of attack, not an applicable patch. |

### Efficiency (Weight: 5%)
**Pro concern:** diff compaction. Did the skill change only the
lines it had to?

| Score | Criteria |
|-------|----------|
| 9-10  | Minimal diff. Every hunk is load-bearing. |
| 7-8   | Compact diff with 1-2 hunks that over-quote context. |
| 5-6   | Multiple hunks rewrite whole functions when a few lines would do. |
| 3-4   | Most of the diff is drive-by reformatting. |
| 1-2   | Whole-file rewrites for every edit. |

### Safety (Weight: 5%)
**Pro concern:** destructive or leakage patterns smuggled into a
patch. Pro's scoring is binary (pass/fail), but a patch that drops
a table or prints a secret should still cost the skill composite.

| Score | Criteria |
|-------|----------|
| 9-10  | No destructive patterns; no secrets in source. |
| 7-8   | One low-severity warning (e.g. `--force` in a shell snippet). |
| 5-6   | Multiple mild warnings. |
| 3-4   | Destructive shell command embedded in the patch. |
| 1-2   | Patch would execute `rm -rf` on apply or leak credentials into source. |

### Consistency (Weight: 5%)
**Pro concern:** run-to-run stability on similar tasks. Pro publishes
pass@k, not pass@1; variance is a real signal.

| Score | Criteria |
|-------|----------|
| 9-10  | Low historical variance; this run lands in-line with the skill's median. |
| 7-8   | Minor variance. |
| 5-6   | Visible drift from the skill's usual quality band. |
| 3-4   | Large negative drift. |
| 1-2   | This run is an outlier; prior runs were materially better. |

## Red Flags

- Patch claims to have run the hidden test suite with no visible test
  invocation in the transcript.
- Any reference to the SWE-bench Verified split (contamination
  penalty fires).
- Silent renames across files with no follow-up sweep.
- Patch mixes an unrelated refactor with the asked change.

## Domain Bonuses

- +0.5 for including a failing repro test that flips to passing with
  the patch (tests-first credit).
- +0.5 for explicitly noting an adjacent issue and declining to fix
  it in the same patch.
