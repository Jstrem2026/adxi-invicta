"""Polygon helpers for tools/design_rooms.py: wings that follow every wall of a building (straight, slanted or
curved), bands of rooms along them, and cutting halls and yards into pieces. Pure Python, metres."""
import math
import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
from atlaslib import footprints as FP  # noqa: E402


def area(p):
    return FP.signed_area(p)


def ccw(p):
    return p if area(p) > 0 else list(reversed(p))


def cw(p):
    return p if area(p) < 0 else list(reversed(p))


def r1(v):
    return round(v + 0.0, 1)


def rpoly(p):
    out = []
    for x, y in p:
        q = [r1(x), r1(y)]
        if not out or q != out[-1]:
            out.append(q)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def bbox(p):
    xs = [q[0] for q in p]
    ys = [q[1] for q in p]
    return min(xs), max(xs), min(ys), max(ys)


def point_in(x, y, p):
    inside = False
    n = len(p)
    for i in range(n):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def clip_half(p, a, b, c):
    """Keep the part of polygon p where a*x + b*y <= c (Sutherland-Hodgman; area-correct for any polygon)."""
    out = []
    n = len(p)
    if not n:
        return out
    for i in range(n):
        P, Q = p[i], p[(i + 1) % n]
        fp, fq = a * P[0] + b * P[1] - c, a * Q[0] + b * Q[1] - c
        if fp <= 0:
            out.append(P)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1])))
    return out


def slab(p, ux, uy, lo, hi):
    """Part of p whose projection on unit vector (ux, uy) lies in [lo, hi]."""
    q = clip_half(p, ux, uy, hi)
    return clip_half(q, -ux, -uy, -lo)


def proj_range(p, ux, uy):
    v = [q[0] * ux + q[1] * uy for q in p]
    return min(v), max(v)


def long_axis(p):
    x0, x1, y0, y1 = bbox(p)
    return (1.0, 0.0) if x1 - x0 >= y1 - y0 else (0.0, 1.0)


def split_by_shares(p, shares, axis=None):
    """Cut p across its long axis into pieces with areas in proportion to shares."""
    ux, uy = axis or long_axis(p)
    lo, hi = proj_range(p, ux, uy)
    tot = sum(shares)
    A = abs(area(p))
    out, start = [], lo
    for k, s in enumerate(shares):
        if k == len(shares) - 1:
            out.append(slab(p, ux, uy, start, hi + 1))
            break
        target = A * s / tot
        a_, b_ = start, hi
        for _ in range(30):  # bisection on the cut position
            mid = (a_ + b_) / 2
            if abs(area(slab(p, ux, uy, start, mid))) < target:
                a_ = mid
            else:
                b_ = mid
        cut = (a_ + b_) / 2
        out.append(slab(p, ux, uy, start, cut))
        start = cut
    return out


def simplify(p, tol=1.0):
    return list(FP.simplify([tuple(q) for q in p], tol))


# ------------------------------------------------------------------ mitred offsets with matching vertices

def _lines(P, d):
    n = len(P)
    L = []
    for i in range(n):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        ln = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / ln, dx / ln  # left normal: inward for a counter-clockwise ring
        L.append(((x1 + nx * d, y1 + ny * d), (dx / ln, dy / ln)))
    return L


def _meet(l1, l2):
    (p, r), (q, s) = l1, l2
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9:
        return (q[0], q[1])
    t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
    return (p[0] + t * r[0], p[1] + t * r[1])


def mitre(P, d):
    """Vertices of P (ccw) moved inward by d, one per vertex of P (vertex i is where edges i-1 and i meet)."""
    L = _lines(P, d)
    n = len(P)
    return [_meet(L[i - 1], L[i]) for i in range(n)]


def _convex(P, i):
    n = len(P)
    a, b, c = P[i - 1], P[i], P[(i + 1) % n]
    return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) > 0


def clean(P, d):
    """Drop vertices until every edge of P keeps its direction when moved inward by d."""
    P = list(P)
    for _ in range(len(P)):
        if len(P) < 3:
            return None
        V = mitre(P, d)
        n = len(P)
        bad = None
        for i in range(n):
            e0 = (P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1])
            e1 = (V[(i + 1) % n][0] - V[i][0], V[(i + 1) % n][1] - V[i][1])
            if e0[0] * e1[0] + e0[1] * e1[1] <= 0.05 * (e0[0] ** 2 + e0[1] ** 2):
                if bad is None or math.hypot(*e0) < bad[1]:
                    bad = (i, math.hypot(*e0))
        if bad is None:
            return P
        i = bad[0]
        j = (i + 1) % n
        drop = j if _convex(P, j) else i
        P.pop(drop)
    return None


def offset_ok(P, d):
    Q = clean(P, d)
    if not Q:
        return None
    V = mitre(Q, d)
    if area(V) <= 1.0 or FP.self_intersects(V):
        return None
    return Q


def inradius(P, hi=None):
    x0, x1, y0, y1 = bbox(P)
    lo, hi = 0.0, hi or min(x1 - x0, y1 - y0) / 2
    for _ in range(18):
        mid = (lo + hi) / 2
        if offset_ok(P, mid):
            lo = mid
        else:
            hi = mid
    return lo


# ------------------------------------------------------------------ a ribbon of bands round a ring

class Ribbon:
    """Bands of rooms and corridors following a ring (an outer wall, or a courtyard wall) inward.
    layers: [(kind, d0, d1)], kind 'rooms' or 'corridor'. Positions along the ribbon are metres along
    each layer's middle line, from vertex 0."""

    def __init__(self, P, depth_total, layers):
        Q = None
        for _ in range(2):
            Q = clean(ccw(P), depth_total)
            if Q:
                break
        self.ok = bool(Q) and len(Q) >= 3
        if not self.ok:
            return
        self.P = Q
        self.layers = layers
        depths = sorted({d for _, a, b in layers for d in (a, b)})
        self.V = {d: mitre(Q, d) for d in depths}
        n = len(Q)
        self.n = n
        self.cum = {}
        for (_, a, b) in layers:
            key = (a, b)
            if key in self.cum:
                continue
            Va, Vb = self.V[a], self.V[b]
            m = [(math.dist(Va[i], Va[(i + 1) % n]) + math.dist(Vb[i], Vb[(i + 1) % n])) / 2 for i in range(n)]
            c = [0.0]
            for v in m:
                c.append(c[-1] + v)
            self.cum[key] = (m, c)

    def length(self, a, b):
        return self.cum[(a, b)][1][-1]

    def _at(self, a, b, s):
        m, c = self.cum[(a, b)]
        s = max(0.0, min(c[-1], s))
        i = 0
        while i < self.n - 1 and c[i + 1] < s:
            i += 1
        f = 0.0 if m[i] < 1e-9 else (s - c[i]) / m[i]
        Va, Vb = self.V[a], self.V[b]
        j = (i + 1) % self.n
        pa = (Va[i][0] + f * (Va[j][0] - Va[i][0]), Va[i][1] + f * (Va[j][1] - Va[i][1]))
        pb = (Vb[i][0] + f * (Vb[j][0] - Vb[i][0]), Vb[i][1] + f * (Vb[j][1] - Vb[i][1]))
        return i, pa, pb

    def piece(self, a, b, s0, s1):
        """Polygon of layer (a, b) between positions s0 and s1."""
        m, c = self.cum[(a, b)]
        i0, pa0, pb0 = self._at(a, b, s0)
        i1, pa1, pb1 = self._at(a, b, s1)
        outer, inner = [pa0], [pb0]
        for i in range(i0 + 1, i1 + 1):
            outer.append(self.V[a][i])
            inner.append(self.V[b][i])
        outer.append(pa1)
        inner.append(pb1)
        return rpoly(outer + list(reversed(inner)))


def band_layers(D, room_depth=12.0, corridor=3.0, two_sided_inner=False):
    """Split a band D deep into rooms and corridors.
    two_sided_inner: the band's inner edge meets another band (thin building), so the last corridor
    is shared down the middle."""
    if D < 7:
        return [("rooms", 0.0, D)]
    if two_sided_inner:
        if D < room_depth + corridor / 2:
            return [("rooms", 0.0, D)]
        unit = 2 * room_depth + corridor
        k = max(0, int(round((D - room_depth - corridor / 2) / unit)))
        layers, d = [], 0.0
        rd = (D - corridor / 2 - k * (corridor)) / (2 * k + 1)
        for _ in range(k):
            layers += [("rooms", d, d + rd), ("corridor", d + rd, d + rd + corridor), ("rooms", d + rd + corridor, d + 2 * rd + corridor)]
            d += 2 * rd + corridor
        layers += [("rooms", d, d + rd), ("corridor", d + rd, D)]
        return layers
    unit = 2 * room_depth + corridor
    if D < unit * 0.75:
        return [("rooms", 0.0, D - corridor), ("corridor", D - corridor, D)]
    k = max(1, int(round(D / unit)))
    rd = (D - k * corridor) / (2 * k)
    layers, d = [], 0.0
    for _ in range(k):
        layers += [("rooms", d, d + rd), ("corridor", d + rd, d + rd + corridor), ("rooms", d + rd + corridor, d + 2 * rd + corridor)]
        d += 2 * rd + corridor
    return layers


def fit_rect(poly, w, d, rng, tries=40):
    """A w x d rectangle (axis-aligned) fully inside poly, or a smaller one; None if nothing fits."""
    x0, x1, y0, y1 = bbox(poly)
    for scale in (1.0, 0.8, 0.6, 0.45, 0.3):
        ww, dd = w * scale, d * scale
        if ww > x1 - x0 or dd > y1 - y0:
            continue
        for _ in range(tries):
            x = rng.uniform(x0, x1 - ww)
            y = rng.uniform(y0, y1 - dd)
            pts = [(x, y), (x + ww, y), (x + ww, y + dd), (x, y + dd), (x + ww / 2, y + dd / 2),
                   (x + ww / 2, y), (x + ww / 2, y + dd), (x, y + dd / 2), (x + ww, y + dd / 2)]
            if all(point_in(px, py, poly) for px, py in pts):
                return x, y, ww, dd
    return None
