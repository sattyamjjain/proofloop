# X thread — v1.1.0 launch

Eight tweets. First is a looping GIF of the Stop hook firing. Keep each
tweet self-contained — people quote individual tweets.

## 1/ (hero — GIF attachment)

every time i ship a claude code skill i wonder: did it actually get
better, or am i hallucinating improvement?

so i built Proofloop — a plugin that auto-grades every skill and subagent
execution on seven dimensions the moment the Stop hook fires.

no LLM call. no config. just a scorecard.

## 2/

the seven dimensions: correctness, completeness, adherence,
actionability, efficiency, safety, consistency.

each scored 1–10 with a weighted composite, persisted to JSON, and
charted over time. the weights are yours — global via `judge-config.json`,
per-rubric via sidecar files.

## 3/

why no LLM call?

because every other tool in this space (Braintrust, Langfuse, Phoenix,
Promptfoo, DeepEval, Ragas, LangSmith, Opik) needs a second LLM to
grade the first one. that costs money. adds latency. and has a
meta-problem: who grades the grader?

Proofloop runs offline regex heuristics.

## 4/

cross-ecosystem from day one.

v1.1 ships adapters for Codex, Cursor, Continue, Gemini CLI, Cowork,
and a generic openai-compatible path. a single plugin that scores
across ecosystems is unique.

one flag: `--adapter codex`.

## 5/

the plugin installs like any Claude Code plugin:

`/plugin marketplace add sattyamjjain/proofloop`
`/plugin install verdict@verdict`

next Stop hook that fires on an allowlisted skill triggers a score in
under 20ms. scores land in `skills/judge/scores/` as JSON.

## 6/

the launch release (v1.1.0) fixes every major heuristic credibility
bug from v1.0: weight-sum invariant, consistency neutral baseline,
docstring-scoped TODOs, safety discussion-context suppression, and
Opus 4.7 tokenizer awareness.

189 passing tests. CI regression gate against a curated corpus.

## 7/

what's next:

— `/judge --against HEAD~1` (shipped)
— Proofloop Studio local HTML dashboard (shipped)
— opt-in small-judge via Haiku 4.5 for the nuanced cases
— rubric marketplace seeded with 11 domain rubrics
— weekly team digest via Anthropic Routines

issue #2 has the 90-day plan.

## 8/ (CTA)

install:
`/plugin marketplace add sattyamjjain/proofloop`

source + docs: github.com/sattyamjjain/proofloop
discord: (invite in the README once created)

if you've been wondering whether your skills are actually getting
better, stop guessing. let Proofloop tell you.
