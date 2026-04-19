# Verdict — Deep Codebase Analysis

**Plugin:** Verdict — Universal Skill & Agent Quality Judge
**Version:** 1.0.0 (released 2026-02-13)
**Stack:** Python 3.9+ stdlib-only · bash (hooks) · markdown rubrics · `unittest`
**Platforms:** `claude-code`, `claude-cowork`
**Report date:** 2026-04-18

---

## 1. Executive summary

Verdict is a Claude Code / Cowork plugin that scores skill or subagent execution transcripts along seven weighted dimensions — correctness, completeness, adherence, actionability, efficiency, safety, consistency — then renders a scorecard, persists it as JSON, and optionally blocks the workflow (hook exit code 2) when the composite falls below a configurable threshold.

The codebase is **unusually disciplined for a plugin**: ~2,400 lines of Python across three scripts, 132 unit tests (all passing), 10 domain-specific rubrics plus a documented `custom-template.md`, and bash hooks with proper dependency checks. The scoring engine is deterministic, stdlib-only (no `pip` dependencies), and the output JSON schema is well-specified.

The product risk sits almost entirely in the **analyzer heuristics themselves**. Every dimension is measured by matching regexes against the raw transcript. That gives you speed and zero runtime cost, but it also means:

- Discussions of error handling get penalized for "correctness" (the word `Exception` appears).
- `# TODO: add docstring` on a complete feature docks points from "completeness".
- Legitimate use of `os.getenv('PASSWORD')` sometimes trips the "safety" credential detector.
- Short, correct answers to short questions are penalized by a length-as-proxy-for-completeness rule.

These are tuning problems, not structural ones — but they cap the tool's accuracy well below LLM-based judges. The natural next step is to make Verdict the *structure* (rubric resolution, persistence, hooks, rendering) and plug a model-based analyzer behind the heuristics.

---

## 2. Repository layout

```
Verdict/
├── .claude-plugin/
│   ├── plugin.json                Manifest (name=verdict, v1.0.0, 2 platforms)
│   └── marketplace.json           Marketplace listing
├── judge-config.json              Root config (auto-judge, weights, threshold)
├── README.md, CHANGELOG.md, CLAUDE.md, LICENSE (MIT)
├── commands/                      4 slash-command markdowns
│   ├── judge.md                   /judge — manual evaluation
│   ├── scorecard.md               /scorecard — score history & trends
│   ├── benchmark.md               /benchmark — vs. reference standards
│   └── judge-config.md            /judge-config — config management
├── agents/
│   └── judge-agent.md             Read-only evaluator subagent
├── hooks/
│   ├── hooks.json                 Stop + SubagentStop event registration (120 s timeout)
│   ├── common.sh                  Dependency check, skill detection, config querying
│   ├── judge-on-stop.sh           Stop event handler
│   └── judge-on-subagent-stop.sh  SubagentStop event handler
├── skills/judge/
│   ├── SKILL.md                   299-line skill definition
│   ├── scripts/
│   │   ├── score.py (987 lines)   Scoring engine — 7 analyzers
│   │   ├── report.py (365 lines)  Unicode scorecard renderer
│   │   ├── benchmark.py (511 lines) Benchmark comparator
│   │   └── detect-skill.sh        Wrapper around common.sh
│   ├── rubrics/                   11 markdown rubrics (10 domain + custom-template)
│   ├── scores/                    Persisted JSON scorecards (one per run)
│   └── references/
│       ├── benchmark-standards.md Domain "Perfect 10" examples
│       └── scoring-methodology.md Calibration guidance
└── tests/
    └── test_score.py              132 unit tests, all passing
```

---

## 3. Plugin manifest

`.claude-plugin/plugin.json`:
- `name: "verdict"`, `version: "1.0.0"`, `license: "MIT"`
- `platforms: ["claude-code", "claude-cowork"]` — dual-platform
- Components registered: 1 skill (`skills/judge/SKILL.md`), 1 agent (`agents/judge-agent.md`), 4 slash commands, hooks JSON, and the root `judge-config.json`.

`.claude-plugin/marketplace.json` lists the plugin under category `"quality-assurance"` with tags including `"LLM-as-judge"`.

---

## 4. The scoring engine (`skills/judge/scripts/score.py`)

### CLI

```
python3 score.py --skill SKILL \
                 --transcript PATH \
                 --rubric-dir skills/judge/rubrics \
                 --scores-dir skills/judge/scores \
                 [--config judge-config.json]
```

### The seven analyzers

Each analyzer returns `(score 0–10, justification string)` from regex pattern counts. The heuristics:

| Dim | Weight | Signal | Deduction table |
|---|---|---|---|
| **Correctness** | 0.25 | `ERROR_PATTERNS` (error, failed, exception, traceback, NoneType…) + `HALLUCINATION_PATTERNS`, normalized by total lines | >10 % → −4; >5 % → −3; >2 % → −2; >0 % → −1 |
| **Completeness** | 0.20 | `INCOMPLETENESS_PATTERNS` (TODO, FIXME, HACK, stub, placeholder, WIP…) + transcript length floor | Incomplete: >5 % → −4, >2 % → −3, >1 % → −2, >0 % → −1. Length: <10 lines → −2, <30 lines → −1. |
| **Adherence** | 0.15 | `deviation_pattern` (instead of, ignoring, skipping instruction, override, disregard…). Default 8; +1 bonus if rubric was loaded with criteria. | >5 → −3; >2 → −2; >0 → −1 |
| **Actionability** | 0.15 | Counts triple-backtick code fences + `file_action_pattern` (created file, Write/Edit/saved…) − `placeholder_pattern` (`<YOUR_`, `INSERT_HERE`, `CHANGEME`, `xxx`). Default 8. | ≥4 fences → +1; any file action → +1; >3 placeholders → −3; 1–3 placeholders → −1 |
| **Efficiency** | 0.10 | `TOOL_CALL_PATTERN` density, `REPEATED_TOOL_PATTERN` retries, transcript length penalty | Density >30 % → −2, >15 % → −1. Retries >5 → −3, >2 → −2, >0 → −1. Length >2000 → −2, >1000 → −1 |
| **Safety** | 0.10 | `SAFETY_PATTERNS` (`rm -rf`, `--force`, `--no-verify`, `DROP/TRUNCATE TABLE`, `chmod 777`, `password=`, `secret=`, `token=`, `eval(`, `exec(`) with a context-skip for `.env/getenv/os.environ/config` and discussion-context lines | `rm -rf /` → −3 (critical). Hardcoded credential outside env context → −2 (critical). `--no-verify` → −1. `chmod 777` → −1. Aggregates: >10 hits → −3, >5 → −2, >0 → −1. |
| **Consistency** | 0.05 | Variance of the previous composite scores in history | No history → 7.0 neutral. std_dev >2.5 → −3; >1.5 → −2; >0.8 → −1; ≤0.8 → +1 |

### Composite & grade

```
composite = Σ (dim_score × weight)        # weights sum to 1.0, not enforced
composite = clamp(composite + bonuses − red_flag_deductions, 0, 10)
grade     = first row in GRADE_TABLE where composite >= threshold
```

`GRADE_TABLE` (11 tiers): A+ ≥9.5, A ≥9.0, A− ≥8.5, B+ ≥8.0, B ≥7.5, B− ≥7.0, C+ ≥6.5, C ≥6.0, C− ≥5.5, D ≥4.0, F ≥0.

### Auto-deductions & bonuses

Red flags (−0.5 each, capped at −2.0): fabricated facts (`hallucinated|fabricated|made up`), self-contradiction (`contradict`), ignored explicit constraints, placeholder tokens, `rm -rf /<non-word>`.

Bonuses (+0.25 each, capped at +1.0): addresses edge cases, justifies trade-offs, produces structured output (headings / lists / tables).

### Output JSON schema

Saved to `skills/judge/scores/{skill}_{YYYYMMDD-HHMMSS}.json`:

```jsonc
{
  "skill": "code-review",
  "timestamp": "2026-04-18T…",
  "composite_score": 8.6,
  "raw_composite": 8.35,
  "grade": "A-",
  "grade_label": "Very Good",
  "dimensions": {
    "correctness":  {"score": 9, "weight": 0.25, "weighted": 2.25, "justification": "…"},
    "completeness": …, "adherence": …, "actionability": …,
    "efficiency":   …, "safety": …,    "consistency": …
  },
  "red_flags": [],
  "bonuses": ["addresses edge cases", "structured output"],
  "adjustments": {"deduction": 0.0, "bonus": 0.5},
  "summary": "…",
  "one_liner": "…",
  "critical_issues": [],
  "recommendations": [],
  "rubric_used": "code-review",
  "transcript_lines": 412
}
```

---

## 5. Reporter (`report.py`) & benchmark comparator (`benchmark.py`)

### Reporter
Renders a Unicode scorecard with box-drawing characters, per-dimension bar chart (10-wide `█` / `░`), weight, trend arrow (`↑ / ↓ / →`) based on the last 3 scores per dimension, plus a historical-average scorecard when n≥2. `--format json` available for programmatic consumption. `--last N` limits history window.

### Benchmark comparator
Parses `references/benchmark-standards.md` for per-dimension and composite benchmarks (falls back to `DEFAULT_BENCHMARKS` if missing). Computes deltas, buckets them (well above / above / slightly below / below), picks the top-3 strengths and weaknesses, and emits improvement suggestions from a hardcoded `IMPROVEMENT_MAP` (4 tips per dimension — generic and skill-agnostic).

---

## 6. Skill detection (`hooks/common.sh` + `detect-skill.sh`)

Four patterns tried in order, first match wins:

1. `skills/*/SKILL\.md` path references → captures the directory segment
2. `Skill tool invoked: <name>` marker
3. JSON field `"skill": "<name>"`
4. Leading slash-command invocation `/<name>` on first line

Caveats: Pattern 4 will incorrectly fire on `/judge` itself (i.e. Verdict can detect its own command as the "skill" being judged). Pattern 1 takes whatever appears last in the transcript if multiple skills are referenced. Skill names with dots (`skill.name`) aren't matched by the `[a-zA-Z0-9_-]+` class.

---

## 7. Rubrics (11 files)

Every rubric follows the same structure: Overview → Dimension Criteria (5-level tables, scores 9–10 / 7–8 / 5–6 / 3–4 / 1–2) → Red Flags → Domain-Specific Bonuses. Domains covered:

- `default.md` — universal fallback
- `code-review.md` — false positives, file coverage, fix actionability
- `frontend-design.md` — validation, responsiveness, accessibility, states
- `documentation.md` — example accuracy, API coverage, format adherence
- `testing.md` — branch coverage, edge cases, isolation, assertion precision
- `security.md` — OWASP alignment, CVSS scoring, disclosure, fix clarity
- `content-writing.md` — fact verification, tone, CTA clarity, word count
- `data-analysis.md` — statistical methods, segment coverage, visualization clarity
- `research.md` — source quality, comprehensiveness, methodology, citations
- `devops.md` — config validation, deployment safety, rollback, monitoring
- `custom-template.md` — documented template for new domains

**Rubric resolution chain** (`load_rubric` in score.py, lines 152–186):
1. Exact filename match `{rubric_dir}/{skill_name}.md`
2. Category prefix — progressively shorter prefix strips (`code-review-v2` → `code-review.md`)
3. Fallback to `default.md`

Rubric parsing uses `### DimensionName` headings; non-standard heading formats (e.g. `**Correctness**`) are silently skipped, which means criteria may not feed the adherence-bonus check.

---

## 8. Hooks

### Registration (`hooks/hooks.json`)
```jsonc
{
  "hooks": {
    "Stop":         [{"hooks": [{"type": "command", "command": "bash hooks/judge-on-stop.sh",         "timeout": 120}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "bash hooks/judge-on-subagent-stop.sh","timeout": 120}]}]
  }
}
```

### Shared shell utilities (`common.sh`)
- Dependency probe: `jq`, `bc`, `python3` — emit install hints on failure, exit 0 to not block the user.
- `detect_skill_from_transcript()` — four regexes above.
- `should_auto_judge(skill, config)` — checks `auto_judge.always` / `auto_judge.never` lists via `jq`.
- `get_threshold(config)` — reads `auto_judge.threshold` (default 5.0).

### `judge-on-stop.sh` / `judge-on-subagent-stop.sh`
1. Dep check (exit 0 if missing).
2. Read stdin JSON → extract transcript path.
3. Detect skill name.
4. `should_auto_judge` gate.
5. Invoke `python3 score.py ...`.
6. Read back composite, grade, one-liner.
7. **If composite < threshold: exit 2** (signals "block") — otherwise emit a success payload on stdout and exit 0.

Exit-code semantics match Verdict's claim ("exit 2 is blocking"), but effective blocking depends on whether the host (Claude Code / Cowork) honors exit 2 from Stop-event hooks, which varies by host version. Worth documenting in the README.

---

## 9. Slash commands & judge agent

- `/judge [skill-name] [--rubric NAME] [--verbose]` — manual evaluation flow; useful when auto-judging was suppressed by the `never` list.
- `/scorecard [skill-name] [--last N] [--all]` — history and trends.
- `/benchmark <skill-name>` — delta vs. `benchmark-standards.md`.
- `/judge-config [subcommand]` — `add-always SKILL`, `add-never SKILL`, `remove SKILL`, `threshold N`, `enable/disable`.

`agents/judge-agent.md` defines a read-only evaluator subagent (tools: Read, Glob, Grep, Bash-read-only) that scores independently and emits the same JSON schema as `score.py`. The skill file gives careful calibration guidance ("score 5 = mediocre, 7 = good, 9–10 = rare") to counter cluster-around-7 rater bias — a nice detail.

---

## 10. Configuration (`judge-config.json`)

```json
{
  "auto_judge": {
    "enabled": true,
    "always": ["code-review","security-scan","feature-dev","debugging","codebase-analyzer","webapp-testing"],
    "never":  ["format","commit","fix-imports","undo","fix-todos","remove-comments","docs","session-start","session-end"],
    "threshold": 5.0,
    "block_on_critical": true
  },
  "manual_judge": { "default_rubric": "default", "verbose": true, "save_scores": true },
  "scoring": { "dimensions": {
    "correctness": 0.25, "completeness": 0.20, "adherence": 0.15, "actionability": 0.15,
    "efficiency": 0.10, "safety": 0.10, "consistency": 0.05
  }}
}
```

⚠️ **Weight-sum invariant (= 1.0) is documented but not enforced in code.** A user who edits the config to weights summing to 1.05 will silently get inflated composites. A one-line `assert abs(sum(weights) - 1.0) < 1e-6` at config load time would catch this.

---

## 11. Test suite (`tests/test_score.py`, 1,220 lines)

**132 tests, all passing** (confirmed by the agent run). stdlib `unittest` only.

Coverage by category:
- Grade boundary tests (~22) — every A+/A/…/F threshold
- Rubric resolution — exact, prefix, fallback
- Dimension analyzer tests — error / completeness / adherence / actionability / efficiency / safety / consistency patterns
- Auto-deduction & bonus detection
- Composite computation
- Config loading
- History loading / consistency variance

**Gaps worth filling:**
- No tests for `report.py` rendering (scorecard alignment, trend detection logic)
- No tests for `benchmark.py` (delta bucketing, strength/weakness selection)
- No tests for hook shell scripts (bash logic is unit-untested — consider `bats`)
- No end-to-end tests that invoke a hook against a synthetic transcript

---

## 12. Top risks & improvement opportunities

1. **Heuristic false positives & negatives.** Every analyzer is regex-based on the raw transcript. That means the phrase "error" in a discussion about error handling, a `TODO:` inside a docstring, or the word "attempt" in normal prose can all shift a dimension by 1–4 points. The product's calibration is therefore coupled to how users talk, not how they perform. Fix: expose an optional LLM back-end (Claude 3.5 Haiku or similar) behind the same analyzer API — structure stays the same, signal quality goes up.
2. **Length-as-proxy-for-completeness.** <10 lines → −2 on completeness, <30 → −1. A 3-line correct answer to a 1-line question scores 8/10 on completeness. Fix: tie the length penalty to task scope (words in the prompt, number of tool-calls expected from the rubric) rather than transcript length absolute.
3. **Neutral-baseline consistency.** No-history → 7.0 is arbitrary and inflates the composite the first time any skill runs. Fix: default to `None` and exclude consistency from the weighted composite until n≥2, renormalizing the remaining weights.
4. **Credential context fragile.** `os.getenv('PASSWORD')` often correctly avoids the penalty, but the regex skip-list (`env|os.environ|getenv|config`) misses `settings.get('PASSWORD')` and similar. Fix: AST-parse Python blocks when possible; for other languages, require a literal on the right-hand side (`= '…'`) before docking points.
5. **Rubric weight override isn't supported.** `judge-config.json` holds one set of weights globally; a testing skill that should weight "completeness" higher (edge cases) or a security skill that should weight "safety" higher can't. Fix: allow per-rubric weight overrides in YAML frontmatter or a sibling `.weights.json`.
6. **Config weight-sum not enforced.** See §10.
7. **`/judge` skill-detection self-match.** Pattern 4 will score Verdict's own commands as the "skill" being judged. Fix: exclude a known allow-list of Verdict commands from that pattern.
8. **Rubric drift.** Rubrics are static markdown; no versioning, no expiry. Consider adding a `rubric_version` field so `score.py` can record which rubric version produced each score.

---

## 13. Bottom line

Verdict is a **tight, principled starting point** for plugin-based quality evaluation on Claude Code and Cowork. Its strengths — zero-dependency Python, a strong test suite, well-structured domain rubrics, dual-mode (auto + manual), and persistent JSON scorecards — are exactly right for a v1.0 release. The next release should treat the regex analyzers as a *fallback* behind an optional LLM judge and address the length-as-proxy and neutral-baseline biases. Once those are fixed, Verdict can credibly claim the "universal" in its tagline.

---

## 14. Schema stability contract *(added 2026-04-19 with v1.1.1)*

Every persisted scorecard JSON carries `"$schema"` and `"schemaVersion"`
fields at the top of the document. These are injected unconditionally by
`skills/judge/scripts/score.py::save_score`; no caller needs to supply
them. The canonical schema lives at
`schemas/scorecard.v1.schema.json` and is tested against every fixture
in `tests/fixtures/scorecards/` via `tests/test_schema.py`.

### Identifiers

- `$schema`: `https://verdict.dev/schemas/scorecard.v1.json` — stable
  URI that never changes for the v1 line of the schema. The domain will
  resolve to a static copy of the schema once `verdict.dev` is live; until
  then the URI is a logical identifier and the authoritative copy is the
  file in-repo.
- `schemaVersion`: SemVer string `"MAJOR.MINOR.PATCH"`.
  - **MAJOR** is pinned to `1` for this schema URI. A breaking change
    (removal of a field, change of a type, change of an enum value,
    change of a required-list) forces a new schema file at
    `schemas/scorecard.v2.schema.json` and a new URI.
  - **MINOR** bumps for additive-compatible changes: new optional
    properties, new enum values on an open enum, newly relaxed
    constraints. Consumers that pin to `schemaVersion >= 1.1.0` must
    keep parsing older documents.
  - **PATCH** bumps are purely editorial: reworded `description` text,
    doc typos, tightened `additionalProperties: true → true with a
    pattern`, and the like.

### Evolution rules

- New **required** top-level field → MAJOR bump (old consumers break).
- New **optional** top-level field → MINOR bump.
- New dimension in `dimensions` → MAJOR bump (existing consumers iterate
  the seven canonical keys and would miss it); this is avoided in
  practice by adding LLM-side data inside the existing dimension entry
  (`dimensions.correctness.llm_score` et al.).
- Enum extension (e.g. a new grade tier) → MINOR bump if old consumers
  can safely ignore the new value, MAJOR otherwise.
- Removing a field that was optional → MINOR bump and a deprecation
  note in `CHANGELOG.md`.
- Renaming a field → treated as remove+add, so MAJOR.

### Deprecation window

Fields marked for removal ship in a MINOR release with a
`"deprecated": true` note in their `description`, then are removed only
in the next MAJOR. Consumers should check `schemaVersion` and fall back
to the legacy field when parsing older documents.

### Consumer pinning

Downstream tools (including Verdict Studio, `benchmark_pack.py`, and
external dashboards) should parse `schemaVersion` first. The minimum
compatible pin is `>= 1.0.0, < 2.0.0`. Any tool that needs a v1.1+
field should guard on `schemaVersion` and degrade gracefully for
v1.0.x documents.

### Test surface

- `tests/test_schema.py::TestSchemaFileWellFormed` — schema itself
  parses and advertises the correct `$id`.
- `tests/test_schema.py::TestPersistedFixtures` — every file in
  `tests/fixtures/scorecards/` validates against the schema and carries
  the right `$schema`/`schemaVersion` values.
- `tests/test_schema.py::TestPersistInjection` — `save_score` injects
  both fields on every write, idempotently, even when the caller's dict
  already carries them (canonical values win).

### Rationale

Before v1.1.1 the scorecard JSON was a moving target: any downstream
consumer that parsed last week's scorecard broke when we added fields
(`model`, `tokenizer_baseline`, `weights_source`). The schema contract
converts that implicit API into an explicit one and gives future
consumers a version they can pin against.
