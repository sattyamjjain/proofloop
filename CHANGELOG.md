# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.2] - 2026-04-30

Patch release. Three new rubrics, two new score-engine helpers,
five new CLI scripts. **926 tests green** (800 → 926, +126 new).
Offline-first invariant preserved; no new runtime dependencies.

> ⚠️ **`eu-ai-act-audit-trail` is NOT counsel-reviewed.** Issue
> O13 — passing the rubric is **NOT** a determination of EU AI
> Act compliance. The disclaimer lives in the rubric file itself
> (`skills/judge/rubrics/eu-ai-act-audit-trail.md`); read it
> before bundling outputs into a regulator handover.

### Added (2026-04-30 session, CC1–CC5 + T1–T3)

- **CC1 — Tool-output-rewrite trust-boundary rubric**
  (`skills/judge/rubrics/tool-output-rewrite.{md,weights.json,example.md}`).
  Five evidence dimensions (hook-rewrite-disclosure, no-rubber-stamp,
  no-credential-injection-on-rewrite, original-vs-rewritten-diff-bounded,
  audit-link-to-hook-source) covering the brand-new
  `hookSpecificOutput.updatedToolOutput` capability shipped in
  Claude Code v2.1.121 (2026-04-29). New helper
  `_detect_hook_rewrite_violations` in `score.py`. New scorecard
  field: `adjustments.tool_output_rewrite`. Adapter
  `claude_code.py` now tags hook-rewrite records with
  `[hook-rewrote: <tool>] [hook-byte-delta: <ratio>]`.
  Source: [code.claude.com — Claude Code v2.1.121 changelog (2026-04-29)](https://code.claude.com/docs/en/changelog).

- **CC2 — EU AI Act Articles 19/26 audit-trail rubric**
  (`skills/judge/rubrics/eu-ai-act-audit-trail.{md,weights.json,example.md}`).
  Seven evidence dimensions (log-retention-attestation,
  decision-logic-grounding, human-intervention-points,
  data-source-provenance, tool-use-attribution,
  no-shadow-decisioning, refusal-on-out-of-scope-data) plus an
  `audit_trail_complete` aggregate flag. **NOT counsel-reviewed**
  — the rubric file carries a NOT-LEGAL-ADVICE disclaimer in the
  header; passing the rubric is not a substitute for counsel
  review. New helper `_compute_eu_ai_act_audit_evidence` in
  `score.py`. New scorecard field: `adjustments.eu_ai_act_audit`.
  New script `eu_audit_export.py` produces a regulator-neutral
  CSV from a scorecard + transcript pair. See Issue O13.
  Sources: [helpnetsecurity.com (2026-04-16)](https://www.helpnetsecurity.com/2026/04/16/eu-ai-act-logging-requirements/),
  [artificialintelligenceact.eu/article/19](https://artificialintelligenceact.eu/article/19/),
  [artificialintelligenceact.eu/article/26](https://artificialintelligenceact.eu/article/26/).

- **CC3 — Berkeley RDI benchmark-gaming detector**
  (`skills/judge/scripts/benchmark_gaming_detector.py` + signature
  pack at `signatures/berkeley-rdi-2026-04-26.json`). Pure-stdlib
  detector that scans transcripts for the four exploit signatures
  Berkeley RDI published (harness-trust-pytest-self-report,
  reward-file-tamper, scoring-grep-target, short-circuit-trajectory).
  Wired into `score.py` via `_apply_benchmark_gaming_penalty` —
  active for `swe-bench-pro` / `terminal-bench` / `browser-agent`
  rubrics. Each detected exploit deducts 0.50 composite. New
  scorecard field: `adjustments.benchmark_gaming`. Berkeley's
  list covers SWE-bench, WebArena, OSWorld, GAIA, Terminal-Bench,
  FieldWorkArena, CAR-bench (the prompt's mention of tau-bench /
  AgentBench was a partial inaccuracy corrected at integration).
  See Issue O14 — signature pack will be refreshable via
  `--signatures-from <url>` in v1.4.3.
  Source: [rdi.berkeley.edu — How We Broke Top AI Agent Benchmarks (2026-04-26)](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/).

- **CC4 — Routines (research preview) trajectory adapter + rubric**
  (`skills/judge/rubrics/routine-execution.{md,weights.json}`).
  `claude_code.py` adapter detects `[routine_trigger: <id>]`
  markers (always honored) and (env-gated) "no human turn in
  first 5 lines" heuristic — when either fires, prepends
  `[trajectory_kind: routine]` sentinel. Score's consistency
  analyzer now reads the sentinel and relaxes std_dev tolerance
  buckets ~33% (cron-triggered runs cluster differently from
  interactive ones). Anthropic Routines is **research preview as
  of 2026-04-29**, NOT GA — rubric copy reflects that. Heuristic
  detection is opt-in via `VERDICT_DETECT_ROUTINE_HEURISTIC=1`
  per Issue O15.
  Sources: [anthropic.com/news/routines](https://www.anthropic.com/news/routines),
  [code.claude.com/docs/en/routines](https://code.claude.com/docs/en/routines).

- **T1 — `verdict audit-export` CLI**
  (`skills/judge/scripts/audit_export.py`). DPO-ready zip bundler
  for fleet-wide scorecards: `manifest.csv` (Article 19/26
  binary flags), `scorecards/*.json` (raw evidence),
  `transcripts-redacted/*.jsonl` (best-effort PII redaction),
  `methodology.md` (signal-to-Article mapping + disclaimer).
  Refuses to bundle `clinical-agentic-workflow` transcripts per
  Issue O16. Stdlib-only.

- **T2 — `verdict bench gaming-check` CLI**
  (`skills/judge/scripts/bench_gaming_check.py`). Thin user-
  facing wrapper around CC3's detector. `--strict` mode adds a
  configurable reasoning-turn floor (default 3). Returns 0 on
  clean, 1 on exploit / short trajectory, 2 on bad input.
  Intended for benchmark publishers / paper authors to lint a
  trajectory before posting the number.

- **T3 — `verdict hook lint` CLI**
  (`skills/judge/scripts/hook_lint.py` + two example hooks under
  `examples/hooks/`). Static-analyzer for `.sh` / `.bash` / `.py`
  / `.js` / `.mjs` / `.ts` PostToolUse hook scripts. Four rules:
  F1 (undisclosed mutation), F2 (missing source tag), F3 (error
  suppression without justification), F4 (literal credential in
  source). Strips comment-only lines so signal in commentary
  doesn't false-flag. Stdlib-only.

### Score-engine wiring

- `_analyze_consistency` now takes optional `transcript_lines` so
  it can detect the routine-trajectory sentinel and relax
  tolerance buckets.
- `_HOOK_SPECIFIC_OUTPUT_RE` matches both the flat dotted form
  (`hookSpecificOutput.updatedToolOutput`) and the nested JSON
  form (`"hookSpecificOutput":{"updatedToolOutput"`) so the CC1
  detector works with both adapter-tagged and raw-JSON
  transcripts.

### Tests

- `tests/test_tool_output_rewrite_rubric.py` — 14 tests
- `tests/test_claude_code_hook_rewrite_tagging.py` — 15 tests
- `tests/test_eu_ai_act_audit_rubric.py` — 13 tests
- `tests/test_eu_audit_export.py` — 12 tests
- `tests/test_benchmark_gaming_detector.py` — 12 tests
- `tests/test_benchmark_gaming_penalty_e2e.py` — 9 tests
- `tests/test_routine_trajectory_detection.py` — 9 tests
- `tests/test_routine_rubric.py` — 8 tests
- `tests/cli/test_audit_export.py` — 13 tests
- `tests/cli/test_bench_gaming_check.py` — 6 tests
- `tests/cli/test_hook_lint.py` — 15 tests

### Tracker hygiene

- ROADMAP_2026.md gains `### 2026-Q2 Cycle 7 (v1.4.2)` section.
- `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` bumped 1.4.1 → 1.4.2.
- README.md rubric count refreshed (24 → 27); script count
  refreshed (12 → 17).

### Open issues filed

- O12 — encoding-bypass on the hook-rewrite detector. Fix
  scheduled for v1.4.3 (schema-version-aware extractor).
- O13 — `eu-ai-act-audit-trail` rubric is **not counsel-reviewed**.
  Disclaimer is in the rubric file. Counsel review pending.
- O14 — Berkeley RDI signature library can drift on next paper
  revision. v1.4.3 will add `--signatures-from <url>`.
- O15 — routine-trajectory detection heuristic gated behind
  `VERDICT_DETECT_ROUTINE_HEURISTIC=1`. Promote to default in
  v1.4.3 after sample-set evaluation.
- O16 — `audit_export.py` PII redaction is best-effort regex.
  CLI refuses `clinical-agentic-workflow`; hardened redactor
  queued for v1.4.3.

### Honest deltas vs prompt

- Prompt claimed "scripts at 14"; actual was 12. Now 17.
- Prompt claimed Anthropic Routines was "GA expansion (rolling)";
  it is **research preview** as of 2026-04-29. Rubric copy and
  changelog reflect that.
- Prompt claimed Claude Code v2.1.121 shipped 2026-04-28; actual
  ship date is 2026-04-29.
- Prompt's Berkeley RDI benchmark list ("tau-bench, AgentBench")
  did not match the actual paper's list (which covers SWE-bench,
  WebArena, OSWorld, GAIA, Terminal-Bench, FieldWorkArena,
  CAR-bench). Signature pack reflects the actual paper.
- Prompt's "non-skippable" wrap-up included items outside this
  release's scope (PyPI publish — Verdict is a Claude Code
  plugin, not PyPI-distributed; Cowork marketplace re-rank — not
  an in-repo action; counsel-reviewed disclaimer — Issue O13,
  swap honored with NOT-LEGAL-ADVICE language in the rubric file
  but not a counsel sign-off).

## [1.4.1] - 2026-04-28

Patch release. One new composite rubric, one extension to an
existing rubric, two new CLI scripts. **800 tests green** (740 →
800, +60 new). Offline-first invariant preserved; no new runtime
dependencies.

### Added (2026-04-28 session, BB1 + BB2 + S1 + S3)

- **BB1 — Ship-readiness composite rubric**
  (`skills/judge/rubrics/ship-readiness.{md,weights.json,example.md}`).
  Seven binary ship-readiness floors mapped onto the canonical seven
  dimensions: reliability-p99-on-replay (≥0.95), safety-refusal-floor
  (≥0.95), cost-bound-honored (true), observability-completeness
  (≥0.90), rollback-discipline (true), human-in-loop-honesty (true),
  and regression-vs-prior-version (≤5%). Floors evaluated by the
  new `_apply_ship_readiness_floors` helper; thresholds tunable via
  the rubric's weights sidecar (`ship_floor_*` keys). New scorecard
  field: `adjustments.ship_readiness` carries `ship_ready` (bool),
  `failed_floors` (list[str]), and the parsed evidence dict. The
  composite only moves when the transcript advocates merging despite
  a failed floor — the rubric's "merge anyway" red flag, which caps
  composite at ≤ 5.0 and emits a critical issue.
- **BB2 — Perception-reality drift extension**
  (project-deal-commerce only). New helper
  `_compute_perception_reality_drift` parses
  `perception_value=$N.NN` / `reality_value=$N.NN` markers and emits
  `{perception_value, reality_value, drift_magnitude, drift_flag,
  threshold}` into `adjustments.perception_reality_drift`. Threshold
  configurable via the weights sidecar's `drift_flag_threshold` key.
  Issue O8: single-data-point anchor (Anthropic's +$2.45/item buyer
  savings) — informational; doesn't deduct.
- **S1 — `verdict ship-gate` CLI**
  (`skills/judge/scripts/ship_gate.py`). Pass/fail a release
  scorecard against three checks: ship_readiness floors, composite
  floor (default 7.0), and regression vs. baseline (default ≤ 5%).
  Returns 0 on pass, 1 on fail, 2 on bad input. `--output sarif`
  emits a SARIF v2.1.0 document the GitHub Actions security tab
  consumes.
- **S3 — `verdict judge-replay` CLI**
  (`skills/judge/scripts/judge_replay.py`). Re-scores a transcript
  with the currently-installed Verdict and asserts per-dimension
  delta ≤ tolerance (default 0.5) and composite delta ≤ tolerance
  (default 0.3) vs. a frozen baseline scorecard. Returns 0 on
  within-tolerance, 1 on drift, 2 on bad input.

### Tests

- `tests/test_ship_readiness_rubric.py` — 18 tests covering rubric
  files, floor parsing, threshold override, merge-anyway red flag,
  and end-to-end scoring via `build_scorecard`.
- `tests/test_perception_reality_drift.py` — 11 tests covering
  rubric gating, threshold override, multi-marker summing, and
  end-to-end emission of the drift block.
- `tests/test_ship_gate.py` — 16 tests covering load, evaluate,
  SARIF rendering, and CLI exit codes.
- `tests/test_judge_replay.py` — 15 tests covering load, diff,
  replay-self-stability, drift detection, and CLI exit codes.

### Tracker hygiene

- ROADMAP_2026.md gains `### 2026-Q2 Cycle 6 (v1.4.1)` section.
- `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` bumped 1.4.0 → 1.4.1.
- README.md rubric / script counts refreshed (23 → 24 rubrics,
  10 adapters unchanged, 12 → 14 scripts).

### Deferred

- S2 (SaaS dashboard) deferred per ROADMAP §5 — no SaaS pivot.
- BB3–BB6 (PaperArena / DeepSeek / Kimi / OfficeQA rubrics)
  scoped out of v1.4.1 pending market-signal verification.

## [1.4.0] - 2026-04-27

Minor release. Five new rubrics, one new adapter, two new
integrations / scripts, three additive scorecard fields. **740 tests
green** (619 → 740, +121 new). Offline-first invariant preserved;
no new runtime dependencies.

### Added (2026-04-27 session, AA1–AA6 + R2 + R3 + R4)

- **AA1 — Project Deal commerce rubric**
  (`skills/judge/rubrics/project-deal-commerce.{md,weights.json,example.md}`).
  Eight commerce concerns mapped onto the canonical seven dimensions;
  per-deployment-tunable economic-asymmetry guard via the
  `_apply_commerce_asymmetry_check` helper. Threshold defaults to
  $5.00 / item with ~2× headroom over Anthropic's published Project
  Deal asymmetry; configurable via the weights sidecar's
  `asymmetry_dock_threshold_usd` and `asymmetry_dock_amount` keys.
  New scorecard field: `adjustments.commerce_asymmetry`.
  Source: [anthropic.com — Project Deal](https://www.anthropic.com/features/project-deal).
- **AA2 — Agentic SAST + Brier calibration rubric**
  (`skills/judge/rubrics/agentic-sast-confidence.{md,weights.json,example.md}`).
  Eight SAST concerns including confidence-calibration measured as
  Brier loss against ground-truth labels in the transcript. New
  helper `_apply_brier_calibration` parses `[confidence:0.NN]` /
  `[ground_truth:true|false]` pairs. New scorecard field:
  `adjustments.brier_calibration`.
  Source: [helpnetsecurity — GitLab 18.11 Agentic SAST](https://www.helpnetsecurity.com/2026/04/17/gitlab-18-11-agentic-ai/).
- **AA3 — Function Hijacking robustness rubric**
  (`skills/judge/rubrics/function-hijacking-robustness.{md,weights.json,example.md}`).
  Eight client-side trust-boundary concerns. Ships with
  `skills/judge/scripts/replay_bfcl_attacks.py --mode=offline-fixture`
  for deterministic ASR aggregation in CI; `--mode=live-replay` is
  declared but reserved for v1.4.x (see Issue O5).
- **AA4 — GPT-5.5 differential rubric**
  (`skills/judge/rubrics/gpt-5-5-differential.{md,weights.json}`)
  + `_resolve_paired_baseline()` helper. Pairwise rubric: consume
  two scorecards (baseline + candidate), produce per-dimension
  delta + Cohen's d + regressed-dimension list. NOT a model-pricing
  registry; works for any pairwise model comparison.
  Source: [cnbc.com — OpenAI GPT-5.5 launch](https://www.cnbc.com/2026/04/23/openai-announces-latest-artificial-intelligence-model.html).
- **AA5 — Cloudflare Mesh dispatch wrapper**
  (`skills/judge/integrations/cloudflare_ai_gateway.py::dispatch_via_mesh`).
  Pure dict-in / dict-out: composes the Mesh-required headers
  (`x-mesh-agent-id`, `x-mesh-trust-level`, `x-mesh-evaluation-class`)
  on top of `verdict_as_eval_webhook`. No HTTP performed; the
  caller dispatches via Worker / MCP shim / urllib.
  Source: [cloudflare.com — Mesh launch](https://www.cloudflare.com/press/press-releases/2026/cloudflare-launches-mesh-to-secure-the-ai-agent-lifecycle/).
- **R2 — Browser Harness adapter + browser-agent rubric**
  (`skills/judge/adapters/browser_harness.py`,
  `skills/judge/rubrics/browser-agent.{md,weights.json}`,
  `tests/fixtures/browser-harness-trace.json`). Flattens
  `[navigate]` / `[click]` / `[fill]` / `[assertion]` /
  `[screenshot]` events. Credential values in fill events are
  redacted at extraction time (passwords, api_keys, secrets,
  tokens, card numbers, CVVs). Registered as `browser-harness` /
  `browser`; auto-detected via score-based dispatch.
- **R3 — HTML-printable scorecard variant**
  (`skills/judge/scripts/explain.py::render_html_printable`). New
  `--format html-printable` emits a single-file HTML scorecard with
  `@media print` CSS — browser "Print to PDF" generates a
  publication-ready document without weasyprint or any other PDF
  library. New CLI flags: `--cover`, `--signer`. Tagged
  `format_version: "explain.html.v1"`.
- **R4 — Local-only cost estimator**
  (`skills/judge/scripts/cost_estimator.py`). Per-scorecard cost
  estimate based on a stdlib-only USD-per-Mtok pricing table for
  Opus 4.7, Sonnet 4.6, Haiku 4.5, GPT-5.5, GPT-5.5 Pro, Gemini
  3.1 Pro. Direct estimate via `--input-tokens / --output-tokens /
  --model` or scorecard-driven via `--scorecard <PATH>` (reads the
  optional `llm_usage` block; returns zero when Verdict ran
  heuristics only). Override the pricing table via
  `--pricing-file PATH`. No SaaS coupling; no telemetry leaves the
  host.

### Changed (2026-04-27 session)

- Plugin / marketplace version → `1.4.0`.
- Adapter registry gains `browser-harness` / `browser`. Total: **10
  adapters**.
- Rubric count: **23** (5 new + 18 inherited).
- Score-based adapter dispatch (`detection_score`) extended to the
  new browser-harness adapter; `_DETECTION_SCORERS` list updated.
- `score.py` scorecard JSON gains:
  - `adjustments.commerce_asymmetry` (always present; zeroed when
    rubric isn't `project-deal-commerce`).
  - `adjustments.brier_calibration` (always present; null when
    rubric isn't `agentic-sast-confidence`).

### Tests (2026-04-27 session)

- New test files: `test_project_deal_rubric.py` (13),
  `test_agentic_sast_rubric.py` (14), `test_function_hijacking_rubric.py`
  (8) + `test_replay_bfcl_attacks.py` (13),
  `test_gpt_5_5_differential_rubric.py` (12),
  `test_cloudflare_mesh_dispatch.py` (11),
  `test_browser_harness_adapter.py` (20),
  `test_cost_estimator.py` (18). Plus 11 new tests added to
  `test_judge_explain.py` for HTML-printable output.
- Total suite: **740 tests green** (+121 vs v1.3.3).

### Honest deferrals

- **R1** (AgentBeats public leaderboard) — SaaS pivot deferred per
  ROADMAP §5.
- **AA3 live-replay mode** — needs CI secrets + opt-in workflow;
  queued for v1.4.x (Issue O5).
- **Issue O3** (clinical PHI dose-string false-positives) remains
  open; the clinical-agentic-workflow rubric stays at EXPERIMENTAL.

### Known issues

- **O4** — Project Deal commerce asymmetry threshold is anchored to
  Anthropic's single Project Deal data point. The
  `asymmetry_dock_threshold_usd` key in the weights sidecar makes
  this configurable, but adopters with their own marketplace data
  should calibrate before relying on the deduction in production.
- **O5** — Function-hijacking live-replay path is not implemented
  in v1.4.0. CI runs offline-fixture mode only.
- **O6** — Closed by R3 (HTML-printable variant lands instead of a
  PDF + weasyprint dep).

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
