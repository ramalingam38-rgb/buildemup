"""C16 — orientation.py tests covering R29 4-step hierarchy + R29c
tiebreaks + R29d OrientationLock plausibility."""
import pytest
from buildemup.components.c16 import (
    OrientationLock, WallCandidate, all_hierarchy_candidates,
    compute_orientation, validate_orientation_lock,
    JurisdictionProfile, OrientationLockMismatchError,
)


def _wall(wall_id, sx, sy, ex, ey, *, is_external=True, has_main_entry=False,
          semantic="aaaaaaaa"):
    import math
    length_mm = int(round(math.hypot(ex - sx, ey - sy)))
    return WallCandidate(
        wall_id=wall_id, start_x_mm=sx, start_y_mm=sy,
        end_x_mm=ex, end_y_mm=ey, length_mm=length_mm,
        semantic_identity_hash=semantic,
        is_external=is_external, has_main_entry=has_main_entry,
    )


class TestStep1ExplicitHint:
    def test_hint_45_deg_wins(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            local_x_axis_orientation_deg_hint=45.0,
        )
        d = compute_orientation(walls=(), jurisdiction_profile=jp)
        assert d.basis == "explicit_hint"
        assert d.orientation_deg == 45.0

    def test_hint_zero_still_wins(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            local_x_axis_orientation_deg_hint=0.0,
        )
        d = compute_orientation(
            walls=(_wall("w1", 0, 0, 1000, 0),),
            jurisdiction_profile=jp,
        )
        assert d.basis == "explicit_hint"
        assert d.orientation_deg == 0.0


class TestStep2PrimaryEntrance:
    def test_entrance_wall_selected(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        walls = (
            _wall("w1", 0, 0, 1000, 0, has_main_entry=False, semantic="bb"),
            _wall("w2", 0, 0, 0, 5000, has_main_entry=True, semantic="aa"),
        )
        d = compute_orientation(walls=walls, jurisdiction_profile=jp)
        assert d.basis == "primary_entrance"
        assert d.chosen_wall_id == "w2"

    def test_multi_entry_tiebreak_lex_min_semantic(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        walls = (
            _wall("wA", 0, 0, 1000, 0, has_main_entry=True, semantic="bbbb"),
            _wall("wB", 0, 0, 1000, 0, has_main_entry=True, semantic="aaaa"),
        )
        d = compute_orientation(walls=walls, jurisdiction_profile=jp)
        assert d.basis == "primary_entrance"
        assert d.chosen_wall_id == "wB"


class TestStep3LongestExternalWall:
    def test_longest_wins(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        walls = (
            _wall("short", 0, 0, 2000, 0, semantic="zz"),
            _wall("long",  0, 0, 6000, 0, semantic="bb"),
            _wall("med",   0, 0, 4000, 0, semantic="cc"),
        )
        d = compute_orientation(walls=walls, jurisdiction_profile=jp)
        assert d.basis == "longest_wall"
        assert d.chosen_wall_id == "long"

    def test_tied_longest_tiebreak_lex_min(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        walls = (
            _wall("A", 0, 0, 5000, 0, semantic="zzzz"),
            _wall("B", 0, 0, 5000, 0, semantic="aaaa"),
        )
        d = compute_orientation(walls=walls, jurisdiction_profile=jp)
        assert d.chosen_wall_id == "B"

    def test_internal_walls_ignored(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        walls = (
            _wall("int_long", 0, 0, 9000, 0, is_external=False, semantic="aa"),
            _wall("ext_short", 0, 0, 3000, 0, is_external=True, semantic="bb"),
        )
        d = compute_orientation(walls=walls, jurisdiction_profile=jp)
        assert d.chosen_wall_id == "ext_short"


class TestStep4LexFallback:
    def test_no_external_no_entry_falls_back(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        walls = (
            _wall("A", 0, 0, 1000, 0, is_external=False, semantic="zz"),
            _wall("B", 0, 0, 1000, 1000, is_external=False, semantic="aa"),
        )
        d = compute_orientation(walls=walls, jurisdiction_profile=jp)
        assert d.basis == "lex_fallback"
        assert d.chosen_wall_id == "B"

    def test_empty_walls_returns_zero(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        d = compute_orientation(walls=(), jurisdiction_profile=jp)
        assert d.basis == "lex_fallback"
        assert d.orientation_deg == 0.0


class TestR29dPlausibility:
    def _jp(self, lock_deg):
        return JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            orientation_lock=OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=lock_deg,
                locked_origin_basis="longest_wall",
                lock_provenance="test_fixture",
            ),
        )

    def test_lock_matching_candidate_passes(self):
        jp = self._jp(0.0)
        walls = (_wall("A", 0, 0, 5000, 0),)
        candidates = all_hierarchy_candidates(walls=walls, jurisdiction_profile=jp)
        # No assertion needed — non-raise = pass
        validate_orientation_lock(
            lock=jp.orientation_lock,
            candidate_decisions=candidates,
        )

    def test_lock_implausible_raises(self):
        jp = self._jp(73.0)  # not within EPSILON of any candidate
        walls = (_wall("A", 0, 0, 5000, 0),)   # axis 0 deg
        candidates = all_hierarchy_candidates(walls=walls, jurisdiction_profile=jp)
        with pytest.raises(OrientationLockMismatchError):
            validate_orientation_lock(
                lock=jp.orientation_lock,
                candidate_decisions=candidates,
            )

    def test_lock_modulo_180_matches(self):
        # 180° is axis-equivalent to 0° (walls are direction-agnostic)
        jp = self._jp(180.0)
        walls = (_wall("A", 0, 0, 5000, 0),)
        candidates = all_hierarchy_candidates(walls=walls, jurisdiction_profile=jp)
        validate_orientation_lock(
            lock=jp.orientation_lock,
            candidate_decisions=candidates,
        )
