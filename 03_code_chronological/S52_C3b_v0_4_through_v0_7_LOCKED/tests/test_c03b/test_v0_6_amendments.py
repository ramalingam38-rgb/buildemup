"""
Tests for v0.6 LOCKED amendments to C3b.

Covers B1, B2, B3, B4 + R19 (extension_metadata excluded from sig)
+ R20 (event log checkpoint hash chain integrity).
"""
from __future__ import annotations

import dataclasses
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from buildemup.components.c03b import (
    C3bRuntimeConfig, DEFAULT_CONFIG, UserActionRequest, start_session,
    apply_user_action_orchestrated,
)
from buildemup.components.c03b.advisory_lint import (
    AdvisoryLintError,
    LintAuditEntry,
    LintTier,
    is_advisory_clean,
    lint_advisory_text,
    lint_advisory_text_tiered,
)
from buildemup.components.c03b.cache_keys import (
    compute_canonical_replay_signature,
)
from buildemup.components.c03b.errors import CorruptionDetectedError
from buildemup.components.c03b.phases.severity import (
    SeverityContext,
    promote_severity,
)
from buildemup.components.c03b.schema import TopologyInvarianceResult
from buildemup.components.c03b.session_storage import C3bSessionStorage
from buildemup.components.c03b.versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    TOPOLOGY_DIVERGENCE_HEAVY_FLOOR,
    TOPOLOGY_DIVERGENCE_MEDIUM_CAP,
)

from .fixtures import make_bundle_3_layouts_happy_path


# ============================================================
# Foundation — version bump
# ============================================================

def test_v0_6_amendments_still_active_at_or_after_v0_6():
    """v0.6 features survive in v0.7+. The version-pin tests live in
    test_versioning.py; this checks the v0.6 amendment surface is still
    intact at whatever the current version is."""
    from buildemup.components.c03b.versioning import _parse_version
    assert _parse_version(C3B_VERSION) >= _parse_version("v0.6.LOCKED")


def test_v0_6_schema_version_at_or_above_4():
    """v0.6 introduced schema_version=4. v0.7 and beyond MUST be >=4."""
    assert C3B_SESSION_SCHEMA_VERSION >= 4


def test_v0_6_topology_divergence_constants():
    assert TOPOLOGY_DIVERGENCE_MEDIUM_CAP == 0.3
    assert TOPOLOGY_DIVERGENCE_HEAVY_FLOOR == 0.7
    assert TOPOLOGY_DIVERGENCE_MEDIUM_CAP < TOPOLOGY_DIVERGENCE_HEAVY_FLOOR


# ============================================================
# B1 — extension_metadata channel
# ============================================================

def test_b1_extension_metadata_default_none():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    assert sess.extension_metadata is None


def test_b1_extension_metadata_can_be_attached():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    sess2 = dataclasses.replace(
        sess,
        extension_metadata={"research_run_id": "exp-001", "model": "ablation_A"},
    )
    assert sess2.extension_metadata == {
        "research_run_id": "exp-001", "model": "ablation_A",
    }


def test_b1_extension_metadata_rejects_more_than_32_keys():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    with pytest.raises(ValueError, match="32-key ceiling"):
        dataclasses.replace(
            sess,
            extension_metadata={f"k{i}": "v" for i in range(33)},
        )


def test_b1_extension_metadata_rejects_oversized_value():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    with pytest.raises(ValueError, match="2048-char ceiling"):
        dataclasses.replace(sess, extension_metadata={"k": "x" * 2049})


def test_b1_extension_metadata_lints_keys_and_values():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    with pytest.raises(AdvisoryLintError):
        dataclasses.replace(
            sess, extension_metadata={"verdict": "the system decided"},
        )


def test_r19_extension_metadata_excluded_from_canonical_sig():
    """R19 — extension_metadata MUST NOT affect canonical_replay_signature."""
    bundle = make_bundle_3_layouts_happy_path()
    sess_a = start_session(bundle, DEFAULT_CONFIG)
    sess_b = dataclasses.replace(
        sess_a,
        extension_metadata={"different": "annotation"},
    )
    sig_a = compute_canonical_replay_signature(session=sess_a, strict_mode="strict")
    sig_b = compute_canonical_replay_signature(session=sess_b, strict_mode="strict")
    assert sig_a == sig_b


# ============================================================
# B2 — advisory lint severity tiers
# ============================================================

def test_b2_hard_block_still_raises_v0_5_compat():
    with pytest.raises(AdvisoryLintError):
        lint_advisory_text("you must accept this tweak", field_name="t")


def test_b2_is_advisory_clean_unchanged_for_v0_5():
    """REVIEW_NEEDED and WARN do not mark text 'unclean' — only HARD_BLOCK does."""
    assert is_advisory_clean("a normal note") is True
    assert is_advisory_clean("you should accept") is False    # HARD_BLOCK
    # bare 'best' is REVIEW_NEEDED — does NOT make text unclean
    assert is_advisory_clean("this is the best fit") is True


def test_b2_tiered_returns_review_for_bare_best():
    entry = lint_advisory_text_tiered("This is the best option for your needs.")
    assert entry is not None
    assert entry.tier == LintTier.REVIEW_NEEDED
    assert entry.offending_phrase == "best"


def test_b2_tiered_returns_review_for_bare_wrong():
    entry = lint_advisory_text_tiered("Picking this color would feel wrong.")
    assert entry is not None
    assert entry.tier == LintTier.REVIEW_NEEDED


def test_b2_tiered_hard_block_for_composite():
    """'best choice' still HARD_BLOCKs even though bare 'best' is REVIEW."""
    with pytest.raises(AdvisoryLintError):
        lint_advisory_text_tiered("This is the best choice for you.")


def test_b2_word_boundary_no_false_positive_rejected():
    """v0.6 B2 — single-word matching uses \\b so 'unrejected_status'
    does NOT match 'rejected'."""
    # find_banned_phrase + lint_advisory_text are HARD-only;
    # they should NOT trigger on a token-internal occurrence
    assert is_advisory_clean("the unrejected_status field is set") is True


def test_b2_word_boundary_yes_match_rejected_as_word():
    """'rejected' surrounded by word boundaries SHOULD HARD-block."""
    with pytest.raises(AdvisoryLintError):
        lint_advisory_text("the tweak was rejected by the system")


def test_b2_tiered_returns_none_for_clean_text():
    assert lint_advisory_text_tiered("A well-suited option.") is None


# ============================================================
# B3 — graded topology divergence
# ============================================================

def test_b3_v0_5_fallback_when_score_none():
    """topology_divergence_score=None preserves v0.5 boolean-only HEAVY."""
    ctx = SeverityContext(topology_classification_change=True)
    assert promote_severity(default_severity="medium", context=ctx) == "heavy"


def test_b3_low_divergence_demotes_to_medium():
    ctx = SeverityContext(
        topology_classification_change=True,
        topology_divergence_score=0.15,
    )
    assert promote_severity(default_severity="medium", context=ctx) == "medium"


def test_b3_mid_divergence_stays_heavy():
    ctx = SeverityContext(
        topology_classification_change=True,
        topology_divergence_score=0.5,
    )
    assert promote_severity(default_severity="medium", context=ctx) == "heavy"


def test_b3_high_divergence_stays_heavy():
    ctx = SeverityContext(
        topology_classification_change=True,
        topology_divergence_score=0.85,
    )
    assert promote_severity(default_severity="medium", context=ctx) == "heavy"


def test_b3_low_divergence_with_two_factors_escalates_to_heavy():
    """Even with low topology divergence, if 2+ OTHER structural factors
    cross threshold, severity escalates to HEAVY."""
    ctx = SeverityContext(
        topology_classification_change=True,
        topology_divergence_score=0.15,
        load_bearing_wall_involvement=True,
        structural_bay_boundary_cross=True,
    )
    assert promote_severity(default_severity="medium", context=ctx) == "heavy"


def test_b3_topology_invariance_rejects_score_out_of_range():
    with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\]"):
        TopologyInvarianceResult(
            source_topology="bay_centric",
            predicted_topology="corridor_centric",
            invariance_preserved=False,
            prediction_basis="heuristic_weak",
            advisory_note="topology classification differs after the change.",
            topology_divergence_score=1.5,
        )


def test_b3_topology_invariance_rejects_invariance_preserved_with_nonzero_score():
    with pytest.raises(ValueError, match="topology_divergence_score=0.0 or None"):
        TopologyInvarianceResult(
            source_topology="bay_centric",
            predicted_topology="bay_centric",
            invariance_preserved=True,
            prediction_basis="mutation_local_only",
            topology_divergence_score=0.4,
        )


def test_b3_continuity_subscores_validation():
    """Subscore keys must be one of: circulation/structural/experiential/plumbing."""
    with pytest.raises(ValueError, match="unknown keys"):
        TopologyInvarianceResult(
            source_topology="bay_centric",
            predicted_topology="corridor_centric",
            invariance_preserved=False,
            prediction_basis="heuristic_weak",
            advisory_note="topology classification differs after the change.",
            topology_divergence_score=0.5,
            continuity_subscores={"circulation": 0.9, "made_up": 0.5},
        )


# ============================================================
# B4 — event-sourced persistence
# ============================================================

@pytest.fixture
def tmp_storage(tmp_path):
    """Fresh C3bSessionStorage per test."""
    db = tmp_path / "c3b_v06_test.db"
    return C3bSessionStorage(db)


def test_b4_save_appends_event(tmp_storage):
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)
    assert tmp_storage.event_count(sess.session_id) == 1


def test_b4_multiple_saves_extend_event_log(tmp_storage):
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)
    target = sess.tweak_option_sets[0].tweaks[0]
    sess2 = apply_user_action_orchestrated(
        sess,
        UserActionRequest("rejected_tweak", chosen_tweak_id=target.tweak_id),
        DEFAULT_CONFIG,
    )
    tmp_storage.save(sess2)
    assert tmp_storage.event_count(sess.session_id) == 2


def test_b4_chain_integrity_passes_after_clean_saves(tmp_storage):
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)
    target = sess.tweak_option_sets[0].tweaks[0]
    sess2 = apply_user_action_orchestrated(
        sess,
        UserActionRequest("rejected_tweak", chosen_tweak_id=target.tweak_id),
        DEFAULT_CONFIG,
    )
    tmp_storage.save(sess2)
    valid, last_good_seq = tmp_storage.verify_session_integrity(sess.session_id)
    assert valid is True
    assert last_good_seq == 1


def test_b4_load_roundtrip_with_chain_verification(tmp_storage):
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)
    loaded = tmp_storage.load(sess.session_id)
    assert loaded is not None
    assert loaded.canonical_replay_signature == sess.canonical_replay_signature


def test_b4_payload_tamper_detected(tmp_storage):
    """Tampering with payload_json after save() must be detected at load()."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)

    # Tamper with the payload_json column directly
    conn = sqlite3.connect(str(tmp_storage.db_path))
    cur = conn.execute(
        "SELECT payload_json FROM c3b_sessions WHERE session_id = ?",
        (sess.session_id,),
    )
    pj = json.loads(cur.fetchone()[0])
    pj["canonical_replay_signature"] = "0" * 64
    conn.execute(
        "UPDATE c3b_sessions SET payload_json = ? WHERE session_id = ?",
        (json.dumps(pj), sess.session_id),
    )
    conn.commit()
    conn.close()

    with pytest.raises(CorruptionDetectedError):
        tmp_storage.load(sess.session_id)


def test_b4_event_log_tamper_detected(tmp_storage):
    """Tampering with c3b_events.event_payload_json must break the
    hash chain at load."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)

    target = sess.tweak_option_sets[0].tweaks[0]
    sess2 = apply_user_action_orchestrated(
        sess,
        UserActionRequest("rejected_tweak", chosen_tweak_id=target.tweak_id),
        DEFAULT_CONFIG,
    )
    tmp_storage.save(sess2)

    # Tamper with event 1
    conn = sqlite3.connect(str(tmp_storage.db_path))
    conn.execute(
        "UPDATE c3b_events SET event_payload_json = ? "
        "WHERE session_id = ? AND sequence_number = ?",
        ('{"tampered":true}', sess.session_id, 1),
    )
    conn.commit()
    conn.close()

    with pytest.raises(CorruptionDetectedError) as exc_info:
        tmp_storage.load(sess.session_id)
    # last_known_good_sequence should be the last verified one (0)
    assert exc_info.value.last_known_good_sequence == 0


def test_b4_forensic_load_skips_verification(tmp_storage):
    """verify_chain=False allows loading even after corruption."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)

    # Tamper
    conn = sqlite3.connect(str(tmp_storage.db_path))
    cur = conn.execute(
        "SELECT payload_json FROM c3b_sessions WHERE session_id = ?",
        (sess.session_id,),
    )
    pj = json.loads(cur.fetchone()[0])
    pj["canonical_replay_signature"] = "0" * 64
    conn.execute(
        "UPDATE c3b_sessions SET payload_json = ? WHERE session_id = ?",
        (json.dumps(pj), sess.session_id),
    )
    conn.commit()
    conn.close()

    # Forensic load — should NOT raise
    forensic = tmp_storage.load(sess.session_id, verify_chain=False)
    assert forensic is not None
    assert forensic.canonical_replay_signature == "0" * 64


def test_b4_delete_clears_all_three_tables(tmp_storage):
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)
    assert tmp_storage.event_count(sess.session_id) == 1

    deleted = tmp_storage.delete(sess.session_id)
    assert deleted is True
    assert tmp_storage.event_count(sess.session_id) == 0
    assert tmp_storage.load(sess.session_id, verify_chain=False) is None


def test_b4_genesis_hash_for_first_event(tmp_storage):
    """First event's parent_checkpoint_hash MUST be the genesis (64 zeros)."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)
    conn = sqlite3.connect(str(tmp_storage.db_path))
    cur = conn.execute(
        "SELECT parent_checkpoint_hash FROM c3b_events "
        "WHERE session_id = ? AND sequence_number = 0",
        (sess.session_id,),
    )
    parent = cur.fetchone()[0]
    conn.close()
    assert parent == "0" * 64


def test_b4_chain_link_correctly_references_prior_hash(tmp_storage):
    """Event N's parent_checkpoint_hash MUST equal event N-1's this_checkpoint_hash."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    tmp_storage.save(sess)
    target = sess.tweak_option_sets[0].tweaks[0]
    sess2 = apply_user_action_orchestrated(
        sess,
        UserActionRequest("rejected_tweak", chosen_tweak_id=target.tweak_id),
        DEFAULT_CONFIG,
    )
    tmp_storage.save(sess2)

    conn = sqlite3.connect(str(tmp_storage.db_path))
    cur = conn.execute(
        "SELECT sequence_number, parent_checkpoint_hash, this_checkpoint_hash "
        "FROM c3b_events WHERE session_id = ? ORDER BY sequence_number ASC",
        (sess.session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    assert len(rows) == 2
    seq0, parent0, this0 = rows[0]
    seq1, parent1, this1 = rows[1]
    assert seq0 == 0 and parent0 == "0" * 64
    assert seq1 == 1
    assert parent1 == this0    # chain link
