# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0-beta.1] - 2026-04-19

### Added

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
