# `verdict bench gaming-check` CLI (T2)

Pre-publication benchmark-gaming linter. Wraps CC3's Berkeley RDI
exploit-signature detector for benchmark publishers / paper
authors / leaderboard ops.

## Why

[Berkeley RDI's audit](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/)
of eight major agent benchmarks (SWE-bench, WebArena, OSWorld,
GAIA, Terminal-Bench, FieldWorkArena, CAR-bench) showed every
single one can be exploited to near-perfect scores without
solving a task. Their automated scanning agent achieved 100%
(89/89) on SWE-bench without writing a line of solution code.

Anyone publishing a benchmark number is a citation-risk if their
trajectory matches a published exploit signature.

## Usage

```shell
python3 skills/judge/scripts/bench_gaming_check.py \
    --transcript path/to/run.jsonl \
    --benchmark swe-bench-pro \
    --strict
```

## Modes

- **default** — scan against the published Berkeley RDI signatures
  for the named benchmark.
- **`--strict`** — also fail on suspiciously short trajectories
  (default 3 reasoning turns; configurable via
  `--strict-min-turns`).

## Signature pack

Default pack lives at
`skills/judge/scripts/signatures/berkeley-rdi-2026-04-26.json`.
Override via `--signature-pack <name>` (resolved under the same
`signatures/` directory). v1.4.3 will add `--signatures-from
<url>` for refresh-without-release. See Issue O14.

## Exit codes

- `0` — clean. No exploit signatures matched.
- `1` — at least one signature tripped (or, with `--strict`, the
  trajectory was too short).
- `2` — bad input.

## Output

`text` (default) lists each finding's class, confidence, and
evidence span. `--output json` emits the same payload as JSON.
