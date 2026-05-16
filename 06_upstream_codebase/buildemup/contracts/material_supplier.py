"""
Material supplier ordering contract.

Phase 1 vision: integrate with Ultratech, JSW Steel, ACC, Asian Paints
for direct material orders + referral fees.

Per the vision doc cost table on slide 6, we can already itemize down
to "Ultratech OPC 53 — 480 bags — Rs.380." This contract makes that
shop-ready: a supplier integration can ingest the BOM and quote/deliver.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class BillOfMaterialsLine:
    """One line in the bill of materials for supplier consumption."""
    item_id: str                      # Stable item code (e.g., "CEM_OPC53_50KG")
    name: str                         # "Cement OPC 53"
    brand: str = ""                   # "Ultratech" — preferred brand
    grade: str = ""                   # "OPC 53"
    is_code: str = ""                 # "IS 12269"
    quantity: float = 0.0
    unit: str = ""                    # "bag", "tonne", "cum"
    estimated_unit_rate_rupees: float = 0.0
    estimated_total_rupees: float = 0.0
    notes: str = ""                   # Quality/spec notes


@dataclass(frozen=True)
class BillOfMaterialsExport:
    """Full BOM for one project, supplier-ready."""
    project_id: str
    user_city: str
    delivery_address_pincode: str = ""    # Empty until user provides

    structural_materials: tuple[BillOfMaterialsLine, ...] = ()
    masonry_materials: tuple[BillOfMaterialsLine, ...] = ()
    finish_materials: tuple[BillOfMaterialsLine, ...] = ()
    plumbing_materials: tuple[BillOfMaterialsLine, ...] = ()
    electrical_materials: tuple[BillOfMaterialsLine, ...] = ()

    estimated_grand_total_rupees: float = 0.0
    expected_delivery_window_days: tuple[int, int] = (15, 45)
    source_trace_id: str = ""


class MaterialSupplierAdapter(Protocol):
    """Interface for supplier integrations (Ultratech, JSW, etc.)."""

    def submit_bom_for_quote(self, bom: BillOfMaterialsExport) -> str:
        """Submit BOM to supplier; returns supplier quote ID."""
        ...

    def get_supplier_quote(self, supplier_quote_id: str) -> dict:
        """Get the supplier's actual quoted prices + delivery."""
        ...

    def place_order(
        self, supplier_quote_id: str,
        delivery_address: str,
        items_to_order: list[str],
    ) -> str:
        """Place order; returns order tracking ID."""
        ...
