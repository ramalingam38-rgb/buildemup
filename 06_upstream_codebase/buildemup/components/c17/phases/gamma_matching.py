"""
C17 — Phase γ — Quote-line ↔ BOQ-item matching (4 tiers)
==========================================================

Input:  PhaseAlphaOutput (canonical quote lines + decomposition)
        PhaseBetaOutput  (ProjectBOQ)
Output: MatchCandidateSet — one entry per quote line, with tier and basis

The 4 tiers per spec § 2.2:
    'high'                              — IS code match OR brand+grade exact
    'medium'                            — brand-only / grade-only + unit OK
    'low'                               — label fuzzy + unit OK
    'human_verification_recommended'    — below 'low' but above hard floor
                                          (Levenshtein > 0.3 AND < 0.5)

Plus 'unmatched' (below 0.3 Levenshtein, no candidate).

Per spec § 6 hard ceilings: Levenshtein < 0.4 emits no candidate at all;
the boundary is therefore [0.3, 0.5) for human_verification, [0.5, 0.85)
for low/medium gradations. (The hard floor is 0.4 for Levenshtein
similarity; the human-review tier sits BELOW that hard floor as a
last-chance signal that doesn't earn a price-signal verdict — R5.)

NB: We use difflib.SequenceMatcher.ratio() as a stdlib-only fuzzy-match
proxy for Levenshtein. It's not literally Levenshtein but is the
standard Python "looks-like" measure and is what the spec's threshold
table is calibrated against (B-C17-FUZZY-MATCH-CALIBRATION refines).

Rule 11 self-analysis:
  1. Multi-match ambiguity: one quote line may match >1 BOQ items
     with similar scores. We pick the highest-scoring; if the top 2
     scores are within 0.05 of each other AND the top score is in
     ['medium', 'high'] tier, we DOWNGRADE to 'low' — ambiguity
     penalty. If still ambiguous and >5 candidates within window,
     raise MatchingAmbiguityError.
  2. Unit-compatibility check: 'cum' vs 'cft' both volume but
     incompatible without conversion. v1.0 requires exact normalised
     unit equality. B-C17-UNIT-CONVERSION-ADAPTER refines.
  3. Lump-sum lines bypass matching entirely — they don't have
     unit/qty/rate to compare. They surface as LumpSumIndicator in
     phase ζ. Phase γ skips them.
  4. R5 enforcement is delayed to phase δ — phase γ emits the tier
     and lets δ apply the signal-downgrade.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Literal, Optional, Tuple

from buildemup.components.c17.contracts import ProjectBOQ, ProjectBOQItem
from buildemup.components.c17.errors import MatchingAmbiguityError
from buildemup.components.c17.phases.alpha_canonicalize import (
    PhaseAlphaOutput,
    QuoteLineCanonical,
    _canon_label,
)
from buildemup.components.c17.phases.beta_boq_assembly import PhaseBetaOutput
from buildemup.components.c17.versioning import (
    LEVENSHTEIN_HARD_CEILING,
    MATCH_TIER_HIGH_THRESHOLD,
    MATCH_TIER_LOW_THRESHOLD,
    MATCH_TIER_MEDIUM_THRESHOLD,
    MATCH_TIER_HUMAN_REVIEW_THRESHOLD,
)


_AMBIGUITY_DOWNGRADE_WINDOW = 0.05      # top-2 within this → downgrade
_AMBIGUITY_HARD_LIMIT_COUNT = 5         # within the high-tier window
_AMBIGUITY_HARD_LIMIT_WINDOW = 0.10


# ============================================================
# § 1 — INTERNAL CANDIDATE TYPES
# ============================================================

MatchTier = Literal["high", "medium", "low", "human_verification_recommended", "unmatched"]


@dataclass(frozen=True)
class MatchCandidate:
    """One (quote_line, boq_item) candidate. Phase γ emits the best
    candidate per quote line (or 'unmatched' if no candidate above
    LEVENSHTEIN_HARD_CEILING)."""
    line_id:             str
    boq_id:              str
    score:               float           # raw fuzzy ratio
    tier:                MatchTier
    basis:               Tuple[str, ...]   # match_basis values


@dataclass(frozen=True)
class PhaseGammaOutput:
    """Bundled output of phase γ."""
    candidates:          Tuple[MatchCandidate, ...]
    unmatched_line_ids:  Tuple[str, ...]
    lump_sum_line_ids:   Tuple[str, ...]


# ============================================================
# § 2 — PHASE γ ENTRY
# ============================================================

def run_phase_gamma(
    alpha_output: PhaseAlphaOutput,
    beta_output:  PhaseBetaOutput,
) -> PhaseGammaOutput:
    """Phase γ entry point."""
    boq = beta_output.project_boq

    # Pre-canonicalize BOQ labels once for performance.
    boq_label_cache: list[tuple[ProjectBOQItem, str]] = [
        (it, _canon_label(it.label)) for it in boq.items
    ]

    candidates: List[MatchCandidate] = []
    unmatched: List[str] = []
    lump_sums: List[str] = []

    for ql in alpha_output.canonical_lines:
        if ql.is_lump_sum:
            lump_sums.append(ql.line_id)
            continue

        cand = _match_one(ql, boq_label_cache)
        if cand is None:
            unmatched.append(ql.line_id)
        else:
            candidates.append(cand)

    return PhaseGammaOutput(
        candidates=tuple(candidates),
        unmatched_line_ids=tuple(unmatched),
        lump_sum_line_ids=tuple(lump_sums),
    )


# ============================================================
# § 3 — MATCH ONE QUOTE LINE
# ============================================================

def _match_one(
    ql: QuoteLineCanonical,
    boq_label_cache: list[tuple[ProjectBOQItem, str]],
) -> Optional[MatchCandidate]:
    """Find the best BOQ candidate for one quote line.

    Returns None when no candidate clears LEVENSHTEIN_HARD_CEILING.

    Scoring strategy:
      1. Try IS-code match — if quote has an "IS xxxx" token in its
         canonical label and a BOQ item has matching is_code, that's
         a tier='high' with basis=('is_code_match', ...).
      2. Try brand+grade exact (canonical_label contains both
         tokens) — tier='high', basis=('brand_grade_exact', ...).
      3. Else use SequenceMatcher.ratio() on canonical labels;
         combine with unit-compatibility into a tier."""
    # 1. IS-code rule
    is_code_in_ql = _extract_is_code(ql.canonical_label)
    if is_code_in_ql:
        for it, _ in boq_label_cache:
            if it.is_code and it.is_code.lower() == is_code_in_ql.lower():
                if _unit_compatible(ql.unit_normalised, it.unit):
                    return MatchCandidate(
                        line_id=ql.line_id,
                        boq_id=it.boq_id,
                        score=0.95,
                        tier="high",
                        basis=("is_code_match", "unit_compatible"),
                    )
                return MatchCandidate(
                    line_id=ql.line_id,
                    boq_id=it.boq_id,
                    score=0.85,
                    tier="medium",       # unit mismatch demotes
                    basis=("is_code_match",),
                )

    # 2. Brand + grade exact in the label
    brand_grade_hits: list[tuple[ProjectBOQItem, float]] = []
    for it, _ in boq_label_cache:
        if not it.brand and not it.grade:
            continue
        score = _brand_grade_score(ql.canonical_label, it.brand, it.grade)
        if score > 0:
            brand_grade_hits.append((it, score))

    if brand_grade_hits:
        brand_grade_hits.sort(key=lambda t: -t[1])
        best_it, best_score = brand_grade_hits[0]
        if best_score >= 1.0 and _unit_compatible(ql.unit_normalised, best_it.unit):
            return MatchCandidate(
                line_id=ql.line_id,
                boq_id=best_it.boq_id,
                score=0.93,
                tier="high",
                basis=("brand_grade_exact", "unit_compatible"),
            )
        elif best_score >= 0.5:
            # Brand-only OR grade-only
            unit_ok = _unit_compatible(ql.unit_normalised, best_it.unit)
            basis = (
                "brand_only" if best_score == 0.5 else "grade_only",
            )
            if unit_ok:
                basis = basis + ("unit_compatible",)
            return MatchCandidate(
                line_id=ql.line_id,
                boq_id=best_it.boq_id,
                score=0.78,
                tier="medium" if unit_ok else "low",
                basis=basis,
            )

    # 3. Pure fuzzy label match
    fuzzy_hits: list[tuple[ProjectBOQItem, float]] = []
    for it, it_canon in boq_label_cache:
        ratio = SequenceMatcher(None, ql.canonical_label, it_canon).ratio()
        if ratio >= LEVENSHTEIN_HARD_CEILING:
            fuzzy_hits.append((it, ratio))

    if not fuzzy_hits:
        # Try the human-review-tier window: 0.3 ≤ ratio < 0.4
        for it, it_canon in boq_label_cache:
            ratio = SequenceMatcher(None, ql.canonical_label, it_canon).ratio()
            if MATCH_TIER_HUMAN_REVIEW_THRESHOLD <= ratio < LEVENSHTEIN_HARD_CEILING:
                fuzzy_hits.append((it, ratio))
        if fuzzy_hits:
            fuzzy_hits.sort(key=lambda t: -t[1])
            best_it, best_score = fuzzy_hits[0]
            return MatchCandidate(
                line_id=ql.line_id,
                boq_id=best_it.boq_id,
                score=best_score,
                tier="human_verification_recommended",
                basis=("label_fuzzy_low",),
            )
        return None  # truly unmatched

    fuzzy_hits.sort(key=lambda t: -t[1])

    # Ambiguity guard
    if len(fuzzy_hits) > _AMBIGUITY_HARD_LIMIT_COUNT:
        top = fuzzy_hits[0][1]
        within = [h for h in fuzzy_hits if (top - h[1]) <= _AMBIGUITY_HARD_LIMIT_WINDOW]
        if len(within) > _AMBIGUITY_HARD_LIMIT_COUNT:
            raise MatchingAmbiguityError(
                f"Phase γ: line[{ql.line_id}] has {len(within)} BOQ "
                f"candidates within {_AMBIGUITY_HARD_LIMIT_WINDOW} of "
                f"the top score {top:.3f}. Cannot disambiguate.",
                line_id=ql.line_id,
                candidate_count=len(within),
            )

    best_it, best_score = fuzzy_hits[0]
    unit_ok = _unit_compatible(ql.unit_normalised, best_it.unit)

    # Top-2 ambiguity → downgrade one tier
    downgrade = False
    if len(fuzzy_hits) >= 2:
        second_score = fuzzy_hits[1][1]
        if (best_score - second_score) <= _AMBIGUITY_DOWNGRADE_WINDOW:
            downgrade = True

    tier = _tier_from_score(best_score)
    if downgrade:
        tier = _downgrade_tier(tier)
    if not unit_ok:
        # Unit mismatch is a strong signal; downgrade once more
        tier = _downgrade_tier(tier)

    basis_list: list[str] = []
    if best_score >= MATCH_TIER_HIGH_THRESHOLD:
        basis_list.append("label_fuzzy_high")
    elif best_score >= MATCH_TIER_MEDIUM_THRESHOLD:
        basis_list.append("label_fuzzy_medium")
    else:
        basis_list.append("label_fuzzy_low")
    if unit_ok:
        basis_list.append("unit_compatible")

    return MatchCandidate(
        line_id=ql.line_id,
        boq_id=best_it.boq_id,
        score=best_score,
        tier=tier,
        basis=tuple(basis_list),
    )


# ============================================================
# § 4 — HELPERS
# ============================================================

_IS_CODE_RE = __import__("re").compile(r"\bis\s+(\d{3,5}(?:[-:]\d{2,4})?)\b")


def _extract_is_code(canonical_label: str) -> Optional[str]:
    m = _IS_CODE_RE.search(canonical_label)
    if not m:
        return None
    return f"IS {m.group(1)}"


def _brand_grade_score(
    canonical_label: str,
    brand: Optional[str],
    grade: Optional[str],
) -> float:
    """Returns 1.0 if both brand and grade appear in the label,
    0.5 if only one, 0.0 if neither."""
    if not brand and not grade:
        return 0.0
    score = 0.0
    if brand and brand.lower() in canonical_label:
        score += 0.5
    if grade and grade.lower() in canonical_label:
        score += 0.5
    return score


def _unit_compatible(quote_unit: str, boq_unit: str) -> bool:
    """v1.0: exact normalised match. B-C17-UNIT-CONVERSION-ADAPTER
    expands. Empty quote unit (lump-sum proximate line) → compatible
    only if the BOQ unit is also empty (extreme edge case)."""
    return quote_unit == boq_unit


def _tier_from_score(score: float) -> MatchTier:
    if score >= MATCH_TIER_HIGH_THRESHOLD:
        return "high"
    if score >= MATCH_TIER_MEDIUM_THRESHOLD:
        return "medium"
    if score >= MATCH_TIER_LOW_THRESHOLD:
        return "low"
    return "human_verification_recommended"


def _downgrade_tier(tier: MatchTier) -> MatchTier:
    return {
        "high":   "medium",
        "medium": "low",
        "low":    "human_verification_recommended",
        "human_verification_recommended": "human_verification_recommended",
        "unmatched": "unmatched",
    }[tier]  # type: ignore[index]
