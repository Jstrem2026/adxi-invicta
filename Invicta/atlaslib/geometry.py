"""Plane geometry helpers for the app. Ship frame: x km from the prow tip toward the
stern, y km across the beam (port negative). Pure Python, no dependencies."""

import math

FRAME_KM = 0.5
LANES = "ABCDEFGHIJKLMNOPQRSTUVWXY"  # 25 lanes, 500 m wide, centred on (index-12)*0.5 km; M on the centreline

M_TO_FT = 3.28084
KM2_TO_SQMI = 1 / 2.589988
M2_TO_ACRES = 1 / 4046.8564224


def lane_centre_km(lane):
    return (LANES.index(lane.upper()) - 12) * 0.5


def lane_at(y_km):
    i = int(round(y_km / 0.5)) + 12
    return LANES[min(max(i, 0), len(LANES) - 1)]


def frame_at(x_km):
    """Nearest frame line (how canon addresses name a point, e.g. D5-F43-F)."""
    return int(round(x_km / FRAME_KM))


def address(deck, x_km, y_km):
    return "D%d-F%d-%s" % (deck, frame_at(x_km), lane_at(y_km))


def polygon_area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def centroid(pts):
    a = cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    if abs(a) < 1e-12:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    return (cx / (3 * a), cy / (3 * a))


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [min(xs), max(xs), min(ys), max(ys)]


def rect_poly(r):
    x0, x1, y0, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi:
            inside = not inside
        j = i
    return inside


def _is_ccw(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return a > 0


def clip(subject, window):
    """Sutherland-Hodgman: subject polygon clipped by a CONVEX window polygon."""
    if not subject or not window:
        return []
    win = list(window) if _is_ccw(window) else list(reversed(window))
    out = list(subject)
    for i in range(len(win)):
        ax, ay = win[i]
        bx, by = win[(i + 1) % len(win)]
        inp = out
        out = []
        if not inp:
            break

        def inside(p):
            return (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) >= -1e-12

        def inter(p, q):
            x1, y1 = p
            x2, y2 = q
            dx, dy = x2 - x1, y2 - y1
            den = (bx - ax) * dy - (by - ay) * dx
            if abs(den) < 1e-15:
                return q
            t = ((ax - x1) * (by - ay) - (ay - y1) * (bx - ax)) / -den
            return (x1 + t * dx, y1 + t * dy)

        s = inp[-1]
        for e in inp:
            if inside(e):
                if not inside(s):
                    out.append(inter(s, e))
                out.append(e)
            elif inside(s):
                out.append(inter(s, e))
            s = e
    return out


def circle_overlap_area(pts, cx, cy, r, step=0.01):
    """Area of polygon ∩ circle by sampling a step-km grid over their common box."""
    bx0, bx1, by0, by1 = bbox(pts)
    x0, x1 = max(bx0, cx - r), min(bx1, cx + r)
    y0, y1 = max(by0, cy - r), min(by1, cy + r)
    if x0 >= x1 or y0 >= y1:
        return 0.0
    n = 0
    y = y0 + step / 2
    while y < y1:
        x = x0 + step / 2
        while x < x1:
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and point_in_poly(x, y, pts):
                n += 1
            x += step
        y += step
    return n * step * step


def rect_overlap(a, b):
    w = min(a[1], b[1]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[2], b[2])
    return w * h if w > 0 and h > 0 else 0.0


def half_width_at(outline, x):
    best = 0.0
    n = len(outline)
    for i in range(n):
        x1, y1 = outline[i]
        x2, y2 = outline[(i + 1) % n]
        lo, hi = min(x1, x2), max(x1, x2)
        if lo <= x <= hi:
            if hi - lo < 1e-12:
                best = max(best, abs(y1), abs(y2))
            else:
                t = (x - x1) / (x2 - x1)
                best = max(best, abs(y1 + t * (y2 - y1)))
    return best


# ---- unit formatting (US first, metric in brackets) -------------------------------

def _n(v, d=0):
    return ("{:,.%df}" % d).format(v)


def fmt_len_m(m):
    ft = m * M_TO_FT
    if m >= 1600:
        return "%s mi (%s km)" % (_n(m / 1609.344, 2), _n(m / 1000, 2))
    return "%s ft (%s m)" % (_n(ft), _n(m, 0 if m >= 10 else 1))


def fmt_area_km2(a):
    if a >= 0.5:
        return "%s sq mi (%s km²)" % (_n(a * KM2_TO_SQMI, 2), _n(a, 2))
    return "%s acres (%s m²)" % (_n(a * 1e6 * M2_TO_ACRES, 1), _n(a * 1e6))
