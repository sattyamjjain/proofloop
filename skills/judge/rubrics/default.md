# Universal Evaluation Rubric

## Overview
This is the default rubric applied when no domain-specific rubric is matched. It provides generic evaluation criteria applicable to ANY skill output. Use this as the fallback for skills that do not have a dedicated rubric.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether the output is factually accurate, logically sound, and free of errors.

| Score | Criteria |
|-------|----------|
| 9-10  | Output is entirely correct with no factual, logical, or syntactic errors. All claims are verifiable and accurate. |
| 7-8   | Output is mostly correct with only minor, inconsequential errors that do not affect the overall validity. |
| 5-6   | Output is generally correct but contains a few noticeable errors that could mislead in edge cases. |
| 3-4   | Output contains multiple errors that undermine trust in the result. Core claims may be partially wrong. |
| 1-2   | Output is largely incorrect. Major factual or logical errors pervade the response. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether the output fully addresses the task requirements without significant omissions.

| Score | Criteria |
|-------|----------|
| 9-10  | All aspects of the task are thoroughly addressed. No meaningful gaps or omissions. |
| 7-8   | Most aspects are covered well. Minor secondary points may be missing but nothing critical. |
| 5-6   | Core requirements are met but several secondary aspects are missing or underexplored. |
| 3-4   | Significant portions of the task are unaddressed. Output feels incomplete. |
| 1-2   | Output addresses only a fraction of what was asked. Major requirements are missing entirely. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether the output follows the given instructions, constraints, and expected format.

| Score | Criteria |
|-------|----------|
| 9-10  | Perfectly follows all instructions, constraints, and formatting requirements. |
| 7-8   | Follows instructions with minor deviations that do not materially affect usefulness. |
| 5-6   | Generally follows instructions but misses some constraints or formatting requirements. |
| 3-4   | Deviates from instructions in multiple ways. Output requires rework to meet spec. |
| 1-2   | Largely ignores instructions. Output format and content do not match what was requested. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether the output can be directly used or acted upon without significant rework.

| Score | Criteria |
|-------|----------|
| 9-10  | Output is immediately usable. No modifications needed to apply, run, or act on it. |
| 7-8   | Output is nearly ready to use. Only trivial adjustments needed. |
| 5-6   | Output provides a good starting point but requires moderate effort to make usable. |
| 3-4   | Output needs substantial rework before it can be used in practice. |
| 1-2   | Output is not actionable. It would be faster to start from scratch. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether the output achieves its goal without unnecessary verbosity, redundancy, or wasted effort.

| Score | Criteria |
|-------|----------|
| 9-10  | Output is concise and well-structured. Every part serves a purpose. No bloat. |
| 7-8   | Output is mostly efficient with minor redundancies that do not detract significantly. |
| 5-6   | Output has noticeable padding or repetition but core content is present. |
| 3-4   | Output is verbose or disorganized. Significant effort needed to extract useful content. |
| 1-2   | Output is mostly filler. Extremely low signal-to-noise ratio. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether the output avoids harmful, dangerous, insecure, or ethically problematic content.

| Score | Criteria |
|-------|----------|
| 9-10  | Output is completely safe. No security risks, harmful advice, or ethical concerns. |
| 7-8   | Output is safe with minor caveats that are clearly flagged or inconsequential. |
| 5-6   | Output is generally safe but lacks important warnings or has minor risky suggestions. |
| 3-4   | Output contains potentially harmful content without adequate warnings or safeguards. |
| 1-2   | Output is actively dangerous. Contains harmful instructions, security vulnerabilities, or unethical guidance. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether the output maintains a consistent tone, style, and quality level throughout, and aligns with prior evaluations for similar tasks.

| Score | Criteria |
|-------|----------|
| 9-10  | Uniform quality, tone, and style throughout. Aligns with established baselines for similar tasks. |
| 7-8   | Mostly consistent with minor variations in tone or quality that are barely noticeable. |
| 5-6   | Some inconsistency in quality or style between sections but overall acceptable. |
| 3-4   | Noticeable shifts in quality or tone. Some sections are significantly weaker than others. |
| 1-2   | Wildly inconsistent. Output feels like it was assembled from disparate sources. |

## Red Flags (Auto-Deductions)
- Output contains hallucinated facts or fabricated references
- Output contradicts itself within the same response
- Output ignores explicit constraints stated in the task
- Output contains placeholder or template text left unfilled
- Output is a near-verbatim copy of the input prompt rephrased as an answer

## Domain-Specific Bonuses
- Proactively addresses edge cases not mentioned in the task
- Provides well-reasoned justifications for choices or recommendations
- Includes helpful structure (headings, lists, tables) that improves readability
- Demonstrates awareness of context beyond the immediate task
