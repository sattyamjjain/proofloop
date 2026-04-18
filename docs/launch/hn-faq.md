# HN Launch FAQ

**Submission title (under 80 chars):**
*Verdict: auto-grade every Claude Code skill execution on seven dimensions, no LLM*

**Link:** demo GIF (not the repo). The repo + docs live in the first comment.

Target: Tuesday 13:00 UTC. Stay in the thread for at least four hours
after posting. Below are drafted responses to the objections and
questions we expect.

---

### "Why seven dimensions specifically? What happens when someone disagrees with the split?"

The seven are: correctness, completeness, adherence, actionability,
efficiency, safety, consistency. They were chosen because every
meaningful evaluation framework I surveyed (Galileo Luna, Anthropic's
internal benchmarks, Ragas, Promptfoo) collapses to some subset of those.
The split isn't sacred — `judge-config.json` lets you rewrite the weights
globally and `<rubric>.weights.json` lets you override per rubric.

### "Isn't this just LLM-as-judge rebranded?"

Almost the opposite. Every competitor calls an LLM to grade the output
— which costs money, adds latency, and has the meta-problem of "who
grades the grader." Verdict runs offline regex heuristics against the
transcript. It's inferior to LLM-as-judge on nuanced judgment calls,
and we say so in the README, but the trade-off is: zero ongoing cost,
no API key, no network call, integrates as a Claude Code plugin with a
`Stop` hook. The opt-in small-judge model path (Haiku 4.5 / Atla Selene)
is there when you want the precision — but it's off by default.

### "Heuristics don't work. You're grading on length."

That was the v1.0 bug and it's in DEEP_ANALYSIS.md if you want the full
list. v1.1.0 (the release this thread is about) fixes four of the worst:

- Weight-sum invariant enforced at config load.
- Consistency no-history default dropped from 7 to 5 (was inflating every
  first run).
- TODO/FIXME inside docstrings no longer counts against completeness.
- Safety deductions skip discussion context — `rm -rf /` in a review
  comment no longer tanks the score.

Opus 4.7's new tokenizer (~35% more tokens) also shifts the length
thresholds, so efficiency is now model-aware. All of it is driven by a
benchmark corpus with CI regression gates, so a future change that
reintroduces length-as-proxy-for-completeness breaks the build.

### "How is this different from Braintrust / Langfuse / Phoenix / Helicone / Promptfoo / DeepEval / Ragas / LangSmith / Opik?"

Those are hosted observability platforms for LLM apps. You send traces
over HTTPS, they render dashboards, you write eval functions in Python
or TypeScript. Verdict is a Claude Code plugin — you install it from
the marketplace, and every `Stop` event in your editor is scored and
dropped into a local scorecard. No server, no traces, no API key.

The moat isn't features; it's distribution. Verdict is the only tool in
the category that ships inside the editor.

### "Does it support Cursor / Codex / Gemini CLI?"

Yes — via the `--adapter` flag on `score.py`. The v1.1 release ships
adapters for `codex`, `cursor`, `continue`, `cowork`, plus a generic
`openai-compatible` one. Each adapter is a 30-line file under
`skills/judge/adapters/`. If your transcript format isn't covered,
contribute one.

### "Show me a failure mode."

A transcript of "I found no issues with this code" on a clearly buggy
file scores 9.2/A with v1.0 because there are no error keywords, no
TODOs, and the transcript is short. The heuristic can't know the file
is buggy. The roadmap fixes this with the opt-in small-judge pass;
until then, Verdict is a signal, not a verdict.

### "Why is the code so conservative — stdlib only, no LLM, etc?"

Three reasons:
1. **Install experience** — `pip install` should be instant and
   zero-supply-chain-risk. If you need to install PyTorch for a
   scoring plugin, the plugin has the wrong shape.
2. **Deterministic.** The same transcript always scores the same. Good
   for CI regression gates (we ship one) and bad for nuance.
3. **Cheap.** Some teams burn a lot of LLM tokens on eval pipelines.
   Verdict is a complement that costs $0 to run forever.

### "Roadmap?"

Issue #2 on the repo has the full 90-day plan — cross-ecosystem launch
week (Week 2: Codex, then Cursor, Continue, Gemini CLI, Windsurf), the
Verdict Studio local HTML dashboard (already shipped as
`scripts/studio.py` actually), an opt-in small-judge model path via
Haiku 4.5, and a rubric marketplace seeded with the 11 rubrics we ship.
