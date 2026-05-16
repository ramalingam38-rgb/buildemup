# C8 Corridor Design — Amendment for C12 Consumption — v0.1

**Component**: 8 (Corridor Design)

**Origin**: Filed as `B-C8-CORRIDOR-ZONE-CONTRACT` in C12 v0.2 PROPOSED Walk #2 amendments (S43). C12 v1 LOCK candidacy depends on this amendment landing.

**Status**: v0.1 PROPOSED → **LOCKED via S43 directive** (Ramalingam: "Let's do the dependencies on c8&c9 and code that also" — interpreted as combined LOCK + code authorization for both routed dependencies).

**Authority**: S43 author's draft; LOCK by Ramalingam's S43 directive cited above.

**Scope**: minimal-surface addition. Does NOT change existing C8 behaviour or test posture.

---

## § 1 — Motivation

C12 (Multi-Floor Placement & Vertical Alignment Engine) requires a way to **reserve corridor regions on the envelope grid** before per-floor SFP (single-floor placement) runs. C12 v0.2 Amendment A6 specifies a reachability BFS check that depends on corridor zones being available as axis-aligned rectangles.

Currently C8 emits `CorridorDesignedCandidate` carrying `CorridorPath` carrying `CorridorSegment`s — rich geometric structure with axis-aligned start/end points + per-segment widths. The information C12 needs (axis-aligned rectangles representing corridor occupancy) is **derivable** from existing C8 output, but no accessor exposes it cleanly.

This amendment adds a thin accessor + a `CorridorZone` dataclass; no semantic change.

---

## § 2 — Contract addition

### § 2.1 — New schema type

```python
@dataclass(frozen=True)
class CorridorZone:
    """An axis-aligned rectangle reserving a region of the envelope
    for corridor occupancy. Derived from CorridorSegment geometry
    for downstream C12 consumption.

    Per the C12 v0.2 Amendment A6 corridor-reservation contract:
    C12 marks each CorridorZone rectangle as occupied (cannot be
    placed-into) before per-floor SFP runs, and verifies room
    reachability via a BFS over the placed rooms + zones graph.

    Fields use SAME conventions as PlacedRoom (C12 schema):
      - (x_m, y_m) = bottom-left corner of the rectangle in envelope
        coordinates (metres).
      - width_m / depth_m = extents along x / y axes.

    For tapered corridor segments, the zone is derived using
    max(start_width, constant_width, end_width) so reservation is
    conservative (over-reserve rather than under-reserve).
    """
    x_m: float
    y_m: float
    width_m: float
    depth_m: float
    source_segment_kind: CorridorSegmentKind  # provenance back to C8

    def __post_init__(self) -> None:
        if self.width_m <= 0.0 or self.depth_m <= 0.0:
            raise ValueError(
                f"CorridorZone requires positive extents; "
                f"got width={self.width_m}, depth={self.depth_m}."
            )
```

### § 2.2 — New accessor

```python
# On CorridorDesignedCandidate:
@property
def corridor_zones(self) -> tuple[CorridorZone, ...]:
    """Derived view: each CorridorSegment in the corridor_path
    converted to a CorridorZone axis-aligned rectangle.

    Conservative (over-reserves on tapered segments):
    width = max(start_width_m, constant_width_m, end_width_m).
    """
```

---

## § 3 — Behavioural contract

- Derivation is pure-deterministic: same `CorridorDesignedCandidate` → same `corridor_zones` tuple (byte-equal).
- Zone ordering is canonical: sorted lex-ASC by `(x_m, y_m, width_m, depth_m)` so reservation order in C12 is stable.
- Tapered segments are reserved conservatively (use max of the three width regions). This may over-reserve corridor space in the taper zones; this is a v1 trade-off — accurate taper modelling is filed as `B-C8-TAPER-ACCURATE-ZONES` post-v1.

---

## § 4 — Invariants

- **Inv A**: Every emitted `CorridorZone` has positive extents (asserted in `__post_init__`).
- **Inv B**: `corridor_zones` tuple ordering is canonical lex-ASC by `(x_m, y_m, width_m, depth_m)`.
- **Inv C**: For each `CorridorSegment` in the source `corridor_path`, exactly one `CorridorZone` is emitted (1-to-1 mapping, no zone fusion or splitting at v1).

---

## § 5 — Test coverage targets

- ~6 derivation tests: uniform-width segment → single zone; tapered segment → over-reserved zone; multi-segment path → multi-zone tuple; canonical ordering verification.
- ~2 invariant tests: positive extents enforced; 1-to-1 mapping enforced.

---

## § 6 — Backward compatibility

- No existing C8 fields modified or removed.
- `corridor_zones` is a new accessor (computed property), not a field; existing serialization/equality semantics unchanged.
- No upstream caller changes required.

---

## § 7 — Status

**LOCKED via S43 directive.** Ready for code application.

Cross-component dependency: C12 v1 LOCK depends on this amendment + the C9 amendment landing.
