"""Tests for Walk mode in the 3D view (web/walk.js), run in Node against fabric worked out by atlaslib/fabric.py.
Jordan, 27 Nov 2026: "I can walk through walls ... I can fly!" Walls stop you, doors let you through, you stay on the
floor, stairs and lifts change floors. Skipped where Node isn't installed."""
import json
import os
import shutil
import subprocess
import unittest

from atlaslib import fabric as FB

WALK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "walk.js")


def sp(i, x0, y0, x1, y1, kind="room", **kw):
    return dict({"id": i, "type": kind, "name": kw.pop("name", i), "levels": ["L1", "L2"],
                 "outline_m": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}, **kw)


# Two floors, 13 ft (4 m) each: a corridor along the south (y 0-4), an office (x 0-10) and a stair core (x 10-20) north of it.
PLAN = {"footprint_m": [20, 14], "levels": [{"id": "L1", "z_m": 0, "height_m": 4}, {"id": "L2", "z_m": 4, "height_m": 4}],
        "elements": [sp("C", 0, 0, 20, 4, "zone", name="Corridor"), sp("A", 0, 4, 10, 14, name="Office"),
                     sp("S", 10, 4, 20, 14, "core", name="Stairs and lifts")]}
BUILDING = {"uid": "T-1", "rect_km": [0, 0.02, 0, 0.014]}

SCRIPT = r"""
const W = require(process.argv[1]);
const {model, b} = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const w = W.make([{b, model, gx: 0, gz: 0}]);
const out = {};
const walk = (secs, keys) => { for (let i = 0; i < secs * 60; i++) w.step(1 / 60, keys); return {x: w.me.x, z: w.me.z, feet: w.me.feet}; };
const ent = w.start([-8, 7, Math.PI / 2]);
out.start = {x: w.me.x, z: w.me.z, feet: w.me.feet, entrance: ent && ent.name};
out.walkIn = walk(4, {f: true});
out.inside = !!w.where();
// into a wall: stand in the corridor, face the office wall (north, +z) away from its door, and walk for 5 s
const doorA = model.elements.find((e) => e.type === 'door' && Math.abs(e.line_m[0][1] - 4) < 0.01 && e.line_m[0][0] < 10);
const dx = (doorA.line_m[0][0] + doorA.line_m[1][0]) / 2;
w.place(dx < 5 ? 8 : 2, 2, 0);
out.wall = walk(5, {f: true});
// through the office door
w.place(dx, 2, 0);
out.door = walk(3, {f: true});
// no flying: run about for a while, feet stay on a floor
w.place(4, 2, Math.PI / 2);
out.run = walk(3, {f: true, run: true});
// up the stair: first flight along its long side, across the half landing, back up the return flight
const st = model.elements.find((e) => e.type === 'stair'), o = st.outline_m;
const u = [o[1][0] - o[0][0], o[1][1] - o[0][1]], v = [o[3][0] - o[0][0], o[3][1] - o[0][1]];
const Lu = Math.hypot(...u), Lv = Math.hypot(...v), uu = u.map((q) => q / Lu), vv = v.map((q) => q / Lv);
const at = (s, t) => [o[0][0] + uu[0] * s + vv[0] * t, o[0][1] + uu[1] * s + vv[1] * t], yaw = (d) => Math.atan2(d[0], d[1]);
let p = at(0.5, Lv / 4); w.place(p[0], p[1], yaw(uu));
walk((Lu - st.landing_m / 2 - 0.5) / 1.6, {f: true});
w.me.yaw = yaw(vv); walk(Lv / 2 / 1.6, {f: true});
w.me.yaw = yaw([-uu[0], -uu[1]]); out.stair = walk(Lu / 1.6, {f: true});
out.stairLevel = w.where() && w.where().id;
// a lift
const lf = model.elements.find((e) => e.type === 'lift');
const c = lf.outline_m.reduce((a, q) => [a[0] + q[0] / 4, a[1] + q[1] / 4], [0, 0]);
w.place(c[0], c[1], 0);
out.lift = [w.me.feet, (w.lift(1), w.me.feet), (w.lift(1), w.me.feet), (w.lift(-1), w.me.feet)];
w.place(3, 2, 0);
out.noLift = w.lift(1);
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "Node is not installed")
class Walk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = FB.with_fabric(PLAN)
        r = subprocess.run(["node", "-e", SCRIPT, WALK], input=json.dumps({"model": cls.model, "b": BUILDING}),
                           capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise AssertionError(r.stderr)
        cls.out = json.loads(r.stdout)

    def test_you_start_outside_an_entrance_and_walk_in(self):
        s = self.out["start"]
        self.assertEqual(s["entrance"], "Entrance")
        self.assertEqual(s["feet"], 0)                         # on the deck outside
        self.assertTrue(self.out["inside"])
        self.assertAlmostEqual(self.out["walkIn"]["feet"], 0.3, places=3)   # up the step onto the ground floor

    def test_a_wall_stops_you(self):
        self.assertLess(self.out["wall"]["z"], 4 - FB.T_PARTITION / 2 - 0.25 + 0.01)   # corridor side of the partition, 10 in (0.25 m) away

    def test_a_door_lets_you_through(self):
        self.assertGreater(self.out["door"]["z"], 4.5)

    def test_you_stay_on_the_floor(self):
        self.assertAlmostEqual(self.out["run"]["feet"], 0.3, places=3)

    def test_the_stairs_take_you_up_a_floor(self):
        self.assertAlmostEqual(self.out["stair"]["feet"], 4.3, delta=0.05)
        self.assertEqual(self.out["stairLevel"], "L2")

    def test_a_lift_goes_floor_to_floor_only_when_you_are_in_it(self):
        self.assertEqual(self.out["lift"], [0.3, 4.3, 4.3, 0.3])
        self.assertFalse(self.out["noLift"])

    def test_doorways_are_cut_out_of_the_walls(self):
        r = subprocess.run(["node", "-e", "const W=require(process.argv[1]);const m=JSON.parse(require('fs').readFileSync(0,'utf8'));"
                            "const c=W.cutWalls(m);console.log(JSON.stringify(Object.fromEntries(Object.entries(c).map(([k,v])=>[k,[v.gaps.length,v.doors.length]]))))", WALK],
                           input=json.dumps(self.model), capture_output=True, text=True, timeout=60)
        got = json.loads(r.stdout)
        for lv, (gaps, doors) in got.items():
            self.assertGreaterEqual(gaps, doors, lv)           # every door and opening makes a gap in a wall


if __name__ == "__main__":
    unittest.main()
