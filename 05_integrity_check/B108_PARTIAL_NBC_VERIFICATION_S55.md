# B-108 Partial — NBC 2016 Corridor Minimum Width Verification (S55)

**Authored:** S55 (May 16, 2026), Ramalingam + Claude
**Scope:** Verify the 0.9m default in `CorridorDesignConfig.regulatory_min_width_m` (C8 schema) against NBC 2016 Part 3 / Part 4 + TNCDBR rule 42.
**Limitation:** Claude does NOT have NBC 2016 PDF access in this session. Findings rest on training data and cannot be considered legally-defensible primary-source verification. A future pass with PDF + licensed architect review (B-238) is still required.

**Status of full B-108:** PARTIAL CLOSURE. The training-data confidence band is documented; full PDF check still queued under B-150 / B-238.

---

## Findings — `CorridorDesignConfig.regulatory_min_width_m = 0.9`

### Likely-correct value, but citation scope was vague

The 0.9m default appears correct for the **interior residential corridor** case BuildEase actually targets: a single-dwelling unit, short corridor (< 30m), serving habitable rooms within one home. Training-data references suggest:

- **NBC 2016 Part 3 § 14 / § 12.5** (interior space planning) treats 0.9m as an acceptable minimum for short corridors inside a single dwelling unit.
- **NBC 2016 Part 4 § 4.3** (fire safety / egress) requires wider corridors when:
  - The corridor serves multiple dwelling units (apartment-block layout).
  - The corridor length exceeds a length threshold (commonly 30m).
  - The corridor functions as a fire-egress path with travel distance > limits.
- **TNCDBR 2019 Schedule II + Rule 42** generally defers to NBC for corridor minimums.

### Where the 0.9m default could be wrong

| Scenario | What NBC plausibly requires | What our default gives | Risk |
|---|---|---|---|
| Single-dwelling, short corridor | 0.9m | 0.9m | ✅ matches |
| Multi-unit apartment hallway | 1.5m+ | 0.9m | ❌ would under-design |
| Long corridor (> 30m) in single home | 1.0m | 0.9m | ❌ marginal under-design |
| Fire-egress corridor on G+3 staircase landing | 1.0m+ | 0.9m | ❌ under-design for fire load |

Since v1 BuildEase targets **single-family residential up to G+3** — and the corridor in our model is the internal circulation within one home, not an apartment hallway — the 0.9m default is **defensible for the v1 use case**. Callers who hit multi-unit or extreme-length scenarios MUST override via the `regulatory_min_width_m` config parameter (already supported).

---

## Recommendations

| # | Action | Severity | Effort |
|---|---|---|---|
| 1 | Verify 0.9m claim against NBC 2016 Part 3 § 14 + Part 4 § 4.3 in actual PDF — confirm the single-dwelling-unit case allows 0.9m for short corridors. | HIGH | Small |
| 2 | If PDF shows 1.0m is the canonical single-dwelling minimum (rather than 0.9m), bump the default and ship a v1 patch. | HIGH | Trivial code change |
| 3 | Document in user-facing copy that BuildEase's corridor minimums target single-family residential only; multi-unit / commercial layouts need an architect override. | MEDIUM | Small (UI text) |
| 4 | When B-238 (architect review) happens, prioritize corridor + staircase + room minima as one verification pass — STAIRCASE (B-150) and CORRIDOR (B-108) and BALCONY (B-150) all share the same uncertainty. | — | (calendar) |
| 5 | Add a long-corridor check (length > 30m) that prompts an override-recommendation — currently no such prompt exists. | MEDIUM | M (new rule) |

---

## Audit trail — what S55 changed

1. `06_upstream_codebase/buildemup/components/c08/schema.py` — added a citation breadcrumb to `CorridorDesignConfig` docstring pointing to this report and naming NBC Part 3 § 14 / Part 4 § 4.3 + the v1 single-dwelling-unit scope.
2. `06_upstream_codebase/buildemup/tests/test_s55_b108_nbc_corridor_min.py` — new tests asserting the 0.9m default is intact and the breadcrumb mentions NBC.
3. This report (B108_PARTIAL_NBC_VERIFICATION_S55.md) — durable audit-trail file in `05_integrity_check/`.

---

*B-108 stays open in backlog until full PDF verification + architect sign-off (B-238). This S55 pass closes the "is the default value defensible for v1?" gate; the legal-defensibility gate remains open.*
