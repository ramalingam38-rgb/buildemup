# AUDIT CHECK — spec-compliance line-by-line for S40-continuation

This audit verifies the LOCKED specs are self-consistent and that the cross-spec contracts hold.

## Spec #1 `MultiFloorDwellingBrief v0.5 LOCKED`

- ✅ Schema: `floors: tuple[FloorRoomBrief, ...]` + `master_bedroom_floor_label: str` + `master_bedroom_selector: Literal["first_bedroom"] = "first_bedroom"`.
- ✅ 6 invariants MFDB-1 through MFDB-6 enumerated in § 3.2.
- ✅ Normalization at construction via `object.__setattr__` (§ 3.1). Module function `_normalize_label`.
- ✅ Helpers: `is_multi_floor` (property → True), `get_floor`, `floor_labels`, `floor_has_master`, `iter_floors_with_master_flag`, `with_master_on` (§ 3.3).
- ✅ 15 backlog items B-MFDB-A through O enumerated in § 7.
- ✅ Test budget ~45 tests in § 5.

## Spec #2 `C9 Amendment v0.11 LOCKED`

- ✅ Adds `has_master_bedroom: bool = True` to FloorRoomBrief (§ 3).
- ✅ Modifies C9 `_materialise_rooms` lines 498 (bedroom) and 548 (bathroom): `is_master = (i == 0) and brief.has_master_bedroom` (§ 3.7).
- ✅ § 3.4 bedroom-perspective naming rationale preserved.
- ✅ § 3.9 orchestration-contextual metadata framing with worked positive/negative examples preserved.
- ✅ § 3.10 trust-boundary delegation: "C9 trusts upstream orchestration; Spec #4 is expected to own the assertion before downstream scoring/caching/persistence" — **superseded by Spec #3 v0.3 MFWZP-5/6 construction-time enforcement** (which Spec #4 v1.6 § 3.9 explicitly acknowledges).
- ✅ 7 backlog items B-C9-A through G enumerated in § 7.
- ✅ ~9 new tests budgeted in § 5.

## Spec #3 `MultiFloorWetZonePlannedCandidate v0.3 LOCKED`

- ✅ Schema: `floors: tuple[WetZonePlannedCandidate, ...]` + `master_bedroom_floor_label: str`.
- ✅ Per-floor labels DERIVED from ancestry path `f.room_sized_candidate.provenance.floor_label` (empirically-verified after v0.1 schema-drift fix; § 3.3).
- ✅ 6 invariants MFWZP-1 through MFWZP-6 enumerated in § 3.2.
- ✅ MFWZP-5 + MFWZP-6 UPGRADE Spec #2 v0.11 § 3.10 trust boundary from "Spec #4 expected to own" to "Spec #3 type-construction enforces."
- ✅ Two mutation helpers: `with_floor_replaced(label, new_wzpc)` (single-floor ops M1-M7/M9) and `with_master_on(new_label, new_per_floor_candidates)` (M8 dwelling-level swap).
- ✅ NO provenance field (defers to C11a lineage).
- ✅ NO selector field (inherits via ancestry).
- ✅ Truth-arbitration policy: emitted room graph is canonical (§ 3.2 + § 3.10).
- ✅ § 3.10 dual-role acknowledgement (passive container + correctness authority + aggregate root).
- ✅ 12 backlog items B-MFWZP-A through L enumerated in § 7.

## Spec #4 `C11A Amendment v1.6 LOCKED`

- ✅ Orchestrator entry: dispatch via `_is_multi_floor()` + new `_validate_multi_floor_protocol()` + `_validate_multi_floor_alignment()` pre-flights (§ 3.1).
- ✅ Tier A + Tier B M6/M7a/M7b: bipartite operator+floor interleaving (§ 3.2 + § 3.3). Bounded imbalance ≤ 1, starvation-free.
- ✅ M8 real impl: cyclic deterministic target selection `sorted_targets[(generation + operator_index) % N]` (§ 3.4).
- ✅ Signature derivation extended with `multi_floor_sig_schema=v1` prefix (§ 3.5).
- ✅ Cache key version bumps "v1.0.0" → "v1.3.0" single-step (§ 3.6).
- ✅ Family aggregation label-preserving `multi_floor:ground=A|first=B` (§ 3.7).
- ✅ Lineage `floor_label_affected: str | None` field (§ 3.8).
- ✅ Trust boundary owned by Spec #3 construction guard + pipeline failure-mode handler (§ 3.9). NO redundant assertion.
- ✅ `affected_floor_set(operator, source, *, direct_floor_label, new_master_floor_label) -> frozenset[FloorImpact]` split-kwarg API (§ 3.11).
- ✅ FloorImpact structured return: `label`, `kind` (direct/indirect), `requires_cascade`, `requires_validation_only`.
- ✅ Refined M8 failure taxonomy: `no_viable_master_target` / `c9_generation_failed` / `c10_validation_failed` / `orchestration_state_drift:mfwzp1..6` (§ 3.4).
- ✅ Determinism tier-table (§ 3.4.1): Tier 1 structural identity → cache; Tier 2 operator scheduling → replay; Tier 3 evolutionary trajectory → NSGA-II.
- ✅ Anti-pattern guard-rail: cache identity NOT a proxy for "already explored" (§ 3.4.1).
- ✅ Generation contract (§ 3.4.2): ownership, monotonicity (advisory), replay, reset semantics.
- ✅ Marker-attribute detection `__multi_floor_candidate__: bool = True` for Spec #3 wrapper (§ 3.5).
- ✅ Test plan: ~28 example-based + ~6 property tests + ~4 integration tests (§ 5).
- ✅ 18 backlog items B-C11A-1 through 18 enumerated in § 7.

## Cross-spec contract integrity

- ✅ Spec #1 `iter_floors_with_master_flag()` → Spec #2 C9 cascade per floor → Spec #3 wrapper construction enforces MFWZP-5/6 — chain intact.
- ✅ Spec #4 § 3.9 trust-boundary handling matches Spec #3 § 3.10 dual-role expectations.
- ✅ Spec #4 § 3.11 FloorImpact extension hook ready for Spec #1 B-MFDB-C cross-floor constraints (when they land).
- ✅ Cache-key version bump v1.0.0 → v1.3.0 covers both Spec #3 (new wrapper type) and Spec #4 (multi-floor pipeline) in one step.

**Audit result**: PASS. Specs are self-consistent and cross-spec contracts hold.
