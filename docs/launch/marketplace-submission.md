# `anthropics/claude-plugins-official` submission packet

Submission is via an auth-gated web form, not a PR (confirmed from
<https://code.claude.com/docs/en/plugins#submit-your-plugin-to-the-official-marketplace>
— the external `external_plugins/` directory is partner-only; the
URL-sourced entries in `marketplace.json` go through the same form).

**Form URLs** (pick whichever you're logged into):

- <https://claude.ai/settings/plugins/submit>
- <https://platform.claude.com/plugins/submit>

Copy the values below into the form. Everything already matches the
canonical shape of entries in `anthropics/claude-plugins-official`'s
`.claude-plugin/marketplace.json` (144 plugins at submission time;
sampled form: `adlc`, `asana`, `zoom-plugin`).

---

## Field-by-field

| Form field        | Value                                                                                                                  |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Name**          | `proofloop`                                                                                                              |
| **Description**   | *See below — two variants depending on character limit.*                                                               |
| **Category**      | `development` (matches the category of 144 existing entries; fallback: `quality-assurance` if a dropdown offers it)    |
| **Source type**   | `url` (a.k.a. "Git URL" — same pattern used by all URL-sourced community entries)                                      |
| **Source URL**    | `https://github.com/sattyamjjain/proofloop.git`                                                                          |
| **Homepage**      | `https://github.com/sattyamjjain/proofloop`                                                                               |
| **Author**        | `Sattyam Jain`                                                                                                         |
| **Author email**  | `sattyamjain96@gmail.com`                                                                                              |
| **License**       | `MIT`                                                                                                                  |
| **Version**       | `1.1.0`                                                                                                                |
| **Keywords/tags** | `judge, evaluation, quality, scoring, skills, agents, rubrics`                                                         |
| **Repository**    | `https://github.com/sattyamjjain/proofloop`                                                                              |

### Description — short (< 100 chars)

> Auto-grade Claude Code and Cowork skill executions on seven dimensions. No LLM call, no config.

### Description — standard (under ~240 chars)

> Auto-grade every Claude Code and Cowork skill execution on seven dimensions (correctness, completeness, adherence, actionability, efficiency, safety, consistency). Hooks-based auto-scoring + persistent scorecards. Offline heuristics — no LLM call required.

### Description — long / features list (for any field that allows markdown)

```markdown
Proofloop auto-evaluates skill and sub-agent execution quality from
Claude Code's `Stop`, `SubagentStop`, and `StopFailure` hooks.

Key differentiators vs Braintrust / Langfuse / Phoenix / Promptfoo /
DeepEval / Ragas / LangSmith / Opik:

- **Offline heuristics — no LLM call.** Zero ongoing cost, no API key.
- **Ships as a plugin, not a SaaS.** Install once, scored forever.
- **7-dimension weighted scoring** with configurable global + per-rubric weights.
- **Cross-ecosystem adapters** for Claude Code, Cowork, Codex, Cursor, Continue.
- **Opus 4.7 tokenizer-aware** efficiency analyser.
- **CI regression gate** — `scripts/benchmark_pack.py` runs a curated corpus on every PR.
- **Stdlib-only Python.** No pip deps, no supply-chain risk, instant install.

v1.1.0 — 237 passing tests. Full changelog in CHANGELOG.md.
```

---

## Canonical `marketplace.json` entry

If the form asks for the exact JSON block (some submission flows do),
paste this — it matches the shape of existing entries verbatim:

```json
{
  "name": "proofloop",
  "description": "Auto-grade every Claude Code and Cowork skill execution on seven dimensions (correctness, completeness, adherence, actionability, efficiency, safety, consistency). Hooks-based auto-scoring + persistent scorecards. Offline heuristics — no LLM call required.",
  "category": "development",
  "source": {
    "source": "url",
    "url": "https://github.com/sattyamjjain/proofloop.git"
  },
  "homepage": "https://github.com/sattyamjjain/proofloop"
}
```

---

## Pre-submission checklist

Before you click submit, verify each of these is still true — the
review team catches every one of them:

- [x] `plugin.json` has `name`, `version`, `description`, `author`, `license` — confirmed in `.claude-plugin/plugin.json`
- [x] `README.md` lives at repo root with an install snippet — ✓
- [x] `LICENSE` file at repo root (MIT) — ✓
- [x] `CHANGELOG.md` includes a v1.1.0 entry — ✓
- [x] `.claude-plugin/marketplace.json` passes `scripts/validate_marketplace.py` — ✓
- [x] CI workflow runs on PRs and is currently green — ✓ (two consecutive green runs)
- [x] Repository is **public** — verify at <https://github.com/sattyamjjain/proofloop>
- [x] No secrets, tokens, or credentials in git history — safe (no `.env`, `credentials.*`, etc.)
- [x] Version tag `v1.1.0` exists and is signed / annotated — ✓
- [x] Release notes published — ✓ <https://github.com/sattyamjjain/proofloop/releases/tag/v1.1.0>

## Assets to attach (if the form accepts files)

- **Screenshot / banner**: a cropped image of the terminal showing a
  Stop hook firing and the scorecard line. Once the demo GIF is
  recorded, use the first frame. (Save to `docs/assets/scorecard.png`
  once captured.)
- **Demo GIF**: 20-second loop. Same one the X thread and HN post
  attach. Host it in the repo at `docs/assets/demo.gif` so the
  marketplace listing can embed a hotlink.

## If the form rejects the submission

Common rejection reasons and fixes:

1. **"Name conflicts with existing plugin"** — our `name: "verdict"`
   is unique in the 144-entry snapshot, but the team may reserve the
   name internally. Fallback: resubmit as `proofloop-judge` and update
   `plugin.json` + `marketplace.json` accordingly.
2. **"Description exceeds N characters"** — use the short variant above.
3. **"README missing required section (installation / usage / license)"**
   — our README has all three.
4. **"Version string doesn't match a published tag"** — reply with
   a link to <https://github.com/sattyamjjain/proofloop/releases/tag/v1.1.0>.

## Post-submission followup

- Review timeline: based on the shape of existing entries, Anthropic
  processes new external submissions in ~3–10 business days. If no
  response after two weeks, email `plugin-team@anthropic.com`
  (or whichever address the `Contact` link on the form surfaces)
  with the submission ID.
- While waiting: submit to the 3 other marketplaces
  (`claudemarketplaces.com`, `aitmpl.com`, `buildwithclaude.com`) —
  they're independent and can land in parallel.
- When approved, the PR lands automatically on `anthropics/claude-plugins-official`;
  we don't need to open our own.
