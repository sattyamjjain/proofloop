# Benchmark Standards

## Overview
This document defines what ideal execution looks like across common skill domains. It establishes concrete benchmarks for "perfect" scores and minimum acceptable thresholds, providing calibration guidance for consistent evaluations.

## What a Perfect 10 Looks Like

### Code Review (Perfect 10)
- **Correctness:** Every flagged issue is a genuine, confirmed bug or anti-pattern. Zero false positives. Severity ratings match industry-standard definitions (critical, high, medium, low).
- **Completeness:** Every changed file reviewed. All issue categories examined: logic bugs, security, performance, style, error handling, concurrency. Cross-file interactions analyzed.
- **Adherence:** Follows the exact review format requested. Uses correct severity labels. Stays strictly within the scope of the changeset.
- **Actionability:** Every finding includes a specific code fix or concrete suggestion. Complex fixes include before/after code snippets.
- **Efficiency:** Findings prioritized by impact. No bikeshedding on trivial style issues while real bugs exist. Executive summary highlights top 3 risks.
- **Safety:** Identifies all OWASP Top 10 vulnerabilities present. Auth/authz issues flagged. Injection vectors caught.
- **Consistency:** Same severity standard applied to first file and last file. Similar issues get identical treatment.

### Security Scan (Perfect 10)
- **Correctness:** 100% true positive rate for findings. CVSS scores independently verifiable. No false positives.
- **Completeness:** Full OWASP Top 10 coverage confirmed. Dependencies scanned with CVE lookups. Configuration, secrets, auth, crypto, and logging all examined.
- **Adherence:** Findings linked to CWE IDs. CVSS v3.1 scoring with attack vector breakdown. Report follows a structured executive summary, findings, remediation format.
- **Actionability:** Each finding has a step-by-step remediation plan with code examples. Effort estimates (quick fix vs. architectural change) provided. Prioritized remediation roadmap included.
- **Efficiency:** Critical findings prominently featured. Informational notes clearly separated. Executive summary fits on one page.
- **Safety:** No working exploit code included. Sensitive data (keys, tokens, internal URLs) redacted. Follows responsible disclosure principles.
- **Consistency:** Uniform CVSS methodology. Same vulnerability type rated identically regardless of where it appears.

### Frontend Design (Perfect 10)
- **Correctness:** Valid HTML5 (zero W3C validation errors). Clean CSS (no parser errors). JS runs without console errors. Renders identically across Chrome, Firefox, Safari, Edge.
- **Completeness:** Fully responsive at 320px, 768px, 1024px, 1440px, and 1920px+. WCAG 2.1 AA compliant. All states covered: default, hover, focus, active, disabled, loading, error, empty, success.
- **Adherence:** Pixel-perfect match to design spec. Correct framework usage (React, Vue, etc.). Proper component composition.
- **Actionability:** Runs immediately with `npm install && npm start`. No placeholder values. All assets included or referenced. README with setup instructions.
- **Efficiency:** Lighthouse performance score 90+. No unused CSS. No render-blocking resources. Images optimized or properly referenced.
- **Safety:** No XSS vectors. All user input sanitized. CSP headers compatible. No inline scripts with dynamic content.
- **Consistency:** Uniform component API patterns. Consistent naming (BEM, CSS modules, etc.). Same spacing and color system throughout.

### Documentation (Perfect 10)
- **Correctness:** Every function signature matches the actual code. All code examples compile and run successfully. Parameter descriptions match actual behavior.
- **Completeness:** 100% of public API surface documented. Every parameter, return type, exception, and side effect described. Includes quickstart, API reference, guides, and troubleshooting.
- **Adherence:** Follows the specified documentation standard (JSDoc, Sphinx, OpenAPI, etc.) perfectly. Consistent structure across all entries.
- **Actionability:** Every API has a working code example. Examples cover common use cases. Copy-paste into a REPL and they work. Installation to first API call takes under 5 minutes following the docs.
- **Efficiency:** Well-organized with searchable structure. No redundant content. Cross-references instead of duplication. Table of contents and index.
- **Safety:** No hardcoded credentials in examples. Security-sensitive APIs have prominent warnings. Deprecated methods clearly marked.
- **Consistency:** Same terminology throughout. Uniform detail level. Every entry follows the same template.

### Testing (Perfect 10)
- **Correctness:** Every test validates exactly what its name claims. Assertions are precise (not just "result is not null"). Mocks faithfully represent real interfaces.
- **Completeness:** Happy path, error paths, edge cases, boundary conditions, null/empty inputs, concurrent access, and permission scenarios all covered. Branch coverage exceeds 90%.
- **Adherence:** Follows framework idioms perfectly. Consistent test naming (given/when/then or similar). Proper use of setup/teardown.
- **Actionability:** All tests pass on first run. Clear failure messages that pinpoint the issue. Self-contained test data (no external dependencies).
- **Efficiency:** Zero redundant tests. Each test covers a unique scenario. Suite completes in under 30 seconds for unit tests.
- **Safety:** Complete test isolation. No shared mutable state. No production side effects. Deterministic (no flakiness).
- **Consistency:** Uniform test structure. Same assertion library throughout. Consistent naming convention.

### Data Analysis (Perfect 10)
- **Correctness:** All calculations independently verifiable. Appropriate statistical methods for data type and distribution. Confidence intervals and p-values correctly computed.
- **Completeness:** All relevant data segments examined. All requested analyses performed. Sample sizes, confidence levels, and limitations clearly stated. Missing data handled and documented.
- **Adherence:** Follows requested methodology. Output format matches spec. Uses specified tools and visualization libraries.
- **Actionability:** Clear, prioritized recommendations with supporting evidence. Each recommendation specifies who should do what by when. ROI estimates where applicable.
- **Efficiency:** Focused on key findings. No vanity metrics. Executive summary captures the essential story in 3-5 bullets.
- **Safety:** Honest data presentation. No misleading axes. Cherry-picking explicitly avoided. Limitations prominently stated.
- **Consistency:** Same statistical methodology throughout. Uniform chart styling. Consistent terminology.

### Content Writing (Perfect 10)
- **Correctness:** All facts independently verifiable. Statistics properly sourced. Technical claims are precise and accurate.
- **Completeness:** Topic covered comprehensively for the target audience. All requested aspects addressed. Introduction, body, conclusion, and CTA all present and well-developed.
- **Adherence:** Matches requested tone, style, and format exactly. Within word count range. Brand voice consistent throughout.
- **Actionability:** Reader can implement advice immediately. Steps are specific and concrete. Resources and next steps are provided.
- **Efficiency:** Tight prose. No filler. Every paragraph advances the narrative. Easy to scan with clear headings.
- **Safety:** No harmful advice. Appropriate disclaimers. Inclusive language. No legal risks.
- **Consistency:** Uniform voice and quality. Smooth transitions. Same terminology throughout.

## Minimum Acceptable Scores

The following are the minimum composite scores required for output to be considered acceptable (i.e., usable without major rework) in each domain:

| Domain           | Minimum Score | Minimum Grade | Rationale |
|------------------|---------------|---------------|-----------|
| Code Review      | 7.0           | B-            | Below this, false positives and missed bugs make the review unreliable. |
| Security Scan    | 7.5           | B             | Security reports must be trustworthy. False positives or missed critical vulns are costly. |
| Frontend Design  | 6.5           | C+            | UI code below this typically has broken layouts or missing responsiveness. |
| Documentation    | 6.5           | C+            | Docs below this have wrong examples or missing APIs that mislead developers. |
| Testing          | 7.0           | B-            | Tests below this may pass trivially or miss important scenarios, giving false confidence. |
| Data Analysis    | 7.0           | B-            | Analysis below this may have wrong calculations or misleading presentations. |
| Content Writing  | 6.0           | C             | Content below this is typically too generic or inaccurate to publish. |
| General (Default)| 6.0           | C             | Universal minimum for any unspecified domain. |

### Interpretation
- **At or above minimum:** Output is usable, possibly with minor corrections.
- **Below minimum by up to 1.0 point:** Output needs significant rework but has salvageable parts.
- **Below minimum by more than 1.0 point:** Output should be rejected and regenerated.

## Industry Comparison Notes

These benchmarks are calibrated against the following industry standards and expectations:

### Code Quality
- Professional code review coverage: 100% of changed files, finding density of 1-3 significant issues per 100 lines of changed code is typical for mature codebases.
- Industry false positive rate for automated code review tools: 10-30%. A score of 7+ expects under 10%.

### Security
- OWASP Top 10 coverage is the industry minimum for web application security assessments.
- NIST Cybersecurity Framework and SOC 2 Type II are reference compliance frameworks.
- Industry false positive rate for SAST tools: 20-50%. A score of 7+ expects under 15%.

### Frontend
- WCAG 2.1 AA compliance is the legal minimum in many jurisdictions (ADA, EAA).
- Lighthouse performance score of 90+ is considered "good" by Google's Web Vitals standards.
- Core Web Vitals (LCP < 2.5s, INP < 200ms, CLS < 0.1) are the performance benchmarks.

### Documentation
- API documentation coverage of 100% of public surface area is the expectation for production-ready libraries.
- The gold standard (e.g., Stripe, Twilio) includes interactive examples, multiple language support, and copy-paste ready code.

### Testing
- Industry standard for production code: 80%+ line coverage, 70%+ branch coverage.
- Test execution time: unit tests under 30 seconds, integration tests under 5 minutes.
- Zero flaky tests is the expectation for CI/CD reliability.

### Data Analysis
- Statistical significance at p < 0.05 is the conventional threshold.
- Reproducibility of analysis is a core requirement in data science.
- Visualization standards reference: Tufte's principles of data visualization, avoiding chartjunk.

### Content
- Professional editorial standards: fact-checked, proofread, structured for the target audience.
- SEO benchmarks (when applicable): targeting featured snippet format, E-E-A-T compliance.
- Readability: Flesch-Kincaid grade level appropriate for target audience.
