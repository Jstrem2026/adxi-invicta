"""Build the scene for each building's concept render (tools/concepts/render.mjs draws it).

    python tools/concepts/scene.py D5/atrium-plaza OUT_DIR [P1-01 ...]

Writes OUT_DIR/<uid>.json: the building's outline, floors, cores and open-air zones from its room plan, plus
its neighbours (outline and height) and the streets around it, all in metres with the building's centre at 0,0.
"""
import json
import math
import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(APP, "data")
sys.path.insert(0, APP)
from atlaslib import categories as CAT  # noqa: E402

ACCENT = {"transit": "#9aa4ae", "police": "#3d7bff", "fire": "#ff3b30", "medical": "#ff5a5a", "homes": "#ffc98a",
          "shops": "#ff9a3c", "offices": "#b78cff", "industry": "#7fd8ff", "utilities": "#ffd23f", "parks": "#7dff9a",
          "schools": "#3fe0c8", "keelway": "#6fd0ff"}


def km_ring(ring, ox, oy):
    return [[round(p[0] * 1000 - ox, 1), round(p[1] * 1000 - oy, 1)] for p in ring]


def rect_ring(r):
    return [[r[0], r[2]], [r[1], r[2]], [r[1], r[3]], [r[0], r[3]]]


def scene(data, p, b, did):
    r = b["rect_km"]
    ox, oy = (r[0] + r[1]) / 2 * 1000, (r[2] + r[3]) / 2 * 1000
    uid = "%s-%s" % (did, b["id"])
    mp = os.path.join(DATA, "models", uid + ".json")
    model = json.load(open(mp, encoding="utf-8")) if os.path.isfile(mp) else None
    cat = b.get("category") or "industry"
    out = {"uid": uid, "id": b["id"], "name": b["name"], "district": data["district"], "precinct": "%s %s" % (p["id"], p["name"]),
           "kind": b["kind"], "category": cat, "accent": ACCENT.get(cat, "#7fd8ff"),
           "look": b.get("look") or "", "height": b.get("height_m") or 10,
           "rings": [km_ring(o, ox, oy) for o in (b.get("outline_km") or [rect_ring(r)])],
           "holes": [km_ring(h, ox, oy) for h in (b.get("holes_km") or [])],
           "size": [(r[1] - r[0]) * 1000, (r[3] - r[2]) * 1000]}
    if model:
        lx, ly = r[0] * 1000 - ox, r[2] * 1000 - oy
        loc = lambda poly: [[round(q[0] + lx, 1), round(q[1] + ly, 1)] for q in poly]
        out["levels"] = [{"z": l["z_m"], "h": l["height_m"]} for l in model["levels"] if l["z_m"] >= 0]
        lvz = {l["id"]: l for l in model["levels"]}
        els = []
        for e in model["elements"]:
            if e["type"] == "core":
                els.append({"t": "core", "p": loc(e["outline_m"])})
            elif e.get("outdoor") or e["type"] == "fixture" or (e["type"] == "room" and b["kind"] in ("park", "yard", "plaza")):
                ls = [lvz[i] for i in (e.get("levels") or [e.get("level")]) if i in lvz]
                top = max((l["z_m"] + l["height_m"] for l in ls), default=4)
                els.append({"t": "zone" if e.get("outdoor") else ("fix" if e["type"] == "fixture" else "room"),
                            "n": e["name"], "p": loc(e["outline_m"]), "h": top})
            elif e["type"] == "room" and e.get("full_height"):
                ls = [lvz[i] for i in e.get("levels", []) if i in lvz]
                if ls:
                    els.append({"t": "hall", "n": e["name"], "p": loc(e["outline_m"]), "h": max(l["z_m"] + l["height_m"] for l in ls)})
        out["els"] = els
    # neighbours within 900 m
    nb = []
    for q in data["precincts"]:
        for c in q["buildings"]:
            if c is b or not c.get("rect_km"):
                continue
            cr = c["rect_km"]
            cx, cy = (cr[0] + cr[1]) / 2 * 1000, (cr[2] + cr[3]) / 2 * 1000
            if math.hypot(cx - ox, cy - oy) > 1100:
                continue
            kind = c["kind"]
            h = c.get("height_m") or (0.3 if kind in ("park", "plaza", "yard", "transport", "bays") else 14)
            if kind in ("park", "plaza", "yard", "transport", "bays"):
                h = 0.3
            nb.append({"rings": [km_ring(o, ox, oy) for o in (c.get("outline_km") or [rect_ring(cr)])],
                       "holes": [km_ring(hh, ox, oy) for hh in (c.get("holes_km") or [])],
                       "h": h, "kind": kind, "cat": c.get("category") or "industry"})
        for st in q.get("streets", []):
            sr = st["rect_km"]
            cx, cy = (sr[0] + sr[1]) / 2 * 1000, (sr[2] + sr[3]) / 2 * 1000
            if abs(cx - ox) < 2500 and abs(cy - oy) < 2500:
                nb_st = [round(sr[0] * 1000 - ox, 1), round(sr[1] * 1000 - ox, 1), round(sr[2] * 1000 - oy, 1), round(sr[3] * 1000 - oy, 1)]
                out.setdefault("streets", []).append(nb_st)
    out["neighbours"] = nb
    return out


def main():
    file, outdir = sys.argv[1], sys.argv[2]
    only = set(sys.argv[3:])
    data = json.load(open(os.path.join(DATA, "decks", *file.split("/")) + ".json", encoding="utf-8"))
    did = "D%s-%s" % (data["deck"], os.path.basename(file))
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for p in data["precincts"]:
        for b in p["buildings"]:
            if b["kind"] == "transport" or (only and b["id"] not in only):
                continue
            s = scene(data, p, b, did)
            with open(os.path.join(outdir, s["uid"] + ".json"), "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False)
            n += 1
    print("%d scenes" % n)


if __name__ == "__main__":
    main()
