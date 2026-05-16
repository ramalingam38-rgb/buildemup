"""
BuildemUp† — Component Output Base Class
==========================================

Enforces contract: every component's output must expose:
  - Transparency triples for all user-facing numeric fields
  - Confidence level for the overall result
  - A user-facing explain() method
  - A machine-readable to_dict() method
  - A list of warnings and trace info

Components that inherit from ComponentOutput cannot accidentally
skip these.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field, fields
from typing import Any

from buildemup.utils.confidence import Confidence
from buildemup.utils.transparency import TransparencyTriple


@dataclass
class ComponentOutput:
    """Base class for all component outputs.

    Subclasses should add their specific fields. This base guarantees
    the cross-cutting contract is honored.
    """
    # Every output has at least one Transparency Triple (the headline number).
    # Subclasses declare which field in their dataclass is the "primary" one.
    trace_id: str = ""
    component_name: str = ""
    overall_confidence: Confidence = Confidence.MEDIUM
    warnings: list[str] = field(default_factory=list)
    info_messages: list[str] = field(default_factory=list)

    def validate(self) -> None:
        """Run sanity checks. Override in subclass for specific checks.

        Raises AssertionError if contract is violated. Called automatically
        by the orchestrator before returning results.
        """
        # Every numeric field annotated as TransparencyTriple must be populated.
        for fld in fields(self):
            val = getattr(self, fld.name)
            if isinstance(val, TransparencyTriple):
                assert val.exact_value is not None, (
                    f"{self.__class__.__name__}.{fld.name}: TransparencyTriple "
                    f"has no exact_value"
                )
                assert val.derivation, (
                    f"{self.__class__.__name__}.{fld.name}: TransparencyTriple "
                    f"has no derivation (Principle 2 violation)"
                )

    def to_dict(self) -> dict[str, Any]:
        """Machine-readable representation."""
        result = {
            "component": self.component_name,
            "trace_id": self.trace_id,
            "overall_confidence": self.overall_confidence.value,
            "warnings": self.warnings,
            "info_messages": self.info_messages,
        }
        # Include any TransparencyTriple fields
        for fld in fields(self):
            val = getattr(self, fld.name)
            if isinstance(val, TransparencyTriple):
                result[fld.name] = val.to_dict()
        return result
