"""Polygon helpers for tools/design_rooms.py: wings that follow every wall of a building (straight, slanted or
curved), bands of rooms along them, and cutting halls and yards into pieces. Metres.

Plan step 4 (27 Nov 2026): the bands (Ribbon), the inset for the middle of a building and the inradius use exact
offsets from Shapely. The old hand-made offsets dropped corners of curved outlines, so whole wings cut across
buildings, and they ignored courtyard walls. Now the bands follow every wall, the outside and each courtyard.
"""
import math
import os
import sys

import shapely
from shapely.geometry import LineString as _Line, Polygon as _Poly
from shapely.geometry.polygon import orient as _orient
from shapely.ops import substring as _substring

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


# ------------------------------------------------------------------ exact offsets (Shapely)

def _region(P, holes=()):
    """The floor of a ring with its courtyards, as one valid polygon (the biggest part if it falls apart)."""
    if len(P) < 3:
        return _Poly()
    g = _Poly([tuple(q[:2]) for q in P], [[tuple(q[:2]) for q in h] for h in holes if len(h) >= 3])
    if not g.is_valid:
        g = shapely.make_valid(g)
    parts = [p for p in shapely.get_parts(g) if p.geom_type == "Polygon" and not p.is_empty]
    return max(parts, key=lambda p: p.area) if parts else _Poly()


def _parts(g):
    return [p for p in shapely.get_parts(g) if p.geom_type == "Polygon" and not p.is_empty]


def _offset(g, d):
    """g moved inward by d (exact; square corners stay square)."""
    if d <= 0:
        return g
    return g.buffer(-d, join_style="mitre", mitre_limit=5.0)


def inset(P, d, holes=()):
    """Ring P moved inward by d as a counter-clockwise point list (the biggest part), or None if nothing is left."""
    parts = _parts(_offset(_region(P, holes), d))
    if not parts:
        return None
    p = max(parts, key=lambda q: q.area)
    if p.area <= 1.0:
        return None
    return [(x, y) for x, y in _orient(p, 1.0).exterior.coords[:-1]]


def offset_ok(P, d):
    """P if it can be moved inward by d and still be a floor, else None."""
    return P if inset(P, d) else None


def inradius(P, hi=None, holes=()):
    """How far the deepest point of the floor is from its nearest wall (radius of the biggest circle inside)."""
    g = _region(P, holes)
    if g.is_empty:
        return 0.0
    r = shapely.maximum_inscribed_circle(g, 0.05).length
    return min(r, hi) if hi else r


# ------------------------------------------------------------------ a ribbon of bands along every wall

EXTEND_MAX = 6.0   # m


class Ribbon:
    """Bands of rooms and corridors following the walls of a floor inward: the outside wall and, when holes are
    given, every courtyard wall too. layers: [(kind, d0, d1)], kind 'rooms' or 'corridor', d0 and d1 the band's
    distance from the wall. Positions along the ribbon are metres along each layer's middle line, from the start of
    the outside wall, then round each courtyard in turn. A piece is the part of its band between two positions, cut
    square to the middle line, so neighbouring pieces share their cut and no piece leaves its band."""

    def __init__(self, P, depth_total, layers, holes=(), fill_to=None):
        """fill_to: the last layer reaches this deep where the floor is wider than depth_total, so a building
        whose width varies has no empty strip down its middle (its innermost corridor gets wider there)."""
        self.region = _region(ccw(P), holes)
        self.layers = layers
        self._buf, self._mid = {}, {}
        self._deep = {}
        if fill_to and layers and fill_to > layers[-1][2]:
            self._deep[(round(layers[-1][1], 6), round(layers[-1][2], 6))] = fill_to
        self.ok = bool(layers) and depth_total > 0 and not self.region.is_empty and self.length(layers[0][1], layers[0][2]) > 1.0

    def _offset(self, d):
        d = round(d, 6)
        if d not in self._buf:
            self._buf[d] = _offset(self.region, d)
        return self._buf[d]

    def _middle(self, a, b):
        key = (round(a, 6), round(b, 6))
        if key not in self._mid:
            rings = []
            for p in sorted(_parts(self._offset((a + b) / 2)), key=lambda q: -q.area):
                p = _orient(p, 1.0)
                rings.append(_Line(p.exterior.coords))
                rings += [_Line(h.coords) for h in p.interiors]
            rings = [r for r in rings if r.length > 1.0]
            cum = [0.0]
            for r in rings:
                cum.append(cum[-1] + r.length)
            deep = self._deep.get(key, b)
            band = self._offset(a).difference(self._offset(deep)) if b > a else _Poly()
            shapely.prepare(band)
            # a piece reaches across its band (and, for the deepened last layer, up to EXTEND_MAX further in;
            # reaching further would cross the middle of the floor into the bands from the opposite wall)
            self._mid[key] = (rings, cum, band, min(max((b - a) / 2, deep - (a + b) / 2), (b - a) / 2 + EXTEND_MAX) + 0.05)
        return self._mid[key]

    def length(self, a, b):
        return self._middle(a, b)[1][-1]

    def piece(self, a, b, s0, s1):
        """Polygon of layer (a, b) between positions s0 and s1 (an empty list if nothing is there)."""
        rings, cum, band, half = self._middle(a, b)
        geoms = []
        for k, r in enumerate(rings):
            lo, hi = max(s0, cum[k]), min(s1, cum[k + 1])
            if hi - lo < 0.05:
                continue
            seg = _substring(r, lo - cum[k], hi - cum[k])
            geoms.append(seg.buffer(half, cap_style="flat", join_style="mitre", mitre_limit=5.0))
        if not geoms:
            return []
        g = shapely.union_all(geoms)
        g = g.intersection(shapely.clip_by_rect(band, *g.bounds))
        parts = _parts(g)
        if not parts:
            return []
        p = max(parts, key=lambda q: q.area)
        return rpoly([(x, y) for x, y in _orient(p, 1.0).exterior.coords[:-1]])


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


def fit_rect(poly, w, d, rng, tries=40, within=None):
    """A w x d rectangle (axis-aligned) fully inside poly (and inside the Shapely shape `within`, the building's
    real footprint, when given), or a smaller one; None if nothing fits."""
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
            if all(point_in(px, py, poly) for px, py in pts) and (
                    within is None or within.covers(shapely.box(x, y, x + ww, y + dd))):
                return x, y, ww, dd
    return None
