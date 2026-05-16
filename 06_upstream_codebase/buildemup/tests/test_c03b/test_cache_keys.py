"""Tests for C3b cache_keys (R6 / R7 / R8 signatures)."""
from __future__ import annotations

import pytest

from buildemup.components.c03b.cache_keys import (
    _canon,
    _sha256_hex,
    compute_canonical_replay_signature,
    compute_presentation_signature,
    compute_schema_descriptor_digest,
    is_valid_signature,
)
from buildemup.components.c03b.versioning import (
    CANONICAL_FLOAT_DECIMALS,
    SIGNATURE_HEX_LENGTH,
)

from tests.test_c03b.fixtures import (
    make_advisory_flag,
    make_tradeoff_session,
)


# ============================================================
# is_valid_signature helper
# ============================================================

def test_is_valid_signature_64_hex():
    assert is_valid_signature("a" * 64) is True


def test_is_valid_signature_wrong_length():
    assert is_valid_signature("a" * 63) is False
    assert is_valid_signature("a" * 65) is False


def test_is_valid_signature_non_hex():
    assert is_valid_signature("z" * 64) is False


def test_is_valid_signature_not_string():
    assert is_valid_signature(None) is False
    assert is_valid_signature(123) is False


# ============================================================
# _canon helper — float rounding (CANONICAL_FLOAT_DECIMALS = 6)
# ============================================================

def test_canon_float_rounded_to_6_decimals():
    val = 1.123456789012
    assert _canon(val) == round(val, CANONICAL_FLOAT_DECIMALS)


def test_canon_dict_sorted_by_key():
    d = {"z": 1, "a": 2, "m": 3}
    out = _canon(d)
    assert list(out.keys()) == ["a", "m", "z"]


def test_canon_tuple_becomes_list():
    assert _canon((1, 2, 3)) == [1, 2, 3]


def test_canon_set_sorted():
    """Sets canonicalize to sorted list for stable hashing."""
    out = _canon({3, 1, 2})
    assert out == [1, 2, 3]


def test_canon_none_stays_none():
    assert _canon(None) is None


def test_canon_bool_stays_bool():
    """bool is a special int subclass; canon preserves bool semantics."""
    assert _canon(True) is True
    assert _canon(False) is False


# ============================================================
# _sha256_hex — produces 64 hex chars
# ============================================================

def test_sha256_hex_length():
    out = _sha256_hex({"k": "v"})
    assert is_valid_signature(out)


def test_sha256_hex_deterministic():
    """Same input → same output."""
    a = _sha256_hex({"x": 1, "y": [1, 2]})
    b = _sha256_hex({"x": 1, "y": [1, 2]})
    assert a == b


def test_sha256_hex_key_order_irrelevant():
    """_canon sorts dict keys, so input order doesn't matter."""
    a = _sha256_hex({"a": 1, "b": 2})
    b = _sha256_hex({"b": 2, "a": 1})
    assert a == b


def test_sha256_hex_value_change_changes_hash():
    a = _sha256_hex({"x": 1})
    b = _sha256_hex({"x": 2})
    assert a != b


# ============================================================
# compute_canonical_replay_signature — R6
# ============================================================

def test_canonical_replay_signature_returns_valid_hash():
    sess = make_tradeoff_session()
    sig = compute_canonical_replay_signature(session=sess, strict_mode="strict")
    assert is_valid_signature(sig)


def test_canonical_replay_signature_deterministic():
    """R6: same inputs → same signature on repeat compute."""
    sess = make_tradeoff_session()
    sig1 = compute_canonical_replay_signature(session=sess, strict_mode="strict")
    sig2 = compute_canonical_replay_signature(session=sess, strict_mode="strict")
    assert sig1 == sig2


def test_canonical_replay_strict_vs_warn_differs():
    """strict_mode is part of the signature inputs."""
    sess = make_tradeoff_session()
    strict_sig = compute_canonical_replay_signature(session=sess, strict_mode="strict")
    warn_sig = compute_canonical_replay_signature(session=sess, strict_mode="warn")
    assert strict_sig != warn_sig


def test_canonical_replay_session_id_affects_signature():
    """Different sessions → different signatures."""
    s1 = make_tradeoff_session(session_id="sess_a")
    s2 = make_tradeoff_session(session_id="sess_b")
    sig1 = compute_canonical_replay_signature(session=s1, strict_mode="strict")
    sig2 = compute_canonical_replay_signature(session=s2, strict_mode="strict")
    assert sig1 != sig2


def test_canonical_replay_iteration_count_affects_signature():
    s1 = make_tradeoff_session(iteration_count=0)
    s2 = make_tradeoff_session(iteration_count=1)
    sig1 = compute_canonical_replay_signature(session=s1, strict_mode="strict")
    sig2 = compute_canonical_replay_signature(session=s2, strict_mode="strict")
    assert sig1 != sig2


def test_canonical_replay_advisory_flag_affects_signature():
    """R14/R15 surface as advisory_flags — must change signature."""
    base = make_tradeoff_session()
    with_flag = make_tradeoff_session(
        advisory_flags=(make_advisory_flag(),),
    )
    sig_base = compute_canonical_replay_signature(
        session=base, strict_mode="strict",
    )
    sig_with_flag = compute_canonical_replay_signature(
        session=with_flag, strict_mode="strict",
    )
    assert sig_base != sig_with_flag


# ============================================================
# compute_presentation_signature — R7
# ============================================================

def test_presentation_signature_returns_valid_hash():
    sig = compute_presentation_signature(canonical_replay_signature="a" * 64)
    assert is_valid_signature(sig)


def test_presentation_signature_deterministic():
    """R7: derived hash; same canonical → same presentation."""
    cr = "f" * 64
    p1 = compute_presentation_signature(canonical_replay_signature=cr)
    p2 = compute_presentation_signature(canonical_replay_signature=cr)
    assert p1 == p2


def test_presentation_signature_depends_on_canonical():
    """Different canonical inputs → different presentation signatures."""
    p1 = compute_presentation_signature(canonical_replay_signature="a" * 64)
    p2 = compute_presentation_signature(canonical_replay_signature="b" * 64)
    assert p1 != p2


def test_presentation_signature_empty_canonical_rejected():
    with pytest.raises(ValueError, match="canonical_replay_signature"):
        compute_presentation_signature(canonical_replay_signature="")


# ============================================================
# compute_schema_descriptor_digest — R8
# ============================================================

def test_schema_descriptor_digest_returns_valid_hash():
    sig = compute_schema_descriptor_digest()
    assert is_valid_signature(sig)


def test_schema_descriptor_digest_deterministic():
    """R8: digest is over field NAMES + TYPES (not values).
    Same schema across runs → same digest."""
    d1 = compute_schema_descriptor_digest()
    d2 = compute_schema_descriptor_digest()
    assert d1 == d2


def test_schema_descriptor_digest_value_invariant():
    """Per R8: the digest does NOT change with field values, since it's
    computed over schema metadata only.

    We can't easily verify this without mutating schema, but we can
    re-compute and confirm the digest only depends on the loaded
    dataclasses' field definitions."""
    d1 = compute_schema_descriptor_digest()
    d2 = compute_schema_descriptor_digest()
    assert d1 == d2
    # Sanity: it's a non-trivial value
    assert d1 != "0" * 64
    assert len(d1) == SIGNATURE_HEX_LENGTH
