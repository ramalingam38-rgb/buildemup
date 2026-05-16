"""C16 — Phase β scheduling tests."""
from buildemup.components.c16 import (
    execute_phase_alpha, execute_phase_beta,
)
from tests.test_c16.fixtures import (
    FakeDoor, standard_config, standard_jurisdiction,
    standard_selection, standard_upstream_inputs, two_room_floor,
)


def _envelope_with(doors=(), floors=None):
    if floors is None:
        floors = (("F0", two_room_floor()),)
    inputs = standard_upstream_inputs(
        per_floor_placements=floors,
        doors_by_floor={label: doors for label, _ in floors},
    )
    return execute_phase_alpha(
        selection_result=standard_selection(),
        upstream_inputs=inputs,
        jurisdiction_profile=standard_jurisdiction(),
        config=standard_config(),
    )


class TestDoorScheduleAssembly:
    def test_one_door_one_schedule_entry(self):
        envelope = _envelope_with(doors=(FakeDoor(
            "bed1", "liv1", "vertical", 1.0, 0.9,
        ),))
        result = execute_phase_beta(envelope=envelope)
        assert len(result.per_floor) == 1
        assert len(result.per_floor[0].door_schedule) == 1
        ds = result.per_floor[0].door_schedule[0]
        assert ds.door_number == "D001"
        assert ds.width_mm == 900
        assert ds.height_mm == 2100
        assert ds.material == "wood"

    def test_zero_doors_empty_schedule(self):
        envelope = _envelope_with()
        result = execute_phase_beta(envelope=envelope)
        assert result.per_floor[0].door_schedule == ()

    def test_door_numbers_sequential_across_floors(self):
        envelope = _envelope_with(
            doors=(FakeDoor("bed1", "liv1", "vertical", 1.0, 0.9),),
            floors=(
                ("F0", two_room_floor()),
                ("F1", two_room_floor()),
            ),
        )
        result = execute_phase_beta(envelope=envelope)
        assert result.per_floor[0].door_schedule[0].door_number == "D001"
        assert result.per_floor[1].door_schedule[0].door_number == "D002"


class TestWindowScheduleEmptyV1:
    def test_no_upstream_windows_means_empty_schedule(self):
        envelope = _envelope_with()
        result = execute_phase_beta(envelope=envelope)
        # B-C16-WINDOW-UPSTREAM-CONTRACT: v1 has no upstream window source
        assert result.per_floor[0].window_schedule == ()


class TestFinishScheduleAssembly:
    def test_one_entry_per_room(self):
        envelope = _envelope_with()
        result = execute_phase_beta(envelope=envelope)
        # two_room_floor has 2 rooms
        assert len(result.per_floor[0].finish_schedule) == 2

    def test_bedroom_default_is_vitrified_tile(self):
        envelope = _envelope_with()
        result = execute_phase_beta(envelope=envelope)
        # rooms sorted lex-ASC by room_id; bed1 < liv1
        bed_finish = result.per_floor[0].finish_schedule[0]
        assert bed_finish.floor_finish == "vitrified_tile"
        # Bedroom is a dry room — wall finish is paint
        assert bed_finish.wall_finish == "emulsion_paint"

    def test_bathroom_gets_anti_skid(self):
        from tests.test_c16.fixtures import FakePlacedRoom, FakePlacedCandidate
        rooms = (FakePlacedRoom("bath1", "BATHROOM", 0, 0, 2, 2),)
        pc = FakePlacedCandidate("sig:1", rooms, ())
        inputs = standard_upstream_inputs(per_floor_placements=(("F0", pc),))
        envelope = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        result = execute_phase_beta(envelope=envelope)
        bath = result.per_floor[0].finish_schedule[0]
        assert bath.floor_finish == "anti_skid_ceramic_tile"
        # Wet room → ceramic tile walls
        assert bath.wall_finish == "ceramic_tile"

    def test_kitchen_wet_wall_finish(self):
        from tests.test_c16.fixtures import FakePlacedRoom, FakePlacedCandidate
        rooms = (FakePlacedRoom("kit1", "KITCHEN", 0, 0, 3, 3),)
        pc = FakePlacedCandidate("sig:1", rooms, ())
        inputs = standard_upstream_inputs(per_floor_placements=(("F0", pc),))
        envelope = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        result = execute_phase_beta(envelope=envelope)
        kit = result.per_floor[0].finish_schedule[0]
        assert kit.floor_finish == "ceramic_tile"
        assert kit.wall_finish == "ceramic_tile"


class TestDeterminism:
    def test_same_input_same_output(self):
        e1 = _envelope_with(doors=(FakeDoor("bed1", "liv1", "vertical", 1.0, 0.9),))
        e2 = _envelope_with(doors=(FakeDoor("bed1", "liv1", "vertical", 1.0, 0.9),))
        r1 = execute_phase_beta(envelope=e1)
        r2 = execute_phase_beta(envelope=e2)
        assert r1 == r2
