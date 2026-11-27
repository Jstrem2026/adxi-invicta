"""Make a room plan buildable: every piece of floor belongs to one space, and no space leaves the building.

Plan step 4 (Jordan, 27 Nov 2026: "go"). The room designers (tools/design_rooms.py, tools/build_designs.py)
lay rooms out with simple offsets, which leave rooms overlapping where wings meet, rooms poking into a
courtyard or past a curved wall, and now and then an outline that crosses itself. This pass fixes the
geometry with exact maths (Shapely) and keeps everything that was designed: every room keeps its id,
name, floors and "about"; only its outline is trimmed.

Rules, in order:
  1. A crossed outline is untangled (make_valid).
  2. Every indoor space is trimmed to the building's outline, minus its courtyards.
  3. Where two spaces on the same floor overlap, the floor goes to one of them:
     stair cores first, then corridors and other zones, then rooms, smaller rooms before bigger ones
     (a small office keeps its corner; the big hall next to it gives up a strip).
  4. A space cut in two keeps its id on the biggest piece; each other usable piece becomes a new space
     with the same name and "about". Slivers narrower than 5 ft (1.5 m) are dropped.
  5. A space with a hole (a stair core standing inside a hall) is cut across the hole, because plan
     outlines are single rings.
Outdoor zones, fixtures and doors are left as they are.

Plan frame: metres from the lot's bow-port corner, x toward the stern, y toward starboard.
"""

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import split as _split
from shapely.strtree import STRtree

from . import geometry as G

SPACES = ("room", "zone", "core")
MIN_WIDTH_M = 1.5      # 5 ft: a piece narrower than this is a sliver, not a room
MIN_PIECE_M2 = 4.0     # 43 sq ft: smaller loose pieces are dropped
GRID_M = 0.01          # outlines are stored to the centimetre


def _levels(e):
    return e.get("levels") or ([e["level"]] if e.get("level") else [])


def _width(g):
    env = shapely.oriented_envelope(g)
    if env.geom_type != "Polygon":
        return 0.0
    c = np.asarray(env.exterior.coords)
    return float(min(np.hypot(*(c[1] - c[0])), np.hypot(*(c[2] - c[1]))))


def _polys(g):
    """The polygon parts of any geometry."""
    return [p for p in shapely.get_parts(g) if p.geom_type == "Polygon" and not p.is_empty]


def _no_holes(p):
    """A polygon with holes -> polygons without, cut across each hole."""
    todo, out = [p], []
    while todo:
        q = todo.pop()
        if not q.interiors:
            out.append(q)
            continue
        h = Polygon(q.interiors[0])
        cx, cy = h.centroid.x, h.centroid.y
        x0, y0, x1, y1 = q.bounds
        w, d = x1 - x0, y1 - y0
        # cut across the short way, through the hole
        line = LineString([(cx, y0 - 1), (cx, y1 + 1)]) if w >= d else LineString([(x0 - 1, cy), (x1 + 1, cy)])
        parts = _polys(_split(q, line))
        if len(parts) < 2:   # should not happen; keep the outer ring rather than loop
            out.append(Polygon(q.exterior))
            continue
        todo.extend(parts)
    return out


def building_frame_shape(b):
    """The building's outline minus its courtyards, in the plan frame (metres)."""
    if not b or not b.get("rect_km"):
        return None
    x0, y0 = b["rect_km"][0], b["rect_km"][2]
    return shapely.transform(G.building_shape(b), lambda c: (c - [x0, y0]) * 1000.0)


def _ring(p):
    p = shapely.geometry.polygon.orient(p, 1.0)
    pts = [[round(x, 2) + 0.0, round(y, 2) + 0.0] for x, y in p.exterior.coords[:-1]]
    out = []
    for q in pts:
        if not out or q != out[-1]:
            out.append(q)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def repair(m, b=None):
    """Fix the plan m in place. Returns a report dict (counts and the names of anything dropped)."""
    rep = {"untangled": 0, "trimmed": 0, "split": 0, "added": 0, "merged": 0, "dropped": []}
    els = m.get("elements", [])
    foot = building_frame_shape(b)
    if foot is not None:
        foot = shapely.set_precision(foot, GRID_M)
        shapely.prepare(foot)
    idx = [i for i, e in enumerate(els)
           if e.get("type") in SPACES and not e.get("outdoor") and len(e.get("outline_m") or []) >= 3]
    if not idx:
        return rep
    geo = {}
    for i in idx:
        o = els[i]["outline_m"]
        g = Polygon([q[:2] for q in o])
        if not g.is_valid:
            g = shapely.make_valid(g)
            rep["untangled"] += 1
        geo[i] = g
    orig_area = {i: geo[i].area for i in idx}

    def rank(i):
        e = els[i]
        t = 0 if e["type"] == "core" else (1 if e["type"] == "zone" else 2)
        return (t, round(orig_area[i], 1), i)

    order = sorted(idx, key=rank)
    tree_geoms = [geo[i] for i in order]
    tree = STRtree(tree_geoms)
    lv = {i: set(_levels(els[i])) for i in idx}
    placed = {}
    pos = {i: k for k, i in enumerate(order)}
    for k, i in enumerate(order):
        g = geo[i]
        if foot is not None and not foot.covers(g):
            g = g.intersection(foot)
        cut = []
        for j in tree.query(tree_geoms[k]):
            oi = order[j]
            if pos[oi] < k and oi in placed and lv[i] & lv[oi]:
                pj = placed[oi]
                if pj.intersects(g) and g.intersection(pj).area > 1e-6:
                    cut.append(pj)
        if cut:
            g = g.difference(shapely.union_all(cut))
        g = shapely.set_precision(g, GRID_M)
        parts = [q for p in _polys(g) for q in _no_holes(p)]
        parts = [p for p in parts if p.area >= 0.5]
        parts.sort(key=lambda p: -p.area)
        good = [p for p in parts if p.area >= MIN_PIECE_M2 and _width(p) >= MIN_WIDTH_M]
        if not good and parts:
            good = parts[:1]   # keep the room even if it is now small; the scan will say so
        if not good:
            placed[i] = shapely.Polygon()
            continue
        placed[i] = shapely.union_all(good)
        if abs(sum(p.area for p in good) - orig_area[i]) > 0.05:
            rep["trimmed"] += 1
        geo[i] = good
    _merge_slivers(els, idx, geo, lv, rep)
    # write back, keeping each element's place in the list; new pieces go at the end with new ids
    used = {e.get("id") for e in els}
    n = len(els)
    nxt = [n]

    def new_id():
        while True:
            nxt[0] += 1
            cand = "E%03d" % nxt[0]
            if cand not in used:
                used.add(cand)
                return cand
    extra, drop = [], set()
    for i in idx:
        g = geo[i]
        if g == "merged":
            drop.add(i)
            continue
        if not isinstance(g, list):   # untouched (never placed means it vanished)
            if i in placed and placed[i].is_empty:
                drop.add(i)
                rep["dropped"].append("%s %s" % (els[i].get("id"), els[i].get("name")))
            continue
        els[i]["outline_m"] = _ring(g[0])
        if len(g) > 1:
            rep["split"] += 1
        for p in g[1:]:
            e2 = dict(els[i])
            e2["id"] = new_id()
            e2["outline_m"] = _ring(p)
            e2["piece_of"] = els[i]["id"]
            extra.append(e2)
            rep["added"] += 1
    if drop:
        m["elements"] = [e for k, e in enumerate(els) if k not in drop] + extra
    else:
        els.extend(extra)
    return rep


STAIR_W = 2.5   # m: two flights side by side; a core narrower than this can't hold a stair


def _merge_slivers(els, idx, geo, lv, rep):
    """A room or corridor trimmed to a sliver (narrower than 5 ft) joins the neighbour on the same floors that
    shares the longest wall with it, so no floor is left as a strip nobody can stand in. A stair core trimmed too
    thin for a stair is removed when another core already serves all its floors."""
    live = [i for i in idx if isinstance(geo[i], list)]
    cores = [i for i in live if els[i]["type"] == "core"]
    for i in cores:
        if _width(geo[i][0]) < STAIR_W:
            others = set().union(*[lv[j] for j in cores if j != i and geo[j] != "merged"]) if len(cores) > 1 else set()
            if lv[i] <= others:
                geo[i] = "merged"
                rep["dropped"].append("%s %s (too thin for a stair; other cores serve its floors)" % (els[i]["id"], els[i]["name"]))
    thin = sorted((i for i in live if els[i]["type"] in ("room", "zone") and geo[i] != "merged" and _width(geo[i][0]) < MIN_WIDTH_M),
                  key=lambda i: geo[i][0].area)
    if not thin:
        return
    cand = [i for i in live if els[i]["type"] in ("room", "zone")]
    tree = STRtree([geo[i][0] for i in cand])
    for i in thin:
        if geo[i] == "merged":
            continue
        g = geo[i][0]
        nbs = []
        for k in tree.query(g.buffer(0.05)):
            j = cand[k]
            if j == i or geo[j] == "merged" or lv[j] != lv[i]:
                continue
            shared = g.boundary.intersection(geo[j][0].buffer(0.02)).length
            if shared > 0.05:
                nbs.append((-shared, j))
        joined = False
        for _, best in sorted(nbs):   # the longest shared wall first; the next one if that join won't make one room
            u = shapely.union(geo[best][0], g, grid_size=GRID_M)
            parts = sorted(_polys(u), key=lambda p: -p.area)
            if not parts or sum(p.area for p in parts[1:]) > 1.0:
                continue
            p0 = parts[0]
            if p0.interiors:   # a pinhole where the two met is filled; a real hole (something inside) is not
                if sum(Polygon(r).area for r in p0.interiors) > 1.0:
                    continue
                p0 = Polygon(p0.exterior)
            geo[best][0] = p0
            joined = True
            break
        if not joined:
            continue
        if len(geo[i]) > 1:   # other usable pieces stay as the room
            geo[i] = geo[i][1:]
        else:
            geo[i] = "merged"
            rep["merged"] += 1
