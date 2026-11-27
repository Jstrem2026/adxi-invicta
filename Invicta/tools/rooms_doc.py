"""Write the "buildings and rooms" design doc of a district from its data and room plans.

    python tools/rooms_doc.py D5/atrium-plaza          writes Game/Docs/Atrium_Plaza_Rooms.md and its mirror
    python tools/rooms_doc.py D5                       every district of the deck that has room plans

Jordan, 27 Nov 2026: "Put them all in the documentation. I want to know what each room does."
Organised by precinct, then building, then floor, then room. Rooms with the same name on a floor are
counted together. Floors with exactly the same rooms are shown once. Feet first, metric in brackets.
"""
import json
import math
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(APP)
DATA = os.path.join(APP, "data")
FT = 3.28084


def ft(m):
    return "{:,}".format(int(round(m * FT)))


def both(m):
    v = round(m, 1)
    return "%s ft (%s m)" % (ft(m), ("%.1f" % v).rstrip("0").rstrip("."))


def area(p):
    a = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def sq(m2):
    if m2 >= 10000:
        return "{:,} sq ft ({:,} m²)".format(int(round(m2 * 10.7639, -2)), int(round(m2, -1)))
    return "{:,} sq ft ({:,} m²)".format(int(round(m2 * 10.7639, -1)), int(round(m2)))


def doc_name(district):
    return district.replace("'", "").replace(" ", "_") + "_Rooms.md"


def levels_of(e):
    return e.get("levels") or [e.get("level")]


def building_section(b, uid, model):
    out = ["### %s · %s" % (b["id"], b["name"]), ""]
    if b.get("purpose"):
        out += ["**What it is for:** %s" % b["purpose"], ""]
    facts = []
    if b.get("height_m") is not None:
        facts.append("%s tall" % both(b["height_m"]))
    if b.get("floors"):
        facts.append(b["floors"])
    if b.get("floor_area_m2"):
        facts.append("%s of rooms" % sq(b["floor_area_m2"]))
    st = b.get("design_status") or "proposed"
    if facts:
        out += ["%s. Room plan %s." % (", ".join(facts).capitalize(), st), ""]
    if b.get("look"):
        out += ["**Look:** %s" % b["look"], ""]
    if not model:
        out += ["_No room plan yet._", ""]
        return out
    els = model["elements"]
    byid = {e["id"]: e for e in els}
    sig_levels = []
    for lv in model["levels"]:
        rows = {}
        for e in els:
            if e["type"] not in ("room", "zone") or lv["id"] not in levels_of(e):
                continue
            if e["type"] == "zone" and not e.get("outdoor") and not e.get("about"):
                continue
            if e["type"] == "zone" and e["name"] in ("Corridor",):
                continue
            k = e["name"]
            r = rows.setdefault(k, {"n": 0, "a": 0.0, "about": e.get("about") or "", "inside": [], "outdoor": e.get("outdoor")})
            r["n"] += 1
            r["a"] += area(e["outline_m"])
            for f in els:
                if f.get("parent") == e["id"] and f.get("name") and f["name"] not in r["inside"]:
                    r["inside"].append(f["name"])
        sig = tuple(sorted((k, v["n"]) for k, v in rows.items()))
        if sig_levels and sig_levels[-1][0] == sig:
            sig_levels[-1][1].append(lv)
        else:
            sig_levels.append((sig, [lv], rows))
    for sig, lvs, rows in sig_levels:
        if not rows:
            continue
        lv = lvs[0]
        tag = lv["name"].split(" · ")[0]
        nm = " · ".join(lv["name"].split(" · ")[1:])
        if len(lvs) > 1:
            head = "%s to %s · %s (%d identical floors)" % (tag, lvs[-1]["name"].split(" · ")[0], re.sub(r" \d+$", "", nm), len(lvs))
        else:
            head = "%s · %s" % (tag, nm)
        z = lv["z_m"]
        where = "deck level" if abs(z) < 0.05 else ("%s above the deck" % both(z) if z > 0 else "%s below the deck" % both(-z))
        out += ["#### %s" % head, "",
                "Floor at %s; %s floor to floor." % (where, both(lv["height_m"])), "",
                "| Room | How many | Floor area | What it does |", "|---|---|---|---|"]
        order = sorted(rows.items(), key=lambda kv: (kv[1]["outdoor"] is True, kv[0].startswith("Stairs")))
        for k, r in order:
            what = r["about"].replace("|", "/")
            if r["inside"]:
                what += " Inside: %s." % ", ".join(r["inside"])
            cnt = str(r["n"]) if r["n"] > 1 else "1"
            each = sq(r["a"] / r["n"]) + (" each" if r["n"] > 1 else "")
            out.append("| %s%s | %s | %s | %s |" % (k, " (open air)" if r["outdoor"] else "", cnt, each, what or "—"))
        out.append("")
    return out


def write(file):
    path = os.path.join(DATA, "decks", *file.split("/")) + ".json"
    data = json.load(open(path, encoding="utf-8"))
    slug = os.path.basename(file)
    did = "D%s-%s" % (data["deck"], slug)
    title = "%s: buildings and rooms" % data["district"]
    out = ["# %s" % title, "",
           "Deck %s · %s. Every building in the district, floor by floor, with every room and what it does "
           "(Jordan, 27 Nov 2026: \"I want to know what each room does\")." % (data["deck"], data["district"]), "",
           "This doc is written from the data by `Invicta/tools/rooms_doc.py`; change the building's room program "
           "(`Invicta/tools/room_programs/`) or its plan (`Invicta/data/models/`), then re-run it. Rooms with the "
           "same name on a floor are counted together; floors that are exactly alike are shown once. "
           "Room plans are **proposed** unless a building says otherwise. Sizes are US first, metric in brackets.", ""]
    n_b = n_r = 0
    for p in data["precincts"]:
        sec = []
        for b in p["buildings"]:
            uid = "%s-%s" % (did, b["id"])
            mp = os.path.join(DATA, "models", uid + ".json")
            model = json.load(open(mp, encoding="utf-8")) if os.path.isfile(mp) else None
            if not model and b["kind"] == "transport":
                continue
            sec += building_section(b, uid, model)
            n_b += 1
            if model:
                n_r += sum(len(levels_of(e)) if not e.get("full_height") else 1 for e in model["elements"] if e["type"] == "room")
        if sec:
            out += ["## %s · %s" % (p["id"], p["name"]), ""]
            if p.get("role"):
                out += [p["role"], ""]
            out += sec
    out.insert(4, "**%d buildings, %s rooms.**" % (n_b, "{:,}".format(n_r)))
    out.insert(5, "")
    text = "\n".join(out).rstrip() + "\n"
    name = doc_name(data["district"])
    for base in ("Game/Docs", "Docs/2_Design_Docs"):
        with open(os.path.join(ROOT, *base.split("/"), name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("Wrote Game/Docs/%s (and its mirror): %d buildings, %d rooms, %d KB." % (name, n_b, n_r, len(text.encode()) // 1024))


def main():
    arg = sys.argv[1]
    if "/" in arg:
        write(arg)
    else:
        d = os.path.join(DATA, "decks", arg)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                write("%s/%s" % (arg, fn[:-5]))


if __name__ == "__main__":
    main()
