"""Give buildings their map colour category and a shaped footprint (Jordan, 27 Nov 2026).

    python tools/shape_buildings.py                      store a colour category on every building, every deck
    python tools/shape_buildings.py D5/port-of-arrivals  also shape that district's buildings inside their lots

Shaping keeps every building's lot (rect_km, so sizes, blocks and the design doc stay as they are) and
draws the building inside it:
  * a building with a stored plan (data/models/<uid>.json) gets the outline of its plan: the union of
    its rooms, halls, cores and walkways on every level (outdoor yards and gardens left out);
  * any other building gets a shape that suits its use (courtyard, L, U, curved front, rounded, oval),
    halls, yards and transport keep their full box, bay rows keep their bays.
The Deck 5 districts made by seed_deck5_districts.py are shaped there instead (their buildings follow
their blocks). Data files keep their own JSON layout.
"""
import json
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
from atlaslib import footprints as FP  # noqa: E402
from atlaslib import geometry as G  # noqa: E402
from atlaslib.categories import categorize  # noqa: E402

DECKS = os.path.join(APP, "data", "decks")
MODELS = os.path.join(APP, "data", "models")
SOLID = ("mass", "room", "zone", "core")


def plan_outline(b, model):
    polys = [e["outline_m"] for e in model.get("elements", []) if e.get("type") in SOLID and not e.get("outdoor") and e.get("outline_m")]
    if not polys:
        return None
    r = b["rect_km"]
    outers, holes = FP.union_outline(polys, r[0], r[2])
    if not outers:
        return None
    full = (r[1] - r[0]) * (r[3] - r[2])
    area = sum(FP.signed_area(o) for o in outers) - sum(abs(FP.signed_area(h)) for h in holes)
    if len(outers) == 1 and not holes and len(outers[0]) == 4 and area > 0.995 * full:
        return None   # the plan fills its whole lot: the box already is the outline
    return outers, holes


def shape_district(data, did):
    k = 0
    counts = {}
    for p in data["precincts"]:
        for b in p["buildings"]:
            if not b.get("rect_km") or b.get("bays_km"):
                continue
            uid = "D%d-%s-%s" % (data["deck"], did.split("/")[1], b["id"])
            mp = os.path.join(MODELS, uid + ".json")
            r = list(b["rect_km"])
            if os.path.isfile(mp):
                with open(mp, encoding="utf-8") as f:
                    got = plan_outline(b, json.load(f))
                for key in ("outline_km", "holes_km", "shape"):
                    b.pop(key, None)
                if got:
                    outers, holes = got
                    b["outline_km"] = [[[round(x, 4), round(y, 4)] for x, y in o] for o in outers]
                    if holes:
                        b["holes_km"] = [[[round(x, 4), round(y, 4)] for x, y in h] for h in holes]
                    b["shape"] = FP.SHAPE_WORDS["plan"]
                    counts["from its plan"] = counts.get("from its plan", 0) + 1
                continue
            if b.get("kind") == "transport" or b.get("status") == "canon":
                continue   # stations, roads and canon footprints keep their box
            st = FP.apply(b, G.rect_poly(r), k)
            b["rect_km"] = r   # the lot stays exactly as listed
            if st == "solid":
                for key in ("outline_km", "holes_km", "shape"):
                    b.pop(key, None)
            else:
                counts[b["shape"]] = counts.get(b["shape"], 0) + 1
            k += 1
    return counts


def main():
    shape = set(sys.argv[1:])
    for deck in sorted(os.listdir(DECKS)):
        for fn in sorted(os.listdir(os.path.join(DECKS, deck))):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(DECKS, deck, fn)
            raw = open(path, encoding="utf-8").read()
            data = json.loads(raw)
            did = "%s/%s" % (deck, fn[:-5])
            for p in data["precincts"]:
                for b in p["buildings"]:
                    b["category"] = categorize(b)
            note = ""
            if did in shape:
                note = " · shapes: %s" % shape_district(data, did)
            m = re.match(r'\{\n( +)"', raw)
            if m:
                txt = json.dumps(data, ensure_ascii=False, indent=len(m.group(1)))
            elif raw.startswith('{"schema": '):
                txt = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))
            else:
                txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(txt + ("\n" if raw.endswith("\n") else ""))
            print("%-28s categories stored%s" % (did, note))


if __name__ == "__main__":
    main()
