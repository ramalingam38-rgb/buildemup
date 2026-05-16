"""Domain serialization helpers — used by per-class to_dict/from_dict.

Per S7a SPEC v1.0 LOCKED § 9.2 + § 9.3, every type reachable from
GateState exposes its own to_dict / from_dict in its owning module.
The METHODS are owned by the domain modules; the IMPLEMENTATION
helpers live here in S6 so the rules (frozenset → sorted list,
tuple → list, MappingProxyType → plain dict, Enum → .value) live in
ONE place and don't drift across types.

Conventions enforced:
  - Dicts have deterministic key order via sort_keys=True at JSON
    boundary (stored state_json layer; not enforced at to_dict() level
    since dict insertion order is already preserved Python 3.7+).
  - frozenset → sorted list (consistent across Pythons).
  - tuple → list (JSON has no tuple).
  - Enum → .value string.
  - None passes through unchanged.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Optional


def enc(value: Any) -> Any:
    """Encode a single value to a JSON-safe form.

    Handles primitives, enums, frozensets, tuples, lists, dicts, and
    objects with a `.to_dict()` method. Dataclasses without a to_dict
    method are not allowed here — the spec invariant is that every
    reachable type owns its own to_dict.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, (tuple, list)):
        return [enc(v) for v in value]
    if isinstance(value, dict):
        return {str(k): enc(v) for k, v in value.items()}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(
        f"don't know how to encode {type(value).__name__}: {value!r}. "
        f"Add a to_dict method or extend domain._serialization.enc"
    )


def dec_optional(payload: Any, decoder: Callable[[Any], Any]) -> Any:
    """Apply decoder if payload is not None; pass None through."""
    return decoder(payload) if payload is not None else None


def dec_tuple(
    payload: Optional[list], decoder: Callable[[Any], Any],
) -> tuple:
    """Decode a list back into a tuple of decoded items."""
    if payload is None:
        return ()
    return tuple(decoder(item) for item in payload)


def dec_enum(payload: Any, enum_cls: type) -> Any:
    """Reconstruct an enum from its .value string."""
    if payload is None:
        return None
    return enum_cls(payload)


__all__ = [
    "enc",
    "dec_optional",
    "dec_tuple",
    "dec_enum",
]
