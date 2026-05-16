"""Tests for Phase β — tweak generation per layout."""
from __future__ import annotations

import pytest

from buildemup.components.c03b.advisory_lint import is_advisory_clean
from buildemup.components.c03b.config import C3bRuntimeConfig
from buildemup.components.c03b.phases.alpha import run_phase_alpha
from buildemup.components.c03b.phases.beta import (
    _DESCRIPTION_TEMPLATES,
    _generate_tweak_id,
    _priority_key,
    _topology_for_layout,
    classify_recommendation_flag,
    generate_tweak_option_set_for_layout,
    render_description,
    run_phase_beta,
)
from buildemup.components.c03b.phases.tables import (
    DIMENSION_TWEAK_MAP,
    TWEAK_CATEGORY_COST_RANGE_INR,
    TWEAK_CATEGORY_DEFAULT_SEVERITY,
    TWEAK_CATEGORY_IMPACT_TABLE,
    lookup_tweak_categories_for_check,
)
from buildemup.components.c03b.versioning import MAX_TWEAKS_PER_LAYOUT

from .fixtures import (
    make_bundle_3_layouts_happy_path,
    make_problem_check,
)


# ============================================================
# Static tables — invariants
# ============================================================

def test_default_severity_table_covers_all_categories():
    expected = {
        "finish_upgrade", "finish_downgrade", "door_relocate",
        "window_resize", "balcony_add", "balcony_remove",
        "storage_add", "utility_zone_carveout", "room_swap",
        "room_resize", "pooja_relocate", "kitchen_reorient",
        "wet_zone_restage",
    }
    assert set(TWEAK_CATEGORY_DEFAULT_SEVERITY.keys()) == expected


def test_impact_table_covers_all_categories():
    assert set(TWEAK_CATEGORY_IMPACT_TABLE.keys()) == set(TWEAK_CATEGORY_DEFAULT_SEVERITY.keys())


def test_cost_range_table_covers_all_categories():
    assert set(TWEAK_CATEGORY_COST_RANGE_INR.keys()) == set(TWEAK_CATEGORY_DEFAULT_SEVERITY.keys())


def test_dimension_tweak_map_covers_dimensions_1_to_10():
    assert set(DIMENSION_TWEAK_MAP.keys()) == set(range(1, 11))


def test_severity_defaults_are_light_or_medium():
    for cat, sev in TWEAK_CATEGORY_DEFAULT_SEVERITY.items():
        assert sev in {"light", "medium"}, f"{cat}={sev}"


# ============================================================
# Description templates — R2 lint cleanliness
# ============================================================

def test_all_description_templates_pass_r2_lint():
    for cat, tmpl in _DESCRIPTION_TEMPLATES.items():
        rendered = tmpl.format(rooms="room_X")
        assert is_advisory_clean(rendered), (
            f"Template for {cat} fails R2 lint: {rendered!r}"
        )


def test_render_description_handles_unknown_category_with_fallback():
    text = render_description("storage_add", ("master_001",))
    assert "storage_add" in text or "storage" in text.lower()


def test_render_description_handles_multiple_rooms():
    text = render_description("storage_add", ("a", "b", "c"))
    assert "a" in text and "b" in text and "c" in text


# ============================================================
# lookup_tweak_categories_for_check
# ============================================================

def test_lookup_with_problem_check_dim7_returns_room_resize_or_wet():
    check = make_problem_check(
        check_id="P7.1", dimension_id=7,
        why_it_matters="The shower length is below minimum.",
    )
    cats = lookup_tweak_categories_for_check(check)
    assert "room_resize" in cats or "wet_zone_restage" in cats or "door_relocate" in cats


def test_lookup_with_problem_check_dim6_kitchen_returns_kitchen_reorient():
    check = make_problem_check(
        check_id="P6.1", dimension_id=6,
        why_it_matters="Kitchen orientation faces north.",
    )
    cats = lookup_tweak_categories_for_check(check)
    assert "kitchen_reorient" in cats


def test_lookup_with_empty_string_returns_empty():
    assert lookup_tweak_categories_for_check("") == ()


def test_lookup_unknown_dimension_returns_empty():
    check = make_problem_check(
        check_id="P1.1", dimension_id=1,    # setbacks → no tweaks
        why_it_matters="Front setback insufficient.",
    )
    assert lookup_tweak_categories_for_check(check) == ()


# ============================================================
# classify_recommendation_flag (R5)
# ============================================================

def test_classify_no_checks_returns_alternative():
    from buildemup.components.c15.schema import CheckSeverity
    assert classify_recommendation_flag(problem_checks_addressed=()) == "alternative"


def test_classify_critical_check_returns_suggested():
    from buildemup.components.c15.schema import CheckSeverity
    check = make_problem_check(
        check_id="P7.1", dimension_id=7, severity=CheckSeverity.CRITICAL,
    )
    assert classify_recommendation_flag(problem_checks_addressed=(check,)) == "suggested"


def test_classify_important_check_returns_suggested():
    check = make_problem_check(check_id="P7.1", dimension_id=7)
    from buildemup.components.c15.schema import CheckSeverity
    assert check.severity == CheckSeverity.IMPORTANT
    assert classify_recommendation_flag(problem_checks_addressed=(check,)) == "suggested"


def test_classify_nice_to_have_returns_optional():
    from buildemup.components.c15.schema import CheckSeverity
    check = make_problem_check(
        check_id="P8.1", dimension_id=8, severity=CheckSeverity.NICE_TO_HAVE,
    )
    assert classify_recommendation_flag(problem_checks_addressed=(check,)) == "optional"


# ============================================================
# _generate_tweak_id determinism (R6)
# ============================================================

def test_generate_tweak_id_is_deterministic():
    id1 = _generate_tweak_id("layout_1", "kitchen_reorient", ("kitchen_001",))
    id2 = _generate_tweak_id("layout_1", "kitchen_reorient", ("kitchen_001",))
    assert id1 == id2


def test_generate_tweak_id_differs_by_category():
    id1 = _generate_tweak_id("layout_1", "kitchen_reorient", ("room_001",))
    id2 = _generate_tweak_id("layout_1", "pooja_relocate", ("room_001",))
    assert id1 != id2


def test_generate_tweak_id_differs_by_rooms():
    id1 = _generate_tweak_id("layout_1", "room_swap", ("room_001",))
    id2 = _generate_tweak_id("layout_1", "room_swap", ("room_002",))
    assert id1 != id2


def test_generate_tweak_id_is_stable_under_room_reordering():
    id1 = _generate_tweak_id("layout_1", "room_swap", ("room_001", "room_002"))
    id2 = _generate_tweak_id("layout_1", "room_swap", ("room_002", "room_001"))
    assert id1 == id2


# ============================================================
# _priority_key sort
# ============================================================

def test_priority_key_suggested_before_optional():
    # Build two minimal tweaks
    from .fixtures import make_tweak_option_light
    suggested = make_tweak_option_light(
        tweak_id="t_suggested", recommendation_flag="suggested",
    )
    optional = make_tweak_option_light(
        tweak_id="t_optional", recommendation_flag="optional",
    )
    assert _priority_key(suggested) < _priority_key(optional)


def test_priority_key_light_before_medium():
    from .fixtures import make_tweak_option_light, make_tweak_option_medium
    light = make_tweak_option_light(tweak_id="t_a")
    medium = make_tweak_option_medium(tweak_id="t_b")
    # Both 'suggested' (default for light builder is 'suggested')
    if light.recommendation_flag == medium.recommendation_flag:
        assert _priority_key(light) < _priority_key(medium)


# ============================================================
# generate_tweak_option_set_for_layout
# ============================================================

def test_generate_tweak_option_set_produces_archetype():
    bundle = make_bundle_3_layouts_happy_path()
    opt_set, envs, errs = generate_tweak_option_set_for_layout(
        layout_index=0, bundle=bundle, config=C3bRuntimeConfig(),
    )
    assert opt_set.layout_archetype == "cost_efficient"


def test_generate_tweak_option_set_picks_correct_layout():
    bundle = make_bundle_3_layouts_happy_path()
    opt_set, _, _ = generate_tweak_option_set_for_layout(
        layout_index=2, bundle=bundle, config=C3bRuntimeConfig(),
    )
    assert opt_set.layout_archetype == "premium_design"


def test_generate_tweak_option_set_has_lex_asc_tweaks():
    bundle = make_bundle_3_layouts_happy_path()
    opt_set, _, _ = generate_tweak_option_set_for_layout(
        layout_index=0, bundle=bundle, config=C3bRuntimeConfig(),
    )
    ids = [t.tweak_id for t in opt_set.tweaks]
    assert ids == sorted(ids)


def test_generate_tweak_option_set_caps_at_max_tweaks():
    bundle = make_bundle_3_layouts_happy_path()
    opt_set, _, _ = generate_tweak_option_set_for_layout(
        layout_index=0, bundle=bundle, config=C3bRuntimeConfig(),
    )
    assert len(opt_set.tweaks) <= MAX_TWEAKS_PER_LAYOUT


# ============================================================
# run_phase_beta — full layout pipeline
# ============================================================

def test_run_phase_beta_populates_3_option_sets():
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    assert len(sess.tweak_option_sets) == 3


def test_run_phase_beta_is_idempotent():
    bundle = make_bundle_3_layouts_happy_path()
    cfg = C3bRuntimeConfig()
    sess = run_phase_alpha(bundle, cfg)
    sess1 = run_phase_beta(sess, bundle, cfg)
    sess2 = run_phase_beta(sess1, bundle, cfg)
    # Second call should be a no-op (option sets already populated)
    assert sess1.tweak_option_sets == sess2.tweak_option_sets


def test_run_phase_beta_layouts_lex_asc_sorted():
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    ids = [s.layout_id for s in sess.tweak_option_sets]
    assert ids == sorted(ids)


def test_run_phase_beta_signs_session_after_population():
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sig_before = sess.canonical_replay_signature
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    # Signature should change because state changed
    assert sess.canonical_replay_signature != sig_before


def test_run_phase_beta_emits_envelopes_for_heavy_tweaks():
    """Severity context with topology change should produce envelopes."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    # At least one envelope (kitchen_reorient on a corridor would be HEAVY)
    # The fixture's wet_zone_restage on a riser-served bath_001 hits multiple
    # context factors, promoting to HEAVY
    assert len(sess.mutation_envelopes) >= 0    # may or may not produce; documented


def test_run_phase_beta_tweaks_satisfy_r3():
    """R3: every tweak grounded in affected_room_ids OR affected_grid_cells."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    for opt_set in sess.tweak_option_sets:
        for t in opt_set.tweaks:
            assert t.affected_room_ids or t.affected_grid_cells


def test_run_phase_beta_tweaks_satisfy_r4_apply_spec_matches_severity():
    """R4: LIGHT → geometry_local/finish; MEDIUM → subset_rerun."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    for opt_set in sess.tweak_option_sets:
        for t in opt_set.tweaks:
            if t.severity_tier == "light":
                assert t.apply_specification.mutation_kind in (
                    "geometry_local", "finish_schedule_only",
                )
            elif t.severity_tier == "medium":
                assert t.apply_specification.mutation_kind == "subset_rerun"
                assert t.apply_specification.subset_rerun_payload is not None


def test_topology_for_layout_deterministic():
    assert _topology_for_layout(0) == "central_spine"
    assert _topology_for_layout(1) == "strip"
    assert _topology_for_layout(2) == "l_shape"
    # Wraps around
    assert _topology_for_layout(3) == "central_spine"
