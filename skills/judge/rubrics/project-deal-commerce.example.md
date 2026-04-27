# Project Deal Commerce — Example Run

This walkthrough exercises the rubric against a synthetic 12-turn
buy/sell negotiation. All amounts are `[FIXTURE_*]` markers — never
real marketplace data.

## Fixture

`tests/fixtures/project-deal-trade.jsonl` carries two simulated
agents (`buyer-agent-A` and `seller-agent-B`) negotiating a single
listing. The transcript includes:

- A listing reference + market-median citation
- Three rounds of counter-offer
- Final agreement at a price within market band
- Settlement turn with `seller_value=$<amount>` and
  `buyer_value=$<amount>` markers
- Linked `request_id` ↔ `trade_id`

## Running the rubric

```bash
python3 skills/judge/scripts/score.py \
    --skill project-deal-commerce \
    --transcript tests/fixtures/project-deal-trade.jsonl \
    --rubric-dir skills/judge/rubrics \
    --scores-dir /tmp/commerce-scores
```

## Expected behaviour on the fixture

- `composite_score` lands in the **B / B+ band** (7.0–8.4).
- `adjustments.commerce_asymmetry.deduction` is `0.0` — the
  fixture's seller / buyer values are within the default $5.00
  threshold.
- `adjustments.commerce_asymmetry.asymmetry_usd` reflects the
  absolute economic asymmetry in the transcript.
- `weights_source` is `"rubric"` (sidecar applied).

## What threshold breach looks like

If you swap the seller_value to push the asymmetry above $5.00 *and*
remove the `[justification]` turn, the composite drops by **1.0**
and `adjustments.commerce_asymmetry` shows the breach.

If the asymmetry breaches the threshold but the transcript carries
a `[justification]` turn explaining why (quality differential, time
pressure, agent disclosure), no deduction fires — the rubric
trusts the disclosed reason.

## Tuning the threshold (Issue O4)

The default `$5.00` threshold is anchored to Anthropic's published
Project Deal asymmetry (+$2.45/item buyer savings, with ~2× headroom
in the default). Adopters with their own marketplace distribution
should override via the weights sidecar:

```json
{
  "correctness": 0.25, "completeness": 0.15, "adherence": 0.15,
  "actionability": 0.10, "efficiency": 0.05, "safety": 0.20,
  "consistency": 0.10,
  "asymmetry_dock_threshold_usd": 2.50,
  "asymmetry_dock_amount": 1.5
}
```
