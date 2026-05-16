"""
BuildemUp — Component 12 — slicing-tree placement subpackage
=============================================================

Per C12 SPEC v1.0 LOCKED § 3.1 + v0.3-A1 (slicing_kd_tree-only at v1).
"""
from .placement import place_rooms_slicing_tree
from .room_spec import RoomSpec

__all__ = [
    "RoomSpec",
    "place_rooms_slicing_tree",
]
