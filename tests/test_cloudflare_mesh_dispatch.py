#!/usr/bin/env python3
"""Tests for Cloudflare Mesh dispatch wrapper (AA5)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "integrations"))
import cloudflare_ai_gateway as cfag  # noqa: E402


def _payload() -> dict:
    path = FIXTURES_DIR / "cloudflare-mesh-dispatch-payload.json"
    return json.loads(path.read_text(encoding="utf-8"))


class TestDispatchViaMeshShape(unittest.TestCase):
    def test_returns_request_and_result(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-1",
        )
        self.assertIn("request", out)
        self.assertIn("result", out)

    def test_request_is_post(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-1",
        )
        self.assertEqual(out["request"]["method"], "POST")
        self.assertEqual(out["request"]["endpoint"], "https://mesh.example/judge")

    def test_required_mesh_headers_present(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-prod",
        )
        headers = out["request"]["headers"]
        self.assertEqual(headers["x-mesh-agent-id"], "verdict-judge-prod")
        self.assertEqual(headers["x-mesh-trust-level"], "evaluator")
        self.assertEqual(headers["x-mesh-evaluation-class"], "verdict-judge-v1")
        self.assertEqual(headers["content-type"], "application/json")

    def test_trust_level_overridable(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-1",
            trust_level="observer",
        )
        self.assertEqual(out["request"]["headers"]["x-mesh-trust-level"], "observer")

    def test_evaluation_class_overridable(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-1",
            evaluation_class="clinical-eval-v1",
        )
        self.assertEqual(
            out["request"]["headers"]["x-mesh-evaluation-class"],
            "clinical-eval-v1",
        )


class TestDispatchResultBody(unittest.TestCase):
    def test_body_is_verdict_eval_webhook_result(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-1",
        )
        body = out["request"]["body"]
        self.assertIn("score", body)
        self.assertIn("passed", body)
        self.assertIn("rationale", body)
        # Score is in [0, 1] (Cloudflare convention).
        self.assertGreaterEqual(body["score"], 0.0)
        self.assertLessEqual(body["score"], 1.0)

    def test_result_mirrors_body(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-1",
        )
        self.assertEqual(out["request"]["body"], out["result"])


class TestDispatchDefensivePaths(unittest.TestCase):
    def test_non_dict_payload_soft_fails(self) -> None:
        out = cfag.dispatch_via_mesh(
            "not a dict",  # type: ignore[arg-type]
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="verdict-judge-1",
        )
        self.assertIsNone(out["request"])
        self.assertFalse(out["result"]["passed"])
        self.assertIn("invalid payload", out["result"]["rationale"])

    def test_missing_endpoint_soft_fails(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="",
            agent_identity="verdict-judge-1",
        )
        self.assertIsNone(out["request"])
        self.assertIn("mesh dispatch requires", out["result"]["rationale"])

    def test_missing_agent_identity_soft_fails(self) -> None:
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="https://mesh.example/judge",
            agent_identity="",
        )
        self.assertIsNone(out["request"])

    def test_no_actual_http_performed(self) -> None:
        """The wrapper composes a request — never sends one."""
        # If the function tried to dispatch, we'd need to mock urlopen.
        # The fact that the test passes without any HTTP mocks proves
        # the function is pure.
        out = cfag.dispatch_via_mesh(
            _payload(),
            mesh_endpoint="http://192.0.2.0/will-not-be-called",
            agent_identity="verdict-judge-1",
        )
        self.assertEqual(out["request"]["endpoint"], "http://192.0.2.0/will-not-be-called")


if __name__ == "__main__":
    unittest.main()
