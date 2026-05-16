#!/usr/bin/env python3
"""
BuildemUp — Component 15 — Cultural Profile Parity Audit
============================================================

Per LOCK-mandatory B-C15-CULTURAL-PROFILE-COVERAGE (S48 walk #1 item 4
scope extension).

Generates a per-profile dimension coverage matrix and a divergence
diff to surface profile-evolution asymmetry. Helps maintainers ensure
profiles don't drift unevenly (e.g., Tamil multigen gets continually
refined while compact urban stays bare).

This tool DOES NOT modify any artifact. It is a read-only auditor.

Outputs:
  - Per-profile severity signature on every (check_id, status) pair
    where any profile diverges from defaults.
  - Divergence diff: which (check_id, status) pairs have ≥1
    profile-specific override vs. all-default.
  - Profile content audit: which checks each profile cares more about
    than default.

Usage:
  python3 buildemup/tools/cultural_profile_parity_audit.py [--check-id PID]

Output is human-readable + machine-parseable JSON tail at end.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

from buildemup.components.c15.contracts import CulturalProfile
from buildemup.components.c15.schema import CheckSeverity, CheckStatus
from buildemup.components.c15.severity_rule_table import (
    SEVERITY_RULE_TABLE_V1,
    lookup_severity,
)


def gather_all_check_ids() -> frozenset[str]:
    """All check_ids referenced in the severity rule table."""
    return frozenset(r.check_id for r in SEVERITY_RULE_TABLE_V1)


def profile_severity_matrix(
) -> dict[CulturalProfile, dict[tuple[str, CheckStatus], CheckSeverity]]:
    """For each profile, for each (check_id, applicable status),
    record the looked-up severity."""
    profiles = tuple(CulturalProfile)
    cids = sorted(gather_all_check_ids())
    statuses = (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL)
    out: dict[CulturalProfile, dict[tuple[str, CheckStatus], CheckSeverity]] = {}
    for prof in profiles:
        per_pair: dict[tuple[str, CheckStatus], CheckSeverity] = {}
        for cid in cids:
            for st in statuses:
                try:
                    per_pair[(cid, st)] = lookup_severity(
                        SEVERITY_RULE_TABLE_V1,
                        check_id=cid, status=st, cultural_profile=prof,
                    )
                except Exception:
                    # No rule for this (cid, status). Skip.
                    pass
        out[prof] = per_pair
    return out


def find_divergence_pairs(
    matrix: dict[CulturalProfile, dict[tuple[str, CheckStatus], CheckSeverity]],
) -> list[tuple[str, CheckStatus]]:
    """(check_id, status) pairs where at least 2 profiles disagree."""
    pairs_by_severities: dict[tuple[str, CheckStatus], set[CheckSeverity]] = defaultdict(set)
    for prof_data in matrix.values():
        for pair, sev in prof_data.items():
            pairs_by_severities[pair].add(sev)
    return sorted(p for p, sevs in pairs_by_severities.items() if len(sevs) > 1)


def profile_coverage_matrix(
) -> dict[CulturalProfile, dict[int, dict[str, int]]]:
    """For each profile, for each dimension 1-10, count rules + check
    coverage shape. Note: this is severity-rule coverage, not check
    coverage."""
    out: dict[CulturalProfile, dict[int, dict[str, int]]] = {}
    for prof in CulturalProfile:
        dim_data: dict[int, dict[str, int]] = {}
        for dim in range(1, 11):
            override_count = 0
            for r in SEVERITY_RULE_TABLE_V1:
                if r.cultural_profile is prof and r.check_id.startswith(f"P{dim}."):
                    override_count += 1
            dim_data[dim] = {"profile_specific_overrides": override_count}
        out[prof] = dim_data
    return out


def print_human_readable() -> None:
    print("=" * 72)
    print("Cultural Profile Parity Audit — C15 v1 LOCK candidate")
    print("=" * 72)
    print()

    # 1. Divergence pairs
    matrix = profile_severity_matrix()
    div_pairs = find_divergence_pairs(matrix)
    print(f"1. Divergence pairs (where ≥2 profiles disagree on severity):")
    print(f"   Total: {len(div_pairs)}")
    for cid, st in div_pairs:
        print(f"   {cid:8s} {st.value:6s}")
    print()

    # 2. Per-profile signatures on divergence pairs
    print(f"2. Per-profile severity signatures on the {len(div_pairs)} "
          f"divergence pairs:")
    for prof in CulturalProfile:
        sig = tuple(matrix[prof].get((cid, st)) for (cid, st) in div_pairs)
        sig_str = " ".join(s.value[:3] if s else "---" for s in sig)
        print(f"   {prof.value:30s} {sig_str}")
    print()

    # 3. Profile parity — count overrides per profile per dim
    print("3. Profile-specific override count per dimension:")
    cov = profile_coverage_matrix()
    print(f"   {'Profile':30s} {'D1 D2 D3 D5 D6 D7':18s}  TOTAL")
    for prof in CulturalProfile:
        dim_counts = cov[prof]
        cells = " ".join(
            f"{dim_counts[d]['profile_specific_overrides']:2d}"
            for d in (1, 2, 3, 5, 6, 7)
        )
        total = sum(d["profile_specific_overrides"] for d in dim_counts.values())
        print(f"   {prof.value:30s} {cells}  {total:5d}")
    print()

    # 4. A3 LOCK signature audit
    print("4. A3 LOCK requirement — ≥3 distinct severity signatures across profiles:")
    sig_set: set[tuple] = set()
    for prof in CulturalProfile:
        sig = tuple(matrix[prof].get((cid, st)) for (cid, st) in div_pairs)
        sig_set.add(sig)
    status = "PASS" if len(sig_set) >= 3 else "FAIL"
    print(f"   Distinct signatures: {len(sig_set)} → {status}")
    print()


def emit_json_tail() -> None:
    matrix = profile_severity_matrix()
    div_pairs = find_divergence_pairs(matrix)
    cov = profile_coverage_matrix()

    sig_set: set[tuple] = set()
    for prof in CulturalProfile:
        sig = tuple(matrix[prof].get((cid, st)) for (cid, st) in div_pairs)
        sig_set.add(sig)

    summary = {
        "divergence_pair_count": len(div_pairs),
        "divergence_pairs": [
            {"check_id": cid, "status": st.value} for (cid, st) in div_pairs
        ],
        "distinct_signatures": len(sig_set),
        "a3_lock_pass": len(sig_set) >= 3,
        "profile_override_counts": {
            prof.value: sum(d["profile_specific_overrides"] for d in cov[prof].values())
            for prof in CulturalProfile
        },
    }
    print("\n=== JSON SUMMARY ===")
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> int:
    print_human_readable()
    emit_json_tail()
    return 0


if __name__ == "__main__":
    sys.exit(main())
