# Verdict — Roadmap to Top 1% (April 2026)

**Starting point (Apr 2026):** v1.0.0 Claude Code plugin · 7-dimension scoring · 11 domain rubrics · 132 unit tests · stdlib-only Python 3.9+ · single-digit stars.
**Goal:** 1,000+ GitHub stars within 90 days. Higher confidence than the other three repos because the category is genuinely empty.

Read `ECOSYSTEM_STATE_2026-04.md` first.

---

## 1. The positioning advantage

This is the project with the shortest path to 1 k stars. Research found **no direct competitor** that ships as a Claude Code / Cowork plugin with hook-based auto-scoring + persistent scorecards + offline heuristics + per-domain rubrics. The community `agent-judge` skill is ~150 stars and lacks persistence, hooks, and rubrics. Anthropic has not shipped a first-party scorer. The plugin marketplace ecosystem (2,500+ marketplaces, 9,000+ plugins) is actively searched by the 747 k-member `/r/ClaudeAI` community that has no answer to "how do I measure my skills' quality over time."

**Verdict is first-mover in a visible category.** This is rare.

**Recommended tagline:** *"Auto-grade every Claude Code and Cowork skill execution on seven dimensions. No LLM call. No config. Just a scorecard."*

The "no LLM call" detail matters more than you think — every competitor (Braintrust, Langfuse, Phoenix, Helicone, Promptfoo, DeepEval, Ragas, LangSmith, Opik) requires a second LLM to grade the first. Cost-sensitive teams love the offline-heuristic angle.

---

## 2. Critical gaps vs April 2026 state of the art

### 2.1 Must-ship before launch

1. **Distribute as a marketplace plugin, not a loose skill repo.** Plugins consumed Skills in the 2025→2026 transition. Put a `.claude-plugin/marketplace.json` at the root and submit PRs to the three big community indexes:
   - `anthropics/claude-plugins-official` (official, highest trust signal)
   - `claudemarketplaces.com`
   - `aitmpl.com`
   - `buildwithclaude.com`
2. **Support the new `agent` hook event type** — Claude Code 2.1.x added agent hooks (60 s timeout, 50 turns). Verdict today handles `Stop` and `SubagentStop`; add `agent` so Verdict scores tool-using sub-agent invocations too.
3. **Routines support** — Routines (Apr 14, research preview) fire scheduled prompts without an interactive session. Verdict's hooks must not crash when the transcript lacks a user turn. Add a `--mode routine` flag.
4. **Opus 4.7 tokenizer** — the new tokenizer shifts token counts up to 35%. Today's efficiency dimension compares raw token counts; update the efficiency analyzer to use model-aware normalization.
5. **Cowork plugin-loading bug workaround** — document the GH #39400 workaround (zip upload vs marketplace install) prominently in the README.
6. **The heuristic brittleness issues** from the earlier `DEEP_ANALYSIS.md`:
   - Safety regex false-positives on discussion context (e.g., a transcript *discussing* `rm -rf /` instead of running it). Add a context window + sentiment sanity check.
   - TODO detection firing on docstring TODOs. Scope the rule to non-docstring lines.
   - Consistency dimension uses an arbitrary 7.0 baseline with no history. Either (a) drop the dimension until you have historical data, or (b) default to "neutral" (5.0) when history is empty.
   - Weight-sum invariant not enforced in code. Add a `validate_config()` at load time.

### 2.2 Features that widen the moat

1. **Small judge-model bootstrap option** — ship an **opt-in** path that calls Claude Haiku 4.5 (cheapest frontier model, $1/$5) or the Atla Selene 8B open judge for a second-opinion score. Default is still heuristic/offline; LLM is the premium mode. This covers the "but LLM-as-judge is more accurate" objection without betraying the offline-first positioning.
2. **Cross-ecosystem scoring** — today Verdict scores Claude Code transcripts. Extend to:
   - **OpenAI Codex** sessions (`.codex/` transcripts or CLI output capture).
   - **Cursor / Windsurf / Continue** agent sessions (via OpenAI-compatible session logs).
   - **Gemini CLI** sessions (new `gemini-cli` session format, v0.38+).
   - **Claude Cowork** session transcripts.
   A single plugin that scores across platforms is unique.
3. **Agent-airlock OTel input** — consume the OTel audit stream from agent-airlock and score a running agent live, not just post-mortem. Verdict becomes the real-time quality dashboard for your middleware. Cross-repo wedge.
4. **Verdict Studio** — a local dashboard (single-binary, no server) showing trends, per-skill radar charts, weekly digests, team rollups in Cowork.
5. **Per-rubric weight overrides** — today `judge-config.json` has global weights. Allow per-rubric overrides so e.g. the `security` rubric weights safety 0.4 vs the default 0.1.
6. **Rubric marketplace** — let users publish and fork rubrics. Seeded with your 11 rubrics; aim for 50 community rubrics in 90 days.
7. **Benchmark pack** — ship a `verdict benchmark` command that runs a curated transcript corpus through the scorer and asserts regressions. Pairs with CI.
8. **Regression-aware scoring** — detect when the same skill is executed on a newer model and the score changes significantly. Model-drift detection is underserved (Galileo Luna-2 does this; nobody else at the plugin level).
9. **`/judge --against commit HEAD~1`** — compare current skill output to the previous run on the same input. Git-native diff-aware scoring.
10. **Hook for scheduled weekly team digests** in Cowork (pairs with Anthropic Routines).

### 2.3 Naming and branding

`Verdict` is a good name. Keep it. Pair it with a mascot — a small stylized gavel icon — and a domain (`verdict.dev` or `getverdict.com`). Consistent branding across the marketplace listing, README, website, and demo GIF is worth ~30% star-conversion uplift based on the case-study research (Opik's rebrand from "CometLLM" is the canonical example).

---

## 3. Milestones and timeline

### Week 0 (polish + v1.1)

- Land the 5 correctness/compatibility fixes.
- Convert to a marketplace plugin with `marketplace.json`.
- Record a 30-second demo GIF: skill executes, Stop hook fires, Unicode scorecard prints in terminal.
- Record a 90-second Loom: show the auto-score flow, then the `/scorecard` trend view, then `/benchmark` delta vs standards.
- Acquire `verdict.dev` or `getverdict.com`.
- Design a gavel logo (Midjourney or a $100 Fiverr commission).

### Week 1 (launch)

- **Tuesday, 13:00 UTC** — HN submission: *"Verdict: auto-grade every Claude Code skill execution on seven dimensions, no LLM required."* Link the GIF, not the repo.
- Same day: `/r/ClaudeAI` post (747 k members, highest-leverage subreddit for this project). Format: "I built this plugin because I kept wondering if my skills were actually getting better or if I was just hallucinating improvement." Include screenshots.
- Submit PRs to `anthropics/claude-plugins-official`, `claudemarketplaces.com`, `aitmpl.com`, `buildwithclaude.com`.
- X thread: 8 tweets, lead with GIF, one tweet per dimension, final tweet links repo.
- DM 10 Claude Code creators (swyx, Theo, simonw, karpathy, and 6 smaller Claude-focused devs) with a personalized demo on their public repos.

### Weeks 2–4

- Cross-ecosystem support (Codex, Gemini CLI, Cursor, Continue). Each ecosystem adds a `/r/<ecosystem>` launch opportunity.
- Rubric marketplace MVP.
- Monthly "State of Claude Code Skills Quality" blog post, using aggregated anonymized scorecards from opt-in users. This is the leaderboard-ownership play (Aider pattern).
- Engage Anthropic's plugin team for official marketplace inclusion.

### Weeks 5–8

- Ship Verdict Studio (local dashboard).
- Small judge-model opt-in (Haiku 4.5 + Atla Selene).
- agent-airlock OTel integration: "airlock's audit stream + Verdict's scorecards = the agent observability stack."
- Cowork-specific features (team digests via Routines).

### Weeks 9–12

- Conference submissions: Latent Space Swyx podcast pitch (warm intro via Discord first), Changelog, ThePrimeagen's weekly dev-tool roundup.
- Verdict v2: rubric versioning, git-diff-aware scoring, regression-aware trends.
- Partner case studies — 3 teams showing year-over-year skill-quality improvement with Verdict.

### 2026-Q2 Cycle 2 (v1.3.0) — shipped 2026-04-24

New ecosystem and API-compat surface, driven by the April-2026 market
signals:

- **Inspect AI log adapter** — UK AISI's `inspect_ai` v0.3 stable
  release (2026-04-20) became the default eval harness for 200+
  published evaluations. Verdict now ingests its JSON logs directly
  (`adapters/inspect_ai_log.py`) so teams that already run Inspect
  can get Verdict scorecards without re-running their agents.
- **`managed-agents-2026-04-01` memory stitch** — Anthropic's
  parallel-agent shared-memory beta emits synthetic records into
  the JSONL transcript. Verdict tags these with
  `[managed-memory-pull]` / `[managed-memory-push]` so downstream
  analyzers can tell first-party reasoning from memory stitching.
- **Prompt caching on the LLM judge** — opt-in second-opinion pass
  now wraps the system prompt in a `cache_control` ephemeral block
  (5m default; `ENABLE_PROMPT_CACHING_1H=1` opts into the 1-hour
  extended beta). Cache hits / misses logged per call.
- **SWE-bench Pro rubric + contamination penalty** — Pro is the
  contamination-resistant successor to Verified. Rubric rewards
  instruction-literal edits; penalty of up to 1.5 composite deducts
  when transcripts reference Verified instance IDs.
- **Terminal-Bench trajectory adapter + rubric** — shell-task agents
  now get a dedicated rubric that weights command-safety + secret-
  leakage at 30%.
- **OTel GenAI semconv enrichment for MLflow adapter** — MLflow
  3.11.1 adopted OpenTelemetry GenAI semantic conventions. Verdict
  reads `gen_ai.request.model`, `gen_ai.usage.*`, and
  `gen_ai.response.finish_reasons` so v1.1.0's model-aware
  efficiency thresholds apply to MLflow traces without caller-side
  changes.

Baseline: 384 tests green pre-cycle. Shipped: 473 tests green (89
new), no new runtime deps, stdlib-only invariant preserved.

### 2026-Q2 Cycle 3 (v1.3.1) — shipped 2026-04-25

Patch cycle. Two additive items, no breakage to v1.3.0:

- `/judge --explain` rationale exporter (Markdown + JSON `explain.v1`)
- OWASP MCP Top 10 (beta) coverage rubric, Safety-weighted 0.50

506 tests green. Q1–Q4 SaaS-pivot product surfaces deferred (ROADMAP
§5 still stands).

### 2026-Q2 Cycle 4 (v1.3.2) — shipped 2026-04-26

Patch cycle. New adapter, EXPERIMENTAL clinical rubric, two adapter-
correctness fixes, two open-issue closures:

- **Z1** Gemini 3.1 Pro Deep Research adapter — flattens
  `research_plan` / `citations[]` / `verifier_notes` /
  `assistant_synthesis` blocks the existing `gemini_cli` adapter
  discarded.
- **Z2** EXPERIMENTAL clinical-agentic-workflow rubric — eight
  clinical concerns mapped onto the canonical seven dimensions; PHI
  redaction guard activates for this rubric only and deducts 2.0
  composite on leak. Ships at EXPERIMENTAL status; **do not market
  publicly** until Issue O3 (dose-string false-positive class) closes
  via real clinical-pilot calibration.
- **Z3** Inspect AI 0.3.x version-pin honesty — adds a one-shot
  stderr warning when the installed `inspect_ai.__version__` falls
  outside `>=0.3.180,<0.4.0`.
- **Z4** Cloudflare AI Gateway eval-webhook integration — pure
  dict-in / dict-out, no SDK dep.
- **Z5** Sandbox-aware self-score CI — workflow declares
  `CLAUDE_SANDBOX_CAPS` explicitly; new `scripts/sandbox_caps_check.py`
  verifies the declaration matches.
- **O1** Adapter detection collision fix — score-based dispatch
  replaces first-match-wins boolean fingerprints. Closes the
  inspect_ai_log / mlflow_trace collision that emerged after Y6.
- **O2** `/judge --explain` truncation cap — `--max-evidence-chars`
  flag (default 4000) keeps Markdown output under GitHub's 65 KB PR
  comment limit.

619 tests green (506 → 619, +113 new). No new runtime deps.

### 2026-Q2 Cycle 5 and beyond — forward look

- LiveCodeBench rubric (targeting v1.4.0).
- Official LMSYS Arena adapter pending data-licence clearance.
- Async streaming of `/judge` output.
- Anthropic marketplace inclusion (`anthropics/claude-plugins-official`).
- Issue O3: clinical PHI dose-string false-positive class — needs
  real clinical-pilot calibration before the rubric leaves
  EXPERIMENTAL.
- GPT-5.5 / GPT-5.5 Pro model-pricing registry (Y8 deferred from
  v1.3.x — needs new infrastructure surface).
- Claude Managed Agents thin tool-schema wrapper (Y9 deferred —
  awaits beta → GA transition).

---

## 4. What to measure

| Metric | Baseline | 30-day | 90-day | 1-year |
|---|---|---|---|---|
| GitHub stars | ~3 | 400 | 3,000 | 15,000 |
| Plugin installs (tracked via marketplaces) | 0 | 2,000 | 25,000 | 200,000 |
| Rubrics in marketplace | 11 | 25 | 75 | 300 |
| Supported ecosystems | 1 (Claude Code) | 3 (+Cowork, +Codex) | 6 | 10 |
| Monthly "State of Skills" reports published | 0 | 1 | 3 | 12 |
| Teams with weekly digests on | 0 | 5 | 50 | 500 |
| Discord members | 0 | 100 | 750 | 5,000 |

---

## 5. What *not* to do

- **Don't turn into another Braintrust/Langfuse.** The moat is the "offline heuristic + plugin-native" angle. If you pivot to a SaaS observability platform you're in a crowded $B-level commercial fight.
- **Don't add third-party Python dependencies.** stdlib-only is part of the pitch — `pip install` should be instantaneous, no supply-chain risk, no conflicts with user projects.
- **Don't over-weight consistency.** The arbitrary 7.0 baseline is a credibility bug. Either do it right (real historical calibration) or drop the dimension.
- **Don't try to be a benchmark** (MMLU-Pro / τ-bench / LiveBench). You score *your own skill executions*, not model capabilities. Different category; don't conflate in the marketing.

---

## 6. Distribution-specific tactic

Verdict's single strongest growth lever is being first in the Anthropic plugin marketplace with this category. The marketplace is searched by every new Claude Code user; being the #1 result for "evaluator" or "quality" nets passive installs forever. Priority actions to secure that:

1. Nominate to `anthropics/claude-plugins-official` immediately — it's reviewed by Anthropic's plugin team.
2. Brand the marketplace listing with a clear hero image, a 20-second looping GIF, and "zero config, zero LLM cost" framing in the first line.
3. Offer free rubric authoring + a team-digest setup call for the first 20 Cowork adopters. Anthropic's customer success team shares recommended plugins; be the one they share.

---

## 7. The CEO-readable one-pager

> *Verdict* is a Claude Code and Cowork plugin that auto-scores every skill and sub-agent execution on seven dimensions — correctness, completeness, adherence, actionability, efficiency, safety, consistency — using fast offline heuristics (no LLM call required). Persistent scorecards track quality over time; per-domain rubrics (code review, design, security, devops, and 7 more) tune the scoring to the work at hand; an opt-in small judge model adds a second-opinion pass when you want it. Verdict is the quality layer for any AI-coding stack — Claude Code, Cowork, Codex, Gemini CLI, Cursor, Continue — and it pairs with agent-airlock's runtime audit stream for end-to-end observability. Zero config, zero third-party dependencies, zero ongoing LLM cost. Install from the Claude plugin marketplace in one command.
