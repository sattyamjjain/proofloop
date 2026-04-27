#!/usr/bin/env python3
"""Verdict scorecard rationale exporter.

Reads an existing scorecard JSON written by ``score.py`` and renders a
PR-comment-friendly Markdown explanation OR a stable-schema JSON
dump. Designed for two consumers:

- humans pasting the output into a pull-request review comment
  (``--format md``, the default)
- CI scripts that need a stable, machine-readable digest of a
  scorecard (``--format json``)

The Markdown format prioritises clarity over completeness — it pulls
the per-dimension table, the adjustments block, the LLM second-opinion
overlay (when present), critical issues, and recommendations into a
shape that lands cleanly inside a GitHub PR comment.

The JSON format is versioned by ``format_version: "explain.v1"`` so
future schema bumps can be detected by consumers.

Stdlib-only. No third-party deps.

Usage:

    python3 skills/judge/scripts/explain.py \\
        --scorecard skills/judge/scores/code-review_2026-04-25.json \\
        [--format md|json] [--out PATH]

Writes to stdout when ``--out`` is omitted.

Source signal: GitHub Discussions #43 — top adopter ask "explain my
scorecard" (https://github.com/sattyamjjain/verdict/discussions/43).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

EXPLAIN_FORMAT_VERSION: str = "explain.v1"
HTML_FORMAT_VERSION: str = "explain.html.v1"

# GitHub PR-comment hard cap is 65,536 chars; the Markdown render must
# stay below that or the auto-comment step in `actions/verdict-comment-pr`
# silently truncates. Default cap leaves headroom for a comment header
# the action prepends. Override with --max-evidence-chars.
DEFAULT_MAX_EVIDENCE_CHARS: int = 4000
TRUNCATION_FOOTER_TEMPLATE: str = (
    "\n\n_Output truncated to {limit} chars to fit GitHub's PR comment "
    "limit. See full report at {url}._\n"
)
TRUNCATION_FOOTER_NO_URL: str = (
    "\n\n_Output truncated to {limit} chars to fit GitHub's PR comment "
    "limit. Re-run with `--max-evidence-chars=0` for the full report._\n"
)

# Canonical dimension order — matches DIMENSIONS in score.py and
# llm_judge.py so the output is stable across all three.
DIMENSIONS: List[str] = [
    "correctness", "completeness", "adherence", "actionability",
    "efficiency", "safety", "consistency",
]


def load_scorecard(path: Path) -> Dict[str, Any]:
    """Load a scorecard JSON file. Raises ``ValueError`` on failure."""
    if not path.is_file():
        raise ValueError(f"scorecard not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read scorecard {path}: {exc}")


def _ordered_dimension_entries(card: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return per-dimension entries in canonical order with the name attached."""
    raw = card.get("dimensions", {}) if isinstance(card, dict) else {}
    if not isinstance(raw, dict):
        return []
    out: List[Dict[str, Any]] = []
    for name in DIMENSIONS:
        entry = raw.get(name)
        if isinstance(entry, dict):
            attached = {"name": name, **entry}
            out.append(attached)
    # Append any extra dims the rubric carries (custom rubrics may
    # extend the canonical seven — preserve order of appearance).
    for name, entry in raw.items():
        if name in DIMENSIONS or not isinstance(entry, dict):
            continue
        out.append({"name": name, **entry})
    return out


def _evidence_block(card: Dict[str, Any]) -> Dict[str, Any]:
    """Compute proxy evidence stats from scorecard fields.

    True evidence spans (the transcript lines that drove each score)
    aren't recorded by the heuristic scorer today; the scorecard only
    persists per-dimension justification strings. ``explain`` surfaces
    what is recorded — counts and matched-pattern names — so PR
    reviewers see the volume of signal behind the score.
    """
    return {
        "transcript_lines": card.get("transcript_lines"),
        "red_flag_count": len(card.get("red_flags", []) or []),
        "bonus_count": len(card.get("bonuses", []) or []),
    }


def render_json(card: Dict[str, Any]) -> str:
    """Render the scorecard as a stable-schema explain.v1 JSON document."""
    dims_out: List[Dict[str, Any]] = []
    for entry in _ordered_dimension_entries(card):
        out_entry: Dict[str, Any] = {
            "name": entry["name"],
            "score": entry.get("score"),
            "weight": entry.get("weight"),
            "weighted": entry.get("weighted"),
            "justification": entry.get("justification", ""),
        }
        if "llm_score" in entry:
            out_entry["llm_score"] = entry["llm_score"]
        if "llm_justification" in entry:
            out_entry["llm_justification"] = entry["llm_justification"]
        dims_out.append(out_entry)

    adjustments_in = card.get("adjustments", {}) or {}
    adjustments_out: Dict[str, Any] = {
        "deduction": adjustments_in.get("deduction", 0.0),
        "bonus": adjustments_in.get("bonus", 0.0),
        "red_flags": list(card.get("red_flags", []) or []),
        "bonuses": list(card.get("bonuses", []) or []),
    }
    # Contamination only appears for rubrics that activated the
    # SWE-bench Pro scanner; surface it when set.
    contamination = adjustments_in.get("contamination")
    if contamination is not None:
        adjustments_out["contamination"] = contamination

    payload: Dict[str, Any] = {
        "format_version": EXPLAIN_FORMAT_VERSION,
        "skill": card.get("skill"),
        "timestamp": card.get("timestamp"),
        "rubric": card.get("rubric_used"),
        "model": card.get("model"),
        "tokenizer_baseline": card.get("tokenizer_baseline"),
        "composite": card.get("composite_score"),
        "raw_composite": card.get("raw_composite"),
        "grade": card.get("grade"),
        "grade_label": card.get("grade_label"),
        "summary": card.get("summary", ""),
        "one_liner": card.get("one_liner", ""),
        "dimensions": dims_out,
        "adjustments": adjustments_out,
        "critical_issues": list(card.get("critical_issues", []) or []),
        "recommendations": list(card.get("recommendations", []) or []),
        "evidence": _evidence_block(card),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _md_dimension_table(entries: List[Dict[str, Any]]) -> str:
    rows = ["| Dimension | Score | Weight | Weighted | Justification |",
            "|-----------|-------|--------|----------|---------------|"]
    for entry in entries:
        score = entry.get("score", "?")
        weight = entry.get("weight", "?")
        weighted = entry.get("weighted", "?")
        justification = (entry.get("justification") or "").replace("|", "\\|").strip()
        if len(justification) > 140:
            justification = justification[:137] + "..."
        rows.append(
            f"| {entry['name']} | {score}/10 | {weight} | {weighted} | "
            f"{justification or '—'} |"
        )
    return "\n".join(rows)


def _md_llm_overlay(entries: List[Dict[str, Any]]) -> str:
    has_llm = any("llm_score" in e for e in entries)
    if not has_llm:
        return ""
    bullets: List[str] = []
    for entry in entries:
        if "llm_score" not in entry:
            continue
        justification = (entry.get("llm_justification") or "").strip()
        bullets.append(
            f"- **{entry['name']}**: {entry['llm_score']}/10 — "
            f"{justification or '_(no justification recorded)_'}"
        )
    return "### LLM second opinion\n\n" + "\n".join(bullets)


def _html_escape(value: Any) -> str:
    """Minimal HTML escaping. Stdlib-only, no html.escape import to keep module light."""
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def render_html_printable(
    card: Dict[str, Any],
    cover_title: Optional[str] = None,
    signer: Optional[str] = None,
) -> str:
    """Render a single-file HTML scorecard with @media print CSS.

    Designed for browser "Print to PDF" workflows — produces a
    publication-ready document without pulling weasyprint or any
    other PDF library (per Issue O6).

    Output structure (one HTML page, A4-friendly):

    1. **Cover page** — title (from *cover_title* or skill+grade),
       composite score, grade, model, timestamp, optional signer.
    2. **Executive summary** — composite + top-3 strengths /
       weaknesses, derived from the dimension scores.
    3. **Per-dimension breakdown** — full table + justifications +
       LLM overlay (when present).
    4. **Adjustments + Critical Issues + Recommendations**.
    5. **Methodology appendix** — rubric name, weights source,
       transcript-line count, evidence stats.
    6. **Signature block** (when *signer* is set).

    The CSS includes ``@media print`` rules that lay out one section
    per page and hide screen-only navigation. Stdlib only.
    """
    skill = card.get("skill", "?")
    grade = card.get("grade", "?")
    grade_label = card.get("grade_label", "")
    composite = card.get("composite_score", "?")
    rubric = card.get("rubric_used", "?")
    model = card.get("model") or "(unknown)"
    timestamp = card.get("timestamp", "?")
    summary = (card.get("summary") or "").strip()
    one_liner = (card.get("one_liner") or "").strip()
    title = cover_title or f"{skill} — Verdict Scorecard"

    entries = _ordered_dimension_entries(card)
    strengths = sorted(entries, key=lambda e: -e.get("score", 0))[:3]
    weaknesses = sorted(entries, key=lambda e: e.get("score", 0))[:3]

    # Build per-dimension rows.
    row_chunks: List[str] = []
    for entry in entries:
        justification = _html_escape(entry.get("justification", ""))
        llm_block = ""
        if "llm_score" in entry:
            llm_block = (
                f'<div class="llm-overlay">'
                f'LLM 2nd opinion: <strong>{entry["llm_score"]}/10</strong> '
                f'<em>{_html_escape(entry.get("llm_justification", ""))}</em>'
                f'</div>'
            )
        row_chunks.append(
            f'<tr>'
            f'<td class="dim">{_html_escape(entry["name"])}</td>'
            f'<td class="num">{entry.get("score", "?")}/10</td>'
            f'<td class="num">{entry.get("weight", "?")}</td>'
            f'<td class="num">{entry.get("weighted", "?")}</td>'
            f'<td class="just">{justification}{llm_block}</td>'
            f'</tr>'
        )

    adjustments = card.get("adjustments", {}) or {}
    red_flags = list(card.get("red_flags", []) or [])
    bonuses = list(card.get("bonuses", []) or [])
    contamination = adjustments.get("contamination", 0.0) or 0.0
    phi_leak = adjustments.get("phi_leak", 0.0) or 0.0
    commerce = adjustments.get("commerce_asymmetry", {}) or {}
    commerce_dock = commerce.get("deduction", 0.0) or 0.0

    adj_items: List[str] = []
    if red_flags:
        adj_items.append(
            f'<li><strong>Red flags</strong> '
            f'(−{adjustments.get("deduction", 0.0)}): '
            f'{_html_escape(", ".join(red_flags))}</li>'
        )
    if bonuses:
        adj_items.append(
            f'<li><strong>Bonuses</strong> '
            f'(+{adjustments.get("bonus", 0.0)}): '
            f'{_html_escape(", ".join(bonuses))}</li>'
        )
    if contamination:
        adj_items.append(
            f'<li><strong>Contamination penalty</strong> (−{contamination}): '
            f'transcript referenced SWE-bench Verified literals</li>'
        )
    if phi_leak:
        adj_items.append(
            f'<li><strong>PHI-leak deduction</strong> (−{phi_leak}): '
            f'unredacted PHI in transcript</li>'
        )
    if commerce_dock:
        adj_items.append(
            f'<li><strong>Commerce asymmetry</strong> (−{commerce_dock}): '
            f'${commerce.get("asymmetry_usd", 0):.2f} USD economic '
            f'asymmetry, unjustified</li>'
        )

    critical = list(card.get("critical_issues", []) or [])
    recs = list(card.get("recommendations", []) or [])
    transcript_lines = card.get("transcript_lines", "?")

    signature_block = ""
    if signer:
        signature_block = (
            f'<section class="signature page-break">'
            f'<h2>Signature</h2>'
            f'<p>Signed by: <strong>{_html_escape(signer)}</strong></p>'
            f'<p>Date: <strong>{_html_escape(timestamp)}</strong></p>'
            f'<p>Verdict format version: '
            f'<code>{HTML_FORMAT_VERSION}</code></p>'
            f'</section>'
        )

    rows = "\n".join(row_chunks)
    adj_html = f'<ul>{"".join(adj_items)}</ul>' if adj_items else "<p>None.</p>"
    critical_html = (
        "<ul>" + "".join(f"<li>{_html_escape(c)}</li>" for c in critical) + "</ul>"
        if critical else "<p>None.</p>"
    )
    recs_html = (
        "<ul>" + "".join(f"<li>{_html_escape(r)}</li>" for r in recs) + "</ul>"
        if recs else "<p>None.</p>"
    )
    strengths_html = "<ul>" + "".join(
        f'<li>{_html_escape(e["name"])} ({e.get("score", "?")}/10)</li>'
        for e in strengths
    ) + "</ul>"
    weaknesses_html = "<ul>" + "".join(
        f'<li>{_html_escape(e["name"])} ({e.get("score", "?")}/10)</li>'
        for e in weaknesses
    ) + "</ul>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_html_escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    color: #111;
    margin: 0;
    padding: 2em;
    line-height: 1.5;
}}
h1 {{ font-size: 2.4em; margin: 0 0 0.4em; }}
h2 {{ font-size: 1.6em; margin: 1.6em 0 0.6em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }}
h3 {{ font-size: 1.2em; margin: 1.2em 0 0.4em; }}
.cover {{ text-align: center; padding-top: 6em; }}
.cover .composite {{ font-size: 5em; font-weight: 700; margin: 0.2em 0; }}
.cover .grade {{ font-size: 2em; color: #555; }}
.cover .meta {{ margin-top: 2em; color: #666; font-size: 0.9em; }}
table {{ width: 100%; border-collapse: collapse; margin: 1em 0; }}
th, td {{ padding: 0.5em 0.6em; border-bottom: 1px solid #eee; vertical-align: top; }}
th {{ background: #f6f6f6; text-align: left; font-weight: 600; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.dim {{ font-weight: 600; text-transform: capitalize; }}
td.just {{ font-size: 0.92em; color: #333; }}
.llm-overlay {{ margin-top: 0.4em; padding-left: 0.6em; border-left: 3px solid #888; font-size: 0.88em; color: #555; }}
.signature {{ margin-top: 4em; border-top: 1px solid #ccc; padding-top: 1em; }}
.appendix {{ font-size: 0.9em; color: #444; }}
.page-break {{ page-break-before: always; }}
@media print {{
    body {{ padding: 1.5cm; }}
    .cover {{ page-break-after: always; padding-top: 6cm; }}
    section {{ page-break-inside: avoid; }}
    h2 {{ page-break-after: avoid; }}
    table {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>
<section class="cover">
    <h1>{_html_escape(title)}</h1>
    <div class="composite">{_html_escape(composite)}/10</div>
    <div class="grade">Grade {_html_escape(grade)}{(" — " + _html_escape(grade_label)) if grade_label else ""}</div>
    {f'<p style="margin-top:2em;font-style:italic;">{_html_escape(one_liner)}</p>' if one_liner else ""}
    <div class="meta">
        Skill: <code>{_html_escape(skill)}</code> · Rubric: <code>{_html_escape(rubric)}</code><br>
        Model: <code>{_html_escape(model)}</code> · Generated: <code>{_html_escape(timestamp)}</code>
    </div>
</section>

<section class="page-break">
    <h2>Executive summary</h2>
    {f"<p>{_html_escape(summary)}</p>" if summary else ""}
    <h3>Top strengths</h3>
    {strengths_html}
    <h3>Areas for improvement</h3>
    {weaknesses_html}
</section>

<section class="page-break">
    <h2>Per-dimension breakdown</h2>
    <table>
        <thead>
            <tr><th>Dimension</th><th>Score</th><th>Weight</th><th>Weighted</th><th>Justification</th></tr>
        </thead>
        <tbody>
{rows}
        </tbody>
    </table>
</section>

<section>
    <h2>Adjustments</h2>
    {adj_html}
    <h2>Critical issues</h2>
    {critical_html}
    <h2>Recommendations</h2>
    {recs_html}
</section>

<section class="page-break appendix">
    <h2>Methodology appendix</h2>
    <p>Verdict scores agent transcripts on seven canonical dimensions
       (correctness, completeness, adherence, actionability,
       efficiency, safety, consistency). Per-rubric weight overrides
       are applied via a sidecar <code>&lt;rubric&gt;.weights.json</code>.</p>
    <ul>
        <li>Rubric: <code>{_html_escape(rubric)}</code></li>
        <li>Weights source: <code>{_html_escape(card.get("weights_source", "config"))}</code></li>
        <li>Tokenizer baseline: <code>{_html_escape(card.get("tokenizer_baseline", 1.0))}</code></li>
        <li>Transcript lines analysed: {_html_escape(transcript_lines)}</li>
        <li>Verdict format version: <code>{HTML_FORMAT_VERSION}</code></li>
    </ul>
</section>

{signature_block}

</body>
</html>
"""


def truncate_markdown(
    rendered: str,
    max_chars: int = DEFAULT_MAX_EVIDENCE_CHARS,
    scorecard_url: Optional[str] = None,
) -> str:
    """Cap *rendered* at *max_chars* and append a truncation footer.

    *max_chars* of ``0`` disables truncation entirely (caller wants
    the full report — useful when piping to a file rather than a PR
    comment). The footer points at *scorecard_url* when provided, or
    instructs the user to re-run with ``--max-evidence-chars=0``.

    The cap counts characters of the rendered output, not Markdown
    "tokens". GitHub's actual limit is 65,536 chars, so the default
    of 4,000 leaves substantial headroom for the wrapping action's
    own header / collapsible-section markup.
    """
    if max_chars == 0 or len(rendered) <= max_chars:
        return rendered
    if scorecard_url:
        footer = TRUNCATION_FOOTER_TEMPLATE.format(
            limit=max_chars, url=scorecard_url,
        )
    else:
        footer = TRUNCATION_FOOTER_NO_URL.format(limit=max_chars)
    body_budget = max(0, max_chars - len(footer))
    return rendered[:body_budget].rstrip() + footer


def render_markdown(card: Dict[str, Any]) -> str:
    """Render a PR-comment-friendly Markdown explanation."""
    skill = card.get("skill", "?")
    grade = card.get("grade", "?")
    grade_label = card.get("grade_label", "")
    composite = card.get("composite_score", "?")
    rubric = card.get("rubric_used", "?")
    model = card.get("model") or "_unknown_"
    timestamp = card.get("timestamp", "?")
    summary = card.get("summary", "").strip()

    header = (
        f"# Verdict Scorecard — `{skill}`\n\n"
        f"**Composite:** {composite}/10 — **Grade:** {grade}"
        f"{(' (' + grade_label + ')') if grade_label else ''}  \n"
        f"**Rubric:** `{rubric}` · **Model:** `{model}` · "
        f"**Timestamp:** `{timestamp}`"
    )
    one_liner = card.get("one_liner")
    if one_liner:
        header += f"\n\n> {one_liner.strip()}"
    if summary:
        header += f"\n\n_{summary}_"

    entries = _ordered_dimension_entries(card)
    sections: List[str] = [header, "## Per-dimension breakdown",
                           _md_dimension_table(entries)]

    overlay = _md_llm_overlay(entries)
    if overlay:
        sections.append(overlay)

    adjustments = card.get("adjustments", {}) or {}
    red_flags = list(card.get("red_flags", []) or [])
    bonuses = list(card.get("bonuses", []) or [])
    contamination = adjustments.get("contamination", 0.0) or 0.0
    if red_flags or bonuses or contamination:
        adj_lines: List[str] = ["## Adjustments", ""]
        if red_flags:
            adj_lines.append(
                f"- **Red flags** (−{adjustments.get('deduction', 0.0)}): "
                f"{', '.join(red_flags)}"
            )
        if bonuses:
            adj_lines.append(
                f"- **Bonuses** (+{adjustments.get('bonus', 0.0)}): "
                f"{', '.join(bonuses)}"
            )
        if contamination:
            adj_lines.append(
                f"- **Contamination penalty** (−{contamination}): "
                "transcript referenced SWE-bench Verified literals"
            )
        sections.append("\n".join(adj_lines))

    critical = list(card.get("critical_issues", []) or [])
    if critical:
        sections.append(
            "## Critical issues\n\n" + "\n".join(f"- {c}" for c in critical)
        )

    recs = list(card.get("recommendations", []) or [])
    if recs:
        sections.append(
            "## Recommendations\n\n" + "\n".join(f"- {r}" for r in recs)
        )

    evidence = _evidence_block(card)
    sections.append(
        "## Evidence\n\n"
        f"- {evidence['transcript_lines']} transcript lines analysed\n"
        f"- {evidence['red_flag_count']} red-flag patterns matched\n"
        f"- {evidence['bonus_count']} bonus signals matched"
    )

    return "\n\n".join(sections) + "\n"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="verdict-explain",
        description="Render a Verdict scorecard JSON as Markdown or JSON.",
    )
    parser.add_argument(
        "--scorecard", required=True,
        help="Path to a scorecard JSON file written by score.py.",
    )
    parser.add_argument(
        "--format", choices=("md", "json", "html-printable"), default="md",
        help=(
            "Output format. md = PR-comment-friendly Markdown (default), "
            "json = stable-schema explain.v1, html-printable = single-file "
            "HTML with @media print CSS (use browser 'Print to PDF' to "
            "generate a PDF; no weasyprint dep)."
        ),
    )
    parser.add_argument(
        "--cover",
        help="Cover-page title for --format html-printable. Defaults to "
             "'<skill> — Verdict Scorecard'.",
    )
    parser.add_argument(
        "--signer",
        help="Signature-block name for --format html-printable. Adds a "
             "final 'Signature' page when present.",
    )
    parser.add_argument(
        "--out",
        help="Write output to PATH. Default: stdout.",
    )
    parser.add_argument(
        "--max-evidence-chars", type=int, default=DEFAULT_MAX_EVIDENCE_CHARS,
        help=(
            "Cap Markdown output length to fit GitHub's 65 KB PR comment "
            f"limit (default: {DEFAULT_MAX_EVIDENCE_CHARS}). Set to 0 to "
            "disable truncation. Ignored for --format json."
        ),
    )
    parser.add_argument(
        "--scorecard-url",
        help=(
            "URL of the full scorecard. When --max-evidence-chars truncates "
            "the Markdown body, the truncation footer points readers here."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        card = load_scorecard(Path(args.scorecard))
    except ValueError as exc:
        print(f"verdict-explain: {exc}", file=sys.stderr)
        return 2
    if args.format == "md":
        rendered = render_markdown(card)
        rendered = truncate_markdown(
            rendered, args.max_evidence_chars, args.scorecard_url,
        )
    elif args.format == "html-printable":
        rendered = render_html_printable(card, args.cover, args.signer)
    else:
        rendered = render_json(card)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
