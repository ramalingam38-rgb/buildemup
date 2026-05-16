# v0_2_backlog_S51_C17_critique_walk_additions.md

**Session:** S51
**Date:** 2026-05-15
**Authority:** Ramalingam directive at S51 close ("File the backlogs and lock this build")
**Component affected:** C17 (BUILD-LOCKED this session at v0.3.LOCKED implementation)
**Predecessor file:** v0_2_backlog_S47_additions.md

This file records all backlog additions surfaced by the 15-item adversarial critique walk on C17 v0.3 LOCKED build at S51 close.

## Verdict distribution

- VALID-BUT-BACKLOG: 7 items (filed below)
- VALID-BUT-FUTURE (v2): 2 items (filed below as v2-conditional)
- DOCUMENTED (already-tracked): 4 items (no new entry — pointers below)
- MISFRAMED / DUPLICATIVE: 6 items (closed with rationale)

Web-search performed per Rule 7: ASCE J. Construction Engineering Vol 149 No 2 (lexical BOQ matching) + Vilnius Tech J. Civ. Eng. & Mgmt. 2026 (BERT NER for construction text, F1 0.81–0.97 vs lexical).

Code-grep performed per Rule 7: verified specific false-positive example `SequenceMatcher("rcc slab waterproof additive", "waterproof coating").ratio() = 0.609` — clears `LEVENSHTEIN_HARD_CEILING=0.4` floor, would currently match in γ. Verified `_signal_explanation` already emits `"delta +X.X%"` literal magnitude — pushback on critique item #5.

---

## § 1 — VALID-BUT-BACKLOG (v1.0 candidates)

### B-C17-SEMANTIC-MATCH-LAYER

**Status:** OPEN, v1.0-strong-candidate
**Priority:** HIGH (verified false-positive risk in γ matching)
**Description:** Add second-pass semantic-compatibility gate before accepting tier-2 (medium) or tier-3 (low) fuzzy matches. Two-stage:
1. **Ontology compatibility check:** classify both labels into domain categories (structural / plumbing / finishing / electrical / wet-zone / waterproofing / earthwork / misc). If categories mismatch, downgrade to tier-4 (human_verification_recommended).
2. **Embedding similarity:** optional small-model embedding (e.g., MiniLM sentence-transformer ≤80MB) check; if embedding-cosine < 0.6, downgrade to tier-4.
**Origin:** S51 critique item #1; verified by code grep — reviewer's example "rcc slab waterproof additive" vs "waterproof coating" gives lexical ratio 0.609, currently passes our 0.4 floor.
**Trigger:** Before v1.0 LOCK, OR before first production deployment of C17, whichever is earlier.
**Effort:** M (ontology table + classifier ≤200 LOC); L if embedding stage added (model load + inference latency budget).
**Test additions required:** specific false-positive corpus (≥20 known-distinct pairs) must downgrade to tier-4 after fix.
**Spec-amendment hook:** likely amends γ matching § (would touch spec § 5).

### B-C17-ARITHMETIC-MISMATCH-INDICATOR

**Status:** OPEN, v1.0-strong-candidate
**Priority:** HIGH (signal we have, surface weakly)
**Description:** Phase α currently logs `qty × rate ≠ total` mismatches into `QuoteLineCanonical.raw_notes` only. Promote to an explicit indicator with severity classification:
- `rounding` (Δ < 1% of line total) — silent
- `ocr_or_arithmetic_error` (1% ≤ Δ < 10%) — informational indicator
- `suspicious_discrepancy` (Δ ≥ 10%) — advisory indicator surfaced to user
Track per-contractor systemic patterns if/when telemetry exists.
**Origin:** S51 critique item #13. The qty×rate cross-check is already done in α; we just don't escalate. Strongest finding in the critique walk.
**Trigger:** v1.0 candidate.
**Effort:** S (new indicator dataclass in schema.py + α writes it + ζ relays it; ≤120 LOC).
**Test additions required:** test_phase_alpha + test_phase_zeta covering the three severity bands.

### B-C17-RATE-SANITY-DETECTOR

**Status:** OPEN, v1.0-candidate
**Priority:** MEDIUM-HIGH (OCR defense-in-depth)
**Description:** Add order-of-magnitude sanity check on incoming quote rates vs ChennaiRateProvider. If `quote_rate > 10 × our_rate_max` OR `quote_rate < 0.1 × our_rate_min`, flag for human review with explicit "this may be a parse / OCR artifact" advisory. Does NOT modify the rate (R3 preserved); only surfaces an indicator.
**Origin:** S51 critique item #7. ParsedQuote signature catches post-parse tampering but not pre-signature OCR corruption (e.g., "₹450" → "₹4500"). RateProvider gives us a reference envelope to detect this cheaply.
**Trigger:** v1.0 candidate.
**Effort:** S (new check inside δ; ≤80 LOC + tests).

### B-C17-LEGITIMATE-PREMIUM-DISCLAIMER

**Status:** OPEN, v1.0-candidate
**Priority:** MEDIUM (advisory polish)
**Description:** Narrow textual addition to ABOVE_REFERENCE_RANGE and BELOW_TYPICAL_QUALITY_RISK signal_explanations: append one principle-aligned sentence acknowledging possible legitimate reasons (premium specification, site access, urgency) — without modelling any of them. Phrasing: "Higher rates can reflect premium specifications, complex site conditions, or specialised workmanship — worth asking the contractor what's included." Stays advisory-tone-clean (passes R2 lint).
**Origin:** S51 critique item #3 (the principle-aligned slice of an otherwise MISFRAMED proposal).
**Trigger:** v1.0 candidate.
**Effort:** XS (text-only change in δ `_signal_explanation`; lint test additions).
**Explicitly NOT in scope:** site-difficulty index, urgency multiplier, premium-finish classifier, contractor-reputation tier — these contradict spec § 0.1 mission.

### B-C17-MATCH-BASIS-EXPANSION

**Status:** OPEN, v1.0-ship-with-semantic-match
**Priority:** MEDIUM
**Description:** When B-C17-SEMANTIC-MATCH-LAYER lands, extend `MatchCandidate.basis` tuple to expose the individual signal scores as discoverable fields: `lexical_score`, `ontology_compatibility`, `embedding_cosine`, `unit_compatible`, `is_code_match`, `brand_match`, `grade_match`. Stays discrete (token strings + optional small floats), NOT continuous 0.0-1.0 confidence (continuous was deliberately rejected as false-precision).
**Origin:** S51 critique item #8 (principle-aligned slice).
**Trigger:** Ship with B-C17-SEMANTIC-MATCH-LAYER.
**Effort:** S (schema field + populating code; ≤60 LOC).

### B-C17-CONTRACTOR-RESPONSE-SECTION

**Status:** OPEN, v1.0-candidate
**Priority:** MEDIUM-HIGH (legal defensibility)
**Description:** Add optional schema field `QuoteComparisonReport.contractor_response: Optional[ContractorResponse]` (immutable, separately signed, never modifies upstream signals). Lets contractors attach a rebuttal or context note that travels with the report. Strengthens reputation defense if reports are shared publicly.
**Origin:** S51 critique item #11. Pairs with already-filed B-C17-LEGAL-REVIEW.
**Trigger:** v1.0 candidate, ship with legal review.
**Effort:** M (schema additions + signature isolation + tests; ≤200 LOC).
**Spec amendment:** spec § 2 (schema) + possibly § 27 (signature isolation).

### B-C17-ALTERNATE-MARKET-REFERENCES

**Status:** OPEN, v1.0-candidate
**Priority:** MEDIUM (legal defensibility)
**Description:** Allow user or contractor to supply alternate rate sources (e.g., a different city, a different supplier quote, a published PWD schedule) that get displayed alongside our ChennaiRateProvider reference. We don't blend (R3 preserved); we show side-by-side. Reduces "biased single source" exposure.
**Origin:** S51 critique item #11.
**Trigger:** v1.0 candidate.
**Effort:** M (rate-provider abstraction extension + UI surface; ≤250 LOC).

---

## § 2 — VALID-BUT-FUTURE (v2 conditional)

### B-C17-PROBABILISTIC-LAYER-DESIGN

**Status:** OPEN, v2-conditional
**Priority:** ARCHITECTURAL (no v0.3/v1.0 work; design hook only)
**Description:** When/if we introduce ML inference (semantic embeddings beyond a fixed model, decomposition inference, learned rate calibration), do NOT integrate it into the deterministic core. Architect as:
- **Deterministic core:** preserves R6 byte-equal replay; ML outputs enter only as advisory annotations
- **Probabilistic augmentation layer:** versioned separately, persists inference snapshots (model_version, embedding_hash, inference_seed, confidence_distribution)
- **Forensic replay mode:** allows re-running with frozen model state
**Origin:** S51 critique item #6. Pre-emptive architectural note; no code action this cycle.
**Trigger:** Any C17 PR that introduces non-deterministic inference.
**Effort:** L (design document required before code).

### B-C17-FEEDBACK-TELEMETRY

**Status:** OPEN, v2-conditional
**Priority:** v2 (post-deployment)
**Description:** Anonymised correction telemetry: user overrides of γ matches, contractor objections, final negotiated values, accepted/rejected advisories. Used to re-calibrate matching heuristics, anomaly thresholds, decomposition inference. Tension with R6 determinism (item #6) — telemetry must NOT feed back into the deterministic core inside a session; it informs offline model updates only.
**Origin:** S51 critique item #10.
**Trigger:** Post first production deployment + ≥1000 reports.
**Effort:** L (telemetry pipeline + privacy/consent UX + offline calibration workflow).

---

## § 3 — Closed without filing (MISFRAMED / DUPLICATIVE / DOCUMENTED)

| Critique item | Verdict | Rationale |
|---|---|---|
| #2 Rate staleness | DOCUMENTED | Already tracked as B-C17-HEURISTIC-ROTATION-DISCIPLINE + v2 vision § 4. Volatility claim overstated (cement/sand/steel move 5-10%/quarter, not weeks-obsolete). |
| #3 Behavioral context (full proposal) | MISFRAMED | Site-difficulty index / urgency multiplier / premium-finish classifier directly contradict spec § 0.1 mission ("alignment NOT catching bad contractors"). Once we model "deserved premium," we're scoring contractors. Principle-aligned slice filed as B-C17-LEGITIMATE-PREMIUM-DISCLAIMER. |
| #4 Lump-sum handling | DOCUMENTED | Already tracked as B-C17-PER-LINE-BUNDLE-CONTEXT. Reviewer's "latent cost allocation / Bayesian decomposition" matches that backlog's intent. |
| #5 Tone reduces usefulness | MISFRAMED | Code grep shows `_signal_explanation` already emits literal `"delta +X.X%"` — magnitude is shown. Reviewer's "96% market percentile" proposal creates exactly the false-precision spec § 27.5 deliberately rejected (we have static min/median/max, not a calibrated empirical distribution). |
| #8 Continuous confidence (full proposal) | MISFRAMED | Continuous 0.0-1.0 was deliberately rejected; `match_basis` exposes individual signals discretely. Principle-aligned slice filed as B-C17-MATCH-BASIS-EXPANSION. |
| #9 Chennai-centric | DOCUMENTED | Spec § 9.1 explicitly scopes v1 to Chennai. RateProvider abstraction + jurisdiction_profile_id already designed for multi-city. |
| #12 Performance at scale | MISFRAMED for v0.3 | Residential ≤100 lines is target scope. Minor vectorisation opportunity noted but not filed — would be premature optimisation pre-deployment. |
| #14 Linear pricing assumption | DUPLICATIVE | Same problem space as item #4 (bundle decomposition). |
| #15 Contractor model | MISFRAMED | Explicit contradiction of spec § 0.1 — this IS the ContractorCredibility we removed in v0.3 LOCK. |

---

## Pattern D / D-067 audit

Pushback rate: 6 of 15 items rejected. Rationale per Pattern D:
- 4 items (#5, #8-full, #14, #15) contradict locked spec design choices (v0.2→v0.3 hard-out of ContractorCredibility; deliberate rejection of false-precision percentile bands; bundle decomposition already filed)
- 2 items (#9, #12) are explicit scope decisions documented in spec, not bugs
- 4 items (#2, #4, #10-pure-telemetry, #11-legal-pure) were already tracked — closed with pointer

The 9 NEW backlog items filed are concrete, shippable, and v1.0 / v2 properly bucketed.

**Strongest two findings (per S51 self-analysis):** B-C17-SEMANTIC-MATCH-LAYER (item #1, verified by code grep) and B-C17-ARITHMETIC-MISMATCH-INDICATOR (item #13, signal we have surfaced weakly). Both filed at v1.0 priority.

---

**End of S51 backlog additions.**
