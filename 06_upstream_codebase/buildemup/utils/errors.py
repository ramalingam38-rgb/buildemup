"""
BuildemUp† — Error Taxonomy
=============================

Custom exception hierarchy for clear error classification.

Three categories:
  - UserActionable: user can fix (adjust input, get soil test, etc.)
  - Unsupported: we can't handle this (Zone V seismic, >G+4 floors)
  - Internal: developer/system issue (missing rate, bad config)

Every raised error must:
  - Inherit from a specific category
  - Have a user_message (plain language)
  - Have a suggested_action (if UserActionable)

†= placeholder name marker.
"""
from __future__ import annotations


# ─── Base ────────────────────────────────────────────────────────────────
class BuildemUpError(Exception):
    """Base for all BuildemUp† errors."""

    def __init__(
        self,
        technical_message: str,
        user_message: str | None = None,
        suggested_action: str | None = None,
    ):
        super().__init__(technical_message)
        self.technical_message = technical_message
        self.user_message = user_message or technical_message
        self.suggested_action = suggested_action

    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "technical_message": self.technical_message,
            "user_message": self.user_message,
            "suggested_action": self.suggested_action,
        }


# ─── Category 1: User actionable (user can fix) ──────────────────────────
class UserActionableError(BuildemUpError):
    """User can take a specific action to fix this."""
    pass


class EnvelopeTooSmallError(UserActionableError):
    """Plot too small after setbacks for structural design."""


class EnvelopeTooIrregularError(UserActionableError):
    """Plot geometry too irregular (L/U with deep re-entrant corner)."""


class SoilTestingRequiredError(UserActionableError):
    """We need real soil data before proceeding."""


class BudgetInfeasibleError(UserActionableError):
    """Budget cannot support the brief."""


# ─── Category 2: Unsupported (we don't handle this in v1) ────────────────
class UnsupportedConfigurationError(BuildemUpError):
    """This configuration is outside our supported range."""
    pass


class SeismicZoneUnsupportedError(UnsupportedConfigurationError):
    """Zone V or unknown zone — needs expert structural design."""


class FloorCountUnsupportedError(UnsupportedConfigurationError):
    """>G+4 floors need custom high-rise design."""


class CityUnsupportedError(UnsupportedConfigurationError):
    """No rate data for this city yet."""


# ─── Category 3: Internal (developer/system issue) ───────────────────────
class InternalError(BuildemUpError):
    """System error — developer should see this, not user."""
    pass


class RateProviderMissingError(InternalError):
    """A rate lookup failed — data inconsistency."""


class KnowledgeBaseError(InternalError):
    """A KB rule is missing or malformed."""


# ─── Helper: wrap standard ValueError when migrating old code ────────────
def wrap_value_error(
    error_class: type[BuildemUpError],
    technical_message: str,
    user_message: str | None = None,
    suggested_action: str | None = None,
) -> BuildemUpError:
    """Convenience for raising properly-typed errors."""
    return error_class(
        technical_message=technical_message,
        user_message=user_message,
        suggested_action=suggested_action,
    )


# ─── User-facing formatting (v0.4) ───────────────────────────────────────
def format_for_user(error: Exception) -> dict:
    """Convert any exception (typed or not) to a user-presentable dict.

    For BuildemUpError: uses the typed user_message + suggested_action.
    For unexpected errors: wraps with a generic apologetic message and
    flags it as an internal issue we should investigate.
    """
    if isinstance(error, BuildemUpError):
        category = "user_actionable"
        if isinstance(error, UnsupportedConfigurationError):
            category = "unsupported"
        elif isinstance(error, InternalError):
            category = "internal"
        return {
            "title": _user_title_for(error),
            "message": error.user_message,
            "suggested_action": error.suggested_action,
            "category": category,
            "error_type": error.__class__.__name__,
            "is_user_facing_safe": True,
        }
    # Unexpected error — never leak internals to user
    return {
        "title": "Something went wrong on our end",
        "message": (
            "We hit an unexpected issue while processing your request. "
            "This is on us, not you. Please try again, or report this if "
            "it keeps happening."
        ),
        "suggested_action": (
            "Try again. If the issue persists, the error reference is below "
            "— share it with support."
        ),
        "category": "internal",
        "error_type": error.__class__.__name__,
        "technical_details": str(error),
        "is_user_facing_safe": False,
    }


def _user_title_for(error: BuildemUpError) -> str:
    """Short title for user display."""
    titles = {
        "EnvelopeTooSmallError": "Your plot is too small",
        "EnvelopeTooIrregularError": "Your plot shape needs an engineer",
        "SoilTestingRequiredError": "Soil test recommended first",
        "BudgetInfeasibleError": "Budget below realistic range",
        "SeismicZoneUnsupportedError": "Your seismic zone needs custom design",
        "FloorCountUnsupportedError": "Too many floors for our v1 engine",
        "CityUnsupportedError": "City not supported yet",
        "RateProviderMissingError": "Rate data unavailable",
        "KnowledgeBaseError": "Knowledge base issue",
    }
    return titles.get(error.__class__.__name__, "Issue with your request")
