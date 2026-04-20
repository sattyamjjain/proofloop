#!/usr/bin/env python3
"""Tests for the MLflow trace adapter (N6)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
from adapters import mlflow_trace  # noqa: E402
import adapters  # noqa: E402


def _sample_trace(status: str = "OK") -> dict:
    return {
        "schema": "mlflow.entities.Trace",
        "info": {"request_id": "req-1", "trace_id": "tr-1", "status": status},
        "data": {
            "spans": [
                {"name": "root", "events": [
                    {"name": "user", "attributes": {"content": "review auth"}},
                    {"name": "tool_call", "attributes": {"name": "read_file", "args": {"path": "x.py"}}},
                    {"name": "tool_result", "attributes": {"name": "read_file", "result": "42 lines"}},
                    {"name": "assistant", "attributes": {"content": "Done"}},
                ]},
            ],
        },
    }


def _write(trace: dict, suffix: str = ".json") -> Path:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with open(fd, "w", encoding="utf-8") as handle:
        json.dump(trace, handle)
    return Path(path)


class TestBasicExtraction(unittest.TestCase):
    def test_shipped_fixture_parses(self) -> None:
        path = str(FIXTURES_DIR / "mlflow-trace.json")
        lines = mlflow_trace.extract_lines(path)
        self.assertTrue(lines, "adapter returned no lines for shipped fixture")
        joined = "\n".join(lines)
        self.assertIn("[user]", joined)
        self.assertIn("[tool_call]", joined)
        self.assertIn("[tool_result]", joined)
        self.assertIn("[assistant]", joined)
        self.assertIn("audience check", joined)

    def test_event_prefixes_consistent(self) -> None:
        path = _write(_sample_trace())
        try:
            lines = mlflow_trace.extract_lines(str(path))
            prefixes = [ln.split(" ", 1)[0] for ln in lines if ln.startswith("[")]
            for prefix in ("[user]", "[tool_call]", "[tool_result]", "[assistant]"):
                self.assertIn(prefix, prefixes)
        finally:
            path.unlink()

    def test_trace_start_and_end_markers_present(self) -> None:
        path = _write(_sample_trace(status="OK"))
        try:
            lines = mlflow_trace.extract_lines(str(path))
            self.assertTrue(any(ln.startswith("[trace_start]") for ln in lines))
            self.assertTrue(any(ln.startswith("[trace_end]") and "status=OK" in ln for ln in lines))
        finally:
            path.unlink()


class TestEnvelopeShapes(unittest.TestCase):
    def test_traces_array_envelope(self) -> None:
        payload = {"traces": [_sample_trace(), _sample_trace(status="ERROR")]}
        path = _write(payload)
        try:
            lines = mlflow_trace.extract_lines(str(path))
            starts = [ln for ln in lines if ln.startswith("[trace_start]")]
            ends = [ln for ln in lines if ln.startswith("[trace_end]")]
            self.assertEqual(len(starts), 2)
            self.assertEqual(len(ends), 2)
            self.assertTrue(any("status=ERROR" in ln for ln in ends))
        finally:
            path.unlink()

    def test_non_trace_payload_returns_empty(self) -> None:
        path = _write({"foo": "bar"})
        try:
            self.assertEqual(mlflow_trace.extract_lines(str(path)), [])
        finally:
            path.unlink()

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(mlflow_trace.extract_lines("/tmp/verdict-mlflow-missing.json"), [])

    def test_malformed_json_returns_empty(self) -> None:
        fd, raw = tempfile.mkstemp(suffix=".json")
        try:
            with open(fd, "w") as handle:
                handle.write("not json")
            self.assertEqual(mlflow_trace.extract_lines(raw), [])
        finally:
            Path(raw).unlink()


class TestFingerprint(unittest.TestCase):
    def test_mlflow_trace_fingerprint_positive(self) -> None:
        path = _write(_sample_trace())
        try:
            self.assertTrue(mlflow_trace.looks_like_mlflow_trace(str(path)))
        finally:
            path.unlink()

    def test_non_mlflow_fingerprint_negative(self) -> None:
        path = _write({"role": "user", "content": "hi"})
        try:
            self.assertFalse(mlflow_trace.looks_like_mlflow_trace(str(path)))
        finally:
            path.unlink()

    def test_missing_file_fingerprint_false(self) -> None:
        self.assertFalse(mlflow_trace.looks_like_mlflow_trace("/tmp/definitely-missing.json"))


class TestAdapterRegistry(unittest.TestCase):
    def test_registered_under_two_names(self) -> None:
        self.assertIn("mlflow-trace", adapters.list_adapters())
        self.assertIn("mlflow", adapters.list_adapters())
        self.assertIs(
            adapters.get_adapter("mlflow"),
            adapters.get_adapter("mlflow-trace"),
        )

    def test_detect_adapter_picks_mlflow_for_trace_fixture(self) -> None:
        path = str(FIXTURES_DIR / "mlflow-trace.json")
        self.assertEqual(adapters.detect_adapter(path), "mlflow-trace")

    def test_detect_adapter_default_for_non_trace_file(self) -> None:
        path = _write({"role": "user", "content": "hi"})
        try:
            self.assertEqual(adapters.detect_adapter(str(path)), "claude-code")
        finally:
            path.unlink()


class TestLazyImport(unittest.TestCase):
    def test_mlflow_runtime_not_imported(self) -> None:
        # Core invariant: we parse the trace JSON directly; we never
        # import mlflow at runtime.
        self.assertNotIn("mlflow", sys.modules)


if __name__ == "__main__":
    unittest.main()
