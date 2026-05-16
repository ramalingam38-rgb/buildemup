"""C16 Sub-1 — cache_keys.py tests.

Coverage:
    - canonical JSON R7c rules (1-10) explicit corner cases
    - sha256_hex determinism
    - C16CacheKeys construction validation
    - canonical_replay_signature vs presentation_signature (R32a/c)
    - config_signature_for excludes observability flags
    - derive_c16_cache_keys triple-tier derivation
"""
from __future__ import annotations

from enum import Enum

import pytest

from buildemup.components.c16 import (
    AuthorityKind,
    C16CacheKeys,
    C16ConfigurationError,
    RenderingConfig,
    canonical_json,
    canonical_replay_signature,
    canonicalize_value,
    config_signature_for,
    derive_c16_cache_keys,
    presentation_signature,
    sha256_hex,
)


# ============================================================
# § 1 — R7c canonical JSON rules
# ============================================================

class TestCanonicalJsonRules:
    # Rule 1: object key lex-ASC
    def test_dict_keys_lex_ascending(self):
        out = canonical_json({"z": 1, "a": 2, "m": 3})
        assert out == '{"a":2,"m":3,"z":1}'

    # Rule 2: enum → .value string
    def test_enum_serialized_as_value_string(self):
        out = canonical_json({"k": AuthorityKind.UPSTREAM_AUTHORITATIVE})
        assert '"upstream_authoritative"' in out
        assert "UPSTREAM_AUTHORITATIVE" not in out

    # Rule 3: Optional[None] OMITTED
    def test_none_fields_omitted_from_dict(self):
        out = canonical_json({"a": 1, "b": None, "c": 3})
        assert out == '{"a":1,"c":3}'
        # No "null" appears
        assert "null" not in out

    # Rule 5: tuples → arrays, order preserved
    def test_tuple_serialized_as_array(self):
        out = canonical_json({"k": (3, 1, 2)})
        assert out == '{"k":[3,1,2]}'

    # Rule 6: frozensets → arrays in lex-ASC order
    def test_frozenset_serialized_as_sorted_array(self):
        out = canonical_json({"k": frozenset({"b", "a", "c"})})
        assert out == '{"k":["a","b","c"]}'

    # Rule 7a: integers → bare integers
    def test_integers_serialized_bare(self):
        out = canonical_json({"k": 42})
        assert out == '{"k":42}'

    # Rule 9: no whitespace between tokens
    def test_no_whitespace_between_tokens(self):
        out = canonical_json({"a": 1, "b": 2, "c": [1, 2, 3]})
        assert " " not in out
        assert "\n" not in out
        assert "\t" not in out

    # Rule 10: no trailing commas
    def test_no_trailing_commas(self):
        out = canonical_json({"a": 1, "b": 2})
        assert ",}" not in out
        out2 = canonical_json({"k": [1, 2, 3]})
        assert ",]" not in out2


class TestNumericFormatting:
    def test_ratio_floats_at_4_decimal_places(self):
        # rule 7c: ratios → 4dp fixed
        out = canonical_json({"r": 0.75})
        assert "0.7500" in out

    def test_ratio_rounding(self):
        out = canonical_json({"r": 0.12345678})
        # canonicalize_value rounds to 4dp → 0.1235
        assert "0.1235" in out


class TestStringEncoding:
    def test_special_chars_escaped(self):
        out = canonical_json({"k": 'hello "world"'})
        assert '\\"' in out

    def test_newline_escaped(self):
        out = canonical_json({"k": "a\nb"})
        assert "\\n" in out

    def test_backslash_escaped(self):
        out = canonical_json({"k": "a\\b"})
        assert "\\\\" in out


# ============================================================
# § 2 — Determinism (R7 byte-equal)
# ============================================================

class TestCanonicalJsonDeterminism:
    def test_same_dict_produces_same_output(self):
        d = {"z": [3, 1, 2], "a": {"q": 1, "p": 2}, "m": frozenset({"b", "a"})}
        out1 = canonical_json(d)
        out2 = canonical_json(d)
        assert out1 == out2

    def test_reordered_dict_produces_same_output(self):
        # Python dict insertion order varies in user code; canonical must
        # normalize to lex-ASC regardless of insertion order.
        d1 = {"a": 1, "b": 2, "c": 3}
        d2 = {"c": 3, "b": 2, "a": 1}
        assert canonical_json(d1) == canonical_json(d2)

    def test_sha256_hex_determinism(self):
        assert sha256_hex("hello") == sha256_hex("hello")
        # And it's 64 hex chars
        assert len(sha256_hex("hello")) == 64

    def test_sha256_hex_different_for_different_inputs(self):
        assert sha256_hex("hello") != sha256_hex("world")


# ============================================================
# § 3 — C16CacheKeys validation
# ============================================================

class TestC16CacheKeysValidation:
    def _good_64_hex(self) -> str:
        return "a" * 64

    def test_valid_keys_accepted(self):
        keys = C16CacheKeys(
            upstream_cache_key=self._good_64_hex(),
            drawing_cache_key=self._good_64_hex(),
            full_cache_key=self._good_64_hex(),
        )
        assert keys.upstream_cache_key == self._good_64_hex()

    def test_short_key_rejected(self):
        with pytest.raises(C16ConfigurationError):
            C16CacheKeys(
                upstream_cache_key="abc",
                drawing_cache_key=self._good_64_hex(),
                full_cache_key=self._good_64_hex(),
            )

    def test_non_hex_chars_rejected(self):
        with pytest.raises(C16ConfigurationError):
            C16CacheKeys(
                upstream_cache_key="g" * 64,  # 'g' is not hex
                drawing_cache_key=self._good_64_hex(),
                full_cache_key=self._good_64_hex(),
            )

    def test_uppercase_hex_rejected(self):
        # Canonical hex is lowercase per hashlib.sha256().hexdigest()
        with pytest.raises(C16ConfigurationError):
            C16CacheKeys(
                upstream_cache_key="A" * 64,
                drawing_cache_key=self._good_64_hex(),
                full_cache_key=self._good_64_hex(),
            )


# ============================================================
# § 4 — config_signature_for excludes observability flags
# ============================================================

class TestConfigSignatureForExcludesObservability:
    def test_same_signature_regardless_of_phase_timings_flag(self):
        c_off = RenderingConfig(capture_phase_timings=False)
        c_on = RenderingConfig(capture_phase_timings=True)
        assert config_signature_for(c_off) == config_signature_for(c_on)

    def test_same_signature_regardless_of_readability_flag(self):
        c_off = RenderingConfig(capture_readability_diagnostics=False)
        c_on = RenderingConfig(capture_readability_diagnostics=True)
        assert config_signature_for(c_off) == config_signature_for(c_on)

    def test_different_signature_for_different_scale(self):
        c_50 = RenderingConfig(working_drawing_scale="1:50")
        c_75 = RenderingConfig(working_drawing_scale="1:75")
        assert config_signature_for(c_50) != config_signature_for(c_75)

    def test_different_signature_for_different_density(self):
        c_full = RenderingConfig(annotation_density="full")
        c_sparse = RenderingConfig(annotation_density="sparse")
        assert config_signature_for(c_full) != config_signature_for(c_sparse)


# ============================================================
# § 5 — canonical_replay_signature (R7)
# ============================================================

class TestCanonicalReplaySignature:
    def _common_kwargs(self, **overrides):
        defaults = dict(
            selection_replay_identity_canon={"sig": "abc"},
            floor_geometries_canon=[{"floor_level": 0}],
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            config_signature=sha256_hex("config"),
            schema_descriptor_digest=sha256_hex("schema"),
            upstream_advisory_flags_canon=[],
        )
        defaults.update(overrides)
        return defaults

    def test_returns_64_hex(self):
        sig = canonical_replay_signature(**self._common_kwargs())
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_determinism(self):
        sig1 = canonical_replay_signature(**self._common_kwargs())
        sig2 = canonical_replay_signature(**self._common_kwargs())
        assert sig1 == sig2

    def test_different_jurisdiction_changes_signature(self):
        # Note: we don't actually validate jurisdiction membership in
        # canonical_replay_signature; it just hashes whatever is passed.
        sig1 = canonical_replay_signature(**self._common_kwargs())
        sig2 = canonical_replay_signature(
            **self._common_kwargs(jurisdiction_id="some_other_id")
        )
        assert sig1 != sig2

    def test_different_domain_scope_changes_signature(self):
        sig1 = canonical_replay_signature(**self._common_kwargs())
        sig2 = canonical_replay_signature(
            **self._common_kwargs(declared_domain_scope="small_commercial_v1")
        )
        assert sig1 != sig2

    def test_different_schema_digest_changes_signature(self):
        sig1 = canonical_replay_signature(**self._common_kwargs())
        sig2 = canonical_replay_signature(
            **self._common_kwargs(schema_descriptor_digest=sha256_hex("other"))
        )
        assert sig1 != sig2


# ============================================================
# § 6 — presentation_signature (R32a/c)
# ============================================================

class TestPresentationSignature:
    def test_includes_canonical_as_prefix(self):
        # R32a: canonical comes first, presentation wraps around it.
        # Practical effect: changing the canonical changes the presentation.
        canon1 = sha256_hex("c1")
        canon2 = sha256_hex("c2")
        p1 = presentation_signature(canonical_replay_signature_value=canon1)
        p2 = presentation_signature(canonical_replay_signature_value=canon2)
        assert p1 != p2

    def test_same_canon_different_diagnostics_differs(self):
        # R32b: two bundles with same canonical CAN have different presentation
        canon = sha256_hex("c")
        p_no = presentation_signature(canonical_replay_signature_value=canon)
        p_with = presentation_signature(
            canonical_replay_signature_value=canon,
            readability_diagnostics_canon={"collision_count": 3},
        )
        assert p_no != p_with

    def test_phase_timings_changes_presentation_only(self):
        canon = sha256_hex("c")
        p1 = presentation_signature(canonical_replay_signature_value=canon)
        p2 = presentation_signature(
            canonical_replay_signature_value=canon,
            phase_timings_canon={"total_ms": 1500},
        )
        assert p1 != p2


# ============================================================
# § 7 — derive_c16_cache_keys triple-tier
# ============================================================

class TestDeriveCacheKeys:
    def _good_args(self, **overrides):
        defaults = dict(
            upstream_cache_key=sha256_hex("upstream"),
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            config_signature=sha256_hex("config"),
        )
        defaults.update(overrides)
        return defaults

    def test_returns_C16CacheKeys(self):
        keys = derive_c16_cache_keys(**self._good_args())
        assert isinstance(keys, C16CacheKeys)
        assert len(keys.drawing_cache_key) == 64
        assert len(keys.full_cache_key) == 64

    def test_upstream_passthrough(self):
        upstream_hex = sha256_hex("u1")
        keys = derive_c16_cache_keys(**self._good_args(upstream_cache_key=upstream_hex))
        assert keys.upstream_cache_key == upstream_hex

    def test_different_upstream_changes_all_downstream_keys(self):
        k1 = derive_c16_cache_keys(**self._good_args(upstream_cache_key=sha256_hex("u1")))
        k2 = derive_c16_cache_keys(**self._good_args(upstream_cache_key=sha256_hex("u2")))
        assert k1.upstream_cache_key != k2.upstream_cache_key
        assert k1.drawing_cache_key != k2.drawing_cache_key
        assert k1.full_cache_key != k2.full_cache_key

    def test_different_jurisdiction_changes_drawing_and_full(self):
        k1 = derive_c16_cache_keys(**self._good_args())
        k2 = derive_c16_cache_keys(**self._good_args(jurisdiction_id="other"))
        assert k1.upstream_cache_key == k2.upstream_cache_key  # same upstream
        assert k1.drawing_cache_key != k2.drawing_cache_key
        assert k1.full_cache_key != k2.full_cache_key

    def test_invalid_upstream_hex_rejected(self):
        with pytest.raises(C16ConfigurationError):
            derive_c16_cache_keys(**self._good_args(upstream_cache_key="short"))

    def test_determinism(self):
        k1 = derive_c16_cache_keys(**self._good_args())
        k2 = derive_c16_cache_keys(**self._good_args())
        assert k1 == k2


# ============================================================
# § 8 — canonicalize_value direct tests
# ============================================================

class TestCanonicalizeValue:
    def test_int_passthrough(self):
        assert canonicalize_value(42) == 42

    def test_str_normalized(self):
        # NFC normalization for unicode
        # Use an example: combined char vs decomposed
        # 'é' as composed (U+00E9) vs decomposed (U+0065 U+0301)
        decomposed = "e\u0301"
        composed = canonicalize_value(decomposed)
        # NFC composes
        assert composed == "\u00e9"

    def test_tuple_recursively_canonicalized(self):
        out = canonicalize_value((1, 2, "hello"))
        assert out == [1, 2, "hello"]

    def test_unsupported_type_rejected(self):
        class Foo:
            pass
        with pytest.raises(C16ConfigurationError):
            canonicalize_value(Foo())

    def test_enum_to_value(self):
        e = AuthorityKind.LOCALLY_DERIVED
        assert canonicalize_value(e) == "locally_derived"

    def test_dict_with_none_values_omits_them(self):
        out = canonicalize_value({"a": 1, "b": None, "c": 3})
        assert out == {"a": 1, "c": 3}
