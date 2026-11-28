"""City planner (Jordan, 28 Nov 2026: "every deck is a working city built around its purpose; every
building has a purpose and a place").

A district's program in data/city_programs.json says what the district needs to do its job: which hull
doors, which response services within reach of them, which security steps, and what every precinct must
hold. check() compares a district's data with its program and lists what is there and what is missing.
propose() places the missing pieces in free land, clear of streets, buildings and the 500 m grid lines,
as new 'proposed' items. apply() adds them to the district data. Nothing already designed is moved,
resized or removed: proposals only add new items, or add doors to an item that has none.

All maths is exact (Shapely). Ship frame: x km from the prow, y km across the beam, port negative.
"""

import json
import math
import os
import re

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep

from . import geometry as G

FRAME_KM = 0.5


# ------------------------------------------------------------------ loading

def load_program(app_dir, district_id):
    with open(os.path.join(app_dir, "data", "city_programs.json"), encoding="utf-8") as fh:
        progs = json.load(fh)
    prog = progs["districts"].get(district_id)
    if not prog:
        raise KeyError("No city program for %s in data/city_programs.json" % district_id)
    return progs, prog


def load_district(app_dir, prog):
    path = os.path.join(app_dir, *prog["file"].split("/"))
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    return path, raw, json.loads(raw)


# ------------------------------------------------------------------ shapes

def precinct_shape(p):
    s = G.shape(p["polygon_km"]) if p.get("polygon_km") else G.box_shape(p["bounds_km"])
    for c in p.get("exclude_circles_km") or []:
        s = s.difference(G.circle(*c))
    return s


def occupied(p):
    """Everything already standing in a precinct: each building's whole lot (its rect_km, courtyards and
    yards included, since a lot belongs to its building), each bay of a row of bays, and the streets."""
    parts = [G.building_shape(b) if b.get("bays_km") else G.box_shape(b["rect_km"]) for b in p["buildings"]]
    parts += [G.box_shape(s["rect_km"]) for s in p.get("streets", [])]
    return unary_union(parts)


def hull_edges(p):
    """The precinct's straight hull edges: horizontal edges on its port-most line, as (x0, x1, y)."""
    ring = p.get("polygon_km") or [[p["bounds_km"][0], p["bounds_km"][2]], [p["bounds_km"][1], p["bounds_km"][2]]]
    ymin = min(pt[1] for pt in ring)
    out = []
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if abs(a[1] - ymin) < 1e-6 and abs(b[1] - ymin) < 1e-6 and abs(a[0] - b[0]) > 1e-6:
            out.append((min(a[0], b[0]), max(a[0], b[0]), ymin))
    return out


def hull_y_at(p, x):
    """The hull line under x: the port-most point of the precinct outline at that x."""
    s = precinct_shape(p)
    cut = s.intersection(LineString([(x, -50), (x, 50)]))
    return cut.bounds[1] if not cut.is_empty else None


def _crosses_grid(r):
    x0, x1, y0, y1 = r
    eps = 1e-6
    fx = math.floor(x0 / FRAME_KM + eps)
    if math.floor(x1 / FRAME_KM - eps) != fx:
        return True
    # lane edges sit at -0.25 + 0.5 k (lane M is centred on the centreline)
    ly = math.floor((y0 + 0.25) / FRAME_KM + eps)
    return math.floor((y1 + 0.25) / FRAME_KM - eps) != ly


def blocks_of(p, extra=()):
    """The precinct's city blocks (cells) as the app cuts them, with extra items standing in it."""
    from .loader import make_blocks
    poly = [tuple(q) for q in (p.get("polygon_km") or G.rect_poly(p["bounds_km"]))]
    bl = make_blocks(0, poly, G.bbox(poly), list(p["buildings"]) + list(extra), p.get("exclude_circles_km", []), p.get("streets", []))
    return [b["cell_km"] for b in bl]


def place_rect(p, size_m, target, taken, clear_km=0.03, step_km=0.01, keep_off_hull_km=0.1, extra=(), tries=12):
    """place_rect_once, but never where the new item would change how the precinct is cut into blocks:
    existing buildings keep their block names and codes."""
    base = blocks_of(p, extra)
    avoid = []
    for _ in range(tries):
        r = place_rect_once(p, size_m, target, list(taken) + avoid, clear_km, step_km, keep_off_hull_km)
        if r is None:
            return None
        if blocks_of(p, list(extra) + [{"id": "new", "name": "new", "rect_km": r}]) == base:
            return r
        avoid.append(box(r[0], r[2], r[1], r[3]).buffer(0.1))
    return None


def place_rect_once(p, size_m, target, taken, clear_km=0.03, step_km=0.01, keep_off_hull_km=0.1):
    """Find a spot for a w x h m box in precinct p, as close as possible to target (x, y): fully in free
    land, at least clear_km from every building and street, clear of the hull band, and not crossing a
    frame or lane line (so it sits in one block). Tries both turns of the box. Returns rect_km or None."""
    region = precinct_shape(p).buffer(-clear_km)
    for e in hull_edges(p):
        region = region.difference(box(e[0] - 1, e[2] - 1, e[1] + 1, e[2] + keep_off_hull_km))
    region = region.difference(unary_union([occupied(p)] + list(taken)).buffer(clear_km))
    if region.is_empty:
        return None
    ok = prep(region)
    best = None
    bx0, by0, bx1, by1 = region.bounds
    for w, h in {(size_m[0] / 1000.0, size_m[1] / 1000.0), (size_m[1] / 1000.0, size_m[0] / 1000.0)}:
        y = by0
        while y + h <= by1 + 1e-9:
            x = bx0
            while x + w <= bx1 + 1e-9:
                r = [round(x, 4), round(x + w, 4), round(y, 4), round(y + h, 4)]
                if not _crosses_grid(r):
                    d = math.hypot((x + w / 2) - target[0], (y + h / 2) - target[1])
                    if (best is None or d < best[0]) and ok.contains(box(r[0], r[2], r[1], r[3])):
                        best = (d, r)
                x += step_km
            y += step_km
    return best[1] if best else None


# ------------------------------------------------------------------ text matching

def _text(b):
    return " ".join(str(b.get(k) or "") for k in ("name", "purpose", "services", "interior", "notes"))


def _find(d, rx, field="name"):
    pat = re.compile(rx, re.I)
    out = []
    for p in d["precincts"]:
        for b in p["buildings"]:
            if pat.search(_text(b) if field == "text" else b.get(field) or ""):
                out.append((p, b))
    return out


# ------------------------------------------------------------------ doors

def doors(d, prog):
    """Every hull door, by class: [{cls, precinct, building, rect, point, width_m, implied}]."""
    out = []
    for c in prog["door_classes"]:
        for p, b in _find(d, c["match"]):
            rects = b.get("doors_km") or []
            for r in rects:
                out.append({"cls": c["id"], "precinct": p["id"], "building": b, "rect": r,
                            "point": ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2), "width_m": (r[1] - r[0]) * 1000, "implied": False})
            if not rects:
                note = (c.get("implied_doors") or {}).get(b["name"])
                if note:
                    r = b["rect_km"]
                    out.append({"cls": c["id"], "precinct": p["id"], "building": b, "rect": None,
                                "point": ((r[0] + r[1]) / 2, r[2]), "width_m": None, "implied": note})
    return out


def _dist_to(pt, b):
    return G.building_shape(b).distance(Point(pt))


# ------------------------------------------------------------------ the check

def check(d, prog):
    """Compare a district with its program. Returns a dict the report and the proposer read."""
    res = {"doors": doors(d, prog), "classes": [], "response": [], "clearance": None, "must_have": [],
           "per_precinct": [], "zones": []}
    by_cls = {}
    for dr in res["doors"]:
        by_cls.setdefault(dr["cls"], []).append(dr)
    for c in prog["door_classes"]:
        got = by_cls.get(c["id"], [])
        owners = {}
        for dr in got:
            owners.setdefault(dr["building"]["id"], dr["building"])
        no_doors = [b for p, b in _find(d, c["match"]) if not b.get("doors_km") and not (c.get("implied_doors") or {}).get(b["name"])]
        ctrl = _find(d, c.get("control") or "^$") if c.get("control") else []
        res["classes"].append({"cls": c, "count": len(got), "owners": list(owners.values()), "no_doors": no_doors,
                               "ok": len(got) >= c.get("min", 1) and not no_doors,
                               "control": [b for p, b in ctrl]})
    # pressure zones: one frame of hull front each
    hp = [p for p in d["precincts"] if p["id"] in prog.get("hull_precincts", [])]
    crew = by_cls.get("crew", [])
    for p in hp:
        for x0, x1, y in hull_edges(p):
            f = math.floor(x0 / FRAME_KM + 1e-6)
            while f * FRAME_KM < x1 - 1e-6:
                a, b = max(x0, f * FRAME_KM), min(x1, (f + 1) * FRAME_KM)
                if b - a > 0.05:
                    has = [dr for dr in crew if a <= dr["point"][0] < b and dr["precinct"] == p["id"]]
                    res["zones"].append({"precinct": p["id"], "frame": "F%d" % f, "x": (a, b), "y": y, "airlocks": len(has)})
                f += 1
    real = [dr for dr in res["doors"] if dr["cls"] != "crew"]
    for rule in prog.get("response", []):
        also = re.compile(rule["also_text"], re.I) if rule.get("also_text") else None
        cands = [b for p in d["precincts"] for b in p["buildings"]
                 if b.get("category") == rule["category"] or (also and also.search(_text(b)))]
        far = []
        for dr in real:
            best = min(cands, key=lambda b: _dist_to(dr["point"], b)) if cands else None
            dist = _dist_to(dr["point"], best) if best else None
            if dist is None or dist > rule["within_km"]:
                far.append((dr, best, dist))
        res["response"].append({"rule": rule, "far": far, "count": len(real)})
    cl = prog.get("clearance")
    if cl:
        posts = [b for p, b in _find(d, cl["match_text"], "text")]
        far = []
        for dr in real:
            best = min(posts, key=lambda b: _dist_to(dr["point"], b)) if posts else None
            dist = _dist_to(dr["point"], best) if best else None
            if dist is None or dist > cl["within_km"]:
                far.append((dr, best, dist))
        res["clearance"] = {"rule": cl, "posts": posts, "far": far, "count": len(real)}
    for rule in prog.get("must_have", []):
        got = [b for p, b in _find(d, rule["match_text"], "text")]
        res["must_have"].append({"rule": rule, "got": got, "ok": len(got) >= rule.get("min", 1)})
    for rule in prog.get("per_precinct", []):
        for p in d["precincts"]:
            got = [b for b in p["buildings"] if re.search(rule["match"], b["name"], re.I)]
            res["per_precinct"].append({"rule": rule, "precinct": p, "got": got, "ok": len(got) >= rule.get("min", 1)})
    return res


# ------------------------------------------------------------------ proposals

def _next_id(p, extra):
    nums = [int(b["id"].split("-")[1]) for b in p["buildings"] if re.match(r"P\d+-\d+$", b["id"])]
    nums += [int(x["building"]["id"].split("-")[1]) for x in extra if x["precinct"] == p["id"]]
    return "%s-%02d" % (p["id"], max(nums + [0]) + 1)


def _size_text(w_m, h_m):
    return "%s × %s ft (%s × %s m)" % (G._n(w_m * G.M_TO_FT), G._n(h_m * G.M_TO_FT), G._n(w_m), G._n(h_m))


def place_near(d, first, size_m, target, taken, out, reach_km=1.2, must_reach=None):
    """place_rect in the precinct `first`; when it is full, in the nearest other precinct of the district
    that comes within reach_km of the target. must_reach=((x, y), km): the spot is no use unless it is
    within km of that point (the furthest door it is meant to serve). Returns (precinct, rect_km) or (None, None)."""
    pt = Point(target)
    order = [first] + [q for q in d["precincts"] if q is not first and precinct_shape(q).distance(pt) <= reach_km]
    best = (None, None, None)
    for q in order:
        r = place_rect(q, size_m, target, taken, extra=_mine(out, q))
        if not r:
            continue
        spot = box(r[0], r[2], r[1], r[3])
        if must_reach and spot.distance(Point(must_reach[0])) > must_reach[1]:
            continue
        dist = spot.centroid.distance(pt)
        if best[0] is None or dist < best[0] - 0.05:   # the home precinct wins a near tie
            best = (dist, q, r)
    return best[1], best[2]


def _mine(out, p):
    return [o["building"] for o in out if "building" in o and o["precinct"] == p["id"]]


def _new(p, extra, **kw):
    b = {"id": _next_id(p, extra), "status": "proposed", "planner": "city planner, 28 Nov 2026"}
    b.update(kw)
    return {"precinct": p["id"], "building": b}


def _hull_free(p, taken, depth_km, gap_km):
    """Free stretches of straight hull front: [(x0, x1, y)], clear of everything by gap_km."""
    out = []
    shapes = [G.box_shape(r) for b in p["buildings"] for r in (b.get("bays_km") or [b["rect_km"]])]
    shapes += [G.box_shape(st["rect_km"]) for st in p.get("streets", [])] + list(taken)
    for x0, x1, y in hull_edges(p):
        band = box(x0, y, x1, y + depth_km)
        inner = band.buffer(-0.0005)
        free = band
        for g in shapes:
            if g.intersects(inner):  # something stands on this stretch of hull: keep gap_km clear of it along the hull
                gx0, gy0, gx1, gy1 = g.bounds
                free = free.difference(box(gx0 - gap_km, y, gx1 + gap_km, y + depth_km))
        for g in getattr(free, "geoms", [free]):
            if not g.is_empty:
                gx0, gy0, gx1, gy1 = g.bounds
                out.append((gx0, gx1, y))
    return out


def propose(d, prog, res=None, gaps=None):
    """New items that fill the gaps in check(). Each is {precinct, building} (a new item) or
    {precinct, add_to, field, value, note} (doors added to an item that has none). Pass a list as gaps to
    get back what could not be placed, in plain words."""
    res = res or check(d, prog)
    fx = prog.get("fixes", {})
    pmap = {p["id"]: p for p in d["precincts"]}
    hp = [pmap[i] for i in prog.get("hull_precincts", []) if i in pmap]
    out, taken = [], []
    gaps = gaps if gaps is not None else []   # what the planner could not place, for the report

    def take(r):
        taken.append(box(r[0], r[2], r[1], r[3]))

    cls = {c["cls"]["id"]: c for c in res["classes"]}

    # 1. military and government berths: the free hull front nearest each end of the port
    f = fx.get("military")
    mc = cls.get("military")
    if f and mc and mc["count"] < mc["cls"].get("min", 1):
        bw, bd = f["berth_size_m"][0] / 1000.0, f["berth_size_m"][1] / 1000.0
        spots = []
        for p in hp:
            for x0, x1, y in _hull_free(p, taken, bd, 0.02):
                if x1 - x0 >= bw:
                    spots.append((p, x0, x1, y))
        ends = []
        if spots:
            ends.append(("Bow", min(spots, key=lambda s: s[1])))
            st = max(spots, key=lambda s: s[2])
            if st is not ends[0][1]:
                ends.append(("Stern", st))
        for end, (p, x0, x1, y) in ends[: mc["cls"].get("min", 1) - mc["count"]]:
            # centred in a short stretch; in a long one, at its end nearest the middle of the port
            if x1 - x0 < 2 * bw:
                xm = (x0 + x1) / 2
            else:
                xm = x1 - bw / 2 - 0.02 if end == "Bow" else x0 + bw / 2 + 0.02
            bay = [round(xm - bw / 2, 4), round(xm + bw / 2, 4), y, round(y + bd, 4)]
            dw, dd = f["door_width_m"] / 1000.0, f["door_depth_m"] / 1000.0
            door = [round(xm - dw / 2, 4), round(xm + dw / 2, 4), round(y - dd, 4), y]
            item = _new(p, [o for o in out if "building" in o],
                        name=f["name"].format(end=end), kind=f["kind"], category=f["category"],
                        size_text="1 bay, %s" % _size_text(f["berth_size_m"][0], f["berth_size_m"][1]),
                        size_m=list(f["berth_size_m"]), rect_km=bay, bays_km=[bay], bay_count=1, bay_names=[f["name"].format(end=end)], doors_km=[door],
                        notes=f["notes"].format(end=end, end_lower=end.lower()), purpose=f["purpose"])
            out.append(item)
            take(bay)
    # 2. the port guard's station, beside the first guard berth
    g = fx.get("guard_station")
    have_guard = _find(d, "^Port Guard")
    berths = [o for o in out if "building" in o and "Guard Berth" in o["building"]["name"]]
    if g and not have_guard and berths:
        o0 = berths[0]
        p = pmap[o0["precinct"]]
        b0 = o0["building"]["rect_km"]
        p, r = place_near(d, p, g["size_m"], ((b0[0] + b0[1]) / 2, b0[3] + 0.3), taken, out)
        if r:
            out.append(_new(p, [o for o in out if "building" in o], name=g["name"], kind="building", category=g["category"],
                            size_text=_size_text(*g["size_m"]), size_m=list(g["size_m"]), rect_km=r,
                            notes="Planner, 28 Nov 2026: beside the %s" % o0["building"]["name"], purpose=g["purpose"]))
            take(r)
    # 3. skiff and small-craft locks: doors for small-craft rows that have none
    s = fx.get("small_craft")
    sc = cls.get("small_craft")
    if s and sc:
        for b in sc["no_doors"]:
            p = next(q for q in d["precincts"] if b in q["buildings"])
            r = b["rect_km"]
            w, dd = s["door_width_m"] / 1000.0, s["door_depth_m"] / 1000.0
            drs = []
            for k in range(1, s["count"] + 1):
                x = r[0] + (r[1] - r[0]) * k / (s["count"] + 1)
                y = hull_y_at(p, x)
                drs.append([round(x - w / 2, 4), round(x + w / 2, 4), round(y - dd, 4), round(y, 4)])
            out.append({"precinct": p["id"], "add_to": b["id"], "name": b["name"], "field": "doors_km", "value": drs, "note": s["note"]})
    # 4. crew airlocks: one per pressure zone (frame) of hull front that has none
    c = fx.get("crew")
    if c:
        cw, cd = c["chamber_m"][0] / 1000.0, c["chamber_m"][1] / 1000.0
        dw, dd = c["door_width_m"] / 1000.0, c["door_depth_m"] / 1000.0
        per = {}
        for z in res["zones"]:
            if z["airlocks"]:
                continue
            p = pmap[z["precinct"]]
            occ = prep(unary_union([occupied(p)] + taken).buffer(0.003))
            a, b = z["x"]
            x = (a + b) / 2 - cw / 2
            found = None
            for k in range(0, int((b - a) * 1000)):  # walk out from the middle of the zone, 1 m at a time
                for xx in (x + k / 1000.0, x - k / 1000.0):
                    if xx < a + 0.005 or xx + cw > b - 0.005:
                        continue
                    r = [round(xx, 4), round(xx + cw, 4), z["y"], round(z["y"] + cd, 4)]
                    if not occ.intersects(box(r[0], r[2], r[1], r[3])):
                        found = r
                        break
                if found:
                    break
            if found:
                xm = (found[0] + found[1]) / 2
                per.setdefault(p["id"], []).append((z["frame"], found, [round(xm - dw / 2, 4), round(xm + dw / 2, 4), round(z["y"] - dd, 4), z["y"]]))
                take(found)
            else:
                per.setdefault(p["id"], []).append((z["frame"], None, None))
        for pid, lst in per.items():
            ok = [t for t in lst if t[1]]
            if not ok:
                continue
            p = pmap[pid]
            xs = [t[1] for t in ok]
            out.append(_new(p, [o for o in out if "building" in o], name=c["name"].format(pid=p["name"]), kind=c["kind"], category=c["category"],
                            size_text="%d airlocks, each %s" % (len(ok), _size_text(*c["chamber_m"])), size_m=list(c["chamber_m"]),
                            rect_km=[min(r[0] for r in xs), max(r[1] for r in xs), min(r[2] for r in xs), max(r[3] for r in xs)],
                            bays_km=xs, bay_count=len(ok), bay_names=["Airlock %s" % t[0] for t in ok], doors_km=[t[2] for t in ok],
                            notes="Planner, 28 Nov 2026: one per pressure zone; %s" % c["door_note"], purpose=c["purpose"]))
            missing = [t[0] for t in lst if not t[1]]
            if missing:
                out[-1]["no_room"] = missing
    # 5. border posts where hull doors are too far from a clearance point
    cl = res.get("clearance")
    f = fx.get("clearance")
    if cl and f and cl["far"]:
        by_p = {}
        for dr, best, dist in cl["far"]:
            by_p.setdefault(dr["precinct"], []).append(dr)
        for pid, drs in sorted(by_p.items()):
            p = pmap[pid]
            tx = sum(dr["point"][0] for dr in drs) / len(drs)
            ty = max(dr["point"][1] for dr in drs) + 0.35
            where = re.sub(r"^(Bow|Stern) Docks.*", r"\1 Docks", p["name"])
            far = max(drs, key=lambda dr: abs(dr["point"][0] - tx))
            p, r = place_near(d, p, f["size_m"], (tx, ty), taken, out, must_reach=(far["point"], cl["rule"]["within_km"]))
            if not r:
                gaps.append("%s: no free land within %s of %d hull doors for a %s" % (pid, G.fmt_len_m(cl["rule"]["within_km"] * 1000), len(drs), f["name"].format(where=where)))
            if r:
                out.append(_new(p, [o for o in out if "building" in o], name=f["name"].format(where=where), kind="building", category=f["category"],
                                size_text=_size_text(*f["size_m"]), size_m=list(f["size_m"]), rect_km=r,
                                notes="Planner, 28 Nov 2026: border clearance for %d hull doors more than %s from one" % (len(drs), G.fmt_len_m(cl["rule"]["within_km"] * 1000)),
                                purpose=f["purpose"], services="Passport desks, customs counters and a health check for crews and passengers of the berths"))
                take(r)
    # 6. one command room for every hull door
    f = fx.get("command")
    cm = next((m for m in res["must_have"] if m["rule"]["id"] == "command"), None)
    if f and cm and not cm["ok"]:
        p = pmap[f["precinct"]]
        real = [dr for dr in res["doors"] if dr["cls"] != "crew"]
        tx = sum(dr["point"][0] for dr in real) / max(1, len(real))
        p, r = place_near(d, p, f["size_m"], (tx, p["bounds_km"][2] + 0.9), taken, out, reach_km=2.0)
        if r:
            out.append(_new(p, [o for o in out if "building" in o], name=f["name"], kind="building", category=f["category"],
                            size_text=_size_text(*f["size_m"]), size_m=list(f["size_m"]), rect_km=r,
                            notes="Planner, 28 Nov 2026: one command room for every hull door of the port",
                            purpose=f["purpose"], services=f["services_text"]))
            take(r)
    # 7. response posts where hull doors are still out of reach once the above is added. A post goes near
    # the furthest door; repeat until every door is in reach or nothing more fits.
    import copy
    skip = set()
    for _ in range(12):
        d2 = copy.deepcopy(d)
        apply(d2, out)
        res2 = check(d2, prog)
        placed = False
        for rr in res2["response"]:
            f = (fx.get("response") or {}).get(rr["rule"]["id"])
            if not f or not rr["far"]:
                continue
            far = [t for t in rr["far"] if (rr["rule"]["id"], t[0]["precinct"]) not in skip]
            if not far:
                continue
            dr0 = max(far, key=lambda t: t[2] if t[2] is not None else 1e9)[0]
            p = pmap[dr0["precinct"]]
            near = [dr for dr, best, dist in rr["far"] if dr["precinct"] == p["id"] and
                    math.hypot(dr["point"][0] - dr0["point"][0], dr["point"][1] - dr0["point"][1]) <= rr["rule"]["within_km"]]
            tx = sum(dr["point"][0] for dr in near) / len(near)
            ty = max(dr["point"][1] for dr in near) + 0.3
            where = re.sub(r"^(Bow|Stern) Docks.*", r"\1 Docks", p["name"])
            p, r = place_near(d, p, f["size_m"], (tx, ty), taken, out, must_reach=(dr0["point"], rr["rule"]["within_km"]))
            if not r:
                gaps.append("%s: no free land within %s of %d hull doors for a %s" % (dr0["precinct"], G.fmt_len_m(rr["rule"]["within_km"] * 1000), len(near), f["name"].format(where=where)))
                skip.add((rr["rule"]["id"], dr0["precinct"]))
                continue
            name = f["name"].format(where=where)
            k = sum(1 for o in out if "building" in o and o["building"]["name"].startswith(name))
            out.append(_new(p, [o for o in out if "building" in o], name=name + (" %d" % (k + 1) if k else ""), kind="building",
                            category=f["category"], size_text=_size_text(*f["size_m"]), size_m=list(f["size_m"]), rect_km=r,
                            notes="Planner, 28 Nov 2026: %d hull door%s more than %s from %s" % (len(near), " was" if len(near) == 1 else "s were",
                                                                                            G.fmt_len_m(rr["rule"]["within_km"] * 1000), rr["rule"]["name"].lower()),
                            purpose=f["purpose"]))
            take(r)
            placed = True
        if not placed:
            break
    gaps[:] = sorted(set(gaps))
    return out


def apply(d, proposals):
    """Add the proposals to the district data (in place). Returns the list of what was added."""
    pmap = {p["id"]: p for p in d["precincts"]}
    done = []
    for o in proposals:
        p = pmap[o["precinct"]]
        if "building" in o:
            if any(b["name"] == o["building"]["name"] for b in p["buildings"]):
                continue
            p["buildings"].append(o["building"])
            done.append(o)
        else:
            b = next(b for b in p["buildings"] if b["id"] == o["add_to"])
            if not b.get(o["field"]):
                b[o["field"]] = o["value"]
                b["notes"] = (b.get("notes") + "; " if b.get("notes") else "") + o["note"]
                done.append(o)
    return done
