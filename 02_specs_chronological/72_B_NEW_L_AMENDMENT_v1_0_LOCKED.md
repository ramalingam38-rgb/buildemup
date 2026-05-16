# B-NEW-L — C8 entry approach compatibility Inv 21 — v1.0 **LOCKED**

**Status**: **v1.0 LOCKED** by Ramalingam at S38, 09 May 2026.
**Predecessor**: v0.1 PROPOSED.
**Authored**: S38.
**Required by**: C11a v1.0 LOCKED § 3.4 — Tier A predicate matrix
`C8.entry_approach` for M9a-d operators.

---

## § 0 — What this amendment adds

C8 already models `CorridorEndpoint` with `kind=ENTRY` but lacked a
named, numbered invariant or callable predicate for entry-approach
compatibility. This amendment:

1. Adds **Inv 21** — Entry approach compatibility — to C8's numbered
   invariant set (1-20 carried from v0.6 LOCKED).
2. Adds `validate_entry_approach(...)` predicate exposed via
   `components/c08/validator.py`.

---

## § 1 — The rule (Inv 21)

For every `CorridorPath` with `has_corridor=True` containing at
least one `CorridorEndpoint` of `kind=ENTRY`, each ENTRY endpoint
MUST lie on the envelope edge corresponding to the
`OrientedCandidate`'s `envelope.facing` direction (within
`DEFAULT_EPSILON_M = 0.001 m` tolerance).

**Cardinal facings** (N/S/E/W) require the endpoint on ONE specific
edge.
**Intercardinal facings** (NE/NW/SE/SW) accept the endpoint on
EITHER of the two adjacent cardinal edges.

**Vacuous-pass cases**: `has_corridor=False`, or paths without any
ENTRY-kind endpoints.

**Mode**: RAISE (per-candidate via existing C8 partial-batch rule).

**Design discipline**: Inv 21 is exposed only as the C11a Tier A
predicate. `validate_corridor_path()` (C8 batch validator) does NOT
call it — Inv 21 is a mutation-time check, not a corridor-
construction-time check.

---

## § 2 — Predicate contract

```python
def validate_entry_approach(
    corridor_path: CorridorPath,
    envelope_width_m: float,
    envelope_depth_m: float,
    plot_facing: PlotOrientation,
    *,
    epsilon_m: float = DEFAULT_EPSILON_M,
) -> tuple[bool, str | None]
```

C11a Tier A registers as `MutationViabilityPredicate(rule_owner="C8",
rule_id="entry_approach", _predicate_fn=validate_entry_approach,
pending_upstream=False)`.

---

## § 3 — Tests

`tests/test_c8_inv21_entry_approach.py` — **21 tests, all passing**.

---

## § 4 — Backlog filed

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-NEW-L-rotated** | Inv 21 generalisation for non-axis-aligned envelopes | post-launch + B-217 polygonal envelope | M |
| **B-NEW-L-multi-entry** | Multi-entry-door support (service vs main entry) | post-launch + observed need | S-M |

---

## § 5 — LOCK authority

**LOCKED v1.0 by Ramalingam at S38, 09 May 2026.**

---

**End of B-NEW-L v1.0 LOCKED.**
