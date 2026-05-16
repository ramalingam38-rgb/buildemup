"""C16 phase pipeline.

Per the v0.5 LOCKED spec § 3:
    Phase α — geometric envelope assembly
    Phase β — door/window/finish scheduling
    Phase γ — working drawing assembly
    Phase δ — permit drawing assembly
    Phase ε — compliance attestation packaging
    Phase ζ — bundle assembly + signature stamping

Each phase is a pure function: input → output, no side effects. The
orchestrator wires them in order, handles per-phase failures, and
emits the final DualDrawingBundle.
"""
