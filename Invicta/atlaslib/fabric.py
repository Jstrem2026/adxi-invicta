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

Rules (US first, metric alongside). The sizes come from data/standards.json (Jordan, 28 Nov 2026: US building
standards, IBC and ADA):
- Walls on every edge between spaces: outside walls 1 ft (0.30 m) thick, stair and lift
  core walls 10 in (0.25 m), partitions 4-7/8 in (0.12 m). Full floor height.
- Doors: every room gets a door, to a corridor or other open zone first, then to a stair
  core, then to a neighbouring room that is already reachable. Single doors 3 ft x 6 ft 8 in
  (0.91 x 2.03 m), 7 ft (2.13 m) high under ceilings of 9 ft (2.74 m) or more; double doors
  6 x 7 ft (1.83 x 2.13 m) for rooms over 1,615 sq ft (150 m²). Entrances are 6 x 8 ft
  (1.83 x 2.44 m) double doors; openings between corridors are 8 ft (2.44 m) high. A door is
  kept clear of any wall that meets its wall part way along. Every stair core gets a door on each
  floor. The ground floor gets an entrance in each corridor or zone with an outside wall (at least
  one per building). Entrances face the street where they can, else a courtyard, never a gap
  narrower than 10 ft (3 m) between rooms or a closed-in corner smaller than 1,076 sq ft (100 m²).
  A long building gets one entrance per 394 ft (120 m) of street front (at most 12), through the
  street-side room beside a corridor farthest from the others, which also opens onto that corridor.
- No door opens into a full-height hall or shaft above its bottom floor (Jordan, 28 Nov 2026): there is no floor there,
  only the drop. Such a hall gets doors on its bottom floor only; upper floors reach it by its stairs or lift core.
- Windows: along outside walls of rooms and zones above ground, except stores, vaults,
  plant, server and wash rooms. Panes 3 ft 11 in (1.2 m) wide every 5 ft 11 in (1.8 m),
  sill 3 ft (0.91 m), head 7 ft (2.13 m), in line with the tops of doors.
- Stairs: in every core, between each floor of the building and the next (never between decks:
  decks are joined only by fast elevators and teleport pads). Risers at most 7 in (0.178 m),
  treads 11 in (0.279 m), two flights 3 ft 11 in (1.2 m) wide (at least 44 in, 1.12 m) with landings
  4 ft 11 in (1.5 m) deep (a half-turn stair), no flight climbing more than 12 ft (3.66 m). A tall
  floor whose stair is too long for its core turns back on itself more times on the way up (as many
  half-turns as it needs, "turns"), the way real stairs climb tall halls. If it still can't fit in
  the core, it is marked "fits": false and the scan says so. A lift shaft 8 ft 6 in (2.6 m) square
  goes beside it where there is room.
- Floor slabs 1 ft (0.30 m) thick under every floor's rooms, with holes for stairs and lifts.
"""

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

import json
import os

# Door, window and stair sizes come from data/standards.json (Jordan, 28 Nov 2026: US building standards).
STANDARDS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "standards.json")
with open(STANDARDS_FILE, encoding="utf-8") as _f:
    STANDARDS = json.load(_f)
_D, _W, _S = (STANDARDS["building"][k] for k in ("doors", "windows", "stairs"))

_WL = STANDARDS["building"]["walls"]
T_OUTSIDE, T_CORE, T_PARTITION = _WL["exterior_m"], _WL["core_m"], _WL["partition_m"]
# Doors 3 ft x 6 ft 8 in (0.91 x 2.03 m), 7 ft (2.13 m) on floors with ceilings 9 ft (2.74 m) or more; double doors
# 6 x 7 ft (1.83 x 2.13 m); street entrances and openings between corridors 6 x 8 ft (1.83 x 2.44 m).
DOOR_W, DOOR_H, DOUBLE_W, BIG_ROOM_M2 = _D["single_width_m"], _D["height_m"], _D["double_width_m"], 150.0
DOUBLE_H = _D["double_height_m"]
TALL_DOOR_H, TALL_CEILING_M, ENTRANCE_H = _D["tall_height_m"], _D["tall_ceiling_m"], _D["entrance_height_m"]
ENTRANCE_W = _D["entrance_width_m"]
WIN_W, WIN_STEP, WIN_SILL, WIN_HEAD = _W["pane_width_m"], _W["pane_step_m"], _W["sill_m"], _W["head_m"]
RISER_MAX, TREAD, FLIGHT_W, LANDING = _S["riser_max_m"], _S["tread_m"], _S["flight_width_m"], _S["landing_m"]
FLIGHT_W_MIN = _S["flight_width_min_m"]
FLIGHT_RISE_MAX = _S["flight_rise_max_m"]  # 12 ft: the most a flight may climb between landings
MIN_FLIGHT_RISERS = 3
LIFT = 2.6
OUTSIDE_DOORS_MAX = 400  # a row of hangar bays can need one each
MAX_TURNS = 40  # half-turns a stair may make within one floor (a stair tower in a tall hall makes many)
SLAB_T = 0.30
OPEN_AIR_M = 3.0  # 10 ft: a gap between rooms narrower than this is not open air, so no entrance faces it
ENTRANCE_EVERY_M = 120.0  # 394 ft of street front per entrance, for long buildings
ENTRANCES_MAX = 12
COURTYARD_MIN_M2 = 100.0  # 1,076 sq ft: an enclosed gap smaller than this is a leftover corner, not a courtyard
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
    junctions = {}  # level -> wall end points, where walls meet
    entrances = set()

    def add_door(space, w, width, height, name, kind="door"):
        pair, a, b, _, L = w
        length = math.dist(a, b)
        width = min(width, length - 0.3)
        if width < DOOR_W - 1e-9:
            return False
        h = lv_by[L].get("height_m") or height
        if height == DOOR_H and h - SLAB_T >= TALL_CEILING_M:
            height = TALL_DOOR_H   # a taller door under a taller ceiling
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        # keep the doorway clear of any wall that meets this one part way along (a corner of a core, a partition):
        # the door goes as near the middle as it can with no wall end inside it
        if L not in junctions:
            junctions[L] = [tuple(q) for e in out if e["type"] == "wall" and e["level"] == L for q in e["line_m"]]
        blocked = []
        for q in junctions[L]:
            along = (q[0] - a[0]) * ux + (q[1] - a[1]) * uy
            if 0.05 < along < length - 0.05 and abs((q[0] - a[0]) * uy - (q[1] - a[1]) * ux) < 0.2:
                blocked.append((along - 0.3, along + 0.3))
        c0 = length / 2 - width / 2
        if blocked:
            spots = sorted((k * 0.05 for k in range(int((length - width) / 0.05) + 1)), key=lambda c: abs(c - c0))
            spots = [c for c in spots if 0.15 <= c <= length - width - 0.15
                     and all(c + width <= lo or c >= hi for lo, hi in blocked)]
            if not spots:
                return False
            c0 = spots[0]
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

    def drop(space, L):
        """True for an upper floor of a full-height hall or shaft: open air down to its bottom floor, no floor to stand on."""
        if not space or not by_id[space].get("full_height"):
            return False
        cl = [x for x in order if x in _levels(by_id[space])]
        return bool(cl) and L != cl[0]

    def rank(space, w):
        o = partner(space, w)
        pri = {"zone": 0, "core": 1, "room": 2}[by_id[o]["type"]] if o else 9
        if o and drop(o, w[4]):
            pri = 8   # last choice: a door into an open drop
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
                add_door(x, w, DOUBLE_W, ENTRANCE_H, "Opening", "opening")

    # entrances on the ground floor: each corridor or zone with an outside wall, else the biggest room.
    # An outside wall here is one that opens to the air: the street first, then a courtyard. A wall that only
    # faces a gap left between rooms (narrower than OPEN_AIR_M) is not a way in (Jordan, 27 Nov 2026: "WHERE IS
    # THE DOOR?" - entrances were opening into gaps inside the building, out of sight of the street).
    air = {}
    if ground in on_level and on_level[ground]:
        floor = _union(np.array([polys[e["id"]] for e in on_level[ground]], dtype=object))
        closed = floor.buffer(OPEN_AIR_M / 2, join_style="mitre").buffer(-OPEN_AIR_M / 2, join_style="mitre").union(floor)
        # a small enclosed gap (a leftover corner between corridors) is not a courtyard either
        gaps = [Polygon(r) for q in shapely.get_parts(closed) if q.geom_type == "Polygon" for r in q.interiors]
        gaps = [g for g in gaps if g.area < COURTYARD_MIN_M2]
        if gaps:
            closed = closed.union(shapely.union_all(gaps))
        street = shapely.union_all([Polygon(q.exterior) for q in shapely.get_parts(closed) if q.geom_type == "Polygon"])
        shapely.prepare(closed)
        shapely.prepare(street)

        def facing(x, w):
            """0 when the wall faces the street, 1 a courtyard, None when it faces neither (a gap inside)."""
            if (x, w[1], w[2]) in air:
                return air[(x, w[1], w[2])]
            a, b = w[1], w[2]
            L = math.dist(a, b) or 1.0
            mx, my, nx, ny = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, -(b[1] - a[1]) / L, (b[0] - a[0]) / L
            out = None
            for sg in (1, -1):
                q = Point(mx + nx * 0.6 * sg, my + ny * 0.6 * sg)
                if polys[x].covers(q):
                    continue
                if not street.covers(q):
                    out = 0
                elif not closed.covers(q):
                    out = 1 if out is None else out
            air[(x, w[1], w[2])] = out
            return out
    else:
        def facing(x, w):
            return 0

    if ground in on_level:
        def outside_walls(x):
            ws = [w for w in walls_at.get((x, ground), []) if None in w[0] and facing(x, w) is not None]
            return sorted(ws, key=lambda w: (facing(x, w), -math.dist(w[1], w[2])))
        cands = [e["id"] for e in on_level[ground] if e["type"] == "zone" and outside_walls(e["id"])]
        if not cands:  # corridors all inside: the biggest room on an outside wall is the entrance hall
            cands = sorted((e["id"] for e in on_level[ground] if e["type"] == "room" and outside_walls(e["id"])),
                           key=lambda x: -polys[x].area)[:1]
        ent_at = []
        for x in cands:
            for w in outside_walls(x)[:1]:
                if add_door(x, w, ENTRANCE_W, ENTRANCE_H, "Entrance"):
                    entrances.add((x, ground))
                    ent_at.append(((w[1][0] + w[2][0]) / 2, (w[1][1] + w[2][1]) / 2))
                    report["entrances"] += 1
        # a long building gets more ways in: one per ENTRANCE_EVERY_M of street front, each through the street-side
        # room beside a corridor that is farthest from the entrances so far (its door to the corridor follows below)
        if air and ent_at:
            front = sum(math.dist(w[1], w[2]) for (x, L), ws in walls_at.items() if L == ground
                        for w in ws if None in w[0] and facing(x, w) == 0)
            want = min(ENTRANCES_MAX, max(1, round(front / ENTRANCE_EVERY_M)))
            lobby = []
            for e in on_level[ground]:
                if e["type"] != "room":
                    continue
                st = [w for w in walls_at.get((e["id"], ground), []) if None in w[0] and facing(e["id"], w) == 0
                      and math.dist(w[1], w[2]) >= ENTRANCE_W + 0.3]
                by_zone = any(partner(e["id"], w) and by_id[partner(e["id"], w)]["type"] == "zone"
                              for w in walls_at.get((e["id"], ground), []))
                if st and by_zone:
                    w = max(st, key=lambda w: math.dist(w[1], w[2]))
                    lobby.append((e["id"], w, ((w[1][0] + w[2][0]) / 2, (w[1][1] + w[2][1]) / 2)))
            while len(ent_at) < want and lobby:
                k = max(range(len(lobby)), key=lambda i: min(math.dist(lobby[i][2], p) for p in ent_at))
                x, w, p = lobby.pop(k)
                if min(math.dist(p, q) for q in ent_at) < ENTRANCE_EVERY_M / 2:
                    break
                # the entrance room opens onto its corridor first, so the way in leads somewhere
                zw = sorted((zw for zw in walls_at.get((x, ground), []) if partner(x, zw) and by_id[partner(x, zw)]["type"] == "zone"),
                            key=lambda zw: -math.dist(zw[1], zw[2]))
                if not any(add_door(x, zw, DOUBLE_W, DOOR_H, "Door") for zw in zw):
                    continue
                if add_door(x, w, ENTRANCE_W, ENTRANCE_H, "Entrance"):
                    entrances.add((x, ground))
                    ent_at.append(p)
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
                if drop(x, L):
                    continue
                opts = [w for w in walls_at.get(k, []) if None not in w[0] and (partner(x, w), L) in seen
                        and not drop(partner(x, w), L)]
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
    for _ in range(OUTSIDE_DOORS_MAX):
        # (a stair core standing on its own, outside the rest of the building, gets its own street door too)
        cut = [x for x, L in nodes if L == ground and (x, L) not in seen
               and (by_id[x]["type"] != "core" or all(partner(x, w) is None for w in walls_at.get((x, L), [])))
               and any(None in w[0] for w in walls_at.get((x, L), []))]
        if not cut:
            break
        x = max(cut, key=lambda i: polys[i].area)
        ext = outside_walls(x) or sorted((w for w in walls_at[(x, ground)] if None in w[0]), key=lambda w: -math.dist(w[1], w[2]))
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
        if by_id[x]["type"] == "room" and k not in doored and not drop(x, L):
            for w in sorted((w for w in walls_at.get(k, []) if None not in w[0] and not drop(partner(x, w), L)), key=lambda w: rank(x, w)):
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

        def rect(x0, x1, y0, y1, fu=False, fv=False, lenL=lenL, lenD=lenD, c=c, u=u, v=v):
            # fu / fv mirror the rectangle to the other end / side of the core
            if fu:
                x0, x1 = lenL - x1, lenL - x0
            if fv:
                y0, y1 = lenD - y1, lenD - y0
            return [_pt(c[0] + u * x0 + v * y0), _pt(c[0] + u * x1 + v * y0),
                    _pt(c[0] + u * x1 + v * y1), _pt(c[0] + u * x0 + v * y1)]

        stair_len = 0.0
        flip = (False, False)
        stair_polys = []
        core_doors = [d for d in out if d["type"] in ("door", "opening") and e["id"] in d.get("between", [])]
        for a_, b_ in zip(cl, cl[1:]):
            h = lv_by[b_]["z_m"] - lv_by[a_]["z_m"]
            if h <= 0:
                continue
            risers = math.ceil(h / RISER_MAX - 1e-9)
            # flights 3 ft 11 in (1.2 m) wide, or down to 3 ft 8 in (1.12 m, the narrowest a building code allows) in a tight core
            fw = FLIGHT_W if lenD >= 2 * FLIGHT_W + 0.1 else max(FLIGHT_W_MIN, (lenD - 0.1) / 2)
            width = 2 * fw + 0.1
            # more half-turns per floor make a shorter stair, keeping at least 3 risers in every flight
            # and enough half-turns that no flight climbs more than 12 ft (3.66 m) between landings
            t0 = max(1, math.ceil(h / (2 * FLIGHT_RISE_MAX) - 1e-9))
            for turns in range(t0, max(t0, min(MAX_TURNS, risers // (2 * MIN_FLIGHT_RISERS))) + 1):
                per = math.ceil(risers / (2 * turns))
                length = (per - 1) * TREAD + 2 * LANDING
                fits = length <= lenL + 1e-6 and width <= lenD + 1e-6
                if fits or width > lenD + 1e-6:
                    break
            stair_len = max(stair_len, min(length, lenL))
            # put the stair where no door of this core opens onto it: try the kept corner first, then the others
            dl = [LineString(d["line_m"]) for d in core_doors if d["level"] in (a_, b_)]
            best = None
            for f in [flip] + [q for q in ((False, False), (False, True), (True, False), (True, True)) if q != flip]:
                oo = rect(0, min(length, lenL), 0, min(width, lenD), *f)
                gap = min((Polygon(oo).distance(q) for q in dl), default=99.0)
                if best is None or gap > best[2]:
                    best = (f, oo, gap)
                if gap >= 1.0:
                    break
            flip, o = best[0], best[1]
            stair_polys.append(Polygon(o))
            out.append({"id": nid("S"), "type": "stair", "name": "Stairs", "level": a_, "to_level": b_, "outline_m": o,
                        "risers": risers, "riser_m": _r(h / risers), "tread_m": TREAD, "flights": 2 * turns, "turns": turns,
                        "flight_width_m": _r(fw), "landing_m": LANDING, "fits": fits, "core": e["id"],
                        "status": "proposed", "derived": True})
            holes.setdefault(b_, []).append(Polygon(o))
            if not fits:
                report["stairs_not_fitting"].append("%s %s, %s to %s: needs %.1f × %.1f m, the core is %.1f × %.1f m" % (
                    e["id"], e.get("name", ""), a_, b_, length, width, lenL, lenD))
        if len(cl) > 1 and lenL - stair_len >= LIFT + 0.2 and lenD >= LIFT:
            o = None
            dl_all = [LineString(d["line_m"]) for d in core_doors]
            for fu in (not flip[0], flip[0]):
                for fv in (flip[1], not flip[1]):
                    q = rect(lenL - LIFT, lenL, 0, LIFT, fu, fv)
                    qp = Polygon(q)
                    if not any(qp.intersects(sp) for sp in stair_polys) and all(qp.distance(x) >= 0.8 for x in dl_all):
                        o = q
                        break
                if o:
                    break
            if o:
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
