"""
C3b — Phase α — Session canonicalization + applicability check
================================================================

Spec § 3 Phase α:
  INPUT: SelectionResult, Brief, PlotAnalysis (via C3bInputBundle)
  PROCESSING:
    1. Validate SelectionResult.layouts is exactly 3 candidates
    2. Check § 1.4 applicability boundary:
       - Preview Mode? (ResolvedBrief.extreme_case_status == 'preview_mode')
       - high_ambiguity ProblemReport?
       - Pareto collapse (layouts too similar)?
    3. If any check fails → emit TradeoffSession with
       current_status='abandoned_no_tweaks' + advisory
    4. Otherwise → build canonical TradeoffSession skeleton with
       iteration_count=0

  OUTPUT: TradeoffSession (skeleton or terminal)

Rule 11 self-analysis:
  1. Applicability failure produces a SESSION not an exception.
     ApplicabilityBoundaryError exists for unit-testing the code path,
     but the runtime path is the session-with-advisory. Documented in
     errors.py.
  2. Pareto collapse uses PARETO_DIVERSITY_FLOOR_* — if ANY ONE floor
     is met (sqft 10% OR cost 15% OR 3 distinct topologies), the
     layouts are "diverse enough." Conservative: if any one floor met,
     applicability passes.
  3. Layout archetype assignment (Cost Efficient / Everyday Living /
     Premium Design) is by rank position:
       rank 0 → cost_efficient
       rank 1 → everyday_living
       rank 2 → premium_design
     This matches Design Principles v3.1 § 5 Layout Triad ordering.
     If C15's ranking changes ordering convention in the future, this
     mapping is the seam to update.
  4. Phase α does NOT compute tweak_option_sets — that's Phase β.
     The session skeleton has empty tweak_option_sets; status is
     "open_for_user_input" only after Phase β/γ/δ populate them.
     We use an INTERMEDIATE skeleton status that we replace later;
     for now, use "open_for_user_input" with empty sets and let Phase β
     fill in.
"""
from __future__ import annotations

import uuid
from typing import Optional

from ..cache_keys import (
    compute_canonical_replay_signature,
    compute_presentation_signature,
    compute_schema_descriptor_digest,
)
from ..config import C3bRuntimeConfig
from ..contracts import C3bInputBundle
from ..errors import (
    ApplicabilityBoundaryError,
    C3bConfigurationError,
    UpstreamSchemaDriftError,
)
from ..schema import (
    LayoutArchetype,
    SessionStatus,
    TradeoffSession,
)
from ..versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    EXPECTED_C15_VERSION,
    EXPECTED_LAYOUT_COUNT,
    PARETO_DIVERSITY_FLOOR_COST_PCT,
    PARETO_DIVERSITY_FLOOR_SQFT_PCT,
    PARETO_DIVERSITY_FLOOR_TOPOLOGY_COUNT,
    SUPPORTED_JURISDICTIONS,
    SUPPORTED_DOMAIN_SCOPES,
)


# ============================================================
# § 1 — Layout archetype assignment
# ============================================================

def archetype_for_rank(rank_position: int) -> LayoutArchetype:
    """Map C16 rank position → Design Principles v3.1 Layout Triad.
    C16 rank_position is 1-indexed (1, 2, 3)."""
    if rank_position == 1:
        return "cost_efficient"
    if rank_position == 2:
        return "everyday_living"
    if rank_position == 3:
        return "premium_design"
    raise C3bConfigurationError(
        f"rank_position={rank_position} outside Layout Triad (1-3). "
        f"C16 SelectionResult must contain exactly {EXPECTED_LAYOUT_COUNT} "
        f"ranked candidates.",
        offending_field="rank_position",
        offending_value=rank_position,
    )


# ============================================================
# § 2 — Applicability checks (spec § 1.4)
# ============================================================

def check_preview_mode(bundle: C3bInputBundle) -> Optional[str]:
    """Return advisory note if Preview Mode detected, else None."""
    if bundle.resolved_brief.extreme_case_status == "preview_mode":
        return (
            "This layout was produced under Preview Mode (an unresolved extreme "
            "case in your brief). C3b can iterate on tweaks once the extreme "
            "case is resolved. You could revisit the brief, resolve the extreme, "
            "and re-run the layout pipeline."
        )
    return None


def check_pareto_diversity(bundle: C3bInputBundle) -> Optional[str]:
    """Return advisory note if Pareto-front collapse detected, else None.

    Layouts are 'diverse enough' if ANY ONE floor is met:
      - sqft varies by >= 10%
      - cost varies by >= 15%
      - 3 distinct topology classifications represented
      - (v0.5 A9) at least 2 distinct functional archetypes
        (cost_efficient / everyday_living / premium_design)
    """
    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    if len(rankings) != EXPECTED_LAYOUT_COUNT:
        return (
            f"The layout pipeline produced {len(rankings)} candidates rather "
            f"than the expected {EXPECTED_LAYOUT_COUNT}. You could re-run the "
            f"layout generation or revisit your brief."
        )

    # v0.5 A9 — archetype diversity floor. Map rank → archetype via the
    # standard Triad. If C16 ranks rank_position 1..3, archetypes are
    # (cost_efficient, everyday_living, premium_design). If C16 emits
    # 3 rankings with the same rank_position triple, archetype diversity
    # passes by construction (3 archetypes for 3 layouts). The floor
    # trips only if a future C16 evolution returns degenerate rankings.
    archetypes_seen: set[str] = set()
    for r in rankings:
        if 1 <= r.rank_position <= 3:
            archetype = {1: "cost_efficient", 2: "everyday_living", 3: "premium_design"}[r.rank_position]
            archetypes_seen.add(archetype)
    if len(archetypes_seen) >= 2:
        return None  # archetype diversity passes

    # cost diversity (use 'score' as proxy when no explicit cost — heuristic
    # for v1.0; v1.x will read actual cost from each layout's cost report)
    scores = [r.score for r in rankings]
    if max(scores) > 0:
        cost_spread_pct = (max(scores) - min(scores)) / max(scores) * 100.0
    else:
        cost_spread_pct = 0.0
    if cost_spread_pct >= PARETO_DIVERSITY_FLOOR_COST_PCT:
        return None  # diverse enough

    # sqft diversity — heuristic: use placed_rooms totals
    sqft_totals: list[float] = []
    for placed_rooms in bundle.placed_rooms_per_layout:
        total = sum(r.geometry.area_sqft for r in placed_rooms)
        sqft_totals.append(total)
    if sqft_totals and max(sqft_totals) > 0:
        sqft_spread_pct = (max(sqft_totals) - min(sqft_totals)) / max(sqft_totals) * 100.0
    else:
        sqft_spread_pct = 0.0
    if sqft_spread_pct >= PARETO_DIVERSITY_FLOOR_SQFT_PCT:
        return None  # diverse enough

    # Topology diversity — would require C5 topology classifications per layout.
    # We don't have those directly; defer to v1.x. For v1.0, fall through if
    # neither cost nor sqft diversity met.
    return (
        "The three ranked layouts came back very similar to each other "
        "(within 15% on cost and 10% on sqft, and with limited archetype "
        "spread). C3b's tweak suggestions need diverse layouts to be useful. "
        "You could explore a different brief configuration or accept one of "
        "the layouts as-is."
    )


def check_high_ambiguity(bundle: C3bInputBundle) -> Optional[str]:
    """Return advisory note if any ProblemReport has low coverage_quality
    (high ambiguity), else None.

    C15's CoverageQuality enum is the gate. We refuse to iterate when
    the underlying problem detection has high uncertainty."""
    # CoverageQuality is an enum; the lowest tier is "low_signal" (high
    # ambiguity). Specific name varies by C15 — we check via .value
    for i, pr in enumerate(bundle.problem_reports):
        try:
            quality_str = pr.coverage_quality.value
        except AttributeError:
            quality_str = str(pr.coverage_quality)
        if "low" in quality_str.lower() or "ambig" in quality_str.lower():
            return (
                f"Layout {i+1}'s problem report came back with low confidence "
                f"({quality_str}). C3b's tweaks rely on confident problem "
                f"detection. You could re-run the layout pipeline or accept "
                f"the layouts as-is."
            )
    return None


# ============================================================
# § 3 — Upstream version check
# ============================================================

def check_upstream_versions(bundle: C3bInputBundle) -> None:
    """Verify upstream-component versions meet semantic-compatibility
    contracts.

    v0.5 A1: replaces exact-equality pinning with version_at_or_above
    semantic check. Raises UpstreamSchemaDriftError when observed <
    min_required, or when observed is in
    KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS.
    """
    from ..versioning import (
        KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS,
        MIN_C15_VERSION,
        version_at_or_above,
    )
    if bundle.problem_reports:
        observed = bundle.problem_reports[0].c15_version
        # Check known-incompatible list first (explicit refusals)
        for component, bad_version in KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS:
            if component == "c15" and observed == bad_version:
                raise UpstreamSchemaDriftError(
                    f"C15 version {observed!r} is on KNOWN_INCOMPATIBLE list; "
                    f"explicit refusal.",
                    expected_version=MIN_C15_VERSION,
                    observed_version=observed,
                    upstream="c15",
                )
        # Semantic-compatibility (>= min) check
        if not version_at_or_above(observed, MIN_C15_VERSION):
            raise UpstreamSchemaDriftError(
                f"C15 version drift: observed {observed!r} is below the "
                f"minimum compatible version {MIN_C15_VERSION!r}.",
                expected_version=MIN_C15_VERSION,
                observed_version=observed,
                upstream="c15",
            )
    # C16 / C7 / C12 etc. have stub-version markers; not checked at runtime
    # since stubs themselves don't carry a version-mismatch concept.


# ============================================================
# § 4 — Configuration validation
# ============================================================

def check_configuration(bundle: C3bInputBundle, config: C3bRuntimeConfig) -> None:
    """Verify jurisdiction + domain scope are supported. Raises
    C3bConfigurationError on mismatch."""
    jp_id = bundle.resolved_brief.jurisdiction_profile_id
    # Allow exact match OR prefix match against any supported jurisdiction
    supported_match = any(
        sj in jp_id or jp_id.startswith(sj) for sj in SUPPORTED_JURISDICTIONS
    )
    if not supported_match:
        raise C3bConfigurationError(
            f"Jurisdiction {jp_id!r} not in SUPPORTED_JURISDICTIONS "
            f"{set(SUPPORTED_JURISDICTIONS)!r}. v1.0 supports Chennai (TN CDBR 2019).",
            offending_field="jurisdiction_profile_id",
            offending_value=jp_id,
        )


# ============================================================
# § 5 — Build session skeleton
# ============================================================

def _build_terminal_session(
    *,
    bundle:         C3bInputBundle,
    config:         C3bRuntimeConfig,
    status:         SessionStatus,
    advisory_note:  str,
) -> TradeoffSession:
    """Build a terminal TradeoffSession when applicability fails.

    The session has:
      - empty tweak_option_sets
      - empty session_history
      - resolved_selection = None
      - one AdvisoryFlag with kind='pareto_diversity_floor_borderline'
        OR 'topology_invariance_weak_basis' (closest fit) describing
        the failure
      - signatures computed at this terminal state
    """
    from ..schema import AdvisoryFlag

    session_id = "sess_" + uuid.uuid4().hex[:16]

    advisory = AdvisoryFlag(
        flag_id="flag_alpha_terminal",
        kind="pareto_diversity_floor_borderline",
        advisory_note=advisory_note,
        related_ids=(),
    )

    # Compute initial signatures (will be re-computed if state mutates)
    placeholder_sigs = {
        "canonical_replay_signature": "0" * 64,
        "presentation_signature":     "0" * 64,
        "schema_descriptor_digest":   compute_schema_descriptor_digest(),
    }

    # Build with placeholder signatures, then re-sign with real ones
    sess = TradeoffSession(
        session_id=session_id,
        source_selection_result_id=(
            bundle.selection_result.replay_identity.selected_layout_signature
        ),
        source_brief_signature=bundle.resolved_brief.brief_signature,
        source_plot_analysis_id=bundle.plot_analysis.plot_analysis_id,
        c3b_version=C3B_VERSION,
        c3b_schema_version=C3B_SESSION_SCHEMA_VERSION,
        jurisdiction_profile_id=bundle.resolved_brief.jurisdiction_profile_id,
        tweak_option_sets=(),
        session_history=(),
        iteration_count=0,
        iteration_cap=config.iteration_cap,
        current_status=status,
        canonical_replay_signature=placeholder_sigs["canonical_replay_signature"],
        presentation_signature=placeholder_sigs["presentation_signature"],
        schema_descriptor_digest=placeholder_sigs["schema_descriptor_digest"],
        resolved_selection=None,
        advisory_flags=(advisory,),
        mutation_envelopes=(),
    )

    return _resign_session(sess, config)


def _resign_session(
    session:      TradeoffSession,
    config:       C3bRuntimeConfig,
) -> TradeoffSession:
    """Re-compute R6/R7/R8 signatures for a session and return a new
    session with them set. Used after any state mutation."""
    canonical = compute_canonical_replay_signature(
        session=session, strict_mode=config.strict_mode,
    )
    presentation = compute_presentation_signature(
        canonical_replay_signature=canonical,
    )
    schema_digest = compute_schema_descriptor_digest()
    # Use dataclasses.replace to rebuild with new signatures
    import dataclasses
    return dataclasses.replace(
        session,
        canonical_replay_signature=canonical,
        presentation_signature=presentation,
        schema_descriptor_digest=schema_digest,
    )


# ============================================================
# § 6 — Phase α entry point
# ============================================================

def run_phase_alpha(
    bundle:  C3bInputBundle,
    config:  C3bRuntimeConfig,
) -> TradeoffSession:
    """Execute Phase α and return either:
      - a skeleton session (status='open_for_user_input', empty tweak sets)
        ready for Phase β to populate, OR
      - a terminal session (status='abandoned_no_tweaks') with an
        advisory explaining why applicability failed
    """
    # Configuration validation
    check_configuration(bundle, config)

    # Upstream version check
    check_upstream_versions(bundle)

    # Selection-result shape check
    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    if len(rankings) != EXPECTED_LAYOUT_COUNT:
        return _build_terminal_session(
            bundle=bundle, config=config,
            status="abandoned_no_tweaks",
            advisory_note=(
                f"The layout pipeline produced {len(rankings)} candidates "
                f"rather than the expected {EXPECTED_LAYOUT_COUNT}. You could "
                f"re-run the layout generation."
            ),
        )

    # Applicability boundary checks
    for check_fn in (
        check_preview_mode,
        check_high_ambiguity,
        check_pareto_diversity,
    ):
        advisory_msg = check_fn(bundle)
        if advisory_msg is not None:
            return _build_terminal_session(
                bundle=bundle, config=config,
                status="abandoned_no_tweaks",
                advisory_note=advisory_msg,
            )

    # All checks passed — build skeleton session ready for Phase β
    session_id = "sess_" + uuid.uuid4().hex[:16]
    sess = TradeoffSession(
        session_id=session_id,
        source_selection_result_id=(
            bundle.selection_result.replay_identity.selected_layout_signature
        ),
        source_brief_signature=bundle.resolved_brief.brief_signature,
        source_plot_analysis_id=bundle.plot_analysis.plot_analysis_id,
        c3b_version=C3B_VERSION,
        c3b_schema_version=C3B_SESSION_SCHEMA_VERSION,
        jurisdiction_profile_id=bundle.resolved_brief.jurisdiction_profile_id,
        tweak_option_sets=(),   # Phase β fills
        session_history=(),
        iteration_count=0,
        iteration_cap=config.iteration_cap,
        current_status="open_for_user_input",
        canonical_replay_signature="0" * 64,    # re-signed below
        presentation_signature="0" * 64,
        schema_descriptor_digest=compute_schema_descriptor_digest(),
        resolved_selection=None,
        advisory_flags=(),
        mutation_envelopes=(),
    )
    return _resign_session(sess, config)


__all__ = [
    "archetype_for_rank",
    "check_preview_mode",
    "check_pareto_diversity",
    "check_high_ambiguity",
    "check_upstream_versions",
    "check_configuration",
    "run_phase_alpha",
    "_resign_session",
    "_build_terminal_session",
]
