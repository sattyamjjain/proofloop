# Scoring Methodology

## Overview
This document defines the mathematical framework for computing evaluation scores, assigning grades, and handling edge cases in the judge skill's scoring system.

## Weighted Composite Formula

The final score for an evaluation is computed as a weighted sum of individual dimension scores:

```
composite_score = sum(dimension_score_i * weight_i) for all dimensions
```

Explicitly:

```
composite_score = (correctness * 0.25)
                + (completeness * 0.20)
                + (adherence * 0.15)
                + (actionability * 0.15)
                + (efficiency * 0.10)
                + (safety * 0.10)
                + (consistency * 0.05)
```

All dimension scores are on a 1-10 scale. The composite score is also on a 1-10 scale since the weights sum to 1.0.

### Custom Weight Overrides
Rubrics may specify custom weights that differ from the defaults above. When custom weights are present, they MUST sum to 100% (1.0). The composite formula remains the same; only the weight values change.

## Grade Thresholds

Composite scores map to letter grades using the following exact ranges:

| Grade | Range         | Label        | Description |
|-------|---------------|--------------|-------------|
| A+    | 9.50 - 10.00  | Exceptional  | Virtually flawless. Exceeds expectations in every dimension. |
| A     | 9.00 - 9.49   | Excellent    | Outstanding quality with only the most trivial imperfections. |
| A-    | 8.50 - 8.99   | Very Good    | High quality across all dimensions. Minor issues only. |
| B+    | 8.00 - 8.49   | Good         | Solid output with a few noticeable but non-critical issues. |
| B     | 7.50 - 7.99   | Above Average| Competent output that meets expectations with room for improvement. |
| B-    | 7.00 - 7.49   | Satisfactory | Meets basic requirements. Some dimensions need improvement. |
| C+    | 6.50 - 6.99   | Adequate     | Acceptable but clearly below professional standards. |
| C     | 6.00 - 6.49   | Mediocre     | Barely meets minimum requirements. Multiple areas need work. |
| C-    | 5.50 - 5.99   | Below Average| Falls short of expectations in several dimensions. |
| D+    | 5.00 - 5.49   | Poor         | Significant deficiencies. Output requires major rework. |
| D     | 4.00 - 4.99   | Very Poor    | Fails to meet most requirements. Fundamental issues present. |
| F     | 1.00 - 3.99   | Failing      | Output is unusable or severely flawed. Does not fulfill the task. |

### Boundary Rules
- Scores are computed to two decimal places.
- Boundary scores are inclusive of the lower bound and exclusive of the upper bound, except for the top grade (A+) which is inclusive on both ends.
- Example: A score of 9.00 is an "A", not an "A-". A score of 8.99 is an "A-", not an "A".

## Auto-Deductions

Red flags listed in domain-specific rubrics trigger automatic score deductions:

### Deduction Rules
1. Each red flag deducts **0.5 points** from the composite score by default.
2. A single evaluation can accumulate a maximum of **2.0 points** in auto-deductions.
3. Auto-deductions are applied AFTER the weighted composite is calculated.
4. The composite score cannot go below 1.0 after deductions.
5. Each unique red flag can only be applied once per evaluation (no double-counting).

### Deduction Formula
```
final_score = max(1.0, composite_score - (num_red_flags * 0.5))
where num_red_flags <= 4 (cap at 2.0 total deduction)
```

### Reporting
When auto-deductions are applied, the evaluation report must list:
- The original composite score before deductions
- Each red flag triggered with a brief explanation
- The deduction amount per flag
- The final adjusted score

## Domain-Specific Bonuses

Bonuses listed in domain-specific rubrics can increase the composite score:

### Bonus Rules
1. Each bonus adds **0.25 points** to the composite score.
2. A single evaluation can accumulate a maximum of **1.0 points** in bonuses.
3. Bonuses are applied AFTER auto-deductions.
4. The composite score cannot exceed 10.0 after bonuses.
5. Each unique bonus can only be applied once per evaluation.

### Bonus Formula
```
final_score_with_bonus = min(10.0, final_score + (num_bonuses * 0.25))
where num_bonuses <= 4 (cap at 1.0 total bonus)
```

## Tie-Breaking Rules

When two or more skill outputs receive the same final composite score, ties are broken using the following priority order:

1. **Correctness score** -- Higher correctness wins (most heavily weighted, most important).
2. **Safety score** -- Higher safety wins (critical dimension regardless of weight).
3. **Completeness score** -- Higher completeness wins.
4. **Actionability score** -- Higher actionability wins.
5. **Adherence score** -- Higher adherence wins.
6. **Efficiency score** -- Higher efficiency wins.
7. **Consistency score** -- Higher consistency wins.
8. **Fewer red flags** -- The output with fewer auto-deductions wins.
9. **More bonuses** -- The output with more domain-specific bonuses wins.

If all tie-breaking criteria are identical, the outputs are declared equivalent.

## Consistency Measurement

The Consistency dimension has a special cross-evaluation component:

### Within-Output Consistency (Primary)
Measured by evaluating uniformity of quality, tone, and standards across different sections of the same output. This is the score reported in the dimension.

### Historical Consistency (Supplementary)
When historical evaluation data is available for the same skill:
1. Compare the current output's dimension scores to the rolling average of the last 10 evaluations.
2. Calculate the standard deviation of each dimension across historical evaluations.
3. If the current evaluation's score deviates by more than 2 standard deviations from the historical mean in any dimension, flag it for review.
4. Historical consistency does NOT directly affect the composite score but is reported as supplementary information.

### Baseline Calibration
For the first evaluation of a new skill (no historical data), consistency is measured purely on within-output uniformity. Historical tracking begins with the first evaluation.

## Score Computation Order

The complete scoring pipeline executes in this order:

1. Score each of the 7 dimensions on a 1-10 scale.
2. Compute the weighted composite score using the formula.
3. Identify and apply auto-deductions (capped at -2.0).
4. Identify and apply domain-specific bonuses (capped at +1.0).
5. Clamp the final score to the [1.0, 10.0] range.
6. Map the final score to a letter grade.
7. Compare against historical data if available and flag anomalies.
8. Generate the evaluation report with all details.
