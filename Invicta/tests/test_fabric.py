"""Tests for the building fabric worked out from the rooms (atlaslib/fabric.py)."""
import copy
import math
import unittest

from atlaslib import fabric as FB


def sp(i, x0, y0, x1, y1, kind="room", level="L1", **kw):
    return dict({"id": i, "type": kind, "name": kw.pop("name", i), "level": level,
                 "outline_m": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}, **kw)


def plan(elements, levels=None):
    return {"footprint_m": [30, 20], "elements": elements,
            "levels": levels or [{"id": "L1", "z_m": 0, "height_m": 4}]}


# Two offices on the north side of a corridor that runs along the south wall:
#   y 0-4 corridor (zone), y 4-14 rooms A (x 0-10) and B (x 10-20).
SIMPLE = plan([sp("C", 0, 0, 20, 4, "zone", name="Corridor"), sp("A", 0, 4, 10, 14), sp("B", 10, 4, 20, 14, name="Store")])


def of(extra, t):
    return [e for e in extra if e["type"] == t]


class Walls(unittest.TestCase):
    def test_walls_between_and_around(self):
        extra, rep = FB.build(SIMPLE)
        walls = of(extra, "wall")
        ext = [w for w in walls if w["kind"] == "exterior"]
        inner = [w for w in walls if w["kind"] == "interior"]
        self.assertAlmostEqual(sum(math.dist(*w["line_m"]) for w in ext), 2 * (20 + 14))  # the outside edge
        self.assertAlmostEqual(sum(math.dist(*w["line_m"]) for w in inner), 20 + 10)       # corridor wall + A|B
        self.assertTrue(all(w["thickness_m"] == FB.T_OUTSIDE for w in ext))
        self.assertTrue(all(w["thickness_m"] == FB.T_PARTITION for w in inner))
        self.assertTrue(all(w["height_m"] == 4 for w in walls))

    def test_plan_file_is_not_changed(self):
        m = copy.deepcopy(SIMPLE)
        out = FB.with_fabric(m)
        self.assertEqual(m, SIMPLE)                                   # the input is untouched
        self.assertEqual(out["elements"][:3], SIMPLE["elements"])     # every room kept, first, as it was
        self.assertEqual(out["schema"], "invicta-atlas/model@2")


class Doors(unittest.TestCase):
    def test_every_room_opens_onto_the_corridor_and_there_is_an_entrance(self):
        extra, rep = FB.build(SIMPLE)
        doors = of(extra, "door")
        self.assertEqual(rep["unreachable"], [])
        self.assertEqual(rep["entrances"], 1)
        for r in ("A", "B"):
            self.assertTrue(any(sorted(d["between"]) == sorted([r, "C"]) for d in doors), r)
        ent = [d for d in doors if d["name"] == "Entrance"]
        self.assertEqual(ent[0]["between"], ["C"])
        self.assertAlmostEqual(ent[0]["width_m"], FB.ENTRANCE_W)

    def test_big_rooms_get_double_doors(self):
        m = plan([sp("C", 0, 0, 30, 4, "zone"), sp("H", 0, 4, 30, 20, name="Hall")])
        extra, _ = FB.build(m)
        d = next(d for d in of(extra, "door") if "H" in d["between"])
        self.assertAlmostEqual(d["width_m"], FB.DOUBLE_W)

    def test_a_room_with_a_drawn_door_keeps_it(self):
        m = copy.deepcopy(SIMPLE)
        m["elements"].append({"id": "E9", "type": "door", "level": "L1", "line_m": [[2, 4], [3, 4]], "width_m": 1})
        extra, rep = FB.build(m)
        self.assertFalse(any("A" in d["between"] for d in of(extra, "door")))
        self.assertEqual(rep["unreachable"], [])

    def test_a_kiosk_in_a_park_gets_its_own_outside_door(self):
        m = plan([sp("K", 0, 0, 5, 5, name="Kiosk"), sp("T", 20, 0, 25, 5, name="Toilets")])
        extra, rep = FB.build(m)
        self.assertEqual(rep["unreachable"], [])
        self.assertEqual(rep["entrances"], 2)


class Stairs(unittest.TestCase):
    TWO = [{"id": "L1", "z_m": 0, "height_m": 4}, {"id": "L2", "z_m": 4, "height_m": 4}]

    def test_stairs_have_real_step_sizes_and_reach_the_upper_floor(self):
        m = plan([sp("C", 0, 0, 20, 4, "zone", levels=["L1", "L2"], level=None),
                  sp("A", 0, 4, 10, 14, levels=["L1", "L2"], level=None),
                  sp("S", 10, 4, 20, 14, "core", levels=["L1", "L2"], level=None, name="Stairs and lifts")], self.TWO)
        extra, rep = FB.build(m)
        st = of(extra, "stair")
        self.assertEqual(len(st), 1)
        s = st[0]
        self.assertEqual(s["risers"], 23)                       # 4 m / 0.18 m, rounded up
        self.assertLessEqual(s["riser_m"], FB.RISER_MAX)
        self.assertAlmostEqual(s["riser_m"] * s["risers"], 4.0, places=2)
        self.assertTrue(s["fits"])
        self.assertEqual(rep["unreachable"], [])                # upstairs is reached by the stairs
        self.assertTrue(of(extra, "lift"))

    def test_a_stair_that_does_not_fit_is_reported(self):
        m = plan([sp("C", 0, 0, 20, 4, "zone", levels=["L1", "L2"], level=None),
                  sp("S", 0, 4, 3, 7, "core", levels=["L1", "L2"], level=None)], self.TWO)
        extra, rep = FB.build(m)
        self.assertFalse(of(extra, "stair")[0]["fits"])
        self.assertEqual(len(rep["stairs_not_fitting"]), 1)

    def test_a_floor_with_no_stairs_is_cut_off(self):
        m = plan([sp("C", 0, 0, 20, 4, "zone"), sp("U", 0, 0, 20, 4, "zone", level="L2")], self.TWO)
        _, rep = FB.build(m)
        self.assertEqual(rep["unreachable"], ["U U (L2)"])

    def test_a_full_height_hall_is_one_space(self):
        m = plan([sp("H", 0, 0, 30, 20, levels=["L1", "L2"], level=None, full_height=True, name="Hangar")], self.TWO)
        extra, rep = FB.build(m)
        self.assertEqual(rep["unreachable"], [])
        self.assertEqual([s["level"] for s in of(extra, "slab")], ["L1"])  # no floor across the hall upstairs


class Windows(unittest.TestCase):
    def test_windows_on_outside_walls_but_not_stores(self):
        extra, _ = FB.build(SIMPLE)
        wins = of(extra, "window")
        self.assertTrue(any(w["space"] == "A" for w in wins))
        self.assertFalse(any(w["space"] == "B" for w in wins))   # "Store"
        for w in wins:
            self.assertGreaterEqual(math.dist(*w["line_m"]) + 1e-6, (w["count"] - 1) * FB.WIN_STEP + FB.WIN_W)

    def test_no_windows_below_ground(self):
        m = plan([sp("A", 0, 0, 10, 10, level="B1")], [{"id": "B1", "z_m": -5, "height_m": 4}])
        extra, _ = FB.build(m)
        self.assertEqual(of(extra, "window"), [])


class Compact(unittest.TestCase):
    def test_compact_keeps_every_wall(self):
        extra, _ = FB.build(SIMPLE)
        c = FB.compact(extra)
        self.assertEqual(sum(len(e["lines_m"]) for e in c if e["type"] == "walls"), len(of(extra, "wall")))
        self.assertEqual(sum(1 for e in c if e["type"] == "door"), len(of(extra, "door")))


if __name__ == "__main__":
    unittest.main()
