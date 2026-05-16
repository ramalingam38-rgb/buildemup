"""Tier-1 unit tests for C4 output immutability (SC-1).

Per SPEC v0.5 LOCKED § 7. MappingProxyType wraps shape_metadata,
baseline_room_orientation_guidelines (outer + inner), and
provenance.source_versions.
"""
from __future__ import annotations

from types import MappingProxyType

import pytest

from buildemup.components.c04 import derive
from buildemup.tests.validation._c4_fixtures import chennai_30x40, make_brief


def test_shape_metadata_is_mappingproxytype():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert isinstance(pa.shape_metadata, MappingProxyType)
    with pytest.raises(TypeError):
        pa.shape_metadata["new_key"] = "value"  # type: ignore[index]


def test_baseline_orientations_uses_mappingproxytype_outer_and_inner():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    outer = pa.baseline_room_orientation_guidelines
    assert isinstance(outer, MappingProxyType)
    # Outer mutation forbidden — item assign + del both raise TypeError.
    from buildemup.components.c04.schema import ClimateZone
    sample_zone = next(iter(outer.keys()))
    with pytest.raises(TypeError):
        outer[ClimateZone.HOT_DRY] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        del outer[sample_zone]           # type: ignore[attr-defined]
    # Inner mutation forbidden too
    for zone, inner in outer.items():
        assert isinstance(inner, MappingProxyType), f"{zone} inner not MappingProxyType"
        with pytest.raises(TypeError):
            inner["new_room"] = ()       # type: ignore[index]


def test_provenance_source_versions_is_mappingproxytype():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert isinstance(pa.provenance.source_versions, MappingProxyType)
    # The 4 KBs must each have a version entry
    assert {"city_geography", "wind_load", "soil_city_defaults", "wind_direction"} <= set(
        pa.provenance.source_versions.keys()
    )
    with pytest.raises(TypeError):
        pa.provenance.source_versions["spoof"] = "v0"  # type: ignore[index]
