# Code Review Evaluation Rubric

## Overview
This rubric evaluates the quality of code review skill outputs. Use it when the skill under evaluation performs code review, pull request analysis, or code quality assessment. A good code review identifies real issues, covers all changed files, and provides actionable fix suggestions.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether identified bugs, issues, and suggestions are real and valid -- not false positives.

| Score | Criteria |
|-------|----------|
| 9-10  | Every flagged issue is a genuine bug, anti-pattern, or valid concern. Zero false positives. Severity ratings are accurate. |
| 7-8   | Nearly all flagged issues are valid. At most one minor false positive. Severity ratings are mostly accurate. |
| 5-6   | Most flagged issues are valid but includes a few false positives or mischaracterized severities. |
| 3-4   | Mix of valid and invalid findings. Several false positives erode trust in the review. |
| 1-2   | Majority of findings are false positives or completely incorrect. Review is unreliable. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether all changed files and relevant code paths are reviewed, and whether all categories of issues are considered.

| Score | Criteria |
|-------|----------|
| 9-10  | All changed files reviewed. Logic bugs, style issues, security concerns, performance, and edge cases all considered. |
| 7-8   | All major files reviewed. Most issue categories covered. Minor files or trivial changes may be skipped appropriately. |
| 5-6   | Core files reviewed but some changed files are overlooked. Only the most obvious issue categories addressed. |
| 3-4   | Several files or significant code paths are not reviewed. Major issue categories are missing. |
| 1-2   | Only a small fraction of the changes are reviewed. Review is superficial at best. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether the review follows the requested format, style guidelines, and review conventions.

| Score | Criteria |
|-------|----------|
| 9-10  | Follows all specified review conventions. Uses requested format (inline comments, summary, severity labels). Respects scope. |
| 7-8   | Follows conventions with minor formatting deviations. Review stays within scope. |
| 5-6   | Generally follows format but missing some requested elements (e.g., no severity labels, missing summary). |
| 3-4   | Deviates significantly from requested format or conventions. Review scope drifts. |
| 1-2   | Ignores review conventions entirely. Output does not resemble the requested format. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether each finding includes a clear, implementable fix suggestion that a developer can act on immediately.

| Score | Criteria |
|-------|----------|
| 9-10  | Every finding includes a specific fix suggestion, often with code snippets. Developer can address each item without further clarification. |
| 7-8   | Most findings have clear fix suggestions. A few may require minor developer interpretation. |
| 5-6   | Findings identify problems but fix suggestions are vague or incomplete for several items. |
| 3-4   | Most findings describe problems without suggesting fixes. Developer must figure out solutions independently. |
| 1-2   | Findings are vague observations with no actionable guidance. "This looks wrong" without explanation. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether the review is focused and avoids nitpicking trivial issues while missing important ones.

| Score | Criteria |
|-------|----------|
| 9-10  | Review prioritizes high-impact issues. Appropriate detail level per severity. No noise or bikeshedding. |
| 7-8   | Review is mostly focused. Minor nitpicks present but clearly marked as low-priority. |
| 5-6   | Review mixes high-impact findings with excessive trivial comments. Some bikeshedding. |
| 3-4   | Review is dominated by trivial style comments while missing or burying important issues. |
| 1-2   | Review is pure noise. Focuses entirely on irrelevant details and misses every significant issue. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether the review identifies security vulnerabilities, unsafe patterns, and potential exploits in the code under review.

| Score | Criteria |
|-------|----------|
| 9-10  | All security-relevant issues identified: injection risks, auth flaws, data exposure, unsafe deserialization, etc. |
| 7-8   | Major security issues identified. Minor security concerns may be overlooked but nothing critical is missed. |
| 5-6   | Some security issues flagged but coverage is inconsistent. Obvious vulnerabilities caught, subtle ones missed. |
| 3-4   | Security dimension is largely ignored. Only the most blatant vulnerabilities are flagged, if any. |
| 1-2   | No security issues identified despite clear vulnerabilities in the code. Or review itself suggests insecure fixes. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether the review applies standards uniformly across all files and maintains consistent severity ratings.

| Score | Criteria |
|-------|----------|
| 9-10  | Same standards applied to all files. Severity ratings are calibrated consistently. Similar issues get similar treatment. |
| 7-8   | Mostly consistent. Minor calibration drift between early and late files in the review. |
| 5-6   | Some inconsistency in how similar issues are rated or described across different files. |
| 3-4   | Clearly inconsistent. Same pattern flagged as critical in one file and ignored in another. |
| 1-2   | No consistency. Severity ratings appear random. Standards shift throughout the review. |

## Red Flags (Auto-Deductions)
- Missed an obvious bug that would cause a runtime error or crash
- Flagged correct code as buggy (high-confidence false positive)
- Provided no actionable suggestions for any finding
- Suggested a fix that would introduce a new bug or security vulnerability
- Reviewed files that were not part of the changeset (hallucinated files)
- Missed a clear SQL injection, XSS, or authentication bypass

## Domain-Specific Bonuses
- Identifies subtle race conditions or concurrency issues
- Catches edge cases in error handling paths
- Suggests performance improvements with measurable impact
- Links findings to relevant documentation or best practices
- Provides before/after code snippets for complex fixes
- Identifies cross-file interaction bugs
