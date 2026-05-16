"""Typed exception classes for Brief / RoomRequirement / FloorRequirement /
BudgetRange validation failures.

Filed as B-013 (closed S55). Before this module existed, every
__post_init__ raised a plain `ValueError` and the C3a S4 classifier
(`brief_change_apply._classify_error`) dispatched on substring matches
against the error message text. That worked but was fragile: any
wording change in a domain validator silently regressed classification
to UNKNOWN.

These typed exceptions all subclass `ValueError`, so any existing
`except ValueError` site keeps working unchanged. The classifier in
C3a now matches by type first; the substring fallback survives for
any future code path that still raises plain ValueError.

Naming convention: each class names the domain concept + the
constraint that failed (e.g. `RoomCountNegativeError`, not
`InvalidRoomCount`). The fact that it's an error is in the suffix.
"""
from __future__ import annotations


class BriefDomainError(ValueError):
    """Base class for all Brief-layer validation errors.

    Inheriting from ValueError preserves backwards compatibility for
    any code that does `except ValueError` (the project has several
    such sites in C2 / C3a / tests).
    """


class BudgetValidationError(BriefDomainError):
    """BudgetRange.__post_init__ rejected the budget.

    Covers both implausibly-low min_lakhs and max_lakhs < min_lakhs.
    The C3a classifier groups both as `CLS_BUDGET`; keeping them as
    one type matches that semantic grouping.
    """


class FloorCountTooLowError(BriefDomainError):
    """Brief.__post_init__: Brief has zero floors (ground floor required)."""


class FloorNumberOutOfRangeError(BriefDomainError):
    """FloorRequirement.__post_init__: floor_number < 0 or > G+3."""


class RoomCountNegativeError(BriefDomainError):
    """RoomRequirement.__post_init__: count < 0."""


class RoomSizeBelowNbcMinError(BriefDomainError):
    """RoomRequirement.__post_init__: min_size_sqm or preferred_size_sqm
    is below the NBC residential minimum for the room type."""


__all__ = [
    "BriefDomainError",
    "BudgetValidationError",
    "FloorCountTooLowError",
    "FloorNumberOutOfRangeError",
    "RoomCountNegativeError",
    "RoomSizeBelowNbcMinError",
]
