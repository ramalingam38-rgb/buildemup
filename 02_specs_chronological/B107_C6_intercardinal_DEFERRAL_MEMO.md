# B-107 — DEFERRAL MEMO: C6 intercardinal facing extension

**Authored:** S59 extended, 2026-05-19, Ramalingam + Claude
**Status:** EXPLICITLY DEFERRED — requires architect / vastu expert input
**Parent component:** C6 — Orientation prioritization
**Parent spec:** `02_specs_chronological/30_C6_SPEC_v0_6_LOCKED.md` (and amendments)

## What the bug is

C6's `prioritize_orientation` explicitly raises `NotImplementedError("intercardinal facing reserved; B-107. v1 supports cardinal only")` when given a plot whose `facing ∈ {NORTHEAST, SOUTHEAST, SOUTHWEST, NORTHWEST}`. v1 supports only the four cardinal directions (N, S, E, W).

Affected scenario: `chennai_30x40_small` — `chennai_30x40()` carries `facing=PlotOrientation.NORTHEAST` and immediately blocks at C6.

## Why a spec amendment is genuinely deferred (not a Claude hot fix)

The spec's choice to reject intercardinal is **intentional and load-bearing**, not an oversight:

1. **Vastu KB has no defined entries for NE/SE/SW/NW orientation.** The Indian residential vastu rules used by C6 (`vastu_partial` and `vastu_strict` profiles) are pinned to cardinal-facing assumptions for entrance placement, kitchen position, pooja-room orientation, and bedroom orientation. There is no published consensus on how these rules SHOULD apply to a plot whose main entrance faces, e.g., 045° (NE).

2. **Vastu expert review is REQUIRED.** Writing rules here without vastu expertise = inventing vastu, which is precisely what the spec was designed to avoid (per `Architecture v1 § 2.4` no-silent-override rule). Two reasonable approaches exist and the choice is domain-expert work:
   - **(a) Project to nearest cardinal**: NE → "treat as North" (most generous), or → "treat as East" (alternative). Picking N vs E for NE is a vastu choice with material implications for room placement.
   - **(b) Genuinely intercardinal rules**: introduce 8-direction vastu rules for entrance/kitchen/pooja. Requires expert authoring of ~50 new KB entries.

3. **The B-238 architect engagement is the right forum.** Once an architect with vastu expertise reviews the existing v1 cardinal logic, they can author either:
   - A C6 v1.1 AMENDMENT that pins one of approach (a) or (b), OR
   - A B-107 closure decision that says "intercardinal stays out of scope; orchestrator UI should reject NE/SE/SW/NW at brief-capture time".

## What's in place today (S59 extended close)

- C6 still raises `NotImplementedError` on intercardinal — unchanged.
- The orchestrator catches this in `_run_c06_orientation` and degrades the C6 phase to STUB with an explicit reason that names B-107. Downstream phases SKIP cleanly; `overall_status` remains OK.
- The scenario corpus records `chennai_30x40_small` as `downgraded_phase="c06_orientation"`. When B-107 closes (with any of the architect-decided approaches), flip the row to `None` to re-validate full happy-path.
- The orchestrator's UI displays the limitation honestly: "C6 does not yet support intercardinal facing (NE/SE/SW/NW) — tracked under B-107. v1 supports cardinal facing only. Rotate the plot to a cardinal facing or wait for B-107 to extend orientation logic."

## What this memo is NOT

This is NOT an amendment to the C6 LOCKED spec. The C6 spec's `intercardinal-rejected` behavior remains correct per the v1 contract. This memo exists to make the deferral reasoning explicit so future-Claude doesn't try to invent vastu rules without architect input.

## When this can be closed

When EITHER:
- B-238 architect feedback includes a vastu position on intercardinal handling, AND a vastu expert (or the architect themselves) signs off on the new rules → author `C6_AMENDMENT_v1_1_LOCKED.md`; OR
- Product decision is "reject intercardinal at the brief-capture form" → close as won't-fix-in-C6; UI gate becomes the closure.

---

**End of B-107 deferral memo.**
