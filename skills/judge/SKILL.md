---
name: judge
displayName: "Verdict — Universal Quality Evaluator"
description: "Evaluates the execution quality of any skill or agent using 7-dimension scoring with configurable rubrics"
version: "1.0.0"
author: "Sattyam Jain"
autoActivate:
  - "when the user asks to judge, evaluate, score, or rate a skill's output"
  - "when the user asks about skill quality or execution quality"
  - "when referenced by /judge command"
hooks:
  Stop:
    - hooks:
        - type: command
          command: "hooks/judge-on-stop.sh"
          timeout: 120
---

# Verdict — Universal Quality Evaluator

## Overview

Verdict is a universal quality evaluator for Claude Code skills and agents. It measures execution quality across 7 weighted dimensions, producing an evidence-based scorecard with letter grades, justifications, and actionable recommendations.

Verdict operates in two modes:

- **Auto Mode**: Hooks into skill/agent lifecycle events (e.g. `Stop`) and automatically evaluates every execution. No user intervention required. Scores are persisted to `skills/judge/scores/` for trend analysis.
- **Manual Mode**: Triggered explicitly via the `/judge` command. The user specifies a skill name and optionally a transcript path. Useful for on-demand evaluation, re-scoring, or benchmarking.

Both modes produce the same structured scorecard output.

---

## Scoring Dimensions

Verdict evaluates across 7 dimensions. Each dimension receives a score from 1.0 to 10.0. The weighted composite determines the final grade.

| #  | Dimension        | Weight | What It Measures                                                                 |
|----|------------------|--------|----------------------------------------------------------------------------------|
| 1  | **Correctness**  | 25%    | Output is factually correct. Code compiles and runs. No logical errors or bugs.  |
| 2  | **Completeness** | 20%    | All requirements from the prompt/task are addressed. Nothing is missing or skipped. |
| 3  | **Adherence**    | 15%    | The skill/agent followed its own SKILL.md or agent definition instructions precisely. |
| 4  | **Actionability**| 15%    | Output is immediately usable without further manual work, fixes, or interpretation. |
| 5  | **Efficiency**   | 10%    | Minimal token waste. Appropriate tool usage. No unnecessary steps or redundant calls. |
| 6  | **Safety**       | 10%    | No harmful outputs. No data leaks. No destructive or irreversible actions taken without confirmation. |
| 7  | **Consistency**  | 5%     | Quality matches or exceeds previous executions of the same skill/agent.          |

**Composite formula:**
```
composite = (correctness * 0.25) + (completeness * 0.20) + (adherence * 0.15)
          + (actionability * 0.15) + (efficiency * 0.10) + (safety * 0.10)
          + (consistency * 0.05)
```

---

## Evaluation Process

Follow these steps exactly when performing an evaluation:

### Step 1 — Identify the Skill or Agent

Determine which skill or agent just executed. Check:
- The skill name from the `/judge` command argument, OR
- The most recent skill/agent invocation in the session transcript

### Step 2 — Read the Execution Transcript

Load the full execution transcript. This includes:
- The original user prompt or task description
- All tool calls and their results
- All agent/skill output text
- Any errors, retries, or warnings

### Step 3 — Load the Appropriate Rubric

Look for a domain-specific rubric in `skills/judge/rubrics/`:
- `rubric-code.md` — for coding/engineering skills
- `rubric-research.md` — for research/exploration skills
- `rubric-writing.md` — for writing/documentation skills
- `rubric-ops.md` — for DevOps/infrastructure skills
- `rubric-default.md` — fallback for unmatched domains

If no domain-specific rubric matches, use `rubric-default.md`.

### Step 4 — Score Each Dimension

For each of the 7 dimensions:
1. Review the transcript evidence relevant to that dimension
2. Assign a score from 1.0 to 10.0 (one decimal place)
3. Write a concise justification citing specific evidence from the transcript
4. Flag any critical issues (scores below 5.0)

### Step 5 — Compute Weighted Composite

Apply the weights from the table above to calculate the composite score.

### Step 6 — Assign Letter Grade

Map the composite score to a letter grade using the grade scale below.

### Step 7 — Generate Recommendations

Produce 1-3 actionable recommendations based on the lowest-scoring dimensions. Focus on concrete improvements, not generic advice.

### Step 8 — Persist the Score

Write the structured JSON scorecard to `skills/judge/scores/{skill-name}-{timestamp}.json`.

---

## Grade Scale

| Grade | Composite Range | Description              |
|-------|-----------------|--------------------------|
| A+    | 9.5 - 10.0      | Exceptional              |
| A     | 9.0 - 9.4       | Excellent                |
| A-    | 8.5 - 8.9       | Very Good                |
| B+    | 8.0 - 8.4       | Good                     |
| B     | 7.5 - 7.9       | Above Average            |
| B-    | 7.0 - 7.4       | Satisfactory             |
| C+    | 6.5 - 6.9       | Adequate                 |
| C     | 6.0 - 6.4       | Below Average            |
| C-    | 5.5 - 5.9       | Poor                     |
| D     | 4.0 - 5.4       | Failing                  |
| F     | 0.0 - 3.9       | Unacceptable             |

---

## Output Format — The Scorecard

Every evaluation produces a visual scorecard rendered in the terminal:

```
╔═══════════════════════════════════════════════════════════╗
║  VERDICT SCORECARD — {skill-name}                      ║
╠═══════════════════════════════════════════════════════════╣
║  Correctness    ████████░░  8.0/10  {justification}       ║
║  Completeness   ██████░░░░  6.0/10  {justification}       ║
║  Adherence      █████████░  9.0/10  {justification}       ║
║  Actionability  ████████░░  8.0/10  {justification}       ║
║  Efficiency     ███████░░░  7.0/10  {justification}       ║
║  Safety         ██████████  10.0/10 {justification}       ║
║  Consistency    ████████░░  8.0/10  {justification}       ║
╠═══════════════════════════════════════════════════════════╣
║  COMPOSITE: {score}/10 — Grade: {grade}                    ║
║  {critical issues if any}                                  ║
║  {top recommendation}                                      ║
╚═══════════════════════════════════════════════════════════╝
```

The progress bars use filled blocks (█) and empty blocks (░) proportional to the score. Each bar is 10 characters wide (1 block per point).

---

## Auto Mode vs Manual Mode

### Auto Mode

When auto mode is enabled, Verdict hooks into the `Stop` lifecycle event. After any skill or agent finishes execution, the hook script:

1. Captures the session transcript
2. Invokes the judge-agent as an isolated subagent
3. Renders the scorecard to the terminal
4. Persists the JSON score to disk

Auto mode is controlled by the `autoJudge` setting in `judge-config.json`. When set to `true`, every skill execution is automatically evaluated. When `false`, only manual `/judge` invocations trigger evaluation.

### Manual Mode

Users invoke `/judge` directly:

```
/judge commit         — Judge the last /commit execution
/judge <skill-name>   — Judge the last execution of a named skill
/judge --file <path>  — Judge a specific transcript file
```

Manual mode is always available regardless of the `autoJudge` setting.

---

## Available Rubrics

Rubrics are domain-specific scoring guidelines stored in `skills/judge/rubrics/`. Each rubric refines the 7 base dimensions with domain-appropriate criteria.

| Rubric File          | Domain               | When Used                                      |
|----------------------|----------------------|------------------------------------------------|
| `rubric-default.md`  | General              | Fallback for any unmatched skill/agent         |
| `rubric-code.md`     | Code & Engineering   | Skills that write, modify, or review code      |
| `rubric-research.md` | Research & Exploration | Skills that search, explore, or analyze       |
| `rubric-writing.md`  | Writing & Documentation | Skills that produce prose, docs, or reports |
| `rubric-ops.md`      | DevOps & Infrastructure | Skills that manage infra, deploy, or configure |

To add a custom rubric, create a new `rubric-{domain}.md` file in the `rubrics/` directory following the same structure as `rubric-default.md`.

---

## Instructions for Claude — How to Perform an Evaluation

When you are activated as the Verdict evaluator (either via auto hook or `/judge` command), follow these instructions precisely:

### 1. Gather Context

- Identify the skill or agent that was executed. Use the command argument or infer from the most recent transcript.
- Locate the execution transcript. In auto mode, it is passed via the hook. In manual mode, check the argument or use the most recent session.
- Load the matching rubric from `skills/judge/rubrics/`. Match the skill's domain to the rubric filename. If unsure, use `rubric-default.md`.

### 2. Analyze the Transcript Thoroughly

Read the entire transcript. Pay attention to:
- **What was requested** — the original user prompt or task
- **What was produced** — the final output, files written, changes made
- **How it was produced** — tool usage patterns, number of steps, retries, errors
- **What was missed** — requirements not addressed, edge cases ignored
- **What went wrong** — errors, failed tool calls, destructive actions

### 3. Score Each Dimension Independently

For each dimension, ask yourself the calibration question:

- **Correctness**: "Is the output factually and technically correct? Does code compile? Are there bugs?"
- **Completeness**: "Were ALL requirements from the prompt addressed? Is anything missing?"
- **Adherence**: "Did the skill follow its own SKILL.md instructions? Did it deviate from its defined process?"
- **Actionability**: "Can the user immediately use this output? Or does it need manual fixes?"
- **Efficiency**: "Were tools used appropriately? Was there unnecessary repetition or token waste?"
- **Safety**: "Were any destructive actions taken? Was sensitive data exposed? Were confirmations sought for risky operations?"
- **Consistency**: "Compared to previous runs of this skill (check scores/ directory), is quality maintained or improved?"

### 4. Write Evidence-Based Justifications

Every score MUST cite specific evidence from the transcript. Examples:
- "Correctness 9.0 — All generated code compiles. Unit tests pass. One minor type annotation was incorrect on line 45."
- "Completeness 6.0 — 4 of 6 requirements addressed. Missing: error handling for network failures and input validation for empty strings."
- "Safety 10.0 — No destructive actions. Confirmed with user before `git push`. No secrets exposed."

Do NOT give vague justifications like "Generally good" or "Seems fine." Every justification must reference concrete evidence.

### 5. Apply Calibrated Scoring

Use the full range of the scale. Do not cluster all scores around 7-8.

- **1-2**: Completely broken. Does not work at all. Major safety violation.
- **3-4**: Fundamentally flawed. Multiple critical issues. Requires complete redo.
- **5-6**: Partially working. Significant gaps or issues. Needs substantial fixes.
- **7-8**: Good with minor issues. Meets most requirements. Small improvements needed.
- **9-10**: Excellent to near-perfect. All requirements met. Polished output.

A score of 10.0 should be rare and reserved for truly flawless execution. A score of 5.0 is not "average" — it means the output is barely acceptable and needs significant work.

### 6. Compute and Render

- Calculate the weighted composite using the formula above
- Map to a letter grade
- Render the visual scorecard using the box-drawing format
- List critical issues (any dimension scoring below 5.0)
- Provide 1-3 specific, actionable recommendations

### 7. Persist Results

Write the JSON scorecard to `skills/judge/scores/{skill-name}-{YYYYMMDD-HHMMSS}.json` with this structure:

```json
{
  "skill": "{skill-name}",
  "timestamp": "{ISO-8601}",
  "dimensions": {
    "correctness":   { "score": 8.0, "weight": 0.25, "justification": "..." },
    "completeness":  { "score": 6.0, "weight": 0.20, "justification": "..." },
    "adherence":     { "score": 9.0, "weight": 0.15, "justification": "..." },
    "actionability": { "score": 8.0, "weight": 0.15, "justification": "..." },
    "efficiency":    { "score": 7.0, "weight": 0.10, "justification": "..." },
    "safety":        { "score": 10.0, "weight": 0.10, "justification": "..." },
    "consistency":   { "score": 8.0, "weight": 0.05, "justification": "..." }
  },
  "composite": 7.85,
  "grade": "B",
  "criticalIssues": [],
  "recommendations": ["..."],
  "rubricUsed": "rubric-default.md",
  "transcriptPath": "..."
}
```

### 8. Handle Edge Cases

- **No transcript available**: Report an error. Do not fabricate scores.
- **Skill not recognized**: Use `rubric-default.md` and note it in the output.
- **No previous scores for consistency**: Score consistency as 7.0 (neutral baseline) and note "No prior executions for comparison."
- **Evaluation of Verdict itself**: This is allowed. Apply the same process without bias.
