"""
BuildemUp — Component 14 — Phase δ: quality-flag emission
==========================================================

Per C14 SPEC v0.2 LOCKED § 3 Phase δ + v0.2 A4 (Structural/Preference
split) + v0.2 A5 (TRANSIT_THROUGH_BEDROOM SKETCH) + v0.2 A6 (truncation
meta-flag, Inv E13') + v0.2 A8 (category_coverage_low) + v0.2 A10
(default severity=info).

Phase δ reads:
- GraphTopology (Phase α)
- NodeMetrics (Phase β)
- RoomMetadata per room (upstream)
- CirculationConfig (thresholds)

and produces TWO tuples of CirculationFlag:
- structural_flags: BOTTLENECK_CONCENTRATION | DEAD_END_ISOLATION |
   CATEGORY_COVERAGE_LOW | TRUNCATION_META
- preference_flags: TRANSIT_THROUGH_BEDROOM | PRIVACY_GRADIENT_VIOLATION |
   EXCESSIVE_DEPTH | TRUNCATION_META

Per A6 / Inv E13': len(structural) + len(preference) ≤ k × density_factor.
When the cap would be exceeded, the LAST tuple to overflow gets its
last slot replaced by a single TRUNCATION_META meta-flag enumerating
the suppressed kinds.

Per A10: ALL preference flags default to severity=info. Structural flags
also default to info at v0.2 (severity escalation belongs to C15).

Per A8: category_coverage is calculated separately by Phase ζ (it
depends on the input room_categories metadata, not on this module).
This module emits the `category_coverage_low` STRUCTURAL flag if the
already-computed coverage is below the threshold. Phase ζ passes the
coverage in via the `category_coverage` parameter so this module
remains a pure flag-emission function.

Inv E7 determinism:
- Rooms iterated in lex-ASC order
- All-pairs BFS in lex-ASC source order; lex-ASC neighbour expansion
- Suppressed-kinds enumeration in fixed StrEnum.value order
- TRUNCATION_META placed at the LAST slot of the over-cap tuple
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .config import CirculationConfig
from .contracts import (
    BEDROOM_CATEGORY_KEYWORDS,
    CIRCULATION_CATEGORY_KEYWORDS,
    PUBLIC_CATEGORY_KEYWORDS,
    RoomMetadata,
)
from .graph_construction import GraphTopology
from .node_metrics import NodeMetrics
from .schema import (
    CirculationFlag,
    PreferenceCirculationFlagKind,
    StructuralCirculationFlagKind,
    TRUNCATION_META_KIND_VALUE,
)


# =============================================================================
# Output: EmittedFlags
# =============================================================================

@dataclass(frozen=True)
class EmittedFlags:
    """Phase δ output: the two flag tuples after truncation-cap
    enforcement.

    Frozen for replay determinism.
    """
    structural_flags: tuple[CirculationFlag, ...]
    preference_flags: tuple[CirculationFlag, ...]


# =============================================================================
# Internal: metadata index for category lookup
# =============================================================================

def _build_category_index(
    metadata: tuple[RoomMetadata, ...],
) -> dict[str, str]:
    """room_id → category string."""
    return {rm.room_id: rm.category for rm in metadata}


def _is_bedroom(category: str) -> bool:
    return category in BEDROOM_CATEGORY_KEYWORDS


def _is_public(category: str) -> bool:
    return category in PUBLIC_CATEGORY_KEYWORDS


def _is_circulation(category: str) -> bool:
    return category in CIRCULATION_CATEGORY_KEYWORDS


# =============================================================================
# Detector 1 — BOTTLENECK_CONCENTRATION (Structural)
# =============================================================================

def _detect_bottleneck_concentration(
    *,
    topology: GraphTopology,
    node_metrics: NodeMetrics,
    category_index: dict[str, str],
    config: CirculationConfig,
) -> list[CirculationFlag]:
    """Per v0.1 § 1.3 BOTTLENECK_CONCENTRATION (Structural).

    A non-corridor room concentrates betweenness above the configured
    threshold. To convert rank → normalized betweenness without changing
    the SKETCH formula (B-C14-BETWEENNESS-FORMULA-LOCK pins the exact
    formula at v1.0), we use a rank-based proxy:

        normalized_rank = 1.0 - (rank - 1) / max(1, k - 1)

    Rank 1 (most-bottleneck) → 1.0; rank k (least) → 0.0.

    A room flags BOTTLENECK_CONCENTRATION iff:
    - normalized_rank ≥ config.betweenness_threshold (default 0.7)
    - AND room is NOT in a CIRCULATION category (corridors / foyers
      SHOULD have high betweenness; that's their architectural purpose)

    This is a SKETCH-level test consistent with the v0.1 § 1.3 text.
    B-C14-BETWEENNESS-FORMULA-LOCK at v1.0 will replace the rank-proxy
    with a true normalized Brandes value.
    """
    flags: list[CirculationFlag] = []
    k = len(topology.nodes)
    rank_lookup = dict(node_metrics.betweenness_rank)

    for room_id in topology.nodes:  # lex-ASC for determinism
        rank = rank_lookup[room_id]
        # Rank-based normalized betweenness proxy:
        if k <= 1:
            normalized = 0.0
        else:
            normalized = 1.0 - (rank - 1) / (k - 1)

        if normalized < config.betweenness_threshold:
            continue

        category = category_index.get(room_id, "")
        if _is_circulation(category):
            # Corridors / foyers / staircases are SUPPOSED to be high-
            # betweenness; not a flag.
            continue

        flags.append(CirculationFlag(
            flag_kind=StructuralCirculationFlagKind.BOTTLENECK_CONCENTRATION,
            affected_room_id=room_id,
            severity="info",  # per A10
            explanation_template=(
                f"Room {room_id} concentrates betweenness "
                f"(rank {rank}/{k}); a single non-corridor room serving "
                f"as primary crossing point may indicate over-reliance "
                f"on it."
            ),
            deduplication_key=f"bottleneck_concentration:{room_id}",
        ))

    return flags


# =============================================================================
# Detector 2 — DEAD_END_ISOLATION (Structural)
# =============================================================================

def _detect_dead_end_isolation(
    *,
    topology: GraphTopology,
    node_metrics: NodeMetrics,
    category_index: dict[str, str],
    main_entry_room_id: str,
) -> list[CirculationFlag]:
    """Per v0.1 § 1.3 DEAD_END_ISOLATION (Structural).

    A room is reachable only via a single non-corridor neighbour
    (degree-1 path) AND it's habitable (not itself a circulation
    category).

    "Reachable only via a single non-corridor neighbour" interprets
    here as:
    - connectivity[room] == 1 (single neighbour)
    - AND that neighbour is NOT a circulation category

    Habitability test: the room itself is also not a circulation
    category (a dead-end corridor that ends in a balcony is fine; it's
    when bedrooms / studies / etc. terminate the path that matters).

    **Sub-4 amendment (Rule 11 self-analysis):** The main entry room
    is EXEMPT from this flag. Entries are degree-1 by architectural
    design (the front door connects to one interior space, typically
    a foyer or living room) — flagging them as "dead-end isolation"
    is a false positive that pollutes small-graph reports. Filed as
    `B-C14-DEAD-END-ENTRY-EXEMPTION-LOCK` (v1.0-LOCK-MANDATORY, S).

    Per A10: severity=info.
    """
    flags: list[CirculationFlag] = []
    conn_lookup = dict(node_metrics.connectivity)
    # Build adjacency for neighbour lookup
    adjacency: dict[str, list[str]] = {r: [] for r in topology.nodes}
    for a, b in topology.edges:
        adjacency[a].append(b)
        adjacency[b].append(a)

    for room_id in topology.nodes:  # lex-ASC for determinism
        if room_id == main_entry_room_id:
            # Main entries are degree-1 by design; exempt.
            continue
        if conn_lookup[room_id] != 1:
            continue
        category = category_index.get(room_id, "")
        if _is_circulation(category):
            continue
        neighbour = adjacency[room_id][0]
        neighbour_category = category_index.get(neighbour, "")
        if _is_circulation(neighbour_category):
            continue

        flags.append(CirculationFlag(
            flag_kind=StructuralCirculationFlagKind.DEAD_END_ISOLATION,
            affected_room_id=room_id,
            severity="info",
            explanation_template=(
                f"Room {room_id} is reachable only through "
                f"{neighbour} (non-corridor). Single-point-of-access "
                f"isolation may be intentional but is worth verifying."
            ),
            deduplication_key=f"dead_end_isolation:{room_id}",
        ))

    return flags


# =============================================================================
# Detector 3 — CATEGORY_COVERAGE_LOW (Structural, per A8 / Inv E18)
# =============================================================================

def _detect_category_coverage_low(
    *,
    category_coverage: float,
    threshold: float,
) -> list[CirculationFlag]:
    """Per v0.2 A8 / Inv E18.

    A single STRUCTURAL flag emitted when `category_coverage < threshold`.
    Empty affected_room_id by convention (the flag pertains to the
    layout as a whole, not a specific room).

    Note: the spec allows empty affected_room_id ONLY for TRUNCATION_META
    per A6 — but the schema's __post_init__ raises if any other flag
    kind has empty affected_room_id. We use a sentinel "<layout>"
    room_id here.
    """
    if category_coverage >= threshold:
        return []
    return [CirculationFlag(
        flag_kind=StructuralCirculationFlagKind.CATEGORY_COVERAGE_LOW,
        affected_room_id="<layout>",
        severity="info",
        explanation_template=(
            f"Category coverage {category_coverage:.0%} below threshold "
            f"{threshold:.0%}; downstream consumers should verify "
            f"upstream categorization quality before trusting "
            f"circulation flags."
        ),
        deduplication_key="category_coverage_low:layout",
    )]


# =============================================================================
# Detector 4 — TRANSIT_THROUGH_BEDROOM (Preference, per v0.2 A5 SKETCH)
# =============================================================================

def _bfs_all_shortest_paths_pass_through(
    *,
    topology: GraphTopology,
    source: str,
    target: str,
    bedroom_set: frozenset[str],
) -> tuple[bool, bool]:
    """Returns (any_path_uses_bedroom_interior, all_paths_use_bedroom_interior).

    Per v0.2 A5 SKETCH definition:
    - TRANSIT_THROUGH_BEDROOM flags a bedroom R iff there exists a pair
      (A, B) where A, B ∉ bedroom_set, A ≠ B ≠ R, AND R is in the
      interior of the lex-ASC canonical BFS shortest path from A to B,
      AND no equal-length alternate avoids all bedroom-category rooms.

    Implementation: instead of computing the canonical lex-ASC BFS path
    (which would only check R against the chosen tie-break), we compute
    BOTH:
    - bedrooms-on-any-shortest-path (informational)
    - bedrooms-on-EVERY-shortest-path (the "no avoidable alternate"
      test — every shortest A→B walk passes through some bedroom)

    The flag fires when EVERY shortest A→B path interior touches a
    bedroom. If at least one shortest path avoids all bedrooms, the
    spec's "alternate avoids bedroom-category rooms" exception applies
    and the flag suppresses.

    Returns the pair (any_uses, all_use) so the caller can implement
    both interpretations if v0.3 amendments change it.
    """
    # Standard "all shortest paths" enumeration via BFS:
    # 1) compute dist[u] from source
    # 2) compute predecessors[u] = parents on shortest-path DAG
    # 3) backwalk from target to source, tracking which paths use a bedroom
    adjacency: dict[str, list[str]] = {r: [] for r in topology.nodes}
    for a, b in topology.edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    # Lex-ASC neighbour order for determinism
    for r in adjacency:
        adjacency[r].sort()

    dist: dict[str, int] = {source: 0}
    predecessors: dict[str, list[str]] = {r: [] for r in topology.nodes}
    queue: deque[str] = deque((source,))
    while queue:
        v = queue.popleft()
        for w in adjacency[v]:
            if w not in dist:
                dist[w] = dist[v] + 1
                queue.append(w)
            if dist.get(w) == dist[v] + 1:
                predecessors[w].append(v)

    if target not in dist:
        return (False, False)
    if dist[target] <= 1:
        # Direct neighbour or self — no interior nodes possible.
        return (False, False)

    # For each node on the shortest-path DAG, compute:
    # any_uses_bedroom[u] = True iff ANY shortest source→u path has
    #   some interior bedroom (i.e., a bedroom strictly between source
    #   and u).
    # all_use_bedroom[u] = True iff EVERY shortest source→u path has
    #   some interior bedroom.
    # Initial: source itself has no interior, so source's flags are
    # (False, False).

    # Walk in BFS order: process by ascending dist.
    nodes_by_dist: dict[int, list[str]] = {}
    for r, d in dist.items():
        nodes_by_dist.setdefault(d, []).append(r)
    max_d = dist[target]

    any_uses: dict[str, bool] = {source: False}
    all_use: dict[str, bool] = {source: False}

    for d in range(1, max_d + 1):
        for r in sorted(nodes_by_dist.get(d, [])):
            # Predecessors at distance d-1
            preds = predecessors[r]
            if not preds:
                continue
            # For each predecessor p: the path source→…→p→r has
            # interior bedroom iff EITHER (a) source→…→p had interior
            # bedroom OR (b) p itself is a bedroom AND p != source
            # (i.e., p is an interior node of source→r). The case
            # where r itself is a bedroom does NOT count yet — r is
            # the endpoint of source→r. r becomes an "interior" only
            # when r is processed as a predecessor of some further
            # node.
            any_pred_uses: list[bool] = []
            all_pred_use: list[bool] = []
            for p in preds:
                # Is p an interior bedroom relative to source→r?
                # Yes if p != source AND p ∈ bedroom_set.
                p_is_interior_bedroom = (
                    p != source and p in bedroom_set
                )
                # Path source→…→p→r uses interior bedroom iff:
                # any_uses[p] OR p_is_interior_bedroom
                this_any = any_uses.get(p, False) or p_is_interior_bedroom
                this_all = all_use.get(p, False) or p_is_interior_bedroom
                any_pred_uses.append(this_any)
                all_pred_use.append(this_all)
            # Aggregate across predecessors:
            # ANY path source→r uses bedroom iff any of the (source→p→r)
            #   paths use bedroom (i.e., ANY pred contributes a bedroom-
            #   using path).
            any_uses[r] = any(any_pred_uses)
            # ALL paths source→r use bedroom iff every pred only offers
            # bedroom-using paths AND every (source→p→r) is bedroom-using.
            all_use[r] = all(all_pred_use)

    return (any_uses.get(target, False), all_use.get(target, False))


def _detect_transit_through_bedroom(
    *,
    topology: GraphTopology,
    category_index: dict[str, str],
) -> list[CirculationFlag]:
    """Per v0.2 A5 SKETCH.

    For each bedroom R, scan all pairs (A, B) of non-bedroom rooms
    with A < B (lex-ASC, A ≠ B ≠ R) and ask:
    - Does every shortest A→B path pass through some interior bedroom?

    If yes AND R is one of the interior bedrooms on those paths, flag R.

    Implementation:
    - For each (A, B) pair, compute (any_uses, all_use) per the helper.
    - If all_use == True (no bedroom-avoiding alternate exists), find
      WHICH bedrooms appear as interior nodes on a canonical (lex-ASC)
      shortest path. Each such bedroom R gets flagged (deduplicated by
      room_id).

    Complexity: O(V) pairs × O(V+E) BFS = O(V²·(V+E)). For V ≤ 15 this
    is bounded at ~5000 ops — well within budget.
    """
    flags: list[CirculationFlag] = []
    nodes = topology.nodes
    bedroom_set = frozenset(
        r for r in nodes
        if _is_bedroom(category_index.get(r, ""))
    )
    non_bedroom = [r for r in nodes if r not in bedroom_set]
    flagged_bedrooms: set[str] = set()

    if len(bedroom_set) == 0:
        return []  # no bedrooms to flag

    # Build adjacency once for canonical-path reconstruction
    adjacency: dict[str, list[str]] = {r: [] for r in nodes}
    for a, b in topology.edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    for r in adjacency:
        adjacency[r].sort()  # lex-ASC

    for i, A in enumerate(non_bedroom):
        for B in non_bedroom[i + 1:]:
            # A < B lex-ASC; check whether all shortest A→B paths
            # transit a bedroom.
            _any, all_use = _bfs_all_shortest_paths_pass_through(
                topology=topology,
                source=A,
                target=B,
                bedroom_set=bedroom_set,
            )
            if not all_use:
                # An alternate bedroom-avoiding path exists; A5 SKETCH
                # exempts this pair.
                continue
            # Find the canonical lex-ASC BFS shortest path from A to B
            # and collect interior bedrooms.
            path = _canonical_bfs_path(
                adjacency=adjacency, source=A, target=B,
            )
            if not path or len(path) < 3:
                continue
            for interior in path[1:-1]:
                if interior in bedroom_set:
                    flagged_bedrooms.add(interior)

    # Emit one flag per uniquely-flagged bedroom, lex-ASC
    for room_id in sorted(flagged_bedrooms):
        flags.append(CirculationFlag(
            flag_kind=PreferenceCirculationFlagKind.TRANSIT_THROUGH_BEDROOM,
            affected_room_id=room_id,
            severity="info",  # per A10
            explanation_template=(
                f"Room {room_id} (bedroom-category) sits on the only "
                f"shortest path between non-bedroom rooms; family "
                f"members must traverse a private space to cross the "
                f"layout."
            ),
            deduplication_key=f"transit_through_bedroom:{room_id}",
        ))
    return flags


def _canonical_bfs_path(
    *,
    adjacency: dict[str, list[str]],
    source: str,
    target: str,
) -> list[str]:
    """Lex-ASC canonical BFS shortest path from source to target.

    Inv E7: among all shortest paths, choose the one whose vertex
    sequence is lex-ASC smallest. We achieve this by always expanding
    neighbours in lex-ASC order and tracking the LEX-FIRST predecessor
    on the shortest-path DAG.
    """
    if source == target:
        return [source]
    dist: dict[str, int] = {source: 0}
    parent: dict[str, str] = {}
    queue: deque[str] = deque((source,))
    while queue:
        v = queue.popleft()
        if v == target:
            break
        for w in adjacency[v]:  # already lex-ASC
            if w not in dist:
                dist[w] = dist[v] + 1
                parent[w] = v
                queue.append(w)
    if target not in dist:
        return []
    # Reconstruct path
    path: list[str] = []
    cur = target
    while cur != source:
        path.append(cur)
        cur = parent[cur]
    path.append(source)
    path.reverse()
    return path


# =============================================================================
# Detector 5 — PRIVACY_GRADIENT_VIOLATION (Preference)
# =============================================================================

def _detect_privacy_gradient_violation(
    *,
    topology: GraphTopology,
    node_metrics: NodeMetrics,
    category_index: dict[str, str],
) -> list[CirculationFlag]:
    """Per v0.1 § 1.3 PRIVACY_GRADIENT_VIOLATION (Preference).

    A private room (bedroom-category) is SHALLOWER (smaller step-depth)
    than a public room (living/dining/etc.). Violates the public→private
    monotonicity heuristic.

    SKETCH formula at v0.2 (B-C14-PRIVACY-GRADIENT-FORMULA-LOCK pins
    the exact rule at v1.0):
    - For each bedroom B, find the max step_depth among PUBLIC rooms
      (max_public_depth).
    - If depth[B] < max_public_depth → flag B.

    Per A10: severity=info.
    """
    flags: list[CirculationFlag] = []
    depth_lookup = dict(node_metrics.step_depth_from_entry)

    public_depths = [
        depth_lookup[r]
        for r in topology.nodes
        if _is_public(category_index.get(r, ""))
    ]
    if not public_depths:
        return []  # no public rooms to compare against
    max_public_depth = max(public_depths)

    for room_id in topology.nodes:  # lex-ASC
        category = category_index.get(room_id, "")
        if not _is_bedroom(category):
            continue
        if depth_lookup[room_id] < max_public_depth:
            flags.append(CirculationFlag(
                flag_kind=PreferenceCirculationFlagKind.PRIVACY_GRADIENT_VIOLATION,
                affected_room_id=room_id,
                severity="info",
                explanation_template=(
                    f"Room {room_id} (bedroom) at depth "
                    f"{depth_lookup[room_id]} is shallower than the "
                    f"deepest public room (depth {max_public_depth}); "
                    f"public→private monotonicity heuristic violated."
                ),
                deduplication_key=f"privacy_gradient_violation:{room_id}",
            ))
    return flags


# =============================================================================
# Detector 6 — EXCESSIVE_DEPTH (Preference)
# =============================================================================

def _detect_excessive_depth(
    *,
    topology: GraphTopology,
    node_metrics: NodeMetrics,
    config: CirculationConfig,
) -> list[CirculationFlag]:
    """Per v0.1 § 1.3 EXCESSIVE_DEPTH (Preference) + v0.2 A10.

    step_depth_from_entry > config.excessive_depth_threshold emits a
    preference flag. Per A10, default severity=info — a ceremonial-
    sequence home may DESIRABLY produce high depth.
    """
    flags: list[CirculationFlag] = []
    threshold = config.excessive_depth_threshold
    for room_id, depth in node_metrics.step_depth_from_entry:  # lex-ASC
        if depth > threshold:
            flags.append(CirculationFlag(
                flag_kind=PreferenceCirculationFlagKind.EXCESSIVE_DEPTH,
                affected_room_id=room_id,
                severity="info",
                explanation_template=(
                    f"Room {room_id} step-depth {depth} exceeds "
                    f"configured threshold {threshold}; access may be "
                    f"circuitous (or intentionally ceremonial)."
                ),
                deduplication_key=f"excessive_depth:{room_id}",
            ))
    return flags


# =============================================================================
# A6 truncation cap — Inv E13'
# =============================================================================

def _apply_truncation_cap(
    *,
    structural: list[CirculationFlag],
    preference: list[CirculationFlag],
    k: int,
    density_factor: float,
) -> tuple[tuple[CirculationFlag, ...], tuple[CirculationFlag, ...]]:
    """Per v0.2 A6 Inv E13'.

    Cap: len(structural) + len(preference) ≤ k × density_factor.

    When the cap is exceeded, the LAST tuple to overflow gets its last
    slot replaced by a single TRUNCATION_META meta-flag enumerating the
    suppressed kinds.

    Strategy:
    1. Compute cap = floor(k × density_factor) (integer cap; 0.75 × 4 = 3).
    2. If total ≤ cap → no truncation, return as-is.
    3. Else: we have `over = total - cap` excess flags. The cap permits
       (cap - 1) "real" flags plus 1 TRUNCATION_META slot — total cap.
       The TRUNCATION_META goes to whichever tuple was over-cap (the
       preference tuple if it was the one to push us over; otherwise
       the structural tuple).

    Concretely the algorithm preserves structural flags first (they are
    closer to universal pathologies per A4), then preference flags.

    We pack:
    - Keep all structural up to `cap - 1` "real" slots (if struct fits
      under cap-1, all kept; otherwise truncate)
    - Then fill preference up to total cap - 1 real slots
    - Place TRUNCATION_META in whichever tuple overflowed

    Edge cases:
    - cap == 0 (e.g., k=1, density=0.75 → 0.75 → floor 0): everything
      truncated; meta-flag goes to structural (the typically-larger tuple).
    - cap == 1: 1 real slot total; we keep 0 real + 1 meta. The first
      structural is replaced by meta if any structural exists; else
      first preference replaced.
    """
    total = len(structural) + len(preference)
    # Integer cap. Always at least 0.
    cap = int(k * density_factor)
    cap = max(0, cap)

    if total <= cap:
        return (tuple(structural), tuple(preference))

    # Truncation needed. Allocate `cap - 1` real slots if cap ≥ 1;
    # 1 meta-flag slot. If cap == 0, we have zero slots total — but
    # we still emit one TRUNCATION_META as a signal (the meta-flag is
    # the only way downstream knows truncation happened, so it MUST
    # appear).

    # Decide which tuple gets the meta-flag: the tuple that overflows.
    # Try filling structural first up to `cap - 1` real slots (or up to
    # its length if smaller). Then preference up to the remaining
    # `cap - 1 - struct_kept` real slots.

    real_slots = max(0, cap - 1)
    struct_kept = min(len(structural), real_slots)
    pref_kept = min(len(preference), real_slots - struct_kept)

    # The over-cap tuple: whichever has un-kept flags. Prefer the
    # preference tuple to absorb the meta (preserving structural
    # density), unless preference fits entirely and structural is the
    # one being truncated.
    pref_suppressed_count = len(preference) - pref_kept
    struct_suppressed_count = len(structural) - struct_kept

    suppressed_kinds: list[str] = []
    for f in structural[struct_kept:]:
        suppressed_kinds.append(str(f.flag_kind))
    for f in preference[pref_kept:]:
        suppressed_kinds.append(str(f.flag_kind))
    # Stable enumeration: dedupe, lex-ASC sort
    unique_kinds = sorted(set(suppressed_kinds))
    total_suppressed = struct_suppressed_count + pref_suppressed_count

    if pref_suppressed_count > 0:
        # Place meta in preference tuple
        meta_in_preference = CirculationFlag(
            flag_kind=PreferenceCirculationFlagKind.TRUNCATION_META,
            affected_room_id="",
            severity="info",
            explanation_template=(
                f"{total_suppressed} flag(s) suppressed by density cap "
                f"(kinds: {', '.join(unique_kinds)})."
            ),
            deduplication_key=f"truncation_meta:preference:{total_suppressed}",
        )
        return (
            tuple(structural[:struct_kept]),
            tuple(preference[:pref_kept]) + (meta_in_preference,),
        )
    else:
        # All preference fit; structural is the one truncated
        meta_in_structural = CirculationFlag(
            flag_kind=StructuralCirculationFlagKind.TRUNCATION_META,
            affected_room_id="",
            severity="info",
            explanation_template=(
                f"{total_suppressed} flag(s) suppressed by density cap "
                f"(kinds: {', '.join(unique_kinds)})."
            ),
            deduplication_key=f"truncation_meta:structural:{total_suppressed}",
        )
        return (
            tuple(structural[:struct_kept]) + (meta_in_structural,),
            tuple(preference[:pref_kept]),
        )


# =============================================================================
# Phase δ main entry
# =============================================================================

def emit_flags(
    *,
    topology: GraphTopology,
    node_metrics: NodeMetrics,
    metadata: tuple[RoomMetadata, ...],
    config: CirculationConfig,
    category_coverage: float,
    main_entry_room_id: str,
) -> EmittedFlags:
    """Phase δ: run all flag-kind detectors + apply A6 truncation cap.

    Per v0.2 LOCKED § 3 Phase δ + A4 + A5 + A6 + A8 + A10.

    Inputs:
      topology: GraphTopology from Phase α
      node_metrics: NodeMetrics from Phase β
      metadata: per-room metadata (categories needed for type-aware flags)
      config: CirculationConfig (thresholds, density factor)
      category_coverage: ∈ [0, 1] from Phase ζ — passed in so this
        module remains pure (no category-coverage computation here)

    Returns:
      EmittedFlags — frozen, with structural + preference flag tuples
      respecting Inv E13' cap.

    All detectors iterate rooms in lex-ASC order for Inv E7 determinism.
    Detector invocation order is FIXED (per § 3 Phase δ statement
    "iterate in fixed order, replay-deterministic"):

      Structural:  bottleneck → dead_end → category_coverage_low
      Preference:  transit_bedroom → privacy_gradient → excessive_depth
    """
    category_index = _build_category_index(metadata)

    # ── Structural detectors ───────────────────────────────────────
    # Order: category_coverage_low FIRST (it's a meta-signal about
    # input quality; if it fires, downstream consumers should verify
    # categorization before trusting OTHER flags). Truncation cap
    # therefore prefers to preserve it.
    structural: list[CirculationFlag] = []
    structural.extend(_detect_category_coverage_low(
        category_coverage=category_coverage,
        threshold=config.category_coverage_low_threshold,
    ))
    structural.extend(_detect_bottleneck_concentration(
        topology=topology,
        node_metrics=node_metrics,
        category_index=category_index,
        config=config,
    ))
    structural.extend(_detect_dead_end_isolation(
        topology=topology,
        node_metrics=node_metrics,
        category_index=category_index,
        main_entry_room_id=main_entry_room_id,
    ))

    # ── Preference detectors ──────────────────────────────────────
    preference: list[CirculationFlag] = []
    preference.extend(_detect_transit_through_bedroom(
        topology=topology,
        category_index=category_index,
    ))
    preference.extend(_detect_privacy_gradient_violation(
        topology=topology,
        node_metrics=node_metrics,
        category_index=category_index,
    ))
    preference.extend(_detect_excessive_depth(
        topology=topology,
        node_metrics=node_metrics,
        config=config,
    ))

    # ── A6 truncation cap (Inv E13') ──────────────────────────────
    structural_capped, preference_capped = _apply_truncation_cap(
        structural=structural,
        preference=preference,
        k=len(topology.nodes),
        density_factor=config.flag_density_factor,
    )

    return EmittedFlags(
        structural_flags=structural_capped,
        preference_flags=preference_capped,
    )


__all__ = [
    "EmittedFlags",
    "emit_flags",
]
