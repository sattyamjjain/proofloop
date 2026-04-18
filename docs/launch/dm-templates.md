# Creator DM templates

Ten creators, each DM personalised with a demo run against one of their
recent public transcripts. The pattern is the same: open with a
concrete observation from their work, attach a specific Verdict output,
end with a single ask (try it / boost it / give feedback).

## Template

> Hey {name} —
>
> loved your recent {specific thing they shipped}. I ran Verdict
> against {public transcript or PR}, and the scorecard flagged
> {specific dimension} at {score}/10 with the note {justification}.
>
> {one-sentence context on why that matters for them}
>
> I'd love a 90-second reaction if you have time. No ask beyond that.
>
> install: /plugin marketplace add sattyamjjain/verdict
> source: github.com/sattyamjjain/verdict
>
> — sattyam

## Targets (in order of leverage)

1. **swyx (@swyx)** — Latent Space / dev tooling authority. He has
   explicit Claude Code and skills content; Verdict is exactly his beat.
2. **Theo (@theo)** — T3 Stack / dev-tool takes. Audience overlap with
   Claude Code is high.
3. **simonw (@simonw)** — Django lineage, ships CLI tools, writes
   about eval pipelines. Verdict's CLI surface is aligned to his taste.
4. **karpathy (@karpathy)** — reach > any nominal fit. Only DM if the
   demo scorecard is airtight (run on one of his public repos first).
5. **matthewberman** — YouTube Claude / AI content; 300k subs.
6. **hwchase17** — LangChain author. Verdict competes with LangSmith;
   position this carefully as "different category, not a competitor."
7. **ggerganov** — llama.cpp author. Offline-first heuristics will
   resonate; expect tough questions on the heuristic accuracy floor.
8. **fchollet** — Keras author. Reputation for clean design; the
   stdlib-only pitch lands.
9. **{SMALLER}_1** — top Claude Code creator on YouTube with <50k subs;
   pick one who has posted a Stop-hook tutorial.
10. **{SMALLER}_2** — top Claude Cowork advocate in the /r/ClaudeAI
    community; pick someone whose Cowork content gets traction.

## Operational notes

- DM on X first; fall back to email found on GitHub profile.
- No more than two DMs per creator per week. If the first doesn't land,
  wait seven days before following up.
- Log each send in a private sheet with date + response. Do not
  automate the send — these are personalised by design.
- Never attach a raw scorecard JSON. Always attach a single cropped
  screenshot of the Unicode scorecard rendered by `/scorecard`.
