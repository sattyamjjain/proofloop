# Data Analysis Evaluation Rubric

## Overview
This rubric evaluates the quality of data analysis and analytics skill outputs. Use it when the skill under evaluation performs statistical analysis, data visualization, trend identification, forecasting, or data-driven recommendations. Good data analysis is mathematically sound, examines all relevant data, and produces clear, actionable recommendations.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether all calculations, statistical methods, and mathematical operations are correct and appropriately applied.

| Score | Criteria |
|-------|----------|
| 9-10  | All calculations verified correct. Statistical methods are appropriate for the data type and distribution. Confidence intervals and significance levels properly computed. |
| 7-8   | Calculations are correct. Statistical methods are appropriate. Minor rounding or presentation issues that do not affect conclusions. |
| 5-6   | Core calculations are correct but some statistical methods may be slightly inappropriate or oversimplified for the data. |
| 3-4   | Multiple calculation errors or use of inappropriate statistical methods that could lead to wrong conclusions. |
| 1-2   | Fundamental math errors. Wrong statistical tests applied. Conclusions are not supported by the data. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether all relevant data was examined, all requested analyses were performed, and results include necessary context.

| Score | Criteria |
|-------|----------|
| 9-10  | All relevant data examined. All requested analyses performed. Results include confidence intervals, sample sizes, and limitations. Outliers addressed. Missing data handled transparently. |
| 7-8   | Most data examined and analyses performed. Minor supplementary analyses may be missing. Key context provided. |
| 5-6   | Core analyses performed but some relevant data segments or requested analyses are missing. Limited context. |
| 3-4   | Significant data segments or analyses are missing. Results lack important context (no sample sizes, confidence levels). |
| 1-2   | Only a fraction of the data or requested analyses are addressed. Missing critical context. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether the analysis follows the requested methodology, output format, and reporting standards.

| Score | Criteria |
|-------|----------|
| 9-10  | Follows requested methodology exactly. Output format matches spec (tables, charts, executive summary). Uses specified tools and libraries. |
| 7-8   | Follows methodology with minor adjustments that are justified. Output format mostly matches spec. |
| 5-6   | Generally follows methodology but takes some unjustified shortcuts. Output format partially matches. |
| 3-4   | Significant methodology deviations without justification. Output format does not match spec. |
| 1-2   | Ignores requested methodology entirely. Output bears no resemblance to the requested format. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether the analysis produces clear, specific recommendations that decision-makers can act on.

| Score | Criteria |
|-------|----------|
| 9-10  | Clear, prioritized recommendations tied directly to data findings. Each recommendation has supporting evidence. Next steps are specific and implementable. |
| 7-8   | Good recommendations linked to findings. Most are specific enough to act on. |
| 5-6   | Some recommendations provided but they are generic or loosely connected to the actual data findings. |
| 3-4   | Few recommendations. Those present are vague ("improve performance") without specific guidance. |
| 1-2   | No recommendations. Analysis is purely descriptive with no path to action. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether the analysis is focused, avoids unnecessary complexity, and presents findings in a digestible format.

| Score | Criteria |
|-------|----------|
| 9-10  | Analysis is focused and efficient. Key findings highlighted upfront. Visualizations are clear and purposeful. No unnecessary metrics or charts. |
| 7-8   | Mostly focused. Minor inclusion of tangential metrics that do not distract from core findings. |
| 5-6   | Some unnecessary analyses or visualizations. Key findings could be presented more concisely. |
| 3-4   | Analysis is bloated with unnecessary metrics. Key findings are buried. Visualizations are cluttered or redundant. |
| 1-2   | Extremely unfocused. Dozens of metrics with no hierarchy. Impossible to identify key findings. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether the analysis avoids misleading presentations, cherry-picked data, and conclusions that misrepresent the underlying data.

| Score | Criteria |
|-------|----------|
| 9-10  | Data presented honestly. Limitations explicitly stated. No misleading axis scales, truncated charts, or cherry-picked time ranges. Biases acknowledged. |
| 7-8   | Data presented fairly. Minor presentation choices could be improved but nothing misleading. |
| 5-6   | Generally fair but some visualization choices could mislead casual readers (e.g., non-zero axis without note). |
| 3-4   | Some cherry-picked data or misleading presentations. Limitations not disclosed. Conclusions overstate findings. |
| 1-2   | Actively misleading. Cherry-picked data to support predetermined conclusions. Deceptive visualizations. Ignores contradictory evidence. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether the analysis maintains consistent methodology, formatting, and terminology throughout.

| Score | Criteria |
|-------|----------|
| 9-10  | Consistent statistical methodology throughout. Uniform chart styling. Same terminology used for same concepts. |
| 7-8   | Mostly consistent. Minor formatting variations between sections. |
| 5-6   | Some inconsistency in methodology or presentation between different parts of the analysis. |
| 3-4   | Different sections use different approaches to similar data. Inconsistent terminology causes confusion. |
| 1-2   | No consistency. Looks like separate analyses cobbled together. |

## Red Flags (Auto-Deductions)
- Cherry-picked data that ignores contradictory evidence
- Wrong statistical methods for the data type (e.g., parametric test on non-normal data without justification)
- Misleading chart axes, truncated scales, or deceptive visualizations
- Correlation presented as causation without qualification
- Missing sample size or confidence interval for key findings
- Calculations that can be verified as mathematically wrong
- Ignoring outliers without explanation

## Domain-Specific Bonuses
- Includes sensitivity analysis or robustness checks
- Provides reproducible analysis with code and data references
- Uses appropriate statistical power analysis
- Includes interactive visualizations or drill-down capability
- Segments analysis by meaningful cohorts
- Accounts for confounding variables
- Provides prediction intervals for forecasts
- Includes methodology comparison (e.g., "we chose method X over Y because...")
