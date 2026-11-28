"""Concept hull, Revision C (proposed 28 Nov 2026).

Jordan's six-view concept sheet (Game/Docs/art/concept/invicta-concept-six-views.png) shows the Invicta
with a pointed bow, wide armoured flanks, a blunt stern with four big engine nozzles, and raised dorsal
fins toward the stern. This tool turns the TOP and LEFT views of that sheet into hull outlines at the
canon size and writes them to Game/Docs/geometry_revC/ (and its mirror in Docs/2_Design_Docs/).

    python tools/concept_hull.py          rewrite the two Rev C outline files from the traced points below

How it works
- The points below were read off the concept sheet by hand (image pixels, 1376 x 768 sheet).
- They are scaled to the canon size: 34.0 km (21.13 mi) long, 12.4 km (7.71 mi) beam, 4.1 km (2.55 mi)
  keel to dorsal plating. The dorsal fins keep their drawn height above that (about 5.16 km / 3.20 mi).
- The concept bow and stern are sharper than the decks allow, so each traced shape is joined with the
  current hull (canon top view, Rev B side profile). The new hull is never smaller than the old one at
  any point, so every deck, district, precinct and building stays exactly where it is.
"""
import argparse
import os

from shapely.geometry import Polygon
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
SIDE_TOP = [  # stern to bow, including the dorsal fins
    (63, 432), (70, 425), (85, 415), (100, 410), (118, 407), (122, 393), (280, 393), (300, 402), (370, 402),
    (380, 412), (480, 416), (500, 422), (550, 429), (600, 438), (650, 451), (670, 459), (677, 466.5),
]
SIDE_BOTTOM = [  # bow to stern
    (650, 480), (600, 486), (550, 492), (500, 503), (450, 509), (400, 511), (350, 513), (300, 515),
    (130, 515), (120, 510), (100, 505), (63, 505),
]


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
    side = unary_union([concept_side(), Polygon(read_csv(REVB_SIDE))]).simplify(0.005)
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
    print("Wrote the Rev C concept hull: top view %d points, side view %d points." % (len(plan), len(side)))


if __name__ == "__main__":
    main()
