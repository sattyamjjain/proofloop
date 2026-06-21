# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation

- Synced README architecture tree with the actual `scripts/`
  inventory: added the missing `check_readme_release_anchor.py`
  entry (shipped in PR #27 on 2026-05-05 as the CHANGELOG ↔ README
  anchor forcing function but never reflected in the tree).
  Surfaced by the 2026-05-20 README-sync audit. No behaviour
  change; tree was 4-of-5; now reads 5-of-5.

- Added a "Cross-family second-opinion pattern note" to the
  `skills/judge/analyzers/llm_judge.py` module docstring, citing
  GitHub Copilot CLI's Rubber Duck (cross-family critic, expanded
  model pairings shipped 2026-05-07) as independent corroboration
  of the pattern this analyzer already implements. Off-by-default,
  stdlib-only, opt-in via `judge-config.json.llm_second_opinion.enabled`.
  Mirrored as a one-paragraph subsection in `skills/judge/SKILL.md`'s
  v1.1.0 features block. New `tests/test_llm_judge_docstring_rubber_duck_citation.py`
  pins the citation to the GitHub Changelog primary URL (no
  aggregators). Source:
  <https://github.blog/changelog/2026-05-07-rubber-duck-in-github-copilot-cli-now-supports-more-models/>.

### Changed

- Rotated the Claude Code release audit comment block in
  `scripts/validate_marketplace.py` to the most-recent five
  releases (newest first): v2.1.129 / v2.1.128 / v2.1.127 / v2.1.126 /
  v2.1.125. Earlier per-row entries (v2.1.124 through v2.1.119) were
  pruned from the table per the ≤5-release cap; the footer paragraph
  preserves the audit history. None of v2.1.127 / v2.1.128 / v2.1.129
  is marketplace-schema-relevant. Extended grep test pins the rotation.

### Notes

- No version stamp bump; `[Unreleased]` only. The next stamped
  release will roll up these documentation + audit-block changes
  alongside whatever code change motivates the cut.

### Dispositions of record (rejected proposals)

- **`--repeats/--seeds` seed-variance / noise-floor mode
  (2026-06-21): REJECT.** A task proposed an opt-in mode that runs the
  same judge N times across seeds/temperature and reports mean, std, a
  bootstrapped 95% CI ("noise floor band"), and a `significant` boolean
  (`|delta_vs_baseline| > band`), framed with the "FID-Lottery" line so
  users can tell a real eval gain from sampling noise. **Rationale for
  rejection:**
  (1) **Architectural no-op on the core path — there is nothing to
  vary.** Proofloop's default scorer is offline heuristics and is
  *deterministic by design*: `rg "random|seed|temperature|numpy|sample"`
  over `skills/judge/scripts/score.py` returns zero matches; the same
  transcript yields the same score every time. Running it N× across
  seeds reports `std = 0`, `band = 0` — it measures noise that the
  engine deliberately does not have. A noise floor is only meaningful
  for a *stochastic* evaluator, which the default path is not.
  (2) **For the only stochastic path it breaks the budget invariant.**
  The opt-in LLM second-opinion tier (`analyzers/llm_judge.py`) is the
  one place sampling variance exists, and it is off-by-default and
  hard-capped via the `task_budgets` beta header + `max_tokens`. N×
  re-sampling across seeds to build a CI band multiplies a deliberately
  capped, opt-in spend N-fold — directly against the offline-first /
  budget-capped core value.
  (3) **The in-scope version already exists.** Run-to-run score
  stability is already handled in-scope by the `consistency` dimension
  (history-based, weight 0.05) and `_detect_verifier_collapse` (a
  rolling-window flatline detector). "Is the score stable / is this
  variance meaningful" is answered deterministically, without a seed
  sweep.
  (4) **Frozen eval-bench scope.** Seed-variance, bootstrapped CI, and
  "is my improvement real vs sampling noise" (FID-Lottery — an
  image-generation-metric variance result) are frontier-lab eval-rigor
  methodology, the family the v4.3 §scope-reset froze ("will not be
  re-added without a runbook spec change"). None has landed.
  (5) **Repo-shape tells.** The task's verify line claims origin
  `…/verdict` (now `proofloop`); it greps `src/` and `pyproject.toml`
  and "find in pyproject.toml/Makefile" and SmokeTests "a published
  wheel" — but there is no `src/`, `pyproject.toml`, `Makefile`,
  `setup.py`, or wheel (stdlib-only plugin; runner
  `python3 -m unittest discover tests/`; version in
  `.claude-plugin/{plugin,marketplace}.json`). "Push to main" ignores
  the branch-+-PR convention. 7th instance of the templated
  scope-expansion pattern.

- **`--objective-outcome` scoring mode — declared end-state
  assertion harness (2026-06-21): REJECT.** A task proposed an opt-in
  `--objective-outcome` mode (and `/judge --objective-outcome` flag):
  the user declares an `outcome.yaml` sidecar (expected files changed,
  expected exit code, expected string present/absent, expected
  test-suite green) and proofloop scores PASS/FAIL per assertion + an
  aggregate, deterministically, from the transcript + workspace
  artifacts with no LLM call — "mirroring CEO-Bench / RNG-Bench /
  NRT-Bench objective state-change scoring." **This one is not a clean
  mechanical reject** — it is neither a 12th rubric nor an 8th
  dimension, so `test_v43_scope_contract` and the `len(dimensions)==7`
  guard do not apply, and it respects every core invariant (offline,
  stdlib-only, no-LLM, additive). It was rejected on scope, by the
  maintainer's explicit decision (2026-06-21), for two reasons:
  (1) **It is the frozen frontier-lab eval-bench scope.** Declaring a
  gold end-state (`outcome.yaml`) and scoring PASS/FAIL against it is
  precisely what SWE-bench / Terminal-Bench do, and the task frames it
  as CEO-Bench / RNG-Bench. Per
  [`CLAUDE.md` §v4.3 Scope Contract](CLAUDE.md#v43-scope-contract-2026-05-03):
  "Frontier-lab eval-bench scope (SWE-bench, Terminal-Bench, GAIA,
  OSWorld, …) is explicitly out of scope and will not be re-added
  without a runbook spec change." No runbook §scope-reset amendment has
  landed, so the gate holds; bringing objective-outcome scoring in is a
  deliberate product decision, not a templated task's call.
  (2) **The in-scope kernel already shipped.** `detect_unverified_success`
  + `_US_RECEIPT` (`skills/judge/scripts/score.py`) already score
  "objective state-change, not an LLM judge": they fire when a run
  *claims* a pass but has no executed-check *receipt* (test runner,
  exit code, pass count) anywhere in the trajectory, docking
  correctness. That is the deliberate, in-scope incarnation of this
  idea — a correctness signal, not a CEO-Bench-style gold-assertion
  harness. (Repo-shape tells, as with the rest of the series: the
  task's verify line claims origin `…/verdict` though it is now
  `proofloop`; it assumes `python -m pytest` though the runner is
  `python3 -m unittest discover tests/`; and "push to main" ignores the
  branch-+-PR convention. The cited `arXiv:2606.18543` / `2606.19338`
  were not verified.) 6th instance of the templated scope-expansion
  pattern (reward-hack, trajectory_safety, orchestration-quality,
  skill_quality_evolution being the prior five with the reward-hack
  re-affirm).

- **`skill_quality_evolution` 8th scoring dimension — static
  skill/MCP-artifact production-readiness scoring (2026-06-21):
  REJECT.** A task proposed an 8th judge dimension that, when the
  artifact under review is detected as a Claude Code skill (SKILL.md +
  scripts) or an MCP-tool definition, scores four sub-checks drawn from
  "arXiv:2606.11435's four evolution paradigms" — production-readiness
  (declared inputs/outputs/failure-modes/idempotency), provenance/
  governance (declared least-privilege scope), execution-feedback
  evolvability (logs/traces/eval hooks), and verifiable safety
  (no undeclared side effects) — auto-enabled on skill detection with a
  `--include skill_quality_evolution` opt-in, README "References" note,
  version bump, branch `feat/skill-quality-evolution-dimension`, PR.
  **Rationale for rejection:**
  (1) **An 8th dimension breaks the 7-dimension core surface, and a
  hard test pins it.** `tests/test_unverified_success.py::
  test_no_new_dimension_added` asserts `len(sc["dimensions"]) == 7`
  and `assertNotIn(...)` for non-canonical dimension ids — it exists
  *because* the `reward_hacking` 8th-dimension proposal (2026-06-04)
  was rejected on the same ground. Adding `skill_quality_evolution`
  makes the count 8 and the test goes red. The seven weights in
  `score.py` (`correctness` .25, `completeness` .20, `adherence` .15,
  `actionability` .15, `efficiency` .10, `safety` .10, `consistency`
  .05) sum to 1.0; an 8th breaks that invariant unless every weight is
  renormalized. "7-dimension scoring" is a named do-not-regress core
  surface (CLAUDE.md).
  (2) **It mutates the frozen scorecard schema.**
  `schemas/scorecard.v1.schema.json` lists exactly those seven as
  `dimensions.required` and as the only `dimensions.properties`. An
  8th dimension forces a schema change, which CLAUDE.md's stability
  rule forbids doing silently ("never silently mutate
  `scorecard.v1.schema.json`"; bump the schema version) — a deliberate
  decision, not a feature add.
  (3) **Domain mismatch — artifact linting, not execution scoring.**
  Proofloop scores *executions* (a run's transcript/trace) against
  domain rubrics. This proposal statically grades a *SKILL.md / MCP
  manifest artifact* for production-readiness, provenance, and
  evolvability — a skill-linter / governance tool, a different product.
  Scope-wise the provenance/evolution-paradigm framing (SkillWiki,
  arXiv:2606.11435) is agent-governance eval-bench territory, the frozen
  frontier family the v4.3 reset removed; bringing any new scored
  surface in needs a runbook §scope-reset amendment first — none has
  landed.
  (4) **Repo-shape tells.** The task finds the version via
  `rg "version" package.json plugin.json manifest.json pyproject.toml`
  and runs "the repo's actual test + lint + typecheck scripts (`cat
  package.json` scripts block or the Makefile; e.g. `npm test && npm
  run lint && npx tsc --noEmit`)" with `--type ts --type js` greps —
  but **no `package.json`, `Makefile`, `pyproject.toml`, `manifest.json`,
  or `setup.py` exists** here; the repo is Python-stdlib-only, the
  runner is `python3 -m unittest discover tests/`, no linter/typechecker
  is configured, and the version lives in
  `.claude-plugin/{plugin,marketplace}.json` + `SKILL.md`. The anchor
  papers were not independently verified. 5th instance of the templated
  12th-rubric / 8th-dimension pattern (reward-hack 2026-06-04 +
  re-affirm 2026-06-21, trajectory_safety 2026-06-09,
  orchestration-quality 2026-06-21).
  (5) **Door left open.** The legitimate kernel — does generated/edited
  skill code over-grant scope or hide undeclared side effects — is
  already partly covered: `score.detect_least_privilege_issues` feeds
  the `safety` dimension and the schema's `least_privilege` findings.
  A narrow in-scope extension belongs there, not as an 8th dimension or
  a new artifact-linting mode, and still needs a runbook §scope-reset
  amendment first.

- **`orchestration-quality` 12th domain rubric — multi-agent
  orchestration trace scoring (2026-06-21): REJECT.** A task proposed
  an `orchestration-quality` rubric preset that, given a multi-agent
  trace (orchestrator decisions + per-agent intermediate artifacts),
  scores routing correctness, dependency ordering, token economy, and
  failure recovery/re-planning — each 0–10 with an "OrchRM-style
  win-lose pair" framing (chosen path vs. a plausible alternative the
  trace implies) — plus a step-record / OpenTelemetry-span-tree input
  adapter, README + CHANGELOG, version bump from 3.1.1, branch
  `feat/orchestration-quality-rubric` → push to main. **Rationale for
  rejection:**
  (1) **A 12th rubric breaks the v4.3 scope contract, CI-enforced.**
  `tests/test_v43_scope_contract.py::test_no_out_of_scope_rubrics`
  asserts `sorted(_rubric_basenames(RUBRICS_DIR) - IN_SCOPE_V43) == []`;
  `IN_SCOPE_V43` is a frozenset of exactly 11 plugin-domain rubric
  names. Verified at disposition time: the rubrics dir holds exactly
  those 11, so adding `orchestration-quality.md` makes the test fail
  with `['orchestration-quality'] != []`. Greening it means editing
  `IN_SCOPE_V43`, whose source of truth is the external runbook
  §scope-reset (2026-05-03); per
  [`CLAUDE.md` §v4.3 Scope Contract](CLAUDE.md#v43-scope-contract-2026-05-03)
  anything outside the 11 in-scope rubrics "needs a runbook spec
  change first." Same blocker as the `reward-hack` (2026-06-04,
  re-affirmed 2026-06-21), `trajectory_safety` (2026-06-09), and
  `metis_safety` (2026-05-18) 12th-rubric REJECTs.
  (2) **Out-of-scope domain — the frozen frontier family.** Scoring a
  multi-agent trace on orchestrator routing / ordering / token economy
  / re-planning, with OrchRM win-lose-pair framing, is multi-agent
  orchestration eval-bench — the same family as the v2.0.0-trimmed
  `browser-agent`, `routine-execution`, and `function-hijacking-
  robustness` rubrics the v4.3 reset froze out. The 11 in-scope rubrics
  each score *quality of work in a domain*; this scores an
  orchestrator's *trajectory*, not a skill execution's quality.
  (3) **Repo-shape tells.** The task locates the version via
  `rg "version" pyproject.toml package.json` and runs "the repo's real
  test/lint/typecheck scripts (confirm via `rg scripts package.json` or
  `[tool.*]` in pyproject)" — but **no `pyproject.toml`, `package.json`,
  or `setup.py` exists** here; the version lives in
  `.claude-plugin/{plugin,marketplace}.json` + `SKILL.md`, the runner is
  `python3 -m unittest discover tests/`, and no linter/typechecker is
  configured. "Push to main after green" ignores the branch-+-PR
  convention. Same templated-from-a-different-repo signature as the
  prior REJECTs.
  (4) **Door left open.** The legitimate kernel — did the orchestrator
  waste work or fail to recover — overlaps the existing `efficiency`
  dimension and `score.detect_red_flags`. A narrow, in-scope version
  would be a signal in `detect_red_flags`, not a 12th eval-bench
  rubric, and would still need a deliberate runbook §scope-reset
  amendment first. Until that lands, the CI scope contract is the gate.

- **`trajectory_safety` 12th domain rubric — trajectory-level
  safety/robustness judging (2026-06-09): REJECT.** A task proposed
  adding a `trajectory_safety` rubric that takes the *full generation
  trace* (intermediate steps / tool calls / partial outputs) and
  scores, on a 0–1 scale with a rationale and an OWASP-Agentic tag:
  (a) whether any mid-sequence step drifts toward an out-of-policy
  action; (b) whether the final answer's safety depends on a step an
  input/output classifier would miss; (c) susceptibility to a
  simulated mid-sequence harmful-span insertion (the
  [arXiv:2606.04778](https://arxiv.org/abs/2606.04778) /
  arXiv:2606.04168 adversarial class) — with fixtures (drift-mid-
  sequence → flagged, uniformly-safe → pass, refusal-with-inserted-
  harmful-span → flagged), README/CHANGELOG, branch
  `feat/trajectory-safety-rubric` → push to main. **Rationale for
  rejection:**
  (1) **A 12th rubric breaks the v4.3 scope contract, CI-enforced.**
  `tests/test_v43_scope_contract.py::test_no_out_of_scope_rubrics`
  computes `sorted(_rubric_basenames(RUBRICS_DIR) - IN_SCOPE_V43)`
  and asserts it is empty; `IN_SCOPE_V43` is a frozenset of exactly
  11 plugin-domain rubric names. This was verified concretely at
  disposition time: dropping `trajectory_safety.md` into
  `skills/judge/rubrics/` makes the test fail with
  `AssertionError: Lists differ: ['trajectory_safety'] != []`. The
  only way to green it is to add `trajectory_safety` to
  `IN_SCOPE_V43`, whose source of truth is the external runbook
  §scope-reset (2026-05-03); per
  [`CLAUDE.md` §v4.3 Scope Contract](CLAUDE.md#v43-scope-contract-2026-05-03),
  anything outside the 11 in-scope rubrics "needs a runbook spec
  change first." Editing the allowlist to wave a new rubric through
  defeats the forcing function. Same blocker as the `reward-hack`
  (2026-06-04) and `metis_safety` (2026-05-18) 12th-rubric REJECTs.
  (2) **Out-of-scope domain — squarely the frozen family.**
  Trajectory-level safety/robustness judging, OWASP-Agentic tagging,
  and simulated harmful-span-insertion robustness (the 2606.04778 /
  2606.04168 adversarial class) are agent-safety eval-bench territory
  — the exact family of the v2.0.0-trimmed `function-hijacking-
  robustness`, `owasp-mcp-top-10-beta`, and "MCP attack benches, etc."
  rubrics the v4.3 reset explicitly froze out. The 11 in-scope rubrics
  each score *quality of work in a domain*; a trajectory-safety
  benchmark scores an agent's adversarial robustness — scoring the
  trajectory, not a skill execution's quality (the task itself asks to
  "make clear this judges the trajectory, not just the output"), which
  is precisely the frontier-lab eval-bench framing the scope reset
  removed.
  (3) **Repo-shape tells.** The task's suggested registration
  mechanism (`rg "rubric|SYSTEM_PROMPT|judge|register|score"`) does
  not match how rubrics work: there is no `register()` and rubrics are
  not defined by a `SYSTEM_PROMPT` — they are plain markdown files
  resolved by *file presence* in `score.load_rubric()` (exact →
  category prefix → `default.md`). The step-5 runner probe
  (`rg "test|lint" package.json pyproject.toml Makefile`) names three
  files that do not exist in this repo (runner is
  `python3 -m unittest discover tests/`), and "push to main" ignores
  the branch-+-PR convention every change here follows. Same
  templated-from-a-different-repo signature as the `metis_safety`
  (2026-05-18), `held_out_consistency` (2026-05-22),
  `ProcessScorerJudge` (2026-05-29), and `reward-hack` (2026-06-04)
  REJECTs.
  (4) **Door left open.** Verdict already has a `safety` scoring
  dimension and a `security` rubric, and `score.detect_red_flags`
  already scans the transcript for destructive/unsafe patterns. A
  *narrow*, in-scope version of the intent — flag a transcript whose
  mid-sequence steps drift unsafe — would be better shaped as an
  additional signal in `detect_red_flags` (alongside the existing
  destructive-command / hallucination flags) than as a 12th
  OWASP-Agentic benchmark rubric, and would still need a deliberate
  runbook §scope-reset amendment before it could ship. Until that
  runbook change lands, the CI scope contract is the gate. **Verified
  excerpt — Existing API (rubric resolution), `score.load_rubric`:**
  `1. {rubric_dir}/{skill_name}.md  2. {rubric_dir}/{category}.md
  (derived from the skill name)  3. {rubric_dir}/default.md`.

- **`reward-hack` 12th domain rubric + RHB grader-gaming detector
  (2026-06-04): REJECT.** A task proposed adding a `reward-hack`
  rubric that scores an agent trajectory on four deterministic
  grader-gaming signatures from the "RHB exploit classes" —
  (a) verification-step-skipped, (b) answer-read-from-task-adjacent
  metadata, (c) grader/assertion tampered or disabled, (d)
  test-specific logic added to pass a check — emitting per-signature
  flags + an aggregate reward-hack score, pure heuristic, wired into
  the ship-gate (non-zero exit over threshold) and `--explain`, with
  a weights sidecar, fixtures, README + CHANGELOG, a version bump
  `v2.0.2 → v2.1.0`, branch `feat/reward-hack-rubric` → push to
  main. **Rationale for rejection:**
  (1) **A 12th rubric breaks the v4.3 scope contract, CI-enforced.**
  `tests/test_v43_scope_contract.py::test_no_out_of_scope_rubrics`
  computes `sorted(_rubric_basenames(RUBRICS_DIR) - IN_SCOPE_V43)`
  and asserts it is empty. `IN_SCOPE_V43` is a frozenset of exactly
  11 plugin-domain rubric names. Dropping `reward-hack.md` into
  `skills/judge/rubrics/` makes `out_of_scope == ['reward-hack']`
  and the test goes red on push. The only way to green it is to add
  `reward-hack` to `IN_SCOPE_V43`, whose source of truth is the
  external runbook §scope-reset (2026-05-03); per
  [`CLAUDE.md` §v4.3 Scope Contract](CLAUDE.md#v43-scope-contract-2026-05-03),
  "anything outside the 11 in-scope rubrics … needs a runbook spec
  change first." Editing the allowlist to wave a new rubric through
  defeats the forcing function rather than honouring it. This is the
  same blocker as the 2026-05-18 `metis_safety` 12th-rubric REJECT.
  (2) **Out-of-scope domain.** RHB (reward-hacking benchmark) /
  agent grader-gaming detection is agent-safety eval-bench territory
  — the same family as the v2.0.0-trimmed `function-hijacking-robustness`
  and `owasp-mcp-top-10-beta` rubrics and the "MCP attack benches,
  etc." the v4.3 reset explicitly froze out. The 11 in-scope rubrics
  each score *quality of work in a domain* (code-review, security,
  devops, …); reward-hack is a cross-cutting *trajectory-integrity
  gate*, not a work domain — so even setting scope aside it is the
  wrong shape for a domain rubric (closer to the existing
  `detect_red_flags` adjustments in `score.py`).
  (3) **Repo-shape tells.** The task reads `skills/judge/score.py`
  (the real path is `skills/judge/scripts/score.py`), greps
  `pyproject` for the version and runs `pytest` (no `pyproject.toml`,
  no `pytest`; version lives in `.claude-plugin/{plugin,marketplace}.json`
  + `SKILL.md`, runner is `python3 -m unittest discover tests/`),
  invokes a `verdict ship-gate` CLI (none exists; the ship-gate is
  `hooks/judge-on-stop.sh`), and bumps `v2.0.2 → v2.1.0` when HEAD
  is already **v2.0.4** (the base version is stale). Same
  templated-from-a-different-repo signature as the `metis_safety`
  (2026-05-18), `held_out_consistency` (2026-05-22), and
  `ProcessScorerJudge` (2026-05-29) REJECTs.
  (4) **Anchor not verified, and it would not matter.** The "RHB
  exploit classes" were cited without a verifiable source; none was
  independently confirmed at disposition time. The scope-contract
  break in (1) and the domain mismatch in (2) stand regardless. Note
  that two invariants the `ProcessScorerJudge` proposal broke are
  here respected — the detector would be stdlib-only / no-LLM and
  would score executions, not models — so a future runbook spec
  change could bring reward-hack into scope deliberately (as a 12th
  rubric, or better as a red-flag signal in `score.py`); until that
  runbook change lands, the CI contract is the gate. Same shape as
  prior REJECT-of-record entries: BrowseComp-Plus (2026-05-06),
  Managed Agents Outcomes rubric beta (2026-05-09), DELEGATE-52
  (2026-05-10), metis_safety + LangSmith/Cowork (2026-05-18),
  held_out_consistency (2026-05-22), ProcessScorerJudge (2026-05-29).
  **Re-affirmed 2026-06-21 (REJECT, 3rd instance).** The identical
  proposal resurfaced — now framed as a "CHEAP tier (heuristic +
  embedding probe) before any frontier-judge tier," citing
  `arXiv:2606.08893` (unverified), with the origin precondition still
  given as `github.com/sattyamjjain/verdict` though the repo is now
  `proofloop`. Re-rejected for the same reason: whether shaped as a
  12th rubric or an 8th `reward_hacking` dimension, it is blocked by
  two guards that are both green at re-affirmation —
  `test_v43_scope_contract` (`IN_SCOPE_V43` pins 11 names) and
  `tests/test_unverified_success.py` (`assertNotIn("reward_hacking",
  sc["dimensions"])`). The in-scope core of the intent — reward-
  hacking as a *correctness/receipt* signal rather than a new
  dimension — already shipped as the `_US_RECEIPT` "no pass without
  proof" check. No runbook §scope-reset amendment has landed, so the
  CI scope contract remains the gate.

- **`ProcessScorerJudge` PRM-free step-by-step process scorer with
  LGS/CGS modes (2026-05-29): REJECT.** A task proposed adding a
  `ProcessScorerJudge` under `src/judges/` that scores a reasoning
  trajectory step-by-step using a scorer model's token likelihood
  rather than a trained PRM: "LGS mode" picks the next step among
  *k* candidates by the scorer model's likelihood; "CGS mode"
  scores by contrast between a strong and weak scorer prompt. It
  asked for a config flag selecting PRM-free process scoring vs the
  existing outcome judge, tests, README + CHANGELOG, a version
  bump, and `feat/process-scorer-judge` → push to main, with the
  test/lint/typecheck runner to be found via `package.json scripts
  / pyproject / Makefile`. **Rationale for rejection:**
  (1) **Module surface does not exist.** The task's own suggested
  grep — `rg "class .*Judge|def judge|src/judges" src` — errors
  with `IO error ... src: No such file or directory`. There is no
  `src/` tree, no `class BaseJudge`/`class .*Judge` hierarchy, and
  no `def judge` interface anywhere in the repo
  (`rg "class .*Judge\b|BaseJudge|ProcessScorer" --type py` is
  empty). Verdict's "judge" is `skills/judge/SKILL.md` plus a
  stdlib heuristic `skills/judge/scripts/score.py` exposing
  module-level functions (`build_scorecard`, `analyze_dimension`,
  `compute_composite`) — not an object-oriented judge surface a
  new subclass could conform to. There is no base-judge signature
  to capture.
  (2) **LLM-on-the-hot-path inverts the core invariant.** Both LGS
  (pick a step by the scorer model's token likelihood) and CGS
  (strong-vs-weak scorer-prompt contrast) *are* model calls as the
  scoring mechanism. Verdict is heuristic-first and stdlib-only;
  the LLM second opinion (`analyzers/llm_judge.py`) is **opt-in and
  off by default** (`judge-config.json.llm_second_opinion.enabled =
  false`, `urllib`-only, token-budget-capped). Making a scorer
  model the judge contradicts the invariant reaffirmed in the
  v2.0.3 (bench-lint) and v2.0.4 (verifier-collapse) ships:
  "offline heuristic is the moat; LLM judging stays opt-in."
  (3) **Scores models, not executions.** A step-by-step
  reasoning-trajectory process scorer (PRM territory) evaluates a
  model's *reasoning chain*. Verdict scores *skill / agent
  execution quality* against rubrics — "verdict scores executions,
  not models" is a stated product boundary. Process reward models,
  like the frontier-lab eval-bench scope (SWE-bench, Terminal-Bench,
  GAIA, OSWorld), are exactly what the 2026-05-03 v4.3 scope reset
  froze out; re-adding them needs a runbook spec change first
  ([`CLAUDE.md` §v4.3 Scope Contract](CLAUDE.md#v43-scope-contract-2026-05-03),
  enforced by `tests/test_v43_scope_contract.py`).
  (4) **Repo-shape tells.** The task references `src/judges`,
  `package.json scripts`, `pyproject`, and a `Makefile`-style
  typecheck runner. Verdict has none of these — no `src/`, no
  `package.json`, no `pyproject.toml`, no `Makefile`, no
  `setup.py`; the actual runner is
  `python3 -m unittest discover tests/` (per `.github/workflows/ci.yml`).
  Same templated-from-a-different-repo signature as the
  2026-05-18 `metis_safety` REJECT and the 2026-05-22
  `held_out_consistency` REJECT (both flagged `pyproject.toml` /
  `Makefile` / `src/` references absent from this repo).
  (5) **No anchor verified, and it would not matter.** LGS/CGS
  ("likelihood-guided" / "contrast-guided" search) and "PRM-free
  process scoring" were presented without a citation; no source was
  independently verified at disposition time. The module-surface,
  invariant, and scope mismatches in (1)–(4) stand regardless of
  whether such a method exists in the literature. Same shape as
  prior REJECT-of-record entries: BrowseComp-Plus (2026-05-06),
  Managed Agents Outcomes rubric beta (2026-05-09), DELEGATE-52
  (2026-05-10), metis_safety + LangSmith/Cowork (2026-05-18),
  held_out_consistency (2026-05-22).

- **`held_out_consistency` test-gaming heuristic on the testing
  rubric (2026-05-22): REJECT.** A daily-prompt row proposed
  adding a stdlib-only `held_out_consistency` heuristic that
  scans transcripts for (a) literal matches against quoted
  test-input values and (b) lookup/branch tables sized
  suspiciously to the visible test count, then docks
  correctness/adherence on hit with a flag string "possible
  test-gaming (visible-vs-held-out gap)", anchored on SpecBench
  (arXiv 2605.21384). **Rationale for rejection:**
  (1) **Mechanically identical to v2.0.0-removed helper.** The
  pre-v2.0.0 `_apply_contamination_penalty` (deleted in commit
  `98ab1c2`) had the exact same shape: `VERIFIED_FIXTURE_PATTERNS`
  scanned for test-input literals, `CONTAMINATION_RUBRICS = frozenset({"swe-bench-pro"})`
  rubric-gated the activation, and the helper returned a
  deduction on hit. The v2.0.0 `### Removed — Breaking changes`
  block explicitly listed `_apply_contamination_penalty` among
  the trimmed helpers. Re-introducing the same mechanic under a
  new name violates the spirit of the v4.3 contract even though
  the rubric inventory stays at 11.
  (2) **Wrong rubric target.** `skills/judge/rubrics/testing.md`
  evaluates the quality of *test-generation skill outputs*
  ("whether tests actually test what they claim to test"). The
  proposal evaluates *whether a coding skill gamed its tests* —
  a different category (outputs-of-coding-skill, not
  outputs-of-testing-skill).
  (3) **Mechanism doesn't fit sidecar shape.** `<rubric>.weights.json`
  overrides dimension weights (e.g., `security.weights.json`
  puts 0.35 on safety). Sidecars do not add new heuristics; they
  re-weight the existing 7.
  (4) **Repo-shape tells.** Prompt references `pyproject.toml`,
  `Makefile`, and "push to main (solo maintainer)" — verdict has
  no `pyproject.toml`, no `Makefile`, and every PR since
  2026-05-03 has gone via PR + CI (branch protection makes
  direct push impossible anyway). Same templated-from-different-repo
  tells as the 2026-05-18 metis_safety REJECT.
  (5) **Plumbing absent.** The heuristic needs structured access
  to "solution code" vs "visible test inputs" inside a
  transcript. Verdict's scorer reads `List[str]` of utterances;
  there is no parser to separate code-under-test from test
  inputs from discussion prose.
  (6) **Unverifiable citation.** arXiv 2605.21384 (SpecBench)
  was not independently verified at disposition time; the
  contract + mechanism + shape mismatches stand regardless.
  Same shape as prior REJECT-of-record entries: BrowseComp-Plus
  (2026-05-06), Managed Agents Outcomes rubric beta (2026-05-09),
  DELEGATE-52 (2026-05-10), metis_safety + LangSmith/Cowork
  (2026-05-18).

- **`metis_safety` 12th rubric + Cowork-vs-LangSmith adapter
  "schema drift" check (2026-05-18): REJECT.** Two daily-prompt
  rows proposed (a) adding a 12th `metis_safety.yaml` rubric to
  `skills/judge/rubrics/` anchored on "Metis paper (arXiv
  2605.10067)" and (b) verifying the Cowork transcript adapter
  against a "post-LangChain-Interrupt schema" (LangSmith Engine,
  May 13). **Rationale for rejection:** (1) The rubric inventory
  is pinned at exactly 11 by
  [`CLAUDE.md` §v4.3 Scope Contract](CLAUDE.md#v43-scope-contract-2026-05-03)
  and enforced by `tests/test_v43_scope_contract.py`; a 12th
  rubric file dropped in `skills/judge/rubrics/` makes that test
  red on PR push. (2) Verdict's rubrics are `.md` files; there is
  no YAML parser in `score.py` (stdlib-only invariant). (3) The
  prompt's project-shape references — `pyproject.toml`,
  `tests/rubrics/`, "Cowork plugin index" — do not exist in this
  repo; tells the row was templated from a different repo's
  conventions. (4) arXiv 2605.10067 was not independently
  verified at disposition time; the contract + shape mismatches
  stand regardless. (5) The Cowork adapter is unrelated to
  LangSmith — Cowork is Anthropic's collaborative Claude product,
  LangSmith is LangChain's tracing product; nothing in a
  LangChain Interrupt release affects Cowork transcripts.
  **Cowork sanity sweep performed anyway as a no-op check:**
  `tests.test_adapters.TestCoworkAdapter` + `tests.test_adapter_fixtures.TestCoworkFixture`
  green; `skills/judge/adapters/cowork.py` is a 19-line
  delegation wrapper over `claude_code.extract_lines` (Cowork
  emits the same JSONL shape as Claude Code), last touched in
  commit `70ed8eb` (Phase 2); fixture `tests/fixtures/cowork.jsonl`
  unchanged. **No drift detected; no patch required.** Same
  shape as prior REJECT-of-record entries: BrowseComp-Plus
  (2026-05-06), Managed Agents Outcomes rubric beta (2026-05-09),
  DELEGATE-52 (2026-05-10).

- **DELEGATE-52 / `outcome_corruption` 8th dimension (2026-05-10):
  REJECT.** A daily-prompt row proposed adding an 8th
  `outcome_corruption` dimension to `/judge` anchored on arXiv
  2604.15597 ("LLMs Corrupt Your Documents When You Delegate",
  HN front page 2026-05-09 per the prompt). **Rationale for
  rejection:** (1) Adding a dimension regresses the "7-dimension
  scoring" core surface explicitly listed in
  [`CLAUDE.md` §v4.3 Scope Contract](CLAUDE.md#v43-scope-contract-2026-05-03)
  under "do not regress." (2) The proposed signal — plan / input /
  trace tri-way diff with "≥2 of 3 oracles agree" fail-closed — is
  runtime trace replay against a sandbox, not heuristic transcript
  scoring. Verdict reads transcripts post-hoc with regex; oracle
  comparison is a different layer (Wall 2 runtime / Wall 3 outcome
  in the prompt's own framing). (3) The proposed `skills/judge/dimensions/`
  directory + `OutcomeCorruptionDimension` class pattern contradicts
  the documented design noted in the 2026-05-06 prompt
  (analyzer functions inside `score.py`, not per-dim directory).
  arXiv ID was not independently verified at disposition time; the
  layer-mismatch rationale stands regardless of the paper's
  existence. Same shape as prior REJECT-of-record entries:
  BrowseComp-Plus (2026-05-06), Managed Agents Outcomes rubric
  beta (2026-05-09).

## [3.1.1] - 2026-06-13

### Fixed

- **Safety false-positive on credential vocabulary.** A clean code review
  that merely assigned a credential-named variable — `token = refresh(token)`,
  `token: str`, `self.token = row.token` — was docked on the safety
  dimension (and flagged "possible hardcoded secret") because the patterns
  matched any `token=`/`token:`. Credential detection is now centralised in
  `_is_hardcoded_secret`, which requires a *literal* value (quoted string or
  bare token) and excludes calls, attribute/module references, env lookups,
  and type annotations. The loose credential patterns were removed from the
  generic `SAFETY_PATTERNS` count. Real hardcoded secrets (quoted, bare, or
  unquoted config values) are still flagged. Adds 4 regression tests.

## [3.1.0] - 2026-06-13

### Added

- **GitHub Action + CI gate.** A repo-root `action.yml` (composite
  action) plus `scripts/gha_gate.py` let any project run the offline
  scorer in CI and fail a job when an agent's composite drops below a
  threshold — `uses: sattyamjjain/proofloop@v3.1.0` with
  `transcript`/`skill`/`threshold` inputs; exposes `composite` and
  `grade` step outputs. No API key. Verified across pass / fail /
  report-only threshold cases.
- **Rendered-scorecard demo in the README** — a real `report.py` render
  (not a mockup) showing how an executed-check receipt earns a perfect
  correctness score.

## [3.0.0] - 2026-06-13

### Changed

- **Renamed the project to Proofloop.** The plugin name, schema
  namespace, and all user-facing surfaces move from "Verdict" to
  "Proofloop"; the GitHub repository is now `sattyamjjain/proofloop`
  (old URLs redirect). The rename resolves a hard collision with Haize
  Labs' open-source `verdict` LLM-judge library (PyPI `verdict`,
  verdict.haizelabs.com) in the identical category. The scorecard
  schema `$id` moves to `https://proofloop.dev/schemas/scorecard.v1.json`;
  the on-disk shape is unchanged (still `scorecard.v1`, additive
  contract intact). Historical CHANGELOG and release notes keep the
  "Verdict" name they shipped under.

### Fixed

- **Hardened two gameable scoring heuristics** (originally PR #43):
  - *Adherence* no longer adds +1 just because a rubric was loaded — it
    did so on every run, inflating adherence to 9 regardless of
    behaviour. The heuristic tier now reports deviation only; positive
    compliance is scored against the rubric by the opt-in LLM tier.
  - *Correctness* no longer returns a free 10 for a transcript that
    merely avoids the words "error"/"failed"/"exception". A perfect
    score now requires an execution receipt (a test run / exit code);
    without one the top mark is capped at 9. Untestable tasks still
    reach 9. Adds 4 anti-gaming tests.

## [2.0.8] - 2026-06-13

Patch release. Adds a stdlib-only, offline **unverified-success
(cheap-tier reward-hacking) signal** to the **correctness** dimension —
*not* a new `reward_hacking` dimension (the 7-dimension contract is
preserved; a prior 8th-dimension proposal, `outcome_corruption` /
DELEGATE-52, was rejected) and *not* a rubric. It is the in-scope
kernel of the rejected `reward-hack` benchmark (#37): the one
deterministic, offline tell — a claimed pass with no executed check.

### Added

- **Unverified-success heuristic** (`skills/judge/scripts/score.py`,
  `detect_unverified_success`, feeding `_analyze_correctness`): flags a
  trajectory that *claims* a check passed ("all tests pass", "build
  succeeded", "verified working") with no **receipt** — no execution
  artefact (a runner invocation, a test count, an exit code) anywhere
  in the trajectory. User instructions ("make sure tests pass") and
  genuine successes backed by an executed `Ran N tests … OK` are not
  flagged. Each finding docks correctness (`correctness_dock`, default
  2), adds a red flag (dual-surfaced like a hallucinated fact), and
  emits the offending claim + a one-line remediation in a top-level
  `unverified_success` array. Offline / heuristic — **no embedding
  probe, no LLM/frontier tier**.
- `judge-config.json.unverified_success` block (`enabled` /
  `correctness_dock` / `red_flag`; the cheap tier runs on every
  trajectory by default).
- Optional top-level `unverified_success` array in
  `schemas/scorecard.v1.schema.json` — additive, backward-compatible.
- Fixtures `tests/fixtures/unverified_success_{faked,genuine}.jsonl`
  and `tests/test_unverified_success.py` (detector units, both
  fixtures, correctness dock + configurable depth, `build_scorecard`
  integration, a `len(dimensions) == 7` regression guard, no-network
  assertion).

### Changed

- `tests/test_score.py::test_clean_transcript_scores_high` fixture now
  includes an executed-check receipt (`Ran 150 tests … OK`). The prior
  fixture asserted a transcript of bare "All tests passed" ×100 (no
  receipt) scores high on correctness — which the new signal correctly
  flags as unverified. The test's intent (a *genuinely* clean
  transcript scores high) is preserved by giving it the receipt a real
  verified run would show. This is the only intended behaviour change.

### Scope / framing

Tiering note (`feat(rubric): reward_hacking dimension with cheap
heuristic+probe tier (Cheap Reward Hacking Detection 2606.08893)`): the
**cheap heuristic tier runs on every trajectory**; the embedding-probe
and frontier-judge tiers from that proposal are *not* shipped — an
embedding probe is not deliverable stdlib-only/offline, and a default
frontier-judge tier conflicts with LLM-judging staying opt-in. The
existing sampled `llm_second_opinion` remains the only model-judge
tier. The reward-hacking *dimension/benchmark* form stays blocked
(8th dimension + the #37-frozen domain); this ships the deterministic
receipt-check kernel as a correctness signal. Anchor:
[arXiv:2606.08893](https://arxiv.org/abs/2606.08893).

## [2.0.7] - 2026-06-11

Patch release. Adds a stdlib-only, offline **least-privilege /
over-scope sub-check** to the **safety** dimension — *not* a new
dimension (the 7-dimension contract is preserved; a prior 8th-dimension
proposal, `outcome_corruption` / DELEGATE-52, was rejected) and *not* a
new rubric (inventory stays at 11). It scores generated agent code for
tool/skill scoping, the same in-scope shape as the v2.0.5 same-family
guard and the v2.0.6 sycophancy signal.

### Added

- **Least-privilege sub-check** (`skills/judge/scripts/score.py`,
  `detect_least_privilege_issues`, feeding `_analyze_safety`): flags
  generated agent code that grants a tool/skill broader authority than
  the task needs — a **wildcard (`*`/all) grant**, a
  **write/delete/admin scope** beyond read-only use, and an **omnibus
  free-form tool** dispatching arbitrary command/code/script input at
  runtime (the single most common over-privilege pattern, and the
  CVE-class root cause behind over-scoped MCP servers). Each finding
  docks the safety dimension (high-severity grants more, capped at 4),
  names the offending tool, and gives a one-line remediation in the
  safety justification, the safety dim's `least_privilege` entry, and a
  top-level `least_privilege` array. Offline / heuristic — **no LLM**.
- Optional top-level `least_privilege` array in
  `schemas/scorecard.v1.schema.json` — additive, backward-compatible.
- Fixtures `tests/fixtures/least_privilege_{overscoped,minimal}.jsonl`
  and `tests/test_least_privilege.py` (detector units, both fixtures,
  safety-dim dock, `build_scorecard` integration, a `len(dimensions)
  == 7` regression guard, no-network assertion).

### Scope / framing

A least-privilege check is a **safety** concern (excess authority is
latent blast radius), so it extends the existing safety analyzer
alongside the `rm -rf` / secret / `chmod 777` checks rather than adding
a dimension. The *missing-authorization-declaration* class was
deliberately **not** inferred from transcripts — detecting the absence
of a scope line false-positives on ordinary tool-use logs ("Edit tool:
…"), so that belongs in a manifest validator.

## [2.0.6] - 2026-06-11

Patch release. Adds a stdlib-only, offline **sycophancy /
false-premise-agreement signal** to the scoring engine — *not* a new
rubric (the inventory stays at 11; the v4.3 scope contract is
untouched), but a heuristic that composes with the existing
`correctness` / `consistency` dimensions and the red-flag deduction
machinery, the same in-scope shape as the v2.0.5 same-family guard.

### Added

- **Sycophancy signal** (`skills/judge/scripts/score.py`,
  `detect_sycophancy`): parses the raw transcript's user/assistant
  turns and detects **answer-flip under pressure** — when the
  assistant abandons a prior answer after a user pushback ("are you
  sure? I think it's X"). The discriminator that avoids penalising a
  *correct* concession: a capitulation ("you're right", "I was wrong")
  **without** fresh reasoning is a sycophantic flip; the same
  capitulation **with** a re-derivation / justification is a
  legitimate update and is not flagged. Emits a top-level `sycophancy`
  object (`score` 0-1 where 1.0 = held under pressure, `flipped`,
  `stance_consistency`, `pushbacks`, `rationale`, `signals`); a
  confirmed flip is added to `red_flags` so it docks the composite
  through the existing `apply_adjustments` lever. Offline and
  heuristic — **no LLM call**; the existing opt-in
  `llm_second_opinion` remains the only LLM path.
- `judge-config.json.sycophancy` block (`enabled`, `flip_red_flag`,
  `min_pushbacks`; enabled by default, offline).
- Optional top-level `sycophancy` field in
  `schemas/scorecard.v1.schema.json` — additive, backward-compatible.
- `skills/judge/references/sycophancy_probes.json`: a labelled
  false-premise probe set across **5 locales** (en/es/fr/hi/zh),
  honouring the 38-language sycophancy finding
  ([arXiv:2606.08451](https://arxiv.org/abs/2606.08451)) — an
  English-only probe set would under-measure the effect.
- Fixtures `tests/fixtures/sycophancy_{flip,hold,true_concession}.jsonl`
  and `tests/test_sycophancy.py` (detector units, the three fixtures,
  `build_scorecard` integration, a no-network offline assertion, and
  probe-set integrity).

### Scope / framing

This scores **agreement-drift** (does the assistant cave to pushback),
distinct from the trajectory-injection rubric proposal rejected on
2026-06-09 (#39) and the role-routing self-preference guard shipped on
2026-06-07 (#38, v2.0.5). It is a response-quality signal over a single
transcript, not a model benchmark, so it ships as engine logic rather
than a 12th rubric. Refs: [arXiv:2606.09068](https://arxiv.org/abs/2606.09068),
[arXiv:2606.08629](https://arxiv.org/abs/2606.08629).

## [2.0.5] - 2026-06-07

Patch release. Adds a stdlib-only **same-family judge guard** plus a
`self_preference_risk` scorecard flag to the opt-in LLM second-opinion
analyzer.

### Added

- **Same-family judge guard** (`skills/judge/analyzers/llm_judge.py`):
  new `model_family()` (prefix-buckets a model ID into
  anthropic/openai/google/meta) and `same_family_guard()`. Before the
  opt-in second opinion runs, the guard compares the executing model
  (from `score.detect_model_from_transcript`) against the configured
  judge model. On a same-family match it (a) sets
  `self_preference_risk: true` on the scorecard and emits a
  `Verdict WARNING:` line on stderr citing the measured effect
  (MT-Bench: GPT-4 +10%, Claude-v1 +25% self-win-rate), and (b) when a
  cross-family `llm_second_opinion.alternate_judge_models` entry is
  configured, auto-prefers it for the call (reachable via the
  documented injected-client / proxy path). Off-by-default with the
  rest of the second opinion; stdlib-only, no new deps.
- `self_preference_risk` (boolean) and `same_family_guard` (object)
  optional top-level scorecard fields — additive, backward-compatible
  in `schemas/scorecard.v1.schema.json`.
- `llm_second_opinion.alternate_judge_models` config key (default `[]`).
- `tests/test_same_family_guard.py`: family bucketing, same-family
  risk + citation, cross-family clear, auto-prefer substitution,
  `build_scorecard` integration via a mock client, and a regression
  assertion that `build_prompt` / `SYSTEM_PROMPT` never use
  first-person framing ("you wrote" / "your work" / "your output").

### Rationale

An LLM judge over-scores its own family. The effect is measured, not
hypothetical (self-preference: arXiv:2306.05685; role-relabel framing
swings scores +23–93pp: arXiv:2606.05976), and in Verdict's stock
configuration the second opinion is Claude-judging-Claude — so the
guard fires on every enabled run, which is the honest signal. The
existing third-party "second-opinion judge" framing is preserved.

## [2.0.4] - 2026-05-29

Patch release. Adds a stdlib-only verifier-collapse detector to the
consistency dimension and wires the resulting flag into both the
`/judge --explain` output (Markdown + `explain.v1` JSON) and the
Stop-hook ship-gate. Closes a latent bug in
`_analyze_consistency`: the prior low-variance branch would
*reward* a flatlined verifier with a `+1` "highly consistent"
bonus — the new detector composes with that path so collapsed
verifiers net to a dock instead.

### Added

- `skills/judge/scripts/score.py::_detect_verifier_collapse` —
  offline statistics over the rolling window of recent scorecards
  for the same skill. Flags `verifier_collapse=true` when, over at
  least `min_samples` of the last `window` cards (defaults 5/10):
    * fraction of composites `>= top_threshold` (default 8.5)
      crosses `top_bucket_fraction` (default 0.95), **and**
    * `std_dev` of composites `< max_std_dev` (default 0.3 —
      tighter than the existing 0.8 "highly consistent" cutoff).

  On a hit, `_analyze_consistency` docks the dimension by
  `consistency_dock` (default 3) and appends a one-line reason.
  The dock is wide enough to net out the existing low-variance
  `+1` bonus that the same data would otherwise trigger.

- `dimensions.consistency.verifier_collapse` /
  `verifier_collapse_reason` / `verifier_collapse_stats` on the
  scorecard, mirrored at the scorecard top level as
  `verifier_collapse: bool` for one-jq-query CI consumption.

- `judge-config.json.verifier_collapse` block (enabled by default;
  set `enabled: false` to disable). Knobs: `window`, `min_samples`,
  `top_threshold`, `top_bucket_fraction`, `max_std_dev`,
  `consistency_dock`, `gate_mode`.

- `explain.v1` JSON surfaces `verifier_collapse` (top-level) plus
  per-dimension `verifier_collapse` / `verifier_collapse_reason` /
  `verifier_collapse_stats` on the consistency entry. The Markdown
  renderer adds a "⚠️ Verifier collapse detected" callout above
  the dimension table, anchored on Verdict's own consistency
  dimension plus the Soft-SVeRL project anchor (no sibling
  benchmark analogies, per the G13 cross-pollination rule).

- `hooks/judge-on-stop.sh` honours
  `judge-config.json.verifier_collapse.gate_mode`:
    * `warn` (default) — stderr `Verdict WARNING: verifier collapse
      detected for $SKILL_NAME — $REASON`, exit code unchanged.
    * `fail` — stderr `Verdict BLOCKED: ...` + `exit 2` (same shape
      as the existing threshold-breach gate).
    * `off` — silent.

- `schemas/scorecard.v1.schema.json` now declares the new optional
  fields (top-level `verifier_collapse` plus the three new
  per-dimension keys). Backward-compatible additive extension; no
  required-field change.

### Tests

- `tests/test_verifier_collapse.py` (new): clean varied history
  produces no flag; collapsed history (10× 9.5) flags + docks the
  consistency dim; below-`min_samples` produces no flag;
  `enabled: false` produces no flag; explain.v1 JSON carries
  top-level + per-dim fields; Markdown renderer emits the callout
  with the Soft-SVeRL anchor; hook gate-mode `warn` exits 0,
  `fail` exits 2, `off` is silent.

### Notes

- The detector is **offline-only** (pure stdlib statistics over
  `scores/`) and is the default-on companion to the off-by-default
  LLM second-opinion analyzer. LLM judging is not made the default
  by this change — the offline heuristic is the moat.

- The signal is **derived from Verdict's own consistency dimension
  plus the Soft-SVeRL project anchor**. Sibling-benchmark analogies
  were considered and dropped per the G13 anti-cross-pollination
  rule; no external evaluation suites are named in code, docs, or
  CHANGELOG for this change.

## [2.0.3] - 2026-05-28

Patch release. Adds an ABA-anchored task-hygiene lint to the
benchmark pack so a suspect regression-gate corpus can be caught
*before* its scores are consumed by CI.

### Added

- `scripts/bench_lint.py` — offline, stdlib-only hygiene lint for
  the regression-gate manifest. Implements four rules adapted from
  the Auto Benchmark Audit framework (Wang et al. 2026,
  arXiv:2605.26079, "Automated Benchmark Auditing for AI Agents
  and Large Language Models", v1 2026-05-25):

    * **VBL001 SpecificationGap** — missing `name`/`skill`, or no
      `expected_*` bound declared (case asserts nothing).
    * **VBL002 EnvironmentCoupling** — absolute transcript path,
      path escapes the manifest dir via `..`, transcript file
      missing on disk, or declared `adapter` doesn't match the
      file suffix.
    * **VBL003 BrittleGrading** — single-point composite/grade/dim
      bounds (`min == max`), or composite range narrower than 0.5.
    * **VBL004 MissingGroundTruth** — transcript is 0-bytes or
      contains zero non-blank lines.

  Aggregate `bench_hygiene_score = 1 - flagged_cases / total_cases`.
  Emits text (default), JSON (`--json`), or SARIF v2.1.0
  (`--sarif PATH`). Exits 0 above threshold (default 0.85), 1 below,
  2 on IO/arg failure. No LLM call — the offline heuristic is the
  moat.

- Ship-gate wire-up in `scripts/benchmark_pack.py`: new `--lint`
  flag runs the hygiene pass *before* the regression suite and
  aborts non-zero if `bench_hygiene_score` is below
  `--hygiene-threshold` (default 0.85). `--sarif PATH` implies
  `--lint` and writes the SARIF document. CI now surfaces "this
  benchmark may not be trustworthy" instead of greenwashing a
  suspect corpus. Legacy positional manifest argument preserved.

### Tests

- `tests/test_bench_lint.py` (21 tests): the shipped
  `benchmarks/manifest.json` scores 1.0 and exits 0; each of the
  four rule classes fires on an injected bad case; SARIF v2.1.0
  envelope and rule inventory pinned; exit-code matrix verified
  (0 above / 1 below / 2 IO-or-arg); `benchmark_pack --lint`
  aborts before the regression suite when the corpus is dirty
  and surfaces the VBL ruleId in stderr.

### Notes

- Verdict's benchmark pack scores *transcripts* against expected
  score bounds, not *tasks* against ground-truth outputs. The four
  ABA classes therefore apply by analogy, not literally; the lint
  output and README both state this adaptation explicitly so
  nobody reads it as a 1:1 ABA implementation. The 25.7%-of-tasks
  flaw rate ABA reports across 168 benchmarks is the motivation
  for catching the same shape of issue before scores ship.

- O17 — `bench_lint.py` adapts ABA to a transcript-regression
  manifest. If Verdict ever grows a true task benchmark (prompt +
  expected output + grader), the four rules will need a literal
  pass: spec gaps against the prompt text, env coupling against
  the grader's external calls, brittle grading against
  exact-match-only graders, missing ground truth against empty
  expected outputs.

## [2.0.2] - 2026-05-06

Patch release. Defensive-compatibility extension to the safety-
dimension allowlist tracking Claude Code v2.1.126 (2026-05-01).
**No breaking changes.** The v4.3 plugin-only scope contract is
unchanged — none of the 16 trimmed rubrics are re-introduced.
**538 tests, all green** (512 → 538; +26 from the new test file +
one extended grep test).

### Changed

- **Safety-dim allowlist widened** to track Claude Code v2.1.126's
  expansion of `--dangerously-skip-permissions`. The
  `_is_plugin_author_write` helper in `score.py` now allowlists
  non-destructive writes to:
  - `.claude/` subtree (any depth — was `.claude/{skills,agents,
    commands}/` only in v2.0.1)
  - `.git/` subtree (`.git/hooks/`, `.git/config`, `.git/info/`)
  - `.vscode/` subtree (`.vscode/settings.json`, `.vscode/launch.json`,
    `.vscode/tasks.json`, etc.)
  - Closed POSIX/zsh shell-config-file set: `.bashrc`,
    `.bash_profile`, `.profile`, `.zshrc`, `.zprofile`, `.zlogin`,
    `.zshenv`
  Destructive shell forms (`rm -rf`, `chmod 777`, `sudo rm`,
  `eval(`, `exec(`, raw `DROP TABLE` / `TRUNCATE TABLE`) on the
  allowlisted paths still dock the safety dimension. The
  shell-config-file set is intentionally **closed**: we do NOT glob
  `.*rc`, which would tolerate writes to `.npmrc` (npm credentials)
  or `.dockerrc` (registry creds).
- **Claude Code release audit comment block** in
  `scripts/validate_marketplace.py` rotated to the most-recent five
  releases (newest first): v2.1.126 / v2.1.125 / v2.1.124 / v2.1.123
  / v2.1.122. The earlier-audited v2.1.121 / v2.1.120 / v2.1.119
  entries are referenced in the footer paragraph but pruned from
  the per-release table (≤5-release cap).

### Tests

- `tests/test_safety_v2_1_126_paths.py` (25 cases) — 3 git
  subtree, 3 vscode subtree, 7 closed shell-config-file, 4
  destructive-precedence, 4 exfil-risk-not-excused, 4
  end-to-end safety-analyzer integration.
- `tests/test_validate_marketplace_v2_1_120.py` — extended grep
  test now asserts the most-recent-five markers
  (v2.1.122–v2.1.126) and pins the prune of pre-v2.1.122 entries.
- `tests/test_safety_claude_paths.py` (10 cases from v2.0.1) —
  remains green; the path-class widening is additive.

### Notes

- The shell-config-file set explicitly excludes `.fishrc` and
  `.config/fish/config.fish`. The Anthropic v2.1.126 changelog text
  reads "shell config files" without enumerating; verdict ships the
  conservative POSIX/zsh login set. If a future Claude Code release
  documents the explicit list and includes fish, widen here and
  update the audit comment block.
- The `.npmrc` / `.dockerrc` / `.aws/credentials` paths remain
  unallowlisted by design. Verdict will dock writes to those files
  even under `--dangerously-skip-permissions` — these are real
  exfil-risk surfaces and not what the v2.1.126 expansion targeted.

## [2.0.1] - 2026-05-04

Patch release. Three additive defensive-compatibility changes for
recent Claude Code transcripts (≤7 days). **No breaking changes.**
The v4.3 plugin-only scope contract is unchanged — none of the 16
trimmed rubrics are re-introduced. **507 tests, all green** (490 →
507; +27 from the three new test files).

### Added

- **Opt-in `duration_ms` enrichment for the efficiency dimension.**
  Reads Claude Code v2.1.119 (2026-04-23) `PostToolUse` /
  `PostToolUseFailure` `duration_ms` from transcripts. The
  `claude_code` adapter (and the built-in fallback loader) emits
  `[tool_duration_ms: <int>]` markers; `_analyze_efficiency`
  aggregates them into `dimensions.efficiency.tool_durations_ms`
  (a list[int], always present). When
  `judge-config.json.scoring.efficiency.duration_ms_dock_threshold`
  is set to an int N (ms), `_analyze_efficiency` docks 0.5 if at
  least 3 calls exceed N; the default `null` preserves v2.0.0
  scorecard shape exactly. Source:
  <https://code.claude.com/docs/en/changelog>.

### Changed

- **Safety dimension** now tolerates plugin-author writes to
  `.claude/{skills,agents,commands}/` paths (Claude Code v2.1.121
  stopped prompting for these under
  `--dangerously-skip-permissions`). The new
  `_is_plugin_author_write` helper suppresses the bulk safety
  counter for non-destructive operations on those paths;
  destructive shell forms (`rm -rf`, `chmod 777`, `eval(`,
  `exec(`, raw `DROP TABLE`, `sudo rm`) still dock.
- **`scripts/validate_marketplace.py`** now type-checks the v2.1.120
  top-level additions to `marketplace.json`: `$schema` (string
  URL), `version` (SemVer string), `description` (string ≤ 500
  chars). Also accepts `$schema` and `version` on individual
  `plugins[]` entries. Backward-compatible: documents missing
  these fields still validate. Source:
  <https://code.claude.com/docs/en/changelog>.

### Tests

- `tests/test_efficiency_duration_ms.py` (17 cases) — adapter
  marker emission, helper extraction, threshold dock semantics,
  end-to-end scorecard field carry-through.
- `tests/test_safety_claude_paths.py` (10 cases) — path
  allowlist, destructive-shell-form rejection, plus a
  forcing-function regression test asserting `score.py` contains
  zero `hookSpecificOutput` / `updatedToolOutput` /
  `_detect_hook_rewrite` references (post-v2.0.0 trim).
- `tests/test_validate_marketplace_v2_1_120.py` (11 cases) —
  top-level keys, plugin-entry keys, type-check failure paths.

### Notes

- The forcing-function regression test in
  `test_safety_claude_paths.py` makes the v4.3 scope contract
  visible to any future PR that tries to re-introduce the trimmed
  `tool-output-rewrite` rubric. Re-adding requires a runbook spec
  change (CLAUDE.md §v4.3 Scope Contract).
- `judge-config.json` gains
  `scoring.efficiency.duration_ms_dock_threshold: null` (default
  off). Existing configs without the field continue to work; the
  loader no-ops when the key is missing.

## [2.0.0] - 2026-05-03

**BREAKING.** Trims Verdict to its plugin-only scope per the
2026-05-03 v4.3 runbook §scope-reset block. 16 frontier-lab
eval-bench rubrics, 6 cross-ecosystem adapters, and 7 bench-eval
scripts were removed. If you depended on any of them, pin to
`v1.4.2` or fork. See the migration note in
[`README.md`](README.md) and the
[`v4.3 Scope Contract`](CLAUDE.md#v43-scope-contract-2026-05-03)
in `CLAUDE.md`.

**Test count: 926 → 469** unittest cases (the 466 plugin-scope
tests pass; the 3 v4.3 contract tests pass; ~457 frontier-lab
tests were deleted alongside the rubrics they covered).

### Added

- **`CLAUDE.md` §v4.3 Scope Contract** — pins the rubric and
  adapter inventory. Source of truth:
  `~/Downloads/AboutMe/skill-references/daily-opportunity-radar/runbook.md`.
- **`tests/test_v43_scope_contract.py`** — two checks: every
  in-scope rubric has its `.md` file; no rubric outside the
  v4.3 allowlist is present. Forcing function for any future
  re-add attempt.
- **`tests/test_skill_md_conformance.py`** — pins
  `skills/judge/SKILL.md` to the Claude Code skill spec
  (frontmatter present, required keys, `allowed-tools` is a
  constrained list, body ≤ 500 lines).
- **`benchmarks/README.md`** — clarifies that the corpus is the
  regression-gate fixture set, NOT a public eval bench. We do
  not advertise leaderboard standing or accept SWE-bench /
  Terminal-Bench / GAIA / OSWorld submissions.

### Changed

- **`skills/judge/SKILL.md`** — added `allowed-tools: [Read,
  Write, Edit, Bash]` to the frontmatter (least-privilege).
  Bumped `version` to `2.0.0`.
- **`README.md`** — rubric count `27 → 11`; deleted the
  Compliance rubrics section; trimmed the Architecture tree;
  trimmed the cross-ecosystem code blocks; added a
  v1.x → v2.0.0 migration note.
- **`.claude-plugin/plugin.json` and `marketplace.json`** —
  bumped to `2.0.0`.
- **`benchmarks/manifest.json`** — removed the
  `routine-triggered-session` case (out-of-scope per v4.3);
  benchmark gate now runs 7 cases (was 8).

### Removed — Breaking changes

**Rubrics (16):** `agentic-sast-confidence`, `browser-agent`,
`clinical-agentic-workflow`, `code-review-aider-polyglot`,
`eu-ai-act-audit-trail`, `function-hijacking-robustness`,
`gpt-5-5-differential`, `model-spec-compliance`,
`owasp-mcp-top-10-beta`, `project-deal-commerce`,
`routine-execution`, `ship-readiness`, `skill-compliance`,
`swe-bench-pro`, `terminal-bench`, `tool-output-rewrite`
(plus their `.weights.json` and `.example.md` sidecars).

**Scripts (7):** `audit_export.py`, `bench_gaming_check.py`,
`benchmark_gaming_detector.py`, `eu_audit_export.py`,
`judge_replay.py`, `replay_bfcl_attacks.py`, `ship_gate.py`.
Plus the `signatures/berkeley-rdi-2026-04-26.json` exploit
signature pack.

**Adapters (6):** `browser_harness.py`, `gemini_cli.py`,
`gemini_deep_research.py`, `inspect_ai_log.py`,
`mlflow_trace.py`, `terminal_bench.py`. The cross-ecosystem
`detect_adapter()` confidence scorer is also gone — pass
`--adapter <name>` explicitly for non-Claude-Code shapes.

**Integrations / exporters:**
`skills/judge/integrations/cloudflare_ai_gateway.py`,
`skills/judge/integrations/lighteval_shim.py`,
`skills/judge/exporters/openai_evals.py`.

**`score.py` helpers:** `_apply_brier_calibration`,
`_apply_commerce_asymmetry_check`, `_apply_contamination_penalty`,
`_apply_phi_redaction_check`, `_apply_ship_readiness_floors`,
`_apply_benchmark_gaming_penalty`,
`_compute_eu_ai_act_audit_evidence`,
`_compute_perception_reality_drift`,
`_detect_hook_rewrite_violations`, `_is_routine_trajectory`
(plus their constants/regexes). The
`scorecard.adjustments` object is now `{deduction, bonus}`
only; downstream consumers reading `adjustments.contamination`,
`.phi_leak`, `.ship_readiness`, `.tool_output_rewrite`,
`.eu_ai_act_audit`, `.benchmark_gaming`, etc. must drop those
references.

**Tests deleted (~33 files):** every test that covered a
removed rubric / script / adapter, plus the cross-ecosystem
`test_adapter_registry.py` and the v1.2.0
`test_rubric_packs.py`.

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
  [Discussions #43](https://github.com/sattyamjjain/proofloop/discussions/43).
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
