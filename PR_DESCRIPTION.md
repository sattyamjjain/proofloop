# PR draft — `v1.1.1 → v1.2.0-beta.1` landing

Copy-paste the body below when you open the PR. The title line is the
repository's expected convention; keep it if you can. This file is
intentionally committed so you can eyeball the draft locally before
publishing.

---

## PR title

```
v1.1.1 — scorecard schema + $schema field + issue cleanup (plus v1.2.0-beta.1 features)
```

## PR base / head

- base: `main`
- head: `feat/v1.2.0-schema-llm-opinion`

## PR body

Executes the 2026-04-19 Claude Code Prompt (Thread A). Every task
below has a commit + tests; the branch grows 262 → 314 passing tests.

### Thread A — tasks completed

- **A1 — `scorecard.v1.schema.json` + `$schema` field.** Canonical
  JSON Schema at `schemas/scorecard.v1.schema.json`. `save_score`
  injects `$schema` and `schemaVersion` at the top of every emitted
  document. DEEP_ANALYSIS.md §Schema stability contract documents the
  SemVer rules. New suites: `tests/test_schema.py`, `tests/_schema_validator.py`
  (stdlib-only validator so we don't take a `jsonschema` dep), and
  four committed scorecard fixtures under
  `tests/fixtures/scorecards/`.

- **A2 — issue hygiene.** [#2][i2] closed with a summary covering
  every completed v1.1.0 item; [#3][i3] opened for v1.2.0 tracking.
  [i2]: https://github.com/sattyamjjain/verdict/issues/2
  [i3]: https://github.com/sattyamjjain/verdict/issues/3

- **A3 — opt-in LLM second-opinion analyzer.**
  `skills/judge/analyzers/llm_judge.py` with stdlib-only
  `AnthropicClient`. Gated by
  `judge-config.json.llm_second_opinion.enabled` (default `false`).
  When on, emits `dimensions[dim].llm_score` /
  `dimensions[dim].llm_justification` alongside the heuristic entries.
  Transcripts trimmed to 16k chars (~4k tokens) with a head/tail
  preservation strategy. Sends `task-budgets-2026-03-13` beta header
  when `budget_tokens` is configured. `tests/test_llm_judge.py` injects
  a fake client — zero network calls in CI. Failures degrade
  gracefully (heuristics-only scorecard, stderr warning).

- **A4 — Gemini CLI adapter.** `skills/judge/adapters/gemini_cli.py`
  handles `parts[]`, flattened `content`, `functionCall`, and
  `functionResponse` shapes. Registered under `gemini-cli` and `gemini`
  in the adapter registry. Fixture:
  `tests/fixtures/gemini-cli.jsonl`. Tests in `test_adapters.py`
  and `test_adapter_fixtures.py`.

- **A5 — `/judge --watch` live re-scoring.**
  `skills/judge/scripts/watch.py` polls the scores directory every 2 s
  (configurable via `--interval`). On change, emits a single-line diff
  header (`improved X, regressed Y, unchanged Z` + composite delta
  with ↑/↓/→) and re-renders Verdict Studio. `--once` flag for tests.
  Slash-command docs updated in `commands/judge.md`.
  `tests/test_watch.py` covers diff math, run-pass behaviour, and the
  CLI once-path.

- **A6 — dogfood self-score CI gate.**
  `.github/workflows/self-score.yml` treats the PR title + body +
  changed-files list as a synthetic transcript and scores it against
  the code-review rubric. Fails the job when composite <
  `VERDICT_PR_THRESHOLD` (default 7.0). Posts the Unicode scorecard as
  a PR comment via `actions/github-script@v7`; updates in place on
  subsequent pushes.

### Version bumps

- `plugin.json` · `marketplace.json` · `SKILL.md` → `1.2.0-beta.1`
- `CHANGELOG.md` — full Added / Changed / Tests / Out-of-scope section

### Tests

| Suite                         | Before | After |
| ----------------------------- | :----: | :---: |
| Total unit tests              |  262   |  314  |
| Benchmark pack cases          |    8   |    8  |
| `test_schema.py`              |    —   |    7  |
| `test_llm_judge.py`           |    —   |   24  |
| `test_watch.py`               |    —   |   12  |
| Gemini coverage               |    —   |    9  |

All green locally. Shellcheck clean on `hooks/*.sh`. Marketplace
validator passes.

### Out of scope for this PR

- Rubric marketplace index (P2)
- Scorecard delta webhook (P2)
- `verdict` PyPI shim (P2)
- MLflow integration (future)

### Upgrade notes for consumers

- Scorecard JSON now carries `$schema` and `schemaVersion` at the top.
  Existing consumers that iterate top-level keys will see two new
  entries; add them to your allowlist or (better) pin to the schema.
- `llm_second_opinion` config block is present but disabled. Old
  configs without the block continue to work; `_llm_second_opinion_config`
  treats a missing block as disabled without warning.
- `adapters/` registry now has `gemini-cli` and `gemini` entries. If
  you vendored the registry, regenerate it.

### Prompt reference

Executes the 2026-04-19 prompt (Thread A only — Thread B was out of
scope by your decision).
