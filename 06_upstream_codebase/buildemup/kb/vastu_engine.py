"""
BuildemUp† — Vastu Engine (v0.4 stub)
======================================

Optional feature, not compulsory. Many Indian families care about Vastu;
many don't. We support it as an opt-in check, not a constraint that
shapes the design.

Scope of v0.4 stub:
  - Direction-based room placement scoring (cardinal directions matter)
  - 5 high-impact rules from Manasara / Mayamata
  - Returns a Vastu compliance report (NOT a refusal — Vastu is preference)

What this is NOT:
  - A traditional Vastu Shastra calculator (those need site-specific
    astrological inputs like nakshatra, brahmasthan calculation)
  - A constraint that prevents the engine from generating layouts
  - A substitute for a Vastu consultant (they earn ₹15-50K for site visit)

The product position: "Here's how your plan scores on common Vastu rules.
We don't optimize for it by default — turn that on if you want."

Sources:
  - Manasara — ancient Sanskrit text on architecture
  - Mayamata — building proportions and orientation
  - Modern Vastu summaries from NBC 2016 informative annex
  - Online Vastu consultant aggregated rules (for what families ask about)

†= placeholder name marker.

KB_VERSION: "Vastu_Stub_2026_v1"
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


KB_VERSION = "Vastu_Stub_2026_v1"


# ─────────────────────────────────────────────────────────────────────────
# Direction enum
# ─────────────────────────────────────────────────────────────────────────
class Direction(str, Enum):
    """The 8 cardinal + intercardinal directions used in Vastu."""
    NORTH = "N"
    NORTHEAST = "NE"
    EAST = "E"
    SOUTHEAST = "SE"
    SOUTH = "S"
    SOUTHWEST = "SW"
    WEST = "W"
    NORTHWEST = "NW"


class RoomType(str, Enum):
    """Room types relevant to Vastu rules."""
    POOJA_ROOM = "pooja_room"
    KITCHEN = "kitchen"
    MASTER_BEDROOM = "master_bedroom"
    GUEST_BEDROOM = "guest_bedroom"
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    TOILET = "toilet"
    BATHROOM = "bathroom"
    STAIRCASE = "staircase"
    ENTRANCE = "entrance"
    STORE = "store"
    STUDY = "study"


# ─────────────────────────────────────────────────────────────────────────
# Vastu rules (5 high-impact ones for v0.4)
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class VastuRule:
    """One Vastu rule."""
    rule_id: str
    room_type: RoomType
    preferred_directions: tuple[Direction, ...]
    avoid_directions: tuple[Direction, ...]
    importance: str          # "high" | "medium" | "low"
    rationale: str           # Plain language explanation


# Top 5 rules covering what most Indian families care about.
# Deliberately limited — full Vastu has 100+ rules, most families care about
# pooja, kitchen, master bedroom, toilets, entrance.
VASTU_RULES = (
    VastuRule(
        rule_id="pooja_NE",
        room_type=RoomType.POOJA_ROOM,
        preferred_directions=(Direction.NORTHEAST, Direction.EAST),
        avoid_directions=(Direction.SOUTH, Direction.SOUTHWEST),
        importance="high",
        rationale=(
            "Pooja room placement is the most universally requested Vastu "
            "constraint. NE is considered the most sacred direction "
            "(Ishanya). E (sunrise) is also auspicious. Avoid SW (Pitru) "
            "and S (associated with Yama)."
        ),
    ),
    VastuRule(
        rule_id="kitchen_SE",
        room_type=RoomType.KITCHEN,
        preferred_directions=(Direction.SOUTHEAST, Direction.NORTHWEST),
        avoid_directions=(Direction.NORTHEAST, Direction.SOUTHWEST),
        importance="high",
        rationale=(
            "Kitchen in SE corner (Agni — fire element). NW is acceptable "
            "secondary. AVOID NE (sacred direction; fire conflicts with "
            "water element) and SW (Pitru zone)."
        ),
    ),
    VastuRule(
        rule_id="master_bedroom_SW",
        room_type=RoomType.MASTER_BEDROOM,
        preferred_directions=(Direction.SOUTHWEST,),
        avoid_directions=(Direction.NORTHEAST,),
        importance="high",
        rationale=(
            "Master bedroom in SW gives stability and earth-element grounding. "
            "AVOID NE (head of family in sacred direction is considered "
            "inauspicious for personal stability)."
        ),
    ),
    VastuRule(
        rule_id="toilet_NW_SE",
        room_type=RoomType.TOILET,
        preferred_directions=(Direction.NORTHWEST, Direction.WEST),
        avoid_directions=(Direction.NORTHEAST, Direction.SOUTHEAST,
                          Direction.SOUTH),
        importance="medium",
        rationale=(
            "Toilets in NW or W are acceptable. AVOID NE (defiles sacred "
            "direction), SE (conflicts with kitchen fire element), and S "
            "(Yama — south is generally avoided for elimination spaces)."
        ),
    ),
    VastuRule(
        rule_id="entrance_NE_E_N",
        room_type=RoomType.ENTRANCE,
        preferred_directions=(Direction.NORTHEAST, Direction.EAST,
                              Direction.NORTH),
        avoid_directions=(Direction.SOUTHWEST, Direction.SOUTH),
        importance="high",
        rationale=(
            "Main entrance facing N, E, or NE is considered most auspicious "
            "(receives morning sun, sacred direction). AVOID S and SW "
            "entrances per most Vastu traditions."
        ),
    ),
)


# ─────────────────────────────────────────────────────────────────────────
# Compliance check
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class VastuComplianceItem:
    """One room's compliance with the relevant Vastu rule."""
    room_type: RoomType
    actual_direction: Direction
    rule: VastuRule
    is_compliant: bool             # In a preferred direction
    is_problematic: bool           # In an avoided direction
    score: int                     # 100=preferred, 50=neutral, 0=avoided
    user_message: str


@dataclass(frozen=True)
class VastuReport:
    """Aggregate Vastu compliance report for a layout."""
    items: tuple[VastuComplianceItem, ...]
    overall_score: int             # 0-100
    overall_message: str
    enabled: bool                  # Whether user opted in for Vastu

    def format_for_user(self) -> str:
        """User-facing format with PROMINENT separation disclosure.

        v0.5: Per the v0.4 review, Vastu output must NEVER be confused
        with structural/engineering output. This method always prepends
        a clear separation banner.
        """
        lines = [
            "─" * 70,
            "VASTU ADVISORY (separate from structural design)",
            "─" * 70,
            "",
            "⚠ IMPORTANT: Vastu compliance is a CULTURAL/PERSONAL preference,",
            "  NOT engineering. Do NOT modify the structural layout based on",
            "  Vastu suggestions without consulting your structural engineer.",
            "  Moving a kitchen, bathroom, or pooja room can change water tank",
            "  placement, plumbing routing, and wall loads in ways that affect",
            "  cost and safety. Engineer review is required for ANY layout",
            "  change driven by Vastu.",
            "",
        ]
        if not self.enabled:
            lines.append("Vastu check is DISABLED (opt-in feature).")
            lines.append("─" * 70)
            return "\n".join(lines)

        lines.append(self.overall_message)
        lines.append("")
        for item in self.items:
            lines.append(f"  • {item.user_message}")
        lines.append("")
        lines.append(
            "These are CULTURAL preferences, not engineering requirements. "
            "Many families don't follow Vastu. Many do, partially. Some "
            "follow it strictly. Your call."
        )
        lines.append("─" * 70)
        return "\n".join(lines)


def check_vastu_compliance(
    room_directions: dict[RoomType, Direction],
    enabled: bool = True,
) -> VastuReport:
    """Score a layout against Vastu rules.

    Args:
        room_directions: which direction each room is in. Only rooms
                         present in this dict are checked.
        enabled: if False, returns an empty report (Vastu opted out).

    Returns:
        VastuReport with per-room scores + overall score.
    """
    if not enabled:
        return VastuReport(
            items=(),
            overall_score=0,
            overall_message="Vastu compliance check is disabled (opt-in feature).",
            enabled=False,
        )

    items: list[VastuComplianceItem] = []
    for rule in VASTU_RULES:
        actual = room_directions.get(rule.room_type)
        if actual is None:
            continue  # Room not in layout — skip
        is_preferred = actual in rule.preferred_directions
        is_avoided = actual in rule.avoid_directions
        if is_preferred:
            score = 100
            msg = (
                f"{rule.room_type.value.replace('_', ' ').title()} in "
                f"{actual.value} — VASTU COMPLIANT (preferred direction)."
            )
        elif is_avoided:
            score = 0
            msg = (
                f"{rule.room_type.value.replace('_', ' ').title()} in "
                f"{actual.value} — Vastu concern (this direction is "
                f"traditionally avoided). {rule.rationale}"
            )
        else:
            score = 50
            msg = (
                f"{rule.room_type.value.replace('_', ' ').title()} in "
                f"{actual.value} — neutral (neither preferred nor avoided)."
            )
        items.append(VastuComplianceItem(
            room_type=rule.room_type,
            actual_direction=actual,
            rule=rule,
            is_compliant=is_preferred,
            is_problematic=is_avoided,
            score=score,
            user_message=msg,
        ))

    if not items:
        overall = 0
        overall_msg = "No Vastu-relevant rooms specified for compliance check."
    else:
        overall = int(sum(i.score for i in items) / len(items))
        if overall >= 80:
            overall_msg = (
                f"Vastu compliance: {overall}/100. Strong alignment with "
                f"common Vastu preferences."
            )
        elif overall >= 50:
            overall_msg = (
                f"Vastu compliance: {overall}/100. Partial alignment. "
                f"Some rooms in non-preferred directions."
            )
        else:
            overall_msg = (
                f"Vastu compliance: {overall}/100. Layout has multiple "
                f"Vastu concerns. Consider repositioning if Vastu is a priority."
            )

    return VastuReport(
        items=tuple(items),
        overall_score=overall,
        overall_message=overall_msg,
        enabled=True,
    )


# ─────────────────────────────────────────────────────────────────────────
# Notes for Component integration
# ─────────────────────────────────────────────────────────────────────────
DISCLAIMER = (
    "Vastu compliance check is OPTIONAL. We don't optimize layouts for "
    "Vastu by default — many families don't follow it strictly. If you "
    "do, enable this check and we'll flag concerns. For deep Vastu "
    "alignment (including astrological/site-specific rules like brahmasthan "
    "calculation, nakshatra-based dates), a Vastu consultant is recommended "
    "(typical fee ₹15-50K for site visit + report)."
)
