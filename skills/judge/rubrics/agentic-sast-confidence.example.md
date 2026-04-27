# Agentic SAST Confidence — Example Run

`tests/fixtures/agentic-sast-trace.jsonl` carries 10 SAST findings
across CWE-89 (SQLi), CWE-79 (XSS), CWE-22 (path traversal), and
CWE-352 (CSRF). Seven are true positives, three are false positives.
Each finding carries a `[confidence:0.NN]` self-report from the
agent and a paired `[ground_truth:true|false]` from the fixture.

## Brier-loss math (illustrative)

For each finding, squared error = `(confidence - outcome)^2` where
outcome = 1.0 (true) or 0.0 (false). Mean of those squared errors
is the Brier loss. The fixture's well-calibrated cases (high
confidence on true positives, low confidence on false positives)
should land Brier loss in the **0.05–0.15 range**, putting Adherence
in the 7-9 band.

## Running

```bash
python3 skills/judge/scripts/score.py \
    --skill agentic-sast-confidence \
    --transcript tests/fixtures/agentic-sast-trace.jsonl \
    --rubric-dir skills/judge/rubrics \
    --scores-dir /tmp/sast-scores
```

## Expected behaviour

- `adjustments.brier_calibration.brier_loss` is in `[0.0, 1.0]`,
  computed across the 10 paired findings.
- `adjustments.brier_calibration.pair_count == 10`.
- `weights_source == "rubric"` (sidecar applied; weights lean onto
  Completeness 0.25 / Correctness 0.20).
- Composite lands in B / B+ band on this fixture.

## When the Brier loss matters

The rubric's **Adherence** dimension caps at 5/10 if Brier loss
> 0.30 (systematically over- or under-confident agent). The
informational nature is by design — Brier feeds the rubric's
written criteria but doesn't directly gate the composite. That
said, an agent reporting `confidence:0.95` on a `[ground_truth:false]`
finding contributes (0.95 - 0)² = 0.9025 to the mean, which alone
can blow past the 0.30 cap.
