"""
BuildemUp† — Insights from Logs (v0.7)
==========================================

Per v0.6 review Drawback 6: we built structured logging but never
used it for pattern detection. This module closes the loop.

What this does:
  ✓ Reads structured log output (JSON lines from utils/logging.py)
  ✓ Aggregates: common warnings, cost distribution, failure modes
  ✓ Produces a weekly text summary (also CSV for spreadsheet users)

What this is NOT:
  ✗ NOT a real-time dashboard (that's v2)
  ✗ NOT ML / anomaly detection (pure counting for now)
  ✗ NOT automated alerting (human runs the script)

Usage:
  # Weekly: run manually or via cron
  python -m buildemup.utils.insights --logs ./logs/ --out ./reports/week_2026_04.md

  # Also importable as a library
  from buildemup.utils.insights import aggregate_logs, InsightsReport

†= placeholder name marker.
"""
from __future__ import annotations
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InsightsReport:
    """Aggregated insights from a period of logs."""
    period_start: str                    # ISO date
    period_end: str                      # ISO date
    total_executions: int = 0
    successful_executions: int = 0
    refused_executions: int = 0
    errored_executions: int = 0

    # Top N warnings (by count)
    top_warnings: list[tuple[str, int]] = field(default_factory=list)

    # Cost distribution (min / p25 / p50 / p75 / max) in rupees
    cost_distribution: dict = field(default_factory=dict)

    # Most common refusal reasons
    refusal_reasons: list[tuple[str, int]] = field(default_factory=list)

    # Per-city execution counts
    city_counts: dict = field(default_factory=dict)

    # Frame sanity outcomes (SAFE / WARNING / FAIL counts)
    frame_sanity_outcomes: dict = field(default_factory=dict)

    # Average confidence distribution
    confidence_distribution: dict = field(default_factory=dict)

    def format_text(self) -> str:
        """Human-readable weekly report."""
        lines = [
            "=" * 70,
            f"BuildemUp Weekly Insights: {self.period_start} → {self.period_end}",
            "=" * 70,
            "",
            f"Total executions:       {self.total_executions}",
            f"  Successful:           {self.successful_executions}",
            f"  Refused (validation): {self.refused_executions}",
            f"  Errored:              {self.errored_executions}",
            "",
        ]

        if self.top_warnings:
            lines.append("TOP WARNINGS (most frequent):")
            for warning, count in self.top_warnings[:10]:
                # Truncate long warnings for display
                display = warning[:70] + "…" if len(warning) > 70 else warning
                lines.append(f"  {count:>4}×  {display}")
            lines.append("")

        if self.cost_distribution:
            lines.append("COST DISTRIBUTION (₹):")
            cd = self.cost_distribution
            lines.append(f"  Min:    ₹{cd.get('min', 0):>12,.0f}")
            lines.append(f"  P25:    ₹{cd.get('p25', 0):>12,.0f}")
            lines.append(f"  Median: ₹{cd.get('p50', 0):>12,.0f}")
            lines.append(f"  P75:    ₹{cd.get('p75', 0):>12,.0f}")
            lines.append(f"  Max:    ₹{cd.get('max', 0):>12,.0f}")
            lines.append("")

        if self.refusal_reasons:
            lines.append("TOP REFUSAL REASONS:")
            for reason, count in self.refusal_reasons[:5]:
                lines.append(f"  {count:>4}×  {reason}")
            lines.append("")

        if self.city_counts:
            lines.append("PER-CITY EXECUTIONS:")
            for city, count in sorted(
                self.city_counts.items(), key=lambda x: -x[1]
            ):
                lines.append(f"  {count:>4}×  {city}")
            lines.append("")

        if self.frame_sanity_outcomes:
            lines.append("FRAME SANITY OUTCOMES:")
            for outcome, count in sorted(
                self.frame_sanity_outcomes.items(), key=lambda x: -x[1]
            ):
                pct = count / max(self.total_executions, 1) * 100
                lines.append(f"  {count:>4}× ({pct:4.1f}%)  {outcome}")
            lines.append("")

        if self.confidence_distribution:
            lines.append("CONFIDENCE DISTRIBUTION:")
            for level, count in sorted(
                self.confidence_distribution.items(), key=lambda x: -x[1]
            ):
                pct = count / max(self.total_executions, 1) * 100
                lines.append(f"  {count:>4}× ({pct:4.1f}%)  {level}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def to_csv_rows(self) -> list[tuple]:
        """Rows for CSV export, for spreadsheet analysis."""
        rows = [("metric", "value")]
        rows.append(("period_start", self.period_start))
        rows.append(("period_end", self.period_end))
        rows.append(("total_executions", self.total_executions))
        rows.append(("successful", self.successful_executions))
        rows.append(("refused", self.refused_executions))
        rows.append(("errored", self.errored_executions))
        for w, c in self.top_warnings[:10]:
            rows.append((f"warning:{w[:50]}", c))
        for r, c in self.refusal_reasons[:5]:
            rows.append((f"refusal:{r[:50]}", c))
        for k, v in self.cost_distribution.items():
            rows.append((f"cost_{k}", v))
        for city, c in self.city_counts.items():
            rows.append((f"city:{city}", c))
        for outcome, c in self.frame_sanity_outcomes.items():
            rows.append((f"frame_sanity:{outcome}", c))
        for level, c in self.confidence_distribution.items():
            rows.append((f"confidence:{level}", c))
        return rows


def aggregate_logs(log_entries: list[dict]) -> InsightsReport:
    """Aggregate a list of structured log entries into an InsightsReport.

    Args:
        log_entries: list of dicts from utils/logging.py (JSON lines).
                     Each dict has at minimum: timestamp, event, fields.

    Returns:
        InsightsReport with aggregated statistics.
    """
    report = InsightsReport(
        period_start="",
        period_end="",
    )

    if not log_entries:
        return report

    # Period boundaries
    timestamps = [e.get("timestamp", "") for e in log_entries if e.get("timestamp")]
    if timestamps:
        report.period_start = min(timestamps)[:10]   # YYYY-MM-DD only
        report.period_end = max(timestamps)[:10]

    # Counters
    warning_counter: Counter = Counter()
    refusal_counter: Counter = Counter()
    city_counter: Counter = Counter()
    frame_counter: Counter = Counter()
    confidence_counter: Counter = Counter()
    costs: list[float] = []

    for entry in log_entries:
        event = entry.get("event", "")

        if event == "execute_complete":
            report.total_executions += 1
            report.successful_executions += 1
            cost = entry.get("cost")
            if isinstance(cost, (int, float)):
                costs.append(float(cost))

        elif event in ("execute_refused", "user_claims_engineer_review_severe_irregularity"):
            # These count as executions but not successful
            report.total_executions += 1
            report.refused_executions += 1
            reason = entry.get("reason") or entry.get("refusal_reason") or "unspecified"
            refusal_counter[reason] += 1

        elif event == "execute_errored":
            report.total_executions += 1
            report.errored_executions += 1

        # Warnings can be attached to any event
        warnings = entry.get("warnings", [])
        if isinstance(warnings, list):
            for w in warnings:
                if isinstance(w, str) and len(w) > 5:
                    # Normalise: take first 80 chars as a key
                    warning_counter[w[:80]] += 1

        # City tagging
        city = entry.get("city")
        if city:
            city_counter[str(city).lower()] += 1

        # Frame sanity outcome
        frame_outcome = entry.get("frame_sanity_overall")
        if frame_outcome:
            frame_counter[str(frame_outcome)] += 1

        # Confidence
        conf = entry.get("cost_confidence")
        if conf:
            confidence_counter[str(conf)] += 1

    # Top N
    report.top_warnings = warning_counter.most_common(10)
    report.refusal_reasons = refusal_counter.most_common(5)
    report.city_counts = dict(city_counter)
    report.frame_sanity_outcomes = dict(frame_counter)
    report.confidence_distribution = dict(confidence_counter)

    # Cost distribution
    if costs:
        costs.sort()
        n = len(costs)
        report.cost_distribution = {
            "min": costs[0],
            "p25": costs[int(n * 0.25)],
            "p50": costs[int(n * 0.5)],
            "p75": costs[int(n * 0.75)],
            "max": costs[-1],
            "count": n,
            "mean": sum(costs) / n,
        }

    return report


def load_log_file(path: str) -> list[dict]:
    """Load JSON-lines log file. Returns list of entry dicts.

    Invalid lines are silently skipped (better than crashing the
    weekly report on one malformed entry).
    """
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def run_weekly_report(log_dir: str, output_path: str) -> None:
    """Produce weekly report from all log files in log_dir.

    This is the main command-line entry point.
    """
    all_entries = []
    if os.path.isdir(log_dir):
        for filename in os.listdir(log_dir):
            if filename.endswith(".log") or filename.endswith(".jsonl"):
                all_entries.extend(
                    load_log_file(os.path.join(log_dir, filename))
                )

    report = aggregate_logs(all_entries)
    text = report.format_text()

    # Write to file
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(text)
    print(text)
    print(f"\nReport written to: {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="BuildemUp weekly insights from structured logs."
    )
    parser.add_argument("--logs", default="./logs/",
                        help="Directory containing .log/.jsonl files")
    parser.add_argument("--out", default="./reports/weekly_insights.md",
                        help="Path for the output report")
    args = parser.parse_args()
    run_weekly_report(args.logs, args.out)
