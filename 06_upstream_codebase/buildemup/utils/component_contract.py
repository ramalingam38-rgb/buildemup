"""
BuildemUp† — Component Contract System (v0.5)
==============================================

Explicit input + output schemas per component, with validation at handoff.

WHY THIS EXISTS (the v0.4 review's most urgent codebase critique):

  As Components 1-17 are added, implicit contracts between them become a
  real risk. Component 7 produces output X. Component 8 consumes it.
  If 8's expectations drift from 7's actual shape, we get silent bugs
  that surface only as wrong final outputs.

  This system makes contracts EXPLICIT — declared in code at the
  component boundary, validated at handoff. Every new component MUST
  declare its input contract and output contract before integration.

WHY NOT PYDANTIC:

  Pydantic adds a 5MB dependency. Our use case is component handoff
  validation — narrow, performance-not-critical, no JSON schema export
  required. Dataclass + a small validator gives 80% of the value at
  zero dependency cost.

  When/if we need JSON-schema export for API documentation, migrate to
  Pydantic in v2. Until then, this is enough.

USAGE PATTERN:

    # Each component declares its contract in its module:
    @component_contract(
        component_id="C07_structural_grid",
        version="0.5",
        consumes=("envelope_width_m: float[5..50]", "city: str", ...),
        produces=("cost: TransparencyTriple", "structure: SizedStructure", ...),
    )
    class StructuralGridEngine:
        ...

    # The contract registry tracks all component contracts.
    # Tests verify that downstream consumers' assumptions match
    # upstream producers' actual outputs.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints
import inspect


# ─────────────────────────────────────────────────────────────────────────
# Contract data structures
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class FieldSpec:
    """One field in an input or output contract."""
    name: str
    type_name: str           # 'float', 'str', 'BuildingType', 'TransparencyTriple'
    required: bool = True
    description: str = ""
    constraints: tuple[str, ...] = ()    # e.g., ('>=5.0', '<=50.0', 'in: chennai|mumbai')

    def format_for_docs(self) -> str:
        req = "required" if self.required else "optional"
        ctx = f" [{', '.join(self.constraints)}]" if self.constraints else ""
        return f"{self.name}: {self.type_name} ({req}){ctx}"


@dataclass(frozen=True)
class ComponentContract:
    """The full contract for one component."""
    component_id: str         # e.g., "C07_structural_grid"
    version: str              # e.g., "0.5"
    description: str
    consumes: tuple[FieldSpec, ...]    # Input fields
    produces: tuple[FieldSpec, ...]    # Output fields

    def format_for_docs(self) -> str:
        lines = [
            f"=== {self.component_id} (v{self.version}) ===",
            f"  {self.description}",
            "",
            "  INPUT (consumes):",
        ]
        for spec in self.consumes:
            lines.append(f"    • {spec.format_for_docs()}")
        lines.append("")
        lines.append("  OUTPUT (produces):")
        for spec in self.produces:
            lines.append(f"    • {spec.format_for_docs()}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# Contract registry (single source of truth for all component contracts)
# ─────────────────────────────────────────────────────────────────────────
_CONTRACT_REGISTRY: dict[str, ComponentContract] = {}


def register_contract(contract: ComponentContract) -> None:
    """Register a component contract in the registry.

    Subsequent re-registrations of the same component_id will OVERWRITE.
    This is intentional — components evolve, the latest contract is what
    integration tests check against.
    """
    _CONTRACT_REGISTRY[contract.component_id] = contract


def get_contract(component_id: str) -> ComponentContract | None:
    return _CONTRACT_REGISTRY.get(component_id)


def all_contracts() -> dict[str, ComponentContract]:
    return dict(_CONTRACT_REGISTRY)


def format_all_contracts() -> str:
    """Print the full integration map for documentation."""
    if not _CONTRACT_REGISTRY:
        return "No component contracts registered yet."
    lines = ["BuildemUp† Component Contract Registry", "=" * 50, ""]
    for contract in _CONTRACT_REGISTRY.values():
        lines.append(contract.format_for_docs())
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────
class ContractViolation(Exception):
    """Raised when an input or output violates the declared contract."""

    def __init__(self, component_id: str, field_name: str, reason: str):
        self.component_id = component_id
        self.field_name = field_name
        self.reason = reason
        super().__init__(
            f"[{component_id}] field '{field_name}' violates contract: {reason}"
        )


# v0.7.1: Domain type names that must be validated as actual domain objects
# (not raw dicts / primitives). Per v0.7 review Drawback 3.
# Component 1 v0.1 adds: Plot, Setbacks, FloorRequirement, RoomRequirement,
# Brief, BudgetRange, CostEstimate, ComplianceSummary, GuidanceMessage.
_DOMAIN_TYPE_NAMES = {
    # Component 7 types
    "Building", "BuildingMeta", "Envelope", "Floor", "FloorType",
    "Column", "ColumnLocation", "DomainGrid",
    # Component 1 types
    "Plot", "PlotType", "Setbacks",
    "FloorRequirement", "RoomRequirement", "FloorUse", "RoomType",
    "Brief", "BudgetRange", "CostEstimate",
    "ComplianceSummary", "GuidanceMessage", "VastuTier",
    # Component 3a types (added Session 18, S2 build)
    # 5 enums
    "ExtremeCaseCategory", "ExtremeCaseId", "ResolutionProbability",
    "BriefMode", "CostConfidence",
    # 10 dataclasses
    "BriefChange", "CostImpact", "ResolutionOption", "ExtremeCase",
    "ExtremeDecision", "ExtremeDecisionLog", "CounterfactualSummary",
    "PreflightSummary", "PreviewModeAcknowledgment", "ResolvedBrief",
}


def _is_domain_type_name(type_name: str) -> bool:
    """True if the declared type_name refers to a domain object.

    Strips container prefixes like 'tuple[...]' or 'list[...]' to
    check the inner type.
    """
    t = type_name.strip()
    # Handle containers: 'tuple[Floor, ...]', 'list[Column]'
    for container in ("tuple[", "list[", "Optional[", "Sequence["):
        if t.startswith(container):
            inner = t[len(container):].rstrip("]")
            # Take the first type argument (strip ", ..." etc.)
            first = inner.split(",")[0].strip()
            return first in _DOMAIN_TYPE_NAMES
    return t in _DOMAIN_TYPE_NAMES


def _check_is_domain_object(value: Any, type_name: str) -> bool:
    """v0.7.1: Validate value is an instance of the declared domain type,
    not a raw dict or primitive. Used to enforce Drawback 3 rule:
    "NO raw dicts between components — use domain objects."

    Returns True if value looks like a domain object (has the expected
    dataclass shape), False if it's a dict / primitive.
    """
    # Raw dicts are NEVER acceptable for domain-typed fields
    if isinstance(value, dict):
        return False
    # Primitives are not domain objects
    if isinstance(value, (str, int, float, bool)):
        return False
    # None is not a domain object (unless field was Optional, handled elsewhere)
    if value is None:
        return False
    # Lists/tuples: check each element is domain-like (not dict)
    if isinstance(value, (list, tuple)):
        return all(
            not isinstance(item, (dict, str, int, float, bool))
            for item in value
        )
    # Otherwise: assume it's a dataclass or similar object
    # (duck-typing: has attributes, not a plain collection)
    return hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__")


def validate_input(component_id: str, input_obj: Any) -> list[str]:
    """Validate an input object against the registered contract.

    Returns list of violations (empty if all good). Does NOT raise —
    use as a check before passing to component, or in tests.

    v0.7.1: fields whose declared type_name is a domain class
    (Building, Envelope, Floor, etc.) must be actual domain objects,
    not raw dicts. This enforces the "domain-only contracts" rule
    from v0.7 review Drawback 3.
    """
    contract = get_contract(component_id)
    if contract is None:
        return [f"No contract registered for {component_id}"]

    violations: list[str] = []
    for spec in contract.consumes:
        if not hasattr(input_obj, spec.name):
            if spec.required:
                violations.append(f"missing required field: {spec.name}")
            continue
        value = getattr(input_obj, spec.name)

        # v0.7.1: Enforce domain-object usage for domain-typed fields
        if _is_domain_type_name(spec.type_name):
            if not _check_is_domain_object(value, spec.type_name):
                violations.append(
                    f"field '{spec.name}' declared as {spec.type_name} "
                    f"must be a domain object, not {type(value).__name__}. "
                    f"Raw dicts and primitives are not permitted for "
                    f"domain-typed fields (v0.7.1 enforcement)."
                )
                continue   # Skip constraint checks on bad type

        # Constraint checks
        for constraint in spec.constraints:
            if not _check_constraint(value, constraint):
                violations.append(
                    f"field '{spec.name}' = {value!r} violates: {constraint}"
                )
    return violations


def validate_output(component_id: str, output_obj: Any) -> list[str]:
    """Validate an output object against the registered contract.

    Returns list of violations (empty if all good).
    """
    contract = get_contract(component_id)
    if contract is None:
        return [f"No contract registered for {component_id}"]

    violations: list[str] = []
    for spec in contract.produces:
        if not hasattr(output_obj, spec.name):
            if spec.required:
                violations.append(f"missing required output field: {spec.name}")
    return violations


def _check_constraint(value: Any, constraint: str) -> bool:
    """Simple constraint language. Examples: '>=5.0', '<=50.0', 'in: a|b|c'."""
    constraint = constraint.strip()
    try:
        if constraint.startswith(">="):
            return float(value) >= float(constraint[2:].strip())
        if constraint.startswith("<="):
            return float(value) <= float(constraint[2:].strip())
        if constraint.startswith(">"):
            return float(value) > float(constraint[1:].strip())
        if constraint.startswith("<"):
            return float(value) < float(constraint[1:].strip())
        if constraint.startswith("in:"):
            allowed = [s.strip() for s in constraint[3:].split("|")]
            return str(value).lower() in [a.lower() for a in allowed]
        if constraint.startswith("not_empty"):
            return bool(value) and (not isinstance(value, str) or value.strip())
    except (ValueError, TypeError):
        return False
    return True  # Unknown constraint type → don't fail


# ─────────────────────────────────────────────────────────────────────────
# Convenience field builders
# ─────────────────────────────────────────────────────────────────────────
def required(name: str, type_name: str, description: str = "",
             *constraints: str) -> FieldSpec:
    return FieldSpec(
        name=name, type_name=type_name, required=True,
        description=description, constraints=constraints,
    )


def optional(name: str, type_name: str, description: str = "",
             *constraints: str) -> FieldSpec:
    return FieldSpec(
        name=name, type_name=type_name, required=False,
        description=description, constraints=constraints,
    )
