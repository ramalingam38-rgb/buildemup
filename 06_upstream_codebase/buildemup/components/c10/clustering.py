"""
BuildemUp† — Component 10 — Phase 2 (Wet-room clustering) module.

Per C10 SPEC v1.0 LOCKED § 3 Phase 2: deterministic greedy partition with
common-feasible-wall merge predicate. Tie-break by cluster_id lex ASC.

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Callable, Iterable


def cluster_wet_rooms(
    wet_rooms: Iterable[str],
    *,
    hard_edges: Iterable[tuple[str, str]] = (),
    hard_anti_edges: Iterable[tuple[str, str]] = (),
    acceptable_wall_sets: dict[str, tuple[str, ...]] | None = None,
    capacity_check: "Callable[[list[str], set[str]], bool] | None" = None,
) -> tuple[dict[str, tuple[str, ...]], dict[str, set[str]]]:
    """Phase 2 — produce final cluster composition.

    Algorithm (per § 3 Phase 2 carried from v0.4 + v0.6 verbatim):
      1. Seed: one cluster per wet room. cluster_id = "cluster_{room_id}",
         seeded in lex-ASC of room_id (deterministic).
      2. Apply HARD edges first by merging the two endpoints into one
         cluster (lex-ASC cluster_id wins as canonical id).
      3. Merge step (common-feasible-wall predicate):
            For each pair (C_i, C_j) in lex-ASC of (cluster_id_i, cluster_id_j):
              overlap_set = intersection(acceptable_wall_sets[r] for r in
                                         C_i ∪ C_j)
              merge if overlap_set non-empty AND no HARD-anti edge spans
                    the merged set AND (capacity_check is None OR
                    capacity_check(merged_members, overlap_set) is True).
         Tie-break: smaller cluster_id wins.
      4. Iterate until a full pass produces no merges.

    Args:
        wet_rooms: iterable of room_id strings.
        hard_edges: pairs (a, b) that MUST share a cluster.
        hard_anti_edges: pairs (a, b) that MUST NOT share a cluster.
        acceptable_wall_sets: required for merge predicate; if None
            treated as empty (no merges beyond HARD).
        capacity_check: optional predicate(merged_member_room_ids,
            overlap_walls) -> bool. When provided, merges that fail this
            check are vetoed. Lets callers prevent Phase-2 from creating
            clusters that Phase 3 cannot serve (Q44 capacity weight).

    Returns:
        (clusters, cluster_acceptable_walls) where:
          - clusters maps cluster_id -> tuple of sorted room_ids
          - cluster_acceptable_walls maps cluster_id -> set of wall_ids
            that ALL cluster members agree on
    """
    rooms = sorted(set(wet_rooms))
    if acceptable_wall_sets is None:
        acceptable_wall_sets = {}
    hard_edges = list(hard_edges)
    hard_anti_edges = [tuple(sorted(p)) for p in hard_anti_edges]

    # Initial: one cluster per room.
    clusters: dict[str, list[str]] = {
        f"cluster_{r}": [r] for r in rooms
    }

    # Apply HARD edges.
    for a, b in hard_edges:
        ca = _find_cluster_for(a, clusters)
        cb = _find_cluster_for(b, clusters)
        if ca is None or cb is None or ca == cb:
            continue
        winner = min(ca, cb)
        loser = max(ca, cb)
        clusters[winner].extend(clusters[loser])
        del clusters[loser]

    # Iterative overlap-merge.
    changed = True
    while changed:
        changed = False
        ids = sorted(clusters.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                ci_id, cj_id = ids[i], ids[j]
                if ci_id not in clusters or cj_id not in clusters:
                    continue
                members = clusters[ci_id] + clusters[cj_id]
                # Forbid merge if a HARD-anti edge straddles.
                if any(
                    (a in clusters[ci_id] and b in clusters[cj_id])
                    or (b in clusters[ci_id] and a in clusters[cj_id])
                    for a, b in hard_anti_edges
                ):
                    continue
                overlap = _overlap_set(members, acceptable_wall_sets)
                if not overlap:
                    continue
                # Capacity-aware predicate: refuse merge if Phase 3 would
                # be unable to serve the merged cluster on any overlap wall.
                if capacity_check is not None and not capacity_check(
                    members, overlap,
                ):
                    continue
                # Merge: smaller id wins.
                winner = min(ci_id, cj_id)
                loser = max(ci_id, cj_id)
                clusters[winner].extend(clusters[loser])
                del clusters[loser]
                changed = True
                break
            if changed:
                break

    # Final shape: tuple of sorted room_ids, set of overlap walls.
    final_clusters: dict[str, tuple[str, ...]] = {
        cid: tuple(sorted(set(rids))) for cid, rids in clusters.items()
    }
    cluster_walls: dict[str, set[str]] = {
        cid: _overlap_set(rids, acceptable_wall_sets)
        for cid, rids in final_clusters.items()
    }
    return final_clusters, cluster_walls


def _find_cluster_for(
    room_id: str, clusters: dict[str, list[str]],
) -> str | None:
    for cid, rids in clusters.items():
        if room_id in rids:
            return cid
    return None


def _overlap_set(
    members: list[str],
    acceptable_wall_sets: dict[str, tuple[str, ...]],
) -> set[str]:
    if not members:
        return set()
    sets = [set(acceptable_wall_sets.get(m, ())) for m in members]
    out = sets[0]
    for s in sets[1:]:
        out = out & s
        if not out:
            break
    return out


__all__ = ["cluster_wet_rooms"]
