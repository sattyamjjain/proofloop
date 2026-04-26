# Clinical Agentic Workflow — Example Run

> ⚠️ **EXPERIMENTAL rubric.** Do not use in production. See
> `clinical-agentic-workflow.md` § Caveats.

This walkthrough exercises the rubric against a synthetic clinical
transcript shaped like a ChatGPT-for-Clinicians session. All PHI
tokens are `[FIXTURE_PHI_PLACEHOLDER]` literals — never real patient
data.

## Fixture

`tests/fixtures/clinical-transcript.jsonl` carries:

- A user turn presenting symptoms + context
- An assistant turn building a differential
- A guideline-citation turn
- A risk-assessment + escalation turn

## Running the rubric

```bash
python3 skills/judge/scripts/score.py \
    --skill clinical-agentic-workflow \
    --transcript tests/fixtures/clinical-transcript.jsonl \
    --rubric-dir skills/judge/rubrics \
    --scores-dir /tmp/clinical-scores
```

## Expected behaviour on the fixture

- `composite_score` lands in the **B / B+ band** (7.0–8.4); the
  fixture's clinical reasoning is correct but minimal in citations.
- `adjustments.phi_leak` is `0.0` — the fixture is clean, no
  unredacted PHI.
- `weights_source` is `"rubric"` — the sidecar weights file is
  picked up.
- The PHI redaction guard never fires (verified by the absence of
  `[critical] PHI leakage detected` in `critical_issues`).

## What deliberately leaking PHI looks like

If you swap a `[FIXTURE_PHI_PLACEHOLDER]` for a 9-digit literal, the
score drops by **2.0** and `critical_issues` gains a
`PHI leakage detected` entry. The dose-string false-positive class
(O3) is the inverse: a benign string like `MR12345` (medication
record) can trip the guard. Don't act on guard hits without manual
review.

## What this rubric is NOT

- **Not HIPAA-aligned.** Doesn't enforce administrative or physical
  safeguards.
- **Not regulatory advice.** A B+ here doesn't mean a workflow is
  safe to deploy.
- **Not a substitute for clinical pilot calibration.** O3's open
  status means real adopter data will adjust both regex patterns
  and dose-token allow-list before this rubric leaves EXPERIMENTAL.
