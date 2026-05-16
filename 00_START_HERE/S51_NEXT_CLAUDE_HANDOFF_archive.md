# 🚨 NEXT CLAUDE — START HERE — S51 OPEN

**Authored:** Ramalingam + Claude, S50 close, May 15 2026
**Session state:** Track 3 canonical 17-component spec phase **COMPLETE** (19 of 19 sub-components LOCKED)
**Your task:** Start coding C17 (Quote Comparison Engine) IMMEDIATELY.

---

## 🎯 IMMEDIATE DIRECTIVE FROM RAMALINGAM

> *"I want the next Claude to start immediately coding the c17."*

**Do not start another spec round. Do not re-litigate C17 design. Spec is LOCKED. Code is next.**

If your instinct is to re-read the C17 spec and "verify" or "refine" before coding — **stop**. The spec went through 3 critique rounds (12 → 4 → 0 patches) and LOCKED at v0.3. Read it once to internalize, then code.

---

## ✅ Prerequisites — ALL READY

| Dependency | Status | Path |
|---|---|---|
| C7 v0.8 LOCKED (cost, RateProvider, MaterialRate, TransparencyTriple) | ✅ Shipped | `06_upstream_codebase/buildemup/components/c07/` |
| C15 v1.0 LOCKED (Problem Finder, SelectionResult) | ✅ Shipped (264 tests) | `03_code_chronological/S50_*/buildemup/components/c15/` |
| C16 v1.2 LOCKED (DualDrawingBundle, AttestedValue, AdvisoryFlag) | ✅ Shipped (419 tests) | `03_code_chronological/S50_*/buildemup/components/c16/` |
| C17 v0.3 LOCKED spec | ✅ LOCKED | `02_specs_chronological/S50_*/spec_C17_v0_3_LOCKED.md` |
| Test infrastructure | ✅ 683/683 green | `03_code_chronological/S50_*/tests/` |

---

## 🛠 First Tasks (in order)

### Task 1 — Read C17 v0.3 LOCKED spec ONCE
- Path: `02_specs_chronological/S50_*/spec_C17_v0_3_LOCKED.md`
- Internalize: § 0.1 mission framing, § 2 output contract, § 3 phase pipeline, § 7 R-invariants (R1–R18), § 9.1 LOCK-mandatory backlog.
- **Do not re-read repeatedly.** Trust the LOCK.

### Task 2 — Set up C17 module skeleton (mirror C16 structure)
```
buildemup/components/c17/
├── __init__.py
├── versioning.py        # C17_VERSION, schema versions, expected upstream versions
├── errors.py            # LocalQuoteError + PerQuoteLineError hierarchies
├── contracts.py         # QuoteComparisonReport + nested dataclasses
├── config.py            # PriceSignal thresholds, fuzzy-match params
├── cache_keys.py        # signature computation
├── schema.py            # schema_descriptor_digest builder
├── upstream_adapter.py  # consumes C7 + C16 typed inputs
├── orchestrator.py      # 6-phase orchestrator (STRICT vs WARN)
└── phases/
    ├── __init__.py
    ├── alpha_canonicalize.py    # Phase α — quote ingestion + canonicalization
    ├── beta_boq_assembly.py     # Phase β — BOQ assembly from C7/C16/RateProvider
    ├── gamma_matching.py        # Phase γ — 4-tier match (high/medium/low/human_verification)
    ├── delta_verdicting.py      # Phase δ — PriceSignal verdicts + thresholds
    ├── epsilon_totals.py        # Phase ε — TotalComparison + DiscussionBaseline
    └── zeta_indicators.py       # Phase ζ — ItemizationIndicators + ReportConfidence + signing
```

This mirrors C16's structure exactly. Study `03_code_chronological/S50_*/buildemup/components/c16/` for the pattern before writing.

### Task 3 — Write versioning.py + contracts.py first
- These are pure data — no logic, no dependencies on phase code
- Use C16's `versioning.py` as template
- The full `QuoteComparisonReport` dataclass tree from § 2 of the spec goes in `contracts.py`

### Task 4 — Implement phases one at a time, with tests
Phase order: α → β → γ → δ → ε → ζ. Mirror C16's discipline: each phase is a pure function, fully tested in isolation, then integration-tested via the orchestrator.

**Target: ~285 tests at v1.0 implementation LOCK (per spec § 10):**
- ~8 versioning
- ~15 errors
- ~30 contracts
- ~15 phase α
- ~15 phase β
- ~25 phase γ
- ~15 phase δ
- ~12 phase ε
- ~15 phase ζ
- ~15 orchestrator
- ~15 PBT layer
- ~10 adversarial corpus (5 scenarios)
- ~20 advisory-tone lint
- ~10 human-review tier
- ~10 decomposition acknowledgment
- ~8 gap interpretation defaults
- ~8 rate staleness disclosure
- ~5 no-aggregate-score
- (= ~285)

### Task 5 — ChennaiRateProvider v1 concrete implementation
- 50+ rates across categories (RCC, masonry, plumbing, electrical, finish)
- Each with `MaterialRate(brand, grade, is_code, rate, rate_min, rate_max, unit, source, supplier_type)` per C7's existing `MaterialRate` pattern
- Source: project's existing `kb/` modules + manual research as needed
- Wire as default `RateProvider` when `jurisdiction_profile_id == "tn_cdbr_2019"`

### Task 6 — Advisory-tone lint (R2 enforcement)
- Banned-phrase list from § 7.1 of C17 v0.3 LOCKED spec
- Lint runs on every emitted `signal_explanation` + `advisory_note` + `conversation_language` string
- Test file `test_c17_advisory_tone_lint.py` catches each banned phrase
- Lint MUST fail loudly if a banned phrase appears in output

### Task 7 — Fuzzy-match calibration
- Corpus of 20+ real-world quote line items with known correct BOQ matches
- Tune Levenshtein threshold per § 6 hard ceiling (0.4) and tier downgrade rules
- Test file verifies ≥ 80% of obvious matches found

---

## 🚫 What NOT to do

- **Do not propose another C17 critique round.** Spec is LOCKED.
- **Do not refactor C15 or C16.** Both LOCKED; they are upstream consumers, not dependencies-to-modify.
- **Do not start C3b implementation yet.** Per Ramalingam: C17 first, then C3b. C3b spec is LOCKED at v0.4 but its phase implementations are after C17 ships.
- **Do not invent new fields on `QuoteComparisonReport`.** The schema is published API per R8. Additions are MINOR bumps requiring justification per R12 (semantic compression).
- **Do not skip R5 downgrade discipline.** Low-confidence matches with would-be `ABOVE_REFERENCE_RANGE` MUST downgrade to `ABOVE_TYPICAL`. We never accuse confidently when uncertain.
- **Do not emit any aggregate trust score for the contractor.** v0.1 had this (`ContractorCredibility.score`) and it was removed in v0.2. Test `test_c17_no_aggregate_score.py` is mandatory — no `score: int`, no `tier` field characterizing the contractor.

---

## 📋 Rule discipline reminders

You inherit Ramalingam's standing rules. Highlights:

- **Rule 1 — Spec-first.** You have a LOCKED spec. Honor it. Don't drift.
- **Rule 7 — Critique handling.** If something genuinely seems wrong in the spec, do Rule 7 critique walk. Don't silently deviate.
- **Rule 8 — LOCK is Ramalingam's authority.** You cannot LOCK C17 implementation; Ramalingam does.
- **Rule 9 / 9.2 — Backlog visibility.** Any item that surfaces during code goes in the backlog immediately.
- **Rule 10.6 — Three-check protocol** before every handoff.
- **Rule 11 — Vigorous self-analysis** at every component build + critique walk. Hunt for Pattern B (dropped output), unstated assumptions, fixture brittleness, dead code, test blind spots.

---

## 📂 What's in this bundle

| Dir | Contents |
|---|---|
| `00_START_HERE/` | This file + RULES_RAMALINGAM_FORMALIZED + THREE_OBLIGATIONS_AND_PATTERNS + prior session archives |
| `01_master_doc/` | MASTER_DOC_v3_14_TO_v3_15_DELTA (S50 close) + prior deltas + MASTER_DESIGN_NARRATIVE_v2_9 |
| `02_specs_chronological/S50_*/` | All S50 spec artifacts: C16 v1.2 LOCKED + ratification, C17 v0.3 LOCKED + ratification, C3b v0.4 LOCKED + ratification, all PROPOSED intermediates |
| `03_code_chronological/S50_*/` | C15 + C16 code at LOCK state + 26 test files + 683/683 green |
| `04_backlog/` | Cumulative backlog snapshots (cross-component) |
| `05_integrity_check/` | Three-check report for S50 close + prior reports |
| `06_upstream_codebase/` | Reference upstream codebase (C1–C14 shipped) |
| `07_design_documents/` | Architecture v3, Design Principles v3.1, Component Validation Report |
| `08_session_transcripts/` | Prior session transcripts (S30+) |
| `09_conversation_artifacts/` | S50 critique walks (9 documents) + responses |

---

## ✋ If you're confused about anything

The shortest unblocking path is:

1. Re-read `01_master_doc/MASTER_DOC_v3_14_TO_v3_15_DELTA.md`
2. Re-read `02_specs_chronological/S50_*/spec_C17_v0_3_LOCKED.md` § 1 (scope) + § 9 (backlog)
3. Re-read `03_code_chronological/S50_*/buildemup/components/c16/orchestrator.py` (your structural template)
4. Then code.

**Don't ask Ramalingam to re-explain C17 scope.** It's in the spec. The spec went through 3 critique rounds. Trust it.

---

## 🎬 Ready signal

When you finish reading this file, your next action is:

```bash
# Set up working tree
mkdir -p buildemup/components/c17/phases
touch buildemup/components/c17/__init__.py
touch buildemup/components/c17/phases/__init__.py

# Start with versioning constants
$EDITOR buildemup/components/c17/versioning.py
```

**Welcome to S51. Start coding. 🚀**
