---
name: judge-explain
description: "Render a Verdict scorecard JSON as PR-friendly Markdown or stable-schema JSON"
---

# `/judge --explain` — Scorecard Rationale Exporter

Reads a scorecard JSON written by `score.py` and renders it in one of
two formats:

- **Markdown** (`--format md`, default) — paste straight into a pull-
  request review comment. Tables for the per-dimension breakdown,
  call-outs for adjustments, evidence stats at the bottom.
- **JSON** (`--format json`) — stable-schema digest tagged
  `format_version: "explain.v1"` so CI scripts can pin to the schema
  and detect future bumps.

## Why

Verdict scorecards already carry every signal needed to justify the
composite score. Adopters asked
([Discussions #43](https://github.com/sattyamjjain/verdict/discussions/43))
for a one-shot way to drop the rationale into PR conversations
without copy-pasting from the raw JSON. `/judge --explain` is that
shot.

## CLI

```bash
python3 skills/judge/scripts/explain.py \
    --scorecard skills/judge/scores/<skill>_<timestamp>.json \
    [--format md|json] \
    [--out PATH]
```

Writes to stdout when `--out` is omitted. Returns exit code 2 if the
scorecard is missing or malformed.

## Markdown output shape

```markdown
# Verdict Scorecard — `<skill>`

**Composite:** <score>/10 — **Grade:** <letter> (<label>)
**Rubric:** `<rubric>` · **Model:** `<model>` · **Timestamp:** `<ISO-8601>`

> <one_liner>

_<summary>_

## Per-dimension breakdown

| Dimension | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| correctness | 8/10 | 0.25 | 2.0 | … |
…

### LLM second opinion           ← only when LLM judge ran
- **correctness**: 9/10 — …

## Adjustments                   ← only when red flags / bonuses / contamination present
- **Red flags** (−<deduction>): …
- **Bonuses** (+<bonus>): …
- **Contamination penalty** (−<contamination>): …

## Critical issues               ← only when present
- …

## Recommendations
- …

## Evidence
- <N> transcript lines analysed
- <X> red-flag patterns matched
- <Y> bonus signals matched
```

## JSON output schema (`explain.v1`)

```json
{
  "format_version": "explain.v1",
  "skill": "code-review",
  "timestamp": "2026-04-25T10:00:00Z",
  "rubric": "code-review",
  "model": "claude-opus-4-7",
  "tokenizer_baseline": 1.35,
  "composite": 8.4,
  "raw_composite": 8.6,
  "grade": "B+",
  "grade_label": "Good",
  "summary": "...",
  "one_liner": "...",
  "dimensions": [
    {
      "name": "correctness",
      "score": 8,
      "weight": 0.25,
      "weighted": 2.0,
      "justification": "...",
      "llm_score": 9,            // optional
      "llm_justification": "..." // optional
    },
    …
  ],
  "adjustments": {
    "deduction": 0.0,
    "bonus": 0.0,
    "red_flags": [],
    "bonuses": [],
    "contamination": 1.5         // optional, only when nonzero
  },
  "critical_issues": [],
  "recommendations": [],
  "evidence": {
    "transcript_lines": 42,
    "red_flag_count": 0,
    "bonus_count": 1
  }
}
```

`format_version` is a SemVer-ish hint — major bumps mean breaking
schema changes; minor bumps mean additive fields only. v1 is the
introduction.

## Limitations (today)

- **No literal evidence spans.** The heuristic scorer doesn't
  currently persist the matched transcript lines per dimension; only
  the justification string + red-flag / bonus pattern names are
  recorded. The `evidence` block surfaces the counts so a reviewer
  can gauge signal volume. Storing the matched spans is queued for
  v1.4.0.
- **No cost telemetry.** Verdict doesn't track API usage today, so
  the explain output omits a cost field. When the LLM second-opinion
  path adds usage tracking, an `usage` block joins the schema as
  `explain.v1.1`.
