# No pass without proof: heuristic-first, in-loop scoring of coding-agent runs

*Draft — Sattyam Jain. The tool described here is [Proofloop](https://github.com/sattyamjjain/proofloop), MIT-licensed.*

AI coding agents now write a large and growing share of the code that
ships. The thing we still can't answer cheaply is the obvious one: **did
the agent actually do a good job on *this* run?** Not "is this model good
on a benchmark" — that one a leaderboard answers. The local, in-the-moment
question: the agent just spent twelve tool calls touching nine files and
declared victory — should I trust it before I `git push`?

There is a whole category of eval tooling, and it's well funded. But
almost all of it points the other way. Braintrust, Langfuse, Arize, Galileo,
LangSmith, DeepEval — these are built for teams *building* an AI product,
to score the chatbot or agent **they** ship. The developer *using* a coding
agent, asking "was that last run any good," is a different user with a
different loop, and that loop is mostly empty. I went looking for "score my
Claude Code / Cursor session" and found… not much.

So I built a small thing to sit in that gap, and the interesting part
turned out not to be the scoring — it was everything I had to do to stop
the scoring from lying to me.

## Why not just ask GPT-4 to grade it?

The reflex is LLM-as-a-judge: take the transcript, hand it to a strong
model, ask for a score. It works, sometimes well — MT-Bench showed a
GPT-4 judge reaching ~80% agreement with human raters
([Zheng et al., 2023](https://arxiv.org/abs/2306.05685)), and rubric-style
prompting like G-Eval ([Liu et al., 2023](https://arxiv.org/abs/2303.16634))
is now standard practice.

But for an *in-the-loop, every-run* signal it has three problems:

1. **Cost and latency.** A judge call per agent run, in the editor, is a
   tax you pay on every save. It pushes the signal out of the loop.
2. **Reliability.** LLM judges carry documented, stubborn biases:
   self-preference (a model rates outputs that look like its own higher —
   [self-recognition correlates with the bias](https://arxiv.org/abs/2410.21819)),
   position bias, and verbosity bias. The judge's *choice of model* is
   often the single biggest variable in the result.
3. **The circularity.** There's something off about using one unverified
   model to certify another unverified model's unverified work. If neither
   ran the tests, you've stacked two guesses.

None of that means LLM judges are useless. It means they shouldn't be the
*floor*.

## The counterintuitive floor: heuristics

The emerging 2026 consensus on eval pipelines is roughly **deterministic
checks first, LLM judge second, human last** — and the deterministic layer
does more work than people expect. One widely-shared analysis of thousands
of labeled agent-failure traces found cheap pattern-based detectors
*outperforming* the best LLM judge on the **structural** failure classes —
loops, malformed tool calls, missing verification — at zero marginal cost,
while LLMs were needed for the semantic, blame-attribution questions. The
split is the point: use the regex for what the regex is great at (and it's
great at more than you'd think), and spend the expensive judgment only
where language understanding is actually required.

Deterministic checks have two more properties that matter for a tool you
run constantly: they're **reproducible** (pin the definition in version
control and the score doesn't drift when the model changes underneath you),
and they're **free**, so you can fire them on every single run without
thinking about a bill.

So Proofloop's default path is offline heuristics — no LLM call, no API
key, no network. It hooks the agent's `Stop` / `SubagentStop` lifecycle
events, reads the transcript, and scores seven weighted dimensions —
correctness, completeness, adherence, actionability, efficiency, safety,
consistency — into a single composite, persisted as a schema-validated
JSON scorecard. An LLM second opinion exists, but it's opt-in and
off by default. The heuristic is the floor; the model is the escalation.

A run looks like this, rendered in the terminal in milliseconds:

```text
╔════════════════════════════════════════════════════════════════════════════╗
║ PROOFLOOP SCORECARD -- feature-dev                                         ║
║ Grade: A- (Very Good)  |  Composite: 8.75/10.0                             ║
╠════════════════════════════════════════════════════════════════════════════╣
║ Correctness    ██████████  10.0/10 (w=0.25) → No errors; receipt present   ║
║ Completeness   █████████░   9.0/10 (w=0.20)                                ║
║ Adherence      ████████░░   8.0/10 (w=0.15) → no deviation signals         ║
║ Actionability  ████████░░   8.0/10 (w=0.15)                                ║
║ Efficiency     ████████░░   8.0/10 (w=0.10)                                ║
║ Safety         ██████████  10.0/10 (w=0.10)                                ║
║ Consistency    █████░░░░░   5.0/10 (w=0.05) → no prior history yet         ║
╚════════════════════════════════════════════════════════════════════════════╝
```

That correctness `10` is the whole thesis, and it leads straight into the
hard part.

## The hard part: your own scorer is the adversary

Here's the thing nobody tells you about a cheap heuristic scorer: **it is
trivially gameable, and the entity most likely to game it is the agent
you're scoring** — not maliciously, just because models optimize for
looking done. If the score is lexical, the agent learns the lexicon. A
scorer you don't actively defend is a scorer that quietly converges on
"everything is fine."

So most of the real work was adversarial — treating my own heuristics as
the threat model. Four examples, all of which were genuine bugs I shipped
fixes for:

**Correctness gave a free 10 for silence.** The original check docked for
error-words ("error", "failed", "exception") and hallucination markers, and
otherwise returned 10. Which means a transcript that simply *avoids those
words* — says nothing, runs nothing, claims nothing — scored a perfect
correctness. The fix is the tool's tagline: **no pass without proof.** A
perfect correctness score now requires an *execution receipt* somewhere in
the run — a test runner invocation, a pass count, an exit code. Without one,
the top mark is withheld. "I refactored it and it looks good" caps at 9;
"`pytest` … `33 passed`" earns the 10. The receipt is the proof.

**Adherence was structurally broken.** It awarded +1 whenever a rubric was
*loaded* — which is every run — so adherence sat at 9 regardless of whether
the agent followed a single instruction. Its own justification string
literally said "rubric available," not "rubric followed." The honest fix
was to admit what a heuristic can and can't see: it can detect **deviation**
(a negative signal — "instead of", "ignoring", "skipping") but it cannot
confirm **compliance** without understanding the task. So heuristic
adherence now only docks for deviation, and positive compliance is left to
the opt-in LLM tier, which actually reads the rubric against the
transcript. No unearned credit.

**Safety cried wolf on the word "token."** A clean code review that wrote
`token = refresh(token)` got docked and flagged "possible hardcoded
secret," because the credential pattern matched any `token =` / `token:`.
So did `token: str` (a type annotation) and `self.token = row.token` (a
reference). The fix narrows "hardcoded secret" to a credential assigned a
*literal* value — a quoted string or a bare token — and excludes calls,
attribute/module references, env lookups, and type names. Real secrets
(`api_key = "sk_live_…"`, unquoted config values) still flag; benign auth
code stops getting punished for its vocabulary.

**A scorer stuck at 9 looks "consistent."** The consistency dimension
rewards low variance across a skill's history — but a scorer that has
quietly collapsed to "always 9" *also* has low variance. That's not
consistency, it's a flatline. A verifier-collapse detector watches the
rolling window and, when nearly every recent score is jammed at the top
with near-zero spread, treats that as a signal the *grader* has stopped
discriminating, and docks rather than rewards it. Same spirit as the
**same-family guard**: when the opt-in LLM judge shares a vendor family
with the model that produced the transcript (Claude grading Claude),
self-preference inflation is likely, so it flags the risk and prefers a
cross-family judge.

The pattern across all four: a heuristic eval is only worth running if you
assume it will be gamed and design against that. The dimensions are the
easy part. The anti-gaming is the product.

## What heuristics honestly can't do

I want to be precise about the ceiling, because overclaiming here is the
fastest way to lose a reader who knows better. Offline heuristics **cannot**
judge whether code is semantically correct, whether a subtle instruction
was honored, or whether an architectural choice was wise. They are a floor,
not a verdict. The receipt check tells you a test *ran and passed* — not
whether the test was meaningful. A 10 on correctness means "no error
signals and the work was checked," not "this is right."

That's exactly *why* the LLM second opinion exists as a tier, with the
self-preference guard wrapped around it. The argument was never "heuristics
replace LLM judges." It's narrower and, I think, correct: **don't pay an
LLM for the 60% a regex catches for free and deterministically, and don't
let it be the only thing standing between an agent's claim and your trust.**

## Scoring the run, not just the diff

The last idea is the one I care about most. Most code-quality tooling
grades the **diff** — the final artifact. Scoring the **run** — the
trajectory, the tool calls, the verification (or lack of it), the moment
the agent declared success without proof — is a different and
under-served question, and it's the one that's actually answerable in the
dev loop, for free, on every execution. It also packages cleanly into a CI
gate: the same offline scorer ships as a GitHub Action that fails a pull
request when an agent's composite drops below your bar. Eval-driven
development, without an eval bill.

Proofloop is [open source](https://github.com/sattyamjjain/proofloop),
offline, and stdlib-only. It's a small tool with an opinionated core: a
cheap, deterministic, in-loop signal is worth building — but only if you're
willing to treat its gameability as the main engineering problem, not a
footnote. No pass without proof.

---

*If you work on agent evaluation and any of the above is wrong or
under-thought, I'd genuinely like to hear it — that's the most useful kind
of reply.*
