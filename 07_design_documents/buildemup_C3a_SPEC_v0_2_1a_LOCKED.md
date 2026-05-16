# Component 3a — Extreme Case Gate (v0.2.1a Specification — LOCKED)

**Status:** LOCKED 29 April 2026. Ready for build start. Patched 30 April 2026 (v0.2.1a — five documentation corrections from S2 build, no behavioral change).
**Target version:** Component 3a v0.1 (first build)
**Architecture position:** Layer 1 (Understanding), runs after Component 2 (Feasibility), before Layer 2 (Generation)
**Companion component:** Component 3b (Post-Layout Trade-off Negotiation) — built later, after layout pipeline exists
**Component contract version:** 0.7.1 (existing infrastructure)
**Master document decision IDs:** D-047 (Component 3 split), D-048 (10 ECs locked), D-049 (Preview Mode added), D-050 (8 v0.2.1 refinements)

---

## Changelog

- **v0.1** (29 Apr 2026, morning) — initial draft, 10 ECs identified, 5 open questions
- **v0.1a** (29 Apr 2026, midday) — Q1 resolved via 15-source web research: EC-008 threshold locked at × 1.5
- **v0.2 LOCKED** (29 Apr 2026, evening) — incorporated 8 critique fixes from external review (#1-#10), Q1-Q5 resolutions, Reactions 1-2, Preview Mode added
- **v0.2.1 LOCKED** (29 Apr 2026, late evening) — second critique round (8 production-readiness issues) addressed:
  - **#1 CRITICAL Preview Mode misuse risk** — mandatory checkbox + room-overlay watermarks + dimension ranges + no construction details
  - **#2 Multi-constraint awareness** — preflight summary screen before first EC modal
  - **#3 Cost confidence stronger usage** — keep exact numbers but add aggressive caveat language + ±% range when LOW confidence
  - **#4 "Different plot" early signaling** — non-blocking hint when severe single-EC fires (EC-006 severe / EC-010 LOW / EC-002 physical)
  - **#5 Counterfactuals framing + max 2 alternatives** (Preview Mode stays in counterfactuals, neutrally formatted)
  - **#6 CBA verification 24h fallback** — "continue assuming NOT CBA" with new /cba-fallback-continue endpoint
  - **#7 Reason-aware BriefChange errors** — surface specific validation reason to user, not generic failure
  - **#8 Transition banner simplification** — trigger on case_id change (not category change), simpler logic, matches user's mental model
- **v0.2.1a** (30 Apr 2026, S2 build session) — five documentation corrections, **no behavioral change**:
  - Section 2.2 EC-003 detection wording: replaced `parking_feasibility.status == HARD_NO` with the actual CheckResult-driven detection (C2's `parking_width_feasibility` blocking issue).
  - Section 2.2 EC-006: added explicit dedup note that EC-006 fires only when `user_stated_setbacks` differ from `nbc_compliant_setbacks`.
  - Section 2.2 EC-008: added code-level note clarifying `c7_cost_estimate.midpoint` = `cost_estimate.exact_value` and `brief.budget.target` = `BudgetRange.max_rupees`.
  - Section 3.2: corrected "13 types (5 enums + 8 dataclasses)" → "15 types (5 enums + 10 dataclasses)".
  - Section 13.S1: corrected the type count for the same reason.

---

## 0. Document purpose

This is the **LOCKED** v0.2 spec for **Component 3a — Extreme Case Gate**. Build sessions begin from this document. Any changes during build go to a `v0.2-backlog` and are triaged separately — they do NOT modify this spec mid-build (Pattern E discipline).

The user (Ramalingam, 29 April 2026) clarified Component 3 has two separable jobs:

- **Component 3a** (this spec) — Extreme Case Gate. Pre-layout. Surfaces fundamental brief-level blockers as decisive "you must change X" moments. Small scope. Builds before layout pipeline.
- **Component 3b** — Post-Layout Trade-off Negotiation. Post-layout. Surfaces specific tweaks once user has seen layouts. Bigger scope. Builds after layout pipeline.

This spec follows the C1 v0.2 LOCKED template that worked.

---

## 1. Purpose & success criteria

### 1.1 What Component 3a does

When `Component 2 (Feasibility)` produces a `DesignGapAnalysis` with one or more blocking gaps that fall into the locked Extreme Case categories, Component 3a:

1. Detects which extreme cases are present
2. Surfaces them to the user one at a time, in priority order
3. Per case, presents 2–4 plain-English resolution options with cost/space impact
4. Receives the user's chosen option, applies it to the brief, logs the decision (chosen + full option set)
5. Re-runs Component 2 with the revised brief
6. Loops until no blockers remain (or user aborts, or user enters Preview Mode)
7. Returns a `ResolvedBrief` ready for layout generation (BUILDABLE or PREVIEW mode)

### 1.2 What Component 3a does NOT do

- Does NOT resolve soft warnings or non-blocking gaps (those flow downstream to layout)
- Does NOT generate layouts (that's Layer 2)
- Does NOT iterate on layouts (that's C3b, post-layout)
- Does NOT use LLM for option suggestion (rule-based only in v0.1)
- Does NOT change the user's chosen city
- Does NOT toggle plot type (DETACHED to CONTINUOUS) — CBA classification is a Master-Plan attribute, not a user choice (research-backed; see EC-006)

### 1.3 Success criteria for v0.1 build

1. Detects all 10 locked extreme cases from a `DesignGapAnalysis`
2. Maps each detected case to a `ResolutionOption` set with 2–4 options each (plus "different plot" and "Preview Mode" conditional options)
3. Each option produces a deterministic `BriefChange` that can be applied (where applicable; "Preview Mode" sets a flag rather than mutating brief)
4. After option chosen, re-runs C2 and either continues or terminates
5. Loop terminates within iteration cap (7 total / 3 per case_id) or escalates if not
6. Decision log captures every choice made + the full option set presented (Level B logging)
7. End-to-end test: brief with multiple blockers → user resolution path → ResolvedBrief → C2 returns no blockers OR Preview Mode requested
8. Test coverage: ~53 tests across 10 case detection paths + flow integration + edge cases + Preview Mode + counterfactual rendering
9. The user-facing language passes the Design Principle 1 test (talks to user, not engine; advisory tone, not auditor tone)
10. The early-warning soft gate fires at 1.25x budget without blocking the flow

### 1.4 Emotional outcome (per Design Principle 1)

After completing Extreme Case Gate, the user should feel: *"Some parts of what I wanted aren't possible on this plot at this budget. The system told me clearly, gave me real options, explained why each option matters, and I made the call. I could even see what my dream looked like via Preview Mode. I'm not surprised by anything."*

Not: *"The system rejected my brief."*

---

## 2. The 10 Extreme Cases (LOCKED)

Each case has: an ID, a category, a detection rule, a user-facing message template, a per-case framing line (psychological layer per critique #8), and a set of `ResolutionOption`s.

### 2.1 Categories

```
SPATIAL    - brief literally won't fit the envelope
LEGAL      - design violates code in a way no layout choice can fix
BUDGET     - no layout makes the numbers work
SITE       - the site itself fights the brief
APPROVAL   - won't get permitted regardless of layout
```

### 2.2 The 10 cases

#### EC-001 — TOTAL_AREA_EXCEEDS_ENVELOPE (Category: SPATIAL)

**Detection:** Sum of room minimum-areas (with circulation factor 1.30 from C1) > buildable envelope × floor count.

**Per-case framing line (shown above options):**
> *"Your plot doesn't have enough buildable area for everything in your brief. One of these trade-offs is necessary to make it work."*

**User-facing message template:**
> *"Your plot fits about {available_sqft} sqft per floor across {floors} floors = {total_buildable} sqft total. The rooms in your brief need at least {required_sqft} sqft. You're short by about {shortfall_sqft} sqft."*

**Resolution options:**
1. Drop the lowest-priority room (per priority order: bedrooms > kitchen > living > rest, so cuts from "rest" first) — RECOMMENDED if shortfall < 200 sqft
2. Reduce room count by 1 (drop bedroom 3, drop study, etc.) — RECOMMENDED if shortfall 200-500 sqft
3. Add a floor (only if FAR allows) — RECOMMENDED if FAR has headroom
4. Accept smaller room sizes (use NBC minimum instead of furniture-envelope minimum) — flagged with INFO advisory: "resulting rooms may be cramped"
5. Proceed anyway (logged risk acceptance) — produces BUILDABLE mode layout because EC-001 is non-legal
6. Preview Mode (see what your full brief looks like, watermarked, not buildable) — always last

#### EC-002 — PLOT_WIDTH_INSUFFICIENT (Category: SITE) [REVISED per critique #2]

**Detection:** Three-tier per Indian reality:

| Tier | Threshold | Behavior |
|---|---|---|
| Physical | width < 12 ft (any home) / 14 ft (2BHK) / 16 ft (3BHK) | HARD_FAIL — even compromised layouts can't fit furniture |
| Severe compromise | 14-15 ft (2BHK) / 16-18 ft (3BHK) | EC-002 fires; user explicitly accepts severe compromises |
| Comfortable | >= 5.5m (2BHK) / 6.7m (3BHK) per Neufert | No EC; soft note in layout output only |

**Per-case framing line:**
> *"Plots this width work, but the layout has real compromises. We want you to know what you're choosing."*

**User-facing message:**
> *"Your plot is {plot_width_ft} ft wide. A {brief_bhk} home is buildable here, but bedrooms will be narrow ({estimated_bedroom_width} ft) and furniture choices will be constrained (no king beds, wardrobes shallower than standard, single-loaded corridor only)."*

**Resolution options:**
1. Reduce BHK count (3BHK to 2BHK) — RECOMMENDED if user expressed flexibility on BHK in C1
2. Accept layout compromises — proceed with compromised brief, layout will fit but feel tight
3. Look for a different plot — promoted to RECOMMENDED if EC-002 co-fires with EC-006 (per critique #5)
4. Proceed anyway / Preview Mode (always last)

#### EC-003 — NO_PARKING_POSITION (Category: SITE)

**Detection:** Any `CheckResult` in `practical_report.blocking_issues` with `check_id == "parking_width_feasibility"` and `severity == HARD_FAIL`. (C1's `parking_feasibility` GuidanceMessage does not propagate to C3a; C2's `parking_width_feasibility` check is the authoritative source.)

**Per-case framing line:**
> *"There's no place on your plot for a covered car bay. To make it work, here's what we can do."*

**User-facing message:**
> *"Your plot is {plot_width_ft} ft wide with {setback_ft} ft setbacks. After leaving room for the entry path, there's no way to fit a covered car bay (needs at least 2.5m x 5m)."*

**Resolution options:**
1. Drop covered parking — accept open street parking — RECOMMENDED in tier-2/3 cities
2. Convert to stilt parking (adds floor cost ~Rs 2.5L but removes ground-floor footprint constraint) — RECOMMENDED in metros
3. Look for a different plot — last resort
4. Proceed anyway / Preview Mode (always last)

#### EC-004 — FAR_EXCEEDED (Category: LEGAL)

**Detection:** `(brief.total_floor_area_sqft / plot.area_sqft) > city_far_limit`.

**Per-case framing line:**
> *"Your brief asks for more building than your city's FAR (Floor Area Ratio) rules allow. To make this approvable, you'll need to make a structural change."*

**User-facing message:**
> *"Your brief works out to {requested_far} FAR. {city} allows up to {permitted_far} FAR for this plot type. You're over by about {excess_sqft} sqft."*

**Resolution options:**
1. Drop a floor (G+2 to G+1) — RECOMMENDED if the dropped floor is small relative to budget
2. Reduce per-floor area (shrink one or more rooms) — RECOMMENDED if excess is small (< 100 sqft)
3. Apply for FAR variance — flagged as advisory ("3-6 month process, Rs 50K-2L typical, success ~30%"), separate from us
4. Preview Mode (see your over-FAR brief as a layout, watermarked) — always last; **note no "proceed anyway" because it's a legal violation**

#### EC-005 — GROUND_COVERAGE_EXCEEDED (Category: LEGAL)

**Detection:** `working_envelope_area > plot.area * city.ground_coverage_max`.

**Per-case framing line:**
> *"Your envelope covers more of the plot than your city's rules allow. To make it approvable, you need a different envelope shape."*

**User-facing message:**
> *"Your envelope covers {working_coverage_pct}% of the plot. {city} allows up to {permitted_coverage_pct}%."*

**Resolution options:**
1. Increase setbacks (reduces footprint to allowed coverage) — RECOMMENDED, lowest cost
2. Reduce ground-floor footprint (e.g., make stilt parking partial-cover instead of full-cover)
3. Apply for variance — advisory only
4. Preview Mode — always last; no proceed-anyway (legal)

#### EC-006 — PRACTICAL_ENVELOPE_BELOW_BUILDABLE (Category: LEGAL) [RENAMED per critique #3]

**Detection:** Practical envelope (after USER-STATED setbacks) < minimum buildable for the brief's smallest possible layout. Code-strict failure is informational only (Invariant 8) — handled by C2's Gap analysis, not as a blocker here.

**Dedup note (added v0.2.1a):** EC-006 fires only when `brief.user_stated_setbacks` differ from `brief.nbc_compliant_setbacks`. If they are equal (the user followed code), EC-001 covers the same condition and EC-006 returns None to avoid duplicate surfacing.

**Per-case framing line:**
> *"Even with the setbacks you specified, your plot doesn't have enough envelope for the smallest version of your brief."*

**User-facing message:**
> *"With your stated setbacks ({front}/{rear}/{sides}), your buildable envelope shrinks to {envelope_sqft} sqft. That's below the minimum needed for any version of your brief ({min_buildable_sqft} sqft)."*

**Resolution options:**
1. Reduce brief scope (drop rooms until min-buildable fits the practical envelope) — RECOMMENDED if scope is flexible
2. Reduce stated setbacks further (advisory: "below 1 ft creates approval and structural challenges")
3. **Verify if your plot is in a Continuous Building Area (CBA)** — info-only with email-checklist follow-up. If CBA-verified, plot allows zero side setbacks. CMDA Master Plan determines this; not a user toggle.
4. Look for a different plot — promoted to RECOMMENDED if EC-006 co-fires with EC-002 (per critique #5)
5. Preview Mode — always last; no proceed-anyway (legal)

**The CBA verify option** carries a special action handler (`requires_action = "EMAIL_CBA_CHECKLIST"`):
- User clicks "Verify CBA"
- System captures email (if not already captured)
- Sends email with: link to CMDA land-use checker, list of known CBA-designated areas in user's city (T. Nagar, Sowcarpet, Mylapore, Triplicane for Chennai), step-by-step verification process, "reply with verification result and we'll restart your brief"
- Brief is paused as draft (24-hour resume token)
- User can return when verified

#### EC-007 — STILT_MANDATE_VIOLATED (Category: LEGAL)

**Detection:** `(city in {Mumbai, Delhi, Pune})` AND `brief.height_m > city.stilt_threshold_m` AND `brief.has_stilt == False`.

**Per-case framing line:**
> *"Your city requires stilt parking above a certain height. Your brief crosses that threshold."*

**User-facing message:**
> *"At {height_m} m, {city} mandates stilt parking (rule applies above {threshold_m} m)."*

**Resolution options:**
1. Add stilt parking (adds ~Rs 2.5L-4L, +1 effective floor) — RECOMMENDED
2. Reduce floor count to drop below threshold
3. Preview Mode — always last; no proceed-anyway (legal)

#### EC-008 — BUDGET_CATASTROPHICALLY_LOW (Category: BUDGET) [TWO-TIER per critique #1]

**Tier 1 — Early Warning (NOT an EC, soft signal only):**
- **Trigger:** `c7_cost_estimate.midpoint > brief.budget.target * 1.25`
- **Behavior:** SOFT_WARN through C2 scoring (-7 to score). Top-3 guidance in C1 mentions phased construction. NO modal. NO interruption to flow.
- **Rationale:** Industry-average overrun is 15-28%; firing at 1.25x catches users who can still adjust, before they emotionally commit.

**Tier 2 — Hard Extreme Case (this is EC-008):**
- **Detection:** `c7_cost_estimate.midpoint > brief.budget.target * 1.5`
- **Code-level note (added v0.2.1a):** in code, "c7_cost_estimate.midpoint" is `gap_analysis.practical_report.cost_estimate.exact_value` and "brief.budget.target" is `brief.budget_range.max_rupees`. The detector compares those two values directly; the spec wording is loose, the code is concrete — trust the code.
- **Threshold rationale (research-backed, locked 29 Apr 2026):**
  - Industry-average construction cost overrun in India = 15-28%
  - Recommended contingency buffer = 10-15%
  - Phased construction in India absorbs gaps up to ~30-40%
  - Top-up loans cover 20-35% gaps subject to LTV 75-85%
  - Beyond 50% gap, no standard Indian construction-finance mechanism bridges it without fundamental scope or budget change

**Per-case framing line:**
> *"The gap between your budget and the cost of this brief is too large for normal solutions like phased construction or top-up loans. You'll need a fundamental decision."*

**User-facing message:**
> *"Building this brief in {city} costs about Rs {estimate_l} L. Your budget is Rs {budget_l} L. The gap is Rs {gap_l} L (~{gap_pct}%). For context: phased construction in India typically absorbs gaps up to ~30-40%; yours is beyond that."*

**Resolution options:**
1. Increase budget by Rs {gap_l} L — with phased construction option ("build core first, finish phase 2 later")
2. Reduce scope dramatically (drop 1 BHK, drop walk-in, drop balcony, use lower-tier finishes)
3. Phase the construction (build shell + core now, finish bedrooms/kitchen later) — RECOMMENDED if gap is 50-65%
4. Pause the project — last resort, not framed as failure
5. Proceed anyway (logged risk acceptance) — BUDGET is non-legal so proceed-anyway is allowed; produces BUILDABLE mode (not Preview)
6. Preview Mode — always last

#### EC-009 — SOIL_REQUIRES_PILE_BUDGET_INSUFFICIENT (Category: SITE + BUDGET intersect)

**Detection:** `soil.classification.requires_pile == True` AND `(c7_estimate + pile_cost_estimate) > budget * 1.2`.

**Per-case framing line:**
> *"Your soil needs a pile foundation, which adds significant cost. Combined with your build estimate, that exceeds your budget."*

**User-facing message:**
> *"Your site has {soil_class} soil. That requires pile foundation (about Rs {pile_cost_l} L extra). Combined with your build estimate of Rs {base_estimate_l} L, you'd need Rs {total_l} L. Your budget is Rs {budget_l} L."*

**Resolution options:**
1. Increase budget to cover pile foundation
2. **Defer pile decision — get a verified soil test (Rs 3K-8K) which may show shallower good soil, in which case pile may not be needed** — RECOMMENDED, low-cost, high-info
3. Look for a different plot — last resort
4. Proceed anyway / Preview Mode (last)

#### EC-010 — APPROVAL_BLOCKER_UNREMEDIABLE (Category: APPROVAL) [REFINED per critique #4]

**Detection:** Any of C2's `legal_only_checks` returns `HARD_FAIL` AND no layout choice can fix it.

**Resolution probability per blocker subtype (NEW per critique #4):**

| Blocker subtype | Resolution probability | Typical path |
|---|---|---|
| Fire access | MEDIUM | Often resolved by minor envelope/entry adjustments + driveway redesign |
| Electric line clearance (LT line) | MEDIUM | Often negotiable through site engineer; line position sometimes shiftable |
| Electric line clearance (HT line) | LOW | HT lines are operationally fixed; usually requires plot change |
| Watercourse setback | LOW | Watercourse is a fixed natural feature; rarely negotiable |
| Heritage/CRZ overlay | LOW | Overlay is regulatory; variance possible but slow |

**Per-case framing line (varies by resolution_probability):**
- HIGH/MEDIUM: *"This kind of approval blocker often has a resolution path. Here's what we can try."*
- LOW: *"This kind of approval blocker is rarely resolvable on this plot. Most often, the realistic path is a different plot."*

**User-facing message:**
> *"This site has an approval blocker: {blocker_description}. {resolution_probability_explainer}. Without resolving this, the building won't be approved."*

**Resolution options (vary by resolution_probability):**

For HIGH/MEDIUM:
1. Apply for planning variance (advisory: "3-6 months, Rs 50K-2L, success ~50%")
2. Engage local planning consultant (advisory: "Rs 15K-30K, often knows shortcuts")
3. Look for a different plot
4. Preview Mode

For LOW:
1. Look for a different plot — RECOMMENDED
2. Apply for planning variance (advisory: "3-6 months, Rs 50K-2L, success ~10%")
3. Preview Mode

**No proceed-anyway for any EC-010 case** (regulatory by definition).

---

## 3. Domain shape

### 3.1 New domain objects (in `domain/extreme_case.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

class ExtremeCaseCategory(Enum):
    SPATIAL = "SPATIAL"
    LEGAL = "LEGAL"
    BUDGET = "BUDGET"
    SITE = "SITE"
    APPROVAL = "APPROVAL"

class ExtremeCaseId(Enum):
    EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE = "EC_001"
    EC_002_PLOT_WIDTH_INSUFFICIENT = "EC_002"
    EC_003_NO_PARKING_POSITION = "EC_003"
    EC_004_FAR_EXCEEDED = "EC_004"
    EC_005_GROUND_COVERAGE_EXCEEDED = "EC_005"
    EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE = "EC_006"
    EC_007_STILT_MANDATE_VIOLATED = "EC_007"
    EC_008_BUDGET_CATASTROPHICALLY_LOW = "EC_008"
    EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW = "EC_009"
    EC_010_APPROVAL_BLOCKER = "EC_010"

class ResolutionProbability(Enum):
    """For EC-010 subtypes; not used for other ECs."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_APPLICABLE = "N/A"

class BriefMode(Enum):
    """The mode the ResolvedBrief flows downstream in."""
    BUILDABLE = "BUILDABLE"
    PREVIEW = "PREVIEW"

class CostConfidence(Enum):
    """Per critique #9, applied to cost_impact_inr fields."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass(frozen=True)
class BriefChange:
    """A discrete, applicable change to a Brief.

    Per critique #7 pushback: BriefChange is intentionally atomic.
    The cascade of dependent fields (FAR, area, cost) happens through
    C2's full re-run after BriefChange is applied. The integrity invariant:
    apply_brief_change() MUST produce a Brief that passes Brief.__post_init__
    validation; otherwise the change is rejected.
    """
    field_path: str
    operation: str            # "DELETE" | "SET" | "INCREMENT"
    new_value: Any
    description: str

@dataclass(frozen=True)
class CostImpact:
    """Transparency Triple for cost (Design Principle 2).

    v0.2.1 update: when confidence == LOW, caveat_language and uncertainty_pct
    are populated; UI surfaces them prominently. Numbers are NEVER hidden
    (rejected critique #3's suppression proposal); instead they are caveated.
    """
    low_inr: int
    midpoint_inr: int
    high_inr: int
    confidence: CostConfidence
    derivation: str
    # v0.2.1 additions:
    caveat_language: Optional[str] = None  # e.g., "this could shift ±40%" — populated for LOW
    uncertainty_pct: Optional[int] = None  # 15 / 25 / 40 for HIGH/MEDIUM/LOW

@dataclass(frozen=True)
class ResolutionOption:
    option_id: str
    description: str
    impact_summary: str
    cost_impact: Optional[CostImpact]
    space_impact_sqft: int
    recommended: bool
    recommendation_reason: Optional[str]
    requires_brief_change: tuple[BriefChange, ...]
    requires_action: Optional[str]  # "EMAIL_CBA_CHECKLIST" | "PAUSE_FOR_USER_VERIFICATION" | None
    risk_advisory: Optional[str]
    is_preview_mode: bool = False

@dataclass(frozen=True)
class ExtremeCase:
    case_id: ExtremeCaseId
    category: ExtremeCaseCategory
    blocking_gap_ids: tuple[str, ...]
    user_facing_message: str
    framing_line: str
    resolution_probability: ResolutionProbability
    options: tuple[ResolutionOption, ...]
    detected_at_iteration: int
    transition_banner: Optional[str]

@dataclass(frozen=True)
class ExtremeDecision:
    case_id: ExtremeCaseId
    chosen_option_id: str
    chosen_option_description: str
    presented_options: tuple[ResolutionOption, ...]  # Q3 Level B logging
    user_acknowledged_at: str
    iteration_index: int

@dataclass(frozen=True)
class ExtremeDecisionLog:
    started_at: str
    completed_at: Optional[str]
    decisions: tuple[ExtremeDecision, ...]
    iterations_used: int
    aborted: bool
    abort_reason: Optional[str] = None
    # "USER_ABORTED" | "MAX_ITERATIONS_REACHED" | "PER_CASE_LIMIT_REACHED"
    # | "USER_CHOSE_PREVIEW_MODE" | "AWAITING_CBA_VERIFICATION"

@dataclass(frozen=True)
class CounterfactualSummary:
    """Per Reaction 1: shown on final ResolvedBrief screen.

    v0.2.1 update: max 2 alternatives per decision (per critique #5).
    Framing line added at the top of the alternatives section.
    """
    case_id: ExtremeCaseId
    chosen_option_id: str
    chosen_outcome: str
    alternatives: tuple[tuple[str, str, str], ...]  # max length 2
    # Each tuple: (option_id, option_description, "would have" outcome statement)
    framing_line: str = (
        "These were valid alternatives at the time. "
        "There is no single 'correct' choice."
    )

@dataclass(frozen=True)
class PreflightSummary:
    """v0.2.1 NEW (per critique #2). Shown BEFORE the first EC modal,
    sets correct expectation that multiple constraints exist and they
    interact.
    """
    total_blocker_count: int
    blocker_categories: tuple[ExtremeCaseCategory, ...]  # unique categories present
    summary_message: str  # e.g., "We found 3 constraints affecting your plan: setbacks, plot width, and budget. Fixing one may affect the others."
    early_plot_hint: Optional[str]  # populated per critique #4 below

@dataclass(frozen=True)
class PreviewModeAcknowledgment:
    """v0.2.1 NEW (per critique #1). When user selects Preview Mode,
    they must explicitly acknowledge before generation. This struct is
    persisted in ExtremeDecisionLog for audit.
    """
    user_acknowledged_at: str  # ISO timestamp
    acknowledgment_text: str   # exact text shown to user
    user_session_id: str       # for audit trail

@dataclass(frozen=True)
class ResolvedBrief:
    original_brief: 'Brief'
    revised_brief: 'Brief'
    decision_log: ExtremeDecisionLog
    final_feasibility: 'DesignGapAnalysis'
    mode: BriefMode
    is_layout_ready: bool
    counterfactuals: tuple[CounterfactualSummary, ...]
    # Preview Mode specifics:
    unresolved_blockers: tuple[ExtremeCase, ...]
    relaxed_constraints: tuple[str, ...]
    # v0.2.1 additions:
    preflight_summary: Optional[PreflightSummary] = None  # populated when ECs were found
    preview_mode_acknowledgment: Optional[PreviewModeAcknowledgment] = None  # populated only in PREVIEW mode
```

### 3.2 Domain types to register in `_DOMAIN_TYPE_NAMES`

All 15 types (5 enums + 10 dataclasses) added to `utils/component_contract.py`'s `_DOMAIN_TYPE_NAMES` set per v0.7.1 enforcement. v0.2.1 adds two new dataclasses: `PreflightSummary` and `PreviewModeAcknowledgment`.

### 3.3 BriefChange integrity invariant (alternative to critique #7)

```python
def apply_brief_change(brief: Brief, change: BriefChange) -> Brief:
    """Apply change to brief and return new validated brief.

    INVARIANT: result MUST pass Brief.__post_init__ validation.
    If validation fails, raise BriefChangeIntegrityError — do NOT
    return malformed brief. C2 only ever sees valid briefs.
    """
    new_brief_dict = _apply_operation(brief, change)
    try:
        new_brief = Brief(**new_brief_dict)  # __post_init__ runs here
    except (ValueError, TypeError) as e:
        raise BriefChangeIntegrityError(
            f"BriefChange {change.description} produced invalid Brief: {e}"
        )
    return new_brief
```

The cascade of dependent fields (FAR, area, cost) happens through C2's full re-run after BriefChange is applied. Component 3a does not duplicate C2 logic.

---

## 4. Algorithm

### 4.1 High-level flow

```
Input: brief (from C1), feasibility_input (optional)

[1] Run C2.run_feasibility(brief, feasibility_input)
     -> gap_analysis : DesignGapAnalysis

[2] Detect extreme cases:
     cases = ExtremeCaseDetector.detect(gap_analysis, brief)

[3] If cases is empty:
     return ResolvedBrief(brief, brief, empty_log, gap_analysis,
                          mode=BUILDABLE, is_layout_ready=True,
                          counterfactuals=(), unresolved_blockers=(),
                          relaxed_constraints=())

[3.5] BUILD PREFLIGHT SUMMARY (v0.2.1, per critique #2):
     If iteration == 0 (first time):
         preflight = build_preflight_summary(cases)
         Compute early_plot_hint per critique #4:
             IF (any case is EC-006 with severe shortfall <60% envelope) OR
                (any case is EC-010 with LOW resolution_probability) OR
                (any case is EC-002 at physical tier):
                 early_plot_hint = "Heads up: based on your plot's
                                    characteristics, you may want to consider
                                    whether this plot is the right fit before
                                    working through these trade-offs."
             ELSE: early_plot_hint = None
         Surface preflight to user as a non-blocking summary screen
         User clicks "Continue" -> proceed to [4]

[4] Sort cases by priority:
     LEGAL -> SITE -> APPROVAL -> SPATIAL -> BUDGET
     Promote "different plot" if EC-002+EC-006 co-fire OR >=2 hard blockers persist iter>=2
     Surface FIRST case to user with framing_line + transition_banner (if applicable)

[5] Receive user's chosen option_id

[6] If option.is_preview_mode:
     # v0.2.1 (per critique #1): require explicit acknowledgment FIRST
     Show mandatory checkbox modal:
         "I understand this cannot be legally approved or built as-is.
         This applies to me, my contractor, and anyone else who sees this layout."
         [ ] (must check)
         [ Continue with Preview Mode ]   [ Go back ]
     If user proceeds:
         Build PreviewModeAcknowledgment(timestamp, exact text, session_id)
         Build ResolvedBrief with mode=PREVIEW, unresolved_blockers=remaining_cases,
         relaxed_constraints derived from blocker categories,
         preview_mode_acknowledgment=ack
         Build counterfactuals from decisions so far + remaining cases
         RETURN
     If user cancels: return to case modal (option not yet committed)

[7] If option.requires_action == "EMAIL_CBA_CHECKLIST":
     Trigger email send, pause brief as draft,
     return aborted=True with abort_reason="AWAITING_CBA_VERIFICATION"

[8] Apply BriefChange(s) from chosen option:
     revised_brief = apply_brief_change(brief, option.requires_brief_change)

[9] Log the decision (chosen + presented options per Q3 Level B)

[10] Re-run C2 on revised_brief -> new_gap_analysis

[11] Detect new extreme cases on new_gap_analysis

[12] Termination checks:
     If new cases is empty:
         Build counterfactuals
         return ResolvedBrief(... mode=BUILDABLE, is_layout_ready=True ...)
     If iteration_count >= 7:
         return ResolvedBrief(aborted=True, abort_reason="MAX_ITERATIONS_REACHED")
     If iter_count_for_case_id >= 3:
         return ResolvedBrief(aborted=True, abort_reason="PER_CASE_LIMIT_REACHED")
     Else:
         # v0.2.1 (per critique #8): trigger on case_id change, not category change
         If new top case.case_id != previous case.case_id AND iter in [2,3]:
             Set transition_banner on new case
         goto [4] with new cases
```

### 4.2 Priority order for surfacing

When multiple cases exist on a single iteration, surface in this order:

1. LEGAL first (FAR, ground coverage, setbacks, stilt) — these define the box
2. SITE second (plot width, parking, soil) — these define what fits the box
3. APPROVAL third (approval blockers) — define if it can be permitted
4. SPATIAL fourth (area exceeds envelope) — defined by box + brief
5. BUDGET last (resolved after physical constraints clarified)

**Rationale:** Resolving budget before physical constraints risks the user "increasing budget" only to find the brief still doesn't fit, wasting their decision.

**"Different plot" promotion rule (per critique #5):**
- IF (EC-002 fires AND EC-006 fires) OR (>=2 hard blockers persist after iter 2):
  - "Different plot" option is promoted to RECOMMENDED in the next case's option set
  - Adds a meta-banner: *"At this point, the most realistic option may be a different plot. We've highlighted that option for you."*

### 4.3 Loop termination (per critique #6)

- **Success:** No extreme cases detected after a re-run of C2 -> return `mode=BUILDABLE, is_layout_ready=True`
- **Preview Mode chosen:** User picked Preview Mode option -> return `mode=PREVIEW, is_layout_ready=True` with unresolved_blockers populated
- **Max total iterations:** 7 iterations attempted, still blockers -> return `aborted=True, abort_reason="MAX_ITERATIONS_REACHED"`. UI: *"After 7 attempts, we still have constraints we can't reconcile. Please consider rethinking the brief from scratch or look for a different plot."*
- **Per-case limit:** Same `case_id` fires 3 times -> return `aborted=True, abort_reason="PER_CASE_LIMIT_REACHED"`. UI: *"This problem keeps coming back even after fixes. The most realistic option may be {recommendation_based_on_case}."*
- **User abort:** User clicks "Save and exit" -> return `aborted=True, abort_reason="USER_ABORTED"`. Brief saved as draft.
- **CBA verification pause:** User picks "Verify CBA" option -> email sent, brief paused as draft, user returns later.

### 4.4 Transition banner logic (per Q5 + v0.2.1 critique #8)

```python
def should_show_transition_banner(
    current_case: ExtremeCase,
    previous_resolved_case: Optional[ExtremeCase],
    iteration: int
) -> Optional[str]:
    """Banner fires only when:
    - We're on iteration 2 or 3 (not iter 1, not iter >= 4)
    - Previous resolved case has DIFFERENT case_id than current
      (v0.2.1: changed from category to case_id per critique #8 — users
       don't think in categories, they think 'a different problem appeared')

    Reasoning: avoids alert fatigue while surfacing genuinely surprising
    transitions. Iter 1 is expected; iter >= 4 needs the loop-detection
    escalation message instead.
    """
    if iteration not in (2, 3):
        return None
    if previous_resolved_case is None:
        return None
    if previous_resolved_case.case_id == current_case.case_id:
        return None  # same problem persisted, no banner
    return (
        f"Your previous choice ({previous_resolved_case.chosen_option_short}) "
        f"resolved {previous_resolved_case.case_id.value} but introduced "
        f"{current_case.case_id.value}. Many briefs need 2-3 iterations — "
        f"this is normal."
    )
```

### 4.5 Preview Mode mechanics (v0.2.1 — significantly hardened per critique #1)

When user selects a Preview Mode option:

**Step 1 — Mandatory acknowledgment gate (NEW v0.2.1):**

Show a hard friction modal:

```
[ Modal ]

  Heading: "Before generating Preview Mode"

  Body:
  "This layout shows your original brief, but it cannot be legally
  approved or built as-is. {N} blocker(s) remain unresolved:

  - {blocker 1 name}
  - {blocker 2 name}
  - ...

  Preview layouts are conceptual only. They have:
  - dimensions shown as ranges, not exact measurements
  - watermarks across rooms (not just page edges)
  - no door/electrical/plumbing/structural details

  Do not use this layout as a construction reference."

  Required:
  [ ] I understand this cannot be legally approved or built as-is.
      This applies to me, my contractor, and anyone else who sees this layout.

  Buttons:
  [ Continue with Preview Mode ]   (disabled until checkbox checked)
  [ Go back to options ]
```

If user cancels: return to case modal, option not committed.
If user proceeds: capture acknowledgment, build PreviewModeAcknowledgment.

**Step 2 — Build ResolvedBrief:**

1. `ResolvedBrief.mode = BriefMode.PREVIEW`
2. `unresolved_blockers` populated with all remaining ExtremeCases
3. `relaxed_constraints` derived from blocker categories:
   - EC-001 -> `("AREA_VS_ENVELOPE",)`
   - EC-004 -> `("FAR",)`
   - EC-005 -> `("GROUND_COVERAGE",)`
   - EC-006 -> `("PRACTICAL_ENVELOPE_MIN",)`
   - EC-007 -> `("STILT_MANDATE",)`
   - EC-010 -> `("APPROVAL_BLOCKERS",)`
4. `preview_mode_acknowledgment` populated with timestamp + exact text + session_id

**Step 3 — Component 16 pre-commitment (HARDENED v0.2.1):**

Component 16 (Renderer, when built) reads `mode` and in PREVIEW mode produces:
- 1 layout (not 3)
- Working drawing-equivalent geometry only — NOT a working drawing
- **Dimensions rendered as RANGES** ("approximately 11-13 ft", not "12.4 ft") so the layout cannot be used as a measurement reference
- **Watermarks at 30% opacity inside each room** (not just page edges) — impossible to crop out without removing the rooms themselves
- Title block reads "PREVIEW LAYOUT — NOT FOR CONSTRUCTION" instead of normal title
- **No door swing details** (suppress door arc rendering)
- **No electrical points**
- **No plumbing route lines**
- **No column positions / structural notation**
- No BOQ
- No regulatory drawing
- No contractor pack
- Persistent banner with `unresolved_blockers` list
- Sticky CTA "Resolve blockers and generate the buildable version"

These are pre-committed to Component 16's spec. Logged in v2_backlog as a Component 16 v0.1 spec requirement.

### 4.6 Counterfactual generation (per Reaction 1 + v0.2.1 critique #5)

After the flow terminates (BUILDABLE or PREVIEW), build a `CounterfactualSummary` per decision.

**v0.2.1 changes per critique #5:**
- Max 2 alternatives per decision (was unlimited; was decision-paralysis risk)
- Pick top 2 by: highest recommendation flag first, then largest impact-distance from chosen
- Preview Mode option STAYS in counterfactuals (rejected critique's hide proposal — honesty over comfort)
- Framing line shown above alternatives: *"These were valid alternatives at the time. There is no single 'correct' choice."*

```python
def build_counterfactual(decision: ExtremeDecision) -> CounterfactualSummary:
    """For each option NOT chosen, generate a 'would have' statement.

    Returns max 2 alternatives. Preview Mode stays in the list, formatted
    neutrally (not as 'better' or 'worse', just 'different').
    """
    chosen = next(o for o in decision.presented_options
                  if o.option_id == decision.chosen_option_id)

    candidates = []
    for opt in decision.presented_options:
        if opt.option_id == decision.chosen_option_id:
            continue
        would_have = _format_would_have(opt)  # neutral phrasing for Preview
        candidates.append((opt, would_have))

    # Rank: recommended first, then by space_impact distance from chosen
    candidates.sort(key=lambda x: (
        not x[0].recommended,
        -abs(x[0].space_impact_sqft - chosen.space_impact_sqft)
    ))

    # Take top 2
    alternatives = tuple(
        (opt.option_id, opt.description, would_have)
        for opt, would_have in candidates[:2]
    )

    return CounterfactualSummary(
        case_id=decision.case_id,
        chosen_option_id=decision.chosen_option_id,
        chosen_outcome=chosen.impact_summary,
        alternatives=alternatives,
        # framing_line uses default
    )

def _format_would_have(opt: ResolutionOption) -> str:
    """Neutral phrasing. For Preview Mode, explicit about its nature."""
    if opt.is_preview_mode:
        return (
            "would have given you a watermarked layout for your original "
            "brief, useful for family discussion but not buildable"
        )
    return f"would have {opt.impact_summary.lower()}"
```

UI uses this on the final ResolvedBrief screen. For family discussion. Not regret-induction; informational only.

### 4.7 Preflight summary (NEW v0.2.1, per critique #2 + #4)

When `iteration == 0` AND `has_blockers == True`, build a `PreflightSummary` and surface it as a non-blocking screen BEFORE the first EC modal:

```python
def build_preflight_summary(cases: tuple[ExtremeCase, ...]) -> PreflightSummary:
    unique_categories = tuple(set(c.category for c in cases))
    total = len(cases)

    if total == 1:
        summary_message = (
            f"We found 1 constraint affecting your plan. "
            f"Let's work through it."
        )
    else:
        category_names = _format_category_list(unique_categories)
        summary_message = (
            f"We found {total} constraints affecting your plan: "
            f"{category_names}. Fixing one may affect the others."
        )

    # Per critique #4: early "wrong plot" hint
    early_plot_hint = None
    if any(_is_severe_envelope_shortfall(c) for c in cases) or \
       any(_is_low_resolution_approval(c) for c in cases) or \
       any(_is_physical_tier_width(c) for c in cases):
        early_plot_hint = (
            "Heads up: based on your plot's characteristics, you may want to "
            "consider whether this plot is the right fit before working "
            "through these trade-offs. We'll show you the options anyway — "
            "your call."
        )

    return PreflightSummary(
        total_blocker_count=total,
        blocker_categories=unique_categories,
        summary_message=summary_message,
        early_plot_hint=early_plot_hint,
    )
```

**UI shape:**

```
[ Preflight Summary Screen ]

  Heading: "Before we generate layouts"

  Body: {summary_message}

  Optional early plot hint (when applicable):
    NOTICE: {early_plot_hint}

  Buttons:
    [ Continue ]
    [ Save and exit ]
```

Single click "Continue" -> proceed to first EC modal. The summary is non-blocking but sets correct expectations.

### 4.8 Reason-aware error formatting (NEW v0.2.1, per critique #7)

When `apply_brief_change()` raises `BriefChangeIntegrityError`, surface the specific validation reason to the user, not a generic failure message.

```python
def format_validation_error_for_user(
    error: BriefChangeIntegrityError,
    option: ResolutionOption,
) -> str:
    """Translate technical validation error into user-facing reason.

    Examples:
        "Brief.bedrooms count below 2" -> 
            "Removing bedroom 3 would leave only 1 bedroom, which is below
             your stated 2-bedroom minimum."

        "Brief.budget.target_inr below threshold" ->
            "Reducing budget by Rs 10L would put estimated cost at Rs 62L vs
             Rs 38L budget — gap exceeds the catastrophic threshold."

        "Brief.floors count exceeds FAR limit" ->
            "Adding a floor would push your design over the FAR limit for
             your city."
    """
    err_type = error.classify()  # one of a known set of validation failures

    template = {
        "BEDROOM_COUNT_BELOW_MIN": (
            f"Removing {option.description.lower()} would leave only "
            f"{error.context['resulting_count']} bedroom(s), which is below "
            f"your stated {error.context['stated_min']}-bedroom minimum."
        ),
        "BUDGET_BELOW_THRESHOLD": (
            f"Reducing budget by Rs {error.context['delta_l']}L would put "
            f"estimated cost at Rs {error.context['est_l']}L vs "
            f"Rs {error.context['budget_l']}L budget — gap exceeds the "
            f"catastrophic threshold."
        ),
        "FAR_EXCEEDED_BY_CHANGE": (
            f"Adding a floor would push your design over the FAR limit for "
            f"{error.context['city']}."
        ),
        # ... etc, one per known classification
    }.get(err_type, f"This option doesn't work for your brief — try another.")

    return template + " Try a different option."
```

The error generator builds these from known violation types; unknown types fall back to the generic message. The UI surfaces the specific reason inline below the option that failed, with the option visually marked as unavailable.

---

## 5. API contract

### 5.1 Endpoint 1: Initial check after C2

```
POST /api/extreme-case/check

Body:
{
  "brief_token": "uuid-from-c1-save",
  "feasibility_input": { ... }
}

200 Response (no blockers):
{
  "has_blockers": false,
  "instructions": "No blockers. Layout generation can proceed.",
  "feasibility_summary": "...",
  "soft_warnings": [...],   // Tier 1 budget early-warning shows here
  "next_step": "PROCEED_TO_LAYOUT"
}

OR (blockers exist):
{
  "has_blockers": true,
  "current_iteration": 0,
  "current_case": { /* ExtremeCaseDict */ },
  "remaining_blocker_count": 3,
  "next_step": "USER_DECIDE"
}
```

### 5.2 Endpoint 2: Apply user's choice

```
POST /api/extreme-case/resolve

Body:
{
  "brief_token": "uuid",
  "case_id": "EC_001",
  "chosen_option_id": "EC_001_OPT_A_DROP_LOWEST_PRIORITY",
  "iteration_index": 0
}

200 Response (continuing):
{
  "applied_changes": [ /* list of BriefChange dicts */ ],
  "revised_brief_summary": "...",
  "is_done": false,
  "current_iteration": 1,
  "next_case": {
    /* ExtremeCaseDict */
    "transition_banner": "Your previous choice ... resolved EC_001 but introduced EC_007. Many briefs need 2-3 iterations - this is normal.",
    /* or null if banner doesn't apply */
  },
  "remaining_blocker_count": 2,
  "next_step": "USER_DECIDE"
}

OR (done — buildable):
{
  "is_done": true,
  "mode": "BUILDABLE",
  "resolved_brief": { /* ResolvedBriefDict */ },
  "decision_log": { /* full log */ },
  "counterfactuals": [ /* per Reaction 1 */ ],
  "next_step": "PROCEED_TO_LAYOUT"
}

OR (done — preview):
{
  "is_done": true,
  "mode": "PREVIEW",
  "resolved_brief": { /* ResolvedBriefDict */ },
  "decision_log": { /* full log */ },
  "counterfactuals": [ /* per Reaction 1 */ ],
  "unresolved_blockers": [ /* list of ExtremeCases the user bypassed */ ],
  "relaxed_constraints": [ "FAR", "STILT_MANDATE" ],
  "warning_message": "This brief has unresolved blockers. The layout you'll see is for preview only and cannot be built without first resolving these.",
  "next_step": "PROCEED_TO_PREVIEW_LAYOUT"
}

OR (paused for CBA verification):
{
  "is_done": false,
  "paused": true,
  "pause_reason": "AWAITING_CBA_VERIFICATION",
  "email_sent_to": "user@example.com",
  "draft_token": "uuid",
  "user_message": "We've sent you a CBA verification checklist. Reply when you have your answer and we'll restart the brief.",
  "next_step": "WAIT_FOR_USER_RETURN"
}

OR (aborted/looped):
{
  "is_done": false,
  "aborted": true,
  "abort_reason": "MAX_ITERATIONS_REACHED" | "PER_CASE_LIMIT_REACHED",
  "user_message": "After 7 attempts, we still can't reconcile your brief...",
  "next_step": "RETURN_TO_BRIEF"
}
```

### 5.3 Endpoint 3: Explicit user abort

```
POST /api/extreme-case/abort

Body:
{
  "brief_token": "uuid",
  "reason": "I want to think about this"
}

200 Response:
{
  "saved_as_draft": true,
  "draft_token": "uuid"
}
```

### 5.4 Endpoint 4: CBA verification follow-up

```
POST /api/extreme-case/cba-verified

Body:
{
  "draft_token": "uuid",
  "verification_result": "CBA_CONFIRMED" | "NOT_CBA" | "STILL_UNSURE"
}

200 Response:
{
  "brief_restarting": true,
  "next_step": "RESTART_BRIEF_WITH_PLOT_TYPE_CONTINUOUS"
                | "PROCEED_WITH_ORIGINAL_BRIEF"
                | "MANUAL_FOLLOWUP"
}
```

### 5.5 Endpoint 5: CBA verification fallback (NEW v0.2.1, per critique #6)

After 24h with no /cba-verified call on a paused brief:

```
POST /api/extreme-case/cba-fallback-continue

Body:
{
  "draft_token": "uuid"
}

200 Response:
{
  "brief_resuming": true,
  "assumed_plot_type": "DETACHED",  // i.e., NOT continuous; safe default
  "next_step": "RESUME_AT_LAST_CASE_WITH_NOT_CBA_ASSUMPTION",
  "user_message": "Continuing assuming your plot is NOT a Continuous Building Area. You can correct this later if needed."
}
```

The system schedules a notification at 24h post-pause inviting the user to use this endpoint. UI surfaces the option as a button: *"Continue assuming NOT CBA"* alongside the original "Verify and reply" CTA.

Logged in `ExtremeDecisionLog` as a decision with `case_id == EC_006`, `chosen_option_id == "EC_006_OPT_3_FALLBACK_NOT_CBA"`.

---

## 6. UI flow (one blocker at a time)

After C1 form submit -> C2 runs silently in background -> if has_blockers:

```
[ Modal/Panel ]

  Heading: "{Case category icon} {Case headline}"

  Optional transition banner (iter 2-3 only, category change):
    INFO: "Your previous choice ({short}) resolved {old_case} but introduced
       {new_case}. Many briefs need 2-3 iterations - this is normal."

  Framing line (psychological layer per critique #8):
    "{per-case framing - e.g., 'One of these trade-offs is necessary.'}"

  Body: {user_facing_message}

  Options:
    Option 1 — {description}
       Impact: {impact_summary}
       Cost: Rs {low}-{midpoint}-{high} L  ({CostConfidence indicator})
       Derivation: "estimated from {derivation}"
       [ Recommended for: {reason} ]   <- shown only on recommended

    Option 2 — ...

    Option 3 — ...

    -----

    Option N — Look for a different plot   <- shown when conditions trigger
       [ Recommended ] when >=2 hard blockers OR EC-002+EC-006 co-fire

    Option (last) — Preview Mode — see your brief as a layout, watermarked, not buildable
       [ This shows you the dream version. The layout cannot be approved or built as-drawn. ]

  Buttons:
    [ Make this choice ]   (disabled until option selected)
    [ Save and exit ]      (saves draft, returns to brief form)

  Footer: "Blocker {N} of {M}" + "Iteration {iter}/7"
```

**One case at a time. No multi-select. No "skip for now" (Q2 — proceed-anyway is an explicit option per case, with category guardrails).**

When done (BUILDABLE) -> green checkmark, "Brief is feasible. Generating layouts..."
When done (PREVIEW) -> orange notice with watermark example, "Generating preview layout. Reminder: this is informational only — not buildable as drawn."

**Final ResolvedBrief screen (both modes) shows counterfactuals:**

```
[ Final Brief Screen ]

  Heading: "Your brief is ready for layout generation"
  Sub: "Mode: BUILDABLE" or "Mode: PREVIEW (informational only)"

  Section: "Decisions you made"

    Decision 1: {case_id}
    You picked: {chosen_option_description}
    Outcome: {chosen_outcome}

    Other options that were available:
    - {alt 1 description} - would have {alt 1 outcome}
    - {alt 2 description} - would have {alt 2 outcome}

    [ Discuss with family - you can come back to this anytime ]

    Decision 2: ...

  Buttons:
    [ Generate layouts ]
    [ Go back and change a decision ]   (re-enters flow at chosen iteration)
```

---

## 7. Integration with C1 and C2

### 7.1 With C1 (Brief Capture)

**Read-only.** C3a never modifies C1's logic. It receives a fully-validated `Brief` as input.

When a user has a saved brief draft (resume token in localStorage), the resume flow includes the C3a state:
- If brief is in `BRIEF_FINALIZED` state -> C3a runs from scratch
- If brief is in `EXTREME_CASE_GATE` state -> resume at iteration N with case M
- If brief is in `LAYOUT_READY` state (BUILDABLE or PREVIEW) -> skip C3a, forward to layout pipeline (or preview pipeline)
- If brief is in `AWAITING_CBA_VERIFICATION` state -> show "verify CBA, click here when done" prompt

### 7.2 With C2 (Feasibility)

**Calls into C2 freely.** C3a is the primary client of C2's `run_feasibility()` after the initial form-submit run.

C2's existing scoring contract is unchanged. C3a only reads:
- `gap_analysis.gaps` filtered to `severity == BLOCKING_IF_NOT_ACCEPTED`
- `gap_analysis.feasibility_practical.score`
- `gap_analysis.cost_delta_to_upgrade_inr`
- `gap_analysis.feasibility_practical.cost_estimate`

**Tier 1 budget early-warning** flows through C2's existing soft-warn pipeline; C3a doesn't add UI for it. It's a regular gap with severity `MARGINAL_OR_BUDGET_EARLY_WARN`.

### 7.3 Component contract registration

```python
ComponentContract(
    component_id="c03a",
    version="0.1.0",
    input_type="Brief",
    output_type="ResolvedBrief",
    requires={"c01": ">=0.9.3", "c02": ">=0.1"},
)
```

### 7.4 Pre-commitment to Component 16

This spec pre-commits Component 16 (Dual-Drawing Renderer) to support a Preview Mode rendering when it's built. Logged in v2_backlog. Component 16's spec must include:
- Detect `ResolvedBrief.mode == PREVIEW`
- Render single layout (not 3)
- Render working drawing only (no regulatory drawing)
- Suppress BOQ + contractor pack
- Add watermark "PREVIEW - NOT BUILDABLE AS-DESIGNED" on every page
- Add persistent banner with `unresolved_blockers` list
- Add sticky CTA "Resolve blockers and generate the buildable version"

---

## 8. Failure modes (per Design Principle 7)

| Failure | What happens |
|---|---|
| C2 returns no blockers (the happy path) | Skip C3a entirely, forward to layout (BUILDABLE) |
| C2 returns Tier 1 early-warning only (1.25x budget) | Skip C3a entirely, soft warning surfaces in layout output |
| C2 returns blocker outside our 10 categories | Log warning, treat as soft warn, allow user to proceed with notice |
| User clicks "Save and exit" | Save brief as draft, return to brief form |
| 7 total iterations reached without resolution | Surface message, save state, return to brief form |
| Same case_id re-fires 3 times | Surface PER_CASE_LIMIT_REACHED message, save state |
| Same case_id re-fires after option chosen (loop) | Detect after 2 such loops, surface "this option created a new version of the same problem" message |
| Option's BriefChange fails Brief.__post_init__ validation | Log error as BriefChangeIntegrityError, refuse to apply, surface "this option doesn't work for your brief - try another" |
| Browser closes mid-flow | Resume token + iteration state lets user continue exactly where they left off |
| C2 itself errors | Bubble up as system error; don't pretend brief is OK |
| User picks Preview Mode | Build PREVIEW ResolvedBrief, forward to preview layout pipeline |
| User picks Verify CBA | Send email, pause as draft, await user return |
| Email sending fails on CBA verify | Log error, surface "we couldn't send the email - check spam folder, or proceed without verification" |

---

## 9. Test plan

### 9.1 File: `tests/test_c03a_session1_domain.py` (~7 tests)
Domain types: round-trip serialization, frozen-ness, validation in `__post_init__`.

### 9.2 File: `tests/test_c03a_session2_detection.py` (~12 tests)
Each of the 10 EC detections with hand-crafted DesignGapAnalysis:
- EC-001 detected; negative case (envelope sufficient)
- EC-002 three-tier (physical / severe / comfortable boundaries)
- EC-003 detected; negative case
- EC-004 / EC-005 / EC-006 / EC-007 each
- EC-008 two-tier (1.25x early warn, 1.5x hard EC)
- EC-009 / EC-010
- Negative tests confirming no false positives

### 9.3 File: `tests/test_c03a_session3_options.py` (~10 tests)
Per EC: option generation produces 2-6 options with correct structure.
- Recommended flag fires correctly
- Cost impact has Transparency Triple
- Preview Mode option is always last
- "Different plot" option promotes when EC-002+EC-006 co-fire
- "Verify CBA" option appears for EC-006 in Chennai
- For EC-010: resolution_probability shifts options correctly

### 9.4 File: `tests/test_c03a_session4_apply.py` (~6 tests)
- BriefChange applied produces correct revised brief
- Immutability preserved
- BriefChangeIntegrityError raised on invalid changes
- Counterfactual built correctly per decision

### 9.5 File: `tests/test_c03a_session5_orchestrator.py` (~12 tests)
Full flow:
- 0 blockers (skip C3a)
- 1 blocker, 1 iteration
- 3 blockers, 1 iteration each
- 1 blocker, resolution creates new blocker (2 iterations)
- 7 total iterations max reached (abort)
- Per-case limit reached (abort)
- User abort
- Preview Mode chosen on iteration 1
- Preview Mode chosen on iteration 3 with partial resolutions
- CBA verification path (pause)
- Transition banner fires correctly (iter 2, category changed)
- Transition banner doesn't fire (iter 1; iter >=4; same category)

### 9.6 File: `tests/test_c03a_session6_api.py` (~6 tests)
Four endpoints, happy + edge paths.

**Total target: ~53 tests.**

---

## 10. What's NOT in scope

- Post-layout trade-off (C3b)
- LLM-driven option suggestion
- Per-room dimension trade-offs
- Topology change suggestions (that's an option set within C5/C11a, not C3a)
- City switch
- Plot search ("find me a different plot") — recommendation only, no listings integration
- Variance-application generator (advisory mentions only)
- Plot type toggling DETACHED to CONTINUOUS (locked NO; only "verify CBA" advisory)
- Per-option click/hover/dwell-time telemetry (Level C logging deferred to v2)

---

## 11. Resolved questions (for the record)

| Q | Resolution | Source |
|---|---|---|
| Q1 — EC-008 budget threshold | x 1.5 (locked); two-tier with 1.25x early-warn (per critique #1) | Web research, 15 sources, 29 Apr 2026 |
| Q2 — "Skip this blocker, proceed anyway"? | Yes for non-legal ECs (EC-001, EC-008) producing BUILDABLE; No for legal/approval ECs producing PREVIEW only | Discussion 29 Apr 2026 |
| Q3 — Decision log retention | Level B: chosen + presented option set logged in ExtremeDecision.presented_options | Audit + analytics research, 29 Apr 2026 |
| Q4 — Plot type change as EC-006 option | NO toggling; advisory "verify CBA" with email-checklist follow-up (Reaction 2) | TNCDBR research + Reaction 2 discussion |
| Q5 — "Heads up, your fix made a new problem" banner | Conditional: iter 2-3 AND category changed; NOT every iteration | Progressive-disclosure UX research |
| Reaction 1 — Counterfactuals on final screen | YES — families discuss alternatives | Discussion 29 Apr 2026 |
| Reaction 2 — Verify CBA action | Email checklist, pause as draft, /cba-verified endpoint | Discussion 29 Apr 2026 |
| Preview Mode | YES — user can see layout past any EC, watermarked, single layout, no BOQ/regulatory/contractor pack | Discussion 29 Apr 2026 |

---

## 12. Locked invariants this component honours

- **Invariant 5 — PENDING ENGINEER VALIDATION on every output.** ResolvedBrief output carries the same disclosure as Brief.
- **Invariant 6 — Bedrooms > Kitchen > Living priority for cuts.** Used in EC-001 option generation.
- **Invariant 7 — Vastu INFO-only, never blocks.** Vastu is never an EC trigger.
- **Invariant 8 — Most realistic briefs land at Code-Strict 40 — correct, not bug.** A Code-Strict 40 score does NOT trigger an EC. Only HARD blockers (BLOCKING_IF_NOT_ACCEPTED) do.
- **Invariant 9 — User owns the decision.** Every EC offers options; user picks. No silent override. Preview Mode honors this fully — user can see the dream even when it's not buildable.
- **Invariant 10 — Confidence != correctness.** ResolvedBrief retains all confidence labels from inputs.

---

## 13. Build sessions (next step after this lock)

**Estimated 8 build sessions** (v0.2.1 scope adjusted: +Preview Mode acknowledgment gate, +preflight summary, +CBA fallback endpoint, +reason-aware errors):

1. **S1 — Domain objects** (`domain/extreme_case.py`, registration in `_DOMAIN_TYPE_NAMES`) — 15 types (5 enums + 10 dataclasses including PreflightSummary + PreviewModeAcknowledgment) — ~310 LOC
2. **S2 — Detection** (`components/c03a/detector.py`, all 10 EC detections + 2-tier EC-002 + 2-tier EC-008) — ~400 LOC
3. **S3 — Option generation** (`components/c03a/option_generator.py`, per-EC option sets + Preview Mode option + "different plot" promotion + Transparency Triple cost impact + LOW-confidence caveat language) — ~520 LOC
4. **S4 — BriefChange application + reason-aware errors** (`components/c03a/brief_change_apply.py` + `components/c03a/error_formatter.py`) — ~220 LOC
5. **S5 — Counterfactual + Preflight builders** (`components/c03a/counterfactual.py` + `components/c03a/preflight.py`) — ~180 LOC
6. **S6 — Orchestrator** (`components/c03a_extreme_case_gate.py`, full loop + termination + transition banner case_id-based + Preview Mode handling with acknowledgment + preflight integration) — ~450 LOC
7. **S7 — API endpoints** (`api/extreme_case_endpoint.py`, 5 endpoints including /cba-fallback-continue + email-trigger for CBA + 24h scheduler hook) — ~290 LOC
8. **S8 — Validation suite** (`tests/test_c03a_session*.py`, ~60 tests across 10 EC paths + integration + Preview Mode acknowledgment + CBA fallback + preflight + reason-aware errors) — ~700 LOC

**Estimated total: ~2,370 LOC + 700 LOC tests = 3,070 LOC. Calendar: 6-8 days at C1/C7 cadence; 1 conversation at back-to-back cadence.**

**Test count: ~60 tests** (up from v0.2's 53 due to v0.2.1 additions).

After S8 ships:
- Update master document Part 4 with Sessions 17-25 (this conversation + 8 build sessions)
- Update master document Part 8 (Build Status: 4 of 17 components built, 13 to go)
- Update master document Part 9 with decisions D-047, D-048, D-049, D-050
- Update master document Part 12 with all new C3a code
- Bump master doc to v2.1 — eventually v3.0 when C3a fully ships

---

*Specification LOCKED by Claude on 29 April 2026, with Ramalingam's approval across multiple review rounds. Ready for build start.*

*Next session: S1 — Domain objects.*
