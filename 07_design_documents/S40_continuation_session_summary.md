# S40-CONTINUATION SESSION NARRATIVE — what actually happened

**Session goal**: complete the four-spec design sequence for B-NEW-T3 (M8 multi-floor real upstream wiring).

**Session outcome**: all four specs LOCKED. Build session deferred to next Claude (S41+).

---

## Timeline

### Phase 1: Spec #1 `MultiFloorDwellingBrief` (5 critique rounds)

- **v0.1 PROPOSED**: first draft. Floors + master designation + selector.
- **v0.1 → v0.2 critique walk**: reviewer caught CRITICAL — master semantics underpowered (no exactly-one-master invariant, unconstrained labels).
- **v0.2 → v0.3 critique walk**: refinements on normalization + helper API.
- **v0.3 → v0.4 critique walk**: mutation-asymmetry observations; backlog filings.
- **v0.4 → v0.5 critique walk**: final doc-polish round.
- **v0.5 LOCKED** at file 85.

### Phase 2: Spec #2 `C9 Amendment` (4 critique rounds)

- **v0.8 PROPOSED**: builds on prior pre-S40-continuation work.
- **v0.8 → v0.9 critique walk**: reviewer caught CRITICAL — orchestration-contextual metadata mixing, default-True asymmetry, trust-boundary observability.
- **v0.9 → v0.10 critique walk**: refinements + cache-signature explicit serialization.
- **v0.10 → v0.11 critique walk**: equality-overload acknowledgement, transitional `dataclasses.replace` idiom documentation, governance-philosophy expansion.
- **v0.11 LOCKED** at file 90.
- **Post-LOCK critique** received with priority signals for B-C9-F (promote on real consumer) + B-C9-G (no longer optional). Filed in project backlog file.

### Phase 3: Spec #3 `MultiFloorWetZonePlannedCandidate` (2 critique rounds + 1 empirical fix)

- **v0.1 PROPOSED**: first draft. **Empirical schema check** caught the ancestry-path bug `provenance.floor_room_brief.floor_label` (wrong) → `provenance.floor_label` (correct, schema-verified via Python REPL).
- **v0.1 → v0.2**: schema-drift fix.
- **v0.2 → v0.3 critique walk**: CRITICAL — wrapper as dual-role passive container + correctness authority. Truth-arbitration policy. Framing refinement on "valid-by-construction" → "master-designation coherence."
- **v0.3 critique walk #2**: zero spec-text patches; reviewer verdict "very close to LOCK quality." Natural LOCK point.
- **v0.3 LOCKED** at file 94.

### Phase 4: Spec #4 `C11A Amendment` (6 critique rounds — the largest)

Three-round behavioral-change sequence:

- **v1.1 PROPOSED**: first draft, master-floor-only Tier A/B, first-eligible M8 target.
- **v1.1 → v1.2**: master-only → ALL FLOORS lex-order; first-eligible → hash-modulo M8. **Two real behavioral changes**.
- **v1.2 → v1.3**: lex-order → operator-major round-robin floor rotation; hash-modulo → cyclic deterministic M8. **Two real algorithmic corrections** (reviewer caught real algorithmic bugs in v1.2).
- **v1.3 → v1.4**: operator-major round-robin → bipartite round-major interleaving (the v1.3 LOCK gate). Plus FloorImpact structured return type, determinism tier-table, stateful chain test, cross-spec integration tests.

Two-round doc-polish sequence:

- **v1.4 → v1.5**: `affected_floor_set` API split (LOCK gate #1) + fairness wording precision "bounded imbalance ≤ 1" (LOCK gate #2) + 4 doc patches.
- **v1.5 → v1.6**: anti-pattern guard-rail + 2-floor-impact framing + label-overloading callout + cross-spec governance status + post-LOCK plan. **Reviewer's final verdict: "PRETTY CLOSE TO LOCK-WORTHY for v1 operational scope."**
- **v1.6 LOCKED** at file 101.

---

## Convergence shape (the pattern)

```
Round           Type              Behavioral changes  Backlog added
─────────────────────────────────────────────────────────────────
Spec #1 v0.1    First draft       —                    7
Spec #1 v0.2    Behavioral        Master semantics     +4
Spec #1 v0.3    Refinements       Helper API          +3
Spec #1 v0.4    Refinements       Mutation patterns    +1
Spec #1 v0.5    Doc-polish        None                 0
─────────────────────────────────────────────────────────────────
Spec #2 v0.8    First draft       —                    3
Spec #2 v0.9    Behavioral        Trust boundary       +2
Spec #2 v0.10   Refinements       Metadata governance  +1
Spec #2 v0.11   Doc-polish        None                 +1
─────────────────────────────────────────────────────────────────
Spec #3 v0.1    First draft       —                    8
Spec #3 v0.2    Bug fix           Schema-drift         +1
Spec #3 v0.3    Behavioral        Trust-boundary upgrade  +3
─────────────────────────────────────────────────────────────────
Spec #4 v1.1    First draft       —                    4
Spec #4 v1.2    Behavioral        Dispatch + selection +5
Spec #4 v1.3    Behavioral        Round-robin + cyclic +3
Spec #4 v1.4    Behavioral        Bipartite + FloorImpact +3
Spec #4 v1.5    Doc-polish        None                 0
Spec #4 v1.6    Doc-polish        None                 +3
─────────────────────────────────────────────────────────────────
TOTAL                              7 behavioral rounds  40 items
```

The substantive design space was genuinely exhausted by v1.4 of Spec #4. v1.5 + v1.6 were progressively-thinner doc-polish rounds.

---

## Key technical decisions captured

### Spec #1
- Tuple ordering is structurally significant but topologically non-canonical (deferred elevation-canonical ordering to B-MFDB-A).
- Selector field exists but only one allowed value at v1.

### Spec #2
- `has_master_bedroom: bool = True` is the orchestration-contextual field that lives on the domain dataclass. Default-True for backwards compat. v0.11 § 3.9's worked positive/negative examples establish the precedent narrowly.
- Trust boundary forward-pointed to Spec #4 — but Spec #3 v0.3 then UPGRADED to construction-time enforcement.

### Spec #3
- `__post_init__` enforces MFWZP-5 (exactly one master globally) + MFWZP-6 (declared master matches derived). Construction-time guard.
- Per-floor labels DERIVED (not declared) via ancestry walk. Empirically-verified path `f.room_sized_candidate.provenance.floor_label`.
- Mutation API: two helpers (`with_floor_replaced` for single-floor; `with_master_on` for dwelling-level M8).

### Spec #4
- **Dispatch**: existing `_is_multi_floor()` helper detects Spec #1 wrapper via `is_multi_floor: bool = True` property. Zero changes to detection logic.
- **Tier A/B fairness**: bipartite operator+floor round-major interleaving. Bounded imbalance ≤ 1, starvation-free on both axes.
- **M8 target selection**: deterministic cyclic `sorted_targets[(generation + operator_index) % N]`. Mathematical coverage guarantee.
- **Signature**: `multi_floor_sig_schema=v1` prefix + per-floor recursive signatures + master label.
- **Cache version**: single-step bump v1.0.0 → v1.3.0 (covers both Spec #3 + #4 in one bump).
- **Family ID**: label-preserving `multi_floor:ground=A|first=B` (sort by label, not by family).
- **Detection**: marker-attribute `__multi_floor_candidate__: bool = True` class attribute on Spec #3's wrapper. Hash-irrelevant — doesn't violate Spec #3 LOCK.
- **affected_floor_set**: split-kwarg API `direct_floor_label` (per-floor ops) / `new_master_floor_label` (M8). FloorImpact structured return with kind / requires_cascade / requires_validation_only.
- **Trust boundary**: NOT a redundant assertion. Spec #3 construction guard fires; C11a wraps `ValueError` as `orchestration_state_drift:mfwzpN`.
- **Determinism tiers**: Tier 1 structural / Tier 2 scheduling / Tier 3 evolutionary. Cache = Tier 1; replay = Tier 2; NSGA-II = Tier 3.
- **Generation contract**: caller-provided, monotonicity advisory, replay-deterministic, reset-supported.

---

## Pushback events worth recording

- **Spec #3 schema-drift catch** (post-PROPOSED, pre-LOCK): Ramalingam directive was "lock it" but empirical schema check caught the ancestry-path bug. Stopped the LOCK, produced v0.2, then LOCKED v0.3 after one more critique round. Confirmed by user: "Apply the backlogs and give me the Spec #3 doc for analysis."
- **Spec #4 v1.3 → v1.4 LOCK gate** (reviewer's explicit naming): "operator-bias limitation is acknowledged explicitly OR full interleaving is added before LOCK." Implemented full interleaving (bipartite).
- **Spec #4 v1.5 → v1.6 LOCK gates** (reviewer's explicit naming): "1. `affected_floor_set()` semantic overload. 2. fairness wording overstated." Both addressed.
- **Post-LOCK Spec #2 critique**: filed as project-backlog priority signals (B-C9-F + B-C9-G retags). Spec #2 LOCKED file not modified — LOCK is canonical.

---

## What's NOT done in S40-continuation

- **B-NEW-T3 build** (the implementation). Deferred to next Claude per the standing rule "never code before a LOCKED spec." All four specs LOCKED at session end; implementation is the next-session work item.
- **Master doc update**. The master doc was not updated in S40-continuation; it should be brought current alongside the build session or as a separate maintenance step. NEXT_CLAUDE_HANDOFF.md serves as the operational handoff.
- **40 backlog items added in this session** are filed but not actioned. All post-v1.
