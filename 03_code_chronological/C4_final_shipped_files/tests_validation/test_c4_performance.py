"""Tier-1 perf test for C4: derive() under 3ms typical (v0.7 walk #6).

Per SPEC v0.7 LOCKED § 14.4. Relaxed from v0.6's 1ms cap to absorb CI
runner variability while still catching meaningful regressions.

Cap evolution:
  v0.5: 10  ms (very loose; ~666× current p95)
  v0.6:  1  ms (tight;       ~66× current p95)
  v0.7:  3  ms (balanced;   ~200× current p95)

S29 measured baseline (1000 warmed calls on dev host):
  min:   0.009ms     p50:   0.010ms     p95:   0.015ms
  p99:   0.031ms     max:   0.064ms     mean:  0.011ms

Why 3 ms (not 1 ms):
  - Typical CI runners are 5-15× slower than a dev host. p95 on a slow
    CI runner could push to ~0.15-0.25ms — still well under 3 ms.
  - 1 ms cap creates flake risk if a CI runner has competing load.
  - 3 ms still catches a 200× regression — i.e., any change that adds
    accidental I/O, network calls, or O(n²) loops will trip the test.
  - Configurable-per-environment is over-engineering for current scale
    (single-developer project, no CI yet).
"""
from __future__ import annotations

import time

from buildemup.components.c04 import derive
from buildemup.tests.validation._c4_fixtures import chennai_30x40, make_brief


def test_derive_completes_under_3ms_for_typical_plot():
    """1000-call P95 must beat 3.0 ms.

    Sample size is 1000 (was 100 in v0.5) for tighter p95 confidence.
    """
    brief = make_brief(chennai_30x40())

    # Warm up — avoid first-call import / JIT effects skewing the sample.
    for _ in range(50):
        derive(brief, now=1.0)

    samples_ms: list[float] = []
    for _ in range(1000):
        t0 = time.perf_counter()
        derive(brief, now=1.0)
        samples_ms.append((time.perf_counter() - t0) * 1000.0)

    samples_ms.sort()
    p95 = samples_ms[949]   # 95th percentile of 1000 samples (index 949)

    assert p95 < 3.0, (
        f"p95 derive() time = {p95:.3f}ms — exceeds 3.0ms cap. "
        f"min={samples_ms[0]:.3f}ms, p50={samples_ms[499]:.3f}ms, "
        f"p99={samples_ms[989]:.3f}ms, max={samples_ms[-1]:.3f}ms"
    )
