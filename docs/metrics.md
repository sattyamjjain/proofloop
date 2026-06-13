# Proofloop metrics

Updated weekly. Tracks the launch-to-1000-stars goal and surfaces
regressions in the quality / distribution funnel. See ROADMAP_2026 §10
for the 90-day target table.

## How to update

Replace the *Current* column below each Monday. Keep historical weeks
in the trailing `## Weekly history` section so trends stay visible
without bloating the header.

```shell
# Numbers that can be read mechanically
gh api repos/sattyamjjain/proofloop --jq '.stargazers_count'
gh api repos/sattyamjjain/proofloop/traffic/views
git log --since='1 week ago' --oneline | wc -l
python3 -m unittest discover tests/ 2>&1 | grep -E 'Ran [0-9]+'
python3 scripts/benchmark_pack.py 2>&1 | tail -5
```

The counts that require outside-the-repo inputs (marketplace installs,
Discord members, rubric-marketplace entries) are collected manually —
leave a `—` when data is not yet available.

## Launch funnel

| Metric                                  | Target @ 30d | Target @ 90d | Current | Notes |
| --------------------------------------- | :----------: | :----------: | :-----: | :---: |
| GitHub stars                            |         400  |        3 000 |    —    |       |
| Plugin installs (all 4 marketplaces)    |       2 000  |       25 000 |    —    |       |
| Rubrics in marketplace (own + community)|          25  |           75 |  11     | ships with 11; target = community contributions |
| Supported ecosystems                    |           3  |            6 |   5     | claude-code, cowork, codex, cursor, continue (Gemini CLI + Windsurf outstanding) |
| Monthly "State of Skills" reports       |           1  |            3 |   0     |       |
| Teams with weekly digests on            |           5  |           50 |   0     |       |
| Discord members                         |         100  |          750 |   —     |       |

## Engineering health

| Metric                                  |  Current | Target |
| --------------------------------------- | :------: | :----: |
| Test count                              |    237   |  ≥ 237 |
| Benchmark-pack cases passing            |    4/4   |   4/4  |
| Marketplace-validator warnings          |      0   |     0  |
| Shellcheck issues on hooks/             |      0   |     0  |
| Open critical-safety regressions        |      0   |     0  |
| Median composite across all scores      |    —     |  ≥ 8.0 |

## Weekly history

### Week 0 — 2026-04-18 (launch prep)

- v1.1.0 PR #1 open. 237 passing tests.
- Stars: starting baseline — 3.
- Benchmark pack: 4/4 cases green.
- CI workflow held back pending `workflow`-scoped OAuth refresh.
- No installs yet — `/plugin marketplace add` pointer is live but not
  featured on any of the 4 upstream marketplaces.

_(Append future weeks above this line in reverse-chronological order.)_
