#!/usr/bin/env python3
"""Generate a single-file HTML dashboard from scores/ JSON files.

Produces a self-contained HTML file (no server, no build step, no
framework) with three views:
  1. Per-skill radar chart of latest dimension scores
  2. Weekly composite trend line per skill
  3. Critical-issue feed

The browser side uses vanilla JavaScript and SVG. No third-party
dependencies on either side. Stdlib-only Python generator.

Usage:
    python3 skills/judge/scripts/studio.py \\
      --scores-dir skills/judge/scores \\
      --output verdict-studio.html
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>Proofloop Studio</title>
<style>
  :root {{
    --bg: #0b0d12; --panel: #141820; --ink: #e9edf5;
    --muted: #8a93a6; --accent: #7fd4ff; --danger: #ff6b6b;
    --warn: #ffd166; --good: #51cf66;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 32px; background: var(--bg); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", system-ui, sans-serif;
    line-height: 1.5;
  }}
  h1 {{ margin: 0 0 8px; font-size: 22px; letter-spacing: 0.5px; }}
  .tagline {{ color: var(--muted); margin-bottom: 32px; font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 20px; }}
  .panel {{
    background: var(--panel); border-radius: 12px; padding: 20px;
    border: 1px solid rgba(255,255,255,0.05);
  }}
  .panel h2 {{ margin: 0 0 12px; font-size: 15px; color: var(--accent); }}
  .skill {{ font-size: 14px; color: var(--muted); margin-bottom: 8px; }}
  .grade {{ font-size: 28px; font-weight: 600; margin-right: 8px; }}
  .grade.A {{ color: var(--good); }} .grade.B {{ color: var(--accent); }}
  .grade.C {{ color: var(--warn); }} .grade.D, .grade.F {{ color: var(--danger); }}
  svg {{ background: transparent; }}
  .axis {{ stroke: rgba(255,255,255,0.08); }}
  .ring {{ fill: none; stroke: rgba(255,255,255,0.05); }}
  .trend-path {{ fill: none; stroke: var(--accent); stroke-width: 2; }}
  .trend-dot {{ fill: var(--accent); }}
  .label {{ fill: var(--muted); font-size: 10px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }}
  td, th {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
  th {{ color: var(--muted); font-weight: 500; }}
  .issue {{ color: var(--danger); font-size: 12px; }}
  .pill {{
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    background: rgba(127,212,255,0.1); color: var(--accent); font-size: 11px;
  }}
</style>
</head>
<body>
<h1>Proofloop Studio</h1>
<p class=\"tagline\">Auto-generated from {score_count} scorecard(s) across {skill_count} skill(s). Generated {generated_at}.</p>
<div class=\"grid\">{panels}</div>
<script>
  // No-op. The HTML is static; this is a placeholder hook for future
  // interactivity (filtering, date-range scrubber, rubric overlay).
  console.log(\"Proofloop Studio loaded with {score_count} scorecards.\");
</script>
</body>
</html>
"""


def _load_scores(scores_dir: Path) -> List[Dict[str, Any]]:
    scores: List[Dict[str, Any]] = []
    if not scores_dir.is_dir():
        return scores
    for path in sorted(scores_dir.glob("*.json")):
        try:
            scores.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return scores


def _group_by_skill(scores: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for score in scores:
        out[score.get("skill", "unknown")].append(score)
    for key in out:
        out[key].sort(key=lambda s: s.get("timestamp", ""))
    return out


def _radar_svg(dimensions: Dict[str, Dict[str, Any]]) -> str:
    """Render a 7-axis radar SVG for one scorecard's dimensions."""
    import math

    dims = [
        "correctness", "completeness", "adherence", "actionability",
        "efficiency", "safety", "consistency",
    ]
    cx, cy, r = 150, 130, 90
    parts: List[str] = [f'<svg viewBox="0 0 300 280" width="300" height="280">']
    # Concentric rings at 2/4/6/8/10
    for ring in (2, 4, 6, 8, 10):
        rr = r * (ring / 10)
        parts.append(f'<circle class="ring" cx="{cx}" cy="{cy}" r="{rr}" />')
    # Axes + labels
    for i, dim in enumerate(dims):
        angle = -math.pi / 2 + (2 * math.pi * i / len(dims))
        ex = cx + r * math.cos(angle)
        ey = cy + r * math.sin(angle)
        parts.append(f'<line class="axis" x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" />')
        lx = cx + (r + 14) * math.cos(angle)
        ly = cy + (r + 14) * math.sin(angle)
        parts.append(
            f'<text class="label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle">{dim[:4]}</text>'
        )
    # Scorecard polygon
    pts: List[str] = []
    for i, dim in enumerate(dims):
        angle = -math.pi / 2 + (2 * math.pi * i / len(dims))
        score = float(dimensions.get(dim, {}).get("score", 0))
        rr = r * (score / 10)
        x = cx + rr * math.cos(angle)
        y = cy + rr * math.sin(angle)
        pts.append(f"{x:.1f},{y:.1f}")
    parts.append(
        f'<polygon points="{" ".join(pts)}" fill="rgba(127,212,255,0.25)" '
        f'stroke="#7fd4ff" stroke-width="1.5" />'
    )
    parts.append("</svg>")
    return "".join(parts)


def _trend_svg(history: List[Dict[str, Any]]) -> str:
    """Render a composite-score trend line across history."""
    if not history:
        return '<p class="label">No history yet.</p>'
    width, height, pad = 300, 80, 10
    values = [float(h.get("composite_score", 0)) for h in history]
    n = len(values)
    parts: List[str] = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    # Plot area 0..10 on y
    if n == 1:
        x = width / 2
        y = height - pad - (values[0] / 10) * (height - 2 * pad)
        parts.append(f'<circle class="trend-dot" cx="{x}" cy="{y:.1f}" r="3" />')
    else:
        step = (width - 2 * pad) / max(n - 1, 1)
        points: List[str] = []
        for i, v in enumerate(values):
            x = pad + i * step
            y = height - pad - (v / 10) * (height - 2 * pad)
            points.append(f"{x:.1f},{y:.1f}")
            parts.append(f'<circle class="trend-dot" cx="{x:.1f}" cy="{y:.1f}" r="2" />')
        parts.append(f'<polyline class="trend-path" points="{" ".join(points)}" />')
    parts.append("</svg>")
    return "".join(parts)


def _grade_letter(grade: str) -> str:
    """Return the top-level letter (A/B/C/D/F) for CSS colour mapping."""
    return (grade or "F")[0].upper()


def _escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_panel(skill: str, history: List[Dict[str, Any]]) -> str:
    latest = history[-1] if history else {}
    grade = latest.get("grade", "F")
    composite = latest.get("composite_score", 0)
    dimensions = latest.get("dimensions", {})
    issues = latest.get("critical_issues", [])
    issues_html = "".join(f'<p class="issue">• {_escape(i)}</p>' for i in issues[:5])
    return f"""
<div class="panel">
  <div class="skill">{_escape(skill)}<span class="pill" style="margin-left:8px">n={len(history)}</span></div>
  <div><span class="grade {_grade_letter(grade)}">{_escape(grade)}</span><span>{composite:.2f}/10</span></div>
  {_radar_svg(dimensions)}
  {_trend_svg(history)}
  {issues_html}
</div>
"""


def generate(scores_dir: Path, output: Path, now: str) -> None:
    """Write the studio dashboard to *output*."""
    scores = _load_scores(scores_dir)
    by_skill = _group_by_skill(scores)
    panels = "".join(
        _render_panel(skill, history) for skill, history in sorted(by_skill.items())
    )
    html = HTML_TEMPLATE.format(
        panels=panels,
        score_count=len(scores),
        skill_count=len(by_skill),
        generated_at=now,
    )
    output.write_text(html, encoding="utf-8")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="verdict-studio")
    p.add_argument("--scores-dir", required=True, help="Directory containing score JSON files.")
    p.add_argument("--output", required=True, help="Output HTML file path.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    from datetime import datetime, timezone
    args = parse_args(argv)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    generate(Path(args.scores_dir), Path(args.output), now)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
