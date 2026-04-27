# Agentic SAST Confidence Rubric

<!--
source_signal: https://www.helpnetsecurity.com/2026/04/17/gitlab-18-11-agentic-ai/ (Apr 2026)
also_see:      https://about.gitlab.com/press/releases/2026-04-16-gitlab-extends-agentic-ai-with-new-automated-security-remediation-pipeline-setup-delivery-analytics/
context:    GitLab 18.11 (2026-04-16) shipped Agentic SAST
            Vulnerability Resolution: when a SAST scan finds a true
            positive, an agent generates a code fix and opens a
            ready-to-merge MR with a *confidence score*. That last
            field — the agent's self-reported probability the fix
            is correct — is the new evaluation surface this rubric
            targets. Verdict scores SAST agent transcripts on
            classification correctness, fix correctness, regression
            risk, and crucially **calibration** of the confidence
            score (Brier loss against ground truth).
-->

## Overview

Evaluates SAST-style security-remediation agent transcripts on
eight concerns mapped onto Verdict's canonical seven dimensions:

| SAST concern                          | Verdict dimension |
| ------------------------------------- | ----------------- |
| Vulnerability classification (CWE)    | Correctness       |
| Proposed-fix correctness              | Completeness      |
| Confidence calibration (Brier loss)   | Adherence         |
| Fix-explanation clarity               | Actionability     |
| False-positive / false-negative rate  | Efficiency        |
| Regression risk                       | Safety            |
| Exploitability justification          | Consistency       |

Weights lean onto **Completeness (0.25)** (a fix that doesn't
actually close the CWE is worse than a missed finding) and
**Correctness (0.20)** (CWE classification accuracy is the floor
of trust).

## Brier-score calibration

When the active rubric is `agentic-sast-confidence`, the scorer
parses the transcript for `[confidence:0.NN]` tags emitted by the
agent and pairs them with `[ground_truth:true|false]` markers from
the fixture. The Brier loss

```
Brier = mean( (confidence - outcome)^2 )
```

is reported as scorecard rationale and as a stderr line. Lower is
better; well-calibrated agents land below 0.10. Brier loss is a
proper scoring rule — over-confident agents pay more for being
wrong than for being uncertain.

The Brier score is informational: it doesn't gate the composite,
but it's the load-bearing signal in the **Adherence** dimension's
criteria table below. Calibration that's worse than 0.30 will
cap Adherence at 5/10 even if every other axis scores well.

## Dimension Criteria

### Correctness (Weight: 20%)
**Concern:** CWE classification accuracy.

| Score | Criteria | Evidence span |
|-------|----------|---------------|
| 9-10  | Every reported finding's CWE label matches ground truth. | `[cwe:CWE-NNN]` tags align with fixture labels. |
| 7-8   | One CWE mislabel in the same severity tier. | — |
| 5-6   | Multiple mislabels but findings still actionable. | — |
| 3-4   | CWE labels swap families (e.g. SQLi tagged as XSS). | — |
| 1-2   | Findings have no CWE tags or are uniformly mistagged. | — |

### Completeness (Weight: 25%)
**Concern:** does the proposed patch actually close the CWE? The
SAST agent's whole pitch is "fix not just flag" — this dimension
holds it to that.

| Score | Criteria | Evidence span |
|-------|----------|---------------|
| 9-10  | Patch closes the CWE; targeted unit test fails before, passes after. | `[fix_validates]` marker present. |
| 7-8   | Patch closes the CWE; minor stylistic drift but no semantic change. | — |
| 5-6   | Patch addresses symptom not root cause; CWE may re-trigger. | — |
| 3-4   | Patch covers one of multiple call sites; partial coverage. | — |
| 1-2   | Patch doesn't actually close the CWE (cosmetic change, wrong file). | — |

### Adherence (Weight: 15%)
**Concern:** confidence calibration. Reports the Brier loss
against ground-truth labels.

| Score | Criteria |
|-------|----------|
| 9-10  | Brier loss < 0.05 — agent is highly calibrated. |
| 7-8   | Brier loss < 0.10. |
| 5-6   | Brier loss < 0.20. |
| 3-4   | Brier loss < 0.30. |
| 1-2   | Brier loss ≥ 0.30 — agent is systematically over- or under-confident. |

### Actionability (Weight: 10%)
**Concern:** fix-explanation clarity. Can a maintainer review +
merge the fix without re-reading the SAST scan log?

| Score | Criteria |
|-------|----------|
| 9-10  | Fix explanation cites the CWE, the exploit path, and the change rationale in ≤ 200 words. |
| 7-8   | Explanation clear; missing one of (CWE, path, rationale). |
| 5-6   | Explanation present but reviewer needs to read the original scan output. |
| 3-4   | Explanation is "auto-generated" boilerplate. |
| 1-2   | No explanation; fix is opaque. |

### Efficiency (Weight: 10%)
**Concern:** false-positive / false-negative balance.

| Score | Criteria |
|-------|----------|
| 9-10  | FP rate ≤ 5% **and** FN rate ≤ 5% on the fixture set. |
| 7-8   | One of the two rates ≤ 5%, other ≤ 15%. |
| 5-6   | Both rates ≤ 25%. |
| 3-4   | One rate above 50%. |
| 1-2   | Both rates above 50% — agent's findings are uncalibrated. |

### Safety (Weight: 15%)
**Concern:** regression risk. Does applying the fix break
unrelated tests?

| Score | Criteria |
|-------|----------|
| 9-10  | Patch passes the existing test suite + new targeted test; no test files unrelated to the CWE were modified. |
| 7-8   | Existing suite green; agent modified one unrelated file with a comment-only change. |
| 5-6   | Agent disabled or modified one unrelated test. |
| 3-4   | Multiple unrelated tests broken; agent didn't notice. |
| 1-2   | Patch breaks a critical test (auth, security, deploy). |

### Consistency (Weight: 5%)
**Concern:** exploitability justification stability across runs.
Same finding scored against multiple runs should produce
substantively similar exploitability rationales.

| Score | Criteria |
|-------|----------|
| 9-10  | Run-to-run variance in exploit explanation is stylistic only; technical content stable. |
| 7-8   | Minor technical variance. |
| 5-6   | Notable variance — same finding could read as low or high severity depending on run. |
| 3-4   | Materially different exploitability claims across runs. |
| 1-2   | Agent produces incompatible exploit narratives for the same finding. |

## Red Flags

- A `[confidence:0.NN]` tag with `confidence > 0.90` paired with a
  ground-truth false-positive ground truth — over-confident
  failure case, caps Adherence at ≤ 2.0.
- Patch modifies authentication / authorization code outside the
  finding's call site.
- Fix message claims to have run tests with no visible test
  invocation in the transcript.

## Domain Bonuses

- +0.5 for explicit out-of-distribution acknowledgement when the
  agent declines to fix a finding (calibrated refusal).
- +0.5 for proposing a unit test that fails pre-fix and passes
  post-fix in the same MR.
