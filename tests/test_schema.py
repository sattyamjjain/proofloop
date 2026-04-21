#!/usr/bin/env python3
"""Validate every persisted scorecard fixture against scorecard.v1.schema.json.

This is the compatibility gate for the Verdict scorecard JSON shape.
When you intentionally evolve the schema, bump ``schemaVersion``, add
the new fields under ``$defs`` or at the top level, and regenerate the
fixtures. See DEEP_ANALYSIS.md §Schema stability contract.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "scorecard.v1.schema.json"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "scorecards"
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "judge" / "scripts"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema_validator import validate  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))
import score  # noqa: E402


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


class TestSchemaFileWellFormed(unittest.TestCase):
    def test_schema_file_parses(self) -> None:
        schema = _load_schema()
        self.assertEqual(
            schema.get("$id"),
            "https://verdict.dev/schemas/scorecard.v1.json",
        )
        self.assertEqual(
            schema.get("$schema"),
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertIn("dimensions", schema["properties"])

    def test_schema_requires_schema_and_version(self) -> None:
        schema = _load_schema()
        self.assertIn("$schema", schema["required"])
        self.assertIn("schemaVersion", schema["required"])


class TestPersistedFixtures(unittest.TestCase):
    """Every scorecard in tests/fixtures/scorecards/ must validate."""

    def test_fixtures_directory_populated(self) -> None:
        self.assertTrue(FIXTURES_DIR.is_dir())
        fixtures = list(FIXTURES_DIR.glob("*.json"))
        self.assertGreaterEqual(
            len(fixtures),
            3,
            "expected at least 3 persisted scorecard fixtures; regenerate them",
        )

    def test_every_fixture_validates(self) -> None:
        schema = _load_schema()
        failures = []
        for path in sorted(FIXTURES_DIR.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"{path.name}: malformed JSON — {exc}")
                continue
            ok, errors = validate(document, schema)
            if not ok:
                failures.append(f"{path.name}:\n  " + "\n  ".join(errors))
        self.assertEqual(failures, [], "schema violations:\n" + "\n".join(failures))

    def test_every_fixture_has_schema_fields_at_top(self) -> None:
        """$schema and schemaVersion must be present and correct."""
        for path in sorted(FIXTURES_DIR.glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                document.get("$schema"),
                "https://verdict.dev/schemas/scorecard.v1.json",
                f"{path.name}: missing or wrong $schema",
            )
            self.assertEqual(
                document.get("schemaVersion"),
                "1.0.0",
                f"{path.name}: missing or wrong schemaVersion",
            )


class TestPersistInjection(unittest.TestCase):
    """save_score must inject $schema and schemaVersion on every write."""

    def test_save_score_injects_schema_fields(self) -> None:
        import tempfile
        scorecard = {
            "skill": "test",
            "timestamp": "2026-04-19T00:00:00Z",
            "composite_score": 8.0,
            "raw_composite": 8.0,
            "grade": "B+",
            "grade_label": "Good",
            "dimensions": {
                "correctness":   {"score": 8, "weight": 0.25, "weighted": 2.0, "justification": "ok"},
                "completeness":  {"score": 8, "weight": 0.20, "weighted": 1.6, "justification": "ok"},
                "adherence":     {"score": 8, "weight": 0.15, "weighted": 1.2, "justification": "ok"},
                "actionability": {"score": 8, "weight": 0.15, "weighted": 1.2, "justification": "ok"},
                "efficiency":    {"score": 8, "weight": 0.10, "weighted": 0.8, "justification": "ok"},
                "safety":        {"score": 8, "weight": 0.10, "weighted": 0.8, "justification": "ok"},
                "consistency":   {"score": 5, "weight": 0.05, "weighted": 0.25, "justification": "ok"},
            },
            "red_flags": [],
            "bonuses": [],
            "adjustments": {"deduction": 0.0, "bonus": 0.0},
            "summary": "s",
            "one_liner": "ok",
            "critical_issues": [],
            "recommendations": [],
            "rubric_used": "default",
            "transcript_lines": 10,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = score.save_score(scorecard, tmp)
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(document["$schema"], score.SCORECARD_SCHEMA_URL)
        self.assertEqual(document["schemaVersion"], score.SCORECARD_SCHEMA_VERSION)
        # Keys must appear at the top of the emitted document (JSON object
        # key order is preserved by Python's json module).
        keys = list(document.keys())
        self.assertEqual(keys[0], "$schema")
        self.assertEqual(keys[1], "schemaVersion")

    def test_save_score_idempotent_when_fields_preexist(self) -> None:
        """If the caller already added $schema/schemaVersion, don't duplicate."""
        import tempfile
        scorecard = {
            "$schema": "https://example.com/other.json",
            "schemaVersion": "2.0.0",
            "skill": "x", "timestamp": "2026-04-19T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = score.save_score(scorecard, tmp)
            document = json.loads(Path(path).read_text(encoding="utf-8"))
            # Raw read has to happen before the tempdir is torn down.
            raw = Path(path).read_text(encoding="utf-8")
        # save_score overrides with its own canonical values.
        self.assertEqual(document["$schema"], score.SCORECARD_SCHEMA_URL)
        self.assertEqual(document["schemaVersion"], score.SCORECARD_SCHEMA_VERSION)
        # No duplicate keys in the persisted JSON text.
        self.assertEqual(raw.count('"$schema"'), 1)
        self.assertEqual(raw.count('"schemaVersion"'), 1)


if __name__ == "__main__":
    unittest.main()
