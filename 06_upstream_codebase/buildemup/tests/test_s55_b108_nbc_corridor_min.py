"""B-108 (S55 partial closure): NBC corridor minimum-width verification.

Verifies:
  1. CorridorDesignConfig.regulatory_min_width_m default is 0.9m
     (NBC 2016 Part 3 § 14 single-dwelling-unit short-corridor).
  2. The class docstring carries an NBC citation breadcrumb so the
     value's provenance is greppable.

Full PDF verification + architect sign-off remains queued under
B-150 / B-238; see 05_integrity_check/B108_PARTIAL_NBC_VERIFICATION_S55.md.
"""
from __future__ import annotations

from buildemup.components.c08.schema import CorridorDesignConfig


def test_regulatory_min_width_default_is_0_9_m():
    cfg = CorridorDesignConfig()
    assert cfg.regulatory_min_width_m == 0.9


def test_corridor_config_docstring_carries_nbc_breadcrumb():
    doc = CorridorDesignConfig.__doc__ or ""
    assert "B-108" in doc
    assert "NBC" in doc
    assert "0.9" in doc


def test_corridor_config_docstring_points_to_verification_report():
    doc = CorridorDesignConfig.__doc__ or ""
    assert "B108_PARTIAL_NBC_VERIFICATION_S55" in doc


def test_corridor_config_docstring_acknowledges_part_4_scope():
    """The breadcrumb must name Part 4 fire-egress so callers know
    when to override (multi-unit / long corridors)."""
    doc = CorridorDesignConfig.__doc__ or ""
    assert "Part 4" in doc


def test_caller_can_override_regulatory_min_for_multi_unit():
    """Override path stays open: multi-unit hallway designers can
    pass a higher minimum. Comfort target must be bumped in lockstep
    per the existing post-init invariant."""
    cfg = CorridorDesignConfig(
        regulatory_min_width_m=1.5, comfort_target_width_m=1.8,
    )
    assert cfg.regulatory_min_width_m == 1.5
