"""Tests for the city planner (atlaslib/planner.py), on a small made-up district and on the real Port of Arrivals."""
import copy
import json
import os
import subprocess
import unittest

from shapely.geometry import box

from atlaslib import geometry as G
from atlaslib import planner as PL

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# One hull precinct 2 km long, hull along y = -1.0, with a row of three berths (each with a hull door)
# and a harbourmaster. Lanes and frames line up with the ship grid.
DIST = {"district": "Test Port", "precincts": [{
    "id": "P1", "name": "Bow Docks", "bounds_km": [10.0, 12.0, -1.0, -0.25],
    "polygon_km": [[10.0, -1.0], [12.0, -1.0], [12.0, -0.25], [10.0, -0.25]],
    "buildings": [
        {"id": "P1-01", "name": "Medium Berths", "kind": "bays", "rect_km": [10.1, 10.5, -1.0, -0.92],
         "bays_km": [[10.1, 10.22, -1.0, -0.92], [10.24, 10.36, -1.0, -0.92], [10.38, 10.5, -1.0, -0.92]],
         "doors_km": [[10.12, 10.2, -1.012, -1.0], [10.26, 10.34, -1.012, -1.0], [10.4, 10.48, -1.012, -1.0]]},
        {"id": "P1-02", "name": "Harbourmaster", "kind": "building", "category": "offices", "rect_km": [10.6, 10.9, -0.8, -0.6]},
    ],
    "streets": [{"name": "Dock Road", "rect_km": [10.0, 12.0, -0.88, -0.85]}]}]}

PROG = {"hull_precincts": ["P1"],
        "door_classes": [
            {"id": "berth", "name": "Berths", "use": "commercial", "match": "Berths", "control": "Harbourmaster", "min": 1},
            {"id": "military", "name": "Guard berths", "use": "military", "match": "Guard Berth", "control": "Port Guard", "min": 1},
            {"id": "crew", "name": "Crew airlocks", "use": "crew", "match": "Crew Airlocks", "min": 1}],
        "response": [{"id": "fire", "name": "Fire", "category": "fire", "within_km": 1.0}],
        "must_have": [], "per_precinct": [],
        "fixes": {
            "military": {"berth_size_m": [120, 80], "door_width_m": 80, "door_depth_m": 12, "name": "{end} Guard Berth",
                         "category": "police", "kind": "bays", "purpose": "p", "notes": "{end} {end_lower}"},
            "crew": {"chamber_m": [10, 8], "door_width_m": 1.829, "door_depth_m": 2, "door_note": "n", "name": "{pid} Crew Airlocks",
                     "category": "transit", "kind": "bays", "purpose": "p"},
            "response": {"fire": {"name": "{where} Fire Post", "size_m": [200, 150], "category": "fire", "purpose": "p"}}}}


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.d = copy.deepcopy(DIST)

    def test_doors_counted_by_class(self):
        res = PL.check(self.d, PROG)
        cls = {c["cls"]["id"]: c for c in res["classes"]}
        self.assertEqual(cls["berth"]["count"], 3)
        self.assertTrue(cls["berth"]["ok"])
        self.assertFalse(cls["military"]["ok"])
        self.assertEqual([b["name"] for b in cls["berth"]["control"]], ["Harbourmaster"])

    def test_pressure_zones_one_per_frame(self):
        res = PL.check(self.d, PROG)
        self.assertEqual([z["frame"] for z in res["zones"]], ["F20", "F21", "F22", "F23"])

    def test_fire_reach(self):
        res = PL.check(self.d, PROG)
        self.assertEqual(len(res["response"][0]["far"]), 3)   # no fire station at all

    def test_proposals_fill_every_gap_and_touch_nothing(self):
        before = copy.deepcopy(self.d)
        props = PL.propose(self.d, PROG)
        self.assertEqual(self.d, before)                     # propose() never edits the data
        d2 = copy.deepcopy(self.d)
        PL.apply(d2, props)
        after = PL.check(d2, PROG)
        self.assertTrue(all(c["ok"] for c in after["classes"]))
        self.assertTrue(all(z["airlocks"] for z in after["zones"]))
        self.assertFalse(after["response"][0]["far"])
        old = {b["id"]: b for b in before["precincts"][0]["buildings"]}
        for b in d2["precincts"][0]["buildings"]:
            if b["id"] in old:
                self.assertEqual(b, old[b["id"]])            # existing items unchanged
            else:
                self.assertEqual(b["status"], "proposed")

    def test_new_items_overlap_nothing_and_stay_in_the_precinct(self):
        d2 = copy.deepcopy(self.d)
        PL.apply(d2, PL.propose(self.d, PROG))
        p = d2["precincts"][0]
        area = PL.precinct_shape(p)
        shapes = [(b["id"], G.building_shape(b)) for b in p["buildings"]] + [("st", G.box_shape(s["rect_km"])) for s in p["streets"]]
        for i, (a, sa) in enumerate(shapes):
            if a != "st":
                self.assertTrue(area.buffer(1e-9).contains(sa), a)
            for b, sb in shapes[i + 1:]:
                self.assertLess(sa.intersection(sb).area, 1e-9, (a, b))

    def test_placed_box_never_crosses_the_grid(self):
        p = self.d["precincts"][0]
        r = PL.place_rect(p, [300, 200], (11.0, -0.5), [])
        self.assertIsNotNone(r)
        self.assertFalse(PL._crosses_grid(r))
        self.assertTrue(PL.precinct_shape(p).contains(box(r[0], r[2], r[1], r[3])))

    def test_apply_twice_adds_nothing(self):
        d2 = copy.deepcopy(self.d)
        props = PL.propose(self.d, PROG)
        self.assertTrue(PL.apply(d2, props))
        self.assertFalse(PL.apply(d2, props))


class PortOfArrivalsTest(unittest.TestCase):
    """The real district: every planner check passes, and the planner proposes nothing more."""

    def test_port_meets_its_program(self):
        progs, prog = PL.load_program(APP, "D5-port-of-arrivals")
        path, raw, d = PL.load_district(APP, prog)
        res = PL.check(d, prog)
        self.assertTrue(all(c["ok"] for c in res["classes"]), [c["cls"]["id"] for c in res["classes"] if not c["ok"]])
        self.assertTrue(all(z["airlocks"] for z in res["zones"]))
        # fire and border clearance are still out of reach only at the Stern Docks (P3), where every lot is taken
        for r in res["response"]:
            self.assertTrue(all(dr["precinct"] == "P3" for dr, b, dist in r["far"]), r["rule"]["id"])
        self.assertTrue(all(dr["precinct"] == "P3" for dr, b, dist in res["clearance"]["far"]))
        self.assertTrue(all(m["ok"] for m in res["must_have"]))
        gaps = []
        self.assertFalse(PL.propose(d, prog, res, gaps))   # nothing more fits
        self.assertTrue(all("P3" in g for g in gaps))      # only the full Stern Docks is left for Jordan


if __name__ == "__main__":
    unittest.main()
