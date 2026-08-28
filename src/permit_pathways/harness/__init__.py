"""Verification harness: the runner and its report.

`__all__` is what makes these re-exports public. Without it, strict mypy
reads an imported name as private to this module, so every caller outside the
package had to either reach past it into `.runner` or carry an
`attr-defined` ignore.
"""

from .runner import VerificationReport, verify_rules

__all__ = ["VerificationReport", "verify_rules"]
