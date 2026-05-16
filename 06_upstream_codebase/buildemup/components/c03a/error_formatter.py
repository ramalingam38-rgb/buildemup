"""
BuildemUp† — Component 3a Session 4: reason-aware error formatter.

Per locked S4 SPEC v0.1 § 8 (and parent C3a spec § 4.8).

Public API:
    format_validation_error_for_user(error, option) -> str

The formatter:
  1. Reads error.classify() to pick a template
  2. Substitutes context fields into the template
  3. Falls back to a generic message for UNKNOWN classification
  4. Appends " Try a different option." to non-UNKNOWN messages

Why split the applier from the formatter:
  - the applier raises structured errors; S6/S7 can log them as JSON
  - copy changes don't force test rewrites in the applier
  - the formatter has zero domain logic — it's pure substitution

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.domain.extreme_case import (
    BriefChangeIntegrityError,
    ResolutionOption,
)


# ─────────────────────────────────────────────────────────────────────
# Templates (S4 spec § 8)
#
# Note on placeholders:
#   {option_action} — substituted from option.description.lower()
#   all others        — read from error.context
# ─────────────────────────────────────────────────────────────────────

_TEMPLATES: dict[str, str] = {
    "BEDROOM_COUNT_BELOW_MIN": (
        "Removing {option_action} would leave only {resulting_count} "
        "bedroom(s), which is below your stated {stated_min}-bedroom "
        "minimum."
    ),
    "BUDGET_BELOW_THRESHOLD": (
        "Reducing budget by ₹{delta_l} L would put estimated cost at "
        "₹{est_l} L vs ₹{budget_l} L budget — gap exceeds the "
        "catastrophic threshold."
    ),
    "FAR_EXCEEDED_BY_CHANGE": (
        "Adding a floor would push your design over the FAR limit for "
        "{city}."
    ),
    "ROOM_AREA_BELOW_NBC_MIN": (
        "Setting {room_type} below NBC minimum ({nbc_min_sqm:.1f} sqm) "
        "is not permitted."
    ),
    "FLOOR_COUNT_BELOW_MIN": (
        "Dropping a floor would leave {resulting_count} floor(s); brief "
        "must have at least {stated_min}."
    ),
    # B-014 (S54 fix): SETBACK_INVALID — when a brief-change would set a
    # setback outside the allowed 0-15m range (e.g. negative from a
    # too-large reduction, or > 15m from an extreme increment).
    "SETBACK_INVALID": (
        "Adjusting the {side} setback by {delta_m}m would make it "
        "{result_m}m, which is outside the allowed 0–15m range."
    ),
    "UNKNOWN": (
        "This option doesn't work for your brief — try another."
    ),
}

_SUFFIX = " Try a different option."

# UNKNOWN is the only template whose copy already says "try another";
# we don't double-suffix it.
_NO_SUFFIX_FOR = frozenset({"UNKNOWN"})

# Default fillers used when context is missing a field — keeps output
# non-empty even on slightly malformed errors. The formatter will
# never raise; it always returns a usable string.
_CONTEXT_DEFAULTS: dict[str, object] = {
    "option_action": "this option",
    "resulting_count": 0,
    "stated_min": 0,
    "delta_l": 0,
    "est_l": 0,
    "budget_l": 0,
    "city": "your city",
    "room_type": "this room",
    "nbc_min_sqm": 0.0,
    # B-014 (S54) SETBACK_INVALID context fields
    "side": "specified",
    "delta_m": 0,
    "result_m": 0,
    "current_m": 0,
}


def format_validation_error_for_user(
    error: BriefChangeIntegrityError,
    option: ResolutionOption,
) -> str:
    """Render a user-facing reason string for a validation failure.

    Per parent C3a spec § 4.8: surface the specific validation reason,
    not a generic message. Non-UNKNOWN messages end with the suffix
    "Try a different option.".

    Args:
        error: the BriefChangeIntegrityError raised by the applier.
        option: the ResolutionOption the user picked. Used to fill
            the {option_action} placeholder.

    Returns:
        A non-empty plain-text string ready to display below the
        failed option in the UI. Never raises.
    """
    classification = error.classify()
    template = _TEMPLATES.get(classification, _TEMPLATES["UNKNOWN"])

    # Build the substitution dict: defaults overlaid with whatever the
    # error's context provides, plus option_action.
    fillers: dict[str, object] = dict(_CONTEXT_DEFAULTS)
    fillers["option_action"] = (option.description or "this option").lower()
    if error.context:
        fillers.update(error.context)

    try:
        body = template.format(**fillers)
    except (KeyError, ValueError, TypeError):
        # Defensive: if template formatting fails (e.g., context value
        # is the wrong type for a numeric format spec), fall back to
        # the UNKNOWN template — never raise from the formatter.
        body = _TEMPLATES["UNKNOWN"]
        classification = "UNKNOWN"

    if classification in _NO_SUFFIX_FOR:
        return body
    return body + _SUFFIX
