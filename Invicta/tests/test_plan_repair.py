"""Tests for the plan repair pass (atlaslib/plan_repair.py) and the exact wall bands of the room designer
(tools/plan_geometry.py), plan step 4."""
import os
import sys
import unittest

import shapely
from shapely.geometry import Polygon

from atlaslib import plan_repair as R
from atlaslib.rooms import check_plan

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import plan_geometry as PG  # noqa: E402


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def el(i, outline, kind="room", level="L1", **kw):
    return dict({"id": i, "type": kind, "name": kw.pop("name", i), "level": level, "outline_m": outline,
                 "about": "What %s does." % i}, **kw)


def plan(elements, levels=None):
    return {"footprint_m": [40, 20], "elements": elements,
            "levels": levels or [{"id": "L1", "z_m": 0, "height_m": 4}]}


BUILDING = {"id": "P1-01", "name": "Test Hall", "rect_km": [1.0, 1.04, 0.0, 0.02]}  # 40 x 20 m


def titles(m, b=BUILDING):
    return {t for t, _, _ in check_plan(m, b)}


def area(e):
    return Polygon(e["outline_m"]).area


def by_id(m):
    return {e["id"]: e for e in m["elements"]}


class Repair(unittest.TestCase):
    def test_overlaps_go_to_the_core_then_the_corridor_then_the_smaller_room(self):
        m = plan([el("H", rect(0, 0, 30, 20), name="Hall"),           # big hall
                  el("O", rect(25, 0, 35, 10), name="Office"),        # small office overlapping the hall
                  el("C", rect(0, 8, 40, 12), "zone", name="Corridor"),
                  el("S", rect(30, 12, 40, 20), "core", name="Stairs and lifts")])
        self.assertIn("Rooms overlap", titles(m))
        R.repair(m, BUILDING)
        self.assertNotIn("Rooms overlap", titles(m))
        e = by_id(m)
        self.assertAlmostEqual(area(e["S"]), 80, places=3)          # the core keeps all of its floor
        self.assertAlmostEqual(area(e["C"]), 160, places=3)         # the corridor keeps all of its floor
        self.assertGreater(area(e["O"]), 40)                        # the office keeps its corner
        for k in "HOCS":                                            # names, floors and "about" are kept
            self.assertEqual(e[k]["about"], "What %s does." % k)
            self.assertEqual(e[k]["level"], "L1")

    def test_rooms_are_trimmed_to_the_outline_and_out_of_the_courtyard(self):
        b = dict(BUILDING, outline_km=[[[1.0, 0.0], [1.04, 0.0], [1.04, 0.02], [1.0, 0.02]]],
                 holes_km=[[[1.015, 0.005], [1.025, 0.005], [1.025, 0.015], [1.015, 0.015]]])
        m = plan([el("A", rect(-5, 0, 20, 20)), el("B", rect(20, 0, 40, 20))])
        self.assertIn("Rooms outside the building", titles(m, b))
        R.repair(m, b)
        self.assertNotIn("Rooms outside the building", titles(m, b))
        self.assertNotIn("Rooms overlap", titles(m, b))
        foot = R.building_frame_shape(b)
        for e in m["elements"]:
            self.assertTrue(foot.buffer(0.02).covers(Polygon(e["outline_m"])))
            self.assertTrue(Polygon(e["outline_m"]).is_valid)

    def test_a_crossed_outline_is_untangled(self):
        m = plan([el("X", [[0, 0], [10, 10], [10, 0], [0, 10]])])  # a bow tie
        self.assertIn("Room outlines cross themselves", titles(m))
        rep = R.repair(m, BUILDING)
        self.assertEqual(rep["untangled"], 1)
        self.assertNotIn("Room outlines cross themselves", titles(m))
        self.assertEqual({e["name"] for e in m["elements"]}, {"X"})

    def test_a_room_cut_in_two_keeps_its_id_and_the_other_piece_is_a_new_room(self):
        m = plan([el("R", rect(0, 0, 40, 10), name="Workshop"), el("C", rect(18, 0, 22, 20), "zone", name="Corridor")])
        rep = R.repair(m, BUILDING)
        rooms = [e for e in m["elements"] if e["name"] == "Workshop"]
        self.assertEqual(len(rooms), 2)
        self.assertEqual(rep["added"], 1)
        self.assertIn("R", {e["id"] for e in rooms})
        new = [e for e in rooms if e["id"] != "R"][0]
        self.assertEqual(new["piece_of"], "R")
        self.assertEqual(new["about"], "What R does.")
        self.assertNotIn("Rooms overlap", titles(m))

    def test_a_core_inside_a_hall_leaves_no_hole(self):
        m = plan([el("H", rect(0, 0, 40, 20), name="Hall"), el("S", rect(15, 6, 25, 14), "core")])
        R.repair(m, BUILDING)
        self.assertNotIn("Rooms overlap", titles(m))
        halls = [e for e in m["elements"] if e["name"] == "Hall"]
        self.assertAlmostEqual(sum(area(e) for e in halls), 800 - 80, places=2)

    def test_a_sliver_joins_its_neighbour(self):
        m = plan([el("A", rect(0, 0, 20, 20)), el("B", rect(20, 0, 20.8, 20), name="Store"), el("C", rect(20.8, 0, 40, 20))])
        self.assertIn("Rooms too narrow to use", titles(m))
        rep = R.repair(m, BUILDING)
        self.assertEqual(rep["merged"], 1)
        self.assertNotIn("Rooms too narrow to use", titles(m))
        self.assertAlmostEqual(sum(area(e) for e in m["elements"]), 800, places=1)

    def test_different_floors_are_not_trimmed_against_each_other(self):
        lv = [{"id": "L1", "z_m": 0, "height_m": 4}, {"id": "L2", "z_m": 4, "height_m": 4}]
        m = plan([el("A", rect(0, 0, 40, 20)), el("B", rect(0, 0, 40, 20), level="L2")], lv)
        R.repair(m, BUILDING)
        self.assertEqual([area(e) for e in m["elements"]], [800, 800])

    def test_a_clean_plan_is_left_alone(self):
        m = plan([el("A", rect(0, 0, 20, 20)), el("B", rect(20, 0, 40, 20))])
        before = [list(map(list, e["outline_m"])) for e in m["elements"]]
        rep = R.repair(m, BUILDING)
        self.assertEqual(rep["trimmed"], 0)
        self.assertEqual([Polygon(o).area for o in before], [area(e) for e in m["elements"]])


class Bands(unittest.TestCase):
    """The room designer's bands follow every wall, including courtyards, and their pieces never overlap."""

    def test_pieces_follow_a_courtyard_and_stay_inside(self):
        outer = [(0, 0), (100, 0), (100, 60), (0, 60)]
        court = [(30, 20), (30, 40), (70, 40), (70, 20)]
        layers = PG.band_layers(19.9, 8, 3, two_sided_inner=False)
        r = PG.Ribbon(outer, 19.9, layers, holes=[court])
        self.assertTrue(r.ok)
        floor = Polygon(outer, [court])
        a, b = layers[0][1], layers[0][2]
        L = r.length(a, b)
        # the middle line goes round the outside wall and round the courtyard
        self.assertGreater(L, 2 * (100 + 60) + 2 * (40 + 20) - 8 * 2 * (a + b) / 2 - 1)
        pieces = [Polygon(r.piece(a, b, s, s + 10)) for s in range(0, int(L) - 10, 10)]
        for p in pieces:
            self.assertTrue(floor.buffer(0.1).covers(p))
        u = shapely.union_all(pieces)
        self.assertAlmostEqual(u.area, sum(p.area for p in pieces), delta=0.05 * u.area)

    def test_a_curved_outline_keeps_its_corners(self):
        # a quarter-round end: the old offsets cut across curves like this one
        import math
        arc = [(60 + 40 * math.cos(t / 20 * math.pi / 2), 40 * math.sin(t / 20 * math.pi / 2)) for t in range(21)]
        ring = [(0, 0)] + arc + [(0, 40)]
        r = PG.Ribbon(PG.ccw(ring), 12, [("rooms", 0, 12)])
        L = r.length(0, 12)
        pieces = [Polygon(r.piece(0, 12, s, s + 5)) for s in range(0, int(L) - 5, 5)]
        floor = Polygon(ring)
        self.assertTrue(all(floor.buffer(0.1).covers(p) for p in pieces))
        self.assertGreater(shapely.union_all(pieces).area, 0.9 * (floor.area - floor.buffer(-12).area))

    def test_inradius_is_the_deepest_point(self):
        self.assertAlmostEqual(PG.inradius([(0, 0), (40, 0), (40, 20), (0, 20)]), 10, delta=0.1)


if __name__ == "__main__":
    unittest.main()
