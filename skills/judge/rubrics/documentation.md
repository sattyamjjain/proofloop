# Documentation Evaluation Rubric

## Overview
This rubric evaluates the quality of documentation generation skill outputs. Use it when the skill under evaluation produces API documentation, README files, user guides, tutorials, or technical reference material. Good documentation is technically accurate, complete, and includes copy-paste ready examples.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether the documentation is technically accurate -- function signatures match reality, code examples work, and descriptions reflect actual behavior.

| Score | Criteria |
|-------|----------|
| 9-10  | All technical content is accurate. Code examples compile/run correctly. Parameter types, return values, and behavior descriptions match the actual code. |
| 7-8   | Technically accurate with minor imprecisions (e.g., slightly outdated parameter default). All code examples work. |
| 5-6   | Mostly accurate but contains some incorrect parameter descriptions or code examples with minor bugs. |
| 3-4   | Multiple inaccuracies. Some code examples fail. Function signatures or descriptions do not match actual behavior. |
| 1-2   | Pervasive inaccuracies. Code examples are broken. Descriptions contradict the actual implementation. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether all public APIs, parameters, return types, exceptions, and edge cases are documented.

| Score | Criteria |
|-------|----------|
| 9-10  | All public APIs documented. Every parameter, return type, and exception described. Edge cases and limitations noted. Includes quickstart, reference, and troubleshooting sections. |
| 7-8   | All primary APIs documented. Most parameters and return types described. Minor utility functions may be omitted. |
| 5-6   | Core APIs documented but secondary APIs, some parameters, or error conditions are missing. |
| 3-4   | Only the most prominent APIs documented. Many parameters, return types, and error conditions omitted. |
| 1-2   | Documentation covers only a fraction of the API surface. Major endpoints or classes are entirely missing. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether the documentation follows the requested format, style guide, and structural conventions.

| Score | Criteria |
|-------|----------|
| 9-10  | Follows the specified documentation format exactly (JSDoc, Sphinx, Swagger, etc.). Consistent style throughout. |
| 7-8   | Follows format with minor deviations. Style is mostly consistent. |
| 5-6   | Generally follows format but some sections use inconsistent structure or miss required fields. |
| 3-4   | Significant format deviations. Mixes documentation styles. Missing required sections. |
| 1-2   | Does not follow any recognizable documentation standard. Freeform text with no structure. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether code examples are copy-paste ready and whether a developer can use the docs to accomplish tasks without additional research.

| Score | Criteria |
|-------|----------|
| 9-10  | Every API has a working code example. Examples cover common use cases and can be copy-pasted directly. Includes installation, setup, and first-use walkthrough. |
| 7-8   | Most APIs have examples. Examples work with minor adjustments (e.g., replacing placeholder values). |
| 5-6   | Some examples provided but coverage is spotty. Examples may need moderate modification to work. |
| 3-4   | Few or no code examples. Descriptions are abstract without showing how to actually use the API. |
| 1-2   | No working examples. Documentation is purely descriptive with no practical guidance. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether the documentation is concise and well-organized, avoiding unnecessary repetition while being easy to navigate.

| Score | Criteria |
|-------|----------|
| 9-10  | Well-organized with clear hierarchy. No unnecessary repetition. Easy to scan. Cross-references used effectively. |
| 7-8   | Good organization. Minor redundancies that do not hinder navigation. |
| 5-6   | Adequate organization but some sections are verbose or information is duplicated across sections. |
| 3-4   | Poorly organized. Hard to find specific information. Significant repetition. |
| 1-2   | No discernible organization. Wall of text. Extreme verbosity with little useful content. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether code examples avoid insecure patterns and whether the documentation includes appropriate security warnings.

| Score | Criteria |
|-------|----------|
| 9-10  | Code examples follow security best practices. Security-sensitive APIs have explicit warnings. No hardcoded credentials in examples. |
| 7-8   | Examples are generally secure. Security-sensitive areas are noted. Placeholder credentials used instead of real ones. |
| 5-6   | Examples mostly safe but lack security warnings on sensitive operations. |
| 3-4   | Some examples demonstrate insecure patterns (e.g., disabling SSL verification) without warnings. |
| 1-2   | Examples contain hardcoded credentials, SQL injection patterns, or actively insecure code. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether the documentation maintains consistent terminology, formatting, and detail level across all sections.

| Score | Criteria |
|-------|----------|
| 9-10  | Uniform terminology, formatting, and detail level throughout. Same term always refers to the same concept. |
| 7-8   | Mostly consistent. Minor terminology variations that do not cause confusion. |
| 5-6   | Some sections are notably more detailed or differently formatted than others. |
| 3-4   | Inconsistent terminology that could confuse readers. Varying quality between sections. |
| 1-2   | No consistency. Same concept called different names. Wildly different formatting between sections. |

## Red Flags (Auto-Deductions)
- Code examples that do not compile or run
- Outdated API references that do not match current version
- Missing examples entirely for documented APIs
- Wrong code samples (e.g., example for function A shown under function B)
- Hardcoded secrets or credentials in examples
- Referencing deprecated methods without noting deprecation
- Dead links to external resources

## Domain-Specific Bonuses
- Includes migration guides for breaking changes
- Provides examples in multiple programming languages
- Includes interactive or runnable code samples (CodePen, Codesandbox links)
- Documents performance characteristics and complexity
- Includes architecture diagrams or visual aids
- Provides changelog integration
- Includes FAQ or common pitfalls section
