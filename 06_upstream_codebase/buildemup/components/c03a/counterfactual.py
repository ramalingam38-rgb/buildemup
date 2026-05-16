"""
BuildemUp† — Component 3a Session 5: counterfactual builder.

Per locked S5 SPEC v1.0 (formerly DRAFT v0.2 — locked after critique
round 1 incorporated patches P1–P4).

Public API:
    build_counterfactual(decision) -> CounterfactualSummary

Pure function. Reads a single ExtremeDecision and produces the family-
discussion summary surfaced on the final ResolvedBrief screen. Per parent
spec § 4.6 and v0.2.1 critique #5: max 2 alternatives per decision,
neutral framing, Preview Mode kept (honesty over comfort).

v1.0 includes critique-round-1 patches:
  - P1 (Drawback 2): acronym-preserving casing in _format_would_have

Design references:
  - parent C3a spec § 4.6 (Counterfactual generation)
  - parent C3a spec § 3.1 (CounterfactualSummary dataclass)
  - locked S5 spec § 3.1, § 4 Q1–Q11, § 5
  - critique round 1 drawbacks 2 (P1), 4 (rejected), 11 (B-023)

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.domain.extreme_case import (
    CounterfactualSummary,
    ExtremeDecision,
    ResolutionOption,
)


# ─────────────────────────────────────────────────────────────────────
# _format_would_have — neutral phrasing helper (§5.2, Q4 + Q5 + P1)
# ─────────────────────────────────────────────────────────────────────

def _format_would_have(opt: ResolutionOption) -> str:
    """Render the "would have ..." phrase for a counterfactual alternative.

    Two cases per parent spec § 4.6 + locked S5 spec Q4 / Q5:

      1. Preview Mode option (is_preview_mode=True):
         Use the verbatim sentence from parent spec § 4.6. Preview Mode
         needs explicit phrasing about its non-buildable nature so the
         family-discussion screen doesn't imply Preview Mode was a
         buildable alternative.

      2. Non-Preview option:
         Use f"would have {summary}" where summary is opt.impact_summary
         with first-character-only lowercasing applied (P1).

    P1 ACRONYM PRESERVATION (Drawback 2 from critique round 1):
      Original v0.1 used impact_summary.lower() which mangles acronyms
      like "TNCDBR variance required" → "tncdbr variance required".
      v0.2 / v1.0 uses a heuristic: lowercase the first character only if
      the second character is lowercase (signals normal Title Case).
      Leave casing alone if the first two characters are both uppercase
      (signals an acronym like "TNCDBR" or "NBC").

      Trade-off: "TNCDBR variance" → "would have TNCDBR variance"
      reads slightly stilted but preserves the acronym. The reverse
      (mangling the acronym) is worse for reader trust.
    """
    if opt.is_preview_mode:
        return (
            "would have given you a watermarked layout for your "
            "original brief, useful for family discussion but not "
            "buildable"
        )

    summary = opt.impact_summary
    if summary and summary[0].isupper():
        # P1: only adjust if second char is lowercase (normal Title Case);
        # leave acronyms (TNCDBR, NBC, ...) intact.
        if len(summary) >= 2 and summary[1].islower():
            summary = summary[0].lower() + summary[1:]
        # else: starts with acronym; leave as-is.

    return f"would have {summary}"


# ─────────────────────────────────────────────────────────────────────
# Public API (§3.1)
# ─────────────────────────────────────────────────────────────────────

def build_counterfactual(decision: ExtremeDecision) -> CounterfactualSummary:
    """Build a per-decision counterfactual summary.

    Per parent spec § 4.6 algorithm:
      1. Find the chosen option in decision.presented_options.
      2. Build candidates from all OTHER options.
      3. Sort: recommended first, then by abs distance from chosen
         on space_impact_sqft. Stable sort preserves input order for
         ties (Q2).
      4. Take top 2 candidates (cap enforced by
         CounterfactualSummary.__post_init__ but pre-trimmed here).
      5. Return CounterfactualSummary with chosen_outcome =
         chosen.impact_summary, alternatives tuple, default framing line.

    Pure function — no side effects.

    Args:
        decision: the ExtremeDecision to summarize.

    Returns:
        CounterfactualSummary with alternatives ≤ 2.

    Raises:
        ValueError — if chosen_option_id is not in presented_options.
            Defensive only; ExtremeDecision.__post_init__ catches this
            normally at construction time.
    """
    # Step 1: find chosen option
    chosen = next(
        (
            o for o in decision.presented_options
            if o.option_id == decision.chosen_option_id
        ),
        None,
    )
    if chosen is None:
        # Defensive — shouldn't happen because ExtremeDecision.__post_init__
        # validates this. But surface a clear error if it somehow does.
        raise ValueError(
            f"build_counterfactual: chosen_option_id "
            f"{decision.chosen_option_id!r} not in "
            f"presented_options={[o.option_id for o in decision.presented_options]!r}"
        )

    # Contract assertion (post-critique-round-2 D1):
    # ResolutionOption.space_impact_sqft is typed as `int` (non-Optional)
    # in S1's domain layer. The distance-based ranking below assumes this.
    # If the type ever relaxes to Optional[int], the subtraction crashes
    # silently. Fail loudly instead, with a pointer to the fix location.
    for o in decision.presented_options:
        if not isinstance(o.space_impact_sqft, int):
            raise TypeError(
                f"S5 contract violated: ResolutionOption "
                f"{o.option_id!r} has space_impact_sqft="
                f"{o.space_impact_sqft!r} (type "
                f"{type(o.space_impact_sqft).__name__}); int expected. "
                f"If this type was deliberately relaxed in S1, update "
                f"build_counterfactual's ranking key in counterfactual.py."
            )

    # Step 2: candidates = everything except the chosen one
    candidates = [
        opt for opt in decision.presented_options
        if opt.option_id != decision.chosen_option_id
    ]

    # Step 3: sort — recommended first, then by abs distance from chosen
    # Python's sort is stable, so equal-key candidates preserve their
    # original presented_options order (Q2 tie-breaker).
    chosen_impact = chosen.space_impact_sqft
    candidates.sort(
        key=lambda o: (
            not o.recommended,                              # False sorts first → recommended first
            -abs(o.space_impact_sqft - chosen_impact),       # larger distance first
        )
    )

    # Step 4: take top 2 and format
    alternatives = tuple(
        (opt.option_id, opt.description, _format_would_have(opt))
        for opt in candidates[:2]
    )

    # Step 5: build the summary (framing_line uses default constant)
    return CounterfactualSummary(
        case_id=decision.case_id,
        chosen_option_id=decision.chosen_option_id,
        chosen_outcome=chosen.impact_summary,
        alternatives=alternatives,
    )
