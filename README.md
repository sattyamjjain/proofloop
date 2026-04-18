# Verdict

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
- **Dual-platform.** Claude Code and Claude Cowork, plus Routines-
  triggered cloud sessions.
- **7-dimension weighted scoring.** Correctness, completeness,
  adherence, actionability, efficiency, safety, consistency — weights
  configurable globally or per rubric via a sidecar `.weights.json`.
- **Cross-ecosystem adapters.** Score transcripts from Claude Code,
  Cowork, Codex, Cursor, Continue, and any OpenAI-compatible format
  with a single `--adapter` flag.
- **11 domain rubrics.** code-review, security, devops, data-analysis,
  frontend-design, testing, documentation, content-writing, research,
  plus `default` and a `custom-template`.
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
  scripts/
    score.py               # Scoring engine
    report.py              # Scorecard reporter
    benchmark.py           # Benchmark comparator
    against.py             # /judge --against delta
    studio.py              # Local HTML dashboard
  adapters/
    claude_code.py         # Native JSONL (default)
    cowork.py              # Claude Cowork sessions
    openai_compatible.py   # Cursor / Continue / generic
    codex.py               # OpenAI Codex CLI
  rubrics/                 # 11 domain rubrics + security.weights.json
  scores/                  # Persisted JSON scorecards
  references/              # Scoring methodology + benchmark standards
agents/judge-agent.md
hooks/
  hooks.json               # Stop / SubagentStop / StopFailure
  common.sh, judge-on-stop.sh, judge-on-subagent-stop.sh, judge-on-stop-failure.sh
commands/                  # /judge, /scorecard, /benchmark, /judge-config, /against
scripts/
  validate_marketplace.py  # April 2026 schema validator
  install_rubric.py        # Fetch + validate community rubrics
  benchmark_pack.py        # Regression gate for CI
benchmarks/
  manifest.json + corpus/  # Curated cases
routines/
  weekly-team-digest.md    # Anthropic Routines prompt
docs/
  research-log.md          # Dated citations for external specs
  followups.md             # Tasks awaiting human action
  launch/                  # Launch collateral (HN, Reddit, X, DMs)
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

See [ROADMAP_2026.md](ROADMAP_2026.md) for the 90-day plan. Open
tracking issue: #2.

## Contributing

Rubric contributions welcome — see `skills/judge/rubrics/custom-template.md`.
Community rubrics can be installed via `scripts/install_rubric.py`
from any HTTPS URL that serves a Verdict-shaped rubric.

## License

MIT — see [LICENSE](LICENSE).
