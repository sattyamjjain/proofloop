# Research & Exploration Evaluation Rubric

## Overview
This rubric evaluates skills that search, explore, investigate, or analyze codebases and information sources. Use it for skills like codebase exploration, research analysis, information gathering, and investigative tasks where the primary output is knowledge and findings rather than code changes.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether findings are factually accurate, references are valid, and conclusions are logically sound.

| Score | Criteria |
|-------|----------|
| 9-10  | All findings are verifiable and accurate. References point to real files, functions, or sources. No fabricated claims. |
| 7-8   | Findings are mostly accurate with minor inaccuracies that do not affect overall conclusions. |
| 5-6   | Some findings are correct but others contain errors or unverified claims that could mislead. |
| 3-4   | Multiple factual errors. References to non-existent files or functions. Conclusions based on flawed analysis. |
| 1-2   | Findings are largely fabricated or hallucinated. References are invalid. Conclusions are unsupported. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether the research covers all requested topics, explores relevant areas, and provides sufficient depth.

| Score | Criteria |
|-------|----------|
| 9-10  | All research questions fully answered. Relevant edge cases and related areas proactively explored. Comprehensive coverage. |
| 7-8   | Most topics covered well. Minor gaps in coverage that do not affect the overall usefulness of findings. |
| 5-6   | Core questions answered but several related areas unexplored. Research feels surface-level in places. |
| 3-4   | Significant topics left unexamined. Research is shallow and misses important connections. |
| 1-2   | Only a fraction of the research scope addressed. Major topics entirely missing. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether the research follows the requested methodology, scope constraints, and output format.

| Score | Criteria |
|-------|----------|
| 9-10  | Follows all research constraints. Stays within scope. Output format matches expectations precisely. |
| 7-8   | Generally follows instructions with minor scope creep or formatting deviations. |
| 5-6   | Partially follows instructions but diverges on methodology or scope in noticeable ways. |
| 3-4   | Significant deviations from requested approach. Output format does not match expectations. |
| 1-2   | Ignores research constraints entirely. Produces output in an unexpected format or scope. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether findings are organized, clearly presented, and immediately usable for decision-making or next steps.

| Score | Criteria |
|-------|----------|
| 9-10  | Findings are well-organized with clear structure. Includes specific file paths, line numbers, and actionable next steps. |
| 7-8   | Findings are mostly well-organized. Key references are provided. Minor gaps in actionability. |
| 5-6   | Findings require additional work to act on. Missing some specific references or next steps. |
| 3-4   | Findings are disorganized. Lack specific references. Require significant effort to use. |
| 1-2   | Findings are unusable without starting the research over. No specific references or structure. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether the research was conducted without unnecessary searches, redundant file reads, or excessive tangents.

| Score | Criteria |
|-------|----------|
| 9-10  | Research path is direct and focused. No redundant searches. Tools used appropriately. |
| 7-8   | Mostly efficient with minor unnecessary steps that do not significantly affect results. |
| 5-6   | Some wasted effort on tangents or redundant searches but core research is present. |
| 3-4   | Significant inefficiency. Many redundant searches or unnecessary tangents. |
| 1-2   | Extremely wasteful. More time spent on irrelevant paths than actual findings. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether the research avoids exposing sensitive information, credentials, or private data found during exploration.

| Score | Criteria |
|-------|----------|
| 9-10  | No sensitive data exposed. Credentials, tokens, and private information properly redacted in output. |
| 7-8   | Safe with minor caveats. Any sensitive findings are flagged appropriately. |
| 5-6   | Generally safe but lacks explicit handling of sensitive data encountered during research. |
| 3-4   | Exposes some sensitive information without adequate warnings or redaction. |
| 1-2   | Outputs credentials, secrets, or private data without any redaction or warning. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether the research maintains consistent depth, methodology, and quality across all topics explored.

| Score | Criteria |
|-------|----------|
| 9-10  | Uniform depth and quality across all researched topics. Consistent methodology throughout. |
| 7-8   | Mostly consistent with minor variations in depth between topics. |
| 5-6   | Noticeable inconsistency — some topics explored deeply while others are superficial. |
| 3-4   | Significant quality gaps between sections. Some topics are thorough, others are barely touched. |
| 1-2   | Wildly inconsistent. Output feels like fragments from different research sessions. |

## Red Flags (Auto-Deductions)
- Hallucinated file paths or function names that do not exist in the codebase
- Fabricated references to documentation or external sources
- Drawing conclusions from a single data point without acknowledging limitations
- Ignoring contradictory evidence found during research
- Presenting speculation as established fact

## Domain-Specific Bonuses
- Discovers non-obvious connections between components or systems
- Provides historical context (git history, commit messages) for findings
- Includes visual diagrams or structured summaries of complex relationships
- Proactively identifies risks or issues beyond the original research scope
