# Verdict regression-gate corpus

This directory holds the curated transcript corpus that
[`scripts/benchmark_pack.py`](../scripts/benchmark_pack.py) replays
against `score.py` on every CI run. Each case in `manifest.json`
asserts a per-dimension bound or composite floor; the gate fails
if heuristic drift causes any case to regress.

## Scope

Per the [v4.3 scope contract](../CLAUDE.md#v43-scope-contract-2026-05-03),
this is the **regression-gate fixture set for Verdict's heuristic
engine**. It is **NOT a public eval bench:**

- We do not advertise Verdict's leaderboard standing.
- We do not accept SWE-bench, Terminal-Bench, GAIA, OSWorld, or
  similar agent-bench submissions.
- The fixtures are not curated for cross-tool benchmarking — they
  exist to detect drift in the seven-dimension scorer.

If you are looking for an eval bench, run the upstream tool that
authored the bench and post results there. If you are looking to
extend Verdict's plugin-scope heuristics, add a case here that
exercises the dimension you are changing and ensure
`benchmark_pack.py` stays green.

## Adding a case

1. Drop a transcript file under `corpus/` (use the smallest
   illustrative shape — these are not training data, just heuristic
   probes).
2. Add a `cases[]` entry to `manifest.json` with one of:
   - `expected_grade_min` / `expected_composite_min` — for cases
     that should pass.
   - `expected_dimension_max` — for cases that should dock a
     specific dimension and stay below the cap.
3. Run `python3 scripts/benchmark_pack.py` and confirm the new
   case passes.
4. Open a PR; CI re-runs the gate.
