"""Lay out the precinct plans of the Deck 5 districts that had none (proposed, 27 Nov 2026).

    python tools/seed_deck5_districts.py          writes data/decks/D5/<district>.json and Game/Docs/<District>_Precincts.md
                                                  (plus the Docs/2_Design_Docs mirror) for the five districts below

Follows the Port of Arrivals pattern: precincts on frame and lane lines, named streets, every building
named (generic names where nothing better exists), US units first with metric in brackets.

How a precinct is laid out (shapes: Jordan, 27 Nov 2026):
  * Its outline is a rectangle (or quarter circle for the Atrium Plaza) on frame and lane lines,
    clipped to the Rev B deck outline. Canon circles (the Atrium Plaza, the Spine Atrium shaft) are cut out.
  * Streets are straight strips. The land between them is the precinct's blocks.
  * Each building is written here with its own name, footprint and purpose. Canon items
    (stations, launch shafts, cruiser gates) are placed at their canon frames; the rest are spread
    over the app's city blocks in list order, centred in their block, 30 m clear of every street and
    20 m clear of each other, so no building ever crosses a street, a block edge or the hull.
    Listed sizes are drawn at the district's scale (below) unless a block is too small for that.
  * A block still empty after that gets a filler suited to the precinct (open bay, quay yard,
    apartment block, garden ...), numbered: Open Bay 1, Open Bay 2 ...
  * Then buildings follow their blocks (follow_blocks): each block's land, 30 m in from its streets,
    the hull and the plaza circles, is shared between its buildings by listed size (lots cut again and
    again across their longer side, so they stay close to square), and each building takes a shape on
    its lot (atlaslib/footprints.py): courtyard, L, U, curved front, rounded, oval, or the whole lot.
    A lot is at most 2.5 times the building's listed footprint; the rest of the block gets a filler
    (or stays open ground in an approved plan). Every building also gets its map colour category.
Everything is "proposed" unless the item itself is canon. Re-running rewrites the five files.
"""
import json
import math
import os
import re
import shutil
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(APP)
sys.path.insert(0, APP)
from atlaslib import geometry as G  # noqa: E402
from atlaslib.loader import Loader, make_blocks, slug  # noqa: E402
from atlaslib import footprints as FP  # noqa: E402
from atlaslib.categories import categorize
from atlaslib import purposes as PU  # noqa: E402

TODAY = "2026-11-27"
FT = 3.28084
PLAZA = (26.0, 0.0, 1.7853)       # Atrium Plaza circle (canon, Sheet S5)
SHAFT = (26.0, 0.0, 0.8)          # Spine Atrium shaft, 1.6 km across (canon, Sheet S5 key data)
GAP = 0.02                        # 20 m between buildings
SET = 0.03                        # 30 m from streets and block edges
STEP = 0.01                       # placement grid, 10 m

# ---------------------------------------------------------------------------------- units

def ftn(m):
    return f"{m * FT:,.0f}"


def size_text(L, W):
    return f"{ftn(L)} × {ftn(W)} ft ({L:,.0f} × {W:,.0f} m)"


def km_text(L, W):
    return f"{ftn(L * 1000)} × {ftn(W * 1000)} ft ({L:.2f} × {W:.2f} km)"


def area_text(a):
    return f"{a / 2.589988:.2f} sq mi ({a:.2f} km²)"


# ---------------------------------------------------------------------------------- geometry

def hull():
    m = Loader(ROOT).model()
    d5 = next(d for d in m["decks"] if d["n"] == 5)
    return [tuple(p) for p in d5["outline_net"]], d5


OUTLINE, DECK5 = hull()


def hw(x):
    return G.half_width_at(OUTLINE, x)


def quarter_disc(cx, cy, r, sx, sy, n=24):
    pts = [(cx, cy)]
    for i in range(n + 1):
        a = i / n * math.pi / 2
        pts.append((cx + sx * r * math.cos(a), cy + sy * r * math.sin(a)))
    return pts


def rect_ok(r, shape, circles):
    x0, x1, y0, y1 = r
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1), (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)]
    if not all(G.point_in_poly(x, y, shape) for x, y in pts):
        return False
    for cx, cy, cr in circles:
        nx, ny = min(max(cx, x0), x1), min(max(cy, y0), y1)
        if (nx - cx) ** 2 + (ny - cy) ** 2 < (cr + GAP) ** 2:
            return False
    return True


def overlaps(a, b, gap):
    return a[0] < b[1] + gap and b[0] < a[1] + gap and a[2] < b[3] + gap and b[2] < a[3] + gap


def inset_shape(shape, d):
    """Shrink a convex polygon by d km (offset each edge inward and intersect)."""
    pts = shape if _ccw(shape) else list(reversed(shape))
    n = len(pts)
    lines = []
    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-9:
            continue
        nx, ny = -(by - ay) / L, (bx - ax) / L   # inward normal for a ccw polygon
        lines.append(((ax + nx * d, ay + ny * d), (bx - ax, by - ay)))
    out = []
    for i in range(len(lines)):
        (p, r), (q, s) = lines[i - 1], lines[i]
        den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-12:
            out.append((q[0], q[1]))
            continue
        t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
        out.append((p[0] + t * r[0], p[1] + t * r[1]))
    return out


def _ccw(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) > 0


# ---------------------------------------------------------------------------------- layout

def lay_out(dist, P):
    """Turn one precinct spec into app data (streets, buildings with rects)."""
    poly = P.get("poly") or G.rect_poly(P["bounds"])
    shape = G.clip(OUTLINE, poly)
    excl = list(P.get("excl", []))
    area = G.polygon_area(shape) - sum(G.circle_overlap_area(shape, c[0], c[1], c[2], 0.005) for c in excl)
    bx = G.bbox(shape)
    inner = inset_shape(shape, 0.004)
    # streets: (name, axis, at, width_m[, lo, hi]); axis "y" runs bow-stern at y=at, "x" runs across at x=at
    streets = []
    for st in P.get("streets", []):
        name, ax, at, w = st[:4]
        h = w / 2000.0
        if ax == "y":
            lo, hi = (st[4], st[5]) if len(st) > 4 else (bx[0], bx[1])
            xs = [x / 1000.0 for x in range(int(lo * 1000), int(hi * 1000) + 1, 5)]
            inside = [x for x in xs if G.point_in_poly(x, at - h + 0.001, shape) and G.point_in_poly(x, at + h - 0.001, shape)
                      and not any((x - c[0]) ** 2 + (at - c[1]) ** 2 < (c[2] + 0.005) ** 2 for c in excl)]
            if not inside:
                raise SystemExit("street %s misses precinct %s" % (name, P["id"]))
            # longest unbroken run
            runs, cur = [], [inside[0]]
            for x in inside[1:]:
                if x - cur[-1] > 0.0051:
                    runs.append(cur)
                    cur = [x]
                else:
                    cur.append(x)
            runs.append(cur)
            for run in runs:
                if run[-1] - run[0] > 0.1:
                    streets.append({"name": name, "width_m": w, "rect_km": [round(run[0], 4), round(run[-1], 4), round(at - h, 4), round(at + h, 4)]})
        else:
            lo, hi = (st[4], st[5]) if len(st) > 4 else (bx[2], bx[3])
            ys = [y / 1000.0 for y in range(int(math.floor(lo * 1000)), int(math.ceil(hi * 1000)) + 1, 5)]
            inside = [y for y in ys if G.point_in_poly(at - h + 0.001, y, shape) and G.point_in_poly(at + h - 0.001, y, shape)
                      and not any((at - c[0]) ** 2 + (y - c[1]) ** 2 < (c[2] + 0.005) ** 2 for c in excl)]
            if not inside:
                raise SystemExit("street %s misses precinct %s" % (name, P["id"]))
            streets.append({"name": name, "width_m": w, "rect_km": [round(at - h, 4), round(at + h, 4), round(min(inside), 4), round(max(inside), 4)]})
    srects = [s["rect_km"] for s in streets]
    placed = []          # rects already used (buildings and bays)
    items = P["items"]
    scale = P.get("scale", dist.get("scale", 1.0))
    for k, it in enumerate(items):
        it["_n"] = k + 1
        it["_fixed"] = bool(it.get("rect") or it.get("bays"))
        if it.get("rect") or it.get("bays"):
            shapes = it.get("bays") or [it["rect"]]
            for s in shapes:
                if not rect_ok(s, inner, excl):
                    raise SystemExit("fixed item %s %s is not inside its precinct" % (P["id"], it["name"]))
                if any(G.rect_overlap(s, q) > 1e-7 for q in srects):
                    raise SystemExit("fixed item %s %s sits on a street" % (P["id"], it["name"]))
            placed.extend(shapes)
    # the app's city blocks, from the streets and the canon items only
    blocks = app_blocks(shape, bx, items, excl, streets)
    free = [it for it in items if not (it.get("rect") or it.get("bays"))]
    n = len(free)
    for i, it in enumerate(free):
        target = it.get("cell", (i * len(blocks)) // max(n, 1))
        order = sorted(range(len(blocks)), key=lambda k: (abs(k - target) if "cell" not in it else (0 if k == target else 1 + abs(k - target))))
        spot = None
        for sc in (scale, (scale + 1) / 2, 1.0, 0.85):
            L, W = round(it["L"] * sc / 10) * 0.01, round(it["W"] * sc / 10) * 0.01
            for ci in order:
                c = blocks[ci]["cell_km"]
                for (l, w) in ((L, W), (W, L)):
                    spot = fit(c, l, w, inner, excl, placed, srects, centre=True)
                    if spot:
                        break
                if spot:
                    break
            if spot:
                break
        if not spot:
            raise SystemExit("no room for %s %s (%g × %g m)" % (P["id"], it["name"], it["L"], it["W"]))
        it["rect"] = spot
        placed.append(spot)
    # every block that is still empty gets a filler that suits the precinct (open bays, yards, homes ...)
    fills = P.get("fill") or []
    counters = {}
    for _round in range(3):
        blocks = app_blocks(shape, bx, items, excl, streets)
        # empty blocks, and (once) blocks less than an eighth built on, get a filler in their free space
        empty = [b for b in blocks if not b["contents"] or (_round == 0 and used_share(b, placed) < 0.125)]
        if not empty or not fills:
            break
        for k, blk in enumerate(empty):
            c = blk["cell_km"]
            base, notes, kind = fills[(len(counters.get("_all", [])) ) % len(fills)][:3]
            counters.setdefault("_all", []).append(1)
            w0, h0 = c[1] - c[0] - 2 * SET, c[3] - c[2] - 2 * SET
            spot = None
            for f in (0.8, 0.7, 0.6, 0.5, 0.4, 0.3):
                l, w = math.floor(w0 * f * 100) / 100, math.floor(h0 * f * 100) / 100
                if l < 0.06 or w < 0.04:
                    continue
                spot = fit(c, l, w, inner, excl, placed, srects, centre=True)
                if spot:
                    break
            if not spot:
                counters["_all"].pop()
                continue
            counters[base] = counters.get(base, 0) + 1
            it = {"name": "%s %d" % (base, counters[base]), "notes": notes, "kind": kind, "rect": spot, "_n": len(items) + 1, "filler": True}
            items.append(it)
            placed.append(spot)
    follow_blocks(P, shape, bx, items, excl, streets, fills, counters)
    out = []
    for it in items:
        b = {"id": "%s-%02d" % (P["id"], it["_n"]), "name": it["name"]}
        if it.get("bays"):
            bl, bw = it["bay_m"]
            b["size_text"] = it.get("size_text") or "%d %s, each %s" % (len(it["bays"]), it.get("bay_word", "bays"), size_text(bl, bw))
            b["size_m"] = [bl, bw]
            b["bays_km"] = [[round(v, 4) for v in s] for s in it["bays"]]
            b["bay_count"] = len(it["bays"])
            if it.get("bay_names"):
                b["bay_names"] = it["bay_names"]
            xs = [s[0] for s in it["bays"]] + [s[1] for s in it["bays"]]
            ys = [s[2] for s in it["bays"]] + [s[3] for s in it["bays"]]
            b["rect_km"] = [round(min(xs), 4), round(max(xs), 4), round(min(ys), 4), round(max(ys), 4)]
        else:
            r = it["rect"]
            Lm, Wm = round((r[1] - r[0]) * 1000), round((r[3] - r[2]) * 1000)
            b["size_text"] = size_text(Lm, Wm)
            b["size_m"] = [Lm, Wm]
            b["rect_km"] = [round(v, 4) for v in r]
            if it.get("outline"):
                b["outline_km"] = it["outline"]
                if it.get("holes"):
                    b["holes_km"] = it["holes"]
                b["shape"] = it["shape"]
        b["notes"] = it.get("notes", "")
        b["status"] = "canon" if dist.get("approved") else it.get("status", "proposed")
        b["kind"] = it.get("kind", "building")
        b["category"] = categorize(b)
        out.append(b)
    return shape, area, streets, out


CAP = 2.5   # a building's lot is at most this many times its listed footprint; the rest of the block gets a filler


def _cut_area(poly, ax, lo, hi):
    b = G.bbox(poly)
    r = [lo, hi, b[2] - 1, b[3] + 1] if ax == "x" else [b[0] - 1, b[1] + 1, lo, hi]
    q = G.clip(poly, G.rect_poly(r))
    return (G.polygon_area(q) if len(q) >= 3 else 0.0), q


def follow_blocks(P, shape, bx, items, excl, streets, fills, counters):
    """Buildings follow their blocks (Jordan, 27 Nov 2026). Each block's buildable land (the block 30 m in
    from its streets, the hull and the plaza circles, so it keeps their curves) is shared out between its
    buildings in strips along the block, in proportion to each building's listed footprint, 20 m apart.
    Each building then takes a shape that fits its strip and its use: courtyard, L, U, curved front,
    rounded or oval, or the whole strip for halls, yards and parks. Canon items drawn at fixed frames
    (stations, pod stops) keep their box and the strip across the block beside them stays open as their
    forecourt. Blocks holding a bay row (launch shafts, berths) keep every box, shaped inside the box."""
    blocks = app_blocks(shape, bx, items, excl, streets)
    k = [0]
    stats = {"strips": 0, "kept": 0}
    for blk in blocks:
        c = blk["cell_km"]
        inside = lambda r: c[0] - 1e-6 <= r[0] and r[1] <= c[1] + 1e-6 and c[2] - 1e-6 <= r[2] and r[3] <= c[3] + 1e-6
        here = [it for it in items if it.get("rect") and not it.get("bays") and inside(it["rect"])]
        fixed = [it for it in here if it.get("_fixed") or it.get("kind") == "transport"]
        members = [it for it in here if it not in fixed]
        if not members:
            continue
        has_bays = any(it.get("bays") and any(G.rect_overlap(q, c) > 1e-7 for q in it["bays"]) for it in items)
        part = _without_streets(blk["part_km"], c, streets)
        lots = None
        if part and not has_bays:
            lots = _block_lots(part, members, fixed, [] if dist_approved(P) else fills, counters, items)
        stats["strips" if lots is not None else "kept"] += 1
        if lots is None:  # keep each box, shaped inside it
            for it in members:
                _shape(it, G.rect_poly(it["rect"]), k[0])
                k[0] += 1
            continue
        for it, lot in lots:
            _shape(it, lot, k[0])
            k[0] += 1
    print("   %s: %d blocks follow their shape, %d keep boxes" % (P["id"], stats["strips"], stats["kept"]))


def dist_approved(P):
    return any(P is q for q in PLAZA_D["precincts"]) and PLAZA_D.get("approved")


def _without_streets(part, c, streets):
    """The block outline with any street along its edge cut off (the app does not cut a block along a
    street when the cut would split a building, so a street can run along a block's edge inside it).
    None when a street runs through the middle of the block."""
    for st in streets:
        r = st["rect_km"]
        if G.rect_overlap(r, [c[0] + 0.001, c[1] - 0.001, c[2] + 0.001, c[3] - 0.001]) <= 1e-7:
            continue
        if r[1] - r[0] >= r[3] - r[2]:   # runs bow to stern
            sides = [[c[0] - 1, c[1] + 1, c[2] - 1, r[2]], [c[0] - 1, c[1] + 1, r[3], c[3] + 1]]
        else:
            sides = [[c[0] - 1, r[0], c[2] - 1, c[3] + 1], [r[1], c[1] + 1, c[2] - 1, c[3] + 1]]
        pieces = [G.clip(part, G.rect_poly(sd)) for sd in sides]
        pieces = [q for q in pieces if len(q) >= 3 and G.polygon_area(q) > 0.002]
        if len(pieces) != 1:
            return None   # the street splits the block in two: leave it as it is
        part = pieces[0]
    return part


def _block_lots(part, members, fixed, fills, counters, items):
    build = FP.offset(part, SET)
    if not build or G.polygon_area(build) < 0.004:
        return None
    bb = G.bbox(build)
    ax = "x" if bb[1] - bb[0] >= bb[3] - bb[2] else "y"
    i0, i1 = (0, 1) if ax == "x" else (2, 3)
    lo, hi = bb[i0], bb[i1]
    # fixed items reserve the strip across the block beside them (their forecourt)
    res = sorted([max(lo, f["rect"][i0] - GAP), min(hi, f["rect"][i1] + GAP)] for f in fixed)
    merged = []
    for a, b in res:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    segs, cur = [], lo
    for a, b in merged:
        if a - cur > 0.06:
            segs.append([cur, a])
        cur = max(cur, b)
    if hi - cur > 0.06:
        segs.append([cur, hi])
    if not segs:
        return None
    for it in members:
        r = it["rect"]
        it["_target"] = (r[1] - r[0]) * (r[3] - r[2])
    groups = [[] for _ in segs]
    for it in members:
        m = (it["rect"][i0] + it["rect"][i1]) / 2
        j = min(range(len(segs)), key=lambda j: 0 if segs[j][0] <= m <= segs[j][1] else min(abs(m - segs[j][0]), abs(m - segs[j][1])))
        groups[j].append(it)
    lots = []
    new = []
    for (a, b), grp in zip(segs, groups):
        if not grp:
            continue
        sub = _strip_lots(build, grp, ax, a, b, fills, counters, items, new)
        if sub is None:
            return None
        lots += sub
    for it in new:
        it["_n"] = len(items) + 1
        items.append(it)
    return lots


def _strip_lots(build, members, ax, lo, hi, fills, counters, items, new):
    A = _cut_area(build, ax, lo, hi)[0]
    T = sum(it["_target"] for it in members)
    i0, i1 = (0, 1) if ax == "x" else (2, 3)
    order = sorted(members, key=lambda it: (it["rect"][i0] + it["rect"][i1]) / 2)
    weights = [it["_target"] for it in order]
    if A > CAP * T:
        if fills:   # the rest of the block gets a filler that suits the precinct
            base, notes, kind = fills[len(counters.get("_all", [])) % len(fills)][:3]
            counters.setdefault("_all", []).append(1)
            counters[base] = counters.get(base, 0) + 1
            filler = {"name": "%s %d" % (base, counters[base]), "notes": notes, "kind": kind, "filler": True,
                      "rect": None, "_target": A - CAP * T}
            new.append(filler)
        else:       # an approved plan gets no new items: the rest of the block stays open ground
            filler = {"_open": True, "_target": A - CAP * T, "rect": [0, 0, 0, 0]}
        order.append(filler)
        weights.append(A - CAP * T)
    region = _cut_area(build, ax, lo, hi)[1]
    out = _split(region, list(zip(order, weights)))
    if out is None:
        return None
    return [(it, q) for it, q in out if not it.get("_open")]


def _shape(it, lot, k):
    tmp = {"name": it["name"], "kind": it.get("kind", "building")}
    tmp["category"] = categorize(tmp)
    style = FP.choose(tmp, lot, k)
    depth = None
    if style == "courtyard" and it.get("_target"):
        per = sum(math.hypot(lot[i][0] - lot[i - 1][0], lot[i][1] - lot[i - 1][1]) for i in range(len(lot)))
        depth = max(0.03, min(0.09, 1.3 * it["_target"] / max(per, 1e-6)))
    FP.apply(tmp, lot, k, style, depth)
    it["outline"], it["holes"], it["shape"] = tmp["outline_km"], tmp.get("holes_km"), tmp["shape"]
    it["rect"] = tmp["rect_km"]


def _split(region, pairs):
    """Share a region between items by area, cutting it in two again and again across its longer side,
    so every lot comes out close to square (a treemap). Lots are 20 m apart. None if a lot gets too thin."""
    region = FP.simplify(region, 1e-5) if len(region) >= 3 else region
    if len(region) < 3 or G.polygon_area(region) < 0.002 or FP.self_intersects(region):
        return None
    rb = G.bbox(region)
    if min(rb[1] - rb[0], rb[3] - rb[2]) < 0.04:
        return None
    if len(pairs) == 1:
        return [(pairs[0][0], region)]
    ax = "x" if rb[1] - rb[0] >= rb[3] - rb[2] else "y"
    i0, i1 = (0, 1) if ax == "x" else (2, 3)
    lo, hi = rb[i0], rb[i1]
    key = lambda pr: ((pr[0]["rect"][i0] + pr[0]["rect"][i1]) / 2) if pr[0].get("rect") and not pr[0].get("_open") and pr[0]["rect"][1] > pr[0]["rect"][0] else 1e9
    pairs = sorted(pairs, key=key)
    tot = sum(w for _, w in pairs)
    acc, k = 0.0, 1
    best = None
    for j in range(1, len(pairs)):
        acc += pairs[j - 1][1]
        if best is None or abs(acc - tot / 2) < best[0]:
            best = (abs(acc - tot / 2), j, acc)
    _, k, left_w = best
    A = G.polygon_area(region)
    goal = A * left_w / tot
    a, b = lo, hi
    for _ in range(40):
        m = (a + b) / 2
        if _cut_area(region, ax, lo, m)[0] < goal:
            a = m
        else:
            b = m
    cut = (a + b) / 2
    left = _cut_area(region, ax, lo - 1, cut - GAP / 2)[1]
    right = _cut_area(region, ax, cut + GAP / 2, hi + 1)[1]
    L = _split(left, pairs[:k])
    R = _split(right, pairs[k:])
    if L is None or R is None:
        return None
    return L + R


def fit(c, L, W, inner, excl, placed, srects, centre=False):
    x0, x1, y0, y1 = c[0] + SET, c[1] - SET, c[2] + SET, c[3] - SET
    if x1 - x0 < L - 1e-9 or y1 - y0 < W - 1e-9:
        return None
    nx = int((x1 - x0 - L) / STEP + 1e-6) + 1
    ny = int((y1 - y0 - W) / STEP + 1e-6) + 1
    near = [q for q in placed if overlaps(q, c, 0.05)]
    roads = [q for q in srects if overlaps(q, c, SET)]
    cands = [(i, j) for j in range(ny) for i in range(nx)]
    if centre:
        mx, my = (c[0] + c[1]) / 2, (c[2] + c[3]) / 2
        cands.sort(key=lambda ij: (x0 + ij[0] * STEP + L / 2 - mx) ** 2 + (y0 + ij[1] * STEP + W / 2 - my) ** 2)
    for i, j in cands:
        x, y = x0 + i * STEP, y0 + j * STEP
        r = [round(x, 4), round(x + L, 4), round(y, 4), round(y + W, 4)]
        if any(overlaps(r, q, GAP) for q in near) or any(overlaps(r, q, SET - 0.001) for q in roads):
            continue
        if not rect_ok(r, inner, excl):
            continue
        return r
    return None


def used_share(blk, placed):
    c = blk["cell_km"]
    return sum(G.rect_overlap(c, q) for q in placed) / max(blk.get("area_km2") or 0, 1e-9)


def app_blocks(shape, bx, items, excl, streets):
    """The blocks the app will draw (same code), given what is placed so far."""
    blds = []
    for it in items:
        if it.get("bays"):
            xs = [q[0] for q in it["bays"]] + [q[1] for q in it["bays"]]
            ys = [q[2] for q in it["bays"]] + [q[3] for q in it["bays"]]
            blds.append({"id": it.get("name"), "name": it["name"], "kind": it.get("kind", "building"), "bays_km": it["bays"],
                         "rect_km": [min(xs), max(xs), min(ys), max(ys)]})
        elif it.get("rect"):
            blds.append({"id": it.get("name"), "name": it["name"], "kind": it.get("kind", "building"), "rect_km": it["rect"]})
    blocks = make_blocks(5, shape, bx, blds, excl, streets)
    for blk in blocks:
        for b in blds:
            for s in (b.get("bays_km") or [b["rect_km"]]):
                if G.rect_overlap(s, blk["cell_km"]) > 1e-7:
                    blk["contents"].append(b["name"])
                    break
    return blocks


# ---------------------------------------------------------------------------------- helpers for specs

def B(name, L, W, notes="", kind="building", **kw):
    d = {"name": name, "L": L, "W": W, "notes": notes, "kind": kind}
    d.update(kw)
    return d


def U(name, L, W, notes=""):
    return B(name, L, W, notes, "utility")


def lanes_for(y0, y1):
    a = G.LANES[max(0, min(24, int(math.floor((y0 + 0.25) / 0.5 + 1e-6)) + 12))]
    b = G.LANES[max(0, min(24, int(math.ceil((y1 + 0.25) / 0.5 - 1e-6)) + 12 - 1))]
    return a, b


def frames_for(x0, x1):
    return int(round(x0 / 0.5)), int(round(x1 / 0.5))


# ================================================================================== DISTRICTS
# Every list below is a proposal (27 Nov 2026). Sizes are length (along the ship, bow to stern)
# × width (across the beam), in metres. The placer may turn a building 90° to fit its block.

def shafts(side, first):
    """C4 (canon): 16 launch shafts a side, 60 × 40 m, F16–F28, lanes D–F (port) or T–V (starboard).
    Placed in four rows of four along the hull shoulder, mid-way between the Launch Road and the hull."""
    groups = []
    for g, x0 in enumerate((8.9, 10.3, 11.5, 12.9)):
        xm = x0 + 0.18
        lim = hw(xm)
        yc = (3.29 + lim) / 2
        bays = []
        for k in range(4):
            bx0 = x0 + k * 0.1
            y_lo, y_hi = yc - 0.02, yc + 0.02
            bays.append([bx0, bx0 + 0.06, -y_hi, -y_lo] if side < 0 else [bx0, bx0 + 0.06, y_lo, y_hi])
        n0 = first + g * 4
        groups.append({"name": "Launch Shafts %d–%d" % (n0, n0 + 3), "bays": bays, "bay_m": (60, 40), "bay_word": "shafts",
                       "bay_names": ["Shaft %d" % (n0 + k) for k in range(4)], "kind": "bays", "status": "canon",
                       "notes": "Canon (errata C4): 60 × 40 m shafts up to the %s Forward Grid. Placement along the shoulder proposed" % ("port" if side < 0 else "starboard")})
    return groups


def racks(first, wing, side):
    """Six squadron rack halls per wing, each sized for its craft (craft mix is an assumption)."""
    types = [("interceptors", 340, 180), ("interceptors", 340, 180), ("strike craft", 400, 200), ("strike craft", 400, 200),
             ("heavy strike craft", 480, 240), ("scouts and electronic-warfare craft", 320, 170)]
    out = []
    for k, (t, L, W) in enumerate(types):
        n = first + k
        out.append(B("Rack Hall %d" % n, L, W, "%s Wing, Squadron %d · 150 racks for %s, stacked in tiers to the roof" % (wing, k + 1, t)))
    return out


STRIKE = {
    "district": "Strike Hangars", "file": "strike-hangars", "doc": "Strike_Hangars_Precincts.md", "code": "D5F2",
    "title": "Strike Hangars",
    "lead": ("Strike Hangars is the bow district of Deck 5 (Aerion), from the prow tip to F34, the full width of the deck. "
             "Canon (Sheet S5, errata C2 and C4): 42.1 sq mi (109.1 km², Rev B), racks for 3,600 craft and 32 launch shafts "
             "up to the Forward Grids, 60,000 people (pilots, deck crews, mechanics, armorers, launch controllers), centre address "
             "D5-F19-M, Keelway stop Strike Hangars at F3. The launch shafts are 197 × 131 ft (60 × 40 m) each, at F16–F28 in "
             "lanes D–F (port) and T–V (starboard). The precincts fill the district on the Rev B outline, which measures "
             "42.23 sq mi (109.37 km²) forward of F34; errata C2's 109.1 km² is a rounded figure (flagged for Jordan)."),
    "rule": ("Layout rule: the bow end is the crews' way in (Keelway Gate), then the magazines (Ordnance Yards) kept away from "
             "everything else, then the four strike wings' rack halls either side of the Keelway with the launch shafts along "
             "both hull shoulders, and the repair yards and Wing Command at the stern end next to the Port of Arrivals and the "
             "Cruiser Docks. The craft mix in each rack hall (interceptors, strike, heavy strike, scouts) is an assumption: canon "
             "only gives the 3,600 total, here 4 wings × 6 squadrons × 150 racks."),
    "precincts": [],
}

STRIKE["precincts"] = [
    {"id": "P1", "name": "Keelway Gate", "bounds": [0.58, 4.0, -2.0, 2.0], "lanes": "K–O",
     "role": "Strike Hangars Keelway station (F3), crew check-in, lifts, clinic",
     "intro": "Where the 60,000 hangar crews arrive for their shifts. The Strike Hangars Keelway stop (canon, F3) sits beside the Keelway.",
     "streets": [("Keelway", "y", 0.0, 60), ("F4 Street", "x", 2.0, 30), ("F6 Street", "x", 3.0, 30)],
     "items": [
         B("Strike Hangars Station", 0, 0, "Keelway stop Strike Hangars, F3 (canon) · two platforms, crew turnstiles", "transport", status="canon",
           rect=[1.24, 1.74, 0.05, 0.18]),
         B("Crew Gate Hall", 300, 200, "duty check-in for every shift · alert boards · kit issue"),
         B("Deck Lift Hall", 220, 160, "lifts to the decks above for crews who live elsewhere"),
         B("Shift Lodge", 260, 180, "rest rooms for crews between shifts · 1,200 bunks"),
         B("Duty Rosters Office", 150, 100, "shift planning for 60,000 crew"),
         B("Gate Canteen", 180, 110, "hot food round the clock"),
         B("Strike Hangars Clinic", 200, 140, "first aid, flight medicine, fitness checks"),
         B("Prow Fire Station", 220, 120, "crash and fire crews for the bow end"),
         B("Gate Pod Stop", 160, 70, "pods to every rack hall", "transport"),
         B("Prow Garden", 300, 200, "small park at the deck's bow tip", "park"),
         U("Gate Utility Plant", 160, 120, "substation · air · water"),
         U("Gate Service Shaft", 110, 90, "access to the 60 m service layer"),
     ]},
    {"id": "P2", "name": "Ordnance Yards", "bounds": [4.0, 8.0, -3.5, 3.5], "lanes": "G–S",
     "role": "Magazines, armorers, weapons assembly, fuel, drone racks",
     "intro": "Every round, missile and fuel cell for the strike wings. The magazines sit in blast berms, well away from the crews' way in and the Keelway.",
     "streets": [("Keelway", "y", 0.0, 60), ("Magazine Road", "y", -1.25, 40), ("Armory Road", "y", 1.25, 40), ("F12 Street", "x", 6.0, 30)],
     "items": [
         B("Missile Magazine", 420, 160, "missiles for the strike wings · buried in blast berms"),
         B("Torpedo Magazine", 380, 190, "heavy torpedoes for the heavy strike squadrons"),
         B("Cannon Round Store", 300, 140, "cannon shells, belted and boxed"),
         B("Countermeasure Store", 240, 120, "flares, chaff and decoy drones"),
         B("Bomb Store", 340, 170, "free-fall and guided bombs"),
         B("Magazine Control", 160, 110, "tracks and issues every round"),
         B("Weapons Assembly Shop", 380, 220, "fuzes fitted, warheads mated, missiles tested"),
         B("Armorers' Hall", 320, 200, "armorers' workshops, tool cribs, training bay"),
         B("Ordnance Test Range", 900, 180, "sealed, baffled live-fire range", "yard"),
         B("Disposal Pit", 180, 180, "safe destruction of faulty rounds", "yard"),
         B("Ordnance Rail Depot", 520, 110, "munitions trains to the rack halls", "transport"),
         B("Loader Drone Depot", 320, 180, "hauler drones that carry rounds to the racks (canon drone class)"),
         U("Propellant Tank Farm", 420, 300, "craft fuel in double-walled tanks"),
         U("Fuel Cell Farm", 300, 260, "charged power cells for the craft"),
         U("Fuel Control Room", 140, 100, "pumps and valves for the fuel lines to the racks"),
         B("Berm Park", 600, 260, "planted blast buffer between the magazines and the Keelway", "park"),
         B("Armorers' Lodge", 260, 150, "rest rooms for armorers on shift"),
         B("Intercept Drone Racks", 340, 200, "intercept drones on ready racks (canon drone class)"),
         B("Strike Drone Racks", 380, 220, "strike drones on ready racks (canon drone class)"),
         B("Ordnance Fire Station", 200, 130, "fire and blast crews"),
         B("Ordnance Clinic", 140, 100, "blast and burn treatment"),
         U("Ordnance Utility Plant", 220, 150, "substation · air · water"),
         U("Ordnance Service Shaft", 140, 110, "access to the 60 m service layer"),
     ]},
    {"id": "P3", "name": "Port Launch Wing", "bounds": [8.0, 14.0, -6.0, -3.25], "lanes": "A–F",
     "role": "Launch shafts 1–16 to the port Forward Grid, launch control, arming aprons",
     "intro": "A strip along the port hull shoulder. Shafts 1–16 (canon) lift craft straight up to the port Forward Grid.",
     "streets": [("Port Launch Road", "y", -3.27, 40), ("F20 Street", "x", 10.0, 30), ("F24 Street", "x", 12.0, 30)],
     "items": shafts(-1, 1) + [
         B("Port Launch Control", 200, 110, "launch controllers for shafts 1–16 · windows over the shaft heads"),
         B("Launch Queue Apron", 600, 140, "craft line up here for their shaft", "yard"),
         B("Port Arming Apron", 460, 120, "last weapons checks before launch", "yard"),
         B("Port Launch Ready Rooms", 180, 90, "crews wait here on alert"),
         B("Shaft Maintenance Shop", 240, 110, "lift cradles and shaft door repairs"),
         U("Port Catapult Plant", 220, 130, "power for the shaft launch rails"),
         B("Port Wing Fire Station", 160, 100, "crash and fire crews"),
         U("Port Launch Service Shaft", 100, 80, "access to the 60 m service layer"),
     ]},
    {"id": "P4", "name": "Starboard Launch Wing", "bounds": [8.0, 14.0, 3.25, 6.0], "lanes": "T–Y",
     "role": "Launch shafts 17–32 to the starboard Forward Grid, recovery apron, damage triage",
     "intro": "The starboard shoulder strip. Shafts 17–32 (canon) serve the starboard Forward Grid; craft coming home are checked here first.",
     "streets": [("Starboard Launch Road", "y", 3.27, 40), ("F20 Street", "x", 10.0, 30), ("F24 Street", "x", 12.0, 30)],
     "items": shafts(1, 17) + [
         B("Starboard Launch Control", 220, 120, "launch controllers for shafts 17–32"),
         B("Recovery Apron", 520, 160, "craft coming home drop out of the shafts here", "yard"),
         B("Starboard Arming Apron", 400, 130, "last weapons checks before launch", "yard"),
         B("Damage Triage Bay", 260, 140, "first look at craft that come back hurt"),
         B("Shaft Door Workshop", 180, 120, "shaft doors and seals"),
         B("Starboard Launch Ready Rooms", 160, 100, "crews wait here on alert"),
         U("Starboard Catapult Plant", 200, 150, "power for the shaft launch rails"),
         B("Starboard Wing Fire Station", 170, 110, "crash and fire crews"),
         U("Starboard Launch Service Shaft", 110, 90, "access to the 60 m service layer"),
     ]},
    {"id": "P5", "name": "Port Rack Halls", "bounds": [8.0, 14.0, -3.25, 0.0], "lanes": "G–M",
     "role": "1st and 2nd Strike Wings: rack halls 1–12 (1,800 craft)",
     "intro": "Twelve squadron rack halls for the 1st and 2nd Wings, each holding 150 craft in tiers under the 1,969 ft (600 m) ceiling, with the wings' ready halls and stores.",
     "streets": [("Keelway", "y", -0.025, 50), ("Port Hangar Road", "y", -1.65, 40), ("F20 Street", "x", 10.0, 30), ("F24 Street", "x", 12.0, 30)],
     "items": racks(1, "1st", -1)[:3] + [B("1st Wing Ready Hall", 260, 160, "ready rooms and briefing for the 1st Wing")] + racks(1, "1st", -1)[3:] + [
         B("Port Rack Lift Control", 140, 100, "runs the rack lifts that bring craft down to the floor"),
         B("Port Taxi Apron", 700, 160, "craft taxi from the halls to the launch roads", "yard")]
         + racks(7, "2nd", -1)[:3] + [B("2nd Wing Ready Hall", 280, 150, "ready rooms and briefing for the 2nd Wing")] + racks(7, "2nd", -1)[3:] + [
         B("Port Hangar Canteen", 200, 120, "meals for the port rack crews"),
         B("Port Parts Store", 300, 180, "spares for 1st and 2nd Wing craft"),
         B("Port Crew Lockers", 220, 110, "lockers and showers"),
         B("Port Racks Fire Station", 200, 120, "crash and fire crews"),
         B("Port Pod Stop", 140, 60, "pods along the Keelway", "transport"),
         U("Port Racks Utility Plant", 240, 160, "substation · air · water"),
         U("Port Racks Service Shaft", 140, 110, "access to the 60 m service layer"),
     ]},
    {"id": "P6", "name": "Starboard Rack Halls", "bounds": [8.0, 14.0, 0.0, 3.25], "lanes": "M–S",
     "role": "3rd and 4th Strike Wings: rack halls 13–24 (1,800 craft)",
     "intro": "Twelve squadron rack halls for the 3rd and 4th Wings, mirroring the port side, plus the craft wash.",
     "streets": [("Keelway", "y", 0.025, 50), ("Starboard Hangar Road", "y", 1.65, 40), ("F20 Street", "x", 10.0, 30), ("F24 Street", "x", 12.0, 30)],
     "items": racks(13, "3rd", 1)[:3] + [B("3rd Wing Ready Hall", 270, 150, "ready rooms and briefing for the 3rd Wing")] + racks(13, "3rd", 1)[3:] + [
         B("Starboard Rack Lift Control", 150, 100, "runs the rack lifts"),
         B("Starboard Taxi Apron", 680, 170, "craft taxi from the halls to the launch roads", "yard")]
         + racks(19, "4th", 1)[:3] + [B("4th Wing Ready Hall", 250, 170, "ready rooms and briefing for the 4th Wing")] + racks(19, "4th", 1)[3:] + [
         B("Craft Wash Hall", 300, 140, "decontamination wash after every sortie"),
         B("Starboard Hangar Canteen", 190, 130, "meals for the starboard rack crews"),
         B("Starboard Parts Store", 320, 170, "spares for 3rd and 4th Wing craft"),
         B("Starboard Crew Lockers", 200, 120, "lockers and showers"),
         B("Starboard Racks Fire Station", 190, 120, "crash and fire crews"),
         B("Starboard Pod Stop", 150, 60, "pods along the Keelway", "transport"),
         U("Starboard Racks Utility Plant", 230, 170, "substation · air · water"),
         U("Starboard Racks Service Shaft", 130, 120, "access to the 60 m service layer"),
     ]},
    {"id": "P7", "name": "Port Repair Yards", "bounds": [14.0, 16.92, -6.0, -3.25], "lanes": "A–F",
     "role": "Heavy repairs, engines, airframes, coatings, salvage",
     "intro": "Where damaged craft are stripped down and rebuilt. Engine run-ups happen behind blast fences.",
     "streets": [("Port Yard Road", "y", -4.5, 30), ("F31 Street", "x", 15.5, 30)],
     "items": [
         B("Heavy Repair Hangar", 520, 300, "full strip-downs, six craft at a time"),
         B("Engine Shop", 360, 200, "engine overhauls and test cells"),
         B("Engine Test Stand", 300, 160, "run-ups behind blast fences", "yard"),
         B("Airframe Shop", 340, 220, "frames, skins and landing gear"),
         B("Avionics Lab", 200, 140, "sensors, radios and flight computers"),
         B("Coatings Hall", 300, 180, "armour and low-signature coatings"),
         B("Port Repair Parts Warehouse", 380, 200, "spares for the repair yards"),
         B("Salvage Yard", 400, 250, "wrecks stripped for parts", "yard"),
         B("Repair Crews' Hall", 220, 130, "lockers, canteen and rest rooms for mechanics"),
         B("Port Yards Fire Station", 160, 110, "fire crews"),
         U("Port Yards Utility Plant", 200, 140, "substation · air · water"),
         U("Port Yards Service Shaft", 120, 100, "access to the 60 m service layer"),
     ]},
    {"id": "P8", "name": "Wing Command", "bounds": [14.0, 16.92, -3.25, 3.25], "lanes": "G–S",
     "role": "Strike wing headquarters, operations, briefings, duty lodges, mess, medical",
     "intro": "The headquarters of the four strike wings. Vector coordinates flight operations and living squadron leaders command the pilots (canon Q106).",
     "streets": [("Keelway", "y", 0.0, 100), ("Command Road", "y", -1.6, 40), ("Ready Road", "y", 1.6, 40), ("F31 Street", "x", 15.5, 30)],
     "items": [
         B("Wing Command", 420, 260, "strike wing headquarters · Vector's flight operations desk · squadron leaders' offices"),
         B("Strike Operations Centre", 300, 220, "live picture of every craft in flight"),
         B("Intelligence Briefing Hall", 260, 180, "threat briefings before every sortie"),
         B("Squadron Leaders' Hall", 240, 160, "the 24 squadron leaders' offices and wardroom"),
         B("Mission Planning Rooms", 220, 150, "routes, targets and timings"),
         B("Debrief Hall", 240, 140, "every flight debriefed on landing"),
         B("Space Conditions Office", 140, 100, "space weather, debris and radiation forecasts for flight crews"),
         B("Command Plaza", 400, 300, "parade and gathering square", "plaza"),
         B("Duty Crew Lodge 1", 300, 180, "rest for crews on 24-hour duty · 1,500 bunks"),
         B("Duty Crew Lodge 2", 340, 160, "rest for crews on 24-hour duty · 1,800 bunks"),
         B("Hangar Mess Hall", 300, 200, "meals for 8,000 a shift"),
         B("Hangar Medical Centre", 320, 200, "flight surgeons, crash trauma, 120 beds"),
         B("Fitness Hall", 260, 180, "g-force training, gym and pool"),
         B("Wing Memorial Garden", 300, 200, "for crews lost in action", "park"),
         B("Hangar Commissary", 220, 140, "shop for daily needs"),
         B("Uniform and Kit Store", 200, 120, "flight suits, helmets, kit"),
         B("Hangar Police Post", 160, 110, "security for the strike decks"),
         B("Command Fire Station", 200, 130, "fire crews"),
         B("Command Pod Stop", 180, 70, "pods along the Keelway", "transport"),
         U("Wing Command Utility Plant", 240, 170, "substation · air · water"),
         U("Wing Command Service Shaft", 140, 120, "access to the 60 m service layer"),
     ]},
    {"id": "P9", "name": "Starboard Repair Yards", "bounds": [14.0, 16.92, 3.25, 6.0], "lanes": "T–Y",
     "role": "Battle-damage rebuilds, weapons fit, shields, drone repairs",
     "intro": "The starboard repair yards: rebuilds, weapons and shields fitted and tuned, and the drone repair bay.",
     "streets": [("Starboard Yard Road", "y", 4.5, 30), ("F31 Street", "x", 15.5, 30)],
     "items": [
         B("Rebuild Hangar", 480, 280, "battle-damage rebuilds"),
         B("Weapons Fit Shop", 300, 180, "guns and pylons fitted and tested"),
         B("Shield Calibration Hall", 260, 200, "craft shields tuned in a screened hall"),
         B("Canopy and Seat Shop", 200, 120, "canopies, ejection seats, cockpit fit"),
         B("Fuel Cell Shop", 220, 150, "power cells tested and recharged"),
         B("Drone Repair Bay", 300, 170, "repairs for strike and intercept drones"),
         B("Tool and Gauge Store", 180, 110, "calibrated tools for the yards"),
         B("Starboard Repair Parts Warehouse", 340, 220, "spares for the repair yards"),
         B("Craft Paint Hall", 280, 160, "squadron markings and touch-ups"),
         B("Starboard Yards Fire Station", 150, 120, "fire crews"),
         U("Starboard Yards Utility Plant", 180, 150, "substation · air · water"),
         U("Starboard Yards Service Shaft", 110, 110, "access to the 60 m service layer"),
     ]},
]

# ---------------------------------------------------------------------------------- Cruiser Docks
# C5 (canon): cruisers 2,000 × 420 × 300 m; 3 Aerion Cruiser Gates in the starboard hull, F38–F48.
# Proposed: each gate is 3,281 ft (1,000 m) wide and opens on two berths side by side, so the
# six cruisers come in nose first across the beam. Berth 1,542 × 6,726 ft (470 × 2,050 m).

def gate(n, x0):
    bays = [[x0 + 0.01, x0 + 0.48, 4.0, 6.048], [x0 + 0.52, x0 + 0.99, 4.0, 6.048]]
    return [
        {"name": "Cruiser Gate %d Berths" % n, "bays": bays, "bay_m": (470, 2050), "bay_word": "berths", "kind": "bays",
         "bay_names": ["Berth %d" % (2 * n - 1), "Berth %d" % (2 * n)],
         "notes": "Two berths for 2 km escort cruisers (canon size 2,000 × 420 m), nose to the hull gate; berths proposed"},
        {"name": "Cruiser Gate %d" % n, "rect": [x0, x0 + 1.0, 6.051, 6.063], "kind": "transport", "status": "canon",
         "notes": "Canon (errata C5): one of the three Aerion Cruiser Gates in the starboard hull, F38–F48. Width proposed"},
    ]


CRUISER = {
    "district": "Cruiser Docks", "file": "cruiser-docks", "doc": "Cruiser_Docks_Precincts.md", "code": "D5F4", "title": "Cruiser Docks",
    "lead": ("Cruiser Docks is the starboard half of Deck 5's middle, F34 to F55, from the Keelway to the starboard hull. "
             "Canon (Sheet S5, errata C5, Q115): 23.2 sq mi (60.0 km²), berths for the six 2 km escort cruisers "
             "(6,562 × 1,378 × 984 ft / 2,000 × 420 × 300 m), three Aerion Cruiser Gates in the starboard hull at F38–F48, "
             "30,000 people (dockworkers, cruiser crews, loaders, inspectors), centre address D5-F43-T, cross-line stop Dockside "
             "at F52, 3.2 mi (5.1 km) to starboard. Aerion and Ferrum share fleet logistics (fuel, ammunition, stores, parts). "
             "The Atrium Plaza (canon) cuts the stern-port corner."),
    "rule": ("Layout rule: the berths sit against the hull behind their gates, stores at the bow end, repairs at the stern end, "
             "freight and the fleet offices along the Keelway. Proposed: each gate is 3,281 ft (1,000 m) wide and opens onto two "
             "berths side by side, so cruisers come in nose first across the beam."),
}
CRUISER["precincts"] = [
    {"id": "P1", "name": "Cruiser Gates", "bounds": [19.0, 24.0, 3.25, 6.1], "lanes": "T–Y",
     "role": "The three Cruiser Gates and six cruiser berths, supply quays",
     "intro": "The three canon Cruiser Gates in the starboard hull and the six berths behind them, with supply quays between the gates.",
     "streets": [("Quay Road", "y", 3.95, 40), ("F41 Street", "x", 20.5, 30), ("F45 Street", "x", 22.5, 30)],
     "items": gate(1, 19.05) + gate(2, 21.0) + gate(3, 22.95) + [
         B("Supply Quay A", 380, 1500, "cranes load stores into the cruisers at Gates 1 and 2", "yard", cell=1),
         B("Supply Quay B", 360, 1450, "cranes load stores into the cruisers at Gates 2 and 3", "yard", cell=3),
         B("Cruiser Gate Control", 220, 140, "opens the three hull gates · traffic to and from the fleet"),
         B("Gangway Hall", 300, 160, "where cruiser crews board and leave"),
         B("Fleet Inspectors' Office", 200, 120, "inspectors sign cruisers in and out"),
         B("Gangway Canteen", 180, 110, "food for crews coming ashore"),
         B("Berths Fire Station", 220, 140, "fire and rescue for the berths"),
         B("Quay Pod Stop", 160, 70, "pods to the Keelway", "transport"),
         U("Berth Utility Plant", 260, 180, "shore power, water and air for docked cruisers"),
         U("Gates Service Shaft", 140, 120, "access to the 60 m service layer"),
     ]},
    {"id": "P2", "name": "Fleet Stores", "bounds": [16.92, 19.0, 3.25, 6.1], "lanes": "T–Y",
     "role": "Cruiser fuel, munitions, stores and repair parts (with Ferrum)",
     "intro": "Fuel, ammunition, stores and repair parts for the six cruisers, shared with Ferrum (canon Q115).",
     "streets": [("Stores Road", "y", 4.6, 30), ("F36 Street", "x", 18.0, 30)],
     "items": [
         B("Cruiser Munitions Magazine", 420, 220, "shells and missiles for the six cruisers"),
         U("Cruiser Fuel Farm", 400, 300, "fuel for the cruisers, piped to the berths"),
         B("Fleet Stores Warehouse", 480, 260, "food, water and supplies for cruiser crews"),
         B("Repair Parts Depot", 360, 200, "parts made on Ferrum (Deck 8)"),
         B("Freight Lift to Ferrum", 200, 200, "heavy-goods lifts down to Deck 8 (assumption)", "transport"),
         B("Stores Control", 160, 110, "stock and loading plans"),
         B("Loaders' Hall", 220, 130, "loaders' lockers and canteen"),
         B("Stores Fire Station", 160, 100, "fire crews"),
         U("Fleet Stores Utility Plant", 180, 140, "substation · air · water"),
         U("Fleet Stores Service Shaft", 110, 100, "access to the 60 m service layer"),
     ]},
    {"id": "P3", "name": "Cruiser Repair Yards", "bounds": [24.0, 27.6235, 3.25, 6.1], "lanes": "T–Y",
     "role": "Module repairs, turrets, engines, armour plate; cross-line Dockside stop",
     "intro": "Cruiser modules (engines, turrets, shields) are lifted out at the berths and rebuilt here; full refits go to Drydock Prime on Deck 8 (canon). The cross-line Dockside stop (canon, F52) is here.",
     "streets": [("Yard Road", "y", 3.95, 40), ("F50 Street", "x", 25.0, 30), ("Cross-line", "x", 26.0, 50, 3.25, 4.94), ("F54 Street", "x", 27.0, 30)],
     "items": [
         B("Dockside Station", 0, 0, "cross-line stop Dockside, F52, 3.2 mi (5.1 km) to starboard (canon)", "transport", status="canon",
           rect=[25.85, 26.15, 4.96, 5.24]),
         B("Module Repair Hall", 700, 320, "engines, turrets and shield modules lifted out of the cruisers"),
         B("Turret Shop", 320, 220, "cruiser turrets rebuilt and test-fired"),
         B("Engine Module Shop", 380, 240, "cruiser engine modules"),
         B("Hull Plate Store", 400, 200, "Void Ore armour plates (canon hull material)"),
         B("Shield Module Lab", 220, 160, "shield emitters tuned and tested"),
         B("Heavy Transporter Depot", 360, 180, "carriers that move modules to and from the berths", "transport"),
         B("Yard Crane Depot", 260, 140, "mobile cranes"),
         B("Inspectors' Hall", 220, 140, "dock inspectors' offices and test labs"),
         B("Dockside Park", 360, 260, "green space by the station", "park"),
         B("Repair Yards Fire Station", 180, 120, "fire crews"),
         U("Repair Yards Utility Plant", 220, 160, "substation · air · water"),
         U("Repair Yards Service Shaft", 130, 110, "access to the 60 m service layer"),
     ]},
    {"id": "P4", "name": "Dock Freight", "bounds": [16.92, 21.0, 0.0, 3.25], "lanes": "M–S",
     "role": "Cargo for the fleet: freight siding, container yard, bonded and cold stores",
     "intro": "Everything the cruisers take on board passes through here first, checked by the inspectors.",
     "streets": [("Keelway", "y", 0.05, 100), ("Freight Road", "y", 1.6, 40), ("F36 Street", "x", 18.0, 30), ("F38 Street", "x", 19.0, 30)],
     "items": [
         B("Keelway Freight Siding", 900, 120, "freight trains to and from the other decks", "transport"),
         B("Container Yard", 600, 400, "stacks of cruiser stores in transit", "yard"),
         B("Bonded Warehouse", 420, 240, "goods waiting for inspection"),
         B("Cold Store", 300, 180, "food for the cruiser crews"),
         B("Loaders' Depot", 340, 200, "loader vehicles and hauler drones"),
         B("Freight Inspection Shed", 380, 200, "inspectors check every load"),
         B("Dock Freight Office", 160, 110, "bookings and paperwork"),
         B("Hazardous Cargo Shed", 240, 160, "fuel cells and chemicals, kept apart"),
         B("Truck Park", 500, 240, "freight trucks waiting for loads", "transport"),
         U("Water and Air Tanks", 260, 200, "stores for cruiser resupply"),
         B("Dock Freight Fire Station", 170, 110, "fire crews"),
         U("Dock Freight Utility Plant", 200, 150, "substation · air · water"),
         U("Dock Freight Service Shaft", 120, 110, "access to the 60 m service layer"),
     ]},
    {"id": "P5", "name": "Fleet Quarter", "bounds": [21.0, 24.0, 0.0, 3.25], "lanes": "M–S",
     "role": "Fleet Admiral's office, captains' and crews' halls, clinic, Keelway Port entrance",
     "intro": "The shore base of the escort fleet: six cruiser captains under the Fleet Admiral (canon), and the halls of the crews and dockworkers.",
     "streets": [("Keelway", "y", 0.05, 100), ("Fleet Road", "y", 1.6, 40), ("F45 Street", "x", 22.5, 30)],
     "items": [
         B("Fleet Admiral's Office", 300, 200, "headquarters of the escort fleet"),
         B("Cruiser Captains' Hall", 220, 160, "the six captains' shore offices"),
         B("Fleet Communications Centre", 200, 140, "secure links to the cruisers (canon Q163)"),
         B("Dock Station Entrance", 240, 120, "starboard entrance to Keelway Port station (F46)", "transport"),
         B("Fleet Plaza", 300, 300, "square in front of the Fleet Admiral's Office", "plaza"),
         B("Cruiser Crews' Hall", 340, 220, "shore rooms, lockers and canteen for crews on leave"),
         B("Dockworkers' Hall", 300, 180, "dockworkers' union hall, lockers, canteen"),
         B("Crew Transit Lodge", 360, 200, "beds for crews between cruisers · 2,000 rooms"),
         B("Fleet Training Hall", 300, 200, "damage-control and boarding drills"),
         B("Fleet Clinic", 260, 160, "crew medicine and dental"),
         B("Dock Canteen", 200, 140, "meals for the dock workforce"),
         U("Fleet Quarter Utility Plant", 200, 140, "substation · air · water"),
         U("Fleet Quarter Service Shaft", 120, 100, "access to the 60 m service layer"),
     ]},
    {"id": "P6", "name": "Dockside", "bounds": [24.0, 27.6235, 0.0, 3.25], "lanes": "M–S", "excl": [PLAZA], "lanes_note": "less the Atrium Plaza",
     "role": "Shops, inn, offices and gardens for the dock workforce; cross-line",
     "intro": "The dockside streets around the Atrium Plaza (canon, not part of the precinct): shops, an inn and the shipping agents' offices.",
     "streets": [("Dockside Road", "y", 2.5, 40), ("Cross-line", "x", 26.0, 50, 1.79, 3.25)],
     "items": [
         B("Dockside Market", 400, 200, "shops and food for dock workers"),
         B("Spacers' Inn", 260, 180, "rooms for visiting crews"),
         B("Dockside Offices", 240, 150, "shipping agents and brokers"),
         B("Dockside Gardens", 500, 200, "garden walk beside the Atrium Plaza", "park"),
         B("Dockside Hostel", 220, 140, "cheap beds for dockworkers on double shifts"),
         B("Dock Police Post", 160, 110, "dock security"),
         B("Dockside Clinic", 160, 120, "walk-in clinic"),
         B("Dockside Pod Stop", 150, 70, "pods around the plaza", "transport"),
         U("Dockside Utility Plant", 180, 130, "substation · air · water"),
         U("Dockside Service Shaft", 110, 100, "access to the 60 m service layer"),
     ]},
]

# ---------------------------------------------------------------------------------- Flight Control
FLIGHT = {
    "district": "Flight Control", "file": "flight-control", "doc": "Flight_Control_Precincts.md", "code": "D5F5", "title": "Flight Control",
    "lead": ("Flight Control is the band across the whole deck from F55 to F59, between the Port of Arrivals and Cruiser Docks "
             "(bow) and the Pilots' Quarter (stern). Canon (Sheet S5): 7.7 sq mi (20.0 km²), the Beacon tower, traffic control, "
             "briefing halls, 15,000 people (controllers, flight officers, dispatchers, analysts), centre address D5-F57-M. "
             "The Keelway runs through the middle; the Atrium Plaza (canon) just touches the bow edge."),
    "rule": ("Layout rule: approach control and sensors at both hull ends, where the docks and gates are; briefings on the "
             "port side, dispatch on the starboard side, and the Beacon with the master traffic room in the middle beside the "
             "Keelway. The Beacon's height is not designed yet (errata D1 allows one landmark per city up to 1,181 ft / 360 m)."),
}
FLIGHT["precincts"] = [
    {"id": "P1", "name": "Port Approach", "bounds": [27.6235, 29.28, -6.1, -3.25], "lanes": "A–F",
     "role": "Approach control and sensors for the port docks and the Hall of Arrivals",
     "intro": "Controllers who bring every ship into the port docks and the Hall of Arrivals.",
     "streets": [("Approach Road", "y", -4.6, 30), ("F57 Street", "x", 28.5, 30)],
     "items": [
         B("Port Approach Control", 320, 200, "controllers for the port docks and the Hall of Arrivals"),
         B("Port Sensor Hall", 240, 180, "radar and sensor arrays for the port approaches"),
         B("Pilot Boat Station", 260, 160, "pilot craft that guide big ships in"),
         B("Port Controllers' Lodge", 200, 140, "rest rooms for controllers on shift"),
         B("Port Approach Fire Station", 150, 100, "fire crews"),
         U("Port Antenna Plant", 220, 120, "power and cooling for the hull antennas"),
         U("Port Approach Utility Plant", 160, 120, "substation · air · water"),
         U("Port Approach Service Shaft", 100, 90, "access to the 60 m service layer"),
     ]},
    {"id": "P2", "name": "Briefing Halls", "bounds": [27.6235, 29.28, -3.25, -0.75], "lanes": "G–L",
     "role": "Main briefing hall, flight plans, space weather, investigations",
     "intro": "Every flight on and off the ship is briefed and filed here.",
     "streets": [("Briefing Road", "y", -2.0, 30), ("F57 Street", "x", 28.5, 30)],
     "items": [
         B("Main Briefing Hall", 360, 220, "1,500 seats · daily flight briefings for the whole deck"),
         B("Squadron Briefing Rooms", 300, 160, "forty rooms for crews and squadrons"),
         B("Flight Plans Office", 200, 140, "every flight on and off the ship is filed here"),
         B("Space Weather Office", 160, 110, "storms, debris and solar wind forecasts"),
         B("Navigation Charts Library", 200, 120, "charts of the Drift Network"),
         B("Accident Investigation Board", 240, 150, "investigates every incident"),
         B("Flight Officers' Club", 220, 140, "officers' dining and lounge"),
         B("Briefing Halls Canteen", 180, 110, "meals for the briefing staff"),
         U("Briefing Halls Utility Plant", 160, 110, "substation · air · water"),
         U("Briefing Halls Service Shaft", 100, 90, "access to the 60 m service layer"),
     ]},
    {"id": "P3", "name": "Beacon", "bounds": [27.6235, 29.28, -0.75, 0.75], "lanes": "L–N", "excl": [PLAZA],
     "role": "The Beacon tower (canon), master traffic control room, Keelway",
     "intro": "The Beacon (canon), the deck's control tower, stands at F57 beside the Keelway with the master traffic room next to it.",
     "streets": [("Keelway", "y", 0.0, 100), ("F57 Street", "x", 28.75, 30)],
     "items": [
         B("The Beacon", 0, 0, "Canon landmark: the deck's control tower. Footprint and place proposed; height not designed yet", status="canon",
           rect=[28.38, 28.62, -0.38, -0.14]),
         B("Traffic Control Centre", 300, 220, "the deck's master traffic room: every craft from launch to landing"),
         B("Backup Control Room", 160, 120, "hardened standby for the Traffic Control Centre"),
         B("Beacon Plaza", 300, 200, "square at the foot of the Beacon", "plaza"),
         B("Controllers' Rest Hall", 200, 140, "quiet rooms between shifts"),
         B("Beacon Pod Stop", 140, 60, "pods along the Keelway", "transport"),
         U("Beacon Utility Plant", 160, 120, "substation · air · water"),
     ]},
    {"id": "P4", "name": "Dispatch", "bounds": [27.6235, 29.28, 0.75, 3.25], "lanes": "O–S",
     "role": "Dispatch centre, schedules, analysts, controller training",
     "intro": "Dispatchers give every craft its crew, slot and route; analysts study the traffic.",
     "streets": [("Dispatch Road", "y", 2.0, 30), ("F57 Street", "x", 28.5, 30)],
     "items": [
         B("Dispatch Centre", 340, 200, "dispatchers assign craft, crews and slots"),
         B("Shuttle Schedules Office", 200, 120, "timetables for every shuttle"),
         B("Cruiser Liaison Office", 180, 110, "links Flight Control with the escort cruisers"),
         B("Analysts' Hall", 260, 160, "traffic data and incident analysis"),
         B("Controllers' Training Centre", 300, 180, "simulators for new controllers"),
         U("Flight Radio Hub", 200, 160, "ship-wide flight radio and data links"),
         B("Dispatch Canteen", 160, 100, "meals for the dispatch staff"),
         B("Dispatch Fire Station", 150, 100, "fire crews"),
         U("Dispatch Utility Plant", 150, 110, "substation · air · water"),
         U("Dispatch Service Shaft", 100, 100, "access to the 60 m service layer"),
     ]},
    {"id": "P5", "name": "Starboard Approach", "bounds": [27.6235, 29.28, 3.25, 6.1], "lanes": "T–Y",
     "role": "Approach control for the Cruiser Gates, rescue coordination, evacuation craft",
     "intro": "Approach control for the three Cruiser Gates and the starboard side, and the rescue centre.",
     "streets": [("Approach Road", "y", 4.6, 30), ("F57 Street", "x", 28.5, 30)],
     "items": [
         B("Starboard Approach Control", 300, 200, "controllers for the Cruiser Gates and the starboard side"),
         B("Starboard Sensor Hall", 260, 160, "radar and sensor arrays for the starboard approaches"),
         B("Gate Traffic Desk", 180, 120, "slots for cruisers using the three gates"),
         B("Rescue Coordination Centre", 260, 180, "search and rescue (canon Q114) and evacuation flights (canon Q160)"),
         B("Evacuation Craft Hangar", 400, 200, "Aerion's evacuation craft (canon Q160)"),
         B("Starboard Controllers' Lodge", 220, 120, "rest rooms for controllers on shift"),
         U("Starboard Approach Utility Plant", 170, 120, "substation · air · water"),
         U("Starboard Approach Service Shaft", 100, 100, "access to the 60 m service layer"),
     ]},
]

# ---------------------------------------------------------------------------------- Pilots' Quarter
PILOTS = {
    "district": "Pilots' Quarter", "file": "pilots-quarter", "doc": "Pilots_Quarter_Precincts.md", "code": "D5F6", "title": "Pilots' Quarter",
    "lead": ("The Pilots' Quarter is the stern end of Deck 5, F59 to the stern wall, the full width of the deck. Canon (Sheet S5): "
             "17.4 sq mi (45.0 km²), housing, simulators, flight school, 45,000 people (flight instructors, trainee pilots, "
             "shopkeepers, home helpers), centre address D5-F63-M, Keelway stop Pilots' Quarter at F65 (end of the line)."),
    "rule": ("Layout rule (Jordan, 26 Nov 2026): Aerion's homes, schools and family services sit here. The flight school and "
             "simulators face each other across the town centre (Pilots' Commons); the homes fill the rounded stern either side "
             "of the Keelway station. Home counts are not designed yet."),
}
PILOTS["precincts"] = [
    {"id": "P1", "name": "Flight School", "bounds": [29.28, 31.5, -6.1, -2.25], "lanes": "A–H",
     "role": "Flight school, training hangar, trainee halls",
     "intro": "Aerion's flight school: classrooms, training craft and the trainees' halls.",
     "streets": [("School Road", "y", -4.2, 30), ("F61 Street", "x", 30.5, 30)],
     "items": [
         B("Flight School Main Hall", 380, 240, "classrooms, lecture theatres, school offices"),
         B("Training Hangar", 460, 260, "the school's training craft"),
         B("Training Flight Line", 800, 160, "training craft parked and serviced", "yard"),
         B("Navigation School", 240, 160, "navigation and Drift charts"),
         B("Engineering School", 280, 180, "mechanics' and armorers' courses"),
         B("Survival School", 300, 200, "escape, survival and vacuum drills"),
         B("Cadet Parade Ground", 300, 200, "parades and graduation", "plaza"),
         B("Trainee Halls 1", 300, 120, "rooms for trainee pilots"),
         B("Trainee Halls 2", 260, 140, "rooms for trainee pilots"),
         B("Trainee Halls 3", 320, 110, "rooms for trainee mechanics and controllers"),
         B("Instructors' Apartments", 240, 160, "homes for flight instructors"),
         B("School Library", 160, 120, "manuals, logs and quiet study"),
         B("School Canteen", 200, 130, "meals for staff and trainees"),
         B("School Sports Field", 400, 250, "pitch and running track", "park"),
         B("Flight School Clinic", 140, 100, "flight medicine for trainees"),
         U("Flight School Utility Plant", 180, 120, "substation · air · water"),
         U("Flight School Service Shaft", 100, 90, "access to the 60 m service layer"),
     ]},
    {"id": "P2", "name": "Simulator Halls", "bounds": [29.28, 31.5, 2.25, 6.1], "lanes": "S–Y",
     "role": "Flight and bridge simulators, zero-g tank, centrifuge, public flight arcade",
     "intro": "Simulators for every pilot and crew aboard, and a public arcade where anyone can fly.",
     "streets": [("Simulator Road", "y", 4.2, 30), ("F61 Street", "x", 30.5, 30)],
     "items": [
         B("Full-Motion Simulator Hall", 420, 240, "48 full-motion cockpit simulators"),
         B("Squadron Simulator Hall", 380, 220, "whole squadrons fly linked missions"),
         B("Cruiser Bridge Simulator", 260, 180, "bridge, helm and gunnery training for cruiser crews"),
         B("Zero-G Training Tank", 220, 220, "weightless drills in a sealed tank"),
         B("Centrifuge Hall", 200, 160, "g-force tolerance training"),
         B("Simulator Control Centre", 200, 120, "runs and records every session"),
         B("Simulator Workshops", 260, 140, "simulator repairs and new cockpits"),
         B("Public Flight Arcade", 240, 160, "simulators open to everyone aboard"),
         B("Starboard Lawn", 400, 220, "lawns between the halls", "park"),
         B("Simulator Halls Canteen", 160, 110, "meals and coffee"),
         U("Simulator Data Centre", 200, 140, "computers that run the simulators"),
         U("Simulator Halls Utility Plant", 200, 150, "substation · air · water"),
         U("Simulator Halls Service Shaft", 100, 100, "access to the 60 m service layer"),
     ]},
    {"id": "P3", "name": "Pilots' Commons", "bounds": [29.28, 31.5, -2.25, 2.25], "lanes": "I–Q",
     "role": "Town centre: town hall, schools, hospital, market, park, museum",
     "intro": "The town centre of the Quarter and the deck's family services: schools, the deck hospital, the market and the main park.",
     "streets": [("Keelway", "y", 0.0, 100), ("Port Commons Road", "y", -1.25, 40), ("Starboard Commons Road", "y", 1.25, 40), ("F61 Street", "x", 30.5, 30)],
     "items": [
         B("Pilots' Quarter Town Hall", 260, 180, "local offices for the Quarter"),
         B("Commons Square", 300, 240, "the Quarter's main square", "plaza"),
         B("Commons Market", 360, 220, "shops and food hall"),
         B("Restaurants Row", 400, 100, "a street of restaurants and cafés"),
         B("Quarter Primary School", 260, 180, "for the children of pilots and crews"),
         B("Quarter Secondary School", 320, 200, "for the children of pilots and crews"),
         B("Childcare Centre", 180, 140, "day care for crews on shift"),
         B("Quarter Hospital", 360, 240, "Aerion's main hospital"),
         B("Family Health Centre", 200, 140, "doctors, dentists, midwives"),
         B("Quarter Library", 200, 140, "books, study rooms, makers' space"),
         B("Aerion Flight Museum", 340, 200, "craft and stories of the strike wings"),
         B("Pilots' Theatre", 240, 180, "theatre and cinema"),
         B("Commons Park", 600, 400, "the Quarter's main park", "park"),
         B("Sports Centre", 320, 220, "pool, courts and gym"),
         B("Commons Hotel", 240, 160, "rooms for visiting families"),
         B("Quarter Police Station", 180, 120, "police for the Quarter"),
         B("Quarter Fire Station", 200, 130, "fire crews"),
         B("Commons Pod Stop", 150, 60, "pods along the Keelway", "transport"),
         U("Commons Utility Plant", 220, 160, "substation · air · water"),
         U("Commons Service Shaft", 120, 110, "access to the 60 m service layer"),
     ]},
    {"id": "P4", "name": "Port Homes", "bounds": [31.5, 33.42, -6.1, -0.75], "lanes": "A–L",
     "role": "Homes: family apartments, towers, terraces, courtyard homes",
     "intro": "Homes on the port side of the rounded stern, from towers by the station to terraces along the hull.",
     "streets": [("Port Homes Road", "y", -3.0, 30), ("F65 Street", "x", 32.5, 30)],
     "items": [
         B("Pilots' Towers 1", 120, 120, "apartment tower by the station"),
         B("Pilots' Towers 2", 100, 100, "apartment tower by the station"),
         B("Family Apartments 1", 240, 120, "family flats around a courtyard"),
         B("Family Apartments 2", 220, 140, "family flats around a courtyard"),
         B("Port Homes Shops", 200, 100, "corner shops and a café"),
         B("Port Homes Park", 400, 260, "playgrounds and lawns", "park"),
         B("Family Apartments 3", 260, 110, "family flats, larger homes on the top floors"),
         B("Courtyard Homes 1", 200, 200, "two-storey homes round a garden court"),
         B("Courtyard Homes 2", 180, 180, "two-storey homes round a garden court"),
         B("Port Homes School", 220, 160, "primary school"),
         B("Crew Terraces 1", 300, 60, "row houses"),
         B("Crew Terraces 2", 280, 60, "row houses"),
         B("Crew Terraces 3", 320, 60, "row houses"),
         B("Senior Pilots' Villas", 260, 160, "homes for retired pilots"),
         B("Port Homes Clinic", 120, 100, "family doctor"),
         U("Port Homes Utility Plant", 160, 120, "substation · air · water"),
         U("Port Homes Service Shaft", 100, 90, "access to the 60 m service layer"),
     ]},
    {"id": "P5", "name": "Quarter Station", "bounds": [31.5, 33.42, -0.75, 0.75], "lanes": "L–N",
     "role": "Pilots' Quarter Keelway station (F65), deck lifts, Keelway depot",
     "intro": "The end of the Keelway: the Pilots' Quarter stop (canon, F65), deck lifts and the depot where Keelway trains rest.",
     "streets": [("Keelway", "y", 0.0, 100), ("F64 Street", "x", 32.0, 30)],
     "items": [
         B("Pilots' Quarter Station", 0, 0, "Keelway stop Pilots' Quarter, F65 (canon) · end of the line", "transport", status="canon",
           rect=[32.2, 32.8, -0.23, -0.07]),
         B("Station Square", 300, 200, "square in front of the station", "plaza"),
         B("Quarter Deck Lifts", 220, 160, "lifts to the other decks", "transport"),
         B("Station Shops", 240, 120, "grocery and daily needs"),
         B("Pod and Taxi Rank", 300, 140, "pods and taxis", "transport"),
         B("Keelway Depot", 500, 200, "Keelway trains stabled at the end of the line", "transport"),
         B("Quarter Hostel", 200, 130, "rooms for visitors"),
         U("Station Utility Plant", 140, 110, "substation · air · water"),
     ]},
    {"id": "P6", "name": "Starboard Homes", "bounds": [31.5, 33.42, 0.75, 6.1], "lanes": "N–Y",
     "role": "Homes: garden apartments, lofts, towers, family courts",
     "intro": "Homes on the starboard side of the rounded stern.",
     "streets": [("Starboard Homes Road", "y", 3.0, 30), ("F65 Street", "x", 32.5, 30)],
     "items": [
         B("Starboard Towers 1", 110, 110, "apartment tower by the station"),
         B("Starboard Towers 2", 130, 100, "apartment tower by the station"),
         B("Garden Apartments 1", 260, 140, "flats with roof gardens"),
         B("Hangar Lofts", 280, 120, "big open lofts for crews"),
         B("Starboard Homes Market", 220, 120, "food market"),
         B("Starboard Green", 420, 240, "lawns and sports courts", "park"),
         B("Garden Apartments 2", 240, 150, "flats with roof gardens"),
         B("Garden Apartments 3", 220, 130, "flats with roof gardens"),
         B("Trainee Flats", 200, 100, "small flats for new graduates"),
         B("Family Courts 1", 220, 200, "family homes round a shared court"),
         B("Family Courts 2", 200, 200, "family homes round a shared court"),
         B("Starboard Homes School", 240, 150, "primary school"),
         B("Row Houses 1", 300, 55, "row houses"),
         B("Row Houses 2", 260, 55, "row houses"),
         B("Starboard Homes Clinic", 130, 100, "family doctor"),
         U("Starboard Homes Utility Plant", 170, 120, "substation · air · water"),
         U("Starboard Homes Service Shaft", 100, 100, "access to the 60 m service layer"),
     ]},
]

# ---------------------------------------------------------------------------------- Atrium Plaza
PLAZA_D = {
    "approved": True,   # Jordan approved the plan as canon (PR #27, 27 Nov 2026)
    "district": "Atrium Plaza", "file": "atrium-plaza", "doc": "Atrium_Plaza_Precincts.md", "code": "D5F1", "title": "Atrium Plaza",
    "lead": ("The Atrium Plaza is Deck 5's central plaza, a circle 2.22 mi (3.57 km) across centred on F52 on the centreline, "
             "around the Spine Atrium shaft. Canon (Sheet S5): 3.9 sq mi (10.0 km²), Governor's Hall, pilots' guild, Atrium "
             "Central station, 10,000 people (Governor's staff, clerks, guards, transit crews), centre address D5-F52-M; the "
             "Spine Atrium shaft is 0.99 mi (1.6 km) across with a 164 ft (50 m) wall. The Keelway and the cross-line both "
             "stop at Atrium Central."),
    "rule": ("Layout rule: the Keelway and the cross-line cut the plaza ring into four quarters. The shaft itself is an opening "
             "(0.78 sq mi, 2.01 km²) and is not part of any precinct, so the four precincts add up to 3.09 sq mi (8.0 km²). "
             "Proposed: the Keelway and cross-line cross the shaft on bridges, with Atrium Central's platforms at the rim."),
}


def quad(sx, sy):
    return quarter_disc(PLAZA[0], PLAZA[1], PLAZA[2] - 0.0003, sx, sy)


PLAZA_D["precincts"] = [
    {"id": "P1", "name": "Governor's Quarter", "poly": quad(-1, -1), "lanes": "I–M", "excl": [SHAFT],
     "role": "Governor's Hall (canon), City Council, Deck Chief, records",
     "intro": "The seat of Aerion's government: Vector's Governor's Hall (canon) and the elected City Council (errata G1).",
     "streets": [("Keelway", "y", -0.025, 50), ("Cross-line", "x", 25.9875, 25)],
     "items": [
         B("Governor's Hall", 300, 200, "Canon: Vector's seat, the Governor's staff and clerks. Footprint proposed", status="canon"),
         B("Aerion City Council Chamber", 200, 140, "the deck's five elected councillors (errata G1)"),
         B("Deck Chief's Office", 160, 120, "office of the Deck Chief (canon post)"),
         B("Hall of Records", 180, 120, "clerks: permits, citizenship and housing desks"),
         B("Governor's Guard Post", 140, 100, "the plaza guards"),
         B("Governor's Garden", 260, 180, "formal garden on the rim", "park"),
     ]},
    {"id": "P2", "name": "Station Quarter", "poly": quad(-1, 1), "lanes": "M–Q", "excl": [SHAFT],
     "role": "Atrium Central station (canon), interchange, transit crews",
     "intro": "Atrium Central (canon), where the Keelway meets the cross-line.",
     "streets": [("Keelway", "y", 0.025, 50), ("Cross-line", "x", 25.9875, 25)],
     "items": [
         B("Atrium Central Station", 0, 0, "Canon stop for the Keelway and the cross-line. Station halls at the shaft rim, beside the Keelway, proposed", "transport", status="canon",
           rect=[24.75, 25.15, 0.08, 0.24]),
         B("Interchange Walk", 300, 100, "covered walk between the Keelway and cross-line platforms", "transport"),
         B("Station Plaza", 240, 180, "square outside the station", "plaza"),
         B("Transit Crews' Hall", 200, 120, "the transit crews' base"),
         B("Help Desk Pavilion", 120, 90, "maps, lost property, help"),
     ]},
    {"id": "P3", "name": "Guild Quarter", "poly": quad(1, -1), "lanes": "I–M", "excl": [SHAFT],
     "role": "The pilots' guild (canon), licensing, guild archive",
     "intro": "Home of the pilots' guild (canon): licences, ratings and the guild lodge.",
     "streets": [("Keelway", "y", -0.025, 50), ("Cross-line", "x", 26.0125, 25)],
     "items": [
         B("Pilots' Guild", 320, 200, "Canon: the guildhall of Aerion's pilots. Footprint proposed", status="canon"),
         B("Licensing Hall", 200, 140, "flight licence tests and ratings"),
         B("Guild Archive", 180, 120, "every pilot's logbook and rating"),
         B("Guild Lodge", 220, 140, "members' club and dining"),
         B("Guild Court", 220, 160, "the guild's courtyard", "plaza"),
     ]},
    {"id": "P4", "name": "Rim Gardens", "poly": quad(1, 1), "lanes": "M–Q", "excl": [SHAFT],
     "role": "Gardens and overlook on the rim of the Spine Atrium, cafés",
     "intro": "Gardens and cafés along the rim of the Spine Atrium, with a terrace looking into the shaft.",
     "streets": [("Keelway", "y", 0.025, 50), ("Cross-line", "x", 26.0125, 25)],
     "items": [
         B("Atrium Rim Gardens", 400, 200, "gardens on the rim of the Spine Atrium", "park"),
         B("Atrium Overlook", 160, 100, "viewing terrace over the shaft", "plaza"),
         B("Rim Cafés", 240, 100, "cafés facing the gardens"),
         B("Plaza Clinic", 120, 90, "first aid"),
         U("Atrium Plaza Utility Plant", 160, 120, "substation · air · water"),
         U("Atrium Plaza Service Shaft", 100, 90, "access to the 60 m service layer"),
     ]},
]


# ---------------------------------------------------------------------------------- scale and block fillers
# Buildings are listed at their working size and drawn at this scale, so they sit at the same city scale
# as the Port of Arrivals (its halls run 1,300 to 3,000 ft / 400 to 900 m). Blocks left empty after the named
# buildings are placed get a filler that suits the precinct (open hangar bays, quay yards, homes, gardens).
STRIKE["scale"], CRUISER["scale"], FLIGHT["scale"], PILOTS["scale"], PLAZA_D["scale"] = 1.6, 1.4, 1.2, 1.3, 1.0
YARD, PARK, BLD = "yard", "park", "building"
FILLS = {
    ("Strike Hangars", "P1"): [("Crew Garden", "small park for crews between shifts", PARK), ("Gate Yard", "parking for crew pods and tugs", YARD)],
    ("Strike Hangars", "P2"): [("Blast Berm", "earth and armour berm between the magazines", YARD), ("Munitions Bunker", "spare magazine bunker inside a blast berm", BLD)],
    ("Strike Hangars", "P3"): [("Launch Apron", "open apron where craft line up for the shafts", YARD)],
    ("Strike Hangars", "P4"): [("Launch Apron", "open apron where craft line up for the shafts", YARD)],
    ("Strike Hangars", "P5"): [("Open Bay", "open hangar floor for craft parked between sorties (canon look: vast open bays)", YARD), ("Taxi Apron", "craft taxi between the halls and the launch roads", YARD)],
    ("Strike Hangars", "P6"): [("Open Bay", "open hangar floor for craft parked between sorties (canon look: vast open bays)", YARD), ("Taxi Apron", "craft taxi between the halls and the launch roads", YARD)],
    ("Strike Hangars", "P7"): [("Work Yard", "outdoor repair yard with mobile cranes", YARD), ("Parts Shed", "covered parts store", BLD)],
    ("Strike Hangars", "P8"): [("Command Garden", "garden between the command buildings", PARK), ("Staff Offices", "offices for wing staff", BLD)],
    ("Strike Hangars", "P9"): [("Work Yard", "outdoor repair yard with mobile cranes", YARD), ("Parts Shed", "covered parts store", BLD)],
    ("Cruiser Docks", "P1"): [("Quay Yard", "open quay with cranes and stacked stores", YARD)],
    ("Cruiser Docks", "P2"): [("Stores Shed", "covered store for fleet supplies", BLD), ("Stores Yard", "open stacking yard", YARD)],
    ("Cruiser Docks", "P3"): [("Module Yard", "open yard for modules waiting for repair", YARD), ("Repair Shed", "covered workshop", BLD)],
    ("Cruiser Docks", "P4"): [("Container Stacks", "stacked containers in transit", YARD), ("Freight Shed", "covered freight store", BLD)],
    ("Cruiser Docks", "P5"): [("Fleet Offices", "offices for the fleet's shore staff", BLD), ("Crew Garden", "garden for crews ashore", PARK)],
    ("Cruiser Docks", "P6"): [("Dockside Shops", "shops and cafés", BLD), ("Pocket Park", "small park", PARK)],
    ("Flight Control", "P1"): [("Antenna Field", "ground antennas and sensor masts", YARD)],
    ("Flight Control", "P2"): [("Briefing Annex", "more briefing rooms", BLD), ("Quiet Garden", "garden for staff on breaks", PARK)],
    ("Flight Control", "P3"): [("Beacon Garden", "garden by the Beacon", PARK)],
    ("Flight Control", "P4"): [("Dispatch Annex", "more dispatch desks", BLD), ("Staff Garden", "garden for staff on breaks", PARK)],
    ("Flight Control", "P5"): [("Antenna Field", "ground antennas and sensor masts", YARD)],
    ("Pilots' Quarter", "P1"): [("Cadet House", "boarding house for cadets", BLD), ("Training Field", "outdoor drill and sports field", PARK)],
    ("Pilots' Quarter", "P2"): [("Simulator Annex", "more simulator bays", BLD), ("Lawn", "lawn between the halls", PARK)],
    ("Pilots' Quarter", "P3"): [("Commons Shops", "shops with flats above", BLD), ("Pocket Park", "small park", PARK)],
    ("Pilots' Quarter", "P4"): [("Apartment Block", "flats for pilots' and crews' families", BLD), ("Garden Court", "homes round a shared garden", BLD), ("Neighbourhood Park", "playground and lawn", PARK), ("Terrace Row", "row houses", BLD)],
    ("Pilots' Quarter", "P5"): [("Station Garden", "garden by the station", PARK)],
    ("Pilots' Quarter", "P6"): [("Apartment Block", "flats for pilots' and crews' families", BLD), ("Garden Court", "homes round a shared garden", BLD), ("Neighbourhood Park", "playground and lawn", PARK), ("Terrace Row", "row houses", BLD)],
    ("Atrium Plaza", "P1"): [("Rim Garden", "garden on the plaza ring", PARK), ("Plaza Pavilion", "kiosks and seating", BLD)],
    ("Atrium Plaza", "P2"): [("Rim Garden", "garden on the plaza ring", PARK), ("Plaza Pavilion", "kiosks and seating", BLD)],
    ("Atrium Plaza", "P3"): [("Rim Garden", "garden on the plaza ring", PARK), ("Plaza Pavilion", "kiosks and seating", BLD)],
    ("Atrium Plaza", "P4"): [("Rim Garden", "garden on the plaza ring", PARK), ("Plaza Pavilion", "kiosks and seating", BLD)],
}

DISTRICTS = [STRIKE, CRUISER, FLIGHT, PILOTS, PLAZA_D]
for _D in DISTRICTS:
    for _P in _D["precincts"]:
        _P["fill"] = FILLS.get((_D["district"], _P["id"]), [])


# ---------------------------------------------------------------------------------- build

def build(D):
    ok = D.get("approved")
    pset = {"schema": "invicta-atlas/precincts@1", "deck": 5, "district": D["district"], "status": "canon" if ok else "proposed", "version": "v2",
            "updated": TODAY, "doc": "Game/Docs/" + D["doc"],
            "note": "Laid out 27 Nov 2026 following the Port of Arrivals pattern. " + ("Approved as canon by Jordan." if ok else "Proposed, awaiting Jordan."),
            "precincts": []}
    rows = []
    for P in D["precincts"]:
        shape, area, streets, bld = lay_out(D, P)
        bx = G.bbox(shape)
        f0, f1 = frames_for(bx[0], bx[1])
        L, W = bx[1] - bx[0], bx[3] - bx[2]
        p = {"id": P["id"], "name": P["name"], "frames": "F%d–F%d" % (f0, f1), "lanes": P["lanes"],
             "bounds_km": [round(v, 4) for v in (P.get("bounds") or bx)],
             "polygon_km": [[round(a, 4), round(b, 4)] for a, b in (P.get("poly") or G.rect_poly(P["bounds"]))],
             "status": "canon" if ok else "proposed", "area_km2_stated": round(area, 2), "role": P["role"],
             "intro": "%s. %s" % (km_text(L, W), P["intro"]), "build_order": int(P["id"][1:])}
        if P.get("excl"):
            p["exclude_circles_km"] = [list(c) for c in P["excl"]]
            p["exclude_note"] = "Spine Atrium shaft (canon) is an opening, not part of the precinct" if P["excl"][0] == SHAFT else "Atrium Plaza (canon) is not part of the precinct"
        if P.get("lanes_note"):
            p["lanes_note"] = P["lanes_note"]
        p["buildings"] = bld
        p["streets"] = streets
        pset["precincts"].append(p)
        rows.append((P, p, L, W, area))
    return pset, rows


def doc_for(D, pset, rows):
    total = sum(r[4] for r in rows)
    ok = D.get("approved")
    out = ["# %s — Precinct Plans (%s)" % (D["title"], "✅ canon, approved by Jordan" if ok else "⏳ proposed, 27 Nov 2026, awaiting Jordan"), ""]
    out.append("Laid out 27 Nov 2026 following the Port of Arrivals pattern (`Port_of_Arrivals_Precincts.md`). %s %s "
               "Plans are true top views: **bow right, port up**." % (D["lead"], "Jordan approved this plan as canon." if ok else "Everything here is a proposal unless marked canon."))
    out.append("")
    out.append(D["rule"])
    out.append("")
    out.append("Common sizes (proposed, as in the Port of Arrivals): main roads 131 ft (40 m), streets 98 ft (30 m), the Keelway corridor 328 ft (100 m). "
               "Every building is kept 98 ft (30 m) clear of the streets, so no block edge ever cuts a building. Building heights, floors and "
               "interiors are not designed yet.")
    out.append("")
    out.append("Building shapes (Jordan, 27 Nov 2026): buildings follow their blocks. Each block's land, 98 ft (30 m) in from its streets, "
               "the hull and the plaza rims, is shared out between its buildings by their listed size, 66 ft (20 m) apart, so buildings "
               "take the block's curves along the Spine Atrium, the Atrium Plaza and the hull. Each building then gets a shape that suits "
               "its use: courtyard, L-shape, U-shape, curved front, rounded corners or oval; halls, hangars, yards and parks fill their "
               "lot. The Size column gives each building's overall size; its shape is in the notes. Map colours show what each "
               "building is used for (legend on the map).")
    out.append("")
    out.append("## Layout")
    out.append("")
    out.append("| # | Precinct | Frames | Lanes | Size | Area | What is there |")
    out.append("|---|---|---|---|---|---|---|")
    for P, p, L, W, a in rows:
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (p["id"], p["name"], p["frames"], p["lanes"] + (" (%s)" % p["lanes_note"] if p.get("lanes_note") else ""),
                                                          km_text(L, W), area_text(a), p["role"]))
    out.append("")
    out.append("Total %s." % area_text(total))
    out.append("")
    for P, p, L, W, a in rows:
        fa, fb = p["frames"].split("–")
        la, lb = p["lanes"].split("–")
        out.append("## %s · %s — %s to %s, lanes %s–%s" % (p["id"], p["name"], fa, fb, la, lb))
        out.append("")
        out.append("%s, %s. %s Status: %s." % (km_text(L, W), area_text(a), P["intro"], "canon" if ok else "proposed"))
        out.append("")
        names = []
        for s in p["streets"]:
            if s["name"] not in names:
                names.append(s["name"])
        out.append("Streets: " + "; ".join("%s, %s ft (%d m)" % (n, ftn(next(s["width_m"] for s in p["streets"] if s["name"] == n)), next(s["width_m"] for s in p["streets"] if s["name"] == n)) for n in names) + ".")
        out.append("")
        out.append("| Item | Size | Notes |")
        out.append("|---|---|---|")
        for b in p["buildings"]:
            note = b["notes"]
            if b["status"] == "canon" and not note.lower().startswith("canon"):
                note = "**Canon** · " + note
            if b.get("shape") and b["shape"] != "follows its block":
                note += " · shape: %s" % b["shape"]
            out.append("| %s | %s | %s |" % (b["name"], b["size_text"], note))
        out.append("")
    return "\n".join(out)


def write_reference(results):
    """Section 8 of Invicta_Ship_Reference.md (and its mirror): one table per district."""
    L = ["", "## 8. Deck 5 precincts for the other districts (⏳ proposed, 27 Nov 2026, awaiting Jordan)", "",
         "Jordan asked (27 Nov 2026) for every Deck 5 district to get its precincts. Each district now has a precinct plan in the "
         "Port of Arrivals pattern: precincts on frame and lane lines, named streets, and every block holding something, with "
         "names and codes. All proposed. Canon kept: Strike Hangars' 32 launch shafts (errata C4, F16–F28, lanes D–F and T–V) "
         "and the Strike Hangars Keelway stop (F3); the three Cruiser Gates (C5, F38–F48) with two 2 km cruiser berths behind "
         "each; the cross-line Dockside stop (F52); the Beacon (F57); the Pilots' Quarter stop (F65); the Governor's Hall, "
         "pilots' guild and Atrium Central in the Atrium Plaza. Homes and family services are in the Pilots' Quarter (design "
         "rule above). Building heights, floors and interiors are not designed yet. Made by `Invicta/tools/seed_deck5_districts.py`.", ""]
    for D, pset in results:
        nb = sum(len(p["buildings"]) for p in pset["precincts"])
        tot = sum(p["area_km2_stated"] for p in pset["precincts"])
        L.append("**%s** (%d precincts, %d items, %s). Details: `%s`." % (D["district"], len(pset["precincts"]), nb, area_text(tot), D["doc"]))
        L += ["", "| # | Precinct | Frames | Lanes | Area | What is there |", "|---|---|---|---|---|---|"]
        for p in pset["precincts"]:
            L.append("| %s | %s | %s | %s | %s | %s |" % (p["id"], p["name"], p["frames"], p["lanes"], area_text(p["area_km2_stated"]), p["role"]))
        L.append("")
    L.append("Notes: the Strike Hangars precincts measure 42.23 sq mi (109.37 km²) on the Rev B outline against errata C2's "
             "109.1 km²; Flight Control's and the Pilots' Quarter's shared edge (29.28 km) and the Atrium Plaza circle fall "
             "between frames; the Spine Atrium shaft (0.78 sq mi, 2.01 km²) is an opening and in no precinct. All four are "
             "logged as known in the app's rules (`Invicta/data/rules.json`).")
    L.append("")
    L.append("Building shapes and map colours (Jordan, 27 Nov 2026): Deck 5 buildings follow their blocks, with curved edges "
             "along the Spine Atrium, the Atrium Plaza rim and the hull, and courtyards, L and U shapes, curved fronts and rounded "
             "corners where they fit. Port of Arrivals buildings that have a building plan show that plan's outline. Every building "
             "is coloured by use on the map and in 3D: roads and transit dark grey, the Keelway light blue, police and security "
             "blue, fire and emergency red, medical white with a red edge, homes warm tan, shops and food orange, offices and "
             "government purple, industry, hangars and docks steel grey, utilities and services yellow, parks and plazas green, "
             "schools and training teal.")
    txt = "\n".join(L) + "\n"
    for base in ("Game/Docs", "Docs/2_Design_Docs"):
        path = os.path.join(ROOT, *base.split("/"), "Invicta_Ship_Reference.md")
        s = open(path, encoding="utf-8").read()
        if "\n## 8. Deck 5 precincts" in s:
            s = s[:s.index("\n## 8. Deck 5 precincts")] + "\n"
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(s.rstrip("\n") + "\n" + txt)


def main():
    results = []
    for D in DISTRICTS:
        pset, rows = build(D)
        path = os.path.join(APP, "data", "decks", "D5", D["file"] + ".json")
        if os.path.isfile(path):   # keep each building's purpose (written by hand, not generated)
            with open(path, encoding="utf-8") as f:
                PU.keep_purposes(json.load(f), pset)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(pset, f, ensure_ascii=False, separators=(", ", ": "))
            f.write("\n")
        doc = PU.put_section(doc_for(D, pset, rows), PU.doc_section(pset)).rstrip("\n")
        for base in ("Game/Docs", "Docs/2_Design_Docs"):
            with open(os.path.join(ROOT, *base.split("/"), D["doc"]), "w", encoding="utf-8", newline="\n") as f:
                f.write(doc + "\n")
        nb = sum(len(p["buildings"]) for p in pset["precincts"])
        print("%-16s %d precincts, %d buildings, %.2f km²" % (D["district"], len(rows), nb, sum(r[4] for r in rows)))
        results.append((D, pset))
    write_reference(results)


if __name__ == "__main__":
    main()
