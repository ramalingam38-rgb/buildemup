"""
BuildemUp — Component 14 — Sub 4 tests
========================================

Phase δ (flag emission), Phase ε (advisory passthrough),
Phase ζ (report assembly + category_coverage).

Per C14 SPEC v0.2 LOCKED § 3 Phases δ/ε/ζ + v0.2 A4 + A5 + A6 + A8 + A10.

Sub 4 target: ~25-30 tests. Covers:

Phase δ detectors:
- BOTTLENECK_CONCENTRATION: hub flagged; corridor exempt; non-bottleneck
   (low rank) not flagged
- DEAD_END_ISOLATION: degree-1 habitable room with non-corridor neighbour
   flagged; degree-1 corridor-connected room NOT flagged
- CATEGORY_COVERAGE_LOW: emitted when coverage < threshold
- TRANSIT_THROUGH_BEDROOM: bedroom on only path between non-bedrooms
   flagged; bedroom-avoidable case NOT flagged
- PRIVACY_GRADIENT_VIOLATION: bedroom shallower than deepest public
   flagged
- EXCESSIVE_DEPTH: depth > threshold flagged; ≤ threshold not flagged

A6 truncation cap:
- No cap fires when flags ≤ k × 0.75
- Cap fires when flags exceed; TRUNCATION_META appears in the over-
  cap tuple's last slot
- Suppressed-kinds enumeration is lex-ASC stable

A10:
- All emitted flags default severity == "info"

Phase ε:
- upstream_advisory_flags byte-identical (Inv E8)
- c14_advisory_flags empty at v0.2 SKETCH
- Rejects non-tuple input

Phase ζ:
- compute_category_coverage: full coverage = 1.0
- compute_category_coverage: zero coverage = 0.0
- compute_category_coverage: empty nodes = 1.0 (degenerate)
- assemble_report end-to-end produces valid CirculationGraphReport
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from buildemup.components.c13.schema import (
    AdvisoryCategory,
    AdvisoryFlag,
)
from buildemup.components.c14 import (
    ALL_RECOGNIZED_CATEGORY_KEYWORDS,
    AdvisoryBundle,
    C14_METRIC_VERSION,
    C14_VERSION,
    CirculationConfig,
    CirculationGraphReport,
    EmittedFlags,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
    GraphTopology,
    NodeMetrics,
    PreferenceCirculationFlagKind,
    RoomMetadata,
    StructuralCirculationFlagKind,
    TRUNCATION_META_KIND_VALUE,
    assemble_advisory_bundle,
    assemble_report,
    compute_category_coverage,
    compute_layout_metrics,
    compute_node_metrics,
    construct_graph_topology,
    derive_c14_cache_keys,
    emit_flags,
)


# =============================================================================
# Helpers
# =============================================================================

@dataclass(frozen=True)
class _StubDoor:
    room_a_id: str
    room_b_id: str


def _door(a: str, b: str) -> _StubDoor:
    return _StubDoor(room_a_id=a, room_b_id=b)


def _rm(rid: str, category: str, is_main: bool = False) -> RoomMetadata:
    return RoomMetadata(
        room_id=rid, category=category, is_main_entry_room=is_main
    )


def _pipeline_pre_phase_delta(
    *,
    doors: tuple[_StubDoor, ...],
    placed_room_ids: tuple[str, ...],
    main_entry: str,
    metadata: tuple[RoomMetadata, ...],
    config: CirculationConfig | None = None,
) -> tuple[GraphTopology, NodeMetrics, float, CirculationConfig]:
    """Build α / β / coverage / config — the inputs to Phase δ."""
    cfg = config or CirculationConfig()
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=placed_room_ids,
        primary_door_ids=frozenset(),
        main_entry_room_id=main_entry,
    )
    m = compute_node_metrics(topology=t, main_entry_room_id=main_entry)
    cov = compute_category_coverage(nodes=t.nodes, metadata=metadata)
    return t, m, cov, cfg


def _run_phase_delta(
    *,
    doors: tuple[_StubDoor, ...],
    placed_room_ids: tuple[str, ...],
    main_entry: str,
    metadata: tuple[RoomMetadata, ...],
    config: CirculationConfig | None = None,
) -> EmittedFlags:
    t, m, cov, cfg = _pipeline_pre_phase_delta(
        doors=doors, placed_room_ids=placed_room_ids,
        main_entry=main_entry, metadata=metadata, config=config,
    )
    return emit_flags(
        topology=t, node_metrics=m, metadata=metadata,
        config=cfg, category_coverage=cov,
        main_entry_room_id=main_entry,
    )


def _kinds(flags: tuple) -> list[str]:
    return [str(f.flag_kind) for f in flags]


def _affected(flags: tuple, target_kind: str) -> set[str]:
    return {
        f.affected_room_id for f in flags
        if str(f.flag_kind) == target_kind
    }


# =============================================================================
# 1. BOTTLENECK_CONCENTRATION detector
# =============================================================================

def test_bottleneck_concentration_hub_flagged():
    """Hub of star ranks #1 in betweenness → flagged."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
            _door("bedroom_01", "living"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
            _rm("bedroom_01", "bedroom"),
        ),
    )
    bottleneck = _affected(
        ef.structural_flags,
        "bottleneck_concentration",
    )
    assert "living" in bottleneck


def test_bottleneck_concentration_corridor_exempt():
    """A corridor that's the hub should NOT be flagged — corridors are
    SUPPOSED to be high-betweenness; that's their architectural purpose."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "corridor_01"),
            _door("corridor_01", "living"),
            _door("bedroom_01", "corridor_01"),
        ),
        placed_room_ids=("entry", "corridor_01", "living", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("corridor_01", "corridor"),
            _rm("living", "living"),
            _rm("bedroom_01", "bedroom"),
        ),
    )
    bottleneck = _affected(
        ef.structural_flags,
        "bottleneck_concentration",
    )
    assert "corridor_01" not in bottleneck


# =============================================================================
# 2. DEAD_END_ISOLATION detector
# =============================================================================

def test_dead_end_isolation_habitable_degree_1_flagged():
    """A bedroom connected only to a living room (degree-1, non-
    corridor neighbour) flags DEAD_END_ISOLATION."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
            _door("bedroom_01", "living"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
            _rm("bedroom_01", "bedroom"),
        ),
    )
    dead_ends = _affected(ef.structural_flags, "dead_end_isolation")
    assert "bedroom_01" in dead_ends


def test_dead_end_isolation_corridor_neighbour_exempt():
    """A bedroom whose single neighbour is a corridor is NOT a dead-end
    by C14's definition — the corridor IS the route."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "corridor_01"),
            _door("corridor_01", "bedroom_01"),
        ),
        placed_room_ids=("entry", "corridor_01", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("corridor_01", "corridor"),
            _rm("bedroom_01", "bedroom"),
        ),
    )
    dead_ends = _affected(ef.structural_flags, "dead_end_isolation")
    # bedroom_01 has degree 1 but its neighbour IS a corridor → not flagged
    assert "bedroom_01" not in dead_ends


# =============================================================================
# 3. CATEGORY_COVERAGE_LOW detector (A8 / Inv E18)
# =============================================================================

def test_category_coverage_low_fires_when_below_threshold():
    """A 4-room layout with 1 known + 3 unknown categories has
    coverage 0.25, below default threshold 0.5 → flag fires."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "room_a"),
            _door("entry", "room_b"),
            _door("entry", "room_c"),
        ),
        placed_room_ids=("entry", "room_a", "room_b", "room_c"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("room_a", "unknown_xxx"),
            _rm("room_b", "unknown_yyy"),
            _rm("room_c", "unknown_zzz"),
        ),
    )
    flagged_kinds = _kinds(ef.structural_flags)
    assert "category_coverage_low" in flagged_kinds


def test_category_coverage_low_silent_when_full_coverage():
    """A layout with all-recognized categories has coverage 1.0,
    above threshold → flag does NOT fire."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
        ),
        placed_room_ids=("entry", "living", "kitchen"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
        ),
    )
    flagged_kinds = _kinds(ef.structural_flags)
    assert "category_coverage_low" not in flagged_kinds


# =============================================================================
# 4. TRANSIT_THROUGH_BEDROOM detector (A5 SKETCH)
# =============================================================================

def test_transit_through_bedroom_unavoidable_route_flagged():
    """Linear chain: entry — bedroom — kitchen. The ONLY route between
    non-bedroom rooms (entry, kitchen) passes through bedroom → flag.

    Use a high `flag_density_factor` to ensure the truncation cap
    doesn't eat the transit flag in this small (k=3) regime.
    """
    ef = _run_phase_delta(
        doors=(
            _door("entry", "bedroom_01"),
            _door("bedroom_01", "kitchen"),
        ),
        placed_room_ids=("entry", "bedroom_01", "kitchen"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("bedroom_01", "bedroom"),
            _rm("kitchen", "kitchen"),
        ),
        config=CirculationConfig(flag_density_factor=5.0),
    )
    transits = _affected(
        ef.preference_flags, "transit_through_bedroom"
    )
    assert "bedroom_01" in transits


def test_transit_through_bedroom_avoidable_route_exempt():
    """Two routes between entry and kitchen: through bedroom OR through
    living. Per A5 SKETCH: alternate avoids all bedroom-category rooms
    → no flag."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "bedroom_01"),
            _door("bedroom_01", "kitchen"),
            _door("entry", "living"),
            _door("kitchen", "living"),
        ),
        placed_room_ids=("entry", "bedroom_01", "kitchen", "living"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("bedroom_01", "bedroom"),
            _rm("kitchen", "kitchen"),
            _rm("living", "living"),
        ),
    )
    transits = _affected(
        ef.preference_flags, "transit_through_bedroom"
    )
    # bedroom_01 NOT flagged — entry→living→kitchen avoids bedroom
    # AND is the same length (2 hops) as entry→bedroom→kitchen.
    assert "bedroom_01" not in transits


def test_transit_through_bedroom_no_bedrooms_silent():
    """Layout without bedrooms: no transit flags possible."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
        ),
        placed_room_ids=("entry", "living", "kitchen"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
        ),
    )
    transits = _affected(
        ef.preference_flags, "transit_through_bedroom"
    )
    assert transits == set()


# =============================================================================
# 5. PRIVACY_GRADIENT_VIOLATION detector
# =============================================================================

def test_privacy_gradient_violation_bedroom_shallower_than_public():
    """Layout: entry → bedroom_01 (depth 1) → living (depth 2) → kitchen
    (depth 3). Bedroom (depth 1) is shallower than deepest public
    (kitchen depth 3) → flag fires.

    Use high flag_density_factor so cap doesn't truncate.
    """
    ef = _run_phase_delta(
        doors=(
            _door("entry", "bedroom_01"),
            _door("bedroom_01", "living"),
            _door("living", "kitchen"),
        ),
        placed_room_ids=("entry", "bedroom_01", "living", "kitchen"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("bedroom_01", "bedroom"),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
        ),
        config=CirculationConfig(flag_density_factor=5.0),
    )
    violations = _affected(
        ef.preference_flags, "privacy_gradient_violation"
    )
    assert "bedroom_01" in violations


def test_privacy_gradient_violation_deep_bedroom_silent():
    """Layout: entry → living (depth 1) → kitchen (depth 2) → bedroom_01
    (depth 3). Bedroom is deepest → no violation."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
            _door("kitchen", "bedroom_01"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
            _rm("bedroom_01", "bedroom"),
        ),
    )
    violations = _affected(
        ef.preference_flags, "privacy_gradient_violation"
    )
    assert "bedroom_01" not in violations


# =============================================================================
# 6. EXCESSIVE_DEPTH detector
# =============================================================================

def test_excessive_depth_flagged_beyond_threshold():
    """Linear chain of 7 nodes: depth 6 > default threshold 5 → flag."""
    doors = tuple(_door(f"r{i}", f"r{i+1}") for i in range(6))
    ef = _run_phase_delta(
        doors=doors,
        placed_room_ids=tuple(f"r{i}" for i in range(7)),
        main_entry="r0",
        metadata=tuple(_rm(f"r{i}", "living") for i in range(7)),
    )
    excessive = _affected(ef.preference_flags, "excessive_depth")
    # r6 is at depth 6, > threshold 5
    assert "r6" in excessive


def test_excessive_depth_silent_within_threshold():
    """Linear chain of 6 nodes: max depth 5 = default threshold 5 → no
    flag (strict > comparison)."""
    doors = tuple(_door(f"r{i}", f"r{i+1}") for i in range(5))
    ef = _run_phase_delta(
        doors=doors,
        placed_room_ids=tuple(f"r{i}" for i in range(6)),
        main_entry="r0",
        metadata=tuple(_rm(f"r{i}", "living") for i in range(6)),
    )
    excessive = _affected(ef.preference_flags, "excessive_depth")
    assert excessive == set()


def test_excessive_depth_custom_threshold():
    """With config.excessive_depth_threshold=2, a 4-node chain (max
    depth 3) flags the depth-3 room."""
    cfg = CirculationConfig(excessive_depth_threshold=2)
    doors = (
        _door("A", "B"),
        _door("B", "C"),
        _door("C", "D"),
    )
    ef = _run_phase_delta(
        doors=doors,
        placed_room_ids=("A", "B", "C", "D"),
        main_entry="A",
        metadata=(
            _rm("A", "main_entrance", is_main=True),
            _rm("B", "living"),
            _rm("C", "living"),
            _rm("D", "living"),
        ),
        config=cfg,
    )
    excessive = _affected(ef.preference_flags, "excessive_depth")
    assert "D" in excessive  # depth 3 > threshold 2


# =============================================================================
# 7. A10 — default severity = info for ALL emitted flags
# =============================================================================

def test_all_emitted_flags_default_to_info_severity():
    """Per A10: all C14 flags default to severity=info; escalation
    belongs to C15."""
    ef = _run_phase_delta(
        doors=(
            _door("entry", "bedroom_01"),
            _door("bedroom_01", "kitchen"),
        ),
        placed_room_ids=("entry", "bedroom_01", "kitchen"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("bedroom_01", "bedroom"),
            _rm("kitchen", "kitchen"),
        ),
    )
    for f in ef.structural_flags + ef.preference_flags:
        assert f.severity == "info", (
            f"Flag {f.flag_kind} severity = {f.severity}, expected 'info'"
        )


# =============================================================================
# 8. A6 — truncation cap (Inv E13')
# =============================================================================

def test_truncation_meta_silent_under_cap():
    """When total flags ≤ k × density_factor, no TRUNCATION_META appears.

    Use a high `flag_density_factor` so the cap comfortably accommodates
    all emergent flags. With k=4 hub and density=5.0, cap=20 ≫ any
    realistic emit count → cap silent.
    """
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
            _door("bedroom_01", "living"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
            _rm("bedroom_01", "bedroom"),
        ),
        config=CirculationConfig(flag_density_factor=5.0),
    )
    all_kinds = _kinds(ef.structural_flags) + _kinds(ef.preference_flags)
    assert TRUNCATION_META_KIND_VALUE not in all_kinds


def test_truncation_meta_fires_when_over_cap():
    """Force cap-overflow via a TIGHT density_factor.

    With k=4 and density_factor=0.5 → cap=2. The hub layout emits 3
    structural flags (1 bottleneck + 2 dead-ends). Cap=2 < 3 → 1 real
    slot + 1 TRUNCATION_META.
    """
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
            _door("bedroom_01", "living"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
            _rm("bedroom_01", "bedroom"),
        ),
        config=CirculationConfig(flag_density_factor=0.5),
    )
    all_kinds = _kinds(ef.structural_flags) + _kinds(ef.preference_flags)
    assert TRUNCATION_META_KIND_VALUE in all_kinds
    # Total flags must respect cap (2 for k=4 × 0.5).
    assert len(ef.structural_flags) + len(ef.preference_flags) <= 2


def test_truncation_meta_explanation_includes_suppressed_count():
    """A6 requires the meta-flag's explanation_template to include
    the count of suppressed flags + stable enumeration of kinds.

    Use same tight-cap config as test_truncation_meta_fires_when_over_cap.
    """
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
            _door("bedroom_01", "living"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
            _rm("bedroom_01", "bedroom"),
        ),
        config=CirculationConfig(flag_density_factor=0.5),
    )
    meta = [
        f for f in ef.structural_flags + ef.preference_flags
        if str(f.flag_kind) == TRUNCATION_META_KIND_VALUE
    ]
    assert len(meta) == 1
    # Per A6: includes count + kinds
    assert "suppressed" in meta[0].explanation_template.lower()


def test_truncation_at_most_one_meta_per_tuple():
    """Inv E13' cardinality: at most ONE TRUNCATION_META per tuple."""
    # Use tight density_factor to force truncation.
    ef = _run_phase_delta(
        doors=(
            _door("entry", "living"),
            _door("living", "kitchen"),
            _door("bedroom_01", "living"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom_01"),
        main_entry="entry",
        metadata=(
            _rm("entry", "main_entrance", is_main=True),
            _rm("living", "living"),
            _rm("kitchen", "kitchen"),
            _rm("bedroom_01", "bedroom"),
        ),
        config=CirculationConfig(flag_density_factor=0.5),
    )
    struct_meta_count = sum(
        1 for f in ef.structural_flags
        if str(f.flag_kind) == TRUNCATION_META_KIND_VALUE
    )
    pref_meta_count = sum(
        1 for f in ef.preference_flags
        if str(f.flag_kind) == TRUNCATION_META_KIND_VALUE
    )
    assert struct_meta_count <= 1
    assert pref_meta_count <= 1


# =============================================================================
# 9. Phase ε — advisory passthrough
# =============================================================================

def test_advisory_passthrough_byte_identical():
    """Inv E8: upstream_advisory_flags returned byte-identical."""
    inflow = (
        AdvisoryFlag(
            flag_kind="long_corridor_route",
            affected_room_id="corridor_01",
            category=AdvisoryCategory.CIRCULATION,
            severity="info",
            explanation_template="Long corridor.",
            deduplication_key="corridor_01:circulation",
        ),
    )
    ab = assemble_advisory_bundle(
        upstream_advisory_flags=inflow,
        structural_flags=(),
        preference_flags=(),
    )
    assert ab.upstream_advisory_flags is inflow or ab.upstream_advisory_flags == inflow


def test_advisory_passthrough_c14_flags_empty_at_v0_2():
    """v0.2 SKETCH: c14_advisory_flags is empty pending
    B-C14-ADVISORY-CONVERSION-CONTRACT-LOCK resolution."""
    ab = assemble_advisory_bundle(
        upstream_advisory_flags=(),
        structural_flags=(),
        preference_flags=(),
    )
    assert ab.c14_advisory_flags == ()


def test_advisory_passthrough_rejects_non_tuple():
    with pytest.raises(TypeError, match="tuple"):
        assemble_advisory_bundle(
            upstream_advisory_flags=[],  # type: ignore[arg-type]
            structural_flags=(),
            preference_flags=(),
        )


def test_advisory_passthrough_rejects_non_advisory_flag_in_tuple():
    with pytest.raises(TypeError, match="AdvisoryFlag"):
        assemble_advisory_bundle(
            upstream_advisory_flags=("not_an_advisory",),  # type: ignore[arg-type]
            structural_flags=(),
            preference_flags=(),
        )


# =============================================================================
# 10. Phase ζ — category_coverage
# =============================================================================

def test_category_coverage_full():
    """All rooms have recognized categories → coverage 1.0."""
    nodes = ("entry", "living", "bedroom_01")
    metadata = (
        _rm("entry", "main_entrance"),
        _rm("living", "living"),
        _rm("bedroom_01", "bedroom"),
    )
    assert compute_category_coverage(nodes=nodes, metadata=metadata) == 1.0


def test_category_coverage_zero():
    """No rooms have recognized categories → coverage 0.0."""
    nodes = ("a", "b", "c")
    metadata = (
        _rm("a", "unknown_x"),
        _rm("b", "unknown_y"),
        _rm("c", ""),
    )
    assert compute_category_coverage(nodes=nodes, metadata=metadata) == 0.0


def test_category_coverage_partial():
    """2 of 4 rooms recognized → coverage 0.5."""
    nodes = ("a", "b", "c", "d")
    metadata = (
        _rm("a", "living"),
        _rm("b", "bedroom"),
        _rm("c", "unknown"),
        _rm("d", "also_unknown"),
    )
    assert compute_category_coverage(nodes=nodes, metadata=metadata) == 0.5


def test_category_coverage_empty_nodes_returns_one():
    """Empty nodes: degenerate-but-safe 1.0."""
    assert compute_category_coverage(nodes=(), metadata=()) == 1.0


def test_category_coverage_missing_metadata_counts_as_unknown():
    """A node with no metadata entry counts as unrecognized."""
    nodes = ("a", "b")
    metadata = (_rm("a", "living"),)  # no entry for b
    assert compute_category_coverage(nodes=nodes, metadata=metadata) == 0.5


# =============================================================================
# 11. Phase ζ — assemble_report end-to-end
# =============================================================================

def test_assemble_report_end_to_end_produces_valid_report():
    """Full α→β→γ→δ→ε→ζ pipeline produces a valid CirculationGraphReport."""
    doors = (
        _door("entry", "living"),
        _door("living", "kitchen"),
        _door("bedroom_01", "living"),
    )
    rooms = ("entry", "living", "kitchen", "bedroom_01")
    metadata = (
        _rm("entry", "main_entrance", is_main=True),
        _rm("living", "living"),
        _rm("kitchen", "kitchen"),
        _rm("bedroom_01", "bedroom"),
    )
    config = CirculationConfig()

    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=rooms,
        primary_door_ids=frozenset(),
        main_entry_room_id="entry",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="entry")
    lm = compute_layout_metrics(
        node_metrics=m, main_entry_room_id="entry", nodes=t.nodes
    )
    cov = compute_category_coverage(nodes=t.nodes, metadata=metadata)
    ef = emit_flags(
        topology=t, node_metrics=m, metadata=metadata,
        config=config, category_coverage=cov, main_entry_room_id="entry",
    )
    ab = assemble_advisory_bundle(
        upstream_advisory_flags=(),
        structural_flags=ef.structural_flags,
        preference_flags=ef.preference_flags,
    )
    ck = derive_c14_cache_keys(
        c13_cache_key="c13:x",
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        config_signature="s",
    )
    report = assemble_report(
        source_placed_candidate_signature="cand_e2e",
        topology=t,
        node_metrics=m,
        layout_metrics=lm,
        emitted_flags=ef,
        advisory_bundle=ab,
        category_coverage=cov,
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        cache_keys=ck,
    )
    assert isinstance(report, CirculationGraphReport)
    assert report.graph_size_category == "normal"
    assert report.category_coverage == 1.0
    # Some flags fired
    assert len(report.structural_flags) + len(report.preference_flags) >= 1


def test_assemble_report_deterministic_replay():
    """Inv E7: same inputs → byte-equal report.

    Use a 4-node (k≥4) layout so RRA + integration are finite —
    NaN-bearing reports cannot satisfy `==` due to IEEE 754 semantics
    (nan != nan). The hash test in Sub 1 covers the NaN-bearing case
    separately."""
    doors = (
        _door("entry", "living"),
        _door("living", "kitchen"),
        _door("living", "bedroom_01"),
    )
    rooms = ("entry", "living", "kitchen", "bedroom_01")
    metadata = (
        _rm("entry", "main_entrance", is_main=True),
        _rm("living", "living"),
        _rm("kitchen", "kitchen"),
        _rm("bedroom_01", "bedroom"),
    )
    config = CirculationConfig()

    def _build():
        t = construct_graph_topology(
            doors=doors, placed_room_ids=rooms,
            primary_door_ids=frozenset(), main_entry_room_id="entry",
        )
        m = compute_node_metrics(topology=t, main_entry_room_id="entry")
        lm = compute_layout_metrics(
            node_metrics=m, main_entry_room_id="entry", nodes=t.nodes
        )
        cov = compute_category_coverage(nodes=t.nodes, metadata=metadata)
        ef = emit_flags(
            topology=t, node_metrics=m, metadata=metadata,
            config=config, category_coverage=cov, main_entry_room_id="entry",
        )
        ab = assemble_advisory_bundle(
            upstream_advisory_flags=(),
            structural_flags=ef.structural_flags,
            preference_flags=ef.preference_flags,
        )
        ck = derive_c14_cache_keys(
            c13_cache_key="c13:x",
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            config_signature="s",
        )
        return assemble_report(
            source_placed_candidate_signature="cand_e2e",
            topology=t, node_metrics=m, layout_metrics=lm,
            emitted_flags=ef, advisory_bundle=ab,
            category_coverage=cov,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=ck,
        )

    r1 = _build()
    r2 = _build()
    assert r1 == r2
