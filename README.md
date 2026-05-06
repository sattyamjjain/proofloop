# Verdict

[![CI](https://github.com/sattyamjjain/verdict/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sattyamjjain/verdict/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/sattyamjjain/verdict)](https://github.com/sattyamjjain/verdict/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Auto-grade every Claude Code and Cowork skill execution on seven
dimensions. No LLM call. No config. Just a scorecard.**

Every other evaluation tool in this space (Braintrust, Langfuse,
Phoenix, Helicone, Promptfoo, DeepEval, Ragas, LangSmith, Opik)
requires a second LLM to grade the first. Verdict runs offline regex
heuristics inside the editor. Zero ongoing cost, zero API key, zero
network call — it ships as a Claude Code plugin that fires on every
`Stop` and `SubagentStop` event.

---

## Install

```shell
/plugin marketplace add sattyamjjain/verdict
/plugin install verdict@verdict
```

That's it. The next skill or subagent execution that matches an
`always` entry in `judge-config.json` is scored automatically; the
scorecard JSON lands in `skills/judge/scores/` and `/scorecard`
renders the trend line.

Works on Claude Code and Claude Cowork. For the Cowork plugin-loading
workaround (GH #39400), see [INSTALL-COWORK.md](INSTALL-COWORK.md).

---

## Why Verdict

|                            | Verdict | Braintrust / Langfuse / Phoenix | Promptfoo / DeepEval | LangSmith / Opik |
| -------------------------- | :-----: | :-----------------------------: | :------------------: | :--------------: |
| Runs inside Claude Code    | ✓       | ✗                               | ✗                    | ✗                |
| Offline (no LLM call)      | ✓       | ✗                               | optional             | ✗                |
| Zero config for first score| ✓       | ✗                               | ✗                    | ✗                |
| Per-domain rubrics         | ✓ (11)  | via code                        | via YAML             | via code         |
| Cross-ecosystem transcripts| ✓       | traces only                     | provider-flex        | LangChain-first  |
| Pip install / deps         | stdlib  | SDK + network                   | SDK                  | SDK + account    |
| Per-rubric weight override | ✓       | ✗                               | ✗                    | ✗                |
| Git-diff-aware delta       | ✓       | ✗                               | ✗                    | limited          |

---

## Features

- **Dual-mode operation.** Automatic via hooks (`Stop`,
  `SubagentStop`, `StopFailure`) or manual via `/judge`.
- **Dual-platform.** Claude Code and Claude Cowork.
- **7-dimension weighted scoring.** Correctness, completeness,
  adherence, actionability, efficiency, safety, consistency — weights
  configurable globally or per rubric via a sidecar `.weights.json`.
- **Plugin-scope adapters.** Score transcripts from Claude Code,
  Cowork, Codex, Cursor, Continue, and any OpenAI-compatible JSON
  shape with a single `--adapter` flag.
- **11 domain rubrics.** code-review, security, devops, data-analysis,
  frontend-design, testing, documentation, content-writing, research,
  default, custom-template. Per-rubric weight overrides via a sidecar
  `<rubric>.weights.json`.
- **Model-aware efficiency.** Opus 4.7's new tokenizer (~35% more
  tokens) doesn't silently penalise its longer outputs — length
  thresholds scale by a per-model baseline.
- **Diff-aware delta.** `/judge --against HEAD~1` renders a side-by-
  side delta and exits non-zero on composite regression so CI can gate
  on it.
- **Local HTML dashboard.** `scripts/studio.py` emits a single-file
  HTML report with radar charts + trend lines — no server, no build
  step.
- **Benchmark regression gate.** Curated transcript corpus plus
  `scripts/benchmark_pack.py` asserts no heuristic drift across
  releases. Wired into CI.
- **Stdlib only.** Python 3.9+, no third-party packages, installs
  instantly with zero supply-chain risk.

> **v1.x → v2.0.0 migration.** v2.0.0 trimmed Verdict to its plugin
> scope per the 2026-05-03 v4.3 reset: 16 frontier-lab eval-bench
> rubrics, 6 cross-ecosystem adapters, and 7 bench-eval scripts were
> removed. If you depended on `swe-bench-pro`, `terminal-bench`,
> `clinical-agentic-workflow`, `eu-ai-act-audit-trail`,
> `tool-output-rewrite`, etc., pin to `v1.4.2` or fork. See
> [`CHANGELOG.md`](CHANGELOG.md) §[2.0.0] and
> [`CLAUDE.md`](CLAUDE.md) §v4.3 Scope Contract.

---

## Quick start

### Automatic mode

Skills on the `auto_judge.always` allowlist are scored without user
intervention. The `Stop` hook emits:

```
Verdict: code-review → 8.7/10 (A-). Solid execution with minor areas for improvement.
```

### Manual mode

```
/judge                            # Score the last execution
/judge --rubric security          # Force a specific rubric
/judge --adapter codex --model claude-opus-4-7
/judge --against HEAD~1           # Delta vs. previous run
/scorecard                        # Trend view across runs
/benchmark code-review            # Delta vs. reference standards
/judge-config                     # View / update allowlist + threshold
```

### Cross-ecosystem

```shell
# Codex CLI session
python3 skills/judge/scripts/score.py \
  --skill code-review \
  --transcript ~/.codex/sessions/latest.json \
  --rubric-dir skills/judge/rubrics \
  --scores-dir skills/judge/scores \
  --adapter codex

# OpenAI-compatible (Cursor / Continue)
python3 skills/judge/scripts/score.py --adapter openai-compatible ...
```

### Studio dashboard

```shell
python3 skills/judge/scripts/studio.py \
  --scores-dir skills/judge/scores \
  --output verdict-studio.html
open verdict-studio.html
```

### Explain a scorecard for a PR comment

```shell
python3 skills/judge/scripts/explain.py \
  --scorecard skills/judge/scores/code-review_2026-04-25.json \
  --format md \
  --out /tmp/pr-comment.md
```

`--format json` emits the same data under a stable
`format_version: "explain.v1"` schema. See
[`SKILL-judge-explain.md`](skills/judge/SKILL-judge-explain.md).

---

## Scoring system

7 weighted dimensions summing to 1.0. Weights live in
`judge-config.json.scoring.dimensions` and can be overridden per
rubric via a `<rubric>.weights.json` sidecar.

| Dimension       | Default | Signal                                           |
| --------------- | :-----: | ------------------------------------------------ |
| Correctness     | 0.25    | Error / hallucination patterns                   |
| Completeness    | 0.20    | TODO/FIXME/HACK density (docstring-scoped)       |
| Adherence       | 0.15    | Deviation keywords vs. rubric criteria           |
| Actionability   | 0.15    | Code fences + file actions − placeholders        |
| Efficiency      | 0.10    | Tool-call density, retries, length (model-aware) |
| Safety          | 0.10    | Destructive commands, exposed creds (context-aware) |
| Consistency     | 0.05    | Variance vs. historical scores                   |

Grades: A+ ≥ 9.5, A ≥ 9.0, A− ≥ 8.5, B+ ≥ 8.0, B ≥ 7.5, B− ≥ 7.0,
C+ ≥ 6.5, C ≥ 6.0, C− ≥ 5.5, D ≥ 4.0, F otherwise.

Per-rubric overrides: drop a sibling `<rubric>.weights.json` next to
`<rubric>.md`. Shipped example: `security.weights.json` weights safety
at 0.35, correctness at 0.20.

---

## Architecture

```
.claude-plugin/
  plugin.json              # Plugin manifest
  marketplace.json         # Marketplace listing
skills/judge/
  SKILL.md                 # Core skill definition
  SKILL-judge-explain.md   # /judge --explain output schema
  scripts/
    score.py               # Scoring engine
    report.py              # Scorecard reporter
    benchmark.py           # Benchmark comparator
    against.py             # /judge --against delta
    compare.py             # /compare two-file diff with regression narrative
    explain.py             # /judge --explain Markdown / JSON / HTML-printable
    studio.py              # Local HTML dashboard
    watch.py               # /judge --watch live re-scoring daemon
    cost_estimator.py      # Per-scorecard USD cost estimator
    hook_lint.py           # PostToolUse hook static analyzer
  adapters/
    claude_code.py         # Native JSONL (default)
    cowork.py              # Claude Cowork sessions
    codex.py               # OpenAI Codex CLI
    openai_compatible.py   # Cursor / Continue / generic
  analyzers/
    llm_judge.py           # Opt-in second-opinion (Claude API + cache_control)
  rubrics/                 # 11 plugin-domain rubrics + sidecar weights
  scores/                  # Persisted JSON scorecards
  references/              # Scoring methodology + benchmark standards
agents/judge-agent.md
hooks/
  hooks.json               # Stop / SubagentStop / StopFailure
  common.sh, judge-on-stop.sh, judge-on-subagent-stop.sh, judge-on-stop-failure.sh
commands/                  # /judge, /scorecard, /benchmark, /judge-config, /against, /compare
scripts/
  validate_marketplace.py  # Schema validator
  install_rubric.py        # Fetch + validate community rubrics
  benchmark_pack.py        # Regression gate for CI
  sandbox_caps_check.py    # CLAUDE_SANDBOX_CAPS declaration check (CI)
benchmarks/
  manifest.json + corpus/  # Regression-gate fixtures (NOT a public eval bench — see benchmarks/README.md)
.github/workflows/
  ci.yml                   # Tests + validators + benchmark gate + shellcheck
judge-config.json
CLAUDE.md, CHANGELOG.md, INSTALL-COWORK.md, README.md, LICENSE
```

---

## Configuration reference

All in `judge-config.json`:

### `auto_judge`

| Key                 | Type     | Description                                              |
| ------------------- | -------- | -------------------------------------------------------- |
| `enabled`           | boolean  | Master switch for automatic judging.                     |
| `always`            | string[] | Skill names auto-judged without further configuration.   |
| `never`             | string[] | Skill names never auto-judged.                           |
| `threshold`         | number   | Minimum composite to pass (0–10).                        |
| `block_on_critical` | boolean  | Exit-2 the hook (block workflow) when below threshold.   |

### `manual_judge`

| Key              | Type    | Description                               |
| ---------------- | ------- | ----------------------------------------- |
| `default_rubric` | string  | Fallback rubric name.                     |
| `verbose`        | boolean | Show per-dimension justifications.        |
| `save_scores`    | boolean | Persist scorecard JSON.                   |

### `scoring.dimensions`

Map of dimension → weight. Weights must sum to 1.0 — `load_config`
rejects otherwise (stderr warning + default fallback).

### `tokenizer_baselines`

Per-model multipliers for the efficiency analyser's length thresholds.
Ships with `claude-opus-4-7: 1.35`, others at 1.0. Override per model
or add new ones — the `default` key catches unknown models.

---

## Requirements

- **Python 3.9+** — stdlib only (no pip deps).
- **jq** — `brew install jq` / `apt-get install jq`.
- **bc** — `brew install bc` / `apt-get install bc`.

## Running tests

```shell
python3 -m unittest discover tests/ -v        # full suite
python3 scripts/validate_marketplace.py       # schema check
python3 scripts/benchmark_pack.py             # regression gate
shellcheck hooks/*.sh                         # hook-script lint
```

## Roadmap

See [ROADMAP_2026.md](ROADMAP_2026.md) for the 90-day plan. Latest
release: [v2.0.2](https://github.com/sattyamjjain/verdict/releases/tag/v2.0.2)
(safety-dim allowlist tracks Claude Code v2.1.126 — `.git/`,
`.vscode/`, and a closed POSIX/zsh shell-config-file set added to
`_is_plugin_author_write`; destructive shell forms still dock).
Previous releases:
[v2.0.1](https://github.com/sattyamjjain/verdict/releases/tag/v2.0.1)
(opt-in `duration_ms` enrichment + safety `.claude` path
allowlist + marketplace validator v2.1.120 keys), and the
breaking
[v2.0.0](https://github.com/sattyamjjain/verdict/releases/tag/v2.0.0)
trim to the v4.3 plugin-only scope — see
[`CHANGELOG.md`](CHANGELOG.md#200---2026-05-03) and the
[v1.x → v2.0.0 migration note](#features). No open tracker issues —
each cycle's scope is tracked in a fresh issue, opened when the
cycle starts and closed at release.

## Contributing

Rubric contributions welcome — see `skills/judge/rubrics/custom-template.md`.
Community rubrics can be installed via `scripts/install_rubric.py`
from any HTTPS URL that serves a Verdict-shaped rubric.

## License

MIT — see [LICENSE](LICENSE).
