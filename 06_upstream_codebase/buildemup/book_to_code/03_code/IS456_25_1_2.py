"""
IS 456:2000 cl. 25.1.2 — Slenderness rule loader.

Worked example for the book-to-code pipeline. Loads structured rules
from JSON and exposes Python functions that the rest of `kb/` can use.

The actual slenderness check function lives in `kb/seismic_detailing.py`
where it integrates with the rest of the structural design logic. This
file demonstrates the loader pattern.

†= placeholder name marker.
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass


_JSON_PATH = Path(__file__).parent.parent / "02_structured" / "IS456_25_1_2.json"


@dataclass(frozen=True)
class SlendernessRule:
    """One slenderness rule from IS 456 cl. 25.1.2."""
    rule_id: str
    threshold: float
    operator: str
    consequence: str
    notes: str


def load_slenderness_rules() -> list[SlendernessRule]:
    """Load slenderness rules from the structured JSON."""
    with open(_JSON_PATH) as f:
        data = json.load(f)

    rules = []
    for rule in data["rules"]:
        rules.append(SlendernessRule(
            rule_id=rule["rule_id"],
            threshold=rule["condition"]["value"],
            operator=rule["condition"]["operator"],
            consequence=rule["consequence"],
            notes=rule["notes"],
        ))
    return rules


def get_source_metadata() -> dict:
    """Get metadata about the source code being loaded."""
    with open(_JSON_PATH) as f:
        data = json.load(f)
    return data["source"]


# Demo: print loaded rules when run directly
if __name__ == "__main__":
    print(f"Source: {get_source_metadata()['title']}")
    print(f"Section: {get_source_metadata()['section']}")
    print()
    print("Loaded rules:")
    for rule in load_slenderness_rules():
        print(f"  {rule.rule_id}: ratio {rule.operator} {rule.threshold}")
        print(f"    → {rule.consequence}")
        print()
