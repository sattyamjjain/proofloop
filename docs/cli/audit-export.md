# `verdict audit-export` CLI (T1)

> ⚠️ **NOT LEGAL ADVICE.** Output is **not** a compliance
> attestation and is **not** a substitute for counsel review.
> Issue O13 — counsel review of the underlying rubric is pending.

## Purpose

Bundle a fleet of Verdict scorecards (filterable by date and
rubric) into a DPO-ready zip suitable for an external auditor.

## Usage

```shell
python3 skills/judge/scripts/audit_export.py \
    --scores-dir skills/judge/scores \
    --since 2025-11-01 \
    --until 2026-04-29 \
    --rubric eu-ai-act-audit-trail \
    --out audit-bundle-2026-04-29.zip
```

## Bundle layout

- `manifest.csv` — one row per scorecard with the Article 19/26
  binary flags.
- `scorecards/<name>.json` — raw evidence (verbatim copies).
- `transcripts-redacted/<name>.jsonl` — best-effort PII-redacted
  transcript copies (only when `--transcripts-root` is given).
- `methodology.md` — signal-to-Article mapping + disclaimer.

## PII redaction (Issue O16)

Best-effort regex pass:

- Emails → `<EMAIL>`
- Phone-shapes → `<PHONE>`
- SSN-shapes → `<SSN>`
- API keys (`sk-…`) → `<API_KEY>`
- AWS keys (`AKIA…`) → `<AWS_KEY>`
- GitHub tokens (`ghp_…`) → `<GH_TOKEN>`

**NOT** sufficient for high-risk health / financial PII.
`audit-export` **refuses** to bundle transcripts whose rubric is
`clinical-agentic-workflow` until a hardened redactor lands in
v1.4.3.

## Exit codes

- `0` — bundle produced.
- `2` — invalid input (missing scores dir).
