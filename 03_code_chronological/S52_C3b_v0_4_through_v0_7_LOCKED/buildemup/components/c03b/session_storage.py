"""
C3b — Session persistence (SQLite WAL)
=========================================

Spec § 9.1 B-C3B-SESSION-PERSISTENCE-WAL-RETROFIT: SQLite WAL mode +
retry + corruption recovery, mirroring C3a's GateStateStorage
hardening (S6 ownership pattern).

Per spec § 3 Phase δ: 'Persist session to SQLite (WAL mode, per S6
ownership inheritance from C3a precedent).'

Storage schema:
  CREATE TABLE c3b_sessions (
    session_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    canonical_replay_signature TEXT NOT NULL,
    presentation_signature TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    last_updated_offset_ms INTEGER NOT NULL DEFAULT 0
  )

The payload_json is the full TradeoffSession serialized via
dataclasses.asdict + json.dumps. Recovery: load by session_id,
deserialize via dataclass reconstruction.

Rule 11 self-analysis:
  1. SQLite WAL has known performance characteristics. For C3b's
     session-state writes (1 write per user action, max 7 actions
     per session per iteration_cap), throughput is non-issue. We
     enable WAL primarily for crash safety (write-ahead log).
  2. The session_id is the natural primary key — UUID-based, no
     collisions. Concurrent updates to the same session_id is a
     user-flow violation (same user shouldn't have two parallel
     C3b sessions on the same brief); we use REPLACE semantics
     (last-write-wins) which matches the single-linear-history
     R16 invariant.
  3. Serialization uses cache_keys._canon for canonicalization. That
     ensures the SAME object always serializes to the SAME bytes —
     useful for verifying signatures match after deserialize/reserialize.
  4. Deserialization rebuilds dataclasses from dicts. We use a
     helper that walks the schema; the schema is stable per
     C3B_SESSION_SCHEMA_VERSION pin.
  5. Recovery path: if schema_version doesn't match
     C3B_SESSION_SCHEMA_VERSION, refuse to deserialize and raise
     SessionPersistenceError (caller decides retry / migrate / abort).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from .errors import CorruptionDetectedError, SessionPersistenceError
from .schema import TradeoffSession
from .versioning import C3B_SESSION_SCHEMA_VERSION


_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SEC = 0.05

# v0.6 B4 — event log + checkpoint hash chain
_GENESIS_CHECKPOINT_HASH: str = "0" * 64
_EVENT_TYPE_SESSION_STATE: str = "session_state_v0_6"
_EVENT_TYPE_MIGRATED_FROM_V0_5: str = "migrated_from_v0_5"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS c3b_sessions (
            session_id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            canonical_replay_signature TEXT NOT NULL,
            presentation_signature TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            last_updated_offset_ms INTEGER NOT NULL DEFAULT 0
        )
    """)
    # v0.6 B4 — append-only event log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS c3b_events (
            event_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_payload_json TEXT NOT NULL,
            parent_checkpoint_hash TEXT NOT NULL,
            this_checkpoint_hash TEXT NOT NULL,
            timestamp_offset_ms INTEGER NOT NULL,
            UNIQUE(session_id, sequence_number)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS c3b_events_by_session
        ON c3b_events(session_id, sequence_number)
    """)
    # v0.6 B4 — periodic snapshots
    conn.execute("""
        CREATE TABLE IF NOT EXISTS c3b_snapshots (
            session_id TEXT PRIMARY KEY,
            last_sequence_number INTEGER NOT NULL,
            snapshot_payload_json TEXT NOT NULL,
            snapshot_checkpoint_hash TEXT NOT NULL
        )
    """)
    conn.commit()


@contextmanager
def _open_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Open a SQLite connection with WAL mode. Retries on transient
    failures (e.g., database locked by another process)."""
    last_exc: Optional[Exception] = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            conn = sqlite3.connect(str(db_path), isolation_level=None)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                _ensure_schema(conn)
                yield conn
            finally:
                conn.close()
            return
        except sqlite3.OperationalError as e:
            last_exc = e
            time.sleep(_RETRY_BACKOFF_SEC * (2 ** attempt))
    raise SessionPersistenceError(
        f"Failed to open SQLite after {_RETRY_ATTEMPTS} attempts: {last_exc}",
        operation="open",
    )


# ============================================================
# § 0.5 — v0.6 B4 event log helpers (hash chain + corruption detection)
# ============================================================

def _canonical_event_payload(payload_obj: dict) -> str:
    """Deterministic JSON encoding of an event payload.
    Used as input to the checkpoint hash so the chain is reproducible."""
    return json.dumps(payload_obj, sort_keys=True, separators=(",", ":"))


def _compute_checkpoint_hash(
    *,
    parent_hash:     str,
    event_id:        str,
    event_type:      str,
    canonical_payload: str,
) -> str:
    """v0.6 R20 — checkpoint hash chain link.

    Returns sha256 hex of (parent || event_id || event_type || payload).
    The deterministic input means independent replays of the same
    event sequence produce identical chains. Any single-byte tamper
    breaks the chain at that point and every link after it.
    """
    h = hashlib.sha256()
    h.update(parent_hash.encode("utf-8"))
    h.update(b"\x00")    # field delimiter
    h.update(event_id.encode("utf-8"))
    h.update(b"\x00")
    h.update(event_type.encode("utf-8"))
    h.update(b"\x00")
    h.update(canonical_payload.encode("utf-8"))
    return h.hexdigest()


def _generate_event_id(session_id: str, sequence_number: int) -> str:
    """Deterministic-shaped event id: session_id + sequence_number + uuid4
    suffix so collisions can't happen across replay runs."""
    return f"evt_{session_id[:24]}_{sequence_number:08d}_{uuid.uuid4().hex[:12]}"


def _read_event_chain_tail(
    conn:        sqlite3.Connection,
    session_id:  str,
) -> tuple[Optional[str], int]:
    """Return (this_checkpoint_hash_of_latest_event, sequence_number)
    for the latest event of this session, or (None, -1) if none yet."""
    cur = conn.execute(
        """
        SELECT this_checkpoint_hash, sequence_number
        FROM c3b_events
        WHERE session_id = ?
        ORDER BY sequence_number DESC
        LIMIT 1
        """,
        (session_id,),
    )
    row = cur.fetchone()
    if row is None:
        return (None, -1)
    return (row[0], row[1])


def _append_session_state_event(
    conn:        sqlite3.Connection,
    session:     TradeoffSession,
    payload:     str,
    event_type:  str = _EVENT_TYPE_SESSION_STATE,
) -> tuple[str, str, int]:
    """Append one event recording the current session state to the
    event log. Returns (event_id, this_checkpoint_hash, sequence_number).

    Caller MUST be inside an open SQLite transaction; this function
    does not commit.
    """
    parent_hash, prev_seq = _read_event_chain_tail(conn, session.session_id)
    sequence_number = prev_seq + 1
    if parent_hash is None:
        parent_hash = _GENESIS_CHECKPOINT_HASH

    event_id = _generate_event_id(session.session_id, sequence_number)
    last_offset = (
        session.session_history[-1].timestamp_offset_ms
        if session.session_history else 0
    )
    # The event payload itself is just (canonical_replay_signature,
    # schema_version, payload_json). We do NOT duplicate the full
    # session payload here — the c3b_sessions row stores that. The
    # event payload is the audit/forensic record of WHAT signature
    # transitioned to.
    event_payload_obj = {
        "canonical_replay_signature": session.canonical_replay_signature,
        "presentation_signature":     session.presentation_signature,
        "schema_version":             session.c3b_schema_version,
        "current_status":             session.current_status,
        "iteration_count":            session.iteration_count,
        "session_history_length":     len(session.session_history),
        "last_timestamp_offset_ms":   last_offset,
    }
    canonical_payload = _canonical_event_payload(event_payload_obj)
    this_hash = _compute_checkpoint_hash(
        parent_hash=parent_hash,
        event_id=event_id,
        event_type=event_type,
        canonical_payload=canonical_payload,
    )
    conn.execute(
        """
        INSERT INTO c3b_events (
            event_id, session_id, sequence_number,
            event_type, event_payload_json,
            parent_checkpoint_hash, this_checkpoint_hash,
            timestamp_offset_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id, session.session_id, sequence_number,
            event_type, canonical_payload,
            parent_hash, this_hash, last_offset,
        ),
    )
    return (event_id, this_hash, sequence_number)


def _upsert_snapshot(
    conn:        sqlite3.Connection,
    session_id:  str,
    last_sequence_number: int,
    snapshot_payload_json: str,
    snapshot_checkpoint_hash: str,
) -> None:
    conn.execute(
        """
        INSERT INTO c3b_snapshots (
            session_id, last_sequence_number,
            snapshot_payload_json, snapshot_checkpoint_hash
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            last_sequence_number = excluded.last_sequence_number,
            snapshot_payload_json = excluded.snapshot_payload_json,
            snapshot_checkpoint_hash = excluded.snapshot_checkpoint_hash
        """,
        (session_id, last_sequence_number, snapshot_payload_json,
         snapshot_checkpoint_hash),
    )


def _verify_event_chain(
    conn:        sqlite3.Connection,
    session_id:  str,
) -> tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """v0.6 R20 — walk the event chain and verify hash integrity.

    Returns:
      (chain_valid, latest_hash, expected_canonical_sig, last_good_seq)

    chain_valid is True iff every link computes the expected hash.
    latest_hash is the this_checkpoint_hash of the last event.
    expected_canonical_sig is what the latest event claims the
      session's canonical_replay_signature should be.
    last_good_seq is the sequence_number of the last verified event
      (useful for recovery: roll back to this checkpoint).
    """
    cur = conn.execute(
        """
        SELECT event_id, sequence_number, event_type, event_payload_json,
               parent_checkpoint_hash, this_checkpoint_hash
        FROM c3b_events
        WHERE session_id = ?
        ORDER BY sequence_number ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    if not rows:
        # No events recorded — no claim to verify
        return (True, None, None, None)

    expected_parent = _GENESIS_CHECKPOINT_HASH
    last_good_seq: Optional[int] = None
    latest_hash: Optional[str] = None
    expected_canonical_sig: Optional[str] = None

    for (event_id, seq, event_type, payload_json,
         parent_hash, this_hash) in rows:
        if parent_hash != expected_parent:
            return (False, latest_hash, expected_canonical_sig, last_good_seq)
        computed = _compute_checkpoint_hash(
            parent_hash=parent_hash,
            event_id=event_id,
            event_type=event_type,
            canonical_payload=payload_json,
        )
        if computed != this_hash:
            return (False, latest_hash, expected_canonical_sig, last_good_seq)
        # Chain link OK
        try:
            decoded = json.loads(payload_json)
            sig_claim = decoded.get("canonical_replay_signature")
        except Exception:
            sig_claim = None
        expected_canonical_sig = sig_claim
        latest_hash = this_hash
        expected_parent = this_hash
        last_good_seq = seq

    return (True, latest_hash, expected_canonical_sig, last_good_seq)


# ============================================================
# § 1 — Serialization helpers
# ============================================================

def _serialize_session(session: TradeoffSession) -> str:
    """Serialize via dataclasses.asdict + json.dumps with sort_keys.

    Handles StrEnum and AuthorityKind (enum) via default encoder
    custom hook."""
    import dataclasses

    def _enc(o):
        # Enum / StrEnum
        if hasattr(o, "value") and not callable(o.value):
            return o.value
        # Sets → sorted lists
        if isinstance(o, (set, frozenset)):
            return sorted(o, key=lambda x: str(x))
        # Bytes → hex
        if isinstance(o, bytes):
            return o.hex()
        raise TypeError(f"Cannot serialize {type(o).__name__}")

    asdict = dataclasses.asdict(session)
    return json.dumps(asdict, sort_keys=True, default=_enc, separators=(",", ":"))


def _deserialize_session(payload_json: str) -> TradeoffSession:
    """Deserialize a TradeoffSession from JSON payload.

    Schema-version mismatch raises SessionPersistenceError per
    Rule 11 self-analysis pt 5."""
    raw = json.loads(payload_json)
    if raw.get("c3b_schema_version") != C3B_SESSION_SCHEMA_VERSION:
        raise SessionPersistenceError(
            f"Stored session schema_version="
            f"{raw.get('c3b_schema_version')!r} mismatches current "
            f"{C3B_SESSION_SCHEMA_VERSION}. Run a migration or refuse to load.",
            operation="deserialize",
        )

    # Reconstruct dataclass tree. Use a builder that walks each known
    # dataclass field — this is verbose but robust to dataclass renames.
    return _reconstruct_session(raw)


def _reconstruct_session(raw: dict) -> TradeoffSession:
    """Rebuild a TradeoffSession from a plain-dict payload.

    Walks the dataclass schema field-by-field, calling the dataclass
    constructors so __post_init__ invariants fire (defense-in-depth
    on stored data integrity)."""
    from .contracts import AttestedValue, AuthorityKind
    from .schema import (
        AdvisoryFlag,
        ApplyOutcome,
        ApplySpecification,
        CompatibilityAssertion,
        PropagationEdge,
        ComfortImpact,
        FinishSchedulePayload,
        GeometryLocalPayload,
        KickBackPayload,
        MutationEnvelope,
        ResolvedSelection,
        SessionTurn,
        SpaceImpact,
        SubsetRerunRequest,
        TopologyInvarianceResult,
        TweakOption,
        TweakOptionSet,
        TweakProvenance,
    )
    from buildemup.utils.confidence import Confidence
    from buildemup.utils.transparency import DerivationLine, TransparencyTriple

    def _tt(d):
        if d is None:
            return None
        return TransparencyTriple(
            label=d["label"],
            exact_value=d["exact_value"],
            unit=d["unit"],
            uncertainty_pct=d["uncertainty_pct"],
            confidence=Confidence(d["confidence"]),
            derivation=[DerivationLine(**dd) for dd in d["derivation"]],
            notes=list(d.get("notes", [])),
        )

    def _av(d):
        if d is None:
            return None
        return AttestedValue(
            value=d["value"],
            authority=AuthorityKind(d["authority"]),
            upstream_source=d.get("upstream_source"),
            derivation_note=d.get("derivation_note"),
        )

    def _si(d):
        if d is None:
            return None
        return SpaceImpact(
            per_room_sqft_delta=tuple(
                (t[0], t[1]) for t in d["per_room_sqft_delta"]
            ),
            total_sqft_delta=d["total_sqft_delta"],
            total_carpet_area_after=_av(d["total_carpet_area_after"]),
            advisory_note=d.get("advisory_note", ""),
        )

    def _ci(d):
        if d is None:
            return None
        return ComfortImpact(
            dimensions_affected=tuple(d["dimensions_affected"]),
            direction=d["direction"],
            magnitude=d["magnitude"],
            advisory_note=d.get("advisory_note", ""),
            # v0.5 A7 — emotional heuristic fields
            perceived_spaciousness=d.get("perceived_spaciousness"),
            arrival_impression=d.get("arrival_impression"),
            family_gathering_comfort=d.get("family_gathering_comfort"),
        )

    def _tir(d):
        if d is None:
            return None
        return TopologyInvarianceResult(
            source_topology=d["source_topology"],
            predicted_topology=d["predicted_topology"],
            invariance_preserved=d["invariance_preserved"],
            prediction_basis=d["prediction_basis"],
            advisory_note=d.get("advisory_note"),
            # v0.6 B3
            topology_divergence_score=d.get("topology_divergence_score"),
            continuity_subscores=d.get("continuity_subscores"),
        )

    def _pe(d):
        # v0.7 C1 — PropagationEdge deserializer
        return PropagationEdge(
            from_system=d["from_system"],
            to_system=d["to_system"],
            relationship_kind=d["relationship_kind"],
            advisory_note=d["advisory_note"],
        )

    def _ca(d):
        chain_raw = d.get("propagation_chain")
        chain = None
        if chain_raw is not None:
            chain = tuple(_pe(e) for e in chain_raw)
        return CompatibilityAssertion(
            against_applied_tweak_id=d["against_applied_tweak_id"],
            compatibility_kind=d["compatibility_kind"],
            result=d["result"],
            advisory_note=d.get("advisory_note"),
            # v0.7 C1
            propagation_chain=chain,
        )

    def _srr(d):
        if d is None:
            return None
        return SubsetRerunRequest(
            trigger_tweak_id=d["trigger_tweak_id"],
            trigger_tweak_category=d["trigger_tweak_category"],
            components_to_rerun=tuple(d["components_to_rerun"]),
            downstream_impact_set=tuple(d["downstream_impact_set"]),
            topology_invariance_check=_tir(d["topology_invariance_check"]),
            expected_completion_seconds=d["expected_completion_seconds"],
            rerun_anchor=d["rerun_anchor"],
            compatibility_assertions=tuple(
                _ca(x) for x in d.get("compatibility_assertions", [])
            ),
        )

    def _glp(d):
        if d is None:
            return None
        return GeometryLocalPayload(
            new_room_function_assignments=tuple(
                (t[0], t[1]) for t in d["new_room_function_assignments"]
            ),
            new_door_placements_replace=tuple(d["new_door_placements_replace"]),
            new_window_assignments=tuple(
                (t[0], int(t[1])) for t in d["new_window_assignments"]
            ),
            advisory_note=d.get("advisory_note", ""),
        )

    def _fsp(d):
        if d is None:
            return None
        return FinishSchedulePayload(
            room_finish_overrides=tuple(
                (t[0], t[1], t[2]) for t in d["room_finish_overrides"]
            ),
            advisory_note=d.get("advisory_note", ""),
        )

    def _asp(d):
        return ApplySpecification(
            mutation_kind=d["mutation_kind"],
            geometry_local_payload=_glp(d.get("geometry_local_payload")),
            subset_rerun_payload=_srr(d.get("subset_rerun_payload")),
            finish_schedule_payload=_fsp(d.get("finish_schedule_payload")),
        )

    def _tp(d):
        return TweakProvenance(
            motivated_by_check_id=d.get("motivated_by_check_id"),
            motivated_by_grid_cell_id=d.get("motivated_by_grid_cell_id"),
            motivated_by_orientation=d.get("motivated_by_orientation"),
            generation_basis=d.get("generation_basis", ""),
        )

    def _kbp(d):
        if d is None:
            return None
        return KickBackPayload(
            target_brief_field=d["target_brief_field"],
            target_brief_field_advisory=d["target_brief_field_advisory"],
            user_requested_change=d["user_requested_change"],
            proposed_change_summary=d["proposed_change_summary"],
        )

    def _me(d):
        return MutationEnvelope(
            envelope_id=d["envelope_id"],
            requested_change_summary=d["requested_change_summary"],
            classification=d["classification"],
            why_not_a_tweak=d["why_not_a_tweak"],
            suggested_pathway=d["suggested_pathway"],
            estimated_pathway_effort=d["estimated_pathway_effort"],
            advisory_note=d["advisory_note"],
            kick_back_payload=_kbp(d.get("kick_back_payload")),
            # v0.5 A6
            speculative_preview_text=d.get("speculative_preview_text"),
        )

    def _to(d):
        return TweakOption(
            tweak_id=d["tweak_id"],
            tweak_category=d["tweak_category"],
            severity_tier=d["severity_tier"],
            affected_room_ids=tuple(d["affected_room_ids"]),
            affected_grid_cells=tuple(d["affected_grid_cells"]),
            description=d["description"],
            cost_impact=_tt(d["cost_impact"]),
            space_impact=_si(d["space_impact"]),
            comfort_impact=_ci(d["comfort_impact"]),
            problem_report_links=tuple(d["problem_report_links"]),
            recommendation_flag=d["recommendation_flag"],
            apply_specification=_asp(d["apply_specification"]),
            provenance=_tp(d["provenance"]),
            presented_count=d.get("presented_count", 0),
        )

    def _tos(d):
        return TweakOptionSet(
            layout_id=d["layout_id"],
            layout_archetype=d["layout_archetype"],
            source_problem_report_id=d["source_problem_report_id"],
            tweaks=tuple(_to(t) for t in d["tweaks"]),
            overall_advisory_note=d["overall_advisory_note"],
        )

    def _ao(d):
        if d is None:
            return None
        return ApplyOutcome(
            apply_status=d["apply_status"],
            error_summary=d.get("error_summary"),
            new_layout_signature=d.get("new_layout_signature"),
            new_problem_report_id=d.get("new_problem_report_id"),
            regression_detected=d.get("regression_detected", False),
            newly_critical_check_ids=tuple(d.get("newly_critical_check_ids", [])),
        )

    def _st(d):
        return SessionTurn(
            turn_id=d["turn_id"],
            iteration_index=d["iteration_index"],
            timestamp_offset_ms=d["timestamp_offset_ms"],
            presented_tweaks=tuple(d["presented_tweaks"]),
            user_action=d["user_action"],
            chosen_tweak_id=d.get("chosen_tweak_id"),
            apply_outcome=_ao(d.get("apply_outcome")),
            post_turn_status=d.get("post_turn_status", "open_for_user_input"),
            # v0.5 A4
            strategic_advisory_text=d.get("strategic_advisory_text"),
        )

    def _rs(d):
        if d is None:
            return None
        return ResolvedSelection(
            chosen_layout_id=d["chosen_layout_id"],
            chosen_layout_archetype=d["chosen_layout_archetype"],
            applied_tweaks=tuple(d["applied_tweaks"]),
            final_layout_signature=d["final_layout_signature"],
            final_problem_report_id=d.get("final_problem_report_id"),
            total_cost_delta=_tt(d.get("total_cost_delta")),
            total_space_delta=_si(d.get("total_space_delta")),
            final_handoff_advisory=d.get("final_handoff_advisory", ""),
        )

    def _af(d):
        return AdvisoryFlag(
            flag_id=d["flag_id"],
            kind=d["kind"],
            advisory_note=d["advisory_note"],
            related_ids=tuple(d.get("related_ids", [])),
        )

    return TradeoffSession(
        session_id=raw["session_id"],
        source_selection_result_id=raw["source_selection_result_id"],
        source_brief_signature=raw["source_brief_signature"],
        source_plot_analysis_id=raw["source_plot_analysis_id"],
        c3b_version=raw["c3b_version"],
        c3b_schema_version=raw["c3b_schema_version"],
        jurisdiction_profile_id=raw["jurisdiction_profile_id"],
        tweak_option_sets=tuple(_tos(s) for s in raw["tweak_option_sets"]),
        session_history=tuple(_st(t) for t in raw["session_history"]),
        iteration_count=raw["iteration_count"],
        iteration_cap=raw["iteration_cap"],
        current_status=raw["current_status"],
        canonical_replay_signature=raw["canonical_replay_signature"],
        presentation_signature=raw["presentation_signature"],
        schema_descriptor_digest=raw["schema_descriptor_digest"],
        resolved_selection=_rs(raw.get("resolved_selection")),
        advisory_flags=tuple(_af(f) for f in raw.get("advisory_flags", [])),
        mutation_envelopes=tuple(_me(e) for e in raw.get("mutation_envelopes", [])),
        # v0.5 A2
        medium_tweak_count_since_full_recompute=raw.get(
            "medium_tweak_count_since_full_recompute", 0,
        ),
        # v0.6 B1
        extension_metadata=raw.get("extension_metadata"),
    )


# ============================================================
# § 2 — Storage API
# ============================================================

class C3bSessionStorage:
    """Persistent session storage backed by SQLite WAL.

    Usage:
        storage = C3bSessionStorage(Path("/tmp/c3b.db"))
        storage.save(session)
        restored = storage.load(session.session_id)
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        # Touch the DB file + ensure schema
        with _open_connection(self.db_path):
            pass

    def save(self, session: TradeoffSession) -> None:
        """Persist a session.

        v0.6 B4 — three writes atomically within one SQLite transaction:
          1. INSERT OR REPLACE into c3b_sessions (fast-read path, v0.5)
          2. INSERT into c3b_events (append-only event log)
          3. UPSERT into c3b_snapshots (resume fast-path)

        All three commit together. Partial writes are impossible under
        SQLite WAL transaction guarantees.
        """
        payload = _serialize_session(session)
        last_offset = (
            session.session_history[-1].timestamp_offset_ms
            if session.session_history else 0
        )
        try:
            with _open_connection(self.db_path) as conn:
                # Open explicit transaction (autocommit was on)
                conn.execute("BEGIN IMMEDIATE")
                try:
                    # 1. Single-row fast-read store (v0.5)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO c3b_sessions (
                            session_id, schema_version,
                            canonical_replay_signature, presentation_signature,
                            payload_json, last_updated_offset_ms
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session.session_id,
                            session.c3b_schema_version,
                            session.canonical_replay_signature,
                            session.presentation_signature,
                            payload,
                            last_offset,
                        ),
                    )
                    # 2. Append event to event log
                    event_id, this_hash, seq_num = _append_session_state_event(
                        conn, session, payload,
                    )
                    # 3. Update snapshot (the latest known-good state)
                    _upsert_snapshot(
                        conn,
                        session_id=session.session_id,
                        last_sequence_number=seq_num,
                        snapshot_payload_json=payload,
                        snapshot_checkpoint_hash=this_hash,
                    )
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to save session {session.session_id!r}: {e}",
                operation="write",
            ) from e

    def load(
        self,
        session_id:   str,
        *,
        verify_chain: bool = True,
    ) -> Optional[TradeoffSession]:
        """Load a session by id. Returns None if not found.

        v0.6 B4 — when verify_chain=True (default), the event log
        hash chain is walked and the canonical_replay_signature of
        the loaded session is checked against the latest event's
        claim. Mismatch raises CorruptionDetectedError.

        Pass verify_chain=False to skip verification (for forensic
        loads of known-corrupt sessions).
        """
        try:
            with _open_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT payload_json FROM c3b_sessions WHERE session_id = ?",
                    (session_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                session = _deserialize_session(row[0])

                if verify_chain:
                    (chain_valid, latest_hash, expected_sig, last_good_seq) = (
                        _verify_event_chain(conn, session_id)
                    )
                    if not chain_valid:
                        raise CorruptionDetectedError(
                            f"Event-log chain integrity broken for session "
                            f"{session_id!r}. The session row loaded but its "
                            f"event history does not verify. Last verified "
                            f"sequence: {last_good_seq}. Recovery options: "
                            f"load with verify_chain=False for forensic "
                            f"inspection, or roll back to the last snapshot.",
                            session_id=session_id,
                            last_known_good_sequence=last_good_seq,
                        )
                    if expected_sig is not None and (
                        expected_sig != session.canonical_replay_signature
                    ):
                        raise CorruptionDetectedError(
                            f"Session {session_id!r} canonical_replay_signature "
                            f"mismatch: loaded session claims "
                            f"{session.canonical_replay_signature!r}, "
                            f"event log claims {expected_sig!r}. The single-"
                            f"row store may have been mutated outside the "
                            f"event log.",
                            session_id=session_id,
                            expected_hash=expected_sig,
                            observed_hash=session.canonical_replay_signature,
                            last_known_good_sequence=last_good_seq,
                        )
                return session
        except CorruptionDetectedError:
            raise
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to load session {session_id!r}: {e}",
                operation="read",
            ) from e

    def delete(self, session_id: str) -> bool:
        """Delete a session by id. Returns True if deleted, False if absent.

        v0.6 B4 — also clears event log and snapshot for the session
        (all within one transaction).
        """
        try:
            with _open_connection(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    cur = conn.execute(
                        "DELETE FROM c3b_sessions WHERE session_id = ?",
                        (session_id,),
                    )
                    deleted = cur.rowcount > 0
                    conn.execute(
                        "DELETE FROM c3b_events WHERE session_id = ?",
                        (session_id,),
                    )
                    conn.execute(
                        "DELETE FROM c3b_snapshots WHERE session_id = ?",
                        (session_id,),
                    )
                    conn.execute("COMMIT")
                    return deleted
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to delete session {session_id!r}: {e}",
                operation="delete",
            ) from e

    def verify_session_integrity(
        self,
        session_id: str,
    ) -> tuple[bool, Optional[int]]:
        """v0.6 B4 — public API for explicit chain verification.

        Returns (chain_valid, last_good_sequence_number). Useful for
        admin tools / health checks without triggering a load.
        """
        try:
            with _open_connection(self.db_path) as conn:
                chain_valid, _, _, last_good_seq = _verify_event_chain(
                    conn, session_id,
                )
                return (chain_valid, last_good_seq)
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to verify session {session_id!r}: {e}",
                operation="read",
            ) from e

    def event_count(self, session_id: str) -> int:
        """v0.6 B4 — count events in the log for a given session.
        Useful for tests + monitoring."""
        try:
            with _open_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM c3b_events WHERE session_id = ?",
                    (session_id,),
                )
                return cur.fetchone()[0]
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to count events for {session_id!r}: {e}",
                operation="read",
            ) from e

    def list_session_ids(self) -> tuple[str, ...]:
        """List all stored session ids (lex-ASC for replay determinism)."""
        try:
            with _open_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT session_id FROM c3b_sessions ORDER BY session_id ASC"
                )
                return tuple(row[0] for row in cur.fetchall())
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to list sessions: {e}",
                operation="read",
            ) from e


__all__ = [
    "C3bSessionStorage",
    "_serialize_session",
    "_deserialize_session",
    "_reconstruct_session",
]
