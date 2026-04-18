# Security policy

Verdict ships as a local Claude Code / Cowork plugin. It does not
collect telemetry, does not make network calls, and depends on no
third-party Python packages. Its threat surface is therefore narrow —
but report anything that looks wrong.

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.** Instead:

1. Email **<sattyamjain96@gmail.com>** with a subject line of the form
   `[Verdict security] <one-line summary>`.
2. Include:
   - Affected version (`git describe --tags`).
   - Reproduction steps or a proof-of-concept — ideally against the
     scoring engine, a hook script, an adapter, or a validator.
   - Impact assessment (what can an attacker do / see / change?).
   - Your preferred disclosure timeline.

You should get an acknowledgement within **3 business days**.

## Supported versions

| Version   | Supported | Notes                                                |
| --------- | :-------: | ---------------------------------------------------- |
| `1.1.x`   | ✅        | Current release line; security fixes land here.       |
| `1.0.x`   | ❌        | Superseded by `1.1.0`; upgrade instead.               |
| `< 1.0`   | ❌        | Never existed as a public release.                    |

## Scope

In scope:

- Scoring engine (`skills/judge/scripts/score.py`, `report.py`,
  `benchmark.py`, `against.py`, `studio.py`).
- Hook scripts (`hooks/*.sh`).
- Adapters (`skills/judge/adapters/*.py`).
- Utility scripts under `scripts/`.
- `judge-config.json` parsing and validation.
- Marketplace manifest validator.

Out of scope (report to the upstream project instead):

- Claude Code itself — <https://github.com/anthropics/claude-code>.
- Claude Cowork / claude.ai infrastructure — <https://support.claude.com>.
- Third-party rubrics installed via `scripts/install_rubric.py` — the
  rubric's own maintainer is responsible. Verdict does validate the
  rubric structure before install; a validation bypass *is* in scope.

## Hardening already in place

The scoring engine is **stdlib-only Python 3.9+** — no pip install, no
supply-chain surface. The hook scripts use `set -euo pipefail`, quote
`jq` outputs, and pass transcripts by path rather than concatenating
shell arguments. Destructive patterns (`rm -rf`, `chmod 777`,
`--no-verify`, exposed credentials) are flagged by the safety
analyser itself — so the tool detects the class of risk it could
otherwise introduce.

The install-rubric utility (`scripts/install_rubric.py`) fetches only
over HTTPS and validates that downloaded markdown contains the Verdict
dimension headings before writing it to disk — a malformed or
intentionally-crafted rubric cannot execute code at install time.

## What we will not do

- Pay bounties. (No bug-bounty program yet.)
- Publicly credit a reporter without their explicit consent.
- Silently patch — every security fix ships with a `CHANGELOG.md`
  entry that describes the issue once the fix is public.
