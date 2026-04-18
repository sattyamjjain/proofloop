# /r/ClaudeAI launch post

**Title:** *I built a Claude Code plugin that auto-grades every skill and subagent execution on seven dimensions, no LLM required*

**Body:**

A few months ago I started noticing my skills getting worse — or at
least, I thought they were. I'd iterate on a rubric, ship it, use it for
two weeks, and then wonder whether the changes I made actually moved the
needle. I had no way to tell.

Every tool I looked at (Braintrust, Langfuse, Phoenix, Promptfoo, etc.)
was either a hosted observability platform I'd have to wire traces
into, or a Python eval library I'd have to script. None of them plugged
into Claude Code, and all of them needed a second LLM to do the grading.

So I built Verdict.

It's a Claude Code plugin. You install it from the marketplace, and
from that point on every `Stop` hook (skill finishes) and
`SubagentStop` hook (subagent finishes) fires a scoring pass. The pass
grades the transcript on seven dimensions — correctness, completeness,
adherence, actionability, efficiency, safety, consistency — using
offline regex heuristics. No LLM call. No API key. Runs in under 20ms.
Persists the scorecard to JSON so `/scorecard` can render trends.

Install:

```
/plugin marketplace add sattyamjjain/verdict
/plugin install verdict@verdict
```

Key features:

- 7-dimension weighted scoring with configurable weights (global + per
  rubric) — security rubric ships with a safety-weight override of 0.35
- 11 domain rubrics: code-review, security, devops, data-analysis,
  frontend-design, testing, documentation, content-writing, research,
  and a template for custom
- Cross-ecosystem: Codex, Cursor, Continue, Gemini CLI, Cowork —
  `--adapter codex` handles OpenAI-compatible transcripts
- Opus 4.7 tokenizer-aware efficiency (auto-scales length thresholds
  by model)
- StopFailure hook skips scoring on API-error turns instead of
  penalising them
- `/judge --against HEAD~1` for diff-aware comparison between runs
- Local HTML dashboard via `scripts/studio.py` — no server
- Benchmark pack + CI regression gate so heuristic changes can't
  silently break your scores

Screenshots / demo GIF: [attach]

Happy to answer anything. If you've been running Claude Code skills
long enough to wonder if they're actually improving, try it and tell
me where it falls over. Issue tracker is open.
