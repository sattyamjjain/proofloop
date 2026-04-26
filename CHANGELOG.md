# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.3] - 2026-04-26

Docs-only patch. Brings `README.md` back into sync with the actual
repo state after three quick releases (v1.3.0 / v1.3.1 / v1.3.2)
in three days. No code changes; 619 tests green.

### Changed

- `README.md` "Why Verdict" comparison table: rubric count
  `(11)` → `(18)`.
- `README.md` Architecture tree:
  - Adapters list expanded from 4 to all 9 (`gemini_cli`,
    `gemini_deep_research`, `mlflow_trace`, `inspect_ai_log`,
    `terminal_bench` were missing).
  - Scripts list expanded from 5 to all 8 (`compare.py`,
    `explain.py`, `watch.py` were missing).
  - New `integrations/`, `exporters/`, `analyzers/` subtrees added
    (lighteval shim, Cloudflare AI Gateway, OpenAI Evals exporter,
    LLM second-opinion).
  - Rubrics comment: `11 + security.weights.json` → `18 rubrics +
    5 weight-override sidecars`.
  - `commands/` line gains `/compare`.
  - `scripts/` (top-level) gains `sandbox_caps_check.py`.
- `README.md` Roadmap section: removed stale reference to "open
  tracking issue: #2" (issue #2 was the v1.1.0 tracker, closed
  long ago). Replaced with a pointer to the latest release and a
  one-line note on the per-cycle tracker pattern.
- Plugin / marketplace version → `1.3.3`.

## [1.3.2] - 2026-04-26

Patch release. New adapter, EXPERIMENTAL clinical rubric, two
adapter-fix items, two open-issue closures. Offline-first invariant
preserved; no new runtime deps.

### Added (2026-04-26 session, Z1–Z6 + O1 + O2)

- **Z1 — Gemini 3.1 Pro Deep Research adapter**
  (`skills/judge/adapters/gemini_deep_research.py`). Parses Deep
  Research / Deep Research Max session JSON: flattens
  `research_plan` → `[plan_step]`, `citations[]` →
  `[citation:<url>] retrieved_at=...`, `verifier_notes` →
  `[verifier_note]`, `assistant_synthesis` → `[assistant]`.
  Registered as `gemini-deep-research` / `gemini-deep`. Auto-detected
  via `deep_research_mode` flag or structural markers. Source signal:
  [blog.google — Deep Research Max (2026-04-22)](https://blog.google/products/gemini/google-gemini-deep-research-max/).
- **Z2 — EXPERIMENTAL clinical-agentic-workflow rubric**
  (`skills/judge/rubrics/clinical-agentic-workflow.{md,weights.json,example.md}`).
  Eight clinical concerns mapped onto Verdict's seven canonical
  dimensions; PHI redaction guard activates only for this rubric and
  deducts 2.0 from composite + emits a critical issue when SSN /
  MRN-prefix / DOB-prefix literals appear. **DO NOT USE IN
  PRODUCTION** — the dose-string false-positive class (Issue O3) is
  open. Source signal:
  [openai.com — ChatGPT for Clinicians (2026-04-25)](https://openai.com/index/chatgpt-for-clinicians/).
- **Z3 — Inspect AI 0.3.x version-pin honesty**
  (`skills/judge/adapters/inspect_ai_log.py`). Adds
  `INSPECT_AI_SUPPORTED_RANGE = ">=0.3.180,<0.4.0"` constant +
  `_check_inspect_ai_version()` returning a one-shot stderr warning
  when the installed `inspect_ai.__version__` falls outside the
  range. PyPI's latest as of 2026-04-26 is 0.3.214; 0.4.x is
  unreleased. Source signal:
  [PyPI inspect-ai](https://pypi.org/project/inspect-ai/).
- **Z4 — Cloudflare AI Gateway eval-webhook integration**
  (`skills/judge/integrations/cloudflare_ai_gateway.py`). Pure
  dict-in / dict-out: accepts the gateway's eval-webhook payload,
  builds a synthetic transcript from
  `request.messages` + `response.choices[0].message`, runs Verdict's
  heuristic scorer, maps the 1-10 composite onto Cloudflare's
  `[0.0, 1.0]` band. No Cloudflare SDK dep. Source signal:
  [blog.cloudflare.com — AI Gateway evals (2026-04-23)](https://blog.cloudflare.com/ai-gateway-evals/).
- **Z5 — Claude Code v2.1.117 sandbox-aware self-score CI**
  (`.github/workflows/self-score.yml` + `scripts/sandbox_caps_check.py`).
  Workflow now declares `CLAUDE_SANDBOX_CAPS=bash:read,fs:read` and
  invokes the new check script (stdlib-only) to verify the
  declaration matches the workflow's expected caps. Declaration-only
  check; runtime isolation is provided by the Claude Code runtime.
  Source signal:
  [code.claude.com changelog](https://code.claude.com/docs/en/changelog).
- **O1 — Adapter detection collision fix**
  (`skills/judge/adapters/__init__.py` + each collision-prone
  adapter). After Y6 (v1.3.0) added OTel `gen_ai.*` attrs to
  `mlflow_trace`, both `inspect_ai_log` and `mlflow_trace` could
  fingerprint a trace carrying both shapes. Refactored
  `detect_adapter` from first-match-wins boolean fingerprints to
  score-based dispatch — each adapter now exposes
  `detection_score(path) -> float` in `[0.0, 1.0]`, and the
  registry returns the highest-scoring name. The MLflow schema
  literal scores 0.95, beating Inspect's 0.70 on collision payloads.
- **O2 — `/judge --explain` truncation cap**
  (`skills/judge/scripts/explain.py`). New `--max-evidence-chars=N`
  flag (default 4000) caps the Markdown render so the
  `actions/verdict-comment-pr` step doesn't silently truncate against
  GitHub's 65 KB PR comment limit. `--max-evidence-chars=0` disables
  truncation entirely. New `--scorecard-url` flag injects a
  templated link into the truncation footer.

### Changed (2026-04-26 session)

- Plugin / marketplace version → `1.3.2`.
- Adapter registry gains `gemini-deep-research` / `gemini-deep`
  (total 9 adapters).
- Rubric count → 18 (`clinical-agentic-workflow` adds, `default` /
  `code-review` / `frontend-design` / `documentation` / `testing` /
  `security` / `content-writing` / `data-analysis` / `research` /
  `devops` / `custom-template` / `code-review-aider-polyglot` /
  `skill-compliance` / `model-spec-compliance` / `swe-bench-pro` /
  `terminal-bench` / `owasp-mcp-top-10-beta`).
- Self-score workflow declares sandbox capabilities explicitly.
- `score.py` carries a new `_apply_phi_redaction_check()` helper
  that activates only when the rubric is `clinical-agentic-workflow`.
- `score.py` scorecard JSON gains `adjustments.phi_leak` field
  (always present; 0.0 unless the redaction guard fired).

### Tests (2026-04-26 session)

- `tests/test_gemini_deep_research_adapter.py` (19), `test_clinical_rubric.py`
  (16), `test_inspect_ai_version_check.py` (16), `test_cloudflare_ai_gateway.py`
  (15), `test_sandbox_caps.py` (20), `test_adapter_registry.py` (14),
  `test_judge_explain.py` gains 10 truncation-cap tests.
- Total suite: **619 tests green** (506 → 619, +113 new).

### Known issues

- **O3** — clinical PHI-redaction false positives on dose strings
  (e.g. `MR12345` next to `mg`). Mitigated heuristically via dose-
  unit allow-list, not closed. Z2 rubric ships at EXPERIMENTAL
  status; do NOT market publicly until O3 closes via real clinical
  pilot calibration.

### Honesty correction

- v1.3.0's adapter docstring said "0.3 stable release" without a
  version-range pin — Z3 closes that gap. A regression test
  (`TestNoStaleVersionReferenceInChangelog`) prevents future entries
  from claiming an unreleased major version is shipped.

## [1.3.1] - 2026-04-25

Patch release. Two additive items, no breaking changes to v1.3.0's
surface.

### Added (2026-04-25 session, Y10 + Y12)

- **`/judge --explain` rationale exporter**
  (`skills/judge/scripts/explain.py`, `skills/judge/SKILL-judge-explain.md`).
  Reads an existing scorecard JSON written by `score.py` and renders
  it as either PR-comment-friendly Markdown (`--format md`,
  default) or a stable-schema JSON document tagged
  `format_version: "explain.v1"` (`--format json`). Output sections:
  per-dimension table, optional LLM second-opinion overlay,
  adjustments (red flags, bonuses, contamination), critical issues,
  recommendations, evidence-stat block. New CLI:
  `python3 skills/judge/scripts/explain.py --scorecard <PATH>
  [--format md|json] [--out PATH]`. Slash command updated:
  `/judge --explain <SCORECARD>`. Source signal:
  [Discussions #43](https://github.com/sattyamjjain/verdict/discussions/43).
- **OWASP MCP Top 10 (beta) coverage rubric**
  (`skills/judge/rubrics/owasp-mcp-top-10-beta.md` +
  `.weights.json`). Maps MCP01–MCP10 risks to Verdict's canonical
  seven dimensions with per-risk evidence-span criteria for the
  scorer to grep against. Safety carries 50% of the weight (eight
  of ten risks roll up there). Carries an explicit BETA caveat —
  re-validate against
  [the OWASP page](https://owasp.org/www-project-mcp-top-10/) on
  every Verdict bump until OWASP marks the list v1.

### Tests (2026-04-25 session)

- `tests/test_judge_explain.py` (23 tests) covers the JSON schema,
  Markdown sections, missing-scorecard error path, and an end-to-
  end round trip from `score.build_scorecard` through `explain`.
- `tests/test_owasp_mcp_rubric.py` (10 tests) pins file existence,
  source-signal header, weights sum, every MCP01–MCP10 label,
  rubric resolution, and an end-to-end scoring run.
- Total suite: **506 tests green** (473 → 506, +33 new).

### Notes

- v1.3.0 already shipped Anthropic's `extended-cache-ttl-2025-04-11`
  beta header (Y3); the redundant Y11 was dropped from this cycle.
- GPT-5.5 model registry (Y8), Managed Agents judge harness (Y9),
  and `bench --watch` (Y13) deferred to v1.4.0.

## [1.3.0] - 2026-04-24

### Added (2026-04-24 session, Y1–Y7)

- **Inspect AI log adapter**
  (`skills/judge/adapters/inspect_ai_log.py`) — parses UK AISI
  `inspect_ai` v0.3 evaluation logs (`.json`) into Verdict's flat
  line stream, tagging assistant / tool-call / tool-result / user
  turns and preserving scorer verdicts as `[ground_truth_score]`
  sentinels. Registered as `inspect-ai` / `inspect`; auto-detected
  via a file-head fingerprint on `"eval": {"task":` /
  `"samples":`. Source signal:
  <https://inspect.aisi.org.uk>, <https://github.com/UKGovernmentBEIS/inspect_ai>.
- **`managed-agents-2026-04-01` memory stitch** —
  `adapters/claude_code.py` now detects the parallel-agent shared-
  memory records that Claude Code streams into the JSONL transcript
  (tokens: `managed_memory_v1`, `agent_memory`, `parent_agent_id`)
  and tags them with `[managed-memory-pull]` / `[managed-memory-push]`
  prefixes. Exposes `parse_managed_agent_memory(lines)` for post-
  processing already-extracted line lists.
- **Prompt-caching `cache_control` on the LLM judge**
  (`analyzers/llm_judge.py`) — the opt-in second-opinion client now
  wraps the system prompt in an ephemeral cached content block by
  default (`"ttl": "5m"`). `ENABLE_PROMPT_CACHING_1H=1` upgrades to
  the 1-hour extended beta (`anthropic-beta:
  extended-cache-ttl-2025-04-11`); `FORCE_PROMPT_CACHING_5M=1` pins
  back to 5m. Cache hits / misses logged to stderr per call. New
  public helpers: `resolve_cache_ttl_from_env`,
  `build_cached_system_block`.
- **SWE-bench Pro rubric + contamination penalty**
  (`skills/judge/rubrics/swe-bench-pro.md` + `.weights.json`;
  `score.py::_apply_contamination_penalty`). Weights lean onto
  Correctness (0.35) and Adherence (0.30). When the active rubric
  is `swe-bench-pro`, the scorer scans the transcript for SWE-bench
  Verified instance-ID patterns (`django__django-12345` etc.) and
  split-name literals; each unique match deducts 0.25 composite, up
  to 1.5 total. Surfaced in the scorecard as
  `adjustments.contamination`. Source signal:
  <https://llm-stats.com/benchmarks/swe-bench-pro>.
- **Terminal-Bench trajectory adapter + rubric**
  (`adapters/terminal_bench.py`, `rubrics/terminal-bench.md` +
  `.weights.json`). Adapter flattens `steps[].{command, stdout,
  stderr, exit_code}` into `[shell_cmd]` / `[stdout]` /
  `[stderr:exit=N]` turns. Rubric weights Safety at 30% because
  command-safety and secret-leakage both roll up there. Source
  signal: <https://llm-stats.com/benchmarks/terminal-bench>.
- **OTel GenAI semconv enrichment for the MLflow adapter**
  (`adapters/mlflow_trace.py::_extract_otel_genai_attrs`). When a
  span carries `gen_ai.request.model`, `gen_ai.usage.input_tokens`,
  `gen_ai.usage.output_tokens`, or `gen_ai.response.finish_reasons`,
  the adapter emits `[model]` / `[usage]` / `[finish_reason]`
  pseudo-turns. `score.MODEL_ID_PATTERN` was widened to accept OTel
  dotted keys too, so the v1.1.0 model-aware efficiency thresholds
  now apply to MLflow traces without code changes on the caller.
  Source signal: <https://mlflow.org/releases/3.11.1/>.

### Changed (2026-04-24 session)

- Plugin / marketplace version → `1.3.0`.
- Adapter registry gains `inspect-ai` / `inspect`, `terminal-bench` /
  `terminal` names. Auto-detection cascade is now
  `inspect-ai → mlflow-trace → terminal-bench → claude-code`.
- `claude_code.extract_lines` runs `parse_managed_agent_memory` as a
  belt-and-braces post-pass so records that slipped through the raw
  fallback still get tagged.

### Tests (2026-04-24 session)

- `tests/test_inspect_ai_adapter.py` (13), `test_managed_agent_memory.py`
  (11), `test_llm_judge_prompt_cache.py` (17), `test_swe_bench_pro_rubric.py`
  (14), `test_terminal_bench.py` (21), `test_mlflow_otel_semconv.py`
  (11). Total suite: 473 tests, all green.

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
