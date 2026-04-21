"""Third-party integration shims.

Every module in this package is an **opt-in** shim. Nothing here is
imported at Verdict startup and nothing here runs unless the user
explicitly constructs / calls the shim function.

Current shims:

- :mod:`lighteval_shim` — expose Verdict as a LightEval v0.13.0+
  custom metric callable.
"""
from __future__ import annotations

from .lighteval_shim import verdict_metric

__all__ = ["verdict_metric"]
