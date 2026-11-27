"""The building fabric: walls, doors, windows, stairs, lifts and floor slabs, worked out
from a building's room plan (Invicta/data/models/<uid>.json).

Jordan, 27 Nov 2026 (plan step 3): "yes" to walls, doors, windows and stairs, with every
existing room and design kept. So nothing here changes a plan file. The rooms stay the
design; the fabric is worked out from them by fixed rules, the same way every time, and
added wherever a plan is shown or exported (the website's 2D and 3D, the docs, and later
the game export). Anything already drawn in a plan (a hand-placed door, a hangar door)
is kept and wins: the rules only fill in what is missing.

Every element made here has "derived": true and status "proposed". Positions are metres
to the millimetre, in the plan frame (from the lot's bow-port corner, x toward the stern,
y toward starboard, z above the deck).

Rules (US first, metric alongside):
- Walls on every edge between spaces: outside walls 1 ft (0.30 m) thick, stair and lift
  core walls 10 in (0.25 m), partitions 6 in (0.15 m). Full floor height.
- Doors: every room gets a door, to a corridor or other open zone first, then to a stair
  core, then to a neighbouring room that is already reachable. Single doors 3 ft (0.9 m)
  wide and 6 ft 11 in (2.1 m) high; double doors 5 ft 11 in (1.8 m) for rooms over
  1,615 sq ft (150 m²). Every stair core gets a door on each floor. The ground floor gets
  an entrance in each corridor or zone with an outside wall (at least one per building).
- Windows: along outside walls of rooms and zones above ground, except stores, vaults,
  plant, server and wash rooms. Panes 3 ft 11 in (1.2 m) wide every 5 ft 11 in (1.8 m),
  sill 2 ft 11 in (0.9 m).
- Stairs: in every core, between each floor and the next. Risers at most 7 in (0.18 m),
  treads 11 in (0.28 m), two flights 3 ft 11 in (1.2 m) wide with landings 4 ft 11 in
  (1.5 m) deep (a half-turn stair). If it can't fit in the core, it is marked "fits": false
  and the scan says so. A lift shaft 8 ft 6 in (2.6 m) square goes beside it where there
  is room.
- Floor slabs 1 ft (0.30 m) thick under every floor's rooms, with holes for stairs and lifts.
"""

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

T_OUTSIDE, T_CORE, T_PARTITION = 0.30, 0.25, 0.15
DOOR_W, DOOR_H, DOUBLE_W, DOUBLE_H, BIG_ROOM_M2 = 0.9, 2.1, 1.8, 2.4, 150.0
ENTRANCE_W = 1.8
WIN_W, WIN_STEP, WIN_SILL, WIN_HEAD = 1.2, 1.8, 0.9, 2.4
RISER_MAX, TREAD, FLIGHT_W, LANDING = 0.18, 0.28, 1.2, 1.5
LIFT = 2.6
SLAB_T = 0.30
NO_WINDOWS = ("vault", "store", "storage", "plant", "server", "magazine", "strongroom", "riser",
              "toilet", "wc", "washroom", "shower", "changing", "cold room", "freezer")
SPACES = ("room", "zone", "core")
EPS = 0.05  # m: how far either side of a wall line to look for the spaces it divides


def _r(v):
    return round(float(v), 3)


def _pt(p):
    return [_r(p[0]), _r(p[1])]


def _levels(e):
    return e.get("levels") or ([e["level"]] if e.get("level") else [])


def _poly(o):
    p = Polygon(o)
    if not p.is_valid:
        p = shapely.make_valid(p).buffer(0)
        if p.geom_type == "MultiPolygon":
            p = max(p.geoms, key=lambda g: g.area)
    return p


def _union(geoms):
    try:
        return shapely.union_all(geoms)
    except shapely.errors.GEOSException:  # rare noding trouble: snap to the millimetre and retry
        return shapely.union_all(geoms, grid_size=0.001)


def _walls_on_level(on, polys, by_id):
    """Walls between the spaces on one floor: [(pair, a, b, kind)], pair = (id, id or None)."""
    ids = [e["id"] for e in on]
    geoms = np.array([polys[i] for i in ids], dtype=object)
    areas = shapely.area(geoms)
    tree = STRtree(geoms)
    net = _union(shapely.boundary(geoms))
    segs = []      # (piece number, a, b)
    for k, part in enumerate(shapely.get_parts(net)):
        c = shapely.get_coordinates(part)
        for i in range(len(c) - 1):
            if abs(c[i + 1][0] - c[i][0]) + abs(c[i + 1][1] - c[i][1]) > 1e-3:
                segs.append((k, c[i], c[i + 1]))
    if not segs:
        return []
    A = np.array([q[1] for q in segs])
    B = np.array([q[2] for q in segs])
    d = B - A
    ln = np.hypot(d[:, 0], d[:, 1])
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1) / ln[:, None]
    mid = (A + B) / 2
    sides = []
    for sgn in (1, -1):
        hit = tree.query(shapely.points(mid + sgn * EPS * nrm), predicate="intersects")
        best = np.full(len(segs), -1)
        if len(hit[0]):
            # smallest space wins where two overlap (the more specific one)
            o = np.lexsort((areas[hit[1]], hit[0]))
            pi, gi = hit[0][o], hit[1][o]
            first = np.r_[True, pi[1:] != pi[:-1]]
            best[pi[first]] = gi[first]
        sides.append(best)
    out = []
    run = None  # [piece, pair, a, b, direction]
    for k, (piece, a, b) in enumerate(segs):
        s1, s2 = sides[0][k], sides[1][k]
        if s1 == s2:
            if run:
                out.append(run); run = None
            continue
        pair = tuple(sorted([ids[s1] if s1 >= 0 else None, ids[s2] if s2 >= 0 else None], key=lambda x: (x is None, x or "")))
        u = d[k] / ln[k]
        if run and run[0] == piece and run[1] == pair and abs(run[4][0] * u[1] - run[4][1] * u[0]) < 1e-6 \
                and np.allclose(run[3], a, atol=1e-6):
            run[3] = b
        else:
            if run:
                out.append(run)
            run = [piece, pair, a, b, u]
    if run:
        out.append(run)
    walls = []
    for piece, pair, a, b, u in out:
        kinds = [by_id[x]["type"] if x else None for x in pair]
        kind = "exterior" if None in pair else ("core" if "core" in kinds else "interior")
        walls.append((pair, (float(a[0]), float(a[1])), (float(b[0]), float(b[1])), kind))
    return walls


def build(m):
    """Work out the fabric of one plan. Returns (elements, report).
    report = {"unreachable": [space names], "stairs_not_fitting": [core notes], "entrances": n}."""
    levels = sorted(m.get("levels", []), key=lambda l: l.get("z_m", 0))
    lv_by = {l["id"]: l for l in levels}
    order = [l["id"] for l in levels]
    ground = next((l["id"] for l in levels if abs(l.get("z_m", 0)) < 0.01), order[0] if order else None)
    els = m.get("elements", [])
    out = []
    report = {"unreachable": [], "stairs_not_fitting": [], "entrances": 0}
    n = {"W": 0, "D": 0, "N": 0, "S": 0, "L": 0, "F": 0}

    def nid(k):
        n[k] += 1
        return "F-%s%d" % (k, n[k])

    spaces = [e for e in els if e.get("type") in SPACES and not e.get("outdoor") and len(e.get("outline_m") or []) >= 3]
    polys = {e["id"]: _poly(e["outline_m"]) for e in spaces}
    by_id = {e["id"]: e for e in spaces}
    on_level = {L: [e for e in spaces if L in _levels(e) and not polys[e["id"]].is_empty] for L in order}

    # ---- walls
    walls_at = {}   # (space id, level) -> [wall]
    for L in order:
        if not on_level[L]:
            continue
        h = lv_by[L].get("height_m") or 0
        for pair, a, b, kind in _walls_on_level(on_level[L], polys, by_id):
            w = (pair, a, b, kind, L)
            for x in pair:
                if x:
                    walls_at.setdefault((x, L), []).append(w)
            out.append({"id": nid("W"), "type": "wall", "level": L, "line_m": [_pt(a), _pt(b)],
                        "thickness_m": {"exterior": T_OUTSIDE, "core": T_CORE, "interior": T_PARTITION}[kind],
                        "height_m": _r(h), "kind": kind, "between": [x for x in pair if x],
                        "status": "proposed", "derived": True})

    # ---- the walking graph: doors, openings and stairs join (space, level) nodes
    graph = {}

    def link(a, b):
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)

    doored = set()  # (space, level) that already have a door or opening
    entrances = set()

    def add_door(space, w, width, height, name, kind="door"):
        pair, a, b, _, L = w
        length = math.dist(a, b)
        width = min(width, length - 0.3)
        if width < DOOR_W - 1e-9:
            return False
        h = lv_by[L].get("height_m") or height
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        c0 = length / 2 - width / 2
        p1 = (a[0] + ux * c0, a[1] + uy * c0)
        p2 = (a[0] + ux * (c0 + width), a[1] + uy * (c0 + width))
        out.append({"id": nid("D"), "type": kind, "name": name, "level": L, "line_m": [_pt(p1), _pt(p2)],
                    "width_m": _r(width), "height_m": _r(min(height, h)), "between": [x for x in pair if x],
                    "status": "proposed", "derived": True})
        for x in pair:
            if x:
                doored.add((x, L))
        other = [x for x in pair if x and x != space]
        if other:
            link((space, L), (other[0], L))
        return True

    def partner(space, w):
        return next((x for x in w[0] if x != space), None)

    def rank(space, w):
        o = partner(space, w)
        pri = {"zone": 0, "core": 1, "room": 2}[by_id[o]["type"]] if o else 9
        return (pri, -math.dist(w[1], w[2]))

    def door_size(space):
        big = by_id[space]["type"] == "room" and polys[space].area > BIG_ROOM_M2
        return (DOUBLE_W, DOUBLE_H) if big else (DOOR_W, DOOR_H)

    # doors already drawn in the plan (hand-placed, hangar doors): kept, and they join what they touch
    for dr in (e for e in els if e.get("type") in ("door", "opening") and e.get("line_m")):
        for L in (_levels(dr) or order[:1]):
            if L not in on_level:
                continue
            zone = LineString(dr["line_m"]).buffer(0.3)
            t = [e["id"] for e in on_level[L] if polys[e["id"]].intersects(zone)]
            for x in t:
                doored.add((x, L))
            for i in range(len(t)):
                for j in range(i + 1, len(t)):
                    link((t[i], L), (t[j], L))
            if len(t) == 1 and L == ground:
                entrances.add((t[0], L))

    # a full-height hall is one tall space, not one per floor: its floors are the same place
    for e in spaces:
        if e.get("full_height"):
            cl = [L for L in order if L in _levels(e)]
            for a_, b_ in zip(cl, cl[1:]):
                link((e["id"], a_), (e["id"], b_))

    # stairs join each core's floors; every core gets a door on every floor
    for e in spaces:
        if e["type"] != "core":
            continue
        cl = [L for L in order if L in _levels(e)]
        for a_, b_ in zip(cl, cl[1:]):
            link((e["id"], a_), (e["id"], b_))
        for L in cl:
            if (e["id"], L) in doored:
                continue
            for w in sorted((w for w in walls_at.get((e["id"], L), []) if None not in w[0]), key=lambda w: rank(e["id"], w)):
                if add_door(e["id"], w, DOOR_W, DOOR_H, "Stair door"):
                    break

    # neighbouring zones (corridors, lobbies, yards) open into each other
    for (x, L), ws in walls_at.items():
        if by_id[x]["type"] != "zone":
            continue
        for w in ws:
            o = partner(x, w)
            if o and by_id[o]["type"] == "zone" and (o, L) not in graph.get((x, L), ()):
                add_door(x, w, DOUBLE_W, DOUBLE_H, "Opening", "opening")

    # entrances on the ground floor: each corridor or zone with an outside wall, else the biggest room
    if ground in on_level:
        def outside_walls(x):
            return sorted((w for w in walls_at.get((x, ground), []) if None in w[0]), key=lambda w: -math.dist(w[1], w[2]))
        cands = [e["id"] for e in on_level[ground] if e["type"] == "zone" and outside_walls(e["id"])]
        if not cands:  # corridors all inside: the biggest room on an outside wall is the entrance hall
            cands = sorted((e["id"] for e in on_level[ground] if e["type"] == "room" and outside_walls(e["id"])),
                           key=lambda x: -polys[x].area)[:1]
        for x in cands:
            for w in outside_walls(x)[:1]:
                if add_door(x, w, ENTRANCE_W, DOUBLE_H, "Entrance"):
                    entrances.add((x, ground))
                    report["entrances"] += 1

    def reach():
        seen = set(entrances)
        todo = list(entrances)
        while todo:
            k = todo.pop()
            for nb in graph.get(k, ()):
                if nb not in seen:
                    seen.add(nb)
                    todo.append(nb)
        return seen

    # grow inward from the entrances: every space not yet reachable gets a door to a reachable neighbour
    nodes = [(e["id"], L) for e in spaces for L in _levels(e) if L in lv_by]

    def grow():
        seen = reach()
        while True:
            added = False
            for k in nodes:
                if k in seen:
                    continue
                x, L = k
                opts = [w for w in walls_at.get(k, []) if None not in w[0] and (partner(x, w), L) in seen]
                for w in sorted(opts, key=lambda w: rank(x, w)):
                    wd, ht = door_size(x)
                    if add_door(x, w, wd, ht, "Door"):
                        added = True
                        break
            if not added:
                return seen
            seen = reach()

    seen = grow()
    # a ground-floor part still cut off (a kiosk in a park, a wing with its own way in) gets its own
    # outside door, biggest space first, until everything on the ground floor that can have one does
    for _ in range(50):
        cut = [x for x, L in nodes if L == ground and (x, L) not in seen and by_id[x]["type"] != "core"
               and any(None in w[0] for w in walls_at.get((x, L), []))]
        if not cut:
            break
        x = max(cut, key=lambda i: polys[i].area)
        ext = sorted((w for w in walls_at[(x, ground)] if None in w[0]), key=lambda w: -math.dist(w[1], w[2]))
        wd, ht = door_size(x)
        if not any(add_door(x, w, max(wd, DOOR_W), ht, "Outside door") for w in ext[:1]):
            walls_at[(x, ground)] = [w for w in walls_at[(x, ground)] if None not in w[0]]  # too short: skip it
            continue
        entrances.add((x, ground))
        report["entrances"] += 1
        seen = grow()
    # a room still without a door (cut off, for example a floor with no stairs) gets its best one anyway
    for k in nodes:
        x, L = k
        if by_id[x]["type"] == "room" and k not in doored:
            for w in sorted((w for w in walls_at.get(k, []) if None not in w[0]), key=lambda w: rank(x, w)):
                wd, ht = door_size(x)
                if add_door(x, w, wd, ht, "Door"):
                    break
    seen = reach()
    for x, L in nodes:
        if (x, L) not in seen:
            report["unreachable"].append("%s %s (%s)" % (x, by_id[x].get("name", ""), L))

    # ---- windows: outside walls of rooms and zones above ground
    entrance_walls = {(e["level"], tuple(e["line_m"][0])) for e in out if e.get("name") == "Entrance"}
    for (x, L), ws in walls_at.items():
        sp = by_id[x]
        lv = lv_by[L]
        if lv.get("z_m", 0) < 0 or sp["type"] == "core" or any(t in sp.get("name", "").lower() for t in NO_WINDOWS):
            continue
        h = lv.get("height_m") or 3
        for pair, a, b, kind, _ in ws:
            if kind != "exterior":
                continue
            length = math.dist(a, b)
            count = int((length - 0.6 - WIN_W) // WIN_STEP) + 1 if length >= WIN_W + 0.6 else 0
            if count < 1:
                continue
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            run = (count - 1) * WIN_STEP + WIN_W
            s0 = (length - run) / 2
            p1 = (a[0] + ux * s0, a[1] + uy * s0)
            p2 = (a[0] + ux * (s0 + run), a[1] + uy * (s0 + run))
            out.append({"id": nid("N"), "type": "window", "level": L, "line_m": [_pt(p1), _pt(p2)],
                        "count": count, "pane_width_m": WIN_W, "spacing_m": WIN_STEP, "sill_m": WIN_SILL,
                        "head_m": _r(min(WIN_HEAD, max(WIN_SILL + 0.6, h - 0.4))), "space": x,
                        "status": "proposed", "derived": True})

    # ---- stairs and lifts in every core
    holes = {}
    for e in spaces:
        if e["type"] != "core":
            continue
        cl = [L for L in order if L in _levels(e)]
        env = shapely.oriented_envelope(polys[e["id"]])
        if env.geom_type != "Polygon":
            continue
        c = np.asarray(env.exterior.coords)[:4]
        e1, e2 = c[1] - c[0], c[3] - c[0]
        if np.hypot(*e1) < np.hypot(*e2):
            e1, e2 = e2, e1
        lenL, lenD = float(np.hypot(*e1)), float(np.hypot(*e2))
        u, v = e1 / lenL, e2 / lenD

        def rect(x0, x1, y0, y1):
            return [_pt(c[0] + u * x0 + v * y0), _pt(c[0] + u * x1 + v * y0),
                    _pt(c[0] + u * x1 + v * y1), _pt(c[0] + u * x0 + v * y1)]

        stair_len = 0.0
        for a_, b_ in zip(cl, cl[1:]):
            h = lv_by[b_]["z_m"] - lv_by[a_]["z_m"]
            if h <= 0:
                continue
            risers = math.ceil(h / RISER_MAX - 1e-9)
            per = math.ceil(risers / 2)
            length = (per - 1) * TREAD + 2 * LANDING
            width = 2 * FLIGHT_W + 0.1
            fits = length <= lenL + 1e-6 and width <= lenD + 1e-6
            stair_len = max(stair_len, min(length, lenL))
            o = rect(0, min(length, lenL), 0, min(width, lenD))
            out.append({"id": nid("S"), "type": "stair", "name": "Stairs", "level": a_, "to_level": b_, "outline_m": o,
                        "risers": risers, "riser_m": _r(h / risers), "tread_m": TREAD, "flights": 2,
                        "flight_width_m": FLIGHT_W, "landing_m": LANDING, "fits": fits, "core": e["id"],
                        "status": "proposed", "derived": True})
            holes.setdefault(b_, []).append(Polygon(o))
            if not fits:
                report["stairs_not_fitting"].append("%s %s, %s to %s: needs %.1f × %.1f m, the core is %.1f × %.1f m" % (
                    e["id"], e.get("name", ""), a_, b_, length, width, lenL, lenD))
        if len(cl) > 1 and lenL - stair_len >= LIFT + 0.2 and lenD >= LIFT:
            o = rect(lenL - LIFT, lenL, 0, LIFT)
            out.append({"id": nid("L"), "type": "lift", "name": "Lift", "levels": cl, "outline_m": o, "core": e["id"],
                        "status": "proposed", "derived": True})
            for L in cl[1:]:
                holes.setdefault(L, []).append(Polygon(o))

    # ---- floor slabs
    for L in order:
        # no floor across the upper levels of a full-height hall: it is open to its roof
        on = [polys[e["id"]] for e in on_level[L]
              if not (e.get("full_height") and L != next(x for x in order if x in _levels(e)))]
        if not on:
            continue
        g = _union(np.array(on, dtype=object))
        if holes.get(L):
            g = g.difference(_union(np.array(holes[L], dtype=object)))
        for part in shapely.get_parts(g):
            if part.geom_type != "Polygon" or part.area < 0.5:
                continue
            out.append({"id": nid("F"), "type": "slab", "level": L, "z_m": _r(lv_by[L].get("z_m", 0)),
                        "outline_m": [_pt(q) for q in part.exterior.coords[:-1]],
                        "holes_m": [[_pt(q) for q in r.coords[:-1]] for r in part.interiors],
                        "thickness_m": SLAB_T, "status": "proposed", "derived": True})
    return out, report



def compact(extra):
    """The fabric in a compact form for the website and the game export: walls and windows grouped
    per floor and kind (four numbers a line), doors without the bookkeeping. Same geometry."""
    out = []
    walls, wins = {}, {}
    for e in extra:
        t = e["type"]
        if t == "wall":
            k = (e["level"], e["kind"], e["thickness_m"], e["height_m"])
            walls.setdefault(k, []).append(e["line_m"][0] + e["line_m"][1])
        elif t == "window":
            k = (e["level"], e["sill_m"], e["head_m"])
            wins.setdefault(k, []).append(e["line_m"][0] + e["line_m"][1] + [e["count"]])
        elif t in ("door", "opening"):
            out.append({"type": t, "name": e["name"], "level": e["level"], "line_m": e["line_m"],
                        "width_m": e["width_m"], "height_m": e["height_m"], "derived": True})
        else:
            out.append({k: v for k, v in e.items() if k not in ("status",)})
    for (L, kind, th, h), lines in walls.items():
        out.append({"type": "walls", "level": L, "kind": kind, "thickness_m": th, "height_m": h,
                    "lines_m": lines, "derived": True})
    for (L, sill, head), lines in wins.items():
        out.append({"type": "windows", "level": L, "sill_m": sill, "head_m": head, "pane_width_m": WIN_W,
                    "spacing_m": WIN_STEP, "lines_m": lines, "derived": True})
    return out

def with_fabric(m):
    """A copy of the plan with its fabric added (schema model@2), for showing and exporting."""
    extra, report = build(m)
    out = dict(m)
    out["schema"] = "invicta-atlas/model@2"
    out["elements"] = list(m.get("elements", [])) + compact(extra)
    out["fabric"] = {"rules": "atlaslib/fabric.py", "status": "proposed", "derived_elements": len(extra),
                     "entrances": report["entrances"], "unreachable": len(report["unreachable"]),
                     "stairs_not_fitting": len(report["stairs_not_fitting"])}
    return out
