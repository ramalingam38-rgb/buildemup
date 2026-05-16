"""
BuildemUp — Component 11a — Phase 0 startup validation (Sub-session 4)
=========================================================================

Per spec § 3 Phase 0:

  1. ``validate_operator_registry()``         — Sub-2 (registry.py)
  2. ``validate_upstream_purity_contract()``   — this module (NEW v0.4)
  3. Sunset-enforcement scan (predicate registry pending count)
  4. ``validate_severity_classification_audit()`` — this module (NEW v1.0 W#5)
  5. Per-config validation                     — done in mutate_topologies()

This module wires (2), (3), and (4). The orchestrator runs them in
order at the very top of ``mutate_topologies()`` before any per-
candidate work begins.

== validate_upstream_purity_contract (Inv 25) ==
Walks ``UPSTREAM_PURITY_REGISTRY`` and confirms each declared entry
point references a real C7/C9/C10 callable. KB-version attestation is
informational at v1.0 (sunset-tagged for B-NEW-Q runtime cross-check
against actual KB versions).

== sunset enforcement (Inv 24) ==
Per § 0.2 LOCK gate: ``pending_upstream_predicate_count == 0`` at v1.0
LOCK; AND ``len(active_waivers) ≤ 3`` (Inv 24 binary clause). Both
clauses checked here.

== validate_severity_classification_audit (Inv 27 / F-v4-5) ==
Walks every TopologyMutationError subclass; verifies each carries a
``severity_tier`` ClassVar with a valid value {'per_candidate', 'batch',
'systemic'}. Failure → SeverityClassificationAuditError raised at
startup. Catches the F-v4-5 fail-closed scenario where an upstream
exception with no severity tier would default to 'systemic' and
batch-halt every per-candidate failure.
"""
from __future__ import annotations

import importlib
from typing import Iterable

from buildemup.components.c11a.errors import (
    DeepMutationPurityContractError,
    PendingUpstreamPredicateError,
    SeverityClassificationAuditError,
    TopologyMutationError,
    iter_registered_errors,
)
from buildemup.components.c11a.predicate_registry import (
    PREDICATE_REGISTRY,
    pending_upstream_predicate_count,
)
from buildemup.components.c11a.schema import (
    UPSTREAM_PURITY_REGISTRY,
    WAIVER_REGISTRY,
)


_VALID_SEVERITY_TIERS = frozenset({"per_candidate", "batch", "systemic"})


# =============================================================================
# § 0.1 / Inv 25 — Upstream purity contract
# =============================================================================


def validate_upstream_purity_contract() -> None:
    """Confirm every entry in ``UPSTREAM_PURITY_REGISTRY`` references a
    real, importable upstream callable.

    The KB-version attestation is informational at v1.0 — checking it
    against runtime KB version requires a cross-component KB-version
    accessor, deferred to B-NEW-Q. v1.0 implements the *structural*
    half: callable resolvability.

    Raises:
        DeepMutationPurityContractError if any registered entry point
        cannot be resolved at runtime (e.g., C7.GridGenerator was
        renamed without registry update).
    """
    for attestation in UPSTREAM_PURITY_REGISTRY:
        component_id = attestation.component_id  # "C7" → "c07" module path
        entry_point = attestation.entry_point   # "GridGenerator.generate" or "size_rooms"

        # Map component_id "C7" → module "buildemup.components.c07".
        module_path = _component_module_path(component_id)
        if module_path is None:
            raise DeepMutationPurityContractError(
                f"UPSTREAM_PURITY_REGISTRY entry references unknown "
                f"component_id={component_id!r}; expected one of "
                f"{{C7, C9, C10}}."
            )

        # Try resolving the entry_point under the component's package.
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise DeepMutationPurityContractError(
                f"UPSTREAM_PURITY_REGISTRY[{component_id}.{entry_point}]: "
                f"failed to import upstream module {module_path}: {exc}"
            )

        # Walk dotted entry_point through the module and any submodules.
        if not _resolve_entry_point(module, entry_point, component_id):
            raise DeepMutationPurityContractError(
                f"UPSTREAM_PURITY_REGISTRY[{component_id}.{entry_point}]: "
                f"entry point not resolvable in {module_path} or its "
                f"submodules. Either update the registry or restore "
                f"the upstream symbol."
            )


def _component_module_path(component_id: str) -> str | None:
    """Map "C7" / "C9" / "C10" → its package import path."""
    return {
        "C7":  "buildemup.components.c07",
        "C9":  "buildemup.components.c09",
        "C10": "buildemup.components.c10",
    }.get(component_id)


def _resolve_entry_point(
    module: object, dotted: str, component_id: str,
) -> bool:
    """Try to resolve ``dotted`` as an attribute path under ``module``,
    falling back to a small list of conventional submodule names.

    ``module`` is the top-level component package (e.g.,
    buildemup.components.c07). The entry points like
    "GridGenerator.generate" / "size_rooms" / "plan_wet_zones" live
    in submodules, not at package top-level. We try the package first
    (in case of re-exports), then a curated list of submodules.
    """
    # Try direct attribute path on the package.
    if _walk_dotted(module, dotted):
        return True

    # Fall back to a curated list of likely submodule names per
    # component. Lightweight — avoids globbing the whole package.
    fallback_submodules = {
        "C7":  ["grid_generator"],
        "C9":  ["room_sizer"],
        "C10": ["wet_zone_planner"],
    }.get(component_id, [])

    for sub in fallback_submodules:
        full_path = f"{module.__name__}.{sub}"  # type: ignore[attr-defined]
        try:
            submod = importlib.import_module(full_path)
        except ImportError:
            continue
        if _walk_dotted(submod, dotted):
            return True

    return False


def _walk_dotted(root: object, dotted: str) -> bool:
    """Walk a dotted attribute path. Returns True if every segment
    resolves."""
    obj = root
    for segment in dotted.split("."):
        obj = getattr(obj, segment, None)
        if obj is None:
            return False
    return True


# =============================================================================
# § 0.2 / Inv 24 — Sunset enforcement (LOCK gate)
# =============================================================================


def enforce_pending_predicate_sunset() -> None:
    """Per Inv 24: the LOCK gate at v1.0 requires
    ``pending_upstream_predicate_count - len(active_waivers) == 0`` AND
    ``len(active_waivers) ≤ 3``.

    At v1.0 LOCK time both clauses pass (B-NEW-J/K/L/P all LOCKED;
    WAIVER_REGISTRY empty). This function raises if either clause is
    violated post-LOCK (e.g., a future amendment introduces a new
    pending_upstream predicate without filing a waiver).

    Raises:
        PendingUpstreamPredicateError on LOCK gate violation.
    """
    pending = pending_upstream_predicate_count()
    waiver_count = len(WAIVER_REGISTRY)

    # Clause 1 — pending == 0 if no waivers cover them.
    if pending - waiver_count > 0:
        unwaived_predicates = [
            f"{p.rule_owner}.{p.rule_id}"
            for p in PREDICATE_REGISTRY
            if p.pending_upstream
        ]
        raise PendingUpstreamPredicateError(
            f"Inv 24 LOCK gate violation: "
            f"{pending} pending_upstream predicate(s) registered with "
            f"only {waiver_count} active waiver(s). Predicates: "
            f"{unwaived_predicates}. File a waiver in WAIVER_REGISTRY "
            f"or land the upstream amendment."
        )

    # Clause 2 — waiver budget cap.
    if waiver_count > 3:
        raise PendingUpstreamPredicateError(
            f"Inv 24 LOCK gate violation: "
            f"{waiver_count} active waivers in WAIVER_REGISTRY exceeds "
            f"the v1.0 cap of 3. Land an upstream amendment to retire "
            f"a waiver before adding another."
        )


# =============================================================================
# § 0.5 / Inv 27 / F-v4-5 — Severity classification audit
# =============================================================================


def validate_severity_classification_audit(
    extra_error_modules: Iterable[str] | None = None,
) -> None:
    """Walk every registered ``TopologyMutationError`` subclass; confirm
    each carries a ``severity_tier`` ClassVar in {'per_candidate',
    'batch', 'systemic'}.

    Per F-v4-5 fail-closed policy: if an upstream-raised exception
    reaches the pipeline's catch-and-classify logic with no
    ``severity_tier`` declared, it defaults to 'systemic' (which
    batch-halts the whole invocation). That's safe-by-default for
    correctness but operationally fragile. This audit catches missing
    declarations at startup, before they can cause production fragility.

    **Registry mechanism (B-NEW-X, S39 critique walk patch)**: walks
    ``iter_registered_errors()`` (a WeakSet populated at class-definition
    time via ``__init_subclass__``) instead of ``cls.__subclasses__()``.
    This eliminates the audit-state accumulation issue from
    dynamically-created subclasses and gives deterministic ordering
    across runs.

    Args:
        extra_error_modules: optional iterable of additional module
            import paths to scan (Sub-4 default scans only the C11a
            error registry; B-NEW-Q post-v1 expands to C7/C9/C10
            error hierarchies).

    Raises:
        SeverityClassificationAuditError if any subclass is missing
        the ClassVar or carries an invalid value.
    """
    # Per B-NEW-X: walk the explicit WeakSet registry, not
    # __subclasses__(). Returns subclasses in deterministic
    # (sorted-by-qualname) order.
    all_classes = iter_registered_errors()

    missing: list[str] = []
    invalid: list[tuple[str, str]] = []

    for cls in all_classes:
        tier = getattr(cls, "severity_tier", None)
        if tier is None:
            missing.append(f"{cls.__module__}.{cls.__qualname__}")
            continue
        if tier not in _VALID_SEVERITY_TIERS:
            invalid.append(
                (f"{cls.__module__}.{cls.__qualname__}", str(tier)),
            )

    # Optionally scan extra modules.
    if extra_error_modules:
        for mod_path in extra_error_modules:
            try:
                module = importlib.import_module(mod_path)
            except ImportError:
                # Permissive — extra modules are advisory at v1.
                continue
            for name in dir(module):
                obj = getattr(module, name, None)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseException)
                    and obj is not BaseException
                ):
                    tier = getattr(obj, "severity_tier", None)
                    if tier is None:
                        missing.append(f"{mod_path}.{name}")
                    elif tier not in _VALID_SEVERITY_TIERS:
                        invalid.append((f"{mod_path}.{name}", str(tier)))

    if missing or invalid:
        parts = []
        if missing:
            parts.append(
                f"missing severity_tier ClassVar on: {missing}"
            )
        if invalid:
            parts.append(
                f"invalid severity_tier values: {invalid} "
                f"(expected one of {sorted(_VALID_SEVERITY_TIERS)})"
            )
        raise SeverityClassificationAuditError(
            "Severity classification audit failed (Inv 27 / F-v4-5): "
            + "; ".join(parts)
        )


# Per B-NEW-X (S39 critique walk): the previous helper
# ``_all_subclasses(cls)`` walked ``cls.__subclasses__()`` recursively.
# That implementation accumulated ALL definitions for the process
# lifetime (including dynamically-created test fixtures) and returned
# results in non-deterministic order. The WeakSet-based registry in
# ``errors.py`` (via ``__init_subclass__``) plus the explicit sort in
# ``iter_registered_errors()`` replaces both behaviours cleanly.


# =============================================================================
# Combined Phase 0 entry point
# =============================================================================


def run_phase_0_startup_validation(
    *,
    severity_audit_extra_modules: Iterable[str] | None = None,
) -> None:
    """Run all four Phase 0 startup validators in canonical order.

    Per spec § 3 Phase 0. Called from ``mutate_topologies()`` before
    any per-candidate work. Idempotent — safe to call multiple times.

    Order:
      1. ``validate_operator_registry()``       (Inv 22, 26, 28)
      2. ``validate_upstream_purity_contract()`` (Inv 25)
      3. ``enforce_pending_predicate_sunset()``  (Inv 24)
      4. ``validate_severity_classification_audit()`` (Inv 27 / F-v4-5)
    """
    # Imported lazily to avoid circulars (registry.py imports from
    # operator_metadata; phase0.py is imported from the orchestrator).
    from buildemup.components.c11a.registry import validate_operator_registry

    validate_operator_registry()
    validate_upstream_purity_contract()
    enforce_pending_predicate_sunset()
    validate_severity_classification_audit(
        extra_error_modules=severity_audit_extra_modules,
    )


__all__ = [
    "validate_upstream_purity_contract",
    "enforce_pending_predicate_sunset",
    "validate_severity_classification_audit",
    "run_phase_0_startup_validation",
]
