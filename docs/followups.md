# Followups required from Daisy

Actions I can't take autonomously. Each has a direct preparation
committed so you can act without re-deriving the work.

## Now (post-v1.1.0 release)

### 1. Activate the CI workflow

The workflow is committed to `ci/workflow.yml` (not yet to
`.github/workflows/ci.yml`) because the release-time OAuth token
lacked the `workflow` scope. Install it with the one-liner:

```shell
gh auth refresh -h github.com -s workflow
./ci/install.sh
git push
```

That moves `ci/workflow.yml` into `.github/workflows/ci.yml`, commits
the move, and triggers the first CI run. Pipeline runs the 237-test
suite, `scripts/validate_marketplace.py`, `scripts/benchmark_pack.py`,
and `shellcheck hooks/*.sh` on every PR across Python 3.9/3.11/3.12.

### 2. Submit marketplace PRs

Each upstream marketplace is its own PR; they can't be generated
automatically because they require your GitHub identity.

- [ ] `anthropics/claude-plugins-official` — add a plugin entry
      pointing at `github.com/sattyamjjain/proofloop`. Use the existing
      `.claude-plugin/marketplace.json` as the source of truth.
- [ ] `claudemarketplaces.com` — follow their PR template.
- [ ] `aitmpl.com` — same.
- [ ] `buildwithclaude.com` — same.

Prepared: `docs/research-log.md` has the current marketplace schema
cited, and `scripts/validate_marketplace.py` confirms our manifest is
valid.

### 3. Acquire domain

Pick one; tell me which before registering.

- `proofloop.dev` — preferred.
- `getverdict.com` — fallback.

Point DNS at Cloudflare Pages once the docs site lands.

### 4. Logo and demo GIF

Drafted in `docs/launch/x-thread.md` (tweet 1 = GIF attachment):

- Gavel logo, SVG + PNG. Fiverr $100 OR Midjourney prompt:
  "minimal gavel icon, line art, single color, dark background, flat,
  dev-tools logo aesthetic, SVG-export-ready".
- 20-second looping GIF of the Stop hook firing and the scorecard
  appearing in the terminal. Keep it under 5 MB so HN accepts it.
- 90-second Loom covering the auto-score flow + `/scorecard` trend
  view + `/benchmark` delta report.

## Launch window (Tuesday 13:00 UTC, after Phase 1 lands)

Each of these has a prepared draft under `docs/launch/`:

- [ ] HN submission — draft in `docs/launch/hn-faq.md`
- [ ] /r/ClaudeAI post — draft in `docs/launch/reddit-post.md`
- [ ] X thread (8 tweets) — draft in `docs/launch/x-thread.md`
- [ ] Creator DMs (10) — templates in `docs/launch/dm-templates.md`
- [ ] Conference pitches — drafts in `docs/launch/pitches.md`
- [ ] Email `plugin-team@anthropic.com` after week 4 with install
      metrics for featured-placement consideration

## Later

- [ ] Discord server — create the invite and link it from README
- [ ] Monthly "State of Claude Code Skill Quality" blog post — aggregate
      anonymised scorecards from opt-in users (requires an opt-in flag
      in `judge-config.json` first; not yet implemented).
- [ ] Case studies (weeks 8, 10, 12) — three teams showing QoQ skill-
      quality improvement with Proofloop.
- [ ] `rubrics.proofloop.dev` — static Cloudflare Pages index of
      community rubrics once 10+ community contributions land.

## Items I deliberately did NOT ship

These require verification against systems I can't reach from this
session; pushing them now would be speculative code:

- **Real per-ecosystem adapters for Gemini CLI and Windsurf.** The
  shipped adapters cover Claude Code, Cowork, Codex, Cursor, Continue
  via the OpenAI-compatible shape. Gemini CLI (v0.38+) and Windsurf
  have ecosystem-specific shapes I couldn't verify offline. Next step:
  capture one session from each, commit as a fixture, add the adapter.
- **OTel score pipeline (`score_otel.py`).** Gated on agent-airlock
  publishing `docs/observability/semconv.md`. Once that lands, wiring
  up is a ~200-line file; the skeleton is implied by the existing
  `build_scorecard` signature.
- **Opt-in small-judge (Haiku 4.5 / Atla Selene).** The roadmap explicitly
  calls for opt-in behaviour; shipping the gate without the actual
  implementation would be worse than nothing. Proposed config shape:
  `small_judge.enabled: false, small_judge.model: claude-haiku-4-5`.
- **`rubric-model-drift-detected` flag.** Needs at least two weeks of
  real score history at different models; can't simulate meaningfully
  yet.
