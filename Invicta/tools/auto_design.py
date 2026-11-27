"""Draft the architecture and room plan of every undesigned building in a precinct, from its footprint.

    python tools/auto_design.py D5/port-of-arrivals P2          draft P2's buildings (writes data + models)
    python tools/auto_design.py D5/port-of-arrivals P2 --dry    show what would be drafted
    python tools/auto_design.py D5/port-of-arrivals all         every precinct in the file

How it works (all numbers come from the footprint and data/typologies.json):
  1. The building's type is the first type in typologies.json whose words appear in its name or notes.
  2. Levels: below-deck levels, then podium levels, then typical floors, each at the type's floor height.
  3. Each level is laid out as bands of rooms either side of a corridor, running along the long side.
     Band count = short side / (2 x room depth + corridor), rounded; room length = long side / room count,
     so the rooms always fill the footprint exactly and never cross its edge.
  4. Every few rooms one cell is a stair-and-lift core that runs through all levels.
  5. Rooms are named from the type's program shares (for example 30 % Main hall); neighbours with the same
     name merge into one room. Identical upper floors share one set of rooms (an element can list many levels).
  6. Height, floors, structure, look, entrances, capacity, services and interior text are filled in;
     everything is marked "proposed". Buildings that already have a plan or a height, canon buildings,
     roads, plazas, parks and berths are left alone.
Plans are written to data/models/<building uid>.json (metres from the building's bow-port corner,
x toward the stern, y toward starboard), the same format the 2D plan and 3D view read.
"""
import argparse
import json
import math
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
TODAY = "2026-11-27"
SKIP_KINDS = {"plaza", "park", "bays"}
CAP = 110  # most rooms on one level (keeps big footprints readable)


def r1(v):
    return round(v + 0.0, 1)


def typ_for(b, types):
    # the name decides first; the notes only when the name matches no type (never for roads and yards)
    texts = [b.get("name", "").lower()] + ([] if b.get("kind") == "transport" else [(b.get("notes") or "").lower()])
    for text in texts:
        for t in types:
            for w in t["match"]:
                if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text):
                    return t
    return None


def split_program(n, program):
    """Names for n cells from program shares, in order."""
    names, tot = [], sum(s for _, s in program)
    acc, k = 0.0, 0
    bounds = []
    for name, s in program:
        acc += s / tot
        bounds.append((acc, name))
    for i in range(n):
        f = (i + 0.5) / n
        while k < len(bounds) - 1 and f > bounds[k][0]:
            k += 1
        names.append(bounds[k][1])
    return names


def layout(Lx, Wy, t, program, levels, key, bands_only=None, all_levels=None, with_cores=True):
    """Rooms for one set of identical levels. Returns (elements, room cells used)."""
    long_x = Lx >= Wy
    Ll, Ws = (Lx, Wy) if long_x else (Wy, Lx)
    c = min(t["corridor"], Ws * 0.25)
    b0 = 2 * t["depth"] + c
    nb = max(1, int(round(Ws / b0)))
    nb = min(nb, 8)
    bw = Ws / nb
    d = (bw - c) / 2
    n = max(2, int(round(Ll / t["module"])))
    n = min(n, max(2, CAP // (2 * nb)))
    rl = Ll / n
    k = max(3, int(round(60.0 / rl)))  # a core about every 60 m
    els, seq = [], [0]

    def pt(u, v):
        return [r1(u), r1(v)] if long_x else [r1(v), r1(u)]

    def rect(u0, v0, u1, v1):
        return [pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)]

    def add(typ, name, poly, lv):
        seq[0] += 1
        e = {"id": "%s-%03d" % (key, seq[0]), "type": typ, "name": name}
        if len(lv) == 1:
            e["level"] = lv[0]
        else:
            e["levels"] = lv
        e["outline_m"] = poly
        e["status"] = "proposed"
        els.append(e)

    cells = []  # (band, side, index, u0, v0, u1, v1)
    cores = []
    for bi in range(nb):
        if bands_only is not None and bi not in bands_only:
            continue
        v0 = bi * bw
        add("zone", "Corridor" if t["corridor"] < 8 else "Walkway", rect(0, v0 + d, Ll, v0 + d + c), levels)
        for side, (a, z) in enumerate(((v0, v0 + d), (v0 + d + c, v0 + bw))):
            for i in range(n):
                cell = (bi, side, i, i * rl, a, (i + 1) * rl, z)
                if with_cores and side == 0 and i % k == k // 2:
                    cores.append(cell)
                else:
                    cells.append(cell)
    names = split_program(len(cells), program)
    # merge neighbours in the same strip with the same name
    i = 0
    while i < len(cells):
        j = i
        while j + 1 < len(cells) and names[j + 1] == names[i] and cells[j + 1][:2] == cells[i][:2] and cells[j + 1][2] == cells[j][2] + 1:
            j += 1
        a, b = cells[i], cells[j]
        add("room", names[i], rect(a[3], a[4], b[5], b[6]), levels)
        i = j + 1
    for cl in cores:
        add("core", "Stairs and lifts", rect(cl[3], cl[4], cl[5], cl[6]), all_levels or levels)
    return els, {"nb": nb, "n": n, "rl": rl, "d": d, "c": c, "bw": bw, "long_x": long_x, "Ll": Ll, "Ws": Ws}


def area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2


def ft(m):
    return "{:,}".format(int(round(m * 3.28084)))


def nice(n):
    return int(round(n / 10.0) * 10) if n >= 100 else int(round(n))


def design(b, t, style):
    r = b["rect_km"]
    Lx, Wy = (r[1] - r[0]) * 1000, (r[3] - r[2]) * 1000
    levels, z = [], 0.0
    below = t.get("below") or []
    zb = 0.0
    for i, lv in enumerate(below):
        zb -= lv["h"]
        levels.append({"id": "LB%d" % (i + 1), "name": "Level B%d · %s" % (i + 1, lv["name"]), "z_m": r1(zb), "height_m": lv["h"], "status": "proposed"})
    floors = t["floors"]
    office_band = t.get("office_band")
    pod = t.get("podium", 0)
    above = []
    for i in range(floors):
        h = t.get("podium_h", t["floor_h"]) if i < pod else t["floor_h"]
        nm = "Ground floor" if i == 0 else ("Podium" if i < pod else "Upper floor")
        above.append({"id": "L%d" % (i + 1), "name": "Level %d · %s" % (i + 1, nm), "z_m": r1(z), "height_m": h, "status": "proposed"})
        z += h
    if office_band:
        above.append({"id": "L2", "name": "Level 2 · Office level", "z_m": r1(z), "height_m": 4.5, "status": "proposed"})
        z += 4.5
    levels = sorted(levels, key=lambda l: l["z_m"]) + above
    all_ids = [l["id"] for l in levels]
    els = []
    ground_ids = [l["id"] for l in above[:max(1, pod)]] if not office_band else ["L1"]
    e, info = layout(Lx, Wy, t, t["ground"], ground_ids, "L1", all_levels=all_ids)
    els += e
    typical = [l["id"] for l in above[max(1, pod):]] if not office_band else []
    if typical:
        bands = None
        if (t.get("towers") or t.get("courtyards")) and info["nb"] >= 2:
            bands = set(range(0, info["nb"], 2))
        e2, _ = layout(Lx, Wy, t, t["upper"], typical, "LT", bands_only=bands, with_cores=False)
        # cores stay where the ground floor put them (they run through all levels); drop upper rooms that sit on a core
        core_polys = [x["outline_m"] for x in els if x["type"] == "core"]
        def overlaps(p, q):
            ax0, ax1 = min(v[0] for v in p), max(v[0] for v in p)
            ay0, ay1 = min(v[1] for v in p), max(v[1] for v in p)
            bx0, bx1 = min(v[0] for v in q), max(v[0] for v in q)
            by0, by1 = min(v[1] for v in q), max(v[1] for v in q)
            return min(ax1, bx1) - max(ax0, bx0) > 0.5 and min(ay1, by1) - max(ay0, by0) > 0.5
        for x in e2:
            if x["type"] == "room" and any(overlaps(x["outline_m"], cp) for cp in core_polys):
                x["name"] += " (around the core)"
        if bands is not None:
            for x in els:
                if x["type"] == "core":
                    keep = [i for i in x["levels"] if i not in typical] if "levels" in x else x.get("level")
                    # cores outside the towers stop at the podium roof
                    yv = [p[1] if info["long_x"] else p[0] for p in x["outline_m"]]
                    band = int(min(yv) // info["bw"] + 1e-6)
                    if band not in bands and "levels" in x:
                        x["levels"] = keep
        els += e2
    if office_band:
        e3, _ = layout(Lx, Wy, dict(t, depth=min(12, t["depth"]), corridor=3, module=12), t["upper"], ["L2"], "L2", bands_only={0}, with_cores=False)
        # the office level sits over the first band only
        els += e3
    for lv, prog in zip([l for l in levels if l["z_m"] < 0], [t.get("below_program")] * len(below)):
        e4, _ = layout(Lx, Wy, dict(t, module=max(t["module"], 30)), prog or [["Plant rooms", 1]], [lv["id"]], lv["id"].replace("L", "B"), with_cores=False)
        els += e4
    # doors: main entrances in the middle of both long sides, plus a door on each short side
    long_x = Lx >= Wy
    Ll, Ws = (Lx, Wy) if long_x else (Wy, Lx)
    w = r1(min(24.0, max(4.0, Ll / 12)))
    def pt(u, v):
        return [r1(u), r1(v)] if long_x else [r1(v), r1(u)]
    for nm, a, bb in (("Main entrance", pt(Ll / 2 - w / 2, 0), pt(Ll / 2 + w / 2, 0)), ("Second entrance", pt(Ll / 2 - w / 2, Ws), pt(Ll / 2 + w / 2, Ws)),
                      ("Side door", pt(0, Ws / 2 - 3), pt(0, Ws / 2 + 3)), ("Side door", pt(Ll, Ws / 2 - 3), pt(Ll, Ws / 2 + 3))):
        els.append({"id": "D-%d" % (len(els) + 1), "type": "door", "name": nm, "level": "L1", "line_m": [a, bb], "width_m": abs(a[0] - bb[0]) + abs(a[1] - bb[1]), "status": "proposed"})
    height = r1(z)
    # capacity
    cap = None
    m = re.search(r"([\d,]+)\s+rooms", b.get("notes") or "")
    if m and t["id"] == "hotel":
        cap = "%s guest rooms (from the brief)" % m.group(1)
    else:
        rooms = [x for x in els if x["type"] == "room"]
        first_upper = t["upper"][0][0] if typical else t["ground"][0][0]
        if t.get("room_m2") and office_band:  # sheds: staff by total floor area
            a = sum(area(x["outline_m"]) for x in rooms if x.get("level") == "L1")
            cap = "about %s %s" % ("{:,}".format(nice(a / t["room_m2"])), t["capacity_word"])
        elif t.get("room_m2"):
            a = sum(area(x["outline_m"]) * len(x.get("levels") or [1]) for x in rooms if x["name"].startswith(first_upper))
            cap = "about %s %s" % ("{:,}".format(nice(a / t["room_m2"])), t["capacity_word"])
        elif t.get("capacity_m2"):
            a = sum(area(x["outline_m"]) for x in rooms if x.get("level") == "L1" or "L1" in (x.get("levels") or []))
            cap = "about %s %s" % ("{:,}".format(nice(a / t["capacity_m2"])), t["capacity_word"])
    ncores = sum(1 for x in els if x["type"] == "core")
    def prog_text(p):
        return ", ".join(n for n, _ in p)
    up_ids = typical or (["L2"] if office_band else [])
    interior = "Level 1: %s." % prog_text(t["ground"])
    if pod > 1:
        interior = "Levels 1–%d (podium): %s." % (pod, prog_text(t["ground"]))
    if up_ids:
        interior += " %s: %s." % ("Level %s" % up_ids[0][1:] if len(up_ids) == 1 else "Levels %s–%s" % (up_ids[0][1:], up_ids[-1][1:]), prog_text(t["upper"]))
    if t.get("towers") and info["nb"] >= 2:
        interior += " The upper floors rise as %d slim towers over the podium." % len(range(0, info["nb"], 2))
    elif t.get("courtyards") and info["nb"] >= 2 and typical:
        interior += " Above level 1 the building splits into %d wings with open courtyards between them." % len(range(0, info["nb"], 2))
    if below:
        interior += " Below deck: %s." % prog_text(t.get("below_program") or [["Plant rooms", 1]])
    fields = {
        "height_m": height,
        "floors": "%d above deck%s" % (len(above), ", %d below" % len(below) if below else ""),
        "structure": t["structure"] + ".",
        "look": "%s. %s" % (t["look"], style),
        "entrances": t["entrances"] + ".",
        "capacity": cap,
        "services": "Stairs and lifts in %d cores; power, air and water from the precinct utility plant; sprinklers and smoke control throughout." % ncores,
        "interior": interior,
    }
    model = {
        "schema": "invicta-atlas/model@1",
        "building_uid": b["uid"] if "uid" in b else None,
        "units": "m",
        "frame": "Metres from the building's bow-port corner: x toward the stern, y toward starboard, z above the deck.",
        "footprint_m": [r1(Lx), r1(Wy)],
        "grid_m": t["module"],
        "source": "Drafted by tools/auto_design.py from the footprint and the '%s' type in data/typologies.json, %s. All proposed." % (t["id"], TODAY),
        "levels": levels,
        "elements": els,
        "updated": TODAY,
    }
    return fields, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="e.g. D5/port-of-arrivals")
    ap.add_argument("precinct", help="P2, or all")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--redo", action="store_true", help="draft again buildings this tool drafted before")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    path = os.path.join(DATA, "decks", *a.file.split("/")) + ".json"
    raw = open(path, encoding="utf-8").read()
    data = json.loads(raw)
    ty = json.load(open(os.path.join(DATA, "typologies.json"), encoding="utf-8"))
    style = ty["style"].get(os.path.basename(a.file), "")
    did = "D%s-%s" % (data.get("deck"), os.path.basename(a.file))
    mdir = os.path.join(DATA, "models")
    done = []
    for p in data["precincts"]:
        if a.precinct != "all" and p["id"] != a.precinct:
            continue
        for b in p.get("buildings", []):
            uid = "%s-%s" % (did, b["id"])
            mp = os.path.join(mdir, uid + ".json")
            mine = os.path.isfile(mp) and "auto_design.py" in json.load(open(mp, encoding="utf-8")).get("source", "")
            if b.get("kind") in SKIP_KINDS or b.get("status") == "canon":
                continue
            if (b.get("height_m") or os.path.isfile(mp)) and not (a.redo and mine):
                continue
            t = typ_for(b, ty["types"])
            if not t:
                continue
            bb = dict(b, uid=uid)
            if "rect_km" not in bb:
                print("  no footprint:", b["id"], b["name"])
                continue
            fields, model = design(bb, t, style)
            done.append((b["id"], b["name"], t["id"], fields["height_m"], len(model["elements"])))
            if not a.dry:
                for k, v in fields.items():
                    if v is not None:
                        b[k] = v
                with open(os.path.join(mdir, uid + ".json"), "w", encoding="utf-8", newline="\n") as f:
                    json.dump(model, f, ensure_ascii=False, indent=1)
                    f.write("\n")
    for x in done:
        print("  %-6s %-28s %-9s %5.1f m  %d parts" % x)
    if not a.dry and done:
        m = re.match(r"\{\r?\n([ \t]+)", raw)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=m.group(1) if m else None) + ("\n" if raw.endswith("\n") else ""))
    print("%d building(s) %s." % (len(done), "would be drafted" if a.dry else "drafted"))
    data["_drafted"] = {b["id"] for p in data["precincts"] for b in p.get("buildings", [])
                        if os.path.isfile(os.path.join(mdir, "%s-%s.json" % (did, b["id"])))
                        and "auto_design.py" in json.load(open(os.path.join(mdir, "%s-%s.json" % (did, b["id"])), encoding="utf-8")).get("source", "")}
    if not a.dry and data.get("doc"):
        root = os.path.dirname(APP)
        for rel in (data["doc"], data["doc"].replace("Game/Docs/", "Docs/2_Design_Docs/", 1)):
            doc_update(os.path.join(root, *rel.split("/")), data, a.precinct)



# ---- Design doc: one short line per drafted building, under its precinct's table, between markers.
def doc_update(doc_path, data, pid_filter, mdir=os.path.join(DATA, "models")):
    if not os.path.isfile(doc_path):
        return
    rb = open(doc_path, "rb").read()
    crlf = b"\r\n" in rb
    text = rb.decode("utf-8").replace("\r\n", "\n")
    for p in data["precincts"]:
        if pid_filter != "all" and p["id"] != pid_filter:
            continue
        lines = text.split("\n")
        start = next((i for i, l in enumerate(lines) if re.match(r"^## %s · " % p["id"], l)), None)
        if start is None:
            continue
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        sec = lines[start:end]
        codes = {}
        for l in sec:
            if l.startswith("| ") and not l.startswith("|---"):
                cells = [c.strip() for c in l.strip().strip("|").split("|")]
                codes[cells[0].replace("**", "")] = cells[-1]
        mk0, mk1 = "<!-- designs %s start -->" % p["id"], "<!-- designs %s end -->" % p["id"]
        body = [mk0, "", "**Building designs (proposed 27 Nov 2026; full room plans in `Invicta/data/models/`):**", ""]
        for b in p.get("buildings", []):
            if not b.get("height_m") or b.get("status") == "canon" or not b.get("interior") or b["id"] not in data.get("_drafted", set()):
                continue
            h = b["height_m"]
            code = codes.get(b["name"], "")
            body.append("- **%s**%s: %s ft (%s m) tall, %s. %s %s Capacity %s." % (
                b["name"], " (%s)" % code if code and code != "—" else "", ft(h), ("%.1f" % h).rstrip("0").rstrip("."), b.get("floors", ""),
                b.get("structure", ""), b.get("interior", ""), b.get("capacity") or "not set"))
        body += ["", mk1]
        if mk0 in sec:
            i0, i1 = sec.index(mk0), sec.index(mk1)
            sec = sec[:i0] + body + sec[i1 + 1:]
        else:
            while sec and sec[-1] == "":
                sec.pop()
            sec = sec + [""] + body + [""]
        lines = lines[:start] + sec + lines[end:]
        text = "\n".join(lines)
    open(doc_path, "wb").write((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    print("Doc updated:", doc_path)


if __name__ == "__main__":
    main()
