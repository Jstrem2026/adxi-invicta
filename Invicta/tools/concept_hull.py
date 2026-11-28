"""Concept hull, Revision C (canon: errata C9, approved by Jordan 28 Nov 2026).

Jordan's six-view concept sheet (Game/Docs/art/concept/invicta-concept-six-views.png) shows the Invicta
with a pointed bow, wide armoured flanks, a blunt stern with four big engine nozzles, and raised dorsal
fins toward the stern. This tool turns the TOP and LEFT views of that sheet into hull outlines at the
canon size and writes them to Game/Docs/geometry_revC/ (and its mirror in Docs/2_Design_Docs/).

    python tools/concept_hull.py          rewrite the Rev C outline files (hull top and side views, and
                                          crown_revC.json for the Crown and Crown Bridge) from the points below

How it works
- The points below were read off the concept sheet by hand (image pixels, 1376 x 768 sheet).
- They are scaled to the canon size: 34.0 km (21.13 mi) long, 12.4 km (7.71 mi) beam, 4.1 km (2.55 mi)
  keel to dorsal plating. The dorsal fins keep their drawn height above that (about 5.16 km / 3.20 mi).
- The concept bow and stern are sharper than the decks allow, so each traced shape is joined with the
  current hull (canon top view, Rev B side profile). The new hull is never smaller than the old one at
  any point, so every deck, district, precinct and building stays exactly where it is.
"""
import argparse
import json
import math
import os

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(APP)
CANON_PLAN = "Docs/1_Canon_Source/Invicta/architecture/hull_plan_km.csv"
REVB_SIDE = "Game/Docs/geometry_revB/hull_side_profile_km_revB.csv"
OUT_DIRS = ["Game/Docs/geometry_revC", "Docs/2_Design_Docs/geometry_revC"]

LENGTH_KM, HALF_BEAM_KM, HULL_HEIGHT_KM = 34.0, 6.193, 4.1

# TOP view: bow tip at x 670, stern (nozzle rims) at x 80, centreline at y 193.
# (x px, half-width px) from stern to bow; the widest point (121 px) is the canon half beam.
TOP_TIP_X, TOP_STERN_X, TOP_MAX_HW = 670, 80, 121
TOP_HALF_WIDTHS = [
    (80, 0), (80, 85), (86, 98), (100, 98), (120, 102), (150, 108), (170, 116), (200, 120), (250, 121),
    (300, 118), (350, 114), (400, 108), (430, 112), (460, 111), (480, 95), (500, 93), (530, 83), (550, 70),
    (600, 54), (630, 45), (650, 33), (665, 15), (670, 0),
]

# LEFT view: bow tip at x 677, stern at x 63, keel at y 515, dorsal plating at y 418 (= 4.1 km).
SIDE_TIP_X, SIDE_STERN_X, SIDE_KEEL_Y, SIDE_DORSAL_Y = 677, 63, 515, 418
# The raised block the sheet draws toward the stern is left out (Jordan, 28 Nov 2026: the raised part on top
# is the bridge, where the front windows are). The Crown below takes its place.
SIDE_TOP = [  # stern to bow, dorsal plating only
    (63, 432), (70, 425), (85, 418), (480, 418), (500, 422), (550, 429), (600, 438), (650, 451), (670, 459),
    (677, 466.5),
]
SIDE_BOTTOM = [  # bow to stern
    (650, 480), (600, 486), (550, 492), (500, 503), (460, 511), (420, 515),
    (130, 515), (120, 510), (100, 505), (63, 505),
]


# The Crown on the dorsal hull (Jordan, 28 Nov 2026: "at the top needs to be the bridge, where the front
# windows are"; "add another level (like deck 1 but smaller) on top of deck 1 for the bridge").
# Placed over the windowed module of the TOP view: its window front at 10.7 km from the prow (Jordan's pin on the
# LEFT view: about 10.8 km), its back 8 km behind, matching the canon "Crown, about 8 km long, on the dorsal hull".
# Inside it is the Bridge Level: like Deck 1 (380 m clear, 60 m service layer below it), 120 m in from the Crown's
# sides. The Crown Bridge (canon 1.2 x 0.48 x 0.15 km) sits at the Bridge Level's front, behind the windows.
# The windows step down to the hull in three terraces, as the concept draws them. Heights follow the deck stack;
# the terrace steps are an assumption.
CROWN = {
    "status": "canon",
    "x_front_km": 10.7, "x_back_km": 18.7, "half_width_km": 2.6, "nose_km": 1.3,
    "z_base_km": 4.1, "z_top_km": 4.54, "terraces_km": [[0.0, 4.24], [0.15, 4.39], [0.3, 4.54]], "back_slope_km": 0.3,
    "bridge_level": {"name": "Bridge Level", "floor_m": 3980, "ceiling_m": 4360, "inset_km": 0.12,
                     "note": "Like Deck 1 but smaller: 380 m clear, on a 60 m service layer above Deck 1's ceiling (3,920 m)."},
    "bridge": {"length_km": 1.2, "beam_km": 0.48, "height_km": 0.15, "x_front_km": 10.95},
}


def crown_shapes():
    c, b, lv = CROWN, CROWN["bridge"], CROWN["bridge_level"]
    x0, x1, hw, nose = c["x_front_km"], c["x_back_km"], c["half_width_km"], c["nose_km"]
    arc = [(x0 + nose * (1 - math.sin(math.radians(a))), -hw * math.cos(math.radians(a))) for a in range(0, 91, 10)]
    pts = [(x1, -hw + 0.3), (x1 - 0.3, -hw)] + [p for p in sorted(arc, key=lambda q: -q[0])]
    plan = Polygon(pts + [(x, -y) for x, y in reversed(pts) if abs(y) > 1e-9])
    level = plan.buffer(-lv["inset_km"], join_style=2)
    zb, zt = c["z_base_km"], c["z_top_km"]
    side = [(x0, zb)]
    for dx, z in c["terraces_km"]:
        side += [(x0 + dx, side[-1][1]), (x0 + dx, z)]
    side = [side[0]] + side[2:] + [(x1 - c["back_slope_km"], zt), (x1, zb)]
    lx0, lx1 = level.bounds[0], level.bounds[2]
    fl, ce = lv["floor_m"] / 1000.0, lv["ceiling_m"] / 1000.0
    lside = [(lx0, fl), (lx0, ce), (lx1, ce), (lx1, fl)]
    bx0, bx1, by = b["x_front_km"], b["x_front_km"] + b["length_km"], b["beam_km"] / 2
    bplan = [(bx0, -by), (bx1, -by), (bx1, by), (bx0, by)]
    bside = [(bx0, fl), (bx0, fl + b["height_km"]), (bx1, fl + b["height_km"]), (bx1, fl)]
    r = lambda ps: [[round(x, 3) + 0.0, round(y, 3) + 0.0] for x, y in ps]
    return {"crown_plan_km": r(list(plan.exterior.coords)[:-1]), "crown_side_km": r(side),
            "level_plan_km": r(list(level.exterior.coords)[:-1]), "level_side_km": r(lside),
            "level_area_km2": round(level.area, 2),
            "bridge_plan_km": r(bplan), "bridge_side_km": r(bside)}


# Deck trimming (Jordan, 28 Nov 2026: "you can cut back the decks"). Each deck keeps its Rev B outline and is cut
# square across where the concept side view can no longer hold it with its armour (180 m above and below).
ARMOR_KM = 0.18
DECK_FILES = {1: "Solenne", 2: "Halcyon", 3: "Meridian", 4: "Bastion", 5: "Aerion", 6: "Machina", 7: "Claustra", 8: "Ferrum"}
DECK_LEVELS_M = {1: (3540, 3920), 2: (3100, 3480), 3: (2660, 3040), 4: (2220, 2600), 5: (1560, 2160), 6: (1120, 1500),
                 7: (680, 1060), 8: (240, 620)}   # canon floor / ceiling (Sheets S1-S8)


def deck_range(side, n):
    """Bow and stern x (km) between which the side view holds deck n and its armour, to 10 m."""
    fl, ce = (v / 1000.0 for v in DECK_LEVELS_M[n])
    good = [i / 100.0 for i in range(0, 3401) if side.contains(box(i / 100.0 - 0.005, fl - ARMOR_KM, i / 100.0 + 0.005, ce + ARMOR_KM))]
    return good[0] - 0.005, good[-1] + 0.005


def deck_outline(n, kind):
    for rel in ("Game/Docs/geometry_revB/deck%d_%s_%s_km_revB.csv" % (n, DECK_FILES[n], kind),
                "Docs/1_Canon_Source/Invicta/architecture/deck%d_%s_%s_km.csv" % (n, DECK_FILES[n], kind)):
        if os.path.isfile(os.path.join(ROOT, *rel.split("/"))):
            return Polygon(read_csv(rel)).buffer(0)
    raise SystemExit("No outline for deck %d (%s)." % (n, kind))


def trimmed_decks(side):
    out = {}
    for n in DECK_FILES:
        x0, x1 = deck_range(side, n)
        res = {}
        for kind in ("net", "gross"):
            old = deck_outline(n, kind)
            new = old.intersection(box(max(x0, old.bounds[0]), -8, min(x1, old.bounds[2]), 8))
            if new.geom_type != "Polygon":
                new = max(new.geoms, key=lambda g: g.area)
            res[kind] = (old, new)
        out[n] = res
    return out


def read_csv(rel):
    with open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as f:
        rows = [ln.strip().split(",") for ln in f if ln.strip()][1:]
    return [(float(a), float(b)) for a, b in rows]


def concept_plan():
    kx = LENGTH_KM / (TOP_TIP_X - TOP_STERN_X)
    ky = HALF_BEAM_KM / TOP_MAX_HW
    port = [((TOP_TIP_X - x) * kx, -h * ky) for x, h in TOP_HALF_WIDTHS]
    return Polygon(port + [(x, -y) for x, y in reversed(port[1:-1])]).buffer(0)


def concept_side():
    kx = LENGTH_KM / (SIDE_TIP_X - SIDE_STERN_X)
    kz = HULL_HEIGHT_KM / (SIDE_KEEL_Y - SIDE_DORSAL_Y)
    return Polygon([((SIDE_TIP_X - x) * kx, (SIDE_KEEL_Y - y) * kz) for x, y in SIDE_TOP + SIDE_BOTTOM]).buffer(0)


def points(g):
    """Outline points from the prow tip, rounded to 1 m."""
    pts = [(round(x, 3) + 0.0, round(y, 3) + 0.0) for x, y in list(g.exterior.coords)[:-1]]
    i = min(range(len(pts)), key=lambda k: (pts[k][0], abs(pts[k][1])))
    return pts[i:] + pts[:i]


def build():
    plan = unary_union([concept_plan(), Polygon(read_csv(CANON_PLAN))]).simplify(0.005)
    side = concept_side().simplify(0.005)   # the decks are trimmed to it (below)
    return points(plan), points(side)


def write(rel, header, pts):
    for d in OUT_DIRS:
        p = os.path.join(ROOT, *d.split("/"), rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(header + "\n" + "".join("%s,%s\n" % (_n(x), _n(y)) for x, y in pts))


def _n(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0.0" if s in ("0", "-0") else s


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    plan, side = build()
    write("hull_plan_km_revC.csv", "x_km_from_prow,y_km_port_neg", plan)
    write("hull_side_profile_km_revC.csv", "x_km_from_prow,z_km_above_keel", side)
    crown = dict(CROWN, note="The Crown, its Bridge Level and the Crown Bridge (Rev C, canon 28 Nov 2026, errata C9; the Bridge is part of the ship and cannot separate, errata C11). "
                 "Axes as the hull files. Place and level from Jordan; the terrace steps are an assumption.", **crown_shapes())
    for d in OUT_DIRS:
        with open(os.path.join(ROOT, *d.split("/"), "crown_revC.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(crown, f, indent=1)
            f.write("\n")
    total = 0.0
    for n, res in trimmed_decks(Polygon(side)).items():
        for kind, (old, new) in res.items():
            write("deck%d_%s_%s_km_revC.csv" % (n, DECK_FILES[n], kind), "x_km_from_prow,y_km_port_neg", points(new))
        old, new = res["net"]
        total += new.area
        print("Deck %d %s: net %.1f -> %.1f km2, runs %.2f to %.2f km" % (n, DECK_FILES[n], old.area, new.area, new.bounds[0], new.bounds[2]))
    print("Total net city floor: %.1f km2. Bridge Level: %.2f km2." % (total, crown["level_area_km2"]))


if __name__ == "__main__":
    main()
