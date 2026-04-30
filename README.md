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
| Per-domain rubrics         | ✓ (27)  | via code                        | via YAML             | via code         |
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
  Cowork, Codex, Cursor, Continue, OpenAI-compatible JSON, Gemini
  CLI, Gemini 3.1 Pro Deep Research, MLflow, Inspect AI,
  Terminal-Bench, and Browser Harness (browser-use) traces with a
  single `--adapter` flag. Auto-detection by confidence-score
  dispatch (the highest-scoring adapter wins).
- **27 domain rubrics + compliance pack + benchmark / commerce /
  security / ship-readiness / hook-trust / EU-audit / routine
  pack.** Eleven everyday rubrics (code-review, security, devops,
  data-analysis, frontend-design, testing, documentation,
  content-writing, research, default, custom-template); compliance
  pack (Aider polyglot, Skill compliance, Model Spec compliance,
  SWE-bench Pro with contamination penalty, Terminal-Bench, OWASP
  MCP Top 10 beta, EXPERIMENTAL clinical agentic-workflow); the
  v1.4.0 pack (Project Deal commerce, Agentic SAST + Brier
  calibration, Function-hijacking robustness, GPT-5.5 differential
  (paired baseline), browser-agent); the v1.4.1 release-readiness
  rubric (ship-readiness with seven binary floors); and the v1.4.2
  pack (tool-output-rewrite for Claude Code v2.1.121's hook-
  rewrite trust boundary, eu-ai-act-audit-trail (NOT
  counsel-reviewed — Issue O13), routine-execution for Anthropic
  Routines research-preview transcripts).
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

## Compliance rubrics

Rubrics that map external compliance frameworks onto Verdict's
canonical dimensions. Status reflects the upstream framework, not
Verdict's coverage.

| Rubric                        | Framework                                  | Upstream status                       |
| ----------------------------- | ------------------------------------------ | ------------------------------------- |
| `owasp-mcp-top-10-beta`       | OWASP MCP Top 10                           | **BETA** (Phase 3, not yet ratified — re-validate against [the OWASP page](https://owasp.org/www-project-mcp-top-10/) on every bump) |
| `clinical-agentic-workflow`   | ChatGPT for Clinicians-style workflow eval | **EXPERIMENTAL** — DO NOT USE IN PRODUCTION (Issue O3 open, PHI redaction false-positives) |
| `project-deal-commerce`       | Anthropic Project Deal agent commerce      | Stable but threshold-anchored (Issue O4 — `asymmetry_dock_threshold_usd` configurable per deployment) |
| `agentic-sast-confidence`     | GitLab 18.11 Agentic SAST + Brier loss     | Stable                                |
| `function-hijacking-robustness` | Forward-looking — client-side trust boundary | v1, offline-fixture replay only (live-replay queued, Issue O5) |
| `gpt-5-5-differential`        | OpenAI GPT-5.5 launch / paired baseline    | Stable (works for any pairwise model) |
| `browser-agent`               | browser-use Browser Harness                | Stable (DOM-event + screenshot + assertion shape) |
| `model-spec-compliance`       | OpenAI Model Spec Evals                    | Stable (1-7 scale, mapped onto Verdict 1-10) |
| `swe-bench-pro`               | SWE-bench Pro                              | Stable (contamination-resistant successor to Verified) |
| `code-review-aider-polyglot`  | Aider polyglot benchmark                   | Stable                                |
| `terminal-bench`              | Terminal-Bench shell-task trajectory eval  | Stable                                |
| `skill-compliance`            | MLflow skill-compliance evaluation         | Stable (mirrors MLflow's offline)     |
| `ship-readiness`              | Verdict release-readiness composite        | Stable (binary floors via the rubric weights sidecar — `ship_floor_*` keys configurable per deployment) |
| `tool-output-rewrite`         | Claude Code v2.1.121 PostToolUse `updatedToolOutput` trust boundary | Stable (verified against published Claude Code v2.1.121 changelog — see Issue O12 for encoding-bypass mitigation) |
| `eu-ai-act-audit-trail`       | EU AI Act Articles 19, 26 audit-trail evidence | **NOT counsel-reviewed** (Issue O13 open — disclaimer in rubric file; passing the rubric is NOT a determination of regulatory compliance) |
| `routine-execution`           | Anthropic Routines (research preview) trajectory shape | Stable (Routines is research preview as of 2026-04-29, not GA — heuristic detection opt-in via `VERDICT_DETECT_ROUTINE_HEURISTIC=1`, Issue O15) |

Beta and experimental rubrics carry a moving-target risk — the
upstream framework's category names, ordering, or severity may
change before v1, and EXPERIMENTAL rubrics carry known false-
positive classes that need real-pilot calibration before deploy.

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
    cost_estimator.py      # Per-scorecard USD cost estimator (R4)
    replay_bfcl_attacks.py # Function-hijacking attack-vector replay harness
    ship_gate.py           # Ship-readiness gate CLI + SARIF v2.1.0 export
    judge_replay.py        # Re-score a transcript and assert vs. baseline
    eu_audit_export.py     # CC2 — EU AI Act Articles 19/26 CSV export
    benchmark_gaming_detector.py # CC3 — Berkeley RDI exploit-signature detector
    audit_export.py        # T1 — DPO-ready zip bundle (NOT LEGAL ADVICE)
    bench_gaming_check.py  # T2 — pre-publication benchmark-gaming linter
    hook_lint.py           # T3 — PostToolUse hook static analyzer
    signatures/
      berkeley-rdi-2026-04-26.json # Berkeley RDI exploit signatures (Issue O14)
  adapters/
    claude_code.py         # Native JSONL (default)
    cowork.py              # Claude Cowork sessions
    openai_compatible.py   # Cursor / Continue / generic
    codex.py               # OpenAI Codex CLI
    gemini_cli.py          # Gemini CLI sessions
    gemini_deep_research.py# Gemini 3.1 Pro Deep Research / Deep Research Max
    mlflow_trace.py        # MLflow Trace JSON exports (with OTel GenAI semconv)
    inspect_ai_log.py      # UK AISI inspect_ai 0.3.x evaluation logs
    terminal_bench.py      # Terminal-Bench shell-task trajectories
    browser_harness.py     # browser-use Browser Harness traces
  integrations/
    lighteval_shim.py      # LightEval metric shim (lazy-imports lighteval)
    cloudflare_ai_gateway.py # Cloudflare AI Gateway + Mesh dispatch wrapper
  exporters/
    openai_evals.py        # Verdict → OpenAI Model Spec Evals JSON
  analyzers/
    llm_judge.py           # Opt-in second-opinion (Claude API + cache_control)
  rubrics/                 # 27 rubrics + per-rubric weight-override sidecars
  scores/                  # Persisted JSON scorecards
  references/              # Scoring methodology + benchmark standards
agents/judge-agent.md
hooks/
  hooks.json               # Stop / SubagentStop / StopFailure
  common.sh, judge-on-stop.sh, judge-on-subagent-stop.sh, judge-on-stop-failure.sh
commands/                  # /judge, /scorecard, /benchmark, /judge-config, /against, /compare
scripts/
  validate_marketplace.py  # April 2026 schema validator
  install_rubric.py        # Fetch + validate community rubrics
  benchmark_pack.py        # Regression gate for CI
  sandbox_caps_check.py    # CLAUDE_SANDBOX_CAPS declaration check (CI)
benchmarks/
  manifest.json + corpus/  # Curated cases
routines/
  weekly-team-digest.md    # Anthropic Routines prompt
docs/
  research-log.md          # Dated citations for external specs
  followups.md             # Tasks awaiting human action
  metrics.md               # Weekly launch + engineering metrics
  launch/                  # Launch collateral (HN, Reddit, X, DMs, marketplace)
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
release: [v1.3.2](https://github.com/sattyamjjain/verdict/releases/tag/v1.3.2).
No open tracker issues — each cycle's scope is tracked in a fresh
issue, opened when the cycle starts and closed at release.

## Contributing

Rubric contributions welcome — see `skills/judge/rubrics/custom-template.md`.
Community rubrics can be installed via `scripts/install_rubric.py`
from any HTTPS URL that serves a Verdict-shaped rubric.

## License

MIT — see [LICENSE](LICENSE).
