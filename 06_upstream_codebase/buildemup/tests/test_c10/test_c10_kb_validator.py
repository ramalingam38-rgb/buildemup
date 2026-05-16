"""
BuildemUp† — Component 10 — KB cross-validator tests.

Per C10 SPEC v1.0 LOCKED § 3 (KB cross-validation startup hook).

†= placeholder name marker.
"""
from __future__ import annotations

import pytest

from buildemup.components.c10 import (
    KBVersionMismatchError,
    get_fixture_types_for,
    get_plumbing_minimum_for,
    load_plumbing_fixture_profiles,
    load_plumbing_minimums,
    validate_plumbing_kbs_compatibility,
)


# =============================================================================
# Disk-loaded happy path
# =============================================================================


class TestKBLoadFromDisk:

    def test_load_minimums_returns_dict_with_rows(self):
        kb = load_plumbing_minimums()
        assert "_kb_version" in kb
        assert isinstance(kb["rows"], list)
        assert len(kb["rows"]) >= 7      # v1 has 7 fixtures

    def test_load_profiles_returns_dict_with_rows(self):
        kb = load_plumbing_fixture_profiles()
        assert "_kb_version" in kb
        assert "_compatible_with_minimums_kb_version" in kb

    def test_validate_returns_orphan_warnings(self):
        # bathtub and floor_drain are in minimums but not referenced.
        warnings = validate_plumbing_kbs_compatibility()
        assert isinstance(warnings, tuple)
        # We expect at least 2 orphans (bathtub, floor_drain).
        assert len(warnings) >= 2
        for w in warnings:
            assert "orphan minimums entry" in w

    def test_validate_succeeds_on_disk_kbs(self):
        # No exception expected — disk KBs are version-aligned.
        validate_plumbing_kbs_compatibility()


# =============================================================================
# Lookup helpers
# =============================================================================


class TestLookupHelpers:

    def test_get_plumbing_minimum_for_water_closet(self):
        row = get_plumbing_minimum_for("water_closet")
        assert row["fixture_type"] == "water_closet"
        assert row["trap_arm_max_m"] > 0

    def test_get_plumbing_minimum_for_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown"):
            get_plumbing_minimum_for("unknown_fixture")

    def test_get_fixture_types_for_combined_bathroom(self):
        types = get_fixture_types_for("bathroom", "combined")
        assert "water_closet" in types
        assert "lavatory" in types
        assert "shower" in types

    def test_get_fixture_types_for_kitchen(self):
        types = get_fixture_types_for("kitchen", None)
        assert types == ("kitchen_sink",)

    def test_get_fixture_types_for_utility(self):
        types = get_fixture_types_for("utility", None)
        assert types == ("utility_sink",)

    def test_get_fixture_types_for_unknown_raises(self):
        with pytest.raises(KeyError, match="No fixture-profile row"):
            get_fixture_types_for("nonexistent", None)


# =============================================================================
# Strict KB regression — S37 patch (S36 critique #7)
# =============================================================================
# When the orchestrator's _build_fixture_types_per_room encounters a missing
# profile row, it must raise KBVersionMismatchError (Inv 16 protection) rather
# than silently falling back to a default fixture tuple.


class TestStrictFallbackRemoval:
    """Verifies _build_fixture_types_per_room raises KBVersionMismatchError
    rather than returning a silent default when the profiles KB lacks a
    needed row."""

    def _bathroom_room(self, subtype_value=None):
        # Build a minimal RoomSizeRequirement-like stub.
        from dataclasses import dataclass
        from buildemup.components.c09.schema import (
            BathroomSubtype, RoomCategory,
        )

        @dataclass
        class _Stub:
            room_id: str
            category: object
            bathroom_subtype: object = None

        if subtype_value is None:
            return _Stub("BATHROOM_X", RoomCategory.BATHROOM, None)
        # Build a fake enum-like object with .value
        @dataclass
        class _Sub:
            value: str
        return _Stub("BATHROOM_X", RoomCategory.BATHROOM, _Sub(subtype_value))

    def test_unknown_bathroom_subtype_raises_kb_version_mismatch(self):
        from buildemup.components.c10.errors import KBVersionMismatchError
        from buildemup.components.c10.wet_zone_planner import (
            _build_fixture_types_per_room,
        )
        rooms = [self._bathroom_room("not_a_real_subtype")]
        with pytest.raises(KBVersionMismatchError, match="bathroom_subtype"):
            _build_fixture_types_per_room(rooms)

    def test_known_subtypes_still_succeed(self):
        # Sanity guard: existing subtypes still work post-patch.
        from buildemup.components.c10.wet_zone_planner import (
            _build_fixture_types_per_room,
        )
        rooms = [
            self._bathroom_room("combined"),
            self._bathroom_room("bath_only"),
            self._bathroom_room("wc_only"),
        ]
        out = _build_fixture_types_per_room(rooms)
        # All three present; non-empty
        assert all(len(v) >= 1 for v in out.values())


# =============================================================================
# Validator failure modes (in-memory KB construction)
# =============================================================================


def _minimal_minimums(version: str = "Plumbing_v1_S35") -> dict:
    return {
        "_kb_id": "plumbing_minimums",
        "_kb_version": version,
        "rows": [
            {
                "fixture_type": "water_closet",
                "trap_arm_max_m": 1.83,
                "min_pipe_diameter_mm": 100,
                "trap_seal_min_mm": 50,
                "source_confidence": "secondary_consensus",
            },
        ],
    }


def _minimal_profiles(compatible_with: str = "Plumbing_v1_S35") -> dict:
    return {
        "_kb_id": "plumbing_fixture_profiles",
        "_kb_version": "Profiles_v2_S35",
        "_compatible_with_minimums_kb_version": compatible_with,
        "rows": [
            {
                "room_category": "bathroom",
                "bathroom_subtype": "wc_only",
                "fixture_types": ["water_closet"],
            },
        ],
    }


class TestValidatorFailureModes:

    def test_version_drift_raises(self):
        profiles = _minimal_profiles(compatible_with="OLD_VERSION")
        minimums = _minimal_minimums(version="Plumbing_v1_S35")
        with pytest.raises(KBVersionMismatchError, match="version drift"):
            validate_plumbing_kbs_compatibility(profiles, minimums)

    def test_orphan_fixture_type_raises(self):
        profiles = _minimal_profiles()
        profiles["rows"][0]["fixture_types"] = ["water_closet", "missing_fixture"]
        minimums = _minimal_minimums()
        with pytest.raises(KBVersionMismatchError, match="orphan fixture types"):
            validate_plumbing_kbs_compatibility(profiles, minimums)

    def test_diameter_too_small_raises(self):
        minimums = _minimal_minimums()
        minimums["rows"][0]["min_pipe_diameter_mm"] = 10
        with pytest.raises(KBVersionMismatchError, match="min_pipe_diameter_mm"):
            validate_plumbing_kbs_compatibility(_minimal_profiles(), minimums)

    def test_diameter_too_large_raises(self):
        minimums = _minimal_minimums()
        minimums["rows"][0]["min_pipe_diameter_mm"] = 500
        with pytest.raises(KBVersionMismatchError, match="min_pipe_diameter_mm"):
            validate_plumbing_kbs_compatibility(_minimal_profiles(), minimums)

    def test_trap_seal_too_small_raises(self):
        minimums = _minimal_minimums()
        minimums["rows"][0]["trap_seal_min_mm"] = 10
        with pytest.raises(KBVersionMismatchError, match="trap_seal_min_mm"):
            validate_plumbing_kbs_compatibility(_minimal_profiles(), minimums)

    def test_trap_seal_too_large_raises(self):
        minimums = _minimal_minimums()
        minimums["rows"][0]["trap_seal_min_mm"] = 200
        with pytest.raises(KBVersionMismatchError, match="trap_seal_min_mm"):
            validate_plumbing_kbs_compatibility(_minimal_profiles(), minimums)

    def test_trap_arm_zero_raises(self):
        minimums = _minimal_minimums()
        minimums["rows"][0]["trap_arm_max_m"] = 0.0
        with pytest.raises(KBVersionMismatchError, match="trap_arm_max_m"):
            validate_plumbing_kbs_compatibility(_minimal_profiles(), minimums)

    def test_trap_arm_negative_raises(self):
        minimums = _minimal_minimums()
        minimums["rows"][0]["trap_arm_max_m"] = -1.0
        with pytest.raises(KBVersionMismatchError, match="trap_arm_max_m"):
            validate_plumbing_kbs_compatibility(_minimal_profiles(), minimums)

    def test_aligned_kbs_pass(self):
        # No-orphan profiles + valid minimums = no warnings.
        warnings = validate_plumbing_kbs_compatibility(
            _minimal_profiles(), _minimal_minimums(),
        )
        assert warnings == ()
