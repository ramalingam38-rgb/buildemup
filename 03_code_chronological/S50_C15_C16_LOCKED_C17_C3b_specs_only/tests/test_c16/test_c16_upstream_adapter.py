"""C16 — upstream_adapter tests."""
import pytest
from buildemup.components.c16 import m_to_mm, floor_label_to_level, sorted_by_floor_label


class TestMToMm:
    def test_zero(self): assert m_to_mm(0.0) == 0
    def test_one_metre(self): assert m_to_mm(1.0) == 1000
    def test_half(self): assert m_to_mm(0.5) == 500
    def test_negative(self): assert m_to_mm(-1.5) == -1500
    def test_micro_precision_rounds(self): assert m_to_mm(0.0005) == 0  # banker's
    def test_above_half_rounds_up(self): assert m_to_mm(0.0006) == 1
    def test_large(self): assert m_to_mm(100.0) == 100000
    def test_returns_int(self): assert isinstance(m_to_mm(3.7), int)
    def test_idempotent_via_division(self):
        for v in [0.0, 1.0, 4.5, 12.345]:
            mm = m_to_mm(v)
            again = m_to_mm(mm / 1000.0)
            assert again == mm


class TestFloorLabelToLevel:
    def test_digit_zero(self): assert floor_label_to_level("0") == 0
    def test_digit_one(self): assert floor_label_to_level("1") == 1
    def test_f_prefixed(self): assert floor_label_to_level("F0") == 0
    def test_f_prefixed_higher(self): assert floor_label_to_level("F2") == 2
    def test_named_ground(self): assert floor_label_to_level("G") == 0
    def test_named_ground_full(self): assert floor_label_to_level("GF") == 0
    def test_named_first(self): assert floor_label_to_level("FF") == 1
    def test_named_second(self): assert floor_label_to_level("SF") == 2
    def test_case_insensitive(self): assert floor_label_to_level("ff") == 1
    def test_whitespace_stripped(self): assert floor_label_to_level("  F1  ") == 1
    def test_unrecognized_returns_sentinel(self):
        assert floor_label_to_level("ZZZ") == -1


class TestSortedByFloorLabel:
    def test_already_sorted_unchanged(self):
        inp = (("F0", "a"), ("F1", "b"), ("F2", "c"))
        assert sorted_by_floor_label(inp) == inp
    def test_reverse_sorted(self):
        inp = (("F2", "c"), ("F1", "b"), ("F0", "a"))
        assert sorted_by_floor_label(inp) == (("F0", "a"), ("F1", "b"), ("F2", "c"))
    def test_empty(self): assert sorted_by_floor_label(()) == ()
    def test_single(self): assert sorted_by_floor_label((("F0", "x"),)) == (("F0", "x"),)
