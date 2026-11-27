"""Building footprints that are not plain rectangles (Jordan, 27 Nov 2026).

A building keeps `rect_km` as its overall box (the lot it sits on, used for blocks, sizes and
labels). When it has a shaped footprint it also stores:

    "outline_km": [[[x, y], ...], ...]    one or more outer rings (ship km, any polygon, curves as points)
    "holes_km":   [[[x, y], ...], ...]    courtyards and other open space inside the outline (optional)
    "shape":      "courtyard"            plain words for the shape (courtyard, L-shape, U-shape, rounded,
                                          oval, curved front, follows its block, from its plan)

The 2D maps and the 3D view draw the outline (with its holes) instead of the box. Pure Python.
"""

import math

from . import geometry as G

SHAPE_WORDS = {
    "solid": "follows its block",
    "rounded": "rounded corners",
    "courtyard": "courtyard",
    "L": "L-shape",
    "U": "U-shape",
    "oval": "oval",
    "bow": "curved front",
    "plan": "from its plan",
}


# ------------------------------------------------------------------ basics

def signed_area(p):
    a = 0.0
    n = len(p)
    for i in range(n):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def ccw(p):
    return list(p) if signed_area(p) > 0 else list(reversed(p))


def bbox(p):
    return G.bbox(p)


def dedupe(p, tol=1e-6):
    out = []
    for q in p:
        if not out or abs(q[0] - out[-1][0]) > tol or abs(q[1] - out[-1][1]) > tol:
            out.append((q[0], q[1]))
    while len(out) > 2 and abs(out[0][0] - out[-1][0]) <= tol and abs(out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out


def simplify(p, tol=0.0008):
    """Drop points that sit within tol km (default 0.8 m) of the line through their neighbours."""
    p = dedupe(p)
    changed = True
    while changed and len(p) > 3:
        changed = False
        out = []
        n = len(p)
        i = 0
        keep = [True] * n
        for i in range(n):
            if not keep[(i - 1) % n]:
                continue  # never drop two neighbours in one pass
            a, b, c = p[(i - 1) % n], p[i], p[(i + 1) % n]
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            if L < 1e-12:
                keep[i] = False
                changed = True
                continue
            d = abs((c[0] - a[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (c[1] - a[1])) / L
            if d < tol:
                keep[i] = False
                changed = True
        out = [q for q, k in zip(p, keep) if k]
        if len(out) < 3:
            break
        p = out
    return p


def _segs_cross(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 > 1e-14 and o2 < -1e-14 or o1 < -1e-14 and o2 > 1e-14) and (o3 > 1e-14 and o4 < -1e-14 or o3 < -1e-14 and o4 > 1e-14)


def self_intersects(p):
    n = len(p)
    segs = [(p[i], p[(i + 1) % n]) for i in range(n)]
    boxes = [(min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])) for a, b in segs]
    order = sorted(range(n), key=lambda i: boxes[i][0])
    for k, i in enumerate(order):
        bi = boxes[i]
        for j in order[k + 1:]:
            bj = boxes[j]
            if bj[0] > bi[1]:
                break
            if abs(i - j) <= 1 or abs(i - j) == n - 1:
                continue
            if bj[2] > bi[3] or bj[3] < bi[2]:
                continue
            if _segs_cross(segs[i][0], segs[i][1], segs[j][0], segs[j][1]):
                return True
    return False


def dist_to_boundary(x, y, p):
    best = 1e9
    n = len(p)
    for i in range(n):
        ax, ay = p[i]
        bx, by = p[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


# ------------------------------------------------------------------ offsets

def _meet(l1, l2):
    (p, r), (q, s) = l1, l2
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
    return (p[0] + t * r[0], p[1] + t * r[1])


def offset(p, d, round_join=False, step_deg=8.0):
    """Move every edge of a simple polygon inward by d km (d < 0 moves it outward).
    Corners are mitred, and edges that shrink to nothing are dropped (so short chords of an arc
    never fold over). With round_join, corners that open up when growing get a circular arc,
    which is how rounded corners are made. Returns None when the result would still fold over
    itself (the polygon is too thin for that offset)."""
    p = ccw(simplify(p))
    if len(p) < 3:
        return None
    if round_join and d < 0:
        return _grow_round(p, d, step_deg)
    lines = []
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        e = (b[0] - a[0], b[1] - a[1])
        L = math.hypot(*e)
        if L < 1e-12:
            continue
        nx, ny = -e[1] / L, e[0] / L  # inward (left) normal of a ccw polygon
        lines.append(((a[0] + nx * d, a[1] + ny * d), e))
    for _ in range(len(lines)):
        if len(lines) < 3:
            return None
        verts = [_meet(lines[i - 1], lines[i]) for i in range(len(lines))]
        bad = None
        for i in range(len(lines)):
            v0, v1 = verts[i], verts[(i + 1) % len(lines)]
            e = lines[i][1]
            if (v1[0] - v0[0]) * e[0] + (v1[1] - v0[1]) * e[1] <= 0:
                bad = i
                break
        if bad is None:
            break
        lines.pop(bad)
    out = dedupe(verts)
    if len(out) < 3 or signed_area(out) <= 1e-9 or self_intersects(out):
        return None
    if d > 0:  # shrinking: every point must stay inside the old outline
        for q in out:
            if not G.point_in_poly(q[0], q[1], p) or dist_to_boundary(q[0], q[1], p) < d * 0.6:
                return None
    return out


def _grow_round(p, d, step_deg):
    out = []
    n = len(p)
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        e1 = (b[0] - a[0], b[1] - a[1])
        e2 = (c[0] - b[0], c[1] - b[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        if l1 < 1e-12 or l2 < 1e-12:
            continue
        n1 = (-e1[1] / l1, e1[0] / l1)
        n2 = (-e2[1] / l2, e2[0] / l2)
        cross = e1[0] * e2[1] - e1[1] * e2[0]
        if cross > 1e-12:  # convex corner: arc round it
            a1 = math.atan2(-n1[1], -n1[0])
            da = math.atan2(-n2[1], -n2[0]) - a1
            while da <= -math.pi:
                da += 2 * math.pi
            while da > math.pi:
                da -= 2 * math.pi
            k = max(1, int(abs(math.degrees(da)) / step_deg))
            for j in range(k + 1):
                t = a1 + da * j / k
                out.append((b[0] - d * math.cos(t), b[1] - d * math.sin(t)))
        else:
            out.append(_meet(((b[0] + n1[0] * d, b[1] + n1[1] * d), e1), ((b[0] + n2[0] * d, b[1] + n2[1] * d), e2)))
    out = dedupe(out)
    if len(out) < 3 or signed_area(out) <= 1e-9 or self_intersects(out):
        return None
    return out


def rounded(p, r):
    """Round every convex corner with radius r km (shrink then grow back with arcs)."""
    q = offset(p, r)
    if not q:
        return None
    return offset(q, -r, round_join=True)


def is_boxy(p, tol=0.97):
    b = bbox(p)
    return abs(signed_area(p)) >= tol * (b[1] - b[0]) * (b[3] - b[2])


# ------------------------------------------------------------------ shapes inside a lot

def l_shape(b, corner, fx=0.5, fy=0.5):
    """A box with one corner cut away: corner 0 bow-port, 1 stern-port, 2 stern-starboard, 3 bow-starboard."""
    x0, x1, y0, y1 = b
    cx, cy = x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy
    if corner == 0:
        pts = [(cx, y0), (x1, y0), (x1, y1), (x0, y1), (x0, cy), (cx, cy)]
    elif corner == 1:
        pts = [(x0, y0), (cx, y0), (cx, cy), (x1, cy), (x1, y1), (x0, y1)]
    elif corner == 2:
        pts = [(x0, y0), (x1, y0), (x1, cy), (cx, cy), (cx, y1), (x0, y1)]
    else:
        pts = [(x0, y0), (x1, y0), (x1, y1), (cx, y1), (cx, cy), (x0, cy)]
    return pts


def u_shape(b, side, open_frac=0.4, depth_frac=0.5):
    """A box with a notch in the middle of one side: 0 port, 1 stern, 2 starboard, 3 bow."""
    x0, x1, y0, y1 = b
    L, W = x1 - x0, y1 - y0
    if side in (0, 2):
        a, c = x0 + L * (1 - open_frac) / 2, x1 - L * (1 - open_frac) / 2
        if side == 0:
            dy = y0 + W * depth_frac
            return [(x0, y0), (a, y0), (a, dy), (c, dy), (c, y0), (x1, y0), (x1, y1), (x0, y1)]
        dy = y1 - W * depth_frac
        return [(x0, y0), (x1, y0), (x1, y1), (c, y1), (c, dy), (a, dy), (a, y1), (x0, y1)]
    a, c = y0 + W * (1 - open_frac) / 2, y1 - W * (1 - open_frac) / 2
    if side == 1:
        dx = x1 - L * depth_frac
        return [(x0, y0), (x1, y0), (x1, a), (dx, a), (dx, c), (x1, c), (x1, y1), (x0, y1)]
    dx = x0 + L * depth_frac
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, c), (dx, c), (dx, a), (x0, a)]


def oval(b, n=48):
    x0, x1, y0, y1 = b
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def bow_front(b, side, frac=0.14, n=16):
    """A box with one long side bowed out in a shallow arc (a curved front), kept inside the box."""
    x0, x1, y0, y1 = b
    L, W = x1 - x0, y1 - y0
    sn = lambda i: math.sin(math.pi * i / n)
    if L >= W:
        s = min(W * frac, 0.04)
        if side % 2 == 0:  # port side
            return [(x0 + L * i / n, y0 + s - s * sn(i)) for i in range(n + 1)] + [(x1, y1), (x0, y1)]
        return [(x0, y0), (x1, y0)] + [(x1 - L * i / n, y1 - s + s * sn(i)) for i in range(n + 1)]
    s = min(L * frac, 0.04)
    if side % 2 == 0:  # bow side
        return [(x1, y0), (x1, y1)] + [(x0 + s - s * sn(i), y1 - W * i / n) for i in range(n + 1)]
    return [(x0, y1), (x0, y0)] + [(x1 - s + s * sn(i), y0 + W * i / n) for i in range(n + 1)]


def courtyard(lot, depth):
    hole = offset(lot, depth)
    if not hole:
        return None
    hb = bbox(hole)
    if min(hb[1] - hb[0], hb[3] - hb[2]) < 0.03 or abs(signed_area(hole)) < 0.12 * abs(signed_area(lot)):
        return None
    soft = rounded(hole, min(0.015, depth * 0.4))
    return soft or hole


def make(lot, style, k=0, depth=None):
    """Footprint for one building on its lot (a polygon in ship km). Returns (outlines, holes, style)."""
    lot = ccw(simplify(lot))
    b = bbox(lot)
    md = min(b[1] - b[0], b[3] - b[2])
    boxy = is_boxy(lot)
    if style == "courtyard":
        dep = depth or max(0.03, min(0.09, md * 0.28))
        h = courtyard(lot, dep)
        if h:
            return [lot], [h], "courtyard"
        style = "solid"
    if style in ("L", "U", "oval", "bow") and not boxy:
        style = "courtyard" if md >= 0.16 else "solid"
        if style == "courtyard":
            return make(lot, "courtyard", k, depth)
    if style == "L":
        return [l_shape(b, k % 4)], [], "L"
    if style == "U":
        return [u_shape(b, k % 4)], [], "U"
    if style == "oval":
        return [oval(b)], [], "oval"
    if style == "bow":
        return [bow_front(b, k)], [], "bow"
    if style == "rounded":
        q = rounded(lot, max(0.008, min(0.04, md * 0.15)))
        if q:
            return [q], [], "rounded"
        style = "solid"
    return [lot], [], "solid"


# ------------------------------------------------------------------ choosing a shape

OPEN_WORDS = ("hangar", "bay", "shed", "works", "depot", "yard", "apron", "plant", "magazine", "bunker", "dock", "quay",
              "berth", "store", "stacks", "field", "range", "shaft", "substation", "gate", "rack", "warehouse", "freight",
              "fuel", "tank farm", "launch", "cradle", "slip", "lift", "station", "stop", "walk", "road", "track")
ROUND_WORDS = ("arena", "stadium", "dome", "rotunda", "chamber", "chapel", "theatre", "amphitheatre", "beacon", "overlook",
               "pavilion", "centrifuge", "observatory", "planetarium", "fountain")


def choose(b, lot, k):
    """Pick a shape for building b (data dict) on its lot. k varies the choice between neighbours."""
    name = (b.get("name") or "").lower()
    kind = b.get("kind", "building")
    cat = b.get("category", "")
    bb = bbox(lot)
    md = min(bb[1] - bb[0], bb[3] - bb[2])
    if kind in ("park", "plaza") or cat == "parks":
        return "rounded"
    if kind in ("transport", "yard", "bays", "utility") or any(w in name for w in OPEN_WORDS):
        return "solid"
    if any(w in name for w in ROUND_WORDS):
        return "oval" if is_boxy(lot) else "rounded"
    if md < 0.09:
        return "rounded"
    if not is_boxy(lot):
        return "courtyard" if md >= 0.16 else "solid"
    if md >= 0.22:
        return ("courtyard", "U", "courtyard", "L")[k % 4]
    if md >= 0.12:
        return ("L", "bow", "U", "L")[k % 4]
    return ("bow", "rounded")[k % 2]


def apply(b, lot, k, style=None, depth=None):
    """Give building b a shaped footprint on lot. Sets outline_km, holes_km, shape and rect_km (the box)."""
    outs, holes, st = make(lot, style or choose(b, lot, k), k, depth)
    r4 = lambda q: [round(q[0], 4), round(q[1], 4)]
    b["outline_km"] = [[r4(q) for q in o] for o in outs]
    if holes:
        b["holes_km"] = [[r4(q) for q in h] for h in holes]
    else:
        b.pop("holes_km", None)
    b["shape"] = SHAPE_WORDS[st]
    xs = [q[0] for o in b["outline_km"] for q in o]
    ys = [q[1] for o in b["outline_km"] for q in o]
    b["rect_km"] = [min(xs), max(xs), min(ys), max(ys)]
    return st


def footprint_area(b):
    """Built ground area in km²: the outline minus its courtyards, or the box (or bays)."""
    if b.get("outline_km"):
        return sum(abs(signed_area(o)) for o in b["outline_km"]) - sum(abs(signed_area(h)) for h in b.get("holes_km") or [])
    shapes = b.get("bays_km") or ([b["rect_km"]] if b.get("rect_km") else [])
    return sum((s[1] - s[0]) * (s[3] - s[2]) for s in shapes)


def outline_points(b):
    return [q for o in b.get("outline_km") or [] for q in o]


# ------------------------------------------------------------------ outline from a stored building plan

def union_outline(polys, x0, y0, flip=False):
    """Union of plan outlines (metres from the lot's bow-port corner) as rings in ship km.
    Exact for the right-angled parts the design tools write. Returns (outers, holes)."""
    xs = sorted({round(q[0], 3) for p in polys for q in p})
    ys = sorted({round(q[1], 3) for p in polys for q in p})
    if len(xs) < 2 or len(ys) < 2:
        return [], []
    filled = set()
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2
        for j in range(len(ys) - 1):
            cy = (ys[j] + ys[j + 1]) / 2
            if any(G.point_in_poly(cx, cy, p) for p in polys):
                filled.add((i, j))
    # directed boundary edges, ccw around each filled cell
    edges = {}
    for (i, j) in filled:
        for a, b, nb in (((i, j), (i + 1, j), (i, j - 1)), ((i + 1, j), (i + 1, j + 1), (i + 1, j)),
                         ((i + 1, j + 1), (i, j + 1), (i, j + 1)), ((i, j + 1), (i, j), (i - 1, j))):
            if nb not in filled:
                edges.setdefault(a, []).append(b)
    rings = []
    while edges:
        start = next(iter(edges))
        ring = [start]
        cur = start
        while True:
            nxt = edges[cur].pop()
            if not edges[cur]:
                del edges[cur]
            if nxt == start:
                break
            ring.append(nxt)
            cur = nxt
            if cur not in edges:
                break
        pts = [(x0 + xs[i] / 1000.0, y0 + ys[j] / 1000.0) for i, j in ring]
        pts = simplify(pts, 1e-7)
        if len(pts) >= 3:
            rings.append(pts)
    outers = [r for r in rings if signed_area(r) > 0]
    holes = [list(reversed(r)) for r in rings if signed_area(r) < 0]
    return outers, holes
