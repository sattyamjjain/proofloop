# Contributing to Verdict

Verdict welcomes contributions. The most impactful kinds, in order:

1. **Rubrics** for domains we don't cover (`security-scan-v2`,
   `kubernetes-review`, `sql-review`, `pentest`, …).
2. **Transcript adapters** for new ecosystems (Gemini CLI, Windsurf,
   Aider, Cody, whatever ships next).
3. **Benchmark cases** that catch a regression the current corpus
   misses.
4. **Bug fixes** and heuristic refinements — with tests.
5. **Docs** improvements, especially examples.

No pip installs, no third-party Python deps. Stdlib only. This is a
hard constraint — see the bottom of this file.

---

## Ground rules

- Conventional-commits style (`feat:`, `fix:`, `docs:`, `ci:`, `test:`,
  `chore:`, `refactor:`).
- One logical change per PR. Keep diffs reviewable.
- 237+ tests must stay green. Add tests for any new logic.
- Validators must stay green: `scripts/validate_marketplace.py` and
  `scripts/benchmark_pack.py`.
- Shellcheck must stay clean on `hooks/*.sh`.
- Branch naming: `feature/<short-desc>`, `fix/<short-desc>`,
  `chore/<short-desc>`.

## Local setup

No dependencies beyond stdlib:

```shell
git clone https://github.com/sattyamjjain/verdict
cd verdict
python3 -m unittest discover tests/ -v       # full suite
python3 scripts/validate_marketplace.py      # schema check
python3 scripts/benchmark_pack.py            # regression gate
shellcheck hooks/*.sh                        # hook lint
```

Python 3.9+ and `jq` / `bc` on `$PATH`.

## Contributing a rubric

Rubrics live in `skills/judge/rubrics/` and follow the template at
`skills/judge/rubrics/custom-template.md`. The five-level table (9–10
/ 7–8 / 5–6 / 3–4 / 1–2) must match the existing rubric shape exactly
— the parser at `skills/judge/scripts/score.py:_parse_rubric_criteria`
only recognises `### DimensionName` headings.

1. Copy `custom-template.md` to `<your-domain>.md`.
2. Fill every dimension's criteria table with domain-specific
   calibration points.
3. Optional: drop a sibling `<your-domain>.weights.json` to override
   global weights for this rubric (sum must equal 1.0).
4. Add a test fixture under `benchmarks/corpus/<your-domain>-sample.jsonl`.
5. Add a case to `benchmarks/manifest.json` so CI guards against
   regressions.
6. PR with title `feat(rubrics): add <your-domain> rubric`.

For the community-hosted flow (not shipping in this repo), publish
the rubric at a stable HTTPS URL and document it. Users install via
`python3 scripts/install_rubric.py <url>`.

## Contributing an adapter

Adapters live in `skills/judge/adapters/`. Each adapter is a module
exposing `extract_lines(path: str) -> List[str]`. Registered in
`skills/judge/adapters/__init__.py`.

1. Capture a real transcript from the target ecosystem. Anonymise it.
2. Save under `tests/fixtures/<ecosystem>-sample.<ext>`.
3. Create `skills/judge/adapters/<ecosystem>.py` following the
   `openai_compatible.py` pattern.
4. Register in `ADAPTERS` in `__init__.py`.
5. Add a test class to `tests/test_adapters.py`.
6. Add an adapter case to `benchmarks/manifest.json`.
7. Document in the Cross-ecosystem section of `README.md`.
8. PR with title `feat(adapters): add <ecosystem> adapter`.

## Contributing a bug fix

- Reproduce the bug in a failing test first.
- Land the fix and the test in the same commit.
- Reference the DEEP_ANALYSIS section if it calls out the root-cause
  category — keeps the audit trail tight.

## Contributing to heuristics

Every change to `score.py` must include:

- A unit test for the specific transition (before → after score).
- A benchmark-pack case that would regress without the change.
- A sentence in `CHANGELOG.md` under *Changed* or *Fixed*.

We deliberately do not chase every subjective scoring edge case. A
heuristic change is worth shipping only if it fixes a credibility bug
(false-positive that a human would dismiss, or false-negative that a
human would catch). See DEEP_ANALYSIS §12 for the class we've already
addressed.

## Pull-request checklist

Before opening the PR:

- [ ] Tests pass locally (`python3 -m unittest discover tests/`).
- [ ] Marketplace validator passes (`python3 scripts/validate_marketplace.py`).
- [ ] Benchmark pack passes (`python3 scripts/benchmark_pack.py`).
- [ ] Shellcheck clean if you touched `hooks/*.sh`.
- [ ] `CHANGELOG.md` updated under `## [Unreleased]` (create the
      section if it doesn't exist).
- [ ] README or `SKILL.md` updated if the change adds or modifies
      user-visible behaviour.
- [ ] No third-party Python imports introduced.

## Review

Single maintainer today (@sattyamjjain). Expect a first review within
**3 business days**. If it's been longer, comment on the PR — GitHub
notifications sometimes slip through.

## The stdlib-only rule

Verdict's install story is "zero ongoing cost, no supply-chain risk,
`pip install` is instant." Every third-party dep weakens that pitch.
If you think you need one, open an issue instead of a PR — we'll
discuss whether the feature can be reshaped to stay stdlib-only, or
move to an opt-in subpackage that users explicitly install (the
small-judge path is the current example).

## License

By contributing, you agree that your contributions will be licensed
under the MIT License (`LICENSE`).
