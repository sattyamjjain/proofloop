# Conference / podcast pitch drafts

## Latent Space (swyx / Alessio)

**Subject:** Verdict — offline heuristic scoring for Claude Code skills (Stop-hook native)

Hey swyx / Alessio,

Just shipped Verdict, a Claude Code plugin that scores every skill /
subagent execution on seven dimensions from the Stop hook, offline,
no LLM call. The moat isn't features — it's distribution: every other
tool in this space asks you to wire traces into a SaaS. Verdict runs
inside the editor.

Would love to do a Latent Space episode on the offline-heuristics
design decision, why stdlib-only matters for plugin distribution, and
where Verdict fits relative to Braintrust / Langfuse / Ragas / Opik.

Happy to bring data from the first 14 days of launch — install counts,
grade distributions by rubric, drift-detection anecdotes.

Discord intro if it's easier: {user handle}.

— sattyam

## Changelog

**Subject:** Claude Code plugin that auto-grades every skill execution — would love a feature

Hi Adam —

Verdict shipped v1.1.0 last week. It's a Claude Code plugin that
auto-scores skill and subagent executions on seven dimensions using
offline heuristics (no LLM call, no API key, no hosted service). Cross-
ecosystem from day one: Codex, Cursor, Continue, Gemini CLI, Cowork
all supported via one adapter flag.

Think "perf budget for LLM skills" — each Stop event emits a JSON
scorecard, `/scorecard` renders trends, and CI gates on regressions
against a curated transcript corpus.

Would love a 15-minute segment. Can ship you a pre-recorded demo if
that shortens the pipeline.

## ThePrimeagen weekly roundup

Short pitch (2 sentences max):

> Claude Code plugin, 7-dimension scoring, no LLM call, one-shot
> install. If you run skills you've been flying blind — this tells you
> if they're actually getting better.

link to demo GIF. Keep it terse — his roundup clips are 10–15 seconds.
