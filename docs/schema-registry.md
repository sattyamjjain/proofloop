# Verdict schema registry

Verdict publishes its public JSON schemas at a stable URL so
downstream consumers can validate scorecards (and future envelopes)
without cloning the Verdict repository.

## Canonical URLs

| Schema                 | Version | URL |
| ---------------------- | :-----: | --- |
| Scorecard              | v1      | <https://verdict.dev/schemas/scorecard.v1.json> |

The `$schema` field in every emitted scorecard points at the
corresponding URL. Consumers should parse `schemaVersion` first and
gate on `>= 1.0.0, < 2.0.0` for the v1 line.

## Transport

Until `verdict.dev` is claimed, the registry is served from **GitHub
Pages** on this repository. The workflow in
`.github/workflows/pages.yml` mirrors every file under `schemas/` into
the `gh-pages` branch on every push to `main`, preserving the
filename so clients can hotlink directly:

```
https://sattyamjjain.github.io/verdict/schemas/scorecard.v1.json
```

Once the domain is live, it will be a simple CNAME over the same
Pages deployment — no schema bodies change, only the hostname.
Consumers pinned to `https://verdict.dev/schemas/…` will resolve
through the CNAME from day one.

## Evolution rules

See `DEEP_ANALYSIS.md §Schema stability contract` for the full
SemVer-plus-deprecation policy. Headline:

- MAJOR pins the URL path (`scorecard.v1.json` ↔ `scorecard.v2.json`).
- MINOR / PATCH bumps do NOT change the URL.
- Any consumer that cares about the distinction should parse the
  `schemaVersion` field out of the document itself.

## Static, not live

The registry is intentionally a **static** Pages site. There is no
tracking, no rate limits, and no service to outage. If the URL stops
resolving, every consumer can pin to the in-repo path
(`schemas/scorecard.v1.schema.json`) as a fallback with byte-for-byte
identical content.

No roadmap entry for a paid / hosted schema registry — it would break
the offline-first pitch Verdict is built on.

## Adding a new schema

1. Drop the `.json` file under `schemas/` at the root of the repo.
2. Update this document with the new row and URL.
3. Push to `main`. The Pages workflow mirrors every `.json` in
   `schemas/` automatically; no manual copying.
4. In-repo consumers (`tests/_schema_validator.py` et al.) pick the
   new schema up without further wiring because they resolve by
   filename.
