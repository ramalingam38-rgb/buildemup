# 06 — Briefing Pack Reading List

**Send this to the architect AFTER engagement letter is signed.**

**Total reading volume:** ~80 pages, broken into 10 documents. Realistic reading time: 4-5 hours across 2-3 evenings.

**Reading order matters.** Document 1 (the orientation note) frames everything; documents 2-3 give product motivation; documents 4-10 are the specs that need critique. Don't send all 10 at once — send in 3 batches over 3 days to avoid overwhelming the reviewer.

---

## Send order (3 batches over 3 days)

### Batch 1 — Orientation (day 1, ~30 min reading)

1. **Orientation note for the architect** (NEW document, written by Ramalingam + Claude specifically for B-238; see `06a_orientation_note_for_architect.md` in this packet) — 2 pages
2. **Project summary one-pager** — extracted from `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` "Project context" paragraph, expanded to one page

### Batch 2 — Product motivation (day 2, ~1 hour reading)

3. **Master Doc v3.16 → v3.17 delta** — `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md`
4. **The "why this project exists" essay** — derived from user's origin story (1 page; written for the architect specifically; can re-use `00_README.md` "Why this matters" section)

### Batch 3 — Specs to critique (days 3-7, ~3-3.5 hours reading)

Send all 7 in one go after architect has confirmed they read Batches 1+2:

5. **C1 + C2 + C3a/b combined** — brief capture, feasibility, extreme-case + negotiation. ~12 pages. Focus: programming layer.
6. **C4 v1.1 LOCKED** — `02_specs_chronological/07_C4_SPEC_v1_1_LOCKED.md`. ~10 pages. Focus: plot analysis, setbacks, FAR, soil defaults.
7. **C6 v0.7 LOCKED + C7 v0.9 LOCKED + C8 v0.6 LOCKED + C9 v0.7 LOCKED** — combined ~20 pages. Focus: orientation, structural grid, corridor, room sizer.
8. **C10 v1.0 LOCKED** — `02_specs_chronological/61_C10_SPEC_v1_0_LOCKED.md`. ~8 pages. Focus: wet zones. **Note to architect: hydraulics depth is being separately reviewed in B-220 with a plumbing engineer; B-238 only validates the WET-ZONE LAYOUT layer.**
9. **C13 v1.0 + C14 v0.2 + C15 v1.0 + C16 v1.2 ratifications** — ~15 pages combined. Focus: door placement, connection graph, problem finder, dual drawings.
10. **C17 v0.3 LOCKED** — `02_specs_chronological/S50_C16_v1_2_C17_v0_3_C3b_v0_4_LOCKED/spec_C17_v0_3_LOCKED.md`. ~5 pages. Focus: quote comparison.

---

## Concrete file paths (Ramalingam: zip these and attach)

When you send to the architect, zip these files into 3 archives matching the batches above. Use plain English filenames the architect can recognize.

### Batch 1 zip — "01_orientation.zip"
- `04_backlog/B238_architect_engagement_packet_S56/06a_orientation_note_for_architect.md` (RENAME to `Orientation_Note_for_Reviewer.md` in the zip)
- (Optional) print to PDF before zipping if the reviewer prefers paper-feel

### Batch 2 zip — "02_product_motivation.zip"
- `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md` (RENAME to `Project_Master_Doc.md`)
- `04_backlog/B238_architect_engagement_packet_S56/06b_why_this_project_exists.md` (RENAME to `Why_This_Project_Exists.md`)

### Batch 3 zip — "03_specs_for_review.zip"
Put each spec in its own subfolder named after the component so the reviewer can navigate:

| Subfolder | Files |
|---|---|
| `C1_C2_C3_brief_and_feasibility/` | Locked specs for C1, C2, C3a, C3b — use `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md` as index |
| `C4_plot_analysis/` | `02_specs_chronological/07_C4_SPEC_v1_1_LOCKED.md` |
| `C5_topology_C6_orientation/` | `02_specs_chronological/16_C5_SPEC_v0_9_LOCKED.md` + `26_C6_SPEC_v0_7_LOCKED.md` |
| `C7_structural_grid/` | `02_specs_chronological/79_C7_AMENDMENT_v0_9_LOCKED.md` |
| `C8_corridor_C9_room_sizer/` | `33_C8_SPEC_v0_6_LOCKED.md` + `41_C9_SPEC_v0_7_LOCKED.md` + `90_C9_AMENDMENT_v0_11_LOCKED.md` |
| `C10_wet_zones/` | `61_C10_SPEC_v1_0_LOCKED.md` + `94_MultiFloorWetZonePlannedCandidate_SPEC_v0_3_LOCKED.md` |
| `C11_topology_mutation/` | `66_C11a_SPEC_v1_0_LOCKED.md` + `69_C11b_SPEC_v1_0_LOCKED.md` + `73_B_NEW_J_AMENDMENT_v1_0_LOCKED.md` |
| `C12_vertical_alignment/` | `02_specs_chronological/C12_v1_0_LOCKED/` (entire folder) |
| `C13_doors/` | `02_specs_chronological/C13_v1_0_LOCKED/` (entire folder) |
| `C14_connection_graph/` | `02_specs_chronological/C14_v0_2_LOCKED/spec_C14_v0_2_LOCKED.md` |
| `C15_problem_finder/` | `02_specs_chronological/S49_C15_LOCK/C15_v1_0_LOCK_RATIFICATION.md` + S48 specs |
| `C16_dual_drawings/` | `02_specs_chronological/S50_C16_v1_2_C17_v0_3_C3b_v0_4_LOCKED/spec_C16_v1_2_LOCKED.md` |
| `C17_quote_comparator/` | `02_specs_chronological/S50_C16_v1_2_C17_v0_3_C3b_v0_4_LOCKED/spec_C17_v0_3_LOCKED.md` |

Also include this top-level file in `03_specs_for_review.zip`:
- `04_backlog/B238_architect_engagement_packet_S56/07_review_question_template.md` (RENAME to `Review_Question_Template.md` — the architect fills this in as their deliverable, OR ignores it and writes free-form)

---

## What to OMIT from the briefing pack

Do NOT send:
- Anything in `08_session_transcripts/` — too raw, too long, will overwhelm
- Anything in `06_upstream_codebase/` — architect doesn't read Python
- Anything in `04_backlog/` other than this packet's own files — too long, history of decisions doesn't matter for review
- Old master doc versions other than v3.16 → v3.17 delta — too much
- S55 LOCK closures Python code — derived from specs, sending derivative is noise

---

## What to PREP separately (for mid-review call)

Have these ready in case architect asks during mid-review:
- A copy of `05_integrity_check/B108_PARTIAL_NBC_VERIFICATION_S55.md` (current state of NBC corridor verification — partial)
- A copy of `05_integrity_check/B150_PARTIAL_NBC_VERIFICATION_S54.md` (current state of NBC primary-source verification — partial)
- The list of KB defaults per city (extract from `06_upstream_codebase/buildemup/kb/soil_city_defaults.py` and `material_rates_multicity.py` — JSON or table format, easier for architect to read than Python)
- An exported list of all 35 entries in the C15 severity rule table + 35 entries in check registry (extract from `06_upstream_codebase/buildemup/components/c15/lock_closures_s55.py` to a readable table)
- The IS 962:1967 renderer conformance values currently pinned (extract from `06_upstream_codebase/buildemup/components/c16/lock_closures_s55.py`)

These are reference materials, not initial reading. Send only if asked.
