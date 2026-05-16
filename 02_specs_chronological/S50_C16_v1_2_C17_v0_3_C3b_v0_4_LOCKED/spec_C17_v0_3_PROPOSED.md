# C17 — Quote Comparison Engine
## Spec v0.3 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor:** v0.2 PROPOSED (S50 mid).
**Composed from:** v0.2 PROPOSED + second critique walk findings (S50 late).
**Session:** S50.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone. This document
> is PROPOSED only.

> **Per Rule 9.4:** Critiques arriving between PROPOSED and LOCK remain
> patch-eligible.

---

## § 0 — Composition rationale (v0.3)

v0.2 was a major restructure (12 SPEC-AMENDMENTs from v0.1 critique).
The second critique walk on v0.2 yielded 17 numbered concerns; the
verdict tally is:

- **4 SPEC-AMENDMENTs** adopted in v0.3 (surgical, not restructural)
- **8 new BACKLOG items** filed per Rule 9.2
- **5 NO ACTION** (philosophical truths already acknowledged in v0.2, or
  unresolvable sociotechnical tensions that no spec patch resolves)

**The reviewer's own meta-warning** governs v0.3: *"v0.2 risk: complexity-
heavy overcorrection."* Patching every surfaced concern would worsen the
exact failure mode the critique identifies (governance accretion).
v0.3's discipline: **only patch what is genuinely actionable as a spec
change; file ongoing tensions as backlog for monitoring or future
work.** This is the standing precedent from C16 v1.1 → v1.2 (3 of 16
patched, 9 already-resolved) applied here.

**The 4 v0.3 patches:**

1. **R15 narrowed** (§ 7 patch) — from "field ordering controls perception"
   to "C17 designates no headline field; visual hierarchy is downstream"
2. **§ 1.4 applicability boundary** (NEW) — C17 v1.0 targets formalized
   urban residential; informal/mason-led/family-network builds are
   explicitly out of scope
3. **§ 26 bundle-level scope limitation** (NEW) — R18 (decomposition
   pluralism) is philosophically correct but bundle-level comparison
   in v1.0 is best-effort, not authoritative; specific weaknesses
   documented
4. **§ 27.5 explainability discipline** (NEW) + small **§ 27.2 sharpening**
   — what is intentionally opaque, what is not, plus user-facing
   consistency-drift acknowledgment

**No new R-invariants in v0.3.** R1–R18 stand. R15 is narrowed but
remains R15 (same number).

**Convergence signal:** v0.1 critique → 12 patches. v0.2 critique → 4
patches. Delta is shrinking. v0.3 is positioned as the LOCK candidate.

---

## § 1 — Scope

### 1.1 — 1.3 — Carried forward unchanged from v0.2

All of v0.2 § 1.1 (What C17 IS), § 1.2 (What C17 IS NOT — the scope
boundary table), and § 1.3 (Scope test) carry forward unchanged.

### 1.4 — Applicability boundary (NEW v0.3)

Per critique pt 6: v0.2 implicitly assumed construction work can be
normalized into structured comparative reference models. Many real
Indian construction relationships do not work that way. v0.3 makes
this explicit.

**C17 v1.0 is designed for:**

- Urban or peri-urban residential builds in the cities `RateProvider`
  supports (v1.0: Chennai, with `tn_cdbr_2019` jurisdiction)
- Formalized contractor relationships where the contractor produces
  a written quote in line-item, turnkey-bundle, labor-material-split,
  room-based, or milestone-based form (per § 2.6 `DecompositionAcknowledgment`)
- Brief-driven projects (homeowner has at least loose specifications;
  C7 + C16 outputs exist as reference BOQ)

**C17 v1.0 is NOT designed for (and may produce misleading results):**

- **Labor-exchange and trusted-family-contractor models** where pricing
  is relational rather than rate-based
- **Phased informal additions** where the "quote" is verbal scope
  evolving with the build
- **Mason-led builds** where the labor lead also sources material on
  rolling basis with no upfront quote
- **Material-owner split arrangements** where the homeowner buys all
  material and pays only labor (the comparative BOQ structure doesn't apply)
- **Community/caste-network builds** where pricing is embedded in
  social trust networks and benchmarking against city-wide rates
  misframes the relationship
- **Sub-residential commercial / industrial work** (out of `declared_domain_scope`)

**When C17 detects (heuristically) that the uploaded quote falls into
one of the above patterns** (signals: zero brand specifications, zero
unit rates, scope-as-prose, very high lump-sum percentage with no
itemization, etc.), the report MUST surface this as part of
`ReportConfidence.overall_report_tier = "human_review_recommended"`
(R17 from v0.2) — AND the `report_confidence.advisory_note` MUST
explicitly state: *"This quote appears to come from a relationship
or arrangement that our comparative analysis isn't well-suited to.
The signals below may not reflect your situation accurately."*

**Implementation:** v1.0 ships heuristic detection only. Full
applicability-aware handling is `B-C17-INFORMAL-CONSTRUCTION-EXPANSION`
(§ 9.5).

---

## §§ 2 – 6 — Carried forward unchanged from v0.2

All of v0.2 § 2 (output contract, including new fields
`RateStalenessDisclosure`, `DecompositionAcknowledgment`,
`ReportConfidence`, `ItemizationIndicators`), § 3 (phase pipeline),
§ 4 (error tiers), § 5 (versioning), and § 6 (hard ceilings) carry
forward unchanged into v0.3.

**One small versioning note:** `C17_REPORT_SCHEMA_VERSION` stays at `2`
(same as v0.2). v0.3's changes are documentation-level (§ 1.4 added,
§ 7 R15 narrowed, § 26 added, § 27.5 added) — they do NOT modify the
dataclass schema, so no schema-version bump is required.

```python
C17_VERSION = "v0.3.PROPOSED"
C17_REPORT_SCHEMA_VERSION = 2     # UNCHANGED from v0.2
C17_IDENTITY_GENERATION = 1
```

---

## § 7 — R-invariants (R15 NARROWED — v0.3 patch)

R1–R18 from v0.2 carry forward. **R15 is narrowed** per critique pt 3.

### 7.1 — R15 (NARROWED in v0.3)

**v0.2 wording (was):**

> R15 — Output ordering doesn't imply severity hierarchy. Within every
> dataclass, neutral factual fields (labels, quantities, rates, sources)
> appear BEFORE derived signals (rate_delta_pct, signal). Within the
> top-level QuoteComparisonReport, the field order is: identity /
> provenance / matched_lines / gaps / unmatched / lump_sums /
> decomposition_ack / totals / discussion_baseline / indicators /
> report_confidence — signal-heavy fields are NOT first.

**v0.3 wording (is):**

> **R15 (NARROWED v0.3)** — **C17 designates no "headline" or "primary"
> field.** From C17's perspective, every field in `QuoteComparisonReport`
> is equal-weight; no field is marked, flagged, or annotated as the
> one a downstream renderer should prominently surface. Visual
> hierarchy is a downstream concern (per § 1.2 scope boundary).
>
> **What C17 still controls:**
> - Field ordering for canonical_replay_signature determinism (R6) —
>   dataclass field order must be stable for replay
> - No emission of `is_headline: bool` or `prominence: int` or similar
>   metadata that asserts visual primacy
> - No annotation in field names suggesting prominence (e.g. naming a
>   field `top_concern` is prohibited)
>
> **What C17 does NOT control:**
> - The order in which a downstream renderer chooses to display fields
> - Whether the renderer chooses to render `matched_lines` before or
>   after `discussion_baseline`
> - Visual prominence (color, size, positioning) of any rendered field
>
> The "neutral fields before signal fields" prescription from v0.2 is
> removed. Determinism-driven ordering remains. Prominence-implying
> metadata remains prohibited.

**Rationale (critique pt 3):** v0.2's R15 prescribed dataclass field
ordering to shape emotional perception — drifting into UX-governance
territory. C17 is a structured-data emitter; the consumer renderer
controls user-perceived ordering. R15's defensible core is
**structural neutrality** (no headline metadata, no prominence
annotation), not field-order psychology. The patch keeps the
defensible core and removes the overreach.

### 7.2 — R1–R14 and R16–R18 — unchanged

All other R-invariants from v0.2 § 7 carry forward unchanged. The
v0.2 § 7.1 banned-phrase template carries forward unchanged.

---

## § 8 — Upstream dependencies — unchanged from v0.2

---

## § 9 — Backlog

### 9.1 — v1.0 LOCK-mandatory — unchanged from v0.2 (5 items)

### 9.2 — DEFERRED from v0.1 era — unchanged (8 items)

### 9.3 — DEFERRED from v0.1 critique walk — unchanged (4 items)

### 9.4 — DEFERRED from v0.2 critique walk (NEW — 8 items)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C17-GOVERNANCE-LAYERED-DOCS` | Eventually split C17 spec into layered documents: (a) core engine invariants, (b) governance overlays, (c) legal/UX policies, (d) operational heuristics. Spec is becoming governance-dense (critique pts 2, 15) — layering it preserves readability without losing rigor | v0.2 critique pts 2, 15 | When v1.x feature work begins | M |
| `B-C17-GRADUATED-DISCLOSURE-V1X` | Downstream renderer should implement graduated disclosure (summary → detail on demand) to mitigate signal-proliferation cognitive load. v0.2 has many indicators (match confidence, decomposition, gaps, itemization, rate caveats, report confidence) — flat presentation overwhelms | v0.2 critique pt 4 | v1.x renderer work | M |
| `B-C17-TIER-DISTRIBUTION-MONITORING` | Post-launch metric: track what % of real-world quotes land in each `match_confidence_tier` and each `overall_report_tier`. If `human_verification_recommended` exceeds threshold (e.g. 40%), the system is producing too many ambiguous results and applicability heuristics need recalibration | v0.2 critique pt 5 | Post-launch monitoring | S (setup) / M (ongoing) |
| `B-C17-FALSE-NEGATIVE-MONITORING` | Post-launch metric: track cases where `GapIndicator.interpretation = "likely_oversight"` (R16 most-generous default) and the omission later turned out to be intentional exploitation. Calibrate R16's default if false-negative rate is high | v0.2 critique pt 9 | Post-launch monitoring | M |
| `B-C17-DISPUTE-APPEAL-PATHWAY` | Define dispute philosophy: what happens when (a) contractor disputes a `GapIndicator`, (b) homeowner believes the report under-warned, (c) `RateProvider` rate turns out wrong, (d) `DecompositionAcknowledgment` mismatched. Currently no formal appeal/correction path exists | v0.2 critique pt 13 | Before v1.0 launch (procedural) or v1.x (architectural) | M |
| `B-C17-BEHAVIORAL-CAVEAT-PRESENTATION` | Research-track: textual caveats (R14 staleness disclosure) may be ignored when decisive numbers are visible. Downstream renderer + UX research should determine how to surface uncertainty so users actually internalize it, not just see it | v0.2 critique pt 12 | v1.x UX research | L |
| `B-C17-USER-FACING-CONSISTENCY-LOG` | When § 27.2 quarterly heuristic rotation changes thresholds, two near-identical quotes evaluated 3 months apart may receive different signals. v1.x: maintain a queryable rotation-log so users can answer "why did the same quote get different results last quarter?" — preserves replay determinism PLUS user-facing consistency explanation | v0.2 critique pt 14 | Per quarterly rotation | S (per rotation) |
| `B-C17-INFORMAL-CONSTRUCTION-EXPANSION` | Long-term: extend C17 to handle labor-exchange, trusted-family, mason-led, material-owner-split, community-network construction models. Per § 1.4, v1.0 explicitly does NOT serve these — v2 or v3 work | v0.2 critique pt 6 | Long-term v2+ vision | XL |

### 9.5 — Summary

| Category | Count |
|---|---|
| LOCK-mandatory (v0.1 set) | 5 |
| DEFERRED from v0.1 era | 8 |
| DEFERRED from v0.1 critique walk | 4 |
| DEFERRED from v0.2 critique walk (NEW v0.3) | 8 |
| **Total tracked** | **25** |

---

## § 10 — Test plan — small additions

v0.2's ~270-test target stands. v0.3 adds two small test files for the
new spec sections:

| New test file | Count | Purpose |
|---|---|---|
| `test_c17_applicability_boundary.py` | ~8 (NEW v0.3) | § 1.4 — heuristic detection of informal-construction-pattern quotes fires `human_review_recommended` and produces the explicit advisory note |
| `test_c17_r15_narrowed.py` | ~5 (NEW v0.3) | R15 narrowing — `QuoteComparisonReport` emits no field named `headline`, `prominent`, `top_concern`, `primary_signal`, etc.; no `is_headline: bool` or `prominence: int` field on any nested type |

**Plus existing `test_c17_no_aggregate_score.py` (v0.2) is extended** by
~3 tests to verify the R15 narrowing — no metadata field asserts visual
primacy. (Same file, additional cases.)

**Revised v1.0 LOCK test target: ~285 tests.**

---

## § 11 — v0.1 critique walk verdicts — unchanged from v0.2 § 11

---

## § 12 — v0.2 critique walk verdicts (NEW — audit trail per Rule 7)

The 17 numbered points from the v0.2 critique walk:

| # | Theme | Verdict | Disposition in v0.3 |
|---|---|---|---|
| 1 | Users still interpret signals as judgment | **NO ACTION — philosophical truth** | v0.2 § 0.1 + § 11.1 already acknowledge wording is mitigation, not resolution. Captured. |
| 2 | System becoming governance-heavy | **BACKLOG** | `B-C17-GOVERNANCE-LAYERED-DOCS` filed § 9.4. Patching governance bloat by adding more spec sections would worsen the problem; correct response is filed-for-future-reorganization, not v0.3 patch. |
| **3** | R15 over-fitting to psychological micro-control | **SPEC-AMENDMENT (the genuine pushback)** | **§ 7.1 R15 narrowed** — from "field ordering controls perception" to "no headline metadata; visual hierarchy is downstream" |
| 4 | Decision fatigue from signal proliferation | **BACKLOG** | `B-C17-GRADUATED-DISCLOSURE-V1X` filed § 9.4 — downstream UX concern |
| 5 | `human_verification_recommended` silent failure mode | **BACKLOG** | `B-C17-TIER-DISTRIBUTION-MONITORING` filed § 9.4 — post-launch metric |
| **6** | Underestimates informal construction economies | **SPEC-AMENDMENT** | **§ 1.4 applicability boundary** (NEW) — explicit out-of-scope statement + heuristic surfacing in `ReportConfidence` |
| 7 | Advisory lint is one layer, not full safety | **NO ACTION** | v0.2 R14 + R15 (now narrowed) + § 1.2 already acknowledge — no new claim that lint is sufficient |
| **8** | Internal vs public heuristic transparency tension | **SPEC-AMENDMENT (small)** | **§ 27.5 explainability discipline** (NEW) — what is intentionally opaque, what is not |
| 9 | "Most generous interpretation" may under-warn | **BACKLOG** | `B-C17-FALSE-NEGATIVE-MONITORING` filed § 9.4 — post-launch metric, calibrate R16 if needed |
| **10** | Decomposition pluralism computationally hard | **SPEC-AMENDMENT (small)** | **§ 26 bundle-level scope limitation** (NEW) — R18 stays philosophically right, but v1.0 is best-effort, not authoritative |
| 11 | Reference convergence pressure | **NO ACTION — unresolvable** | Sociotechnical truth; no spec patch helps. Captured for awareness. |
| 12 | Rate staleness disclosures as "legal decoration" | **BACKLOG** | `B-C17-BEHAVIORAL-CAVEAT-PRESENTATION` filed § 9.4 — downstream + UX research |
| 13 | No appeal / dispute model | **BACKLOG** | `B-C17-DISPUTE-APPEAL-PATHWAY` filed § 9.4 — procedural before launch / architectural in v1.x |
| **14** | Quarterly heuristic rotation creates consistency drift | **SPEC-AMENDMENT (small) + BACKLOG** | **§ 27.2 sharpened** — user-facing consistency note added. `B-C17-USER-FACING-CONSISTENCY-LOG` filed § 9.4. |
| 15 | Engineering + UX + legal + ethics blending | **BACKLOG (consolidates with #2)** | Same `B-C17-GOVERNANCE-LAYERED-DOCS` |
| 16 | Product may become "fairness app" socially | **NO ACTION — unresolvable** | Narrative compression is inevitable; § 0.1 already accepts as ongoing tension |
| 17 | v0.2's biggest success: limitations acknowledgment | **PRAISE — no action** | Noted as positive convergence signal |

**Totals:** 4 SPEC-AMENDMENTs + 8 backlog items + 5 NO ACTION = 17 of 17
verdicted.

### 12.1 — Honest meta-comment

This was the most measured critique in the C17 trajectory. v0.1's
critique surfaced 12 structural defects. v0.2's critique surfaced
ongoing sociotechnical *tensions* — not defects. The reviewer
explicitly cautioned: *"v0.2 risk: complexity-heavy overcorrection."*

The discipline in v0.3 was to **honor that caution**: patch only
what is genuinely a spec-actionable change (4 items), file the rest
as backlog (8 items), and resist the temptation to add R19–R24 or
new spec sections for every observed tension. **Architectural
restraint is itself a v0.3 design choice.**

The delta (v0.1 → 12 patches → v0.2 → 4 patches → v0.3) signals
convergence. v0.3 is positioned as the natural LOCK candidate.

---

## § 26 — Bundle-level comparison scope limitation (NEW v0.3)

Per critique pt 10. R18 (BOQ decomposition pluralism, from v0.2 § 7)
states that a contractor's non-line-itemized quote is
**legitimate-but-different**, never a defect. This is philosophically
correct. v0.3 adds operational honesty about what C17 v1.0 can and
cannot do for non-line-itemized quotes.

### 26.1 — Line-item comparison (v1.0: full support)

For quotes where `DecompositionAcknowledgment.detected_decomposition_style
== "line_itemized"` AND `alignment_quality_indicator == "high"`,
C17 v1.0 produces full-quality `MatchedLine[]` output with all signals
(`PriceSignal`, `signal_explanation`, deltas).

### 26.2 — Bundle-level comparison (v1.0: best-effort, NOT authoritative)

For quotes where `detected_decomposition_style != "line_itemized"`
(turnkey_bundles, labor_material_split, room_based, milestone_based,
hybrid), C17 v1.0 produces **best-effort comparison only**, with
the following honest limitations:

- A turnkey package typically includes labor + material + transport +
  supervision + wastage + equipment + subcontracting + contingency.
  Decomposing this against a line-item BOQ requires either (a) the
  contractor's internal cost split, which we don't have, or (b) our
  modeled split, which is heuristic.
- `our_total` for the bundle is reconstructed from C7 + C16 + finish
  rates, but the matching to a single bundled quote line necessarily
  loses internal-cost-allocation information.
- `rate_delta_pct` at the bundle level is meaningful only at coarse
  granularity (typically ±15% threshold instead of ±5/20%); v1.0
  applies a `bundle_threshold_inflation_factor` of 3.0× to all
  thresholds when comparing bundle lines.
- Per-line `PriceSignal` enums for bundle lines MUST be downgraded
  one tier compared to line-item analysis (e.g., a +25% bundle delta
  produces `ABOVE_TYPICAL`, not `ABOVE_REFERENCE_RANGE` — because
  bundle-internal cost variance accounts for typical ±15% spread).
- `ReportConfidence.overall_report_tier` is at most `"moderate_signal"`
  for any quote where bundle-level analysis dominates (≥50% of total
  ₹ value comes from bundle lines), regardless of how cleanly the
  bundles match.

### 26.3 — When bundle-level analysis cannot proceed

If `detected_decomposition_style == "hybrid"` AND bundle structures
are not consistently identifiable, `ReportConfidence.overall_report_tier
= "human_review_recommended"` with the explicit advisory note:

> *"Your contractor's quote mixes multiple pricing styles in a way
> our automated comparison can't reliably structure. The report below
> is partial. We'd recommend discussing specific line items with the
> contractor and using our reference rates as conversation anchors
> rather than as a comparison verdict."*

### 26.4 — v1.x trajectory

`B-C17-INFORMAL-CONSTRUCTION-EXPANSION` (§ 9.4) covers extending C17
to model bundle-internal cost allocation more accurately (e.g., by
maintaining a `BundleCompositionModel` that knows typical Chennai
turnkey decompositions). v1.0 ships with the limitation explicit.

**Rationale:** Don't overpromise. R18 stays as a philosophical
invariant; v1.0's operational reality is honestly bounded.

---

## § 27 — Adversarial evolution discipline (v0.2 § 27 + v0.3 patches)

§§ 27.1 (public vs internal heuristics), 27.3 (cosmetic-vs-substantive
itemization), and 27.4 (adversarial evolution roadmap) carry forward
unchanged from v0.2.

### 27.2 — Heuristic rotation cadence (SHARPENED v0.3)

v0.2 wording carried forward, **with this addition** per critique pt 14:

> **User-facing consistency acknowledgment.** Two near-identical quotes
> uploaded to C17 three months apart may receive different
> `PriceSignal` values for individual lines, because `RateProvider.
> kb_version` advanced and internal thresholds rotated per § 27.4.
>
> **What is preserved:**
> - **Replay determinism** for each emitted report — given the same
>   `c17_schema_version` + `rate_provider_kb_version` + threshold-table
>   version, the report reproduces byte-equal (R6, R11).
> - **Auditability** — `RateStalenessDisclosure.rate_provider_kb_version`
>   and `rate_provider_kb_date` are stamped on every report.
>
> **What is NOT preserved:**
> - User-facing interpretive consistency across rotations. The same
>   quote evaluated against `Chennai_2026_Q2_v1` rates vs
>   `Chennai_2026_Q4_v1` rates may produce different signal verdicts
>   on the same line because the reference rate changed.
>
> **v0.3 commitment:** This drift IS structurally honest — the world
> changed, the reference changed, the comparison changed. v1.x ships
> `B-C17-USER-FACING-CONSISTENCY-LOG` (§ 9.4) so users can query
> "what changed between rotations" when running the same quote
> against different `kb_version`s.

### 27.5 — Explainability discipline (NEW v0.3)

Per critique pt 8. § 27.1 introduced public-vs-internal heuristic
separation, but did not resolve the explainability tension this creates.
v0.3 makes the policy explicit.

**What C17 publicly explains (to homeowners using the report):**

- The categories of every signal: `PriceSignal` enum values + meaning,
  `match_confidence_tier` values + meaning, `GapIndicator.interpretation`
  values + meaning
- The rate-data source: `RateStalenessDisclosure` always carries
  `kb_version`, `kb_date`, `locality`, `micro_market_caveat`,
  `market_volatility_caveat`
- Per-line provenance: `MatchedLine.provenance` traces back to the
  upstream source (which BOQ line, which rate, which version)
- The structural distinction between quote quality and contractor
  competence (R13 mandatory clause)

**What C17 does NOT publicly explain:**

- Specific numerical thresholds for `PriceSignal` enum boundaries
  (the ±5/±20% from v0.1 § 2.3 stays internal — rotates per § 27.2)
- Specific Levenshtein thresholds for fuzzy match tiers
- Specific weighting of `ItemizationIndicators` components
- Internal heuristic-rotation table version
- Detection patterns for cosmetic itemization

**Why this opacity exists (must be defensible if asked):**

- If thresholds were public, contractors would quote at threshold-1
  to evade signals — `B-C17-HEURISTIC-ROTATION-DISCIPLINE` is the
  active defense
- Internal weighting protects against cosmetic gaming
- Detection patterns are anti-adversarial; publishing them defeats
  their purpose

**User-facing policy statement** (default text C17 emits in the report's
`upstream_check_provenance` block):

> *"This report uses reference rates and comparison rules calibrated
> for Chennai 2026. Some specific numerical thresholds are not
> published to keep the comparison reliable against contractors who
> might otherwise optimize against published thresholds. You can see
> what category each signal falls into and what data drove it, but
> the exact numerical cutoffs are not surfaced. If you'd like to
> discuss a specific signal, our support pathway can walk you through
> it case-by-case." (per `B-C17-DISPUTE-APPEAL-PATHWAY`)*

**Note on regulator concerns:** If Indian regulators eventually require
algorithmic transparency for consumer-facing comparison tools, this
policy may need revision. v1.0 ships with this stance; legal review
per `B-C17-LEGAL-REVIEW-PROCESS` includes regulator-facing transparency
positioning.

---

## § 28 — Three-check protocol (Rule 10.6) — at LOCK time

(To be filled at LOCK time per the C15 / C16 pattern.)

---

## § 29 — Convergence assessment

A measured spec sequence converges when each round produces fewer
genuine patches than the previous one. The C17 trajectory:

| Round | Patches | Backlog filed | Note |
|---|---|---|---|
| v0.1 critique | 12 SPEC-AMENDMENTs | 4 | Major restructure (removed credibility score, renamed enums, new mission framing) |
| v0.2 critique | **4 SPEC-AMENDMENTs** | 8 | Surgical refinements (R15 narrowing, applicability, bundle scope, explainability) |
| v0.3 critique (if any) | predicted ≤ 2 | ≤ 5 | Convergence floor |

The v0.2 → v0.3 delta is **a third the size of the v0.1 → v0.2 delta**.
This is the convergence signal a spec should produce before LOCK.

**A v0.4 round is warranted only if a third critique surfaces a
genuinely actionable spec change** (not just additional tensions —
v0.2's critique already established that ongoing tensions are not
patches). Otherwise v0.3 should LOCK.

---

## § 30 — LOCK adjudication request (Rule 8)

**This document is C17 v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication.**

For Ramalingam to LOCK v0.3, please confirm:

1. **§ 1.4 applicability boundary** — explicit out-of-scope statement
   for informal/mason-led/family-network/labor-exchange builds. v1.0
   targets formalized urban residential.
2. **§ 7.1 R15 narrowing** — from field-ordering prescription to
   "no headline metadata; visual hierarchy is downstream." Accepts
   the genuine pushback from critique pt 3.
3. **§ 26 bundle-level scope limitation** — R18 stays philosophically
   correct; v1.0 is best-effort for non-line-itemized quotes with
   honest limitations enumerated (threshold inflation 3×, tier
   downgrades, max `"moderate_signal"` report tier).
4. **§ 27.2 sharpening** — user-facing consistency drift across
   rotations is structurally honest, paired with backlog
   `B-C17-USER-FACING-CONSISTENCY-LOG`.
5. **§ 27.5 explainability discipline** — public-vs-internal opacity
   policy is now explicit, with default user-facing text.
6. **§ 9.4 (8 new backlog items)** — all filed.
7. **§ 12 critique-walk verdicts** — 17 of 17 verdicted; audit trail
   complete.

If yes to all: **state "C17 v0.3 LOCKED"** and code implementation
begins per § 9.1 LOCK-mandatory backlog.

If corrections needed: state which sections need patches; I'll
compose v0.4 PROPOSED.

**Recommendation:** v0.3 should LOCK. The v0.2 critique was largely
endorsement-with-tensions-surfaced rather than fix-this. The 4 v0.3
patches absorb the actionable items; the 8 backlog items capture the
monitoring/future-work tensions. Further critique rounds will yield
diminishing returns. Each round of unbounded patching risks the exact
governance-accretion failure mode the v0.2 critique itself warned
against.

---

**END OF C17 v0.3 PROPOSED — PENDING Ramalingam LOCK**
