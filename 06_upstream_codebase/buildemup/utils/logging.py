"""
BuildemUp† — Structured Logging
=================================

Every pipeline run gets a unique trace_id. Every log entry includes
trace_id + component + event_type + structured data.

This makes debugging possible: "user X got weird layout, trace_id ABC123"
→ grep logs for ABC123 → see every decision made.

Usage:
  from buildemup.utils.logging import get_logger, new_trace_id

  trace_id = new_trace_id()
  logger = get_logger("component7.grid_generator", trace_id)
  logger.info("grid_generated", bay_x=4.0, bay_y=3.6, columns=12)

Logs are structured as JSON lines for easy grep/filter.

†= placeholder name marker.
"""
from __future__ import annotations
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any


# Configure root logger to emit structured JSON lines
_CONFIGURED = False


def _configure_root_logger():
    """One-time root logger setup.

    Default behavior: in-memory trace capture only, NO console output.
    Console JSON output is opt-in via enable_console_logging().
    This keeps the user-facing output clean.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger("buildemup")
    root.setLevel(logging.INFO)

    # Remove any existing handlers
    for h in root.handlers[:]:
        root.removeHandler(h)

    # No console handler by default. Trace handler installed separately.
    # Use a NullHandler so logging doesn't complain about no handlers.
    root.addHandler(logging.NullHandler())
    root.propagate = False

    _CONFIGURED = True


def enable_console_logging():
    """Opt-in: enable JSON-line console output for debugging.

    By default, BuildemUp suppresses log output to keep user-facing
    text clean. Call this in dev/debug scenarios.
    """
    root = logging.getLogger("buildemup")
    # Avoid adding duplicate console handlers
    has_console = any(
        isinstance(h, logging.StreamHandler)
        and not isinstance(h, _MemoryTraceHandler)
        and not isinstance(h, logging.NullHandler)
        for h in root.handlers
    )
    if has_console:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONLineFormatter())
    root.addHandler(handler)


class _JSONLineFormatter(logging.Formatter):
    """Formats each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "component": record.name,
            "event": record.getMessage(),
        }
        # Extra fields set via `logger.info("msg", extra={"key": val})`
        if hasattr(record, "trace_id"):
            data["trace_id"] = record.trace_id
        if hasattr(record, "data"):
            data["data"] = record.data
        return json.dumps(data, default=str)


def new_trace_id() -> str:
    """Generate a new unique trace ID for a pipeline run."""
    return uuid.uuid4().hex[:12]


class TracedLogger:
    """Logger wrapper that always includes trace_id.

    Use this instead of stdlib logger directly.
    """

    def __init__(self, name: str, trace_id: str):
        _configure_root_logger()
        self._logger = logging.getLogger(f"buildemup.{name}")
        self.trace_id = trace_id

    def info(self, event: str, **data: Any):
        self._log(logging.INFO, event, data)

    def warning(self, event: str, **data: Any):
        self._log(logging.WARNING, event, data)

    def error(self, event: str, **data: Any):
        self._log(logging.ERROR, event, data)

    def debug(self, event: str, **data: Any):
        self._log(logging.DEBUG, event, data)

    def _log(self, level: int, event: str, data: dict):
        extra = {"trace_id": self.trace_id}
        if data:
            extra["data"] = data
        self._logger.log(level, event, extra=extra)


def get_logger(component_name: str, trace_id: str | None = None) -> TracedLogger:
    """Get a traced logger for a component.

    If trace_id is None, generates a fresh one.
    Auto-installs in-memory trace capture so summarize_trace() works.
    """
    install_trace_handler()  # Auto-install on first use
    return TracedLogger(component_name, trace_id or new_trace_id())


# For silencing logs in tests
def silence_logs():
    """Silence buildemup logs (for test runs)."""
    logging.getLogger("buildemup").setLevel(logging.CRITICAL)


# ─── Trace summarisation (v0.4) ──────────────────────────────────────────
# In-memory trace store. For production this would be replaced by a real
# log store (e.g., file tail or ELK). For dev/testing, in-memory is enough.
_TRACE_STORE: dict[str, list[dict]] = {}


class _MemoryTraceHandler(logging.Handler):
    """Captures log records into the in-memory trace store."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            trace_id = getattr(record, "trace_id", None)
            if not trace_id:
                return
            event = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "component": record.name.replace("buildemup.", ""),
                "event": record.getMessage(),
                "data": getattr(record, "data", {}),
            }
            _TRACE_STORE.setdefault(trace_id, []).append(event)
        except Exception:
            pass  # Never let logging break the program


_TRACE_HANDLER_INSTALLED = False


def install_trace_handler():
    """Enable in-memory trace capture. Call once at startup."""
    global _TRACE_HANDLER_INSTALLED
    if _TRACE_HANDLER_INSTALLED:
        return
    _configure_root_logger()  # Ensure level is set before adding handler
    root = logging.getLogger("buildemup")
    root.addHandler(_MemoryTraceHandler())
    _TRACE_HANDLER_INSTALLED = True


def summarize_trace(trace_id: str) -> str:
    """Return a human-readable summary of all events for one trace.

    Used during debugging: 'user X got weird output, what happened?'
    Pass the trace_id from their output, get a chronological narrative.
    """
    events = _TRACE_STORE.get(trace_id, [])
    if not events:
        return f"No events found for trace_id={trace_id}"

    lines = [
        f"=== Trace: {trace_id} ===",
        f"  {len(events)} events, "
        f"from {events[0]['ts']} to {events[-1]['ts']}",
        "",
    ]
    for i, e in enumerate(events, 1):
        component = e["component"]
        event = e["event"]
        level = e["level"]
        marker = "⚠" if level in ("WARNING", "ERROR") else "·"
        lines.append(f"  {i:>3}. {marker} [{component}] {event}")
        if e["data"]:
            for k, v in e["data"].items():
                # Truncate long values for readability
                v_str = str(v)
                if len(v_str) > 80:
                    v_str = v_str[:77] + "..."
                lines.append(f"         {k}: {v_str}")
    lines.append("")
    return "\n".join(lines)


def clear_trace_store():
    """Clear the in-memory trace store. Useful for tests."""
    _TRACE_STORE.clear()
