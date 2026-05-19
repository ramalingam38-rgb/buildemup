# B-C12-EDGE-DENSITY — DEFERRAL MEMO: slicing-tree shared-edge bias

**Authored:** S59 extended, 2026-05-19, Ramalingam + Claude
**Status:** EXPLICITLY DEFERRED — algorithmic redesign requires architect review
**Parent component:** C12 — Single-floor placement (slicing kd-tree)
**Parent spec:** `02_specs_chronological/C12_v1_0_LOCKED/` (immutable; do not edit)
**Filed:** Post-LOCK (S45 C13 corpus discovery); subsequently re-confirmed S46, S47, S57.

## What the bug is

C12's `slicing_kd_tree` (the v1.0 placement algorithm that turns sized rooms into placed rectangles) routinely produces zero shared edges between rooms in multi-room layouts. Rooms get placed at non-contiguous corner anchors with corridor gaps between them, so:

- C13 `place_doors` has nowhere to place interior doors → emits `DoorPositionInfeasibleError` for every internal pair → 0 successful door placements.
- C14 connection graph runs on an empty edge set.
- C15 problem-finder analyzes triples with empty graphs (degrades signal).
- C16 renderer receives 0 drawable candidates → STUB.

The whole downstream C13→C16 chain effectively runs on synthetic-only fixtures during testing because real C12 output is graph-empty.

## Why a spec amendment is genuinely deferred

This is a deep algorithmic redesign, not a parameter tweak:

1. **Effort estimate (per S46 handoff): "M" — medium-to-large.** The fix involves changing C12's slicing-tree split heuristic to bias toward shared-edge density (e.g., prefer splits that create wall adjacency between rooms with high connection-graph weight). That's a new optimization objective with its own trade-offs:
   - Aspect-ratio quality (existing): produces tall/skinny rooms when over-optimized for adjacency.
   - Vastu compliance (existing): adjacency bias may push rooms into culturally-discouraged adjacencies.
   - Area utilization (existing): adjacency bias may waste envelope area.

2. **Validator surface change.** C12's existing Inv 7 ("no overlap") and Inv 9 ("axis-aligned") are unaffected, but Inv 5 ("rooms cover envelope without gap >= corridor_width") may need redefinition if the new heuristic produces adjacency at the cost of gap closure.

3. **Cache-key + replay impact.** C12 v1.1 would necessarily change `c12_cache_key` semantics. Existing C12 caches and replay tests would all need re-baselining.

4. **Downstream cascades.** Every C13/C14/C15/C16/C17 test that uses synthetic hub-and-spoke fixtures (per the S46 workaround) would need re-baselining once real C12 actually produces hub-and-spoke layouts. The number of affected tests is large (200+).

5. **B-238 architect feedback is the right input.** The architect's review will say which of the trade-offs above are acceptable. Designing this without that input is guessing about what "a good Indian residential floor plan" looks like architecturally.

## What's in place today (S59 extended close)

The orchestrator handles the symptom gracefully:

- C12 phase ships OK (the `place_and_align` call succeeds — per-candidate `DoorPositionInfeasibleError` failures are captured inside `batch.failed`, not as phase failures).
- C13 phase ships OK (same shape — `place_doors` returns successfully even when 0 internal doors fit).
- C14 phase ships OK (analyzes whatever C13 produces).
- C15 phase ships OK (analyzes whatever (C12, C13, C14) triples it gets).
- C16 phase ships OK or STUB depending on whether ANY candidate has a usable upstream join. On smoke fixtures the result is consistently STUB with the explicit breadcrumb: `"No drawable candidates after upstream join: every C12 PlacedCandidate either failed C13 door placement or C14 circulation analysis. (C12 sparse-edge density problem — filed as B-C12-EDGE-DENSITY; working as designed.)"`.

The C16 UI surface (`orchestrator_run.html`) shows this STUB-with-reason honestly. The architect can see the symptom without the pipeline crashing.

## Closure path

When closing this:
1. Author `C12_AMENDMENT_v1_1_LOCKED.md` with the chosen slicing-tree heuristic.
2. Implement in `components/c12/slicing_kd_tree.py` (or the relevant module).
3. Re-baseline C12 caches (`c12_cache_key_version` bump).
4. Re-baseline downstream C13/C14/C15/C16/C17 fixtures.
5. Update the scenario corpus to remove "C16 may be OK or STUB" tolerance.

Estimated total effort: 4-6 focused sessions across multiple components.

## What this memo is NOT

This is NOT an amendment. The C12 v1.0 contract remains correct as designed; the algorithm choice is a known limitation, not a contract violation. This memo exists to make the deferral reasoning explicit and to keep future-Claude from attempting a quick fix that wouldn't actually address the architectural choice.

---

**End of B-C12-EDGE-DENSITY deferral memo.**
