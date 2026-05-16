"""
BuildemUp† — In-Memory Insights Buffer (v0.7.2)
===================================================

Per v0.7.1 review: surface "top 3 repeated warnings" proactively in
output, so users benefit from patterns seen in earlier executions.

Scope (deliberately narrow):
  ✓ In-memory ring buffer of recent execution signatures
  ✓ Aggregates top-N recurring warnings
  ✓ Returns None if buffer too small for meaningful patterns
  ✓ Thread-safe for concurrent requests (Railway deployment)

NOT in scope (v2):
  ✗ Persistent storage across deployments
  ✗ ML-based anomaly detection
  ✗ Cross-user correlation
  ✗ Dashboard / analytics UI

Railway notes:
  The buffer resets on every deployment. This is fine — patterns
  rebuild within the first 20-50 executions. If persistent insights
  become important, upgrade to file-backed storage in v0.8 with
  proper Railway volume mount.

†= placeholder name marker.
"""
from __future__ import annotations
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any


# Buffer size: keep the last 200 executions in memory.
# Small enough to be fast, large enough to surface real patterns.
# At 200 entries × ~1 KB each = ~200 KB RAM. Trivial for Railway.
_DEFAULT_BUFFER_SIZE = 200

# Minimum executions needed before we surface patterns.
# Below this, "top warnings" is noise, not signal.
_MIN_EXECUTIONS_FOR_INSIGHTS = 10

# Minimum occurrence rate to be considered "common".
# A warning must appear in ≥ 20% of executions to count as a pattern.
_MIN_OCCURRENCE_RATE = 0.20


@dataclass(frozen=True)
class ExecutionSignature:
    """A lightweight fingerprint of one execution for pattern analysis.

    Deliberately small — we don't store PII, only patterns.
    """
    timestamp: str                          # ISO timestamp
    city: str                               # lowercased
    seismic_zone: str                       # "II", "III", etc.
    floors_above_ground: int
    warnings: tuple[str, ...]               # first 80 chars each
    frame_sanity_result: str                # SAFE/WARNING/FAIL
    global_stability_result: str            # SAFE/WARNING/FAIL
    has_refusal: bool
    cost_bucket_lakhs: int                  # rounded to lakh
    validation_status_variant: str          # "standard" | "user_claim"


@dataclass(frozen=True)
class ProactiveGuidance:
    """Top-N pattern finding for proactive user guidance."""
    total_executions_seen: int              # How much signal we have
    top_warnings: tuple[tuple[str, int], ...]  # (warning_text, count)
    top_cities: tuple[tuple[str, int], ...]
    frame_sanity_distribution: dict[str, int]
    global_stability_distribution: dict[str, int]
    user_message: str                       # Rendered for display

    @property
    def has_meaningful_signal(self) -> bool:
        """True if we have enough data to surface patterns."""
        return self.total_executions_seen >= _MIN_EXECUTIONS_FOR_INSIGHTS


class InsightsBuffer:
    """Thread-safe in-memory ring buffer for recent executions.

    Usage:
      buffer = get_insights_buffer()           # singleton
      buffer.record(signature)                  # after each execute()
      guidance = buffer.get_proactive_guidance()  # before explain()
    """

    def __init__(self, maxsize: int = _DEFAULT_BUFFER_SIZE):
        self._deque: deque[ExecutionSignature] = deque(maxlen=maxsize)
        self._lock = Lock()
        self._maxsize = maxsize

    def record(self, signature: ExecutionSignature) -> None:
        """Record one execution signature. Thread-safe."""
        with self._lock:
            self._deque.append(signature)

    def size(self) -> int:
        """Current buffer size."""
        with self._lock:
            return len(self._deque)

    def clear(self) -> None:
        """Reset buffer. Used by tests."""
        with self._lock:
            self._deque.clear()

    def snapshot(self) -> tuple[ExecutionSignature, ...]:
        """Return immutable snapshot of current contents."""
        with self._lock:
            return tuple(self._deque)

    def get_proactive_guidance(self) -> ProactiveGuidance:
        """Compute top-N patterns from buffer contents.

        Returns ProactiveGuidance with meaningful signal flag.
        Safe to call on empty buffer — returns zero-count guidance.
        """
        snapshot = self.snapshot()
        total = len(snapshot)

        if total == 0:
            return ProactiveGuidance(
                total_executions_seen=0,
                top_warnings=(),
                top_cities=(),
                frame_sanity_distribution={},
                global_stability_distribution={},
                user_message="No execution history yet.",
            )

        # Count warnings across all signatures
        warning_counter: Counter = Counter()
        for sig in snapshot:
            for w in sig.warnings:
                # Normalise: first 80 chars as the dedup key
                warning_counter[w[:80]] += 1

        # Only warnings that appear in ≥ MIN_OCCURRENCE_RATE of executions
        threshold = max(2, int(total * _MIN_OCCURRENCE_RATE))
        common_warnings = [
            (w, c) for w, c in warning_counter.most_common()
            if c >= threshold
        ][:3]    # top 3

        # City frequency
        city_counter: Counter = Counter(sig.city for sig in snapshot)
        top_cities = tuple(city_counter.most_common(3))

        # Frame sanity + global stability distributions
        frame_dist = dict(Counter(sig.frame_sanity_result for sig in snapshot))
        drift_dist = dict(Counter(sig.global_stability_result for sig in snapshot))

        # Build user-facing message
        user_message = _format_guidance_message(
            total=total,
            common_warnings=common_warnings,
            top_cities=top_cities,
            frame_dist=frame_dist,
            drift_dist=drift_dist,
        )

        return ProactiveGuidance(
            total_executions_seen=total,
            top_warnings=tuple(common_warnings),
            top_cities=top_cities,
            frame_sanity_distribution=frame_dist,
            global_stability_distribution=drift_dist,
            user_message=user_message,
        )


def _format_guidance_message(
    total: int,
    common_warnings: list[tuple[str, int]],
    top_cities: tuple,
    frame_dist: dict,
    drift_dist: dict,
) -> str:
    """Render proactive guidance into user-facing text.

    If no meaningful signal, returns a short "no patterns yet" message.
    """
    if total < _MIN_EXECUTIONS_FOR_INSIGHTS:
        return (
            f"Not enough history yet to surface patterns "
            f"({total}/{_MIN_EXECUTIONS_FOR_INSIGHTS} minimum). "
            f"Proactive guidance activates once more plans are processed."
        )

    lines = [
        f"Based on {total} similar recent plans, users commonly encounter:",
    ]

    if common_warnings:
        for i, (warning, count) in enumerate(common_warnings, 1):
            pct = count / total * 100
            lines.append(f"  {i}. {warning} ({pct:.0f}% of plans)")
    else:
        lines.append("  No recurring warnings in recent plans.")

    # Frame sanity distribution (if meaningful spread)
    total_frame = sum(frame_dist.values())
    if total_frame > 0:
        safe = frame_dist.get("SAFE", 0)
        safe_pct = safe / total_frame * 100
        if safe_pct < 80:
            # If a lot of plans have issues, flag it
            warn_fail = total_frame - safe
            lines.append(
                f"\nNote: {warn_fail} of {total_frame} recent plans had "
                f"frame sanity issues (WARNING or FAIL). Confirm column "
                f"sizing and moments with your engineer."
            )

    return "\n".join(lines)


# ─── Singleton access (process-wide, per deployment) ─────────────────────
_SINGLETON: InsightsBuffer | None = None
_SINGLETON_LOCK = Lock()


def get_insights_buffer() -> InsightsBuffer:
    """Return the process-wide insights buffer.

    On Railway this resets when the deployment restarts — that's fine.
    Patterns rebuild in the first ~10 executions.
    """
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            if _SINGLETON is None:
                _SINGLETON = InsightsBuffer()
    return _SINGLETON


def reset_insights_buffer_for_testing() -> None:
    """Reset the singleton. ONLY for tests."""
    global _SINGLETON
    with _SINGLETON_LOCK:
        _SINGLETON = None


# ─── Helper: build signature from execution result ───────────────────────
def build_signature_from_result(
    inp: Any,
    result: Any,
    has_refusal: bool = False,
) -> ExecutionSignature:
    """Build an ExecutionSignature from a Component 7 input + output.

    Uses getattr with safe defaults so it works across versions and for
    both successful + refused executions.
    """
    # Validation status variant (standard / user-claim)
    status_str = getattr(result, "validation_status", "")
    variant = (
        "user_claim" if "UNVERIFIED" in status_str or "claim" in status_str.lower()
        else "standard"
    )

    # Cost bucket in lakhs (rounded) — for privacy, bucketed not exact
    cost_bucket = 0
    try:
        cost = getattr(result, "cost", None)
        if cost is not None:
            cost_value = getattr(cost, "exact_value", 0)
            cost_bucket = int(round(cost_value / 100_000))
    except Exception:
        pass

    # Extract frame sanity result if present
    frame_result = "UNKNOWN"
    try:
        fs = getattr(result, "frame_sanity", None)
        if fs is not None:
            frame_result = fs.overall_result.value
    except Exception:
        pass

    # Extract global stability result if present
    drift_result = "UNKNOWN"
    try:
        gs = getattr(result, "global_stability", None)
        if gs is not None:
            drift_result = gs.overall_result.value
    except Exception:
        pass

    # Warnings — take first 10 to bound memory usage
    warnings_raw = getattr(result, "all_warnings", []) or []
    # Truncate each warning to 80 chars and take first 10
    warnings_clean = tuple(str(w)[:80] for w in warnings_raw[:10])

    return ExecutionSignature(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        city=str(getattr(inp, "city", "unknown")).lower(),
        seismic_zone=str(getattr(inp, "seismic_zone", "II")),
        floors_above_ground=int(getattr(inp, "floors_above_ground", 0)),
        warnings=warnings_clean,
        frame_sanity_result=frame_result,
        global_stability_result=drift_result,
        has_refusal=has_refusal,
        cost_bucket_lakhs=cost_bucket,
        validation_status_variant=variant,
    )
