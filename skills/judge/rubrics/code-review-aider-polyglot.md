# Aider-Polyglot Code Review Rubric

<!--
source_signal: https://aider.chat/docs/leaderboards/ (Apr 2026)
context:   Aider Polyglot ranked Opus 4.5 @ 89.4%, GPT-5 @ 88.0%,
           Opus 4.7 @ 87.6% on SWE-Bench-flavoured multi-file edits.
           Verdict rides that wave with a rubric tuned to the
           axes Aider's benchmark actually measures, expressed
           against Verdict's canonical seven dimensions.
-->

## Overview

Evaluates code-review / code-edit skill outputs on the axes the
Aider polyglot benchmark actually measures: did the edit apply
cleanly, did it stay scoped, did it keep multiple files coherent,
and did it follow the instruction literally?

Each of Aider's concerns maps onto one of Verdict's seven canonical
dimensions so the scorecard stays comparable with other rubrics:

| Aider concern           | Verdict dimension |
| ----------------------- | ----------------- |
| Syntactic/semantic edit | Correctness       |
| Multi-file coherence    | Completeness      |
| Instruction-follow      | Adherence         |
| Applies cleanly         | Actionability     |
| Diff compaction         | Efficiency        |
| Destructive patterns    | Safety            |
| Run-to-run stability    | Consistency       |

Weights shift onto **Adherence** and **Actionability** because
Aider-style tasks reward literal instruction follow-through and
compilable output over prose elegance. Override with a
`code-review-aider-polyglot.weights.json` sidecar if your repo shape
prefers different weighting (e.g. bump Safety for infra monorepos).

## Dimension Criteria

### Correctness (Weight: 20%)
**Aider concern:** syntactic correctness of the emitted edit +
semantic correctness of the intended change. If the diff wouldn't
apply, this is where the signal lands.

| Score | Criteria |
|-------|----------|
| 9-10  | Every edit applies cleanly. Resulting tree passes `py_compile` / `tsc --noEmit` / equivalent. No logic regressions in the touched functions. |
| 7-8   | Edits apply. One trivial post-edit fix needed (missing import, unused var) but no semantic regression. |
| 5-6   | Most edits apply; at least one has a fuzz-mismatch or missed-context SEARCH block. Compilation breaks in one file. |
| 3-4   | Multiple edits don't apply. Logic errors visible in the diff without running the code. |
| 1-2   | Diff is not syntactically valid. Search blocks don't match the source. |

### Completeness (Weight: 15%)
**Aider concern:** multi-file coherence. When a change spans multiple
files, do the edits agree? A renamed symbol must be renamed
everywhere; a new function must be called in every caller that was
supposed to use it.

| Score | Criteria |
|-------|----------|
| 9-10  | All call sites updated. Cross-file invariants (type signatures, exported names, API contracts) hold. |
| 7-8   | One or two callers missed but the change is trivial to complete. |
| 5-6   | Multiple call sites out of sync. Tests would fail. |
| 3-4   | Symbols renamed only in definition; callers left pointing at the old name. |
| 1-2   | Each file edited in isolation with no awareness of the others. |

### Adherence (Weight: 20%)
**Aider concern:** instruction-follow + edit locality. Did the skill
do literally what was asked, without opportunistic "while I was here"
drift? Aider tasks are tightly specified (`replace foo with bar`, `add
a guard clause`) and the benchmark is brutal on deviation.

| Score | Criteria |
|-------|----------|
| 9-10  | Output mirrors the instruction one-for-one. Diff touches only lines directly required by the prompt. No opportunistic rewrites, no import reshuffles. |
| 7-8   | The ask is fulfilled with 1-2 minor drifts (import reorder, small helper rename) that don't change behaviour. |
| 5-6   | Skill partly pushed back on the instruction or did a slightly different variant. Some drift into untouched code. |
| 3-4   | Skill paired the asked change with an unprompted refactor, or touched files not mentioned in the prompt. |
| 1-2   | Skill declined, substituted its own preferred approach, or refactored across the repo. |

### Actionability (Weight: 15%)
**Aider concern:** can the diff be applied and committed without
manual touch-ups?

| Score | Criteria |
|-------|----------|
| 9-10  | `git apply` (or Aider auto-apply) succeeds; tests run; no placeholders. |
| 7-8   | One post-apply touch-up needed (add an import, rename a var). |
| 5-6   | Apply succeeds but output needs formatting / lint fixes. |
| 3-4   | Apply partly fails; reviewer has to reconstruct several hunks. |
| 1-2   | Output isn't applicable as-is; needs full manual rewrite. |

### Efficiency (Weight: 15%)
**Aider concern:** diff compaction. Is the diff minimal for the
change being made? Aider SEARCH/REPLACE blocks reward surgical
precision; this dimension captures that.

| Score | Criteria |
|-------|----------|
| 9-10  | Every hunk is the minimum line set required. No redundant context, no whole-function rewrites when two lines would do. |
| 7-8   | Diff is compact with 1-2 hunks that over-quote context lines. |
| 5-6   | Several hunks replace entire functions when only a few lines needed to change. |
| 3-4   | Most hunks rewrite whole files to change a few lines. |
| 1-2   | The output is "here's the new file" for everything touched. |

### Safety (Weight: 10%)
**Aider concern:** destructive patterns buried in the edits. Aider
tasks rarely touch deploy scripts, so this weight stays modest —
bump it to 0.20-0.25 for infra repos.

| Score | Criteria |
|-------|----------|
| 9-10  | No destructive patterns. |
| 7-8   | One low-severity warning (e.g. `--force` in a suggested git command). |
| 5-6   | Multiple mild warnings. |
| 3-4   | Destructive shell command embedded in the edit. |
| 1-2   | Edit would execute `rm -rf` on apply or leak credentials into source. |

### Consistency (Weight: 5%)
**Aider concern:** run-to-run stability. Variance against prior
scores for the same skill — do edits on similar tasks land at
similar quality, or does the skill behave unpredictably?

| Score | Criteria |
|-------|----------|
| 9-10  | Low historical variance; this run lands in-line with the median. |
| 7-8   | Minor variance. |
| 5-6   | Visible drift from the skill's usual quality band. |
| 3-4   | Large negative drift. |
| 1-2   | This run is an outlier; prior runs were materially better. |

## Red Flags

- Aider SEARCH block does not match the source → diff is unappliable.
- Claim of having tested changes without a visible tool call to run tests.
- Silent renames across files with no follow-up sweep.

## Domain Bonuses

- +0.5 for including a minimal reproducer when fixing a reported bug.
- +0.5 for explicitly noting and skipping an adjacent issue rather
  than fixing it silently.
