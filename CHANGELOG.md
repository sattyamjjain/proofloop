# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-04-20

### Added (2026-04-20 session, N1–N8)

- **Auto Memory cross-session transcript stitching** — `adapters/
  claude_code.py::extract_lines` now accepts a directory of `*.jsonl`
  session files (e.g. `~/.claude/history/`) and concatenates them in
  mtime order with a `--- session break ---` marker between files.
  Memory-preamble lines (detected via `memory_block`, `<memory>`,
  `auto-memory`, `claude_memory` tokens) are prefixed with
  `[system-memory] ` so downstream scoring can separate injected
  system context from user-turn output.
- **`task_budgets-2026-03-13` beta header** wired into the opt-in
  LLM judge (`skills/judge/analyzers/llm_judge.py`). Reads
  `judge-config.json.llm_second_opinion.task_budget_tokens`, enforces
  the 20k minimum, sends the soft budget via
  `output_config.task_budget` **and** raises `max_tokens` to a 1.25×
  hard ceiling so the judge finishes without over-spend. Optional
  stderr countdown logs every call for CI drift monitoring.
- **Three new rubrics** in the v1.2.0 pack:
  - `code-review-aider-polyglot.md` — Aider-polyglot-flavoured
    mapping against Verdict's canonical dimensions.
  - `skill-compliance.md` — MLflow "skill compliance" dimension
    ported offline.
  - `model-spec-compliance.md` — OpenAI Model Spec Evals 1-7 scale
    mapped onto Verdict 1-10 via a documented rescaling table.
  - Each rubric carries a `source_signal:` header citing provenance.
- **`--export openai-evals` exporter**
  (`skills/judge/exporters/openai_evals.py`) + matching CLI flag.
  Default threshold 7/10. Optional `--export-rescale` flag emits the
  Model Spec 1-7 bucket. LLM second-opinion fields round-trip.
- **LightEval v0.13.0+ metric shim**
  (`skills/judge/integrations/lighteval_shim.py`) — exposes Verdict
  as a callable metric returning a float in `[0, 1]`. Lazy-import
  protocol: `lighteval` is never imported by Verdict at runtime.
- **MLflow trace ingestion adapter**
  (`skills/judge/adapters/mlflow_trace.py`) — parses
  `mlflow.entities.Trace` JSON exports without importing `mlflow`.
  Registered as `mlflow-trace` / `mlflow`; auto-detected via a
  file-head fingerprint.
- **Schema registry static site**: `docs/schema-registry.md` +
  `.github/workflows/pages.yml` mirror `schemas/*.json` to GitHub
  Pages at `https://sattyamjjain.github.io/verdict/schemas/…`.
- **`/judge --compare-runs` + `/compare` slash command**
  (`skills/judge/scripts/compare.py`) — two-file delta with
  narrative callouts for Auto Memory regression signatures:
  composite drop, memory-block growth, consistency slide,
  per-dimension ≥ 3-point drops.

### Changed (2026-04-20 session)

- `judge-config.json.llm_second_opinion` gains a `task_budget_tokens`
  field (nullable). Off-by-default semantics unchanged.
- `commands/judge.md` adds `--export`, `--out`, `--export-rescale`
  flags plus a pointer to the new `/compare` command.
- `plugin.json` now registers `./commands/compare.md`.

### Tests (2026-04-20 session)

- 314 → 384 (+70). New suites: `test_auto_memory.py`,
  `test_llm_judge_budget.py`, `test_rubric_packs.py`,
  `test_openai_evals_export.py`, `test_lighteval_shim.py`,
  `test_mlflow_trace_adapter.py`, `test_compare_runs.py`.

### Added (2026-04-19 session, A1–A6 — carried forward from v1.1.1 scope)

- **Scorecard schema** (`schemas/scorecard.v1.schema.json`) — JSON
  Schema draft 2020-12 describing every field of the persisted scorecard
  JSON, with per-dimension entries and forward-compatible slots for LLM
  second-opinion output.
- **`$schema` + `schemaVersion` fields** on every persisted scorecard.
  Injected by `save_score`; callers can't forget or override the
  canonical identifiers. Consumers should pin `schemaVersion >= 1.0.0,
  < 2.0.0`.
- **DEEP_ANALYSIS.md §Schema stability contract** documenting SemVer
  rules, deprecation window, and test surface for the v1 schema line.
- **Opt-in LLM second-opinion analyzer**
  (`skills/judge/analyzers/llm_judge.py`). When
  `judge-config.json.llm_second_opinion.enabled = true` and
  `ANTHROPIC_API_KEY` is set, Verdict emits both heuristic and LLM
  scores under `dimensions[dim].llm_score` /
  `dimensions[dim].llm_justification`. Stdlib-only HTTP
  (`urllib.request`); no `anthropic` package is imported. Sends the
  `task-budgets-2026-03-13` beta header when `budget_tokens` is set.
  Transcripts over 16k chars are truncated with a head/tail split and
  an elision marker.
- **Gemini CLI adapter** (`skills/judge/adapters/gemini_cli.py`).
  Handles `parts[]`, flattened `content`, `functionCall`, and
  `functionResponse` shapes; registered under both `gemini-cli` and
  `gemini`.
- **`/judge --watch` live re-scoring** (`skills/judge/scripts/watch.py`).
  Polls `scores/` every 2 s, renders a diff header per change
  (`improved X, regressed Y, unchanged Z since last run`), and
  re-emits Verdict Studio.
- **Dogfood self-score CI gate**
  (`.github/workflows/self-score.yml`). Treats the PR title + body +
  changed-files list as a synthetic transcript, scores it against the
  code-review rubric, and fails the job when composite drops below
  the `VERDICT_PR_THRESHOLD` (default 7.0). Scorecard posted as a PR
  comment.
- **Scorecard fixtures** at `tests/fixtures/scorecards/` — canonical
  examples covering every adapter / rubric path; every fixture must
  validate against the shipped schema on every CI run.

### Changed

- `/judge` usage line now documents `--adapter`, `--model`,
  `--against`, `--watch`, and `--llm-second-opinion` flags; includes
  `gemini-cli` in the adapter list.
- Version bumps to `1.2.0-beta.1` across `plugin.json`,
  `marketplace.json`, and `SKILL.md`.

### Tests

- 262 → 314 (+52). New suites: `test_schema.py`, `test_llm_judge.py`,
  `test_watch.py`; Gemini cases added to `test_adapters.py` and
  `test_adapter_fixtures.py`.

### Out of scope for this beta

Rubric marketplace index (P2), scorecard delta webhook (P2),
`verdict` PyPI shim (P2), MLflow integration (future).

## [1.1.0] - 2026-04-18

### Added

- **Cross-ecosystem adapters** (`skills/judge/adapters/`) — transcript
  adapters for Claude Code (native), Claude Cowork, OpenAI-compatible
  formats (Cursor / Continue), and OpenAI Codex CLI. `score.py` grows
  a `--adapter NAME` flag; the built-in loader remains the default.
- **`StopFailure` hook** — when a Claude Code turn ends due to an API
  error (rate_limit, authentication_failed, etc.), Verdict skips
  auto-judging the transcript instead of docking its scores.
- **Model-aware efficiency** — `score.py` auto-detects the model from
  JSONL transcripts (or accepts `--model` override) and scales the
  long-transcript thresholds by a per-model tokenizer baseline. Ships
  with `claude-opus-4-7: 1.35` to absorb Opus 4.7's new tokenizer.
- **Per-rubric weight overrides** — `<rubric>.weights.json` sidecar
  alongside `<rubric>.md` overrides the global weights for that rubric.
  Shipped with `security.weights.json` (safety 0.35, correctness 0.20).
- **`validate_config()`** — rejects configs whose
  `scoring.dimensions` weights don't sum to 1.0; surfaces a stderr
  warning and falls back to defaults instead of silently inflating.
- **`/judge --against HEAD~1`** (`skills/judge/scripts/against.py`) —
  diff-aware scoring. Renders a side-by-side delta table; exits 2 on
  composite regression so CI can gate.
- **Verdict Studio** (`skills/judge/scripts/studio.py`) — single-file
  HTML dashboard with per-skill radar charts, trend lines, and critical-
  issue feed. Vanilla JS + SVG, no build step.
- **Rubric install CLI** (`scripts/install_rubric.py`) — fetch a
  community rubric (and optional weights sidecar) from any HTTPS URL,
  validate it, and drop it into `skills/judge/rubrics/`.
- **Marketplace validator** (`scripts/validate_marketplace.py`) —
  stdlib-only validator for `.claude-plugin/marketplace.json` against
  the April 2026 schema (owner, plugins, source variants, reserved
  names, kebab-case, 40-character SHAs).
- **Benchmark pack + manifest** (`benchmarks/` + `scripts/benchmark_pack.py`) —
  curated transcript corpus plus a regression gate that asserts each
  case still satisfies its expected bounds.
- **Routines support** — `routines/weekly-team-digest.md` is a ready-
  to-paste prompt for Anthropic Routines. Routine-triggered sessions
  fire the normal `Stop` hook; no `--mode routine` flag is required.
- **Research log** (`docs/research-log.md`) — dated citations for
  every external spec (hooks reference, marketplace schema, routines,
  Opus 4.7 tokenizer).
- **Launch collateral drafts** — `docs/launch/{hn-faq, reddit-post,
  x-thread, dm-templates, pitches}.md`.

### Changed

- **Consistency no-history default: 7 → 5.** The previous 7 inflated
  every first-run composite. See DEEP_ANALYSIS §12.3.
- **TODO/FIXME inside Python docstrings** no longer dock completeness.
  New `_strip_docstring_lines()` elides triple-quoted blocks before
  counting incompleteness tokens.
- **Safety discussion-context suppression.** `rm -rf /`, `chmod 777`,
  `--no-verify`, and credential patterns in review comments or warning
  text no longer trigger safety deductions or red-flag auto-deductions.
- **Plugin / marketplace version bumps to 1.1.0.**
- **`/judge` slash command documentation** expanded with `--adapter`,
  `--model`, and `--against` flags.

### Fixed

- Weight-sum invariant now enforced at config load (previously
  documented but not checked — a 1.05-sum config silently produced
  inflated composites).
- `detect_model_from_transcript` strips trailing snapshot suffixes
  (`-YYYYMMDD`) so model aliases map to the same tokenizer baseline.

### Tests

- 132 → 237 (+105). Adds coverage for adapters, model detection,
  rubric weight sidecars, docstring-scoped completeness, safety
  discussion-context, benchmark-pack bounds, studio rendering,
  marketplace validation, and the `/judge --against` CI gate.

## [1.0.0] - 2026-02-13

### Added

- Initial release of Verdict plugin for Claude Code and Claude Cowork.
- Dual-mode operation: automatic hooks and manual `/judge` command.
- 7-dimension weighted scoring system (correctness, completeness, adherence, actionability, efficiency, safety, consistency).
- 10 domain-specific rubrics in Markdown format (code-review, frontend-design, documentation, testing, security, content-writing, data-analysis, research, devops) plus a custom template.
- Persistent score storage as JSON in `skills/judge/scores/`.
- Slash commands: `/judge`, `/scorecard`, `/benchmark`, `/judge-config`.
- Python scoring engine with composite score calculation.
- Judge agent for autonomous evaluation workflows.
- `judge-config.json` for project-level configuration.
- Plugin manifest and marketplace metadata.
