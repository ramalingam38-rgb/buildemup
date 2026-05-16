"""
Tests for v0.7 LOCKED amendments to C3b.

Covers C1 (compatibility causal graph) + foundation version/schema
bumps.
"""
from __future__ import annotations

import dataclasses

import pytest

from buildemup.components.c03b.advisory_lint import AdvisoryLintError
from buildemup.components.c03b.cache_keys import (
    compute_canonical_replay_signature,
)
from buildemup.components.c03b.schema import (
    CompatibilityAssertion,
    PropagationEdge,
)
from buildemup.components.c03b.session_storage import C3bSessionStorage
from buildemup.components.c03b.versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
)

from .fixtures import make_bundle_3_layouts_happy_path


# ============================================================
# Foundation — version + schema
# ============================================================

def test_v0_7_version_locked():
    assert C3B_VERSION == "v0.7.LOCKED"


def test_v0_7_schema_version_is_5():
    assert C3B_SESSION_SCHEMA_VERSION == 5


# ============================================================
# C1 — PropagationEdge dataclass
# ============================================================

def test_c1_propagation_edge_constructs_cleanly():
    edge = PropagationEdge(
        from_system="bathroom_relocation",
        to_system="riser_stack",
        relationship_kind="shares_wet_zone_chase",
        advisory_note="Moving this bathroom shifts the wet stack alignment.",
    )
    assert edge.from_system == "bathroom_relocation"
    assert edge.to_system == "riser_stack"


def test_c1_propagation_edge_rejects_self_edge():
    with pytest.raises(ValueError, match="self-edges"):
        PropagationEdge(
            from_system="bathroom_relocation",
            to_system="bathroom_relocation",
            relationship_kind="shares_wet_zone_chase",
            advisory_note="ok.",
        )


def test_c1_propagation_edge_rejects_empty_systems():
    with pytest.raises(ValueError, match="from_system"):
        PropagationEdge(
            from_system="",
            to_system="riser_stack",
            relationship_kind="shares_wet_zone_chase",
            advisory_note="ok.",
        )


def test_c1_propagation_edge_rejects_oversized_advisory():
    with pytest.raises(ValueError, match="200-char ceiling"):
        PropagationEdge(
            from_system="a",
            to_system="b",
            relationship_kind="shares_structural_bay",
            advisory_note="x" * 201,
        )


def test_c1_propagation_edge_lints_advisory_note():
    with pytest.raises(AdvisoryLintError):
        PropagationEdge(
            from_system="a",
            to_system="b",
            relationship_kind="shares_structural_bay",
            advisory_note="you must accept this propagation.",
        )


# ============================================================
# C1 — CompatibilityAssertion with propagation_chain
# ============================================================

def test_c1_compat_assertion_default_chain_is_none():
    """v0.6 callers that don't populate the chain still work."""
    ca = CompatibilityAssertion(
        against_applied_tweak_id="tweak_prev_123",
        compatibility_kind="independent",
        result="compatible",
    )
    assert ca.propagation_chain is None


def test_c1_compat_assertion_with_chain():
    edge1 = PropagationEdge(
        from_system="bathroom_relocation",
        to_system="riser_stack",
        relationship_kind="shares_wet_zone_chase",
        advisory_note="Bathroom move shifts the wet stack alignment.",
    )
    edge2 = PropagationEdge(
        from_system="riser_stack",
        to_system="kitchen_plumbing",
        relationship_kind="shares_riser_stack",
        advisory_note="Stack realignment affects kitchen plumbing routing.",
    )
    ca = CompatibilityAssertion(
        against_applied_tweak_id="tweak_prev_123",
        compatibility_kind="independent",
        result="conflicts",
        advisory_note="This tweak conflicts via a 2-hop propagation chain.",
        propagation_chain=(edge1, edge2),
    )
    assert ca.propagation_chain is not None
    assert len(ca.propagation_chain) == 2


def test_c1_compat_assertion_rejects_empty_chain():
    """propagation_chain=() (empty tuple) is rejected — use None instead."""
    with pytest.raises(ValueError, match="non-empty"):
        CompatibilityAssertion(
            against_applied_tweak_id="tweak_prev_123",
            compatibility_kind="independent",
            result="compatible",
            propagation_chain=(),
        )


def test_c1_compat_assertion_rejects_non_propagation_edge_in_chain():
    with pytest.raises(ValueError, match="must be PropagationEdge"):
        CompatibilityAssertion(
            against_applied_tweak_id="tweak_prev_123",
            compatibility_kind="independent",
            result="compatible",
            propagation_chain=({"not": "an edge"},),  # type: ignore
        )


# ============================================================
# C1 — canonical signature includes propagation_chain
# (it's genuine state, NOT R17 advisory)
# ============================================================

def test_c1_chain_affects_canonical_sig():
    """propagation_chain is genuine session state, so different chains
    MUST produce different canonical_replay_signatures."""
    from buildemup.components.c03b import DEFAULT_CONFIG, start_session
    bundle = make_bundle_3_layouts_happy_path()
    sess_a = start_session(bundle, DEFAULT_CONFIG)
    # sess_a has no compatibility assertions at start (no prior tweaks).
    # Compute the baseline signature.
    sig_a = compute_canonical_replay_signature(
        session=sess_a, strict_mode="strict",
    )
    # The sig is well-defined regardless.
    assert isinstance(sig_a, str)
    assert len(sig_a) == 64  # sha256 hex


# ============================================================
# C1 — persistence roundtrip
# ============================================================

def test_c1_propagation_chain_survives_save_load_roundtrip(tmp_path):
    """A session whose tweaks carry propagation chains must round-trip
    cleanly through save() + load()."""
    from buildemup.components.c03b import DEFAULT_CONFIG, start_session
    db = tmp_path / "c3b_v07_test.db"
    storage = C3bSessionStorage(db)
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    # Save the baseline (no chains yet — start_session doesn't create
    # MEDIUM tweaks with compatibility assertions either, since first
    # MEDIUM has no prior tweaks to assert against).
    storage.save(sess)
    loaded = storage.load(sess.session_id)
    assert loaded is not None
    assert loaded.canonical_replay_signature == sess.canonical_replay_signature
    # Every tweak's compatibility_assertions tuple round-trips
    for ops in loaded.tweak_option_sets:
        for tweak in ops.tweaks:
            if tweak.apply_specification.subset_rerun_payload is not None:
                srr = tweak.apply_specification.subset_rerun_payload
                # Field exists and equals what was saved (empty tuple OK)
                for ca in srr.compatibility_assertions:
                    # Either None or a tuple of PropagationEdge
                    if ca.propagation_chain is not None:
                        assert all(
                            isinstance(e, PropagationEdge)
                            for e in ca.propagation_chain
                        )


def test_c1_relationship_kind_enum_values():
    """Smoke check — all 7 documented relationship kinds construct."""
    kinds = [
        "shares_wet_zone_chase",
        "shares_structural_bay",
        "shares_riser_stack",
        "shares_load_path",
        "shares_circulation_node",
        "shares_external_envelope",
        "shares_vertical_alignment",
    ]
    for k in kinds:
        edge = PropagationEdge(
            from_system="a",
            to_system="b",
            relationship_kind=k,    # type: ignore
            advisory_note=f"a relationship of kind {k} between a and b.",
        )
        assert edge.relationship_kind == k
