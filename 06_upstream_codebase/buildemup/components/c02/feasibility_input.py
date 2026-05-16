"""
Component 2 — FeasibilityInput pattern (Session E architecture).

Wraps the captured Brief plus optional fields the user might not know
(soil type, water table, distance from electric line, distance from
water course, etc.) with provenance tracking.

Each optional field has 3 possible states:

  USER_PROVIDED_VERIFIED — user has the data + had it validated
    (soil test report, NABL lab result, surveyor measurement, etc.)
    → check uses value with HIGH confidence

  USER_PROVIDED_UNVERIFIED — user gave a value but didn't verify it
    (eyeballed distance, neighbour told them, builder's word)
    → check uses value with MEDIUM confidence + verification rec

  USER_DOESNT_KNOW — user explicitly said "I don't know" or skipped
    → check uses city-default educated guess with LOW confidence
    → if guess would HARD_FAIL the check, downgrade to SOFT_WARN
       (per the user's approved principle: "assumed values that would
        HARD-fail → soft-warn")

  NOT_ASKED — the field hasn't been surfaced to the user yet
    → treated same as USER_DOESNT_KNOW for v0.1 (Sessions H+ will
      track this differently for UI purposes)

The pattern is enforced via the InputField generic dataclass below.
Each check that needs an "I don't know"-able field calls
inputfield.use_value_with_confidence() which returns:
  (value: T, confidence: ConfidenceLevel, source: FieldSource)

The check then knows whether to downgrade severity for assumed values.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    ConfidenceLevel, VerificationPriority,
)


class FieldSource(Enum):
    """Provenance of an optional FeasibilityInput field value.

    USER_PROVIDED_VERIFIED: data + verified (NABL soil test, etc.)
    USER_PROVIDED_UNVERIFIED: user gave value but no verification
    USER_DOESNT_KNOW: user explicitly skipped / "I don't know"
    NOT_ASKED: field not yet surfaced to user (treated as DOESNT_KNOW
        for v0.1; H+ may render it differently in UI)
    """
    USER_PROVIDED_VERIFIED = "user_provided_verified"
    USER_PROVIDED_UNVERIFIED = "user_provided_unverified"
    USER_DOESNT_KNOW = "user_doesnt_know"
    NOT_ASKED = "not_asked"


T = TypeVar("T")


@dataclass(frozen=True)
class InputField(Generic[T]):
    """An optional FeasibilityInput field with provenance tracking.

    Use construct_*() classmethods to build with the right source.
    The 3-state pattern is enforced — value can be None ONLY when
    source is USER_DOESNT_KNOW or NOT_ASKED.
    """
    value: T | None
    source: FieldSource
    user_facing_question: str = ""
    field_name: str = ""

    def __post_init__(self) -> None:
        # Provenance invariants
        if self.source in (FieldSource.USER_PROVIDED_VERIFIED,
                           FieldSource.USER_PROVIDED_UNVERIFIED):
            if self.value is None:
                raise ValueError(
                    f"InputField source={self.source.value} requires "
                    f"a non-None value. Use USER_DOESNT_KNOW if user "
                    f"didn't provide."
                )
        elif self.source in (FieldSource.USER_DOESNT_KNOW,
                             FieldSource.NOT_ASKED):
            # When source indicates absence of user data, value MUST be None
            # (otherwise it's contradictory: 'I don't know' + a value)
            if self.value is not None:
                raise ValueError(
                    f"InputField source={self.source.value} requires "
                    f"value=None (user has not provided a value). "
                    f"Got value={self.value!r}. Use unverified() if "
                    f"the user did provide a value."
                )

    @classmethod
    def verified(cls, value: T, *, field_name: str = "",
                 user_facing_question: str = "") -> InputField[T]:
        return cls(value=value,
                   source=FieldSource.USER_PROVIDED_VERIFIED,
                   field_name=field_name,
                   user_facing_question=user_facing_question)

    @classmethod
    def unverified(cls, value: T, *, field_name: str = "",
                   user_facing_question: str = "") -> InputField[T]:
        return cls(value=value,
                   source=FieldSource.USER_PROVIDED_UNVERIFIED,
                   field_name=field_name,
                   user_facing_question=user_facing_question)

    @classmethod
    def unknown(cls, *, field_name: str = "",
                user_facing_question: str = "") -> InputField[T]:
        return cls(value=None,
                   source=FieldSource.USER_DOESNT_KNOW,
                   field_name=field_name,
                   user_facing_question=user_facing_question)

    @classmethod
    def not_asked(cls, *, field_name: str = "",
                  user_facing_question: str = "") -> InputField[T]:
        return cls(value=None,
                   source=FieldSource.NOT_ASKED,
                   field_name=field_name,
                   user_facing_question=user_facing_question)

    @property
    def is_user_data_present(self) -> bool:
        """True if the user provided a value (verified or not)."""
        return self.source in (
            FieldSource.USER_PROVIDED_VERIFIED,
            FieldSource.USER_PROVIDED_UNVERIFIED,
        )

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Map source → confidence."""
        if self.source == FieldSource.USER_PROVIDED_VERIFIED:
            return ConfidenceLevel.HIGH
        if self.source == FieldSource.USER_PROVIDED_UNVERIFIED:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @property
    def verification_priority_for_value(self) -> VerificationPriority:
        """Suggested verification priority based on source."""
        if self.source == FieldSource.USER_PROVIDED_VERIFIED:
            return VerificationPriority.OPTIONAL
        if self.source == FieldSource.USER_PROVIDED_UNVERIFIED:
            return VerificationPriority.IMPORTANT
        return VerificationPriority.IMPORTANT  # don't-know defaults

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        # T is opaque (str / float / bool / etc). The Brief-driven
        # callers populate JSON-safe primitives only; we encode the
        # value as-is. Per S7a SPEC § 9.4 to_dict is pure (no I/O).
        return {
            "value": self.value,
            "source": self.source.value,
            "user_facing_question": self.user_facing_question,
            "field_name": self.field_name,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "InputField":
        return cls(
            value=payload.get("value"),
            source=FieldSource(payload["source"]),
            user_facing_question=payload.get("user_facing_question", ""),
            field_name=payload.get("field_name", ""),
        )


@dataclass(frozen=True)
class FeasibilityInput:
    """Wrapper for Brief + optional fields the user might not know.

    Plain Brief data is in `brief`. Optional fields with provenance
    are individual InputField instances. Checks that need an optional
    field use the corresponding InputField.

    Future Sessions (E onward): more optional fields added here.
    Session E ships with: soil_type, water_table_depth_m,
    distance_from_electric_line_m, distance_from_water_course_m.
    """
    brief: Brief

    # Soil characterization
    soil_type: InputField[str] = field(default_factory=lambda: InputField.not_asked(
        field_name="soil_type",
        user_facing_question=(
            "What soil type is on your plot? "
            "(sandy_alluvial / black_cotton / laterite / clay / "
            "weathered_rock / mixed)"
        ),
    ))

    # Water table depth in metres below ground
    water_table_depth_m: InputField[float] = field(default_factory=lambda: InputField.not_asked(
        field_name="water_table_depth_m",
        user_facing_question=(
            "What is the depth of the water table below your plot? "
            "(metres, in the wettest month)"
        ),
    ))

    # Distance from nearest overhead electric line
    distance_from_electric_line_m: InputField[float] = field(
        default_factory=lambda: InputField.not_asked(
            field_name="distance_from_electric_line_m",
            user_facing_question=(
                "What is the distance from your plot edge to the "
                "nearest overhead electric line? (metres)"
            ),
        )
    )

    # Whether HT or LT line (only relevant if distance provided)
    electric_line_type: InputField[str] = field(
        default_factory=lambda: InputField.not_asked(
            field_name="electric_line_type",
            user_facing_question="Is the electric line LT (low) or HT (high tension)?",
        )
    )

    # Distance from nearest water course (drain/stream/river)
    distance_from_water_course_m: InputField[float] = field(
        default_factory=lambda: InputField.not_asked(
            field_name="distance_from_water_course_m",
            user_facing_question=(
                "What is the distance from your plot to the nearest "
                "water course (drain, stream, river)? (metres)"
            ),
        )
    )

    # Boolean: is there ANY water course within 30m?
    has_water_course_within_30m: InputField[bool] = field(
        default_factory=lambda: InputField.not_asked(
            field_name="has_water_course_within_30m",
            user_facing_question=(
                "Is there any drain, stream, or river within 30m of your plot?"
            ),
        )
    )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "brief": self.brief.to_dict(),
            "soil_type": self.soil_type.to_dict(),
            "water_table_depth_m": self.water_table_depth_m.to_dict(),
            "distance_from_electric_line_m":
                self.distance_from_electric_line_m.to_dict(),
            "electric_line_type": self.electric_line_type.to_dict(),
            "distance_from_water_course_m":
                self.distance_from_water_course_m.to_dict(),
            "has_water_course_within_30m":
                self.has_water_course_within_30m.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "FeasibilityInput":
        return cls(
            brief=Brief.from_dict(payload["brief"]),
            soil_type=InputField.from_dict(payload["soil_type"]),
            water_table_depth_m=InputField.from_dict(
                payload["water_table_depth_m"]
            ),
            distance_from_electric_line_m=InputField.from_dict(
                payload["distance_from_electric_line_m"]
            ),
            electric_line_type=InputField.from_dict(
                payload["electric_line_type"]
            ),
            distance_from_water_course_m=InputField.from_dict(
                payload["distance_from_water_course_m"]
            ),
            has_water_course_within_30m=InputField.from_dict(
                payload["has_water_course_within_30m"]
            ),
        )
