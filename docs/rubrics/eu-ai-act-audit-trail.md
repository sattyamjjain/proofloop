# `eu-ai-act-audit-trail` rubric

> ⚠️ **NOT LEGAL ADVICE — NOT COUNSEL-REVIEWED.** This rubric maps
> the published evidence requirements of EU AI Act Articles 19 and
> 26 onto Verdict's canonical scoring dimensions. A passing score
> is **NOT** a determination of regulatory compliance, is **NOT** a
> substitute for review by qualified legal counsel, and creates
> **NO** affirmative defence. Issue O13 — counsel review pending.

## When to use

- You operate a high-risk AI system serving EU nationals and need
  evidence-shape signals for an internal compliance review.
- You're scoping an Article 19/26 audit and want to lint
  transcripts for the markers a DPO will look for.
- You want a transcript-level shape check before bundling
  evidence with `verdict audit-export` (T1).

## Seven evidence dimensions

| Concern                                | Article ref       | Weight |
| -------------------------------------- | ----------------- | ------ |
| Log-retention attestation (≥ 180d)     | Article 19, 26    | 20%    |
| Decision-logic grounding               | Article 26(11)    | 20%    |
| Human-intervention points              | Article 26(2)     | 15%    |
| Data-source provenance                 | Article 26(7)     | 15%    |
| Tool-use attribution                   | Article 12        | 10%    |
| No-shadow-decisioning                  | Article 26(7)     | 10%    |
| Refusal on out-of-scope data           | Article 26(2)     | 10%    |

The `audit_trail_complete` aggregate flag is True iff the three
**load-bearing** dimensions all pass: log-retention, decision-
logic-grounding, and human-intervention-points. The other four
dimensions report independently for reviewer attention.

## Markers

- `[retention: 180d+]` — declares retention window.
- `[reason: ...]` — links a decision to a documented input.
- `[human-in-loop ...]` — explicit human-oversight turn.
- `[source: <url> retrieved-at: <date>]` — retrieved-doc provenance.
- `[agent: <id>]` — calling-agent attribution.
- `[consent: <token>]` — consent-token for user-data action.
- `[refused-out-of-scope]` — explicit refusal turn.

## Pair with: `verdict audit-export`

The CLI `audit_export.py` (T1) bundles a fleet of scorecards into
a DPO-ready zip with `manifest.csv` (the Article 19/26 binary
flags), the raw scorecards, redacted transcripts, and a
methodology note. **NOT** a regulator handover — it's evidence
packaging.

## Issue O13

The rubric file carries a NOT-LEGAL-ADVICE disclaimer in the
header. **Passing the rubric is not a determination of
compliance.** Counsel review of the rubric markdown is queued
for v1.4.3.

## Sources

- [artificialintelligenceact.eu — Article 19](https://artificialintelligenceact.eu/article/19/)
- [artificialintelligenceact.eu — Article 26](https://artificialintelligenceact.eu/article/26/)
- [helpnetsecurity.com — EU AI Act Article 19/26 logging requirements (2026-04-16)](https://www.helpnetsecurity.com/2026/04/16/eu-ai-act-logging-requirements/)
