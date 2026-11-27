"""Tests for the room-plan checks (atlaslib/rooms.py)."""
import unittest

from atlaslib.rooms import check_plan


def room(i, outline, level="L1", kind="room", **kw):
    return dict({"id": i, "type": kind, "name": i, "level": level, "outline_m": outline}, **kw)


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def plan(elements, levels=None, size=(20, 10)):
    return {"footprint_m": list(size), "elements": elements,
            "levels": levels or [{"id": "L1", "z_m": 0, "height_m": 4}]}


BUILDING = {"id": "P1-01", "name": "Test Hall", "rect_km": [1.0, 1.02, 0.0, 0.01]}  # 20 × 10 m


def titles(m, b=BUILDING):
    return {t for t, _, _ in check_plan(m, b)}


class RoomChecks(unittest.TestCase):
    def test_clean_plan_has_no_problems(self):
        m = plan([room("A", rect(0, 0, 10, 10)), room("B", rect(10, 0, 20, 10))])
        self.assertEqual(titles(m), set())

    def test_rooms_touching_along_a_wall_do_not_overlap(self):
        m = plan([room("A", rect(0, 0, 10, 10)), room("B", rect(10, 0, 20, 10))])
        self.assertNotIn("Rooms overlap", titles(m))

    def test_overlap(self):
        m = plan([room("A", rect(0, 0, 12, 10)), room("B", rect(10, 0, 20, 10))])
        self.assertIn("Rooms overlap", titles(m))

    def test_room_inside_another_counts_as_overlap(self):
        m = plan([room("A", rect(0, 0, 20, 10)), room("B", rect(2, 2, 6, 6))])
        self.assertIn("Rooms overlap", titles(m))

    def test_different_floors_do_not_overlap(self):
        lv = [{"id": "L1", "z_m": 0, "height_m": 4}, {"id": "L2", "z_m": 4, "height_m": 4}]
        m = plan([room("A", rect(0, 0, 20, 10)), room("B", rect(0, 0, 20, 10), level="L2"),
                  room("S", rect(0, 0, 0, 0), kind="core", levels=["L1", "L2"])], lv)
        self.assertNotIn("Rooms overlap", titles(m))

    def test_self_crossing(self):
        m = plan([room("A", [[0, 0], [10, 10], [10, 0], [0, 10]])])
        self.assertIn("Room outlines cross themselves", titles(m))

    def test_narrow_room(self):
        m = plan([room("A", rect(0, 0, 10, 1))])
        self.assertIn("Rooms too narrow to use", titles(m))

    def test_room_outside_building(self):
        m = plan([room("A", rect(15, 0, 25, 10))])
        self.assertIn("Rooms outside the building", titles(m))

    def test_room_in_courtyard(self):
        b = dict(BUILDING, outline_km=[[[1.0, 0.0], [1.02, 0.0], [1.02, 0.01], [1.0, 0.01]]],
                 holes_km=[[[1.005, 0.002], [1.015, 0.002], [1.015, 0.008], [1.005, 0.008]]])
        m = plan([room("A", rect(5, 2, 15, 8))])
        self.assertIn("Rooms outside the building", titles(m, b))

    def test_floor_without_stairs(self):
        lv = [{"id": "L1", "z_m": 0, "height_m": 4}, {"id": "L2", "z_m": 4, "height_m": 4}]
        m = plan([room("A", rect(0, 0, 10, 10)), room("B", rect(0, 0, 10, 10), level="L2")], lv)
        self.assertIn("Floors with no stairs or lift", titles(m))

    def test_upper_levels_of_a_full_height_hall_need_no_stairs(self):
        # a tank or hangar two levels tall has no floor to stand on at the top level
        lv = [{"id": "L1", "z_m": 0, "height_m": 4}, {"id": "L2", "z_m": 4, "height_m": 4}]
        m = plan([room("T", rect(0, 0, 10, 10), levels=["L1", "L2"], level=None, full_height=True),
                  room("O", rect(10, 0, 20, 10))], lv)
        self.assertNotIn("Floors with no stairs or lift", titles(m))

    def test_floors_that_do_not_stack(self):
        lv = [{"id": "L1", "z_m": 0, "height_m": 4}, {"id": "L2", "z_m": 5, "height_m": 4}]
        m = plan([room("S", rect(0, 0, 3, 3), kind="core", levels=["L1", "L2"])], lv)
        self.assertIn("Floors do not stack", titles(m))

    def test_plan_size_differs_from_map(self):
        m = plan([room("A", rect(0, 0, 10, 10))], size=(30, 10))
        self.assertIn("Plan size differs from the map", titles(m))


if __name__ == "__main__":
    unittest.main()
