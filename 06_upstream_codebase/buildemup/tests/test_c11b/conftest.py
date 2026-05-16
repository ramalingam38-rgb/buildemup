"""C11b test fixtures.

C11b's orchestrator depends on C11a's ``derive_canonical_signature``,
which walks a deeply-nested attribute path on the source artifact
(``room_sized_candidate.corridor_designed_candidate.oriented_candidate
.topology_candidate.kind``). Building fake source artifacts that
satisfy that contract is brittle and out-of-scope for C11b-only tests.

This autouse fixture monkeypatches the signature derivation at the
phase1 module level to return a stable hash of the artifact identity.
Tests that DO want to exercise the real C11a signature path can use
the ``real_signature`` marker or import from C11a directly.
"""
from __future__ import annotations

import hashlib

import pytest


@pytest.fixture(autouse=True)
def _stub_canonical_signature(request, monkeypatch):
    """Monkeypatch ``derive_canonical_signature`` in C11b's phase1
    module so orchestrator tests with fake artifacts pass cleanly.

    Skip this fixture for tests marked ``real_signature``.
    """
    if "real_signature" in request.keywords:
        return
    import buildemup.components.c11b.phase1 as phase1_mod

    def _stub(artifact):
        # Stable hash of identity — different artifacts → different sigs.
        return hashlib.sha256(repr(id(artifact)).encode()).hexdigest()[:32]

    monkeypatch.setattr(phase1_mod, "derive_canonical_signature", _stub)
