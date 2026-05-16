"""
BuildemUp† — Setbacks domain object.

The four setback distances around a plot: front, rear, left side,
right side. Used in two forms per SPEC_v0.2:

  user_stated_setbacks  : what the user thinks or wants
  nbc_compliant_setbacks: what the city DCR / NBC requires

Both are compared in soft-guide messages.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Setbacks:
    """Four setback distances (in metres) around a plot.

    Left/right are defined from the street perspective (someone standing
    on the street facing the plot — left hand = left side).

    For CONTINUOUS plots, side setbacks = 0.
    For SEMI_DETACHED, the shared side = 0.
    """
    front_m: float
    rear_m: float
    side_left_m: float
    side_right_m: float

    def __post_init__(self) -> None:
        for name, value in (
            ("front_m", self.front_m),
            ("rear_m", self.rear_m),
            ("side_left_m", self.side_left_m),
            ("side_right_m", self.side_right_m),
        ):
            if value < 0.0:
                raise ValueError(
                    f"Setback {name}={value}m cannot be negative."
                )
            if value > 15.0:
                # Unreasonable for residential — catch data-entry errors
                raise ValueError(
                    f"Setback {name}={value}m exceeds 15m — unusual for "
                    f"residential. Check input."
                )

    @property
    def total_width_reduction_m(self) -> float:
        """How much the plot width shrinks due to side setbacks."""
        return self.side_left_m + self.side_right_m

    @property
    def total_depth_reduction_m(self) -> float:
        """How much the plot depth shrinks due to front + rear setbacks."""
        return self.front_m + self.rear_m

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "front_m": self.front_m,
            "rear_m": self.rear_m,
            "side_left_m": self.side_left_m,
            "side_right_m": self.side_right_m,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Setbacks":
        return cls(
            front_m=payload["front_m"],
            rear_m=payload["rear_m"],
            side_left_m=payload["side_left_m"],
            side_right_m=payload["side_right_m"],
        )

    def describe(self) -> str:
        """One-liner for logs."""
        return (
            f"F={self.front_m} R={self.rear_m} "
            f"L={self.side_left_m} R={self.side_right_m} (m)"
        )

    def difference_from(self, other: "Setbacks") -> dict[str, float]:
        """Signed element-wise comparison: self - other.

        Returns a dict of signed differences. Negative means self is
        smaller (likely a violation if self is user-stated vs other is
        NBC-compliant).

        We return a dict rather than a Setbacks object because
        differences can be negative but Setbacks can't.
        """
        return {
            "front_m": self.front_m - other.front_m,
            "rear_m": self.rear_m - other.rear_m,
            "side_left_m": self.side_left_m - other.side_left_m,
            "side_right_m": self.side_right_m - other.side_right_m,
        }

    def is_at_least(self, other: "Setbacks") -> bool:
        """True if all four sides of self are ≥ corresponding side of other.

        Used to check compliance: user_stated.is_at_least(nbc_compliant)
        returns True when the user is compliant on every side.
        """
        return (
            self.front_m >= other.front_m
            and self.rear_m >= other.rear_m
            and self.side_left_m >= other.side_left_m
            and self.side_right_m >= other.side_right_m
        )
