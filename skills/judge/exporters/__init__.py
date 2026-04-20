"""Scorecard exporters for interop with other evaluation formats.

v1.2.0 ships:

- :mod:`openai_evals` — OpenAI Model Spec Evals-compatible JSON.
"""
from __future__ import annotations

from .openai_evals import to_openai_evals_format

__all__ = ["to_openai_evals_format"]
