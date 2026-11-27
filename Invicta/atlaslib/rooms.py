"""Checks on every building's room plan (Invicta/data/models/<uid>.json).

Jordan, 27 Nov 2026: "Yes, use Shapely" for exact math and checks on every room.
Until now the scan stopped at each building's footprint; these checks look inside.

Each check reports one issue per building, with a count and a few examples, so a
building with 40 overlaps shows once, not 40 times. They are warnings for now: the
room designer (tools/design_rooms.py) is being reworked to fix them at the source
(plan step 4), and then they become errors.

Plan frame: metres from the building lot's bow-port corner, x toward the stern,
y toward starboard (the corner of rect_km at x0, y0).
"""

import json
import os

import numpy as np
import shapely
from shapely.strtree import STRtree

from . import fabric as FB
from . import geometry as G

MIN_ROOM_WIDTH_M = 1.5    # 5 ft: narrower than this, a person can't use the room
MIN_OVERLAP_M2 = 1.0      # 11 sq ft: smaller overlaps are rounding where walls meet
OUTSIDE_TOL_M = 0.5       # rooms may sit up to 1.6 ft (0.5 m) past the outline (wall line)
MIN_OUTSIDE_M2 = 2.0      # and must stick out by more than 22 sq ft (2 m²) to count
SPACES = ("room", "zone", "core")  # things that take up floor; fixtures sit inside rooms


def _examples(items, n=3):
    more = len(items) - n
    return "; ".join(items[:n]) + ("; and %d more" % more if more > 0 else "")


def _levels(e):
    return e.get("levels") or ([e["level"]] if e.get("level") else [])


def _polygons(outlines):
    """Many outlines -> array of polygons in one call (much faster than one at a time)."""
    out = np.empty(len(outlines), dtype=object)
    ok = [i for i, o in enumerate(outlines) if len(o) >= 3]
    out[:] = shapely.Polygon()
    if ok:
        coords = np.array([q[:2] for i in ok for q in outlines[i]], dtype=float)
        idx = np.repeat(np.arange(len(ok)), [len(outlines[i]) for i in ok])
        out[ok] = shapely.polygons(shapely.linearrings(coords, indices=idx))
    return out


def check_plan(m, b=None):
    """Problems in one plan. Returns a list of (title, detail-without-building-name, fix)."""
    out = []
    levels = {l["id"]: l for l in m.get("levels", [])}
    els = [e for e in m.get("elements", []) if e.get("outline_m")]

    # Levels stack with no gap or overlap
    ls = sorted(levels.values(), key=lambda l: l.get("z_m", 0))
    bad = ["%s ends at %g m, %s starts at %g m" % (a["id"], a["z_m"] + a["height_m"], c["id"], c["z_m"])
           for a, c in zip(ls, ls[1:]) if abs(a["z_m"] + a["height_m"] - c["z_m"]) > 0.01]
    if bad:
        out.append(("Floors do not stack", "%d gap(s) or overlap(s) between floors: %s." % (len(bad), _examples(bad)),
                    "Each floor's z_m should equal the floor below's z_m + height_m."))

    # Elements on floors that don't exist
    missing = sorted({"%s (%s)" % (e["id"], L) for e in els for L in _levels(e) if L not in levels})
    if missing:
        out.append(("Rooms on a floor that does not exist", "%d: %s." % (len(missing), _examples(missing)), None))

    if not els:
        return out
    polys = _polygons([e["outline_m"] for e in els])
    valid = shapely.is_valid(polys)

    # Shapes that cross themselves
    broken = ["%s %s" % (e["id"], e["name"]) for e, ok in zip(els, valid) if not ok]
    if broken:
        out.append(("Room outlines cross themselves", "%d room shape(s) cannot be built in 3D: %s." % (len(broken), _examples(broken)),
                    "Redraw the outline so its edges do not cross."))

    # Rooms too narrow to use
    rooms = [i for i, e in enumerate(els) if e["type"] == "room" and valid[i]]
    if rooms:
        mrr = shapely.oriented_envelope(polys[rooms])
        narrow = []
        for i, env in zip(rooms, mrr):
            c = np.asarray(env.exterior.coords) if env.geom_type == "Polygon" else None
            if c is None:
                w = 0.0
            else:
                w = min(np.hypot(*(c[1] - c[0])), np.hypot(*(c[2] - c[1])))
            if w < MIN_ROOM_WIDTH_M:
                narrow.append("%s %s %s" % (els[i]["id"], els[i]["name"], G.fmt_len_m(w)))
        if narrow:
            out.append(("Rooms too narrow to use", "%d room(s) under %s wide: %s." % (len(narrow), G.fmt_len_m(MIN_ROOM_WIDTH_M), _examples(narrow)),
                        "Widen them or merge them with a neighbour."))

    # Rooms outside the building's own outline (curved edges, courtyards)
    if b and b.get("rect_km"):
        x0, y0 = b["rect_km"][0], b["rect_km"][2]
        foot = G.building_shape(b)
        foot_m = shapely.transform(foot, lambda c: (c - [x0, y0]) * 1000.0).buffer(OUTSIDE_TOL_M)
        outside = []
        shapely.prepare(foot_m)
        inside = shapely.covers(foot_m, polys)
        for i, e in enumerate(els):
            if valid[i] and not inside[i] and e["type"] in SPACES and not e.get("outdoor"):
                a = polys[i].difference(foot_m).area
                if a > MIN_OUTSIDE_M2:
                    outside.append("%s %s (%s outside)" % (e["id"], e["name"], G.fmt_area_m2(a)))
        if outside:
            out.append(("Rooms outside the building", "%d room(s) reach past the building's outline or into its courtyard: %s." % (len(outside), _examples(outside)),
                        "Re-run the room designer on this building."))
        fw, fd = m.get("footprint_m", [None, None])
        bw, bd = (b["rect_km"][1] - b["rect_km"][0]) * 1000, (b["rect_km"][3] - b["rect_km"][2]) * 1000
        if fw is not None and (abs(fw - bw) > 1 or abs(fd - bd) > 1):
            out.append(("Plan size differs from the map", "The plan is %s × %s, the map box is %s × %s." % (
                G.fmt_len_m(fw), G.fmt_len_m(fd), G.fmt_len_m(bw), G.fmt_len_m(bd)), "Re-run the room designer on this building."))

    # Overlapping spaces on the same floor
    by_level = {}
    for i, e in enumerate(els):
        if valid[i] and e["type"] in SPACES and not e.get("outdoor"):
            for L in _levels(e):
                by_level.setdefault(L, []).append(i)
    over = []
    for L, idx in by_level.items():
        if len(idx) < 2:
            continue
        g = polys[idx]
        # Candidate pairs: boxes that share more than MIN_OVERLAP_M2 (rooms that only touch
        # along a wall share no box area, so they are skipped without measuring).
        pairs = STRtree(g).query(g)
        a, c = pairs[0], pairs[1]
        keep = a < c
        a, c = a[keep], c[keep]
        bb = shapely.bounds(g)
        w = np.minimum(bb[a, 2], bb[c, 2]) - np.maximum(bb[a, 0], bb[c, 0])
        h = np.minimum(bb[a, 3], bb[c, 3]) - np.maximum(bb[a, 1], bb[c, 1])
        keep = (w > 0) & (h > 0) & (w * h > MIN_OVERLAP_M2)
        a, c = a[keep], c[keep]
        if len(a):  # then keep pairs whose insides really share floor (fast on prepared shapes)
            shapely.prepare(g)
            keep = shapely.relate_pattern(g[a], g[c], "2********")
            a, c = a[keep], c[keep]
        if not len(a):
            continue
        areas = shapely.area(shapely.intersection(g[a], g[c]))
        for ia, ic, ar in zip(a, c, areas):
            if ar > MIN_OVERLAP_M2:
                over.append("%s and %s on %s (%s)" % (els[idx[ia]]["name"], els[idx[ic]]["name"], L, G.fmt_area_m2(ar)))
    if over:
        out.append(("Rooms overlap", "%d overlap(s) between rooms, corridors or stair cores on the same floor: %s." % (len(over), _examples(over)),
                    "Move or trim the rooms so each piece of floor belongs to one room."))

    # Every floor of a multi-storey building reached by stairs or a lift
    if len(levels) > 1:
        served = {L for e in els if e["type"] == "core" for L in _levels(e)}
        dry = [l["id"] for l in ls if l["id"] not in served]
        if dry:
            out.append(("Floors with no stairs or lift", "%d of %d floors have no stair or lift core: %s." % (len(dry), len(levels), ", ".join(dry)),
                        "Add a core that serves these floors."))
    return out


CHECK_VERSION = 2  # raise when a check changes, so cached results are redone


def scan_plans(model, models_dir, add, cache_path=None):
    """Check every room plan. `add(sev, cat, title, detail, entity, path, fix)` records an issue.
    With `cache_path`, results are kept per plan file and reused while neither the file nor its
    building on the map has changed, so a rescan only re-checks what changed."""
    if not os.path.isdir(models_dir):
        return
    buildings = {}
    for did, ps in model.get("precinct_sets", {}).items():
        for p in ps["precincts"]:
            for b in p["buildings"]:
                buildings[b["uid"]] = b
    cache = {}
    if cache_path and os.path.isfile(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("version") != CHECK_VERSION:
                cache = {}
        except (OSError, ValueError):
            cache = {}
    plans = cache.get("plans", {})
    fresh = {}
    n_plans = 0
    totals = {}
    for name in sorted(os.listdir(models_dir)):
        if not name.endswith(".json"):
            continue
        rel = "Invicta/data/models/" + name
        path = os.path.join(models_dir, name)
        st = os.stat(path)
        uid = name[:-5]
        b = buildings.get(uid)
        bkey = json.dumps([b.get(k) for k in ("id", "name", "rect_km", "outline_km", "holes_km", "bays_km")] if b else None)
        key = [st.st_mtime_ns, st.st_size, bkey]
        hit = plans.get(name)
        if hit and hit["key"] == key:
            res = hit["res"]
        else:
            res = _check_file(path, name, buildings)
        fresh[name] = {"key": key, "res": res}
        for sev, title, detail, entity, fix in res["issues"]:
            add(sev, "rooms" if sev != "error" else "data", title, detail, entity, rel, fix)
        if res.get("ok"):
            n_plans += 1
            for k, v in res["fabric"].items():
                totals[k] = totals.get(k, 0) + v
    if cache_path:
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"version": CHECK_VERSION, "plans": fresh}, f)
        except OSError:
            pass  # a cache that can't be written only makes the next scan slower
    if n_plans:
        add("decision", "rooms", "Walls, doors, windows and stairs are proposed",
            "Worked out by rule from the rooms of the %d room plans (atlaslib/fabric.py): %s walls, %s doors, "
            "%s openings, %s window runs, %s flights of stairs, %s lifts and %s floor slabs. "
            "They are shown in the 2D plans and 3D view; the plan files are unchanged. Approve the rules or say what to change." % (
                n_plans, *("{:,}".format(totals.get(k, 0)) for k in ("wall", "door", "opening", "window", "stair", "lift", "slab"))),
            None, "Invicta/atlaslib/fabric.py", None)

def _check_file(path, name, buildings):
    try:
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError) as e:
        return {"ok": False, "issues": [["error", "Room plan could not be read", "%s: %s" % (name, e), None, None]]}
    uid = m.get("building_uid") or name[:-5]
    b = buildings.get(uid)
    who = "%s %s" % (b["id"], b["name"]) if b else uid
    issues = []
    if not b:
        issues.append(["warning", "Room plan for a building that is not on the map",
                       "%s has a room plan, but no district file lists that building." % uid, None, None])
    for title, detail, fix in check_plan(m, b):
        issues.append(["warning", title, "%s: %s" % (who, detail), uid if b else None, fix])
    # The fabric (walls, doors, windows, stairs) worked out from the rooms: can every room be reached?
    extra, rep = FB.build(m)
    if rep["unreachable"]:
        issues.append(["warning", "Rooms with no way in",
                       "%s: %d space(s) can't be reached from an entrance through doors and stairs: %s." % (
                           who, len(rep["unreachable"]), _examples(rep["unreachable"])), uid if b else None,
                       "Usually a floor whose stair core doesn't reach the floor below. Add or extend a core."])
    if rep["stairs_not_fitting"]:
        issues.append(["warning", "Stairs too big for their core",
                       "%s: %d flight(s) of stairs don't fit their core: %s." % (
                           who, len(rep["stairs_not_fitting"]), _examples(rep["stairs_not_fitting"])), uid if b else None,
                       "Make the core bigger, or the floor lower."])
    count = {}
    for e in extra:
        count[e["type"]] = count.get(e["type"], 0) + 1
    return {"ok": True, "issues": issues, "fabric": count}
