"""
BuildemUp† — Knowledge Base Version Registry
==============================================

Single source of truth for all KB versions and their LAST_UPDATED dates.
Every output should embed the versions of all KB modules that contributed,
so we can reproduce past outputs exactly when codes/rates change later.

Why this matters:
  - In 2027 a user asks: "I got an estimate in Apr 2026 — why does today's
    estimate differ?" Answer: KB versions changed. Show them what changed.
  - When a structural engineer reviews our output 6 months later, they
    need to know exactly which version of IS 456 / IS 13920 we applied.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class KBVersionInfo:
    """Version info for one knowledge module."""
    module_name: str
    version: str           # e.g., 'RCC_India_IS456_2026_v1'
    last_updated: str      # ISO date 'YYYY-MM-DD'
    source_codes: tuple[str, ...]   # Indian codes referenced
    notes: str = ""


# All KB versions in one place — single source of truth
KB_VERSIONS: dict[str, KBVersionInfo] = {
    "rcc_design_rules": KBVersionInfo(
        module_name="rcc_design_rules",
        version="RCC_India_IS456_2026_v1",
        last_updated="2026-04-01",
        source_codes=("IS 456:2000", "IS 875 Part 1, 2",
                      "Devdas Menon", "B.C. Punmia"),
    ),
    "soil_foundation_rules": KBVersionInfo(
        module_name="soil_foundation_rules",
        version="Soil_India_2026_v1",
        last_updated="2026-04-01",
        source_codes=("IS 1080:1985", "IS 1904:1986", "IS 6403:1981"),
        notes="Soil profiles for 7 cities; refresh annually with new geotech data",
    ),
    "load_estimation": KBVersionInfo(
        module_name="load_estimation",
        version="Loads_India_2026_v1",
        last_updated="2026-04-01",
        source_codes=("IS 875 Part 1, 2, 3", "B.C. Punmia"),
    ),
    "seismic_detailing": KBVersionInfo(
        module_name="seismic_detailing",
        version="Seismic_IS13920_2026_v1",
        last_updated="2026-04-01",
        source_codes=("IS 13920:2016", "IS 1893 Part 1:2016", "C.V.R. Murty"),
    ),
    "wind_load": KBVersionInfo(
        module_name="wind_load",
        version="Wind_IS875_2026_v1",
        last_updated="2026-04-01",
        source_codes=("IS 875 Part 3:2015",),
    ),
    "pile_foundation": KBVersionInfo(
        module_name="pile_foundation",
        version="Pile_Foundation_IS2911_2026_v1",
        last_updated="2026-04-01",
        source_codes=("IS 2911 Part 1, Sec 2:2010", "IS 2911 Part 4:2013",
                      "P.C. Varghese"),
    ),
    "material_rates_chennai": KBVersionInfo(
        module_name="material_rates_chennai",
        version="Chennai_2026_Q2_v1",
        last_updated="2026-04-01",
        source_codes=("CPWD DSR 2026", "Chennai market survey Q2 2026"),
        notes="Refresh quarterly — rates valid Q2 2026 (Apr-Jun)",
    ),
    "material_rates_multicity": KBVersionInfo(
        module_name="material_rates_multicity",
        version="MultiCity_2026_Q2_v1",
        last_updated="2026-04-01",
        source_codes=("CPWD DSR 2026", "State PWD schedules", "City surveys"),
        notes="Bangalore, Hyderabad, Mumbai, Pune, Delhi. Refresh quarterly.",
    ),
}


def get_all_versions() -> dict[str, str]:
    """Return {module_name: version} for embedding in outputs."""
    return {k: v.version for k, v in KB_VERSIONS.items()}


def get_versions_for_modules(module_names: list[str]) -> dict[str, str]:
    """Return versions for a specific subset of modules.

    Used by orchestrator to embed only the KBs that actually contributed
    to a particular output.
    """
    return {
        name: KB_VERSIONS[name].version
        for name in module_names
        if name in KB_VERSIONS
    }


def get_version_info(module_name: str) -> KBVersionInfo | None:
    return KB_VERSIONS.get(module_name)


def format_versions_for_user(versions: dict[str, str]) -> str:
    """Human-readable version block for explain() output."""
    lines = ["Knowledge base versions used in this estimate:"]
    for module, version in sorted(versions.items()):
        info = KB_VERSIONS.get(module)
        last_updated = f" (updated {info.last_updated})" if info else ""
        lines.append(f"  • {module}: {version}{last_updated}")
    lines.append(
        "  Save these versions if you want to reproduce this exact estimate "
        "later — codes and rates change over time."
    )
    return "\n".join(lines)


# ─── v0.5: Data freshness reporting ─────────────────────────────────────
# We must never silently ship stale data. This surfaces how stale each
# KB module is in days/quarters since last update.
def get_data_freshness_report(today_iso: str | None = None) -> dict:
    """Return freshness summary for all KB modules.

    Per-module: how many days/quarters since last_updated.
    Flags modules that exceed their refresh cadence.

    Cadence rules (refresh cycle by category):
      - Material rates → quarterly (90 days)
      - Indian codes (IS xxxx) → yearly (365 days, codes change rarely)
      - Soil profiles → yearly
      - Building type registry → yearly

    Args:
        today_iso: ISO date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Dict with per-module status + overall flag.
    """
    from datetime import date, datetime
    if today_iso is None:
        today = date.today()
    else:
        today = datetime.fromisoformat(today_iso).date()

    # Cadence in days, by module category
    quarterly_modules = {"material_rates_chennai", "material_rates_multicity"}
    yearly_modules = {
        "rcc_design_rules", "soil_foundation_rules", "load_estimation",
        "seismic_detailing", "wind_load", "pile_foundation",
    }

    per_module = []
    stale_modules = []
    for module_name, info in KB_VERSIONS.items():
        try:
            updated = datetime.fromisoformat(info.last_updated).date()
            days_old = (today - updated).days
        except (ValueError, TypeError):
            days_old = -1  # Unknown

        if module_name in quarterly_modules:
            cadence_days = 90
            cadence_label = "quarterly"
        elif module_name in yearly_modules:
            cadence_days = 365
            cadence_label = "yearly"
        else:
            cadence_days = 365
            cadence_label = "yearly"

        is_stale = days_old > cadence_days if days_old >= 0 else False
        if is_stale:
            stale_modules.append(module_name)

        per_module.append({
            "module": module_name,
            "version": info.version,
            "last_updated": info.last_updated,
            "days_old": days_old,
            "cadence": cadence_label,
            "cadence_days": cadence_days,
            "is_stale": is_stale,
        })

    return {
        "today": today.isoformat(),
        "modules": per_module,
        "stale_count": len(stale_modules),
        "stale_modules": stale_modules,
        "all_fresh": len(stale_modules) == 0,
    }


def format_freshness_report(today_iso: str | None = None) -> str:
    """Human-readable freshness report. Used by maintainers, not end-users."""
    report = get_data_freshness_report(today_iso)
    lines = [
        f"BuildemUp† Knowledge Base Freshness Report ({report['today']})",
        "=" * 60,
        "",
    ]
    for m in report["modules"]:
        flag = "⚠ STALE" if m["is_stale"] else "✓ fresh"
        lines.append(
            f"  {flag}  {m['module']:<32} "
            f"{m['days_old']:>4}d old "
            f"({m['cadence']} refresh expected)"
        )
    lines.append("")
    if report["all_fresh"]:
        lines.append("All KB modules are within their refresh cadence.")
    else:
        lines.append(
            f"⚠ {report['stale_count']} module(s) stale: "
            f"{', '.join(report['stale_modules'])}"
        )
        lines.append(
            "Refresh stale modules before next release. Quarterly cadence for "
            "rates, yearly for codes."
        )
    return "\n".join(lines)


# ─── v0.6: Freshness enforcement with tiered severity ────────────────────
# Per user decision:
#   < 90 days: OK
#   90-180 days: WARNING (confidence degraded)
#   > 180 days: BLOCK or degrade confidence
#
# For rates specifically (quarterly cadence). Codes are yearly so the
# thresholds are 365/730 days for code modules.

def enforce_freshness_and_get_action(today_iso: str | None = None) -> dict:
    """Check KB freshness and recommend action per the 3-tier rule.

    Returns dict with:
      - action: 'OK' | 'WARN_DEGRADE_CONFIDENCE' | 'BLOCK_STALE'
      - stale_modules: list of stale module names with severity
      - user_message: formatted text for user display
    """
    report = get_data_freshness_report(today_iso)

    # Classify each module by age
    warn_modules = []
    block_modules = []
    for m in report["modules"]:
        if m["days_old"] < 0:
            continue  # Unknown age, skip
        cadence = m["cadence_days"]
        # Warning threshold: exceeds cadence
        # Block threshold: exceeds 2x cadence
        if m["days_old"] > cadence * 2:
            block_modules.append({
                "module": m["module"],
                "days_old": m["days_old"],
                "cadence_days": cadence,
            })
        elif m["days_old"] > cadence:
            warn_modules.append({
                "module": m["module"],
                "days_old": m["days_old"],
                "cadence_days": cadence,
            })

    if block_modules:
        action = "BLOCK_STALE"
        names = [m["module"] for m in block_modules]
        user_message = (
            f"⚠ DATA IS STALE — the following KB module(s) have not been "
            f"refreshed in over 2× their cadence: {', '.join(names)}. "
            f"Estimate cost quality is significantly degraded. Please "
            f"contact us to refresh before relying on this output."
        )
    elif warn_modules:
        action = "WARN_DEGRADE_CONFIDENCE"
        names = [m["module"] for m in warn_modules]
        user_message = (
            f"⚠ Data freshness warning: {', '.join(names)} is past its "
            f"refresh cadence. Confidence has been degraded — treat "
            f"cost values as more uncertain than usual."
        )
    else:
        action = "OK"
        user_message = "All KB modules are within their refresh cadence."

    return {
        "action": action,
        "warn_modules": warn_modules,
        "block_modules": block_modules,
        "user_message": user_message,
        "today": report["today"],
    }


def should_degrade_confidence(today_iso: str | None = None) -> bool:
    """Simple boolean: should we bump confidence down a level?

    True if any KB module is past its refresh cadence.
    """
    result = enforce_freshness_and_get_action(today_iso)
    return result["action"] in ("WARN_DEGRADE_CONFIDENCE", "BLOCK_STALE")
