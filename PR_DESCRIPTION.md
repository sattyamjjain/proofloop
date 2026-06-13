# PR drafts — stacked v1.1.1 + v1.2.0 landing

Two PRs, stacked. Copy-paste the body you need when you open each.
Kept in-repo so you can eyeball them locally before publishing.

---

## PR 1 — v1.1.1 (schema + issue hygiene)

### PR title

```
v1.1.1 — scorecard schema + $schema field + issue cleanup
```

### Base / head

- base: `main`
- head: `feat/v1.2.0-schema-llm-opinion`

### Body

Executes Thread A of the 2026-04-19 prompt. Commit `0b225cb` on branch
`feat/v1.2.0-schema-llm-opinion`. **Stop here if you want only v1.1.1
scope**; the v1.2.0 N1–N8 work stacks on top in PR 2.

- **A1** — `schemas/scorecard.v1.schema.json` + `$schema` /
  `schemaVersion` injection in `save_score`. Four committed fixtures
  under `tests/fixtures/scorecards/`. DEEP_ANALYSIS.md §Schema
  stability contract.
- **A2** — issue #2 closed with a v1.1.0 completeness summary;
  issue #3 opened for v1.2.0 tracking.
- **A3** — opt-in LLM second-opinion analyzer
  (`skills/judge/analyzers/llm_judge.py`). Off by default.
- **A4** — Gemini CLI adapter (`skills/judge/adapters/gemini_cli.py`)
  registered under `gemini-cli` / `gemini`.
- **A5** — `/judge --watch` live re-scoring
  (`skills/judge/scripts/watch.py`).
- **A6** — dogfood self-score CI gate
  (`.github/workflows/self-score.yml`).

Tests: 262 → 314 (+52). CI green locally (`validate_marketplace` +
`benchmark_pack` both pass).

---

## PR 2 — v1.2.0 (Auto Memory + task budgets + rubric pack + interop)

### PR title

```
v1.2.0 — Auto Memory, task budgets, rubric packs, MLflow/OpenAI-Evals interop
```

### Base / head

- base: `feat/v1.2.0-schema-llm-opinion` *(stacks on PR 1; merge that
  first, then rebase)*
- head: `feat/v1.2.0-rubric-pack-expansion`

### Body

Executes the 2026-04-20 prompt. Tests: 314 → 384 (+70). Benchmark
pack 8/8, marketplace validator clean.

#### N1 — Auto Memory cross-session stitching

`adapters/claude_code.py::extract_lines` now accepts a directory of
`*.jsonl` session files. Concatenates in mtime order with
`--- session break ---` markers. Memory-preamble lines flagged with
`[system-memory] ` so downstream scorers can separate injected system
context from actual user-turn output. Tokens recognised:
`memory_block`, `<memory>`, `auto-memory`, `claude_memory`. Fixture at
`tests/fixtures/claude-code-multisession/` + `tests/test_auto_memory.py`
(12 cases).

#### N2 — `task_budgets-2026-03-13` beta header

`AnthropicClient` now sends the `anthropic-beta:
task_budgets-2026-03-13` header when a `budget_tokens` is set, plus
`output_config.task_budget` soft cap and a `max_tokens` hard ceiling
at `1.25×` of the soft budget. Enforces the 20k minimum documented
by Anthropic. Optional stderr countdown for CI drift monitoring.
Config plumbing: `llm_second_opinion.task_budget_tokens`.
`tests/test_llm_judge_budget.py` (9 cases) verifies the exact wire
format without touching the network.

#### N3 — Three new rubrics

- `code-review-aider-polyglot.md` — maps Aider-polyglot benchmark
  axes (syntactic/semantic correctness, multi-file coherence,
  instruction-follow, diff compaction) onto Proofloop's canonical
  seven dimensions.
- `skill-compliance.md` — MLflow's "skill compliance" dimension
  (did the agent actually load and follow the skill?) ported offline.
- `model-spec-compliance.md` — OpenAI Model Spec Evals 1-7 scale,
  with a documented rescaling table to Proofloop's native 1-10.

Each carries a `source_signal:` header citing the article it rides.
`tests/test_rubric_packs.py` (6 cases) exercises structure + parser +
end-to-end scoring.

#### N4 — `--export openai-evals` exporter

`skills/judge/exporters/openai_evals.py` converts a Proofloop scorecard
into Model Spec Evals JSON (`{run_id, criteria, summary}`). Threshold
7/10 default. `--export-rescale` flag emits Model Spec's native 1-7
bucket. LLM second-opinion fields round-trip into `llm_score` /
`llm_rationale`. CLI flag wired through `score.py`.
`tests/test_openai_evals_export.py` (10 cases).

#### N5 — LightEval metric shim

`skills/judge/integrations/lighteval_shim.py` exposes
`verdict_metric(predictions, references, rubric)` returning a float in
`[0, 1]`. `lighteval` is **never** imported at runtime — lazy-import
protocol preserves Proofloop's offline-first pitch.
`tests/test_lighteval_shim.py` (7 cases).

#### N6 — MLflow trace ingestion adapter

`skills/judge/adapters/mlflow_trace.py` parses
`mlflow.entities.Trace` JSON exports without importing `mlflow`.
Registered under `mlflow-trace` / `mlflow`; auto-detected via a
file-head fingerprint (`adapters.detect_adapter`).
Fixture at `tests/fixtures/mlflow-trace.json`.
`tests/test_mlflow_trace_adapter.py` (14 cases).

#### N7 — Schema registry static site

`docs/schema-registry.md` + `.github/workflows/pages.yml`. Every file
under `schemas/` mirrors to GitHub Pages on push to `main`; once
`proofloop.dev` is live, a CNAME swap lands the canonical URLs.

#### N8 — `/judge --compare-runs` (and `/compare` slash command)

`skills/judge/scripts/compare.py` + `commands/compare.md`. Explicit
two-file delta with narrative callouts for Auto Memory regression
signatures (composite drop, memory growth, consistency slide,
per-dimension ≥ 3-point drops). Exit 2 on composite regression so CI
can gate. Complement to `/judge --against HEAD~1`.
`tests/test_compare_runs.py` (12 cases).

### Version bumps

- `plugin.json` · `marketplace.json` · `SKILL.md` → `1.2.0`
- `CHANGELOG.md` — full Added / Changed / Tests sections for both
  2026-04-19 and 2026-04-20 sessions.
- `plugin.json.components.commands` now registers `./commands/compare.md`.

### Hard constraints honoured

- Offline-first preserved: LLM judge default **off**, MLflow adapter
  **parse-only** (never imports `mlflow`), LightEval shim **lazy-imports**.
- No new non-stdlib runtime deps in Proofloop core.
- No secrets in fixtures.
- 384 / 314 / 237 — test count never dropped below baseline at any
  intermediate commit.

### Out of scope (per the 2026-04-20 prompt)

- Rubric marketplace live index
- `verdict` PyPI shim
- Paid / hosted schema registry
- `verdict-airlock` scaffold — explicitly rejected on 2026-04-19 and
  reaffirmed on 2026-04-20

### Prompt references

Executes the 2026-04-19 prompt (Thread A only, Thread B skipped by
explicit user decision) and the 2026-04-20 prompt (N1–N8).
