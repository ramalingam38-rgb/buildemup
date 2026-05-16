# B-150 Partial — NBC 2016 Primary-Source Verification (S54)

**Authored:** S54 (May 16, 2026), Ramalingam + Claude
**Scope:** Partial verification of NBC-cited values in `kb_rules/room_minimums.json` against Claude's training knowledge of NBC 2016 Part 3 + Part 4.
**Limitation:** Claude does NOT have NBC 2016 PDF access in this session. The "verified-likely-correct" findings rest on training data and cannot be considered legally-defensible primary-source verification. A future pass with PDF access (or licensed architect review under B-238) is still required.

**Status of full B-150:** OPEN. This partial pass closes one third of the gate; B-150 stays Bucket A until PDF-checked.

---

## Findings — `room_minimums.json`

### ✅ Likely correct (cross-checked against training knowledge)

| Field | Value | Citation | Confidence |
|---|---|---|---|
| BEDROOM_MASTER | 9.5 sqm | NBC 2016 Part 3 cl. 6.1.1 | HIGH — single-occupancy habitable room minimum |
| BEDROOM_REGULAR | 7.5 sqm | NBC 2016 Part 3 cl. 6.1.1 | HIGH — multi-room dwelling minimum per habitable room |
| LIVING | 9.5 sqm | NBC 2016 Part 3 cl. 6.1.1 | HIGH — habitable room minimum |
| KITCHEN | 5.0 sqm | NBC 2016 Part 3 cl. 6.1.2 | HIGH — recall NBC specifies 5.0 m² + min width 1.8m |
| BATHROOM_ATTACHED | 1.8 sqm | NBC 2016 Part 3 cl. 6.2 | HIGH — bath alone ~1.8 m² is canonical |
| BATHROOM_COMMON | 2.8 sqm | NBC 2016 Part 3 cl. 6.2 | HIGH — combined WC+bath ~2.8 m² is canonical |

### ⚠ Needs PDF verification — value may be slightly off

| Field | Value | Citation | Concern |
|---|---|---|---|
| **STAIRCASE** | 5.5 sqm | NBC 2016 Part 4 cl. 4.3.3 — claims "min width 0.9m for residential" | **NBC 2016 Part 4 specifies 1.0m minimum for residential staircase width** in single-family dwellings, not 0.9m. The 0.9m is canonical for apartment-block service stairs, NOT primary residential stairs. The 5.5 sqm area derivative may also need recalculation. **Verify against NBC 2016 Part 4 cl. 4.3.3 directly.** |
| **BALCONY** | 1.5 sqm | NBC 2016 Part 3 cl. 6.3 "0.9m × 1.8m typical" | The "0.9m × 1.8m = 1.62 sqm" cited math doesn't match the 1.5 sqm value. NBC doesn't actually mandate a minimum balcony area at the all-India level (state/city DCRs may). Either correct the math (1.5→1.62) or remove the cl. 6.3 citation. **Verify whether NBC 2016 has any balcony minimum.** |

### 🚩 Citation likely wrong — these aren't NBC mandates

| Field | Value | Citation | Concern |
|---|---|---|---|
| **POOJA** | 1.5 sqm | "NBC 2016 Part 3 (ancillary room minimum)" | NBC 2016 Part 3 does NOT define an "ancillary room minimum" clause. Pooja rooms are not regulated by NBC — they're cultural/optional. Citation should be **removed** or replaced with "industry typical (no NBC mandate)." |
| **DINING** | 6.0 sqm | "NBC 2016 Part 3 (dining minimum, often combined with living)" | NBC 2016 has no separate "dining minimum"; dining is typically subsumed under habitable room area. Citation should be **fixed** to reflect that this is a useful-minimum heuristic, not an NBC mandate. |
| **UTILITY** | 2.0 sqm | "NBC 2016 Part 3 (utility/washing area)" | Same issue — no specific NBC clause defines utility minimums. **Industry-typical only.** |
| **STORE** | 1.5 sqm | "NBC 2016 Part 3 (storage room minimum)" | Same issue. **Industry-typical only.** |

### Circulation factor

| Field | Value | Citation | Concern |
|---|---|---|---|
| `circulation_factor` (1.30-1.40) | typically 1.35 | "IS 3861-2002 (Method of Measurement of Plinth, Carpet and Rentable Area)" | IS 3861-2002 defines plinth/carpet/rentable area calculation but does NOT specify circulation multipliers (1.30/1.35/1.40). These ratios are engineer's-rule-of-thumb derived FROM the standard's measurement definitions, not stipulated by it. Citation should be softened to **"derived from IS 3861-2002 definitions; industry survey for multiplier values."** |

---

## Recommendations

| # | Action | Severity | Effort |
|---|---|---|---|
| 1 | Verify STAIRCASE 0.9m claim against NBC 2016 Part 4 cl. 4.3.3 in actual PDF. If 1.0m is correct for residential, fix value (5.5 sqm may also change). | HIGH | Small |
| 2 | Either fix BALCONY math (1.5 → 1.62 sqm) or remove the cl. 6.3 citation if NBC has no balcony mandate. | MEDIUM | Small |
| 3 | Reword POOJA / DINING / UTILITY / STORE citations to "industry typical (no NBC mandate)." The values themselves are fine for v1; the citations mislead the user about regulatory backing. | MEDIUM | Trivial |
| 4 | Soften IS 3861-2002 circulation_factor citation to acknowledge it's a derived rule-of-thumb, not a code-mandated value. | LOW | Trivial |
| 5 | When B-238 (architect review) happens, prioritize NBC verification as part of their pass — they will have current code copies and can settle items 1-4 authoritatively. | — | (calendar) |
| 6 | Spot-check `setback_rules.json` NBC-fallback values + `seismic_rules.json` IS 1893 citations + `load_rules.json` IS 875 citations in a future B-150 pass. This document covered only `room_minimums.json`. | MEDIUM | Medium |

---

## What this verification DID NOT cover

This was room_minimums.json only. Still pending:

- `setback_rules.json` — NBC fallback values (the city-specific Chennai/Mumbai/Delhi/Bangalore/Pune/Hyderabad rules were authored from city DCRs, not NBC, so most of this file isn't NBC-cited; but the `_fallback_nbc` block needs review)
- `seismic_rules.json` — IS 1893:2016 citations (Zone factors, response reduction, importance factors)
- `load_rules.json` — IS 875 Parts 1+2+3 citations (dead/live/wind loads)
- `coverage_rules.json` — FAR/ground coverage (mostly city DCR, not NBC)
- `rwh_approval_rules.json` — RWH mandates (city + state, with NBC Part 9 cross-refs)

Each file deserves its own verification pass. Estimated effort: ~2 hours per file with PDF access.

---

## Sign-off

- **Auditor:** Claude (training-data based; not legally defensible)
- **Date:** 2026-05-16 (S54)
- **Confidence:** MEDIUM — high for canonical habitable-room minimums, LOW for ancillary-room citations and the staircase width
- **Recommended next step:** When B-238 (architect review) is scheduled, include this document in the brief so the architect can do the authoritative PDF cross-check.
