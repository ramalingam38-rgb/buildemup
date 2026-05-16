# C13 v1.x Polish Backlog — Cumulative Rollup (S44 Continuation Close)

**Origin**: Items deferred during C13 spec walks #2-#7 per Rule 9.2 +
D15 MVP-LOCK freeze + reviewer recommendations.
**Total**: 35 items (28 C13-scope, 4 C12-scope routed earlier, 3 project-scope).

---

## C13-scope (28 items)

### Walk #2 originated (5)
| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C13-WINDOW-AVOIDANCE | Door selection avoids blocking windows | Window data upstream | M v1.x (priority-elevated post-LOCK per walk #4) |
| B-C13-SIGHT-LINE-OPTIMIZATION | Choose door angle for entry sight-line quality | C14 sight-line scoring | L (C14-routed) |
| B-C13-VASTU-PLACEMENT | Cultural placement rules | C5 vastu-rules layer | M |
| B-C13-FURNITURE-CLEARANCE | Door swing doesn't conflict with furniture | C9 furniture-fit data | M |
| B-C13-POCKET-DOORS | Pocket/sliding variants | Upstream door-type field | M |

### Walk #3 originated (5)
| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C13-SEMANTIC-PRIORITY-RESIDENTIAL | Full living>kitchen>pooja>dining typology ranking | C14 ships | M (C14-routed) |
| B-C13-PRIVACY-GRADIENT | Privacy-aware door selection | C14 privacy scoring | M (C14-routed) |
| B-C13-AUTO-MULTI-DOOR | Heuristic multi-door (no caller input) | Production usage signal | S-M |
| B-C13-LARGE-N-CSP-CONVERGENCE | Convergence guarantee for n > 15 | Luxury/commercial scaling | L v2+ |
| B-C13-FULL-3D-SWING-MODEL | Tier 3 fidelity (HIGH_FIDELITY) | 3D rendering needs | L v2+ |

### Walk #4 originated (4)
| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C14-LAYOUT-QUALITY-BAND | GOOD/ACCEPTABLE/COMPROMISED bands | When C14 v0.1 sketch lands | M (C14-side) |
| B-C13-MULTI-DOOR-BEDROOM-OVERRIDE | Luxury master suite multi-door | Luxury-residential demand | S |
| B-C13-CONVERGENCE-CORPUS | First 1000 production runs analysis | 1000 runs accumulated post-LOCK | S |
| B-PROJECT-PIPELINE-CONVENTION-CONSOLIDATION | Migrate C11a/C11b/C12 to typestate | C12 v2.0 cycle | L v2+ |

### Walk #5 originated (10) — D15 polish-deferred bundle
| ID | Description | Priority |
|---|---|---|
| B-C13-INVARIANT-CLASSIFICATION-FRAMEWORK | LEGALITY/SAFETY/QUALITY classification + governance checklist | partially shipped in v0.6 E1 + v0.7 expanded |
| B-C13-CATEGORY-SPECIFIC-DENSITY-CAPS | Per-category advisory density caps (emergency never aggregated) | v1.x |
| B-C13-INVARIANT-TAXONOMY-GROUPING | Formal grouping of D1-D23 into 6 categories — **CRITICAL priority** (3 walks deep) | v1.x within 30 days post-LOCK |
| B-C13-PHASE-D-DEBUG-PROVENANCE | Mutation-trail / rejected-states / rollback-reasons logging | v1.x |
| B-PROJECT-PIPELINE-RESULT-LINTING | Linting for new components to declare result pattern | v1.x project |
| B-C13-TELEMETRY-TIER-CLASSIFICATION | Tier minimal/debug/research + sampling | v1.x |
| B-C13-APPROXIMATE-EXPORT-RESTRICTIONS | Machine-readable fidelity metadata + export restrictions | v1.x (mostly C15-side) |
| B-C13-LAYERED-PBT-STRATEGY | Shared generators/scaffolds + mutation testing | v1.x |
| B-PROJECT-CONTRACT-REGISTRY | Centralized contract registry + dependency diagrams | v1.x project |
| B-C13-ADVISORY-CATEGORY-STRUCTURAL-RESTRICTION | Restrict advisories to observable structural signals | v1.x |

### Walk #6 originated (7)
| ID | Description | Effort |
|---|---|---|
| B-C13-GRAPH-TAXONOMY-FORMALIZATION | Formal G_all/G_primary/G_service/G_emergency namespacing | S (v1.x doc) |
| B-C13-CONSTRAINT-TAXONOMY | HARD/CONDITIONAL/ADVISORY/OPTIMIZATION doc (E1 partial bootstrap) | S |
| B-C13-CACHE-COMPATIBILITY-MANIFEST | Geometry/advisory/protocol/legality semantic versions in single manifest | M |
| B-C13-POLICY-GOVERNANCE-SECTION | Explicit policy-governance section | S |
| B-PROJECT-MECHANICAL-GOVERNANCE | CI checks + schema registries + linting + contract manifests | L v2+ |
| B-C14-EVALUATION-OPTIMIZATION-UX-SPLIT | C14 may need split into evaluation/optimization/UX-recommendation | L (C14-side) |
| B-C13-ADVERSARIAL-INTEGRATION-CORPUS | Adversarial corpus immediately after C14 sketch — **PRE-BUILD VALIDATION** | M |

### Walk #7 originated (4)
| ID | Description | Effort |
|---|---|---|
| B-C13-ADVISORY-CHANNEL-SPLIT | Split AdvisoryFlags into structural/experiential/safety channels | M |
| B-C13-DOC-SPLIT-CORE-GOVERNANCE-OPS | Separate spec into core/governance/ops docs | S |
| B-C13-PROVENANCE-VERBOSITY-TIERS | Verbosity levels for ConditionalLegalityViolation | S |
| B-C13-INTERNATIONALIZATION-POLICY-LAYER | Universal-code vs regional-conventions vs configurable-cultural | L v2+ |

---

## C12-scope (routed, 4 items from S44 critique walk)

These were filed in `v0_2_backlog_S44_C12_critique_walk_additions.md`:

| ID | Description | Pre-condition |
|---|---|---|
| B-C12-CAUSAL-FAILURE-TRACEABILITY | Causal failure traceability via parallel FailureTrace | None |
| B-C12-MISALIGNMENT-SEVERITY-SCORING | Severity score for misaligned features | C14 shipped |
| B-C12-LAYOUT-MEMORY-BANK | Retrieval-assisted topology initialization | C15 + N=200 plans |
| B-PROJECT-SPEC-DRIFT-CI | CI parser for LOCKED spec vs production code | All 17 components shipped |

Additionally from C13 v0.2 A5:
| ID | Description | Status |
|---|---|---|
| B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT | Add `edge_type: EdgeType` enum to C12 SharedEdge | HIGH priority; routed C12 v1.1 amendment; decoupled from C13 LOCK via C13 v0.3 B5 Protocol |

---

## Project-scope (3 items)

| ID | Description |
|---|---|
| B-PROJECT-PIPELINE-CONVENTION-CONSOLIDATION | (W#4) Migrate older components to typestate post-LOCK |
| B-PROJECT-PIPELINE-RESULT-LINTING | (W#5) Linting for new components to declare result pattern |
| B-PROJECT-MECHANICAL-GOVERNANCE | (W#6) CI + schema registries + linting + contract manifests |
| B-PROJECT-CONTRACT-REGISTRY | (W#5) Centralized contract registry + dependency diagrams |
| B-PROJECT-SPEC-DRIFT-CI | (S44 C12 walk) Detect LOCKED spec vs code drift |

(Note: 5 project-scope items total; some counted under walk-origin sections above. Net unique project-scope items: 5.)

---

## Priority hot-list (within 30 days post-C13 LOCK)

1. **B-C13-INVARIANT-TAXONOMY-GROUPING** — CRITICAL (cognitive overload flagged 3 walks deep)
2. **B-C13-ADVERSARIAL-INTEGRATION-CORPUS** — pre-build validation per walk #6
3. **B-C14-LAYOUT-QUALITY-BAND** — needed for C14 v0.1 sketch
4. **B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT** — C12 v1.1 spec walk
5. **B-C13-WINDOW-AVOIDANCE** — escalated to "v1.x post-LOCK fast-follow" per walk #4

Rest = standard v1.x evolution.

---

**Total cumulative backlog: 35 items** (28 C13-scope + 4 C12-scope routed + 5 project-scope, with some overlap counted under multiple buckets).
