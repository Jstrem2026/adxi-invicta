"""Turn hand-written building designs into plans (2D and 3D) and building data.

    python tools/build_designs.py D5/port-of-arrivals P8      build every design in data/designs/D5/port-of-arrivals/P8.json

A design file holds one entry per building, each written for that building (not from a template):

    {"id": "P8-02", "name": "Shuttle Ops",
     "levels": [["L1", "Ground floor", 0, 6], ["L2", "Ops floor", 6, 5], ...],      id, name, floor height above deck (m), storey height (m)
     "parts": [                                                                    each part is one wing, hall, tower or yard
        {"name": "Ops wing", "x": 40, "y": 60, "w": 220, "d": 48,                  metres from the lot's bow-port corner (x stern, y starboard)
         "levels": ["L1", "L2"], "layout": "corridor", "depth": 14, "corridor": 4,
         "cores": 2,                                                               stair and lift cores at the corridor ends (and middle if 3)
         "rooms": {"L1": [["Lobby", 400], ["Briefing rooms", 300, 3]], "L2": [["Dispatch floor", 1800]]}},
                                                                                    [name, m2] or [name, m2 each, count]; "rest" fills what is left
        {"name": "Apron", "x": 0, "y": 0, "w": 700, "d": 60, "layout": "outdoor"},
        {"name": "Hangar hall", ..., "layout": "bays", "bays": 6, "bay_name": "Work bay"}   equal bays across the long side
        {"name": "Atrium", ..., "layout": "hall"}                                  one room the size of the part
     ],
     "height_note", "structure", "look", "entrances", "capacity", "services", "interior"}

Rooms are packed in order along both sides of the corridor and stretched to fill each side exactly, so no room
crosses a part's edge. Parts never leave the lot. Everything is written as status "proposed".
"""
import json
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
sys.path.insert(0, os.path.join(APP, "tools"))
import auto_design  # noqa: E402  (doc writer)

TODAY = "2026-11-27"


def r1(v):
    return round(v + 0.0, 1)


def expand(rooms):
    out = []
    for r in rooms:
        if len(r) >= 3:
            out += [[r[0], r[1]]] * int(r[2])
        else:
            out.append([r[0], r[1]])
    return out


def pack_side(rooms, length, depth):
    """[(name, length)] stretched so they fill `length` exactly."""
    if not rooms:
        return []
    fixed = [(n, (a / depth if a != "rest" else None)) for n, a in rooms]
    used = sum(l for _, l in fixed if l)
    rest = [i for i, (_, l) in enumerate(fixed) if l is None]
    if rest:
        left = max(length - used, 4.0 * len(rest))
        fixed = [(n, l if l is not None else left / len(rest)) for n, l in fixed]
    tot = sum(l for _, l in fixed)
    k = length / tot
    return [(n, l * k) for n, l in fixed]


def build_part(p, add, lot):
    x0, y0, w, d = p["x"], p["y"], p["w"], p["d"]
    assert x0 >= -0.01 and y0 >= -0.01 and x0 + w <= lot[0] + 0.01 and y0 + d <= lot[1] + 0.01, "%s leaves the lot" % p["name"]
    along_x = p.get("axis", "x" if w >= d else "y") == "x"
    L, D = (w, d) if along_x else (d, w)

    def rect(u0, v0, u1, v1):
        if along_x:
            pts = [[x0 + u0, y0 + v0], [x0 + u1, y0 + v0], [x0 + u1, y0 + v1], [x0 + u0, y0 + v1]]
        else:
            pts = [[x0 + v0, y0 + u0], [x0 + v1, y0 + u0], [x0 + v1, y0 + u1], [x0 + v0, y0 + u1]]
        return [[r1(a), r1(b)] for a, b in pts]

    lay = p.get("layout", "corridor")
    lv_all = p.get("levels", ["L1"])
    if lay == "outdoor":
        add("zone", p["name"], rect(0, 0, L, D), ["L1"], outdoor=True)
        return
    if lay == "mass":
        add("mass", p["name"], rect(0, 0, L, D), lv_all)
        return
    if lay == "hall":
        add("room", p.get("room", p["name"]), rect(0, 0, L, D), lv_all, full=True)
        return
    if lay == "bays":
        n = p["bays"]
        names = p.get("bay_names") or ["%s %d" % (p.get("bay_name", "Bay"), i + 1) for i in range(n)]
        for i in range(n):
            add("room", names[i % len(names)], rect(L * i / n, 0, L * (i + 1) / n, D), lv_all, full=True)
        return
    # corridor layout
    c = p.get("corridor", 3)
    depth = p.get("depth", (D - c) / 2)
    two = D >= 2 * min(depth, (D - c) / 2) + c - 0.01 and D - c >= 8
    if two:
        dA = (D - c) / 2 if p.get("depth") is None else min(depth, (D - c) / 2)
        dA = (D - c) / 2  # rooms fill both sides fully
        sides = [(0, dA), (dA + c, D)]
        cor = (dA, dA + c)
    else:
        sides = [(c, D)]
        cor = (0, c)
    ncores = p.get("cores", 0)
    core_len = p.get("core_len", 10)
    core_pos = []
    if ncores:
        core_pos = [0.0, L - core_len] if ncores >= 2 else [L / 2 - core_len / 2]
        if ncores >= 3:
            core_pos.insert(1, L / 2 - core_len / 2)
        for u in core_pos:
            add("core", "Stairs and lifts", rect(u, sides[0][0], u + core_len, sides[0][1]), lv_all)
    groups = p.get("rooms", {})
    for key, rooms in groups.items():
        lvs = expand_levels(key, lv_all)
        add("zone", p.get("corridor_name", "Corridor"), rect(0, cor[0], L, cor[1]), lvs)
        rooms = expand(rooms)
        # split rooms between sides by area; side A loses the core cells
        segsA = segments(L, core_pos, core_len)
        side_len = [sum(b - a for a, b in segsA)] + ([L] if two else [])
        tot = sum(side_len)
        areas = [(a if a != "rest" else 0) for _, a in rooms]
        cut, acc, target = len(rooms), 0.0, sum(areas) * side_len[0] / tot if two else None
        if two:
            for i, a in enumerate(areas):
                if acc + a / 2 > target and i > 0:
                    cut = i
                    break
                acc += a
        lists = [rooms[:cut], rooms[cut:]] if two else [rooms]
        for si, (v0, v1) in enumerate(sides):
            lst = lists[si] if si < len(lists) else []
            if not lst:
                lst = [["Stores", "rest"]]
            if si == 0 and core_pos:
                # pack into the gaps between cores, in order
                segs = segsA
                seg_tot = sum(b - a for a, b in segs)
                packed = pack_side(lst, seg_tot, v1 - v0)
                pos, si2 = 0.0, 0
                for name, ln in packed:
                    while ln > 0.05 and si2 < len(segs):
                        a, b = segs[si2]
                        start = a + pos
                        room_end = min(b, start + ln)
                        add("room", name, rect(start, v0, room_end, v1), lvs)
                        ln -= room_end - start
                        pos = room_end - a
                        if room_end >= b - 0.05:
                            si2 += 1
                            pos = 0.0
            else:
                u = 0.0
                for name, ln in pack_side(lst, L, v1 - v0):
                    add("room", name, rect(u, v0, u + ln, v1), lvs)
                    u += ln


def segments(L, core_pos, core_len):
    if not core_pos:
        return [(0.0, L)]
    out, u = [], 0.0
    for c in sorted(core_pos):
        if c - u > 0.5:
            out.append((u, c))
        u = c + core_len
    if L - u > 0.5:
        out.append((u, L))
    return out


def expand_levels(key, lv_all):
    if key == "all":
        return lv_all
    if "-" in key:
        a, b = key.split("-")
        ia, ib = lv_all.index(a), lv_all.index(b)
        return lv_all[ia:ib + 1]
    return [key]


def build(entry, b, did):
    r = b["rect_km"]
    lot = ((r[1] - r[0]) * 1000, (r[3] - r[2]) * 1000)
    levels = [{"id": l[0], "name": "Level %s · %s" % (l[0][1:], l[1]) if not l[0].startswith("LB") else "Level B%s · %s" % (l[0][2:], l[1]),
               "z_m": l[2], "height_m": l[3], "status": "proposed"} for l in entry["levels"]]
    els = []

    def add(typ, name, poly, lvs, outdoor=False, full=False):
        e = {"id": "E%03d" % (len(els) + 1), "type": typ, "name": name}
        if len(lvs) == 1:
            e["level"] = lvs[0]
        else:
            e["levels"] = lvs
        e["outline_m"] = poly
        if outdoor:
            e["outdoor"] = True
        if full and len(lvs) > 1:
            e["full_height"] = True  # one tall space through these levels (a hall), not separate floors
        e["status"] = "proposed"
        els.append(e)

    for p in entry["parts"]:
        build_part(p, add, lot)
    for dr in entry.get("doors", []):
        els.append({"id": "E%03d" % (len(els) + 1), "type": "door", "name": dr[0], "level": dr[3] if len(dr) > 3 else "L1",
                    "line_m": [dr[1], dr[2]], "width_m": r1(abs(dr[1][0] - dr[2][0]) + abs(dr[1][1] - dr[2][1])), "status": "proposed"})
    top = max(l["z_m"] + l["height_m"] for l in levels)
    model = {"schema": "invicta-atlas/model@1", "building_uid": "%s-%s" % (did, b["id"]), "units": "m",
             "frame": "Metres from the lot's bow-port corner: x toward the stern, y toward starboard, z above the deck.",
             "footprint_m": [r1(lot[0]), r1(lot[1])], "grid_m": entry.get("grid_m", 10),
             "source": "Designed for this building (data/designs), built with tools/build_designs.py, %s. All proposed." % TODAY,
             "levels": levels, "elements": els, "updated": TODAY}
    above = [l for l in levels if l["z_m"] >= 0]
    below = [l for l in levels if l["z_m"] < 0]
    fields = {"height_m": r1(entry.get("height_m", top)),
              "floors": entry.get("floors") or "%d above deck%s" % (len(above), ", %d below" % len(below) if below else ""),
              "structure": entry["structure"], "look": entry["look"], "entrances": entry["entrances"],
              "capacity": entry.get("capacity"), "services": entry.get("services"), "interior": entry["interior"]}
    if entry.get("name") and entry["name"] != b["name"]:
        fields["name"] = entry["name"]
    return fields, model


def rename_rows(fp, pid, renames):
    rb = open(fp, "rb").read()
    crlf = b"\r\n" in rb
    lines = rb.decode("utf-8").replace("\r\n", "\n").split("\n")
    cur = None
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            m = re.match(r"^## (P\d+) · ", ln)
            cur = m.group(1) if m else None
        if cur == pid and ln.startswith("| "):
            first = ln[2:].split(" | ")[0]
            if first in renames:
                lines[i] = "| " + renames[first] + ln[2 + len(first):]
    out = "\n".join(lines)
    open(fp, "wb").write((out.replace("\n", "\r\n") if crlf else out).encode("utf-8"))


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    file, pid = sys.argv[1], sys.argv[2]
    path = os.path.join(DATA, "decks", *file.split("/")) + ".json"
    raw = open(path, encoding="utf-8").read()
    data = json.loads(raw)
    did = "D%s-%s" % (data["deck"], os.path.basename(file))
    spec = json.load(open(os.path.join(DATA, "designs", *file.split("/"), pid + ".json"), encoding="utf-8"))
    pr = [p for p in data["precincts"] if p["id"] == pid][0]
    byid = {b["id"]: b for b in pr["buildings"]}
    built, renames = [], {}
    for entry in spec["buildings"]:
        b = byid[entry["id"]]
        if entry.get("name") and entry["name"] != b["name"]:
            renames[b["name"]] = entry["name"]
        fields, model = build(entry, b, did)
        for k, v in fields.items():
            if v is not None:
                b[k] = v
        with open(os.path.join(DATA, "models", "%s-%s.json" % (did, b["id"])), "w", encoding="utf-8", newline="\n") as f:
            json.dump(model, f, ensure_ascii=False, indent=1)
            f.write("\n")
        built.append(b["id"])
        print("  %-6s %-32s %5.1f m  %3d parts" % (b["id"], b["name"], fields["height_m"], len(model["elements"])))
    m = re.match(r"\{\r?\n([ \t]+)", raw)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=m.group(1) if m else None) + ("\n" if raw.endswith("\n") else ""))
    data["_drafted"] = set(built) | {b["id"] for b in pr["buildings"] if os.path.isfile(os.path.join(DATA, "models", "%s-%s.json" % (did, b["id"])))
                                     and "auto_design" in open(os.path.join(DATA, "models", "%s-%s.json" % (did, b["id"])), encoding="utf-8").read(400)}
    root = os.path.dirname(APP)
    for rel in (data["doc"], data["doc"].replace("Game/Docs/", "Docs/2_Design_Docs/", 1)):
        if renames:  # keep the doc's building table in step with new names (only inside this precinct's section)
            rename_rows(os.path.join(root, *rel.split("/")), pid, renames)
        auto_design.doc_update(os.path.join(root, *rel.split("/")), data, pid)
    print("%d building(s) built." % len(built))


if __name__ == "__main__":
    main()
