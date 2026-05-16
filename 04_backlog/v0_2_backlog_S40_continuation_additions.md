# C11a v0.2 Backlog — S40-continuation Additions (post-Spec-#2-LOCK)

**Session**: S40-continuation (B-NEW-T3 spec sequence: 4-spec sequence for M8 multi-floor real upstream wiring).
**Filed by**: Claude per Rule 9.2 (always-file-backlog directive) and per Ramalingam directive ("Apply the backlogs").
**Format**: Mirrors `v0_2_backlog_S40_additions.md`.

---

## § 1 — Spec sequence status

| Spec | Status | File(s) in `02_specs_chronological/` |
|---|---|---|
| Spec #1: `MultiFloorDwellingBrief` v0.5 | LOCKED at S40-continuation | 80-85 |
| Spec #2: C9 Amendment v0.11 | LOCKED at S40-continuation | 86-90 |
| Spec #3: `MultiFloorWetZonePlannedCandidate` v0.2 | PROPOSED, awaiting LOCK | 91 (v0.1), 92 (v0.2) |
| Spec #4: C11a Amendment v1.1 | NOT YET DRAFTED | — |

---

## § 2 — Items LANDED via spec LOCK (Specs #1 + #2)

Cumulative backlog items filed across the four critique walks of Spec #1
and the four critique walks of Spec #2. All filed in their respective
spec § 7 backlog tables; see those specs for full descriptions, triggers,
and effort estimates. This file mirrors them and adds the post-LOCK
priority signals.

### Spec #1 (MultiFloorDwellingBrief) backlog — 15 items

`B-MFDB-A` floor_elevation_m · `B-MFDB-B` add/remove_floor helpers ·
`B-MFDB-C` per-floor staircase landing constraint · `B-MFDB-D` C1
multi-floor brief-capture · `B-MFDB-E` mid-level/basement/mezzanine ·
`B-MFDB-F` lookup-map opt · `B-MFDB-G` formal Protocol migration ·
`B-MFDB-H` user-facing exception strategy · `B-MFDB-I` v2 selector
enum widening · `B-MFDB-J` multi-master / dual-master support ·
`B-MFDB-K` pathological-label sanitization · `B-MFDB-L` non-livable
floor taxonomy · `B-MFDB-M` strict-mode lookup helpers · `B-MFDB-N`
spec restructure (normative/rationale/forward-compat split) ·
`B-MFDB-O` `canonical_topology_signature()` helper.

### Spec #2 (C9 Amendment) backlog — 7 items

`B-C9-A` split master-bedroom flag (bedroom + bathroom variants) ·
`B-C9-B` rename `has_master_bedroom` → `has_master_suite` ·
`B-C9-C` explicit cache-signature serialization ·
`B-C9-D` structural master-room derivation (replace `(i == 0)` positional) ·
`B-C9-E` architectural / protocol tests for prose-authoritative semantic constraints ·
`B-C9-F` physical-equivalence helper (`is_physically_equivalent`) ·
`B-C9-G` architecture-governance convention for "directly-affects-runtime-behaviour" criterion.

---

## § 3 — Post-LOCK priority signals (from v0.11 critique walk)

A critique of Spec #2 v0.11 was received AFTER LOCK. Per Rule 8 paragraph
4, post-LOCK critique cannot drive PROPOSED → PROPOSED iteration on the
spec itself. The reviewer's actually-actionable signals were two
priority re-tags on existing backlog items (not new items, not spec
changes). Filed here as priority signals so they survive into future
sessions.

### B-C9-F priority signal — promote on first real consumer

**Original spec text** (Spec #2 v0.11 § 7):
> Trigger: "When deduplication / topology canonicalization / lineage
> clustering needs physical-only equivalence (likely first surfaces
> in C11a v1.1 cache or in a future stress-fuzz refactor). Status:
> Open (post-v1)."

**Post-LOCK priority signal** (v0.11 critique walk MAJOR-1):
The transitional `dataclasses.replace(a, has_master_bedroom=True) == dataclasses.replace(b, has_master_bedroom=True)` idiom (introduced in Spec #2 v0.11 § 3.9 as a workaround until the helper lands) **silently breaks the moment a second orchestration-context field appears on `FloorRoomBrief`**. Adding (e.g.) a `lineage_tag`, `orchestration_phase`, `suite_policy`, or `accessibility_override` field would mean physical equivalence requires erasing N fields, not 1, and the idiom would still produce false-equality (because the new field would still differ).

**Practical priority**: promote B-C9-F from "post-v1" to "**priority-promote on first real consumer**." A real consumer is any code site that needs physical-only equivalence — most likely C11a v1.1's cache (Spec #4) when computing topology-equivalence-ignoring-orchestration-state. Recommended action: include the `is_physically_equivalent()` helper in Spec #4's build session if Spec #4 needs it, OR file a dedicated micro-session to ship the helper independently if Spec #4 doesn't surface the need.

### B-C9-G priority signal — no longer optional future cleanup

**Original spec text** (Spec #2 v0.11 § 7):
> Trigger: "≥3 orchestration-contextual-field proposals reach review,
> OR when an architecture-review process formalises. Status: Open
> (post-v1)."

**Post-LOCK priority signal** (v0.11 critique walk CRITICAL-1):
Spec #2 v0.11 has begun **codifying meta-architecture conventions** (worked precedent examples for "directly-affects-runtime-behaviour," explicit acceptable/unacceptable contextual-field criteria, future-governance escalation conditions). The spec is no longer merely a component contract — it's partially an architecture-governance doctrine. Reviewer flags: "Once a spec starts defining admissibility criteria, precedent interpretation, governance escalation, it becomes difficult to distinguish component contract from architecture constitution."

**Practical priority**: B-C9-G's trigger condition ("≥3 contextual-field proposals") understates the urgency. **Realistic re-tag**: "promote when the next contextual-field proposal arrives" (i.e., on the first attempt to add a second orchestration-context field to `FloorRoomBrief` or any other domain dataclass). Otherwise architecture policy fragments across specs and future contributors interpret C9 amendment prose as globally authoritative architecture policy without realizing they shouldn't.

### Two backlog items to consider creating later (NOT filed now)

The v0.11 critique also surfaced architectural-philosophy-level
observations that don't fit existing backlog items:

- **B-C9-H candidate** (NOT YET FILED): formal architectural-identity
  model documenting which equivalence notion (physical / structural /
  orchestration-context) is canonical in which contexts. Hypothetical;
  defer until B-C9-F lands and we observe how `is_physically_equivalent`
  is consumed.
- **B-C9-I candidate** (NOT YET FILED): cross-cutting architecture
  principles document (ADR-style) for items that span multiple
  components. Hypothetical; defer until ≥2 cross-cutting principles
  exist and have produced inter-spec coupling.

These are NOT filed as B-NNN entries today (per Rule 9.2 "discard
requires explicit Ramalingam direction" — but conversely, filing
hypothetical items prematurely is also undesirable). They're flagged
here as candidates so future sessions can promote them when triggered.

---

## § 4 — Summary

| Category | Count |
|---|---|
| Specs LOCKED in S40-continuation | **2** (Spec #1 v0.5, Spec #2 v0.11) |
| Specs PROPOSED / awaiting LOCK | **1** (Spec #3 v0.2) |
| Specs not yet drafted | **1** (Spec #4 C11a v1.1) |
| New backlog items added (this session, across Specs #1+#2 § 7) | **22** (15 B-MFDB-* + 7 B-C9-*) |
| Post-LOCK priority signals filed | **2** (B-C9-F promote-on-real-consumer, B-C9-G promote-on-next-contextual-field-proposal) |
| Hypothetical backlog candidates flagged but not filed | **2** (B-C9-H formal identity model, B-C9-I ADR system) |
| Total project tests after Spec #2 build (when it lands) | **2769** (2760 baseline + 9 new) |
| Tier B operators real-wired | **2/4** (M6 at S39, M7a/M7b at S40 — unchanged in S40-continuation) |
| Pending Tier B for B-NEW-T3 build | **1** (M8 — gated on Specs #3 + #4 LOCKED) |

---

**End of S40-continuation Additions.**
