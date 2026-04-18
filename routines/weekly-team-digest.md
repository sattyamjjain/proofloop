---
name: Verdict weekly team digest
schedule: weekly
description: Post a weekly quality digest to Slack summarising Verdict scorecards.
---

# Weekly Verdict team digest

This routine is configured via Anthropic Routines
(<https://code.claude.com/docs/en/routines>, research preview) and runs
as a normal Claude Code cloud session. The routine prompt below is the
user turn; Verdict's `Stop` hook fires normally when the session ends.

## Setup

1. Open <https://claude.ai/code/routines> (or run `/schedule weekly
   Verdict team digest` from any Claude Code session).
2. Attach the repository or repositories whose `skills/judge/scores/`
   directory you want summarised.
3. Select the Slack connector so the routine can post the digest.
4. Paste the prompt below verbatim, then pick **Weekly** as the
   trigger cadence (Monday 09:00 local is a good default).

## Routine prompt

```
You are the Verdict weekly digest bot.

1. List every JSON file in skills/judge/scores/ whose timestamp falls
   in the last 7 calendar days. For each file, load the JSON and note
   the skill, composite_score, grade, and any critical_issues entries.

2. Group by skill. For each skill:
   - compute the average composite this week vs. the average of the
     prior 7 days (fall back to "no baseline" when there are no prior
     entries)
   - highlight the single best and single worst scorecard
   - summarise any safety or correctness critical issues verbatim

3. Run python3 scripts/benchmark_pack.py and include its pass/fail
   output at the top.

4. Post a message to the #engineering-quality Slack channel with the
   summary. Keep it under 30 lines. Use Slack mrkdwn syntax for
   headings and bullets.

5. If any skill regressed more than 0.5 composite points week-over-
   week, open a GitHub issue titled "Quality regression: {skill}
   dropped {delta}" in this repository and tag @sattyamjjain.

Stop the session once the digest is posted. No code changes.
```

## Operational notes

- Routines run on Anthropic-managed cloud infrastructure. Every run
  starts from the repository's default branch.
- Because the routine uses the Slack connector and posts comments, its
  actions appear under your personal Slack + GitHub identities — scope
  channel membership and repo permissions accordingly.
- Pro users get 5 routine runs/day, Max 15, Team/Enterprise 25 — the
  weekly schedule is well within all plans.
- Verdict's `Stop` hook fires in the routine's session just as it would
  in an interactive one, and the scorecard JSON is committed on branches
  prefixed with `claude/` by default (toggle **Allow unrestricted branch
  pushes** if you prefer direct pushes to `main`).
