# C17 — Quote Comparison Engine
## Spec v0.2 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor:** v0.1 PROPOSED (S49 close).
**Composed from:** v0.1 PROPOSED + critique walk findings (S50 open).
**Session:** S50.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone. This document
> is PROPOSED only. Do not interpret as locked until Ramalingam
> explicitly states "v0.2 LOCKED".

> **Per Rule 9.4:** Critiques arriving between PROPOSED and LOCK remain
> patch-eligible.

---

## § 0 — Composition rationale

v0.1 PROPOSED was structurally sound but **substantially under-addressed
the sociotechnical risks** that emerge once C17 mediates a real
homeowner-contractor relationship. The critique walk surfaced 20
concerns; 12 became SPEC-AMENDMENTs in v0.2; 2 became new backlog items.

**The single most important lesson v0.1 missed:** my own C15 precedent.
C15 was renamed from "Lived Quality Scorer" to "Layout Problem Finder"
because **aggregate scores compress into authority**. v0.1 then turned
around and added a `ContractorCredibility.score: int (0-100)` field — a
single-number trust compression for *contractors*, who are humans with
reputations, livelihoods, and legal standing. This was the same
mistake at higher stakes. v0.2 removes the aggregate score entirely.

### 0.1 — Mission framing (NEW)

**C17's purpose: alignment and clarity in the homeowner-contractor
relationship. NOT: catching bad contractors.**

This single sentence governs every other choice in this spec. Every
field, every verdict label, every advisory string, every output
ordering must be read against this mission.

Concretely:
- C17 does NOT produce verdicts that accuse, characterize, or grade
  contractors as people or businesses.
- C17 produces signals that help the homeowner ask better questions
  in their next conversation with their contractor.
- C17 assumes the homeowner and contractor will continue working
  together for 4–6 months. The output must not poison that relationship.
- C17 assumes its outputs WILL be screenshotted and shared publicly.
  Every emitted string is designed under that assumption.

This framing inherits Design Principles v3.1 Principle 3 (advisory tone,
not auditor tone) and applies it structurally, not just textually.

---

## § 1 — Scope

C17 consumes:
1. A **user-uploaded contractor quote** parsed into structured line
   items via an upstream parser (OCR + Claude API). The parser is OUT
   OF SCOPE for C17.
2. The **project reference BOQ** derived from C7 cost estimates + C16
   schedules + `RateProvider` rates.

C17 produces a **`QuoteComparisonReport`** — a structured artifact
containing per-line signal indicators, gap indicators, suspicious-
lump-sum indicators, a discussion-baseline reference, and itemization-
quality indicators. **No aggregate trust score.** No "credibility tier."

### 1.1 — What C17 IS

- A **structured-data emitter** producing comparison signals (same
  scope discipline as C16: no pixels, no PDF, no UI).
- An **advisory layer** producing language designed for the homeowner-
  contractor *conversation*, not for accusation or social posting.
- **Reference-anchored**: every signal traces back to `MaterialRate.is_code`
  + `MaterialRate.brand` + `MaterialRate.grade` from the `RateProvider`,
  with rate staleness and locality caveats surfaced on every output
  (R14 — NEW v0.2).
- **Transparency-Triple output** for every numeric: range + midpoint +
  derivation (per Design Principles v3.1 Principle 2).
- **Authority-restrained**: outputs are framed as "reference signals"
  not "verdicts."

### 1.2 — What C17 IS NOT (scope boundary)

| Concern | C17 emits | Consumer / other component handles |
|---|---|---|
| OCR / PDF parsing | structured `ParsedQuote` input — produced by **upstream parser** | upstream parser layer |
| Visual rendering | structured signal data + ordering | downstream consumer renderer |
| Aggregate trust/credibility score | NOTHING — explicitly excluded v0.2 | not a feature |
| Contractor rating system | NOTHING — explicitly excluded | not a contractor marketplace |
| Real-time supplier rates | static `RateProvider` rates with staleness markers | v2 vision |
| Negotiation broker | discussion-baseline reference, conversation starters | user-driven |
| Auto-dispatching reports to contractor | NOTHING — outputs for the homeowner only | user-driven |
| Definitive market truth | reference range with explicit uncertainty | reality (rates are volatile) |

### 1.3 — Scope test (Design Principles v3.1 § 2)

C17 closes the **Information asymmetry** between homeowner and
contractor. **The closure mechanism is shared transparency, not
adversarial verdict.**

---

## § 2 — Output contract

C17 emits a `QuoteComparisonReport`. All fields canonically ordered
for replay determinism. **Output ordering follows R15 (NEW): neutral
factual fields appear before signal indicators; severity-implying
fields are NEVER positioned for visual prominence.**

### 2.1 — Top-level `QuoteComparisonReport` (REVISED v0.2)

```
QuoteComparisonReport
├── source_quote_signature:        str (64-hex sha256 of parsed quote)
├── source_boq_signature:          str (64-hex sha256 of project BOQ)
├── c17_version:                   str ("v0.2.PROPOSED" at v0.2)
├── c17_schema_version:            int (2 at v0.2 — bump from v0.1's 1)
├── jurisdiction_profile_id:       str
├── declared_domain_scope:         str
├── rate_staleness_disclosure:     RateStalenessDisclosure  # NEW v0.2 (R14)
│
├── matched_lines:                 tuple[MatchedLine, ...]
│       lex-ASC sort by quote_line.line_id
│
├── missing_from_quote:            tuple[GapIndicator, ...]
│       (renamed from MissingItem v0.1 — "gap indicator" is neutral)
│       lex-ASC sort by boq_item.boq_id
│
├── unmatched_quote_lines:         tuple[UnmatchedQuoteLine, ...]
│       lex-ASC sort
│
├── lump_sum_indicators:           tuple[LumpSumIndicator, ...]
│       (renamed from SuspiciousLumpSum v0.1)
│
├── decomposition_acknowledgment:  DecompositionAcknowledgment  # NEW v0.2 (R18)
│       Recognizes that the contractor's BOQ structure may legitimately
│       differ from ours (turnkey bundles, labor/material splits, etc.)
│
├── total_comparison:              TotalComparison
│
├── discussion_baseline:           DiscussionBaseline  # RENAMED from CounterOffer
│
├── itemization_indicators:        ItemizationIndicators  # RESTRUCTURED v0.2
│       (replaces v0.1's ContractorCredibility — no aggregate score)
│
├── report_confidence:             ReportConfidence  # NEW v0.2 (R17)
│       Top-level "this report has X % of lines confidently matched;
│       Y % flagged for human review"
│
├── advisory_flags:                tuple[AdvisoryFlag, ...]
├── upstream_check_provenance:     tuple[CheckProvenance, ...]
├── canonical_replay_signature:    str
├── presentation_signature:        str
└── schema_descriptor_digest:      str
```

### 2.2 — `MatchedLine` (REVISED — adds HUMAN_VERIFICATION_RECOMMENDED tier)

```
MatchedLine
├── line_id:                       str
├── quote_label:                   str  # verbatim from contractor
├── matched_boq_id:                str
├── matched_boq_label:             str
├── match_confidence_tier:         Literal[
│       "high",                                # IS code OR brand+grade exact
│       "medium",                              # brand-only OR grade-only + unit
│       "low",                                 # name fuzzy + unit
│       "human_verification_recommended",      # NEW v0.2 (R-NEW from #6,#18)
│   ]
├── match_basis:                   tuple[Literal[...], ...]
│
├── quote_quantity:                AttestedValue (UPSTREAM_AUTHORITATIVE)
├── quote_unit:                    str
├── quote_rate:                    AttestedValue (UPSTREAM_AUTHORITATIVE)
├── quote_total:                   AttestedValue (UPSTREAM_AUTHORITATIVE)
│
├── our_quantity:                  AttestedValue (UPSTREAM_AUTHORITATIVE)
├── our_rate_median:               AttestedValue (UPSTREAM_AUTHORITATIVE)
├── our_rate_min:                  AttestedValue (UPSTREAM_AUTHORITATIVE)
├── our_rate_max:                  AttestedValue (UPSTREAM_AUTHORITATIVE)
├── our_total:                     AttestedValue (LOCALLY_DERIVED)
│
├── rate_delta_pct:                AttestedValue (LOCALLY_DERIVED)
├── total_delta:                   AttestedValue (LOCALLY_DERIVED)
│
├── signal:                        PriceSignal  # RENAMED from PriceVerdict
├── signal_explanation:            str         # advisory-tone reference language
└── provenance:                    CheckProvenance
```

### 2.3 — `PriceSignal` enum (RENAMED from PriceVerdict — accusation removed)

Per critique pt 7. Old → New mapping:

| v0.1 PriceVerdict | v0.2 PriceSignal | Rationale |
|---|---|---|
| `OVERPRICING` | `ABOVE_REFERENCE_RANGE` | Removes accusation; describes data position |
| `HIGH` | `ABOVE_TYPICAL` | Reference-anchored, not judgmental |
| `FAIR` | `WITHIN_TYPICAL` | Removes implicit moral framing |
| `UNDERPRICED` | `BELOW_TYPICAL_QUALITY_RISK` | Preserves concern signal without accusation |
| `MISSING_QTY` | `INSUFFICIENT_DATA` | Describes the data state, not blame |

**Thresholds unchanged from v0.1** (>20% / +5% to +20% / -5% to +5% / -20% to -5% / <-20%) but their EFFECT changes — see R5 below (`ABOVE_REFERENCE_RANGE` requires high-confidence match, otherwise downgrades to `ABOVE_TYPICAL`).

**Per R15 (NEW v0.2):** `signal` is NOT the first field of `MatchedLine`. Neutral factual fields (quote_label, quantities, rates) appear before. The signal is computed *from* facts; presenting it first inverts the logical order.

### 2.4 — `GapIndicator` (renamed + 4-way classification per critique pt 13)

```
GapIndicator    # v0.1 was "MissingItem"
├── boq_id:                        str
├── boq_label:                     str
├── expected_quantity:             AttestedValue
├── expected_unit:                 str
├── expected_total_low_high:       tuple[float, float]
├── interpretation:                Literal[
│       "likely_oversight",            # default — most generous
│       "possibly_omitted_intentionally",
│       "may_be_deferred_to_later_phase",
│       "insufficient_evidence_to_classify",
│   ]
│       Per critique #13: missing items are not always manipulation.
│       Default to "likely_oversight" — most generous interpretation.
│       Other tiers require positive evidence in the quote (e.g.,
│       "labor only" notation → "may_be_deferred_to_later_phase").
├── severity:                      Literal["critical", "important", "minor"]
└── advisory_note:                 str
        e.g. "Waterproofing for first-floor bathrooms isn't listed
              in the quote. It's worth confirming with the contractor
              whether this is included or will be charged separately."
              NEVER "missing from quote — contractor will charge later."
```

### 2.5 — `LumpSumIndicator` (renamed from SuspiciousLumpSum)

Same fields as v0.1's `SuspiciousLumpSum`, with two changes:
- `advisory_note` MUST follow advisory-tone template (R2)
- Reframed as "indicator" not "suspicious" — the lump sum may have a
  legitimate reason; the indicator flags it for the user to ask.

### 2.6 — `DecompositionAcknowledgment` (NEW v0.2 — critique pt 14)

```
DecompositionAcknowledgment
├── detected_decomposition_style:  Literal[
│       "line_itemized",         # matches our BOQ structure
│       "turnkey_bundles",       # contractor groups by package
│       "labor_material_split",  # separate labor and materials
│       "room_based",            # priced per room/area
│       "milestone_based",       # priced per construction stage
│       "hybrid",                # mixed
│       "unknown",
│   ]
├── alignment_quality_indicator:   Literal["high", "moderate", "low"]
│       NOT a verdict on the contractor. A signal about how well our
│       comparison can structurally engage with the quote.
└── advisory_note:                 str
        e.g. "Your contractor's quote uses turnkey bundles rather than
              line-item rates. This is a legitimate quoting style. Some
              of our line-by-line comparisons may not apply directly;
              we've focused on the bundle totals and key materials."
```

Per R18 (NEW): a different BOQ decomposition is **legitimate-but-different**, never a defect.

### 2.7 — `TotalComparison` (REVISED — reframed savings)

```
TotalComparison
├── quote_total:                   AttestedValue (UPSTREAM_AUTHORITATIVE)
├── our_estimate_total:            TransparencyTriple
├── delta_amount:                  AttestedValue (LOCALLY_DERIVED)
├── delta_pct:                     AttestedValue (LOCALLY_DERIVED)
├── headline_summary:              str
│       Reference-tone — describes the comparison, not the quote's worth.
│       e.g. "The quote is ₹13L higher than our reference estimate.
│              Our reference is one input among several to consider."
│       NOT: "Quote ₹71.5L vs our ₹58.5L — ₹13L higher".
├── potential_conversation_range:  tuple[float, float]   # RENAMED v0.2
│       (was potential_savings_low_high in v0.1)
│       Critique pt 8: never headline savings as an outcome.
│       Now framed as range to discuss, not realized savings.
└── conversation_range_disclaimer: str
        e.g. "This range is a reference for conversation, not a savings
              guarantee. Final cost depends on site conditions, scope
              changes, variation orders, material choices, and contractor
              terms. Rate references are from {kb_version}."
```

### 2.8 — `DiscussionBaseline` (RENAMED from CounterOffer — critique pt 5)

```
DiscussionBaseline    # v0.1 was "CounterOffer"
├── adjusted_total:                TransparencyTriple
│       our_estimate_total + reasonable_contractor_margin
├── reasonable_margin_pct:         AttestedValue
│       From RateProvider.contractor_margin_default_pct.
│       NEVER undercut. NEVER inflated.
├── conversation_language:         str   # RENAMED from negotiation_language
│       Advisory-tone template for the homeowner to use in their next
│       conversation with the contractor. NEVER confrontational.
│       e.g.: "Could you walk me through the basis for the {material}
│              line? Our reference range from {kb_source} is {low}–{high}
│              and your quote is at {quote_rate}. I'd appreciate
│              understanding the difference."
│       Per critique pt 5: this is about clarification, not minimization.
└── disclaimer:                    str
        "This baseline assumes typical Chennai rates as of {kb_version}.
         It is not a price target. The actual contract price depends on
         many factors specific to your project that we don't see."
```

### 2.9 — `ItemizationIndicators` (REPLACES ContractorCredibility — critique pt 2)

**The single biggest v0.2 change.** v0.1's `ContractorCredibility` had
`score: int (0-100)` + `tier: Literal["trustworthy", "reasonable",
"needs_scrutiny", "high_risk"]`. Both REMOVED.

What replaces them:

```
ItemizationIndicators
├── itemization_completeness_pct:  AttestedValue (LOCALLY_DERIVED)
│       (BOQ items mapped) / (total BOQ items) × 100
│       Pure data indicator. NO interpretation label attached.
├── lump_sum_count:                int
├── lump_sum_pct_of_total:         AttestedValue (LOCALLY_DERIVED)
├── critical_items_present:        tuple[str, ...]
│       Which critical items DO appear in the quote.
├── critical_items_gap:            tuple[str, ...]
│       Which critical items don't appear. Per § 2.4 GapIndicator
│       interpretation, default is "likely_oversight" not accusation.
├── margin_transparency:           Literal["shown_explicitly",
│                                         "embedded_in_rates",
│                                         "not_detectable",
│                                         "decomposition_does_not_apply"]
│       "decomposition_does_not_apply" for turnkey bundles where
│       margin discipline isn't the right frame.
├── rate_consistency:              Literal["consistent",
│                                         "mixed",
│                                         "highly_variable",
│                                         "insufficient_matches"]
└── advisory_note:                 str
        Per R13 (NEW): MUST explicitly state that these are
        **quote-formatting indicators**, NOT contractor competence
        indicators. Example mandatory clause:
        "These indicators reflect how the quote was written, not the
         quality of work the contractor will deliver. A well-itemized
         quote and a strong contractor are different things."
```

**No score. No tier. No "trustworthy" / "high_risk" labels.** The user
sees the underlying signals and decides for themselves. This mirrors
the C15 lesson: aggregation becomes authority.

### 2.10 — `ReportConfidence` (NEW v0.2 — critique pt 18)

```
ReportConfidence
├── total_quote_lines:                 int
├── high_confidence_matches:           int
├── medium_confidence_matches:         int
├── low_confidence_matches:            int
├── human_verification_recommended:    int    # NEW match tier (§ 2.2)
├── unmatched_quote_lines:             int
├── overall_report_tier:               Literal[
│       "high_signal",          # ≥75% high+medium confidence; report is useful
│       "moderate_signal",      # ≥50% high+medium
│       "high_ambiguity",       # <50% high+medium — report tier
│       "human_review_recommended",  # >25% human_verification_recommended tier
│   ]
└── advisory_note:                     str
        e.g. "This quote has many handwritten or informally-itemized
              lines. Our automatic comparison may not capture everything
              accurately. We'd recommend reviewing the comparison with
              someone you trust before drawing conclusions."
```

### 2.11 — `RateStalenessDisclosure` (NEW v0.2 — critique pt 4)

```
RateStalenessDisclosure
├── rate_provider_kb_version:      str   # e.g. "Chennai_2026_Q2_v1"
├── rate_provider_kb_date:         str   # ISO 8601
├── rate_provider_locality:        str   # "Chennai-wide" or future micro-market
├── micro_market_caveat:           str
│       "Rates may vary 5–15% between different parts of Chennai
│        depending on contractor ecosystem, supply chains, and
│        project access. Our reference is a Chennai-wide median."
├── market_volatility_caveat:      str
│       "Construction rates can shift 10–20% within a single quarter
│        based on monsoon timing, demand, and material supply.
│        These reference rates are anchored to {kb_date}."
└── recommended_review_cadence:    str
        e.g. "If this quote is more than 60 days old or your project
              extends past {date+90}, rates may have changed."
```

This is the structural answer to critique pt 4 (RateProvider as
centralized trust dependency). Every output carries staleness +
locality + volatility caveats. The downstream renderer is **required**
(R14) to surface these in every numeric display.

---

## § 3 — Phase pipeline (mostly unchanged from v0.1; small adjustments)

Same 6-phase α–ζ pattern. Updates in v0.2:

**Phase γ (Matching) — REVISED:**
- New fourth tier: `HUMAN_VERIFICATION_RECOMMENDED` when match confidence
  falls below the low-tier threshold but a candidate match exists.
- New first sub-step: detect overall quote decomposition style
  (§ 2.6 `DecompositionAcknowledgment`). If not `line_itemized`,
  some matching strategies fall back to bundle-level comparison.

**Phase δ (Verdicting) — REVISED:**
- `signal` enum renamed (per § 2.3).
- `ABOVE_REFERENCE_RANGE` requires `match_confidence_tier ∈ {high, medium}`;
  otherwise downgrades to `ABOVE_TYPICAL`. (R5 — same logic as v0.1's
  `OVERPRICING → HIGH` downgrade, with new names.)
- `HUMAN_VERIFICATION_RECOMMENDED` matches DO NOT produce a `signal` at
  all. Their `MatchedLine.signal` is `None`. They surface ONLY in
  `ReportConfidence.human_verification_recommended` count.

**Phase ε (Totals + DiscussionBaseline) — REVISED:**
- "Counter-offer" language replaced with "discussion baseline" (§ 2.8).
- "Savings" framing replaced with "conversation range" (§ 2.7).
- `RateStalenessDisclosure` populated from `RateProvider.kb_version`.

**Phase ζ (Indicators + bundle signing) — REVISED:**
- `ContractorCredibility` REMOVED.
- `ItemizationIndicators` produced (§ 2.9) — pure data, no aggregate.
- `ReportConfidence` computed (§ 2.10) — meta-indicator for the report
  itself, not for the contractor.
- Adversarial-evolution hooks (R-NEW per § 27 below) wired here.

---

## § 4 — Error tiers (unchanged from v0.1)

`LocalQuoteError` (always halts) + `PerQuoteLineError` (STRICT vs WARN).

---

## § 5 — Versioning

```python
C17_VERSION = "v0.2.PROPOSED"
C17_REPORT_SCHEMA_VERSION = 2     # MINOR bump per R9 (additive only)
C17_IDENTITY_GENERATION = 1

SUPPORTED_JURISDICTIONS = {"tn_cdbr_2019"}
SUPPORTED_DOMAIN_SCOPES = {"residential_v1"}

EXPECTED_C7_VERSION   = "v0.8.LOCKED"
EXPECTED_C16_VERSION  = "v0.5.LOCKED"

EPSILON_RATE_DELTA_PCT = 0.5
EPSILON_AMOUNT_RUPEES  = 100
```

Note: `c17_schema_version` bumps 1 → 2 because v0.2 ADDS fields
(`rate_staleness_disclosure`, `decomposition_acknowledgment`,
`report_confidence`) and RENAMES enum members (PriceVerdict →
PriceSignal). The rename is technically MAJOR per R9 strict reading,
but since v0.1 was PROPOSED (never LOCKED, never released), no
external consumer holds v0.1; treating the v0.1 → v0.2 transition as
MINOR is acceptable. **At v1.0 LOCK, the rename and field-removal
relative to v0.1 will be documented; no compatibility burden.**

---

## § 6 — Hard ceilings (unchanged from v0.1)

| Field | Hard ceiling |
|---|---|
| `ParsedQuote.line_items` length | 500 |
| `quote_total` | ₹50 crore |
| Single line item amount | ₹1 crore |
| `MaterialRate.rate` | ₹1 lakh per unit |
| Levenshtein threshold | 0.4 |
| Match-tier downgrade threshold | confidence < 0.5 → tier 3 |
| **NEW v0.2:** human-review threshold | confidence < 0.3 → tier 4 (`human_verification_recommended`) |

---

## § 7 — R-invariants (v0.2 set — 18 total)

R1–R12 from v0.1 carry forward unchanged except R2 wording sharpened.
R13–R18 are NEW v0.2 in response to critique walk.

| Invariant | Statement |
|---|---|
| **R1** | Every numeric output wrapped in `AttestedValue` per R22 inheritance from C16 |
| **R2** | Every `signal_explanation` + `advisory_note` + `conversation_language` string MUST pass advisory-tone lint against banned-phrase list. Banned list expanded v0.2: "overcharging", "fraud", "scam", "cheating", "ripping off", "do not pay", "refuse to pay", "must demand", "demand immediately", **"hidden charges", "trying to charge", "marked up", "padding the bill", "suspicious", "trustworthy", "untrustworthy", "credible", "not credible"** (last 6 added v0.2) |
| **R3** | `rate_delta_pct` and `total_delta` are LOCALLY_DERIVED; quote rates and our rates are UPSTREAM_AUTHORITATIVE — never blended |
| **R4** | Match confidence is **tiered** (high / medium / low / human_verification_recommended), never continuous (R39 inheritance) |
| **R5** | `ABOVE_REFERENCE_RANGE` signal requires `match_confidence_tier ∈ {high, medium}`. Low-confidence matches downgrade to `ABOVE_TYPICAL`. `human_verification_recommended` matches produce `signal = None` (no signal at all) |
| **R6** | `canonical_replay_signature` byte-equal on replay (R7 inheritance) |
| **R7** | `presentation_signature` has canonical as prefix (R32a inheritance) |
| **R8** | `QuoteComparisonReport` schema is public versioned API (R37 inheritance) |
| **R9** | `discussion_baseline.adjusted_total` MUST be derived as `our_estimate_total + reasonable_contractor_margin`. Never undercut. Never inflated beyond `RateProvider.contractor_margin_range_pct().high` |
| **R10** | Architectural primacy (R36 inheritance) — every comparison line MUST attach to a building element identifier from C16 OR structural element from C7 |
| **R11** | Determinism boundary (R35 inheritance) |
| **R12** | Semantic compression discipline (R39 inheritance) — every new field justified against information vs noise |
| **R13** (NEW) | **Itemization quality ⊥ contractor competence.** `ItemizationIndicators` MUST include the explicit clause: "These indicators reflect how the quote was written, not the quality of work the contractor will deliver." No code path emits an aggregate trust score. No tier label characterizes the contractor. |
| **R14** (NEW) | **Rate uncertainty is structurally surfaced.** Every `QuoteComparisonReport` MUST carry a populated `RateStalenessDisclosure` with non-empty `kb_version`, `kb_date`, `locality`, `micro_market_caveat`, `market_volatility_caveat`. The downstream consumer is contractually expected to surface these in every numeric display. |
| **R15** (NEW) | **Output ordering doesn't imply severity hierarchy.** Within every dataclass, neutral factual fields (labels, quantities, rates, sources) appear BEFORE derived signals (rate_delta_pct, signal). Within the top-level `QuoteComparisonReport`, the field order is: identity / provenance / matched_lines / gaps / unmatched / lump_sums / decomposition_ack / totals / discussion_baseline / indicators / report_confidence — signal-heavy fields are NOT first. |
| **R16** (NEW) | **Missing-item interpretation defaults to most-generous.** `GapIndicator.interpretation` defaults to `"likely_oversight"` unless positive evidence exists in the quote for another classification. C17 NEVER defaults to assuming hidden intent. |
| **R17** (NEW) | **Report-level human-review escape valve.** When `ReportConfidence.high_confidence_matches + medium_confidence_matches < 50%` of `total_quote_lines`, OR `human_verification_recommended ≥ 25%`, `ReportConfidence.overall_report_tier = "human_review_recommended"` AND the report's downstream display MUST surface this prominently. |
| **R18** (NEW) | **BOQ decomposition pluralism.** A contractor's quote that decomposes work differently than our BOQ is **legitimate-but-different**, never a defect. `DecompositionAcknowledgment` MUST be populated for every report. When `detected_decomposition_style != "line_itemized"`, signals are computed at the appropriate abstraction level (bundle-level if turnkey, room-level if room-based, etc.), and `ItemizationIndicators.margin_transparency` may correctly be `"decomposition_does_not_apply"`. |

### 7.1 — Advisory-tone template (R2 enforcement — v0.2 expanded)

**Allowed phrasings:**
- "This rate is above our reference range for {item} in Chennai 2026.
  Our reference is {low}–{high}/unit; the quote is at {quote_rate}/unit.
  Worth asking the contractor about the specification."
- "The {item} line in the quote doesn't appear to match a standard
  brand. It might be worth asking which brand and grade is being used."
- "{item} is typically included for this type of project. The quote
  doesn't mention it — worth confirming with the contractor whether
  it's included, will be charged separately, or is owner-supplied."
- "Could you walk me through how you've priced {bundle}? I'd like to
  understand what's included."

**Banned phrasings (R2 lint):**
- "overcharging", "ripping off", "fraud", "scam", "cheating"
- "do not pay", "refuse to pay", "demand immediately"
- "hidden charges", "trying to charge", "padding the bill"
- "suspicious", "trustworthy", "untrustworthy", "credible", "not credible"
- "warning", "alert", "danger" (visual-hierarchy words)
- Any phrase characterizing the contractor as a person/business

---

## § 8 — Upstream dependencies (unchanged from v0.1)

C7 v0.8 LOCKED, C16 v1.2 LOCKED, RateProvider, TransparencyTriple,
AttestedValue, AdvisoryFlag.

---

## § 9 — Backlog (v0.2 update)

### 9.1 — v1.0 LOCK-mandatory (5 items — unchanged from v0.1)

(see v0.1 § 9.1: phase implementations, test coverage parity,
ChennaiRateProvider v1, advisory-tone lint, fuzzy-match calibration.)

**v0.2 addition:** `B-C17-ADVISORY-TONE-LINT` now covers the expanded
banned-phrase list (R2 v0.2). Existing item, expanded scope.

### 9.2 — v0.1 deferred items (8 items — unchanged)

(parser integration, multi-city rates, contractor-response loop,
localization, etc.)

### 9.3 — NEW v0.2 backlog items (4 items, per Rule 9.2)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C17-NON-PRICE-DIMENSION-ACKNOWLEDGMENT` | Every report includes a default-emitted advisory note explicitly stating "price is one dimension of contractor evaluation, not the only one." Operationalizes critique pt 9 | v0.1 critique pt 9 | v1.0 LOCK | S |
| `B-C17-MICRO-MARKET-CALIBRATION` | Sub-Chennai rate variation (Velachery vs Chennai South vs outskirts). Requires rate-data collection per micro-market | v0.1 critique pt 11 | v1.x post-launch data | M |
| `B-C17-LEGAL-REVIEW-PROCESS` | Legal counsel reviews the spec + sample outputs BEFORE first user-facing release. Specifically: do the v0.2 reframings (PriceSignal, DiscussionBaseline, ItemizationIndicators, GapIndicator) survive Indian defamation / contract-tortious-interference law? | v0.1 critique pt 15 | Before first launch | M |
| `B-C17-HEURISTIC-ROTATION-DISCIPLINE` | Periodic rotation of internal heuristic thresholds + signals to prevent contractor cosmetic gaming (per critique pts 1, 10). Document which heuristics are public vs internal-only | v0.1 critiques pt 1, 10 | Quarterly post-launch | M |

### 9.4 — Summary

| Category | Count |
|---|---|
| LOCK-mandatory (v0.1 set + R2 expansion) | 5 |
| DEFERRED (v0.1 era) | 8 |
| NEW from v0.1 critique walk | 4 |
| **Total tracked** | **17** |

---

## § 10 — Test plan (v0.2 update)

Same ~210-test target as v0.1, with these additions:

| New test file / additions | Count | Purpose |
|---|---|---|
| `test_c17_advisory_tone_lint.py` | ~20 (was 10 in v0.1) | R2 enforcement — expanded banned-phrase list, including new "credible"/"trustworthy" etc. |
| `test_c17_human_review_tier.py` | ~10 (NEW) | R17 — report-level escape valve fires correctly |
| `test_c17_decomposition_acknowledgment.py` | ~10 (NEW) | R18 — different BOQ structures recognized as legitimate |
| `test_c17_gap_interpretation_defaults.py` | ~8 (NEW) | R16 — missing-item interpretation defaults to "likely_oversight" |
| `test_c17_rate_staleness_disclosure.py` | ~8 (NEW) | R14 — every report carries staleness + locality + volatility caveats |
| `test_c17_no_aggregate_score.py` | ~5 (NEW) | R13 — report has no `score`, no `tier` field on contractor; itemization indicators carry the explicit "not contractor competence" clause |

**New target: ~270 tests at v1.0 LOCK.**

---

## § 11 — Critique walk verdicts (v0.1 → v0.2 audit trail)

Per Rule 7: every critique point with verdict + disposition. The full
20 points from v0.1 critique walk:

| # | Theme | Verdict | Disposition in v0.2 |
|---|---|---|---|
| 1 | Contractors will adversarially optimize | **SPEC-AMENDMENT** | § 27 (NEW) adversarial-evolution discipline + `B-C17-HEURISTIC-ROTATION-DISCIPLINE` |
| 2 | Aggregate credibility score 0–100 dangerous | **SPEC-AMENDMENT — biggest single patch** | `ContractorCredibility` REMOVED entirely. Replaced with `ItemizationIndicators` (§ 2.9) — no score, no tier. R13 (NEW) enforces. |
| 3 | Corporate-style contractor bias | **SPEC-AMENDMENT** | R13 (NEW) — itemization quality ⊥ contractor competence. Mandatory explicit clause in every report. |
| 4 | RateProvider as centralized trust | **SPEC-AMENDMENT** | `RateStalenessDisclosure` (NEW § 2.11) + R14 (NEW) — every report carries staleness/locality/volatility caveats |
| 5 | Counter-offer as price-suppression | **SPEC-AMENDMENT** | `CounterOffer` → `DiscussionBaseline` rename (§ 2.8). "Negotiation language" → "conversation language." Math unchanged; framing fully reworked. |
| 6 | Matching more fragile than spec assumes | **SPEC-AMENDMENT** | NEW fourth tier `human_verification_recommended` in match_confidence_tier (§ 2.2). NEW threshold (confidence < 0.3) in § 6. |
| 7 | "OVERPRICING" accusatory terminology | **SPEC-AMENDMENT** | `PriceVerdict` → `PriceSignal` enum rename. All 5 values renamed (§ 2.3). |
| 8 | Savings estimates create false expectations | **SPEC-AMENDMENT** | `potential_savings_low_high` → `potential_conversation_range` (§ 2.7) + mandatory `conversation_range_disclaimer` |
| 9 | Commoditization of construction | **BACKLOG** | `B-C17-NON-PRICE-DIMENSION-ACKNOWLEDGMENT` filed § 9.3 |
| 10 | Quote gaming / cosmetic optimization | **SPEC-AMENDMENT (consolidates with #1)** | § 27 (NEW) + `B-C17-HEURISTIC-ROTATION-DISCIPLINE` |
| 11 | Jurisdictional variability finer than city | **BACKLOG** | `B-C17-MICRO-MARKET-CALIBRATION` filed § 9.3 |
| 12 | "Too authoritative" meta-risk | **SPEC-AMENDMENT (consolidates with #5, #7, #20)** | § 0.1 mission framing + signal/baseline renames |
| 13 | Missing items: not all = manipulation | **SPEC-AMENDMENT** | `MissingItem` → `GapIndicator` rename + 4-way interpretation classifier (§ 2.4) + R16 default-to-most-generous |
| 14 | BOQs not as canonical as spec assumes | **SPEC-AMENDMENT** | `DecompositionAcknowledgment` (NEW § 2.6) + R18 (NEW) |
| 15 | Legal exposure non-linear growth | **PROCESS-AMENDMENT + BACKLOG** | `B-C17-LEGAL-REVIEW-PROCESS` filed § 9.3; legal review now required before first launch |
| 16 | Advisory tone lint insufficient — visual semantics | **SPEC-AMENDMENT (partial)** | R15 (NEW) — output ordering doesn't imply severity hierarchy. Pixel-level visual semantics remain downstream per § 1.2. |
| 17 | Most viral / most misused feature | **SPEC-AMENDMENT** | Every numeric carries staleness + caveats (R14). Every emitted string designed assuming public sharing. § 0.1 mission framing. |
| 18 | No human-escalation strategy | **SPEC-AMENDMENT** | NEW `human_verification_recommended` match tier (§ 2.2) + `ReportConfidence.overall_report_tier="human_review_recommended"` (§ 2.10) + R17 (NEW) |
| 19 | Trust design > algorithms | **NO ACTION** | Captured implicitly via §§ 0.1, 2.3, 2.7, 2.8, 2.9 reframings |
| 20 | Consumer-vs-contractor adversarial framing | **SPEC-AMENDMENT — top-level** | § 0.1 mission framing (NEW) — "alignment and clarity," not "catching bad contractors" |

**Totals:** 12 SPEC-AMENDMENTs adopted + 4 backlog items filed + 4
consolidations + 0 misframed + 0 pushback.

### 11.1 — Honest meta-comment

This critique was **substantially right.** Unlike the C16 v1.0 and
v1.1 critique walks (where most points were deflected by § 18 scope
boundary), this critique surfaced genuine blind spots in v0.1 that the
C15 "Scorer → Problem Finder" lesson should have prevented. Specifically,
v0.1's `ContractorCredibility.score` field was the same mistake at
higher stakes (contractors are humans with reputations vs C15's layouts
which are not). v0.2 corrects this and structures the rest of the spec
around the mission framing the critique made explicit.

---

## § 27 — Adversarial evolution discipline (NEW v0.2)

Per critique pts 1, 10. Contractors will optimize against C17 once
users start uploading their quotes. v0.2 addresses this at three levels:

### 27.1 — Public vs internal heuristics

The following are SAFE to publish (and are documented in this spec):
- The 5 `PriceSignal` enum values + their threshold ranges
- The 4 `GapIndicator.interpretation` values
- The structure of `ItemizationIndicators`
- The 4 `match_confidence_tier` values

The following are INTERNAL and NOT published externally:
- Specific Levenshtein thresholds for fuzzy match
- Specific weighting of `ItemizationIndicators` components
- The `RateStalenessDisclosure` cadence rules
- Detection rules for `SuspiciousLumpSum` triggers
- Any rule that, if known, would let a contractor cosmetically optimize

**Operational rule:** when external documentation (marketing, blog,
public spec) describes C17, it describes the *categories* but never
the *thresholds*. This spec is internal.

### 27.2 — Heuristic rotation cadence

Per `B-C17-HEURISTIC-ROTATION-DISCIPLINE` (§ 9.3), internal thresholds
rotate quarterly post-launch. Rotation principles:
- Threshold rotation MUST preserve replay determinism for already-emitted
  reports. Old reports remain reproducible from their `c17_schema_version`
  + `rate_provider_kb_version`. Only NEW reports use new thresholds.
- Rotation amplitude is bounded: thresholds may shift ±20% per
  quarter, no more.
- Rotation is logged with version-pinned thresholds-table for audit.

### 27.3 — Cosmetic-vs-substantive itemization

Some contractors will start producing **cosmetically itemized** quotes
that satisfy `ItemizationIndicators.itemization_completeness_pct` but
hide manipulation in unit-rate weirdness. Detection patterns
(NOT in user-facing spec):
- High `itemization_completeness_pct` + high `rate_delta_pct` variance
  across matched lines → flag for human_verification_recommended
- "Suspicious itemization" — line items that look itemized but are
  artificially split (e.g., "RCC cement 50 bags @ ₹400" + "RCC labor
  for cement work 50 units @ ₹150" — the labor unit makes no sense)

Detection rules are internal-only per § 27.1.

### 27.4 — Adversarial evolution roadmap

v1.0 ships with the heuristics in this spec. v1.x quarters post-launch
each ship one of:
- Threshold recalibration (per § 27.2)
- New detection pattern for emerging cosmetic gaming
- Removal of a heuristic that's been gamed too thoroughly

This is `B-C17-HEURISTIC-ROTATION-DISCIPLINE`.

---

## § 28 — Three-check protocol (Rule 10.6) — at LOCK time

(To be filled at LOCK time per the C15 / C16 pattern.)

---

## § 29 — LOCK adjudication request (Rule 8)

**This document is C17 v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**

For Ramalingam to LOCK v0.2, please confirm:

1. **§ 0.1 mission framing** — C17 is "alignment and clarity," NOT
   "catching bad contractors." This sentence governs every other choice.
2. **§ 2.3 `PriceSignal` rename** — `OVERPRICING/HIGH/FAIR/UNDERPRICED/MISSING_QTY`
   → `ABOVE_REFERENCE_RANGE/ABOVE_TYPICAL/WITHIN_TYPICAL/BELOW_TYPICAL_QUALITY_RISK/INSUFFICIENT_DATA`.
3. **§ 2.9 `ItemizationIndicators`** — REPLACES `ContractorCredibility`.
   No aggregate score. No trust tier. Pure data + mandatory clause
   distinguishing quote quality from contractor competence (R13).
4. **§ 2.8 `DiscussionBaseline`** — RENAMED from `CounterOffer`.
   Conversation language, not negotiation language.
5. **§ 2.4 `GapIndicator`** — RENAMED from `MissingItem`. 4-way
   interpretation classifier defaulting to "likely_oversight" (R16).
6. **§ 2.6 `DecompositionAcknowledgment`** — NEW. Recognizes turnkey/
   labor-material/room-based quotes as legitimate-but-different (R18).
7. **§ 2.10 `ReportConfidence`** — NEW. Report-level "high_ambiguity" /
   "human_review_recommended" tiers (R17).
8. **§ 2.11 `RateStalenessDisclosure`** — NEW. Every report carries
   staleness + locality + volatility caveats (R14).
9. **§ 7 R13–R18** — 6 new invariants from critique walk.
10. **§ 27 adversarial-evolution discipline** — NEW. Public vs internal
    heuristic separation + quarterly rotation cadence.
11. **§ 11 critique-walk audit trail** — 20 verdicts recorded
    per Rule 7.
12. **§ 9.3 4 new backlog items** — non-price acknowledgment,
    micro-market calibration, legal review, heuristic rotation.

If yes to all: **state "C17 v0.2 LOCKED"** OR (more likely given the
size of the changes): **run another critique walk** before LOCK.

If corrections needed: state which sections need patches; I'll compose
v0.3 PROPOSED.

**Convergence note:** v0.1 → v0.2 was a substantial restructure (12
SPEC-AMENDMENTs). v0.2 → v0.3 (if a third critique walk surfaces new
ground) should be much smaller. v0.2 is the natural LOCK candidate
unless a third critique surfaces structural gaps.

---

**END OF C17 v0.2 PROPOSED — PENDING Ramalingam LOCK**
