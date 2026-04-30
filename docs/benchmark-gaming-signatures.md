# Benchmark-gaming signature pack format

The CC3 detector (`benchmark_gaming_detector.py`) and T2 CLI
(`bench_gaming_check.py`) read exploit signatures from a JSON
pack under `skills/judge/scripts/signatures/`.

## Pack layout

```json
{
  "signature_pack": "berkeley-rdi-2026-04-26",
  "source_url": "https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/",
  "verified_at": "2026-04-29",
  "covered_benchmarks": [
    "swe-bench", "webarena", "osworld", "gaia",
    "terminal-bench", "fieldworkarena", "car-bench"
  ],
  "exploits": [
    {
      "exploit_class": "harness-trust-pytest-self-report",
      "applies_to": ["swe-bench-pro"],
      "description": "...",
      "patterns": ["echo .*PASSED", "..."],
      "min_short_circuit_length": 80,
      "confidence_default": 0.85
    }
  ]
}
```

## Field reference

- **`signature_pack`** — name; matches the filename without
  `.json`.
- **`source_url`** — primary-source URL (used in scorecard
  evidence references).
- **`verified_at`** — ISO date when the signatures were last
  cross-checked against the source.
- **`covered_benchmarks`** — informational; the benchmarks the
  pack claims coverage of.
- **`exploits[]`** — one object per exploit class.
  - **`exploit_class`** — short label (used in scorecard
    `critical_issues`).
  - **`applies_to`** — list of rubric names this exploit is
    relevant to (`swe-bench-pro`, `terminal-bench`,
    `browser-agent`). Empty / absent = applies to all.
  - **`patterns`** — list of regex strings (Python regex
    dialect, case-insensitive, multi-line).
  - **`min_reasoning_turns`** — optional integer; trajectory
    must have ≥ this many "reasoning turns" (long non-shell
    lines) to avoid the short-circuit class.
  - **`min_short_circuit_length`** — optional integer; the full
    transcript text must exceed this length.
  - **`confidence_default`** — float [0.0, 1.0]; how confident
    the published signature is when matched.

## Refreshing the pack (Issue O14)

The Berkeley RDI signatures will move with future paper
revisions. v1.4.2 ships the 2026-04-26 pack at
`signatures/berkeley-rdi-2026-04-26.json`.

v1.4.3 will add a `--signatures-from <url>` flag to both the
detector and the T2 CLI so a fresh pack can be loaded without a
Verdict release. Until then, override via
`--signature-pack <name>` after dropping a new file into
`signatures/`.

## Sources

- [rdi.berkeley.edu — How We Broke Top AI Agent Benchmarks (2026-04-26)](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/)
