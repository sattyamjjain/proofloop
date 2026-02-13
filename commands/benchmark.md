---
name: benchmark
description: "Compare skill scores against ideal benchmarks"
usage: "/benchmark [skill-name]"
---

# /benchmark — Compare Against Ideal Benchmarks

Compare a skill's historical performance against defined benchmark standards.

## Arguments

- `skill-name` (required): The skill to benchmark.

## What to Do

1. Read benchmark standards from `skills/judge/references/benchmark-standards.md`
2. Read historical scores for the specified skill from `skills/judge/scores/`
3. Compute average per dimension across all historical evaluations
4. Compare against benchmark:

```
┌───────────────────────────────────────────────────────────────┐
│  SKILLJUDGE BENCHMARK — {skill-name}                          │
├────────────────┬──────────┬───────────┬───────────────────────┤
│ Dimension      │ Your Avg │ Benchmark │ Delta                 │
├────────────────┼──────────┼───────────┼───────────────────────┤
│ Correctness    │ 8.2      │ 8.5       │ -0.3 (Below)          │
│ Completeness   │ 7.5      │ 8.0       │ -0.5 (Below)          │
│ Adherence      │ 9.0      │ 8.0       │ +1.0 (Above)          │
│ Actionability  │ 8.0      │ 8.0       │  0.0 (On target)      │
│ Efficiency     │ 7.0      │ 7.5       │ -0.5 (Below)          │
│ Safety         │ 9.5      │ 9.0       │ +0.5 (Above)          │
│ Consistency    │ 6.5      │ 7.0       │ -0.5 (Below)          │
├────────────────┼──────────┼───────────┼───────────────────────┤
│ COMPOSITE      │ 8.05     │ 8.14      │ -0.09                 │
└────────────────┴──────────┴───────────┴───────────────────────┘

Strengths: Adherence (+1.0), Safety (+0.5)
Weaknesses: Completeness (-0.5), Efficiency (-0.5), Consistency (-0.5)

Recommendations:
1. Focus on covering all requirements (Completeness gap)
2. Reduce unnecessary tool calls (Efficiency gap)
3. Build more consistent quality (Consistency gap)
```

If no scores exist for the skill, inform the user to run `/judge` first.
