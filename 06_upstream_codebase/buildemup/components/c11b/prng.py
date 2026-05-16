"""
BuildemUp — Component 11b — PRNG seed derivation
=================================================

Per SPEC v1.1 LOCKED § 0.7 (D-PR-1, D-PR-2) + Inv 29.

The derivation is PURE-DETERMINISTIC: same ``master_seed`` +
``topology_index`` + ``topology_signature`` → byte-equal PRNG stream
(Inv 29 TIER-1 conjunction with same env tuple + same tie-break rule).

We use ``numpy.random.SeedSequence`` explicitly per NumPy's recommended
practice for reproducible spawning — keeps future parallel NSGA-II
(B-NEW-Z) clean.
"""
from __future__ import annotations

import hashlib

import numpy as np


def derive_per_topology_seed(
    master_seed: int,
    topology_index: int,
    topology_signature: str,
) -> int:
    """Pure deterministic derivation per Inv 29.

    SHA256 over the canonical concatenation, truncated to 32 bits so
    ``SeedSequence`` accepts it cleanly. Any int up to 2^32 is fine;
    32 bits keeps logs readable.
    """
    payload = f"{master_seed}|{topology_index}|{topology_signature}"
    h = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(h[:4], byteorder="big")


def _build_per_topology_rng(
    master_seed: int,
    topology_index: int,
    topology_signature: str,
) -> np.random.Generator:
    """Build a per-topology PRNG via explicit ``SeedSequence`` for
    NumPy version stability.

    ``numpy.random.default_rng(int)`` semantics have been stable since
    NumPy 1.17, but NumPy's recommended practice is to construct via
    ``SeedSequence`` explicitly to make intent unambiguous and to enable
    reproducible spawning in future parallel implementations (B-NEW-Z
    deterministic-parallel-NSGA-II).
    """
    seed = derive_per_topology_seed(master_seed, topology_index, topology_signature)
    seed_seq = np.random.SeedSequence(seed)
    return np.random.default_rng(seed_seq)


__all__ = [
    "derive_per_topology_seed",
    "_build_per_topology_rng",
]
