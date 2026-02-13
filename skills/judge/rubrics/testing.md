# Testing Evaluation Rubric

## Overview
This rubric evaluates the quality of test generation skill outputs. Use it when the skill under evaluation writes unit tests, integration tests, end-to-end tests, or test plans. Good test output catches real bugs, covers edge cases, and produces reliable, non-flaky results.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether tests actually test what they claim to test -- assertions are meaningful, mocks are accurate, and test logic is sound.

| Score | Criteria |
|-------|----------|
| 9-10  | Every test validates exactly what it claims. Assertions are precise and meaningful. Mocks accurately represent real dependencies. No tautological tests. |
| 7-8   | Tests are well-targeted. Assertions are meaningful. Minor mock inaccuracies that do not affect test validity. |
| 5-6   | Most tests are valid but some assertions are too broad or mocks are oversimplified, reducing confidence. |
| 3-4   | Several tests have incorrect assertions, wrong expectations, or mocks that do not reflect reality. |
| 1-2   | Tests are fundamentally broken. Assertions test the wrong thing. Tests that pass regardless of code correctness. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether edge cases, error paths, boundary conditions, and all critical code paths are covered.

| Score | Criteria |
|-------|----------|
| 9-10  | Happy path, error paths, edge cases, and boundary conditions all covered. Null/empty inputs, overflow, concurrency, and permission scenarios tested. |
| 7-8   | Happy path and major error paths covered. Most edge cases addressed. A few boundary conditions may be missing. |
| 5-6   | Happy path well-covered. Some error paths tested. Edge cases and boundary conditions are sparse. |
| 3-4   | Only happy path tested. Error handling largely untested. No edge cases or boundary conditions. |
| 1-2   | Minimal test coverage. Only the most basic scenario tested, if that. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether tests follow the specified testing framework conventions, naming patterns, and project structure.

| Score | Criteria |
|-------|----------|
| 9-10  | Tests follow the framework idioms perfectly (e.g., proper use of describe/it, setUp/tearDown). Consistent naming. Proper test organization. |
| 7-8   | Follows framework conventions with minor deviations. Naming is mostly consistent. |
| 5-6   | Generally follows conventions but some tests are structured unconventionally or named inconsistently. |
| 3-4   | Significant deviation from framework conventions. Inconsistent structure. |
| 1-2   | Tests do not follow any recognizable testing conventions for the specified framework. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether tests can be run immediately without modification and whether failure messages clearly indicate what went wrong.

| Score | Criteria |
|-------|----------|
| 9-10  | All tests run immediately. Clear test descriptions. Failure messages pinpoint the exact issue. Setup/teardown is self-contained. |
| 7-8   | Tests run with minimal setup. Most failure messages are descriptive. |
| 5-6   | Tests run after some configuration. Some failure messages are generic and require investigation. |
| 3-4   | Tests require significant setup to run. Failure messages are unhelpful. Missing fixtures or test data. |
| 1-2   | Tests do not run. Missing dependencies, broken imports, or incomplete test fixtures. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether the test suite avoids redundant tests, runs efficiently, and provides maximum coverage per test.

| Score | Criteria |
|-------|----------|
| 9-10  | No redundant tests. Each test covers a unique scenario. Test suite runs quickly. Shared fixtures used appropriately. |
| 7-8   | Minor redundancy between tests. Suite runs in reasonable time. |
| 5-6   | Some redundant tests. A few tests cover the same scenario differently. Could be more efficient. |
| 3-4   | Significant redundancy. Many tests are variations of the same case. Slow test execution due to unnecessary setup. |
| 1-2   | Extremely redundant. Most tests duplicate each other. Suite is bloated with no additional coverage benefit. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether tests are isolated, do not affect production data, and clean up after themselves.

| Score | Criteria |
|-------|----------|
| 9-10  | Tests are fully isolated. No shared mutable state. No production side effects. Proper cleanup in teardown. Test data is self-contained. |
| 7-8   | Tests are mostly isolated. Minor shared state that does not cause flakiness. |
| 5-6   | Some tests share state or depend on execution order. Minor risk of side effects. |
| 3-4   | Tests modify shared resources. Risk of affecting production data or other tests. Missing cleanup. |
| 1-2   | Tests directly interact with production systems. No isolation. Tests could cause data loss or corruption. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether tests maintain consistent structure, naming, assertion style, and quality level throughout.

| Score | Criteria |
|-------|----------|
| 9-10  | All tests follow the same structural pattern. Consistent assertion library usage. Uniform naming convention. |
| 7-8   | Mostly consistent. Minor variations in style between test files. |
| 5-6   | Some inconsistency in test structure or assertion style between different modules. |
| 3-4   | Tests for different modules look like they were written by different people with different conventions. |
| 1-2   | No consistency. Mix of assertion libraries, naming styles, and structural patterns. |

## Red Flags (Auto-Deductions)
- Tests that always pass regardless of implementation (tautological tests)
- Tests with no assertions
- Flaky tests that depend on timing, network, or execution order
- Tests that modify production databases or external services
- Mocks that do not match the interface of the real dependency
- Tests that test framework behavior rather than application logic
- Hardcoded sleep/delay as synchronization mechanism

## Domain-Specific Bonuses
- Uses property-based testing where appropriate
- Includes parameterized tests for input variation coverage
- Tests demonstrate clear Arrange-Act-Assert structure
- Includes test coverage metrics or identifies coverage gaps
- Tests serve as living documentation of expected behavior
- Uses snapshot testing appropriately for complex outputs
- Includes performance/benchmark tests for critical paths
