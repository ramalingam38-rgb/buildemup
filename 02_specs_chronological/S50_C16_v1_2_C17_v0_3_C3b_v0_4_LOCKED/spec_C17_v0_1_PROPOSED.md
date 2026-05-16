# C17 — Quote Comparison Engine
## Spec v0.1 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Session:** S49 close (or S50 open).
**Authoritative source:** `MASTER_DESIGN_NARRATIVE_v2_9.md` § 5.5
"Component 17 — Quote Comparison Engine" + Design Principles v3.1
Principle 3 (advisory tone) + Principle 2 (Transparency Triple).
**Predecessor:** none — C17 is greenfield, no v0.0 baseline.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone. This document
> is PROPOSED only. Do not interpret as locked until Ramalingam
> explicitly states "v0.1 LOCKED" (or "v1.0 LOCKED" after critique
> rounds — see § 13).

---

## § 0 — Composition rationale

C17 is the final unbuilt component in Track 3 canonical (positions 1
through 17, 19 sub-components when C3a/C3b and C11a/C11b are counted
separately). C3b remains the only other gap.

C17 is named **"the strongest individual differentiator"** in the
master narrative. It directly closes the **Information asymmetry**
between homeowner and contractor — the founding-story problem.

C17 is dependency-unblocked now that C16 LOCKED. Its upstream inputs
are:
- C7's `StructuralCostEstimator` (frame + foundation cost,
  `TransparencyTriple` output, brand/grade/IS-code via `MaterialRate`)
- C16's `DualDrawingBundle.permit_drawing_model.compliance_attestation`
  (built-up area, floor count, FAR — anchors for sanity checks)
- C16's `WorkingDrawingModel.finish_schedule` (per-room finish
  materials — anchors for fuzzy match against quote line items)
- Project-level `RateProvider` (city-specific median + min/max rates)

C17's outputs feed into:
- The user-facing quote-comparison report
- The Contractor Pack (one of the 4 docs in the Contractor Defence Layer)
- Marketing / viral artifacts ("Saved ₹9L by uploading your quote")

This spec follows the C15/C16 pattern: § 1 scope, § 2 output contract,
§ 3 phases, § 4 errors, § 5 versioning, § 6 hard ceilings, § 7 invariants,
§ 8 dependencies, § 9 backlog, § 10 LOCK request.

---

## § 1 — Scope

C17 consumes:
1. A **user-uploaded contractor quote** (PDF, image, or Excel — parsed
   into structured line items via OCR + Claude API call)
2. The **project BOQ** derived from C7 cost estimates + C16 schedules +
   `RateProvider` rates

C17 produces a **`QuoteComparisonReport`** — a `TransparencyTriple`
of quote-vs-BOQ deltas + per-line verdicts + missing-items list +
suspicious-lump-sum list + counter-offer + contractor credibility score.

### 1.1 — What C17 IS

- A **data emitter** producing a structured comparison report. (Same
  scope discipline as C16: no pixels, no PDF rendering, no UI.)
- An **advisory layer** (Design Principles v3.1 Principle 3): produces
  language like "this rate is above current Chennai market" — never
  "contractor is overcharging."
- **Code-cited, brand-grounded:** every comparison anchors on
  `MaterialRate.is_code` + `MaterialRate.brand` + `MaterialRate.grade`
  from the `RateProvider`, NOT on opaque cost categories.
- **Transparency-Triple output** for every numeric: range + midpoint +
  derivation (per Principle 2).

### 1.2 — What C17 IS NOT (scope boundary)

| Concern | C17 emits | Consumer / other component handles |
|---|---|---|
| OCR / PDF parsing of quote file | structured `ParsedQuote` input — produced by an **upstream parser**, NOT by C17 | upstream: PDF/OCR/Claude-API parser ships into C17 |
| Visual rendering of report | structured report data | downstream consumer renderer |
| Sending counter-offers to contractor | counter-offer language only | user / consumer UI |
| Real-time supplier rates / live market scrape | static `RateProvider` rates per city | v2 vision item |
| Contractor reputation / reviews | credibility score from quote-content heuristics ONLY | not a contractor marketplace |
| Auto-negotiating with contractor | language for the user to use | user is always in the loop |

### 1.3 — Scope test (per Design Principles v3.1 § 2)

C17 closes the **Information asymmetry** between homeowner and contractor.
This is the one of three asymmetries the founding scope test
identifies. C17 is in-scope by definition.

---

## § 2 — Output contract

C17 emits a `QuoteComparisonReport`. Single typed output, all fields
canonically ordered for replay determinism (per the C15/C16 R7c pattern).

### 2.1 — Top-level `QuoteComparisonReport`

```
QuoteComparisonReport
├── source_quote_signature:        str (64-hex sha256 of parsed quote)
├── source_boq_signature:          str (64-hex sha256 of project BOQ)
├── c17_version:                   str ("v0.1.PROPOSED" at v0.1)
├── c17_schema_version:            int (1 at v0.1)
├── jurisdiction_profile_id:       str (city — must match upstream)
├── declared_domain_scope:         str (residential_v1 / etc.)
│
├── matched_lines:                 tuple[MatchedLine, ...]
│       Each = one ParsedQuote line item × matched BOQ line.
│       sorted lex-ASC by quote_line.line_id.
│
├── missing_from_quote:            tuple[MissingItem, ...]
│       BOQ items that have NO corresponding quote line.
│       sorted lex-ASC by boq_item.boq_id.
│
├── unmatched_quote_lines:         tuple[UnmatchedQuoteLine, ...]
│       Quote lines that don't match any BOQ item (extra work the
│       contractor added that wasn't in our scope).
│       sorted lex-ASC by quote_line.line_id.
│
├── suspicious_lump_sums:          tuple[SuspiciousLumpSum, ...]
│       Quote lines that are lump-sum > 2% of total without itemization.
│
├── total_comparison:              TotalComparison
│       Top-level ₹ comparison: quote_total vs our_estimate_total vs
│       counter_offer with TransparencyTriple derivation.
│
├── counter_offer:                 CounterOffer
│       Recommended response language + adjusted total.
│
├── contractor_credibility:        ContractorCredibility
│       Score 0–100 + tier label + the heuristic components that drove it.
│
├── advisory_flags:                tuple[AdvisoryFlag, ...]
│       R8 passthrough from upstream + C17-emitted flags.
│
├── upstream_check_provenance:     tuple[CheckProvenance, ...]
│       Per R15 — every numeric traces back to upstream source.
│
├── canonical_replay_signature:    str  (R7 byte-equal on replay)
├── presentation_signature:        str  (R32a — canonical as prefix)
└── schema_descriptor_digest:      str  (R26b)
```

### 2.2 — `MatchedLine` (the per-line verdict — core differentiator)

```
MatchedLine
├── line_id:                       str   (canonical from upstream)
├── quote_label:                   str   (verbatim from contractor)
├── matched_boq_id:                str   (which BOQ line this maps to)
├── matched_boq_label:             str   (our canonical label)
├── match_confidence_tier:         Literal["high", "medium", "low"]
│       per R39 (semantic-compression discipline from C16 v1.2):
│       discrete tiers, not continuous score.
├── match_basis:                   tuple[Literal[
│       "is_code", "brand", "grade", "name_fuzzy", "unit_match",
│   ], ...]  # ordered most→least authoritative
│
├── quote_quantity:                AttestedValue (UPSTREAM_AUTHORITATIVE)
├── quote_unit:                    str
├── quote_rate:                    AttestedValue (UPSTREAM_AUTHORITATIVE)
├── quote_total:                   AttestedValue (UPSTREAM_AUTHORITATIVE)
│
├── our_quantity:                  AttestedValue (UPSTREAM_AUTHORITATIVE from C7/C16)
├── our_rate_median:               AttestedValue (UPSTREAM_AUTHORITATIVE from RateProvider)
├── our_rate_min:                  AttestedValue (UPSTREAM_AUTHORITATIVE from RateProvider)
├── our_rate_max:                  AttestedValue (UPSTREAM_AUTHORITATIVE from RateProvider)
├── our_total:                     AttestedValue (LOCALLY_DERIVED — our_quantity × our_rate_median)
│
├── rate_delta_pct:                AttestedValue (LOCALLY_DERIVED)
│       (quote_rate - our_rate_median) / our_rate_median * 100
├── total_delta:                   AttestedValue (LOCALLY_DERIVED)
│       quote_total - our_total
│
├── verdict:                       PriceVerdict
│       enum {FAIR, HIGH, OVERPRICING, UNDERPRICED, MISSING_QTY}
├── verdict_explanation:           str
│       advisory-tone (Principle 3): "This rate is above current
│       Chennai market" not "Contractor is overcharging"
└── provenance:                    CheckProvenance
```

### 2.3 — `PriceVerdict` enum + thresholds

Per master narrative § 5.5 step 3:

| Delta | Verdict | Color (downstream) | Confidence required |
|---|---|---|---|
| `rate_delta_pct > +20%` | `OVERPRICING` | red | medium+ (low-confidence matches downgrade to HIGH) |
| `+5% < rate_delta_pct ≤ +20%` | `HIGH` | amber | any |
| `−5% ≤ rate_delta_pct ≤ +5%` | `FAIR` | green | any |
| `−20% ≤ rate_delta_pct < −5%` | `FAIR` | green | flag if quality concern |
| `rate_delta_pct < −20%` | `UNDERPRICED` | yellow | flag "often low-quality" |
| `our_quantity is None` | `MISSING_QTY` | grey | we can't compute delta |

**Thresholds are CONFIG, not hardcoded.** `RateProvider` may override
per-city (Mumbai contractor margins skew different from Chennai).

### 2.4 — `MissingItem` + `UnmatchedQuoteLine`

```
MissingItem
├── boq_id:                        str
├── boq_label:                     str
├── expected_quantity:             AttestedValue
├── expected_unit:                 str
├── expected_total_low_high:       tuple[float, float]  (range from RateProvider min/max)
├── severity:                      Literal["critical", "important", "minor"]
│       critical = structural / waterproofing / sanitation
│       important = electrical / lighting / plumbing
│       minor = aesthetic / nice-to-have
└── advisory_note:                 str
        e.g. "Waterproofing FF baths is typically included; absence
              may mean the contractor expects to charge later."

UnmatchedQuoteLine
├── line_id:                       str
├── quote_label:                   str
├── quote_total:                   AttestedValue
├── classification:                Literal[
│       "extra_scope",       # legitimate addition outside our BOQ
│       "duplicate",         # already covered by another line
│       "unrecognized",      # we can't classify
│       "suspicious",        # too generic to verify
│   ]
└── advisory_note:                 str
```

### 2.5 — `SuspiciousLumpSum`

```
SuspiciousLumpSum
├── line_id:                       str
├── label:                         str         # "Sundries", "Misc", "Site preparation"
├── amount:                        AttestedValue
├── pct_of_total:                  AttestedValue (LOCALLY_DERIVED)
├── trigger_rule:                  Literal[
│       "generic_label_over_2pct",
│       "no_itemization",
│       "duplicates_other_line",
│   ]
└── advisory_note:                 str   # advisory-tone request for breakdown
```

### 2.6 — `TotalComparison` (the headline number)

```
TotalComparison
├── quote_total:                   AttestedValue (UPSTREAM_AUTHORITATIVE)
├── our_estimate_total:            TransparencyTriple
│       (full breakdown — passthrough from C7 + C16 + RateProvider)
├── delta_amount:                  AttestedValue (LOCALLY_DERIVED)
├── delta_pct:                     AttestedValue (LOCALLY_DERIVED)
├── headline_label:                str
│       e.g. "Quote ₹71.5L vs our estimate ₹58.5L — ₹13L higher (22%)"
└── potential_savings_low_high:    tuple[float, float]
        Range: (counter_offer.adjusted_total - quote_total).
        Per master narrative: "Saved ₹5–10L per project".
```

### 2.7 — `CounterOffer`

```
CounterOffer
├── adjusted_total:                TransparencyTriple
│       our_estimate_total + reasonable_contractor_margin
├── reasonable_contractor_margin_pct: AttestedValue
│       from RateProvider.contractor_margin_default_pct (e.g. 7%)
├── negotiation_language:          str
│       advisory-tone, multi-line text the user can paste into a
│       message to the contractor. NEVER confrontational.
└── savings_estimate:              TransparencyTriple
        quote_total - adjusted_total (with range from rate variability)
```

### 2.8 — `ContractorCredibility`

```
ContractorCredibility
├── score:                         int (0–100)
├── tier:                          Literal[
│       "trustworthy",       # 80–100
│       "reasonable",        # 60–79
│       "needs_scrutiny",    # 40–59
│       "high_risk",         # 0–39
│   ]
├── components:                    tuple[CredibilityComponent, ...]
│       Each: name + score_contribution + advisory_note
│       Components:
│         - itemization_completeness  (BOQ items mapped / total BOQ items)
│         - lump_sum_discipline       (fewer suspicious lumps → higher)
│         - rate_consistency          (variance of rate deltas)
│         - missing_critical_items    (waterproofing / electrical / plumbing)
│         - margin_transparency       (whether margin shown as separate line)
└── overall_advisory_note:          str
```

---

## § 3 — Phase pipeline

C17 uses the same 6-phase pattern as C16 (α through ζ) so the
conceptual model stays uniform. Each phase is a pure function.

### Phase α — Quote ingestion + canonicalization

INPUT: `ParsedQuote` (upstream parser output — typed dataclass).
PROCESSING:
1. Validate `ParsedQuote.line_items` shape + non-emptiness.
2. Canonicalize line_ids (lex-ASC sort, dedupe).
3. Normalize labels (lowercase, strip punctuation, extract grade strings).
4. Build `CanonicalizedQuote` with stable line_ids.

OUTPUT: `CanonicalizedQuote`.

### Phase β — BOQ assembly

INPUT: C7 `StructuralCostEstimator` output, C16 `WorkingDrawingModel.finish_schedule`,
       C16 `permit_drawing_model.compliance_attestation`, `RateProvider`.
PROCESSING:
1. Derive structural BOQ lines from C7 (concrete, steel, formwork, foundation).
2. Derive finish BOQ lines from C16 finish_schedule × room areas
   from `permit_drawing_model.compliance_attestation`.
3. Derive plumbing + electrical BOQ lines from C16 plumbing_stacks
   + room counts (heuristic at v0.1; brief-driven post-v1.0).
4. Attach `MaterialRate` (with brand/grade/IS-code) from `RateProvider`
   to every BOQ line.

OUTPUT: `ProjectBOQ` with stable lex-ASC ordering.

### Phase γ — Matching

INPUT: `CanonicalizedQuote`, `ProjectBOQ`.
PROCESSING:
1. **Tier 1 (high-confidence) match:** IS code OR brand+grade exact match.
2. **Tier 2 (medium-confidence) match:** brand-only OR grade-only +
   unit match.
3. **Tier 3 (low-confidence) match:** name fuzzy match (Levenshtein
   distance ≤ threshold) + unit match.
4. **Multi-pass deduplication:** if a single BOQ line attracts multiple
   quote lines (or vice versa), resolve via tier hierarchy +
   lex-ASC tiebreak.
5. Surface unmatched-from-both-sides into `unmatched_quote_lines` +
   `missing_from_quote`.

OUTPUT: `MatchedSet` + `MissingSet` + `UnmatchedSet`.

### Phase δ — Verdicting

INPUT: `MatchedSet`, `RateProvider` (for thresholds + margin defaults).
PROCESSING:
1. Compute `rate_delta_pct` per matched line.
2. Apply `PriceVerdict` thresholds from § 2.3.
3. Low-confidence matches with `OVERPRICING` verdict downgrade to
   `HIGH` (we don't accuse confidently when match is uncertain).
4. Build advisory-tone `verdict_explanation` per line (Principle 3).
5. Detect suspicious lump sums (`SuspiciousLumpSum` rules § 2.5).

OUTPUT: `MatchedLine[]` + `SuspiciousLumpSum[]`.

### Phase ε — Totals + counter-offer

INPUT: `MatchedLine[]`, `MissingSet`, `UnmatchedSet`, `RateProvider`.
PROCESSING:
1. Compute `quote_total` (sum) + `our_estimate_total` (with
   `TransparencyTriple` derivation — passthrough from C7 + finish costs).
2. Compute `adjusted_total = our_estimate_total + (our_estimate_total ×
   reasonable_contractor_margin_pct)`.
3. Build `CounterOffer.negotiation_language` per Principle 3
   (advisory tone template — see § 7.1).
4. Compute `potential_savings_low_high` as range.

OUTPUT: `TotalComparison` + `CounterOffer`.

### Phase ζ — Credibility + bundle signing

INPUT: all phase outputs.
PROCESSING:
1. Compute `ContractorCredibility.score` from 5 components in § 2.8.
2. Apply tier mapping per score.
3. Build `R15` provenance trail (every numeric back to its upstream).
4. Compute `canonical_replay_signature` (R7 byte-equal — R7d: no time).
5. Compute `presentation_signature` (R32a — canonical as prefix).
6. Compute `schema_descriptor_digest` (R26b).
7. Construct `QuoteComparisonReport` (R20-equivalent referential
   integrity enforced at `__post_init__`).

OUTPUT: `QuoteComparisonReport`.

---

## § 4 — Error tiers (mirrors C16's two-tier hierarchy)

### 4.1 — `LocalQuoteError` (always halts)
- `UpstreamSchemaDriftError` — `ParsedQuote` doesn't match expected shape
- `C17ConfigurationError` — bad `RateProvider` / jurisdiction mismatch
- `JurisdictionNotSupportedError` — no rates for city
- `BOQAssemblyError` — C7/C16 upstream contracts unsatisfied

### 4.2 — `PerQuoteLineError` (STRICT raises / WARN collects)
- `MissingUpstreamDataError` — required upstream field is None/empty
- `RateNotFoundError` — `RateProvider.get_rate(category, key)` raises KeyError
- `MatchConfidenceUnderrunError` — Tier 3 match falls below acceptable
  Levenshtein threshold (STRICT halts; WARN moves line to unmatched)
- `LumpSumPolicyViolationError` — quote has too many lump sums to
  produce a useful comparison

STRICT vs WARN mode passed in by orchestrator (same pattern as C16).

---

## § 5 — Versioning

```python
C17_VERSION = "v0.1.PROPOSED"
C17_REPORT_SCHEMA_VERSION = 1
C17_IDENTITY_GENERATION = 1

SUPPORTED_JURISDICTIONS = {"tn_cdbr_2019"}  # v0.1 ships Chennai-first
SUPPORTED_DOMAIN_SCOPES = {"residential_v1"}

EXPECTED_C7_VERSION   = "v0.8.LOCKED"
EXPECTED_C16_VERSION  = "v0.5.LOCKED"   # runtime version; spec v1.2 LOCKED

EPSILON_RATE_DELTA_PCT = 0.5    # below 0.5%, treat as zero delta
EPSILON_AMOUNT_RUPEES  = 100    # below ₹100, treat as rounding noise
```

R9 (from C15/C16) carries forward: ADDITIVE field bumps `_SCHEMA_VERSION`
MINOR; removal/rename requires MAJOR (cross-hundred boundary).

---

## § 6 — Hard ceilings

| Field | Hard ceiling | Rationale |
|---|---|---|
| `ParsedQuote.line_items` length | 500 | typical residential quotes are 50–150 lines; > 500 indicates parser error |
| `quote_total` | ₹50 crore (5e8) | residential v1 scope |
| Single line item amount | ₹1 crore (1e7) | a lump sum > ₹1Cr is structurally impossible for residential |
| `MaterialRate.rate` | ₹1 lakh per unit | sanity bound |
| Levenshtein threshold | 0.4 (40% of label length) | beyond this is no longer fuzzy match — it's unrelated |
| Match-tier downgrade threshold | confidence < 0.5 → tier 3 | per R39 discrete tiers, not continuous |

Hard ceilings raise `LocalQuoteError`; never silently truncated.

---

## § 7 — R-invariants (initial set — 12)

C17 inherits C16's R7 / R8 / R9 / R15 / R20 / R22 / R25 / R32a / R26b /
R33b / R35 / R36 / R37 / R39 pattern, **adapted** for C17's domain.
Initial v0.1 invariant set:

| Invariant | Statement |
|---|---|
| **R1** (C17-local) | Every numeric output is wrapped in `AttestedValue` per R22 (C16 inheritance) |
| **R2** | Every verdict explanation MUST be advisory-tone (Principle 3) — enforced via lint of `verdict_explanation` text against a banned-phrase list ("overcharging", "fraud", "scam", "ripping off") |
| **R3** | `rate_delta_pct` and `total_delta` are LOCALLY_DERIVED; quote rates and our rates are UPSTREAM_AUTHORITATIVE — never blended |
| **R4** | Match confidence is **tiered** (high / medium / low), never continuous — per C16 R39 |
| **R5** | `OVERPRICING` verdict requires `match_confidence_tier ∈ {high, medium}`. Low-confidence matches downgrade to `HIGH`. We never accuse confidently when uncertain. |
| **R6** | `canonical_replay_signature` is byte-equal on replay (R7 inheritance from C16) |
| **R7** | `presentation_signature` has canonical as prefix (R32a inheritance) |
| **R8** | `QuoteComparisonReport` schema is public versioned API (R37 inheritance) — MINOR additive, MAJOR breaking, deprecation policy applies |
| **R9** | `counter_offer.adjusted_total` MUST be derived as `our_estimate_total + reasonable_contractor_margin`. Never undercut. Never inflate beyond `RateProvider.contractor_margin_range_pct().high`. |
| **R10** | Architectural primacy (R36 inheritance) — every comparison line MUST attach to a building element identifier (room_id, wall_id, etc.) from C16 OR to a structural element from C7. Free-floating comparisons prohibited. |
| **R11** | Determinism boundary (R35 inheritance) — same `ParsedQuote` + same `RateProvider` + same C7/C16 inputs → byte-equal `canonical_replay_signature`. |
| **R12** | Semantic compression discipline (R39 inheritance) — every new field added to `QuoteComparisonReport` MUST attach to a quote line OR be required for replay determinism OR be required for credibility scoring. No free-floating metadata. |

Critique walk may add R13–Rn before LOCK.

### 7.1 — Advisory-tone template (R2 enforcement reference)

The `verdict_explanation` and `negotiation_language` strings are
generated from templates with banned-phrase lint:

**Allowed:**
- "This rate is above current Chennai 2026 median (₹{our_rate}/unit
  vs ₹{quote_rate}/unit, +{delta}%)."
- "The {item} rate is {delta}% higher than typical for this brand
  and grade."
- "You may want to ask the contractor for the brand and grade
  specification on {item}."
- "It's worth requesting a breakdown for the lump-sum line '{label}'
  before signing."

**Banned (R2 lint):**
- "overcharging", "ripping off", "fraud", "scam", "cheating", "rob"
- "do not pay", "refuse to pay"
- "must demand", "demand immediately"

---

## § 8 — Upstream dependencies

| Dependency | Locked version | Used for |
|---|---|---|
| C7 (Structural Grid) | v0.8.LOCKED | structural BOQ (concrete, steel, formwork, foundation) via `StructuralCostEstimator` |
| C16 (Dual-Drawing Renderer) | v1.2 LOCKED (S49) | finish schedule, compliance attestation (area, FAR, floor count), room geometry for finish-cost computation |
| `RateProvider` (utility) | concrete city impls (e.g. `ChennaiRateProvider`) | brand/grade/IS-code/rate lookup |
| `TransparencyTriple` (utility) | existing | numeric output format |
| `AttestedValue` (from C16 contracts) | LOCKED | provenance + authority discipline |
| `AdvisoryFlag` (from C13/C14) | LOCKED | R8 passthrough |

**Upstream parser (PDF/OCR/Claude API → `ParsedQuote`)** is OUT OF
SCOPE for C17 itself. C17 consumes a typed `ParsedQuote` produced by
a separate parsing layer. This is the same architectural pattern
C16 uses (it consumes typed upstream contracts, not raw inputs).

The parser will be `B-C17-PARSER-INTEGRATION` post-LOCK.

---

## § 9 — Backlog (initial — Rule 9)

### 9.1 — v1.0 LOCK-mandatory (must close before LOCK)

| ID | Description | Effort |
|---|---|---|
| `B-C17-PHASE-IMPLEMENTATIONS` | Implement all 6 phases (α–ζ) | L |
| `B-C17-TEST-COVERAGE-PARITY-WITH-C16` | ≥150 tests across phases + orchestrator + PBT layer ≥15 + 5-scenario adversarial corpus | L |
| `B-C17-RATE-PROVIDER-CHENNAI-V1` | Concrete `ChennaiRateProvider` with 50+ rates for v1 launch | M |
| `B-C17-ADVISORY-TONE-LINT` | Automated lint of `verdict_explanation` against banned-phrase list (R2 enforcement) | S |
| `B-C17-FUZZY-MATCH-ACCURACY-CALIBRATION` | Test corpus of 20 real-world quotes with known correct matches; tune Levenshtein threshold | M |

### 9.2 — DEFERRED post-LOCK (v1.x acceptable)

| ID | Description | Trigger |
|---|---|---|
| `B-C17-PARSER-INTEGRATION` | OCR + Claude API parser layer producing `ParsedQuote` | v1.0 ships with manual `ParsedQuote` input from web form / Excel template; full parser is v1.1 |
| `B-C17-MULTI-CITY-RATES` | Bangalore, Mumbai, Delhi, Hyderabad `RateProvider` implementations | When each city launches |
| `B-C17-CREDIBILITY-CALIBRATION` | Real-world calibration of credibility tiers against contractor outcomes | After v1 launch + 6 months of data |
| `B-C17-CONTRACTOR-RESPONSE-LOOP` | Two-way negotiation flow (contractor responds → user can re-run C17) | v2 feature |
| `B-C17-NEGOTIATION-LANGUAGE-LOCALIZATION` | Tamil + Hindi versions of counter-offer templates | v1.x post Tamil-language brief |
| `B-C17-PLUMBING-ELECTRICAL-BOQ-DETAILED` | Detailed plumbing/electrical BOQ from brief (not heuristic from room counts) | Brief integration matures |
| `B-C17-AGGREGATE-CONTRACTOR-CREDIBILITY` | Cross-project credibility (same contractor, multiple projects) | Multi-project data + identity discipline |
| `B-C17-EXPORT-BOQ-EXCEL` | Export ProjectBOQ as Excel for user to share with contractors | UI / downstream |

### 9.3 — Summary

| Category | Count |
|---|---|
| LOCK-mandatory | 5 |
| DEFERRED | 8 |
| **Total tracked** | **13** |

---

## § 10 — Test plan (mirrors C16 § 7)

Target at v1.0 LOCK:

| Test file | Count | Purpose |
|---|---|---|
| `test_c17_versioning.py` | ~8 | constants, expected upstream versions |
| `test_c17_errors.py` | ~15 | two-tier hierarchy |
| `test_c17_contracts.py` | ~30 | output dataclass shapes + post_init validation |
| `test_c17_config.py` | ~12 | RenderingConfig-equivalent for thresholds |
| `test_c17_phase_alpha.py` (canonicalization) | ~15 | quote parsing edge cases |
| `test_c17_phase_beta.py` (BOQ assembly) | ~15 | C7 + C16 input handling |
| `test_c17_phase_gamma.py` (matching) | ~25 | three-tier match logic, dedup, edge cases |
| `test_c17_phase_delta.py` (verdicting) | ~15 | threshold logic + low-conf downgrade |
| `test_c17_phase_epsilon.py` (totals) | ~12 | counter-offer math, savings range |
| `test_c17_phase_zeta.py` (credibility + signing) | ~15 | credibility scoring, signature determinism |
| `test_c17_orchestrator.py` | ~15 | STRICT vs WARN, batch |
| `test_c17_pbt.py` (PBT layer) | ~15 | property-based: signature determinism, match tier monotonicity |
| `test_c17_adversarial_corpus.py` (5 scenarios) | ~10 | (1) all-lump-sum quote, (2) all-missing quote, (3) all-matching quote, (4) quote with no IS-codes (fuzzy-only), (5) quote at hard ceiling |
| `test_c17_advisory_tone_lint.py` | ~10 | R2 enforcement — banned phrases caught |
| **Total** | **~210** | |

---

## § 11 — Critique walk readiness (Rule 7)

Initial critique-walk surfaces I'd expect, with pre-emptive notes:

| Likely critique | Pre-emptive position |
|---|---|
| "C17 is doing too much — split parser, comparison, credibility?" | C17 explicitly EXCLUDES the parser (§ 8 footnote). Comparison + credibility are tightly coupled (credibility scores derive from comparison heuristics); splitting them would create R39 violations. **Defend the boundary.** |
| "Why is OCR not in scope?" | Same reason C16 doesn't render pixels: C17 is a structured-data emitter. The parser is an independent upstream layer. (§ 1.2 + § 8 explicit.) |
| "Fuzzy match accuracy is risky for legal/cost claims" | R5 explicitly downgrades `OVERPRICING` → `HIGH` for low-confidence matches. R2 advisory-tone lint blocks accusatory language. § 9.1 includes calibration corpus. **Defend the tier discipline.** |
| "How do we handle contractors who refuse to itemize?" | `SuspiciousLumpSum` detection (§ 2.5) + advisory-tone request-for-breakdown language. We never refuse to produce a report; we flag the lumps and proceed. |
| "What if `RateProvider` rates are outdated?" | `MaterialRate.source` carries the rate provenance string. Consumer surfaces "rates as of Chennai 2026 Q2" so user knows the timestamp. `RateProvider.kb_version` enables drift detection. |
| "Tamil-language quote support?" | v1.0 English-only (matches brief intake). `B-C17-NEGOTIATION-LANGUAGE-LOCALIZATION` filed. |

---

## § 12 — Three-check protocol (Rule 10.6 — at LOCK time)

(To be filled at LOCK time. Promised vs delivered checks, R-invariant
enforcement-point map, file integrity + test pass count.)

---

## § 13 — LOCK adjudication request (Rule 8)

**This document is C17 v0.1 PROPOSED. PENDING Ramalingam LOCK
adjudication.**

C17 follows the same multi-round PROPOSED → critique → LOCK pattern
as C15 (3 rounds) and C16 (3 PROPOSED rounds: v1.0 → v1.1 → v1.2).
v0.1 LOCK is unusual — typically a critique round produces v0.2
PROPOSED before LOCK. The path I expect:

1. **You read v0.1 PROPOSED + run a critique walk.**
2. I respond with patches → **v0.2 PROPOSED** + per-point verdicts table.
3. Possibly another critique → **v0.3 PROPOSED** or directly LOCK.
4. **LOCK.** Then code begins per § 9.1 LOCK-mandatory backlog.

To LOCK v0.1 as-is (which would skip the critique round), please
confirm:

1. **§ 1 scope** — C17 IS quote comparison + credibility; C17 is NOT
   the parser, not the renderer, not the negotiation broker.
2. **§ 2 output contract** — `QuoteComparisonReport` shape is right.
3. **§ 3 phase pipeline** — 6 phases α–ζ mirroring C16's pattern.
4. **§ 7 invariants** — R1–R12 are correct as initial set.
5. **§ 8 upstream dependencies** — C7 + C16 + RateProvider are the
   correct anchors.
6. **§ 9 backlog** — 5 LOCK-mandatory + 8 deferred.

If yes to all: **state "C17 v0.1 LOCKED"** (unusually direct LOCK).

If corrections needed: state which sections need patches and I'll
compose v0.2 PROPOSED.

**My recommendation: do a critique walk first.** v0.1 is the first
draft; it would be unusual for a first-draft spec this size (≈600
lines, 12 invariants, 13 backlog items) to LOCK without at least
one critique round. Expect a v0.2 or v0.3 before LOCK.

---

**END OF C17 v0.1 PROPOSED — PENDING Ramalingam LOCK**
