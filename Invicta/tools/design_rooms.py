"""Design every building of a district down to its rooms, from the building's own outline and a written program.

    python tools/design_rooms.py D5/atrium-plaza            design every building that has no room plan yet
    python tools/design_rooms.py D5/atrium-plaza P2-04      just one building (redo it even if it has a plan)
    python tools/design_rooms.py D5/atrium-plaza --redo     redo every building this tool designed before
    python tools/design_rooms.py D5/atrium-plaza --dry      show what would be designed

Jordan, 27 Nov 2026: "For deck 5, scan all buildings down to each room. Put them all in the documentation.
I want to know what each room does."

The programs (what rooms each kind of building holds, what each room does, how tall each floor is, what
it looks like) are written by hand in tools/room_programs/, one file per district. This tool only does
the geometry and the bookkeeping:

  1. The building's outline (outline_km minus holes_km, or its box) is drawn onto a grid in metres
     from the lot's bow-port corner (x toward the stern, y toward starboard), the frame the plans use.
  2. "ring" buildings (offices, halls, homes): a band of wings runs round every outside edge and every
     courtyard, as deep as two rows of rooms and a corridor; what is left in the middle becomes the
     building's big rooms (chamber, atrium, sports hall, court) from the program.
     "hall" buildings (hangars, sheds, stores): the biggest piece is the hall, cut into bays, with a
     support wing along one side; other pieces become wings.
     "yard" and "park" lots: open zones in strips, with small buildings (offices, pavilions) in them.
  3. Wings get a corridor, stair-and-lift cores about every 70 m (235 ft), and rooms packed along both
     sides in the program's order; a "fill" room repeats to use the rest of the floor.
  4. Every room and zone gets "about": a plain sentence on what it does (shown in the room panel).
  5. Height, floors, structure, look, entrances, capacity, services and interior are written to the
     building; everything new is marked proposed (design_status), the building's own status is kept.

Plans go to data/models/<building uid>.json, the same format the 2D plan and 3D view read.
Variation: repeated buildings (Rack Hall 1 to 24) are varied from a seed made of the building's uid, so
the same building always comes out the same, but neighbours differ.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
import random
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
sys.path.insert(0, os.path.join(APP, "tools"))
import plan_geometry as G  # noqa: E402
sys.path.insert(0, APP)
from atlaslib import plan_repair  # noqa: E402
TODAY = "2026-11-27"
SOURCE_TAG = "tools/design_rooms.py"
FT = 3.28084


# ------------------------------------------------------------------ units

def ft(m):
    return "{:,}".format(int(round(m * FT)))


def both(m):
    v = round(m, 1)
    return "%s ft (%s m)" % (ft(m), ("%.1f" % v).rstrip("0").rstrip("."))


def sqft(m2):
    return "{:,} sq ft ({:,} m²)".format(int(round(m2 * 10.7639, -1)), int(round(m2)))


def r1(v):
    return round(v + 0.0, 1)


# ------------------------------------------------------------------ program helpers

def seed_for(uid):
    return int(hashlib.sha1(uid.encode()).hexdigest()[:12], 16)


def pick(rng, v):
    return rng.choice(v) if isinstance(v, (list, tuple)) else v


def expand_floors(spec, rng):
    """[(name, height, count or (lo, hi)[, "below"]), ...] -> levels [(id, name, z, h, group)]."""
    out, z, n, zb, nb = [], 0.0, 0, 0.0, 0
    for gi, g in enumerate(spec):
        if len(g) > 3 and g[3] == "below":
            cnt = g[2] if isinstance(g[2], int) else rng.randint(*g[2])
            for k in range(cnt):
                zb -= g[1]
                nb += 1
                out.append(("LB%d" % nb, g[0], r1(zb), g[1], gi))
    for gi, g in enumerate(spec):
        if len(g) > 3 and g[3] == "below":
            continue
        cnt = g[2] if isinstance(g[2], int) else rng.randint(*g[2])
        for k in range(cnt):
            n += 1
            nm = g[0] if cnt == 1 else "%s %d" % (g[0], k + 1)
            out.append(("L%d" % n, nm, r1(z), g[1], gi))
            z += g[1]
    return out


def expand_rooms(spec, rng, prog):
    """Program rows -> ([(name, m2, about)], fill). Row forms:
       ("Name", m2, "about")              one room
       ("Name", m2, "about", n)           n rooms
       ("Name", m2, "about", (lo, hi))    a random count
       ("?Name", m2, "about")             optional: kept about half the time
       ("*Name", m2, "about")             the fill room, repeated to use the rest of the floor
       ("|A|B", m2, "about")              one of several names
    """
    rooms, fill = [], None
    for row in spec:
        name, a, ab = row[0], row[1], row[2]
        n = row[3] if len(row) > 3 else 1
        if isinstance(n, tuple):
            n = rng.randint(*n)
        if name.startswith("?"):
            if rng.random() < 0.5:
                continue
            name = name[1:]
        if name.startswith("|"):
            name = rng.choice(name[1:].split("|"))
        if name.startswith("*|"):
            # several fill names: each becomes a fill, so the floor rotates between them
            fill = (fill or []) + [(nm, a, ab) for nm in name[2:].split("|")]
            continue
        if name.startswith("*"):
            fill = (fill or []) + [(name[1:], a, ab)]
            continue
        for k in range(n):
            rooms.append((name, a, ab))
    if fill is None:
        fill = [prog.get("fill", ("Offices", 120, "Offices for the people who work in the building."))]
    return rooms, fill


class Plan:
    def __init__(self, uid, lot):
        self.uid, self.lot, self.els = uid, lot, []

    def add(self, typ, name, poly, lvs, about=None, outdoor=False, full=False, parent=None):
        poly = G.rpoly(poly)
        if len(poly) < 3 or abs(G.area(poly)) < 1.0:
            return None
        e = {"id": "E%03d" % (len(self.els) + 1), "type": typ, "name": name}
        if len(lvs) == 1:
            e["level"] = lvs[0]
        else:
            e["levels"] = list(lvs)
        e["outline_m"] = poly
        if about:
            e["about"] = about
        if outdoor:
            e["outdoor"] = True
        if full and len(lvs) > 1:
            e["full_height"] = True
        if parent:
            e["parent"] = parent
        e["status"] = "proposed"
        self.els.append(e)
        return e


def poly_rect(x, y, w, d):
    return [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]


# ------------------------------------------------------------------ the building

def lot_geometry(b):
    r = b["rect_km"]
    Lx, Wy = (r[1] - r[0]) * 1000, (r[3] - r[2]) * 1000
    tr = lambda ring: [((p[0] - r[0]) * 1000, (p[1] - r[2]) * 1000) for p in ring]
    rings = [tr(o) for o in b.get("outline_km") or []] or [[(0, 0), (Lx, 0), (Lx, Wy), (0, Wy)]]
    holes = [tr(h) for h in b.get("holes_km") or []]
    return Lx, Wy, rings, holes


def design(b, uid, prog, rng):
    """Returns (fields, model)."""
    Lx, Wy, rings, holes = lot_geometry(b)
    plan = Plan(uid, (Lx, Wy))
    levels = expand_floors(prog["floors"], rng)
    ctx = {"name": b["name"], "rng": rng, "b": b, "foot": plan_repair.building_frame_shape(b)}
    mode = prog.get("mode", "ring")
    rings = [G.ccw(G.simplify(r, 0.8)) for r in rings]
    holes = [G.cw(G.simplify(h, 0.8)) for h in holes]
    stats = {"area": sum(abs(G.area(r)) for r in rings) - sum(abs(G.area(h)) for h in holes)}
    if mode == "hall" and holes:
        mode = "ring"
    for ri, ring in enumerate(rings):
        hs = [h for h in holes if G.point_in(h[0][0], h[0][1], ring)] if ri == 0 or len(rings) > 1 else []
        if mode in ("yard", "park"):
            layout_open(plan, ring, prog, levels, rng, ctx)
        elif mode == "hall":
            layout_hall(plan, ring, prog, levels, rng, ctx)
        else:
            layout_ring(plan, ring, hs, prog, levels, rng, ctx)
    top = max(l[2] + l[3] for l in levels)
    if prog.get("height_extra"):
        top += prog["height_extra"]
    model = {"schema": "invicta-atlas/model@1", "building_uid": uid, "units": "m",
             "frame": "Metres from the lot's bow-port corner: x toward the stern, y toward starboard, z above the deck.",
             "footprint_m": [r1(Lx), r1(Wy)], "grid_m": 10,
             "source": "Designed room by room for this building from its outline and its program in tools/room_programs, "
                       "laid out with %s, %s. All proposed." % (SOURCE_TAG, TODAY),
             "levels": [{"id": l[0], "name": ("Level B%s · %s" % (l[0][2:], l[1])) if l[0].startswith("LB") else "Level %s · %s" % (l[0][1:], l[1]),
                         "z_m": l[2], "height_m": l[3], "status": "proposed"} for l in levels],
             "elements": plan.els, "updated": TODAY}
    # trim overlaps, rooms past the walls and crossed outlines with exact maths (plan step 4)
    plan_repair.repair(model, b)
    plan.els = model["elements"]
    fields = text_fields(b, prog, levels, plan, rng, stats, top)
    return fields, model


def hall_levels(h, levels):
    above = [l for l in levels if l[2] >= 0]
    if h.get("outdoor"):
        return [above[0][0]]
    span = h.get("span", 1)
    return [l[0] for l in above] if span == "all" else [l[0] for l in above[:span]]


def level_groups(levels, hall_lvsets):
    """Split each floor group by which halls take part of it, so identical floors share one set of rooms."""
    out = {}
    for l in levels:
        sig = tuple(k for k, s in enumerate(hall_lvsets) if l[0] in s)
        out.setdefault((l[4], sig), []).append(l[0])
    return sorted(out.items(), key=lambda kv: (kv[0][0], kv[1][0]))


def rooms_for(prog, gi, ctx, rng):
    spec = prog["rooms"][gi] if gi < len(prog["rooms"]) else prog["rooms"][-1]
    if callable(spec):
        spec = spec(ctx)
    return expand_rooms(spec, rng, prog)


def layout_ring(plan, P, holes, prog, levels, rng, ctx):
    """Wings round every wall and courtyard; the middle holds the big rooms."""
    wing = pick(rng, prog.get("wing", 30))
    rd = prog.get("room_depth", 11.0)
    cor = prog.get("corridor", 3.0)
    halls = list(prog.get("halls", []))
    court = prog.get("court")
    A = abs(G.area(P)) - sum(abs(G.area(h)) for h in holes)
    if holes:
        # wings along the outside wall and along every courtyard wall, meeting in the middle
        # (as deep as the floor's usual half-width; where it is wider, the middle corridor widens)
        ir = G.inradius(P, holes=holes)
        per = sum(math.dist(r_[i], r_[(i + 1) % len(r_)]) for r_ in [P] + list(holes) for i in range(len(r_)))
        # back to back in the middle, as deep as the floor's usual half-width (the middle rooms are deeper where it is wider)
        rib = [(P, min(ir, A / per) * 0.999, False, holes)]
        inner = None
    else:
        ir = G.inradius(P)
        if ir <= wing + 6 or (not halls and not court):
            rib = [(P, ir * 0.999, True, [])]
            inner = None
        else:
            rib = [(P, wing, False, [])]
            inner = G.inset(P, wing)
    # halls in the middle, or (no middle) as full-depth pieces of the wings
    in_ribbon = []
    hall_pieces = []
    if inner and (halls or court):
        hs = halls[:] if halls else [court]
        shares = [h.get("share", 1.0) for h in hs]
        if court and halls and abs(G.area(inner)) > 6000 * len(halls):
            hs.append(court)
            shares.append(0.6)
        cap = prog.get("hall_max_m2")
        Ai = abs(G.area(inner))
        if cap and Ai > cap * 1.3:
            # a middle far bigger than its halls need: the halls keep their size, the rest is an open light court
            tot = sum(shares)
            shares = [min(s / tot * Ai, (h.get("max_m2") or cap)) for s, h in zip(shares, hs)]
            spare = Ai - sum(shares)
            if spare > 0.2 * Ai:
                c = court or LIGHT_COURT
                if c in hs:
                    shares[hs.index(c)] += spare
                else:
                    hs.append(c)
                    shares.append(spare)
        pieces = G.split_by_shares(inner, shares)
        hall_pieces = list(zip(hs, pieces))
    else:
        in_ribbon = [h for h in halls if not h.get("outdoor")]
    ribbons = []
    for ring, D, mid, hs_ in rib:
        r = G.Ribbon(ring, D, G.band_layers(D, rd, cor, two_sided_inner=mid), holes=hs_,
                     fill_to=G.inradius(ring, holes=hs_) if (mid or hs_) else None)
        if r.ok:
            ribbons.append(r)
    lv_ids = [l[0] for l in levels if l[2] >= 0]
    below_ids = [l[0] for l in levels if l[2] < 0]
    # hall-in-ribbon positions (full depth), on the main ribbon
    ribbon_halls = []
    if ribbons and in_ribbon:
        r0 = ribbons[0]
        lay0 = r0.layers[0]
        Ltot = r0.length(lay0[1], lay0[2])
        Dtot = r0.layers[-1][2]
        s = Ltot * rng.uniform(0.02, 0.2)
        for h in in_ribbon:
            want = h.get("ribbon_len") or min(Ltot * 0.3, max(30.0, h.get("m2", 0) / max(Dtot, 1), Ltot * 0.1))
            ribbon_halls.append((h, s, s + want))
            s += want + 8
    hall_lvsets = [set(hall_levels(h, levels)) for h, _ in hall_pieces] + [set(hall_levels(h, levels)) for h, _, _ in ribbon_halls]
    # ---- the big rooms
    for h, poly in hall_pieces:
        place_hall_poly(plan, poly, h, levels, rng)
    for h, s0, s1 in ribbon_halls:
        r0 = ribbons[0]
        D = r0.layers[-1][2]
        lay = r0.layers[0]
        k = r0.length(0.0, D) / r0.length(lay[1], lay[2])
        poly = r0.piece(0.0, D, s0 * k, s1 * k)
        place_hall_poly(plan, poly, h, levels, rng)
    # ---- cores, corridors and rooms
    core_every = prog.get("core_every", 70.0)
    core_len = prog.get("core_len", 8.0)
    cor_name, cor_about = prog.get("corridor_name", ("Corridor", "The corridor linking the rooms on this floor to the stairs and lifts."))
    cores_done = False
    for gkey, lvs in level_groups(levels, hall_lvsets):
        gi, sig = gkey
        rooms, fill = rooms_for(prog, gi, ctx, rng)
        if lvs[0].startswith("LB"):
            continue
        blocked = [(s0, s1) for k, (h, s0, s1) in enumerate(ribbon_halls) if (len(hall_pieces) + k) in sig]
        strips = []
        for ri, r in enumerate(ribbons):
            room_layers = [l for l in r.layers if l[0] == "rooms"]
            # cores sit in the innermost room layer, so they reach the corridor
            core_layer = room_layers[-1] if room_layers else None
            for kind, a, b in r.layers:
                L = r.length(a, b)
                lay0 = r.layers[0]
                scale = L / r.length(lay0[1], lay0[2])
                blk = [(s0 * scale, s1 * scale) for s0, s1 in blocked] if ri == 0 else []
                cores = []
                if core_layer and (kind, a, b) == core_layer and L > 30:
                    nc = max(1, int(round(L / core_every)))
                    for k in range(nc):
                        c0 = L * (k + 0.5) / nc - core_len / 2
                        if not any(s0 - 2 < c0 < s1 + 2 for s0, s1 in blk):
                            cores.append((c0, c0 + core_len))
                segs = free_segments(L, blk + cores)
                if kind == "corridor":
                    for s0, s1 in segs:
                        u = s0
                        while u < s1 - 0.5:
                            v = min(s1, u + 120.0)
                            plan.add("zone", cor_name, r.piece(a, b, u, v), lvs, cor_about)
                            u = v
                else:
                    for s0, s1 in segs:
                        strips.append((r, a, b, s0, s1))
                    if not cores_done:
                        for c0, c1 in cores:
                            plan.add("core", "Stairs and lifts", r.piece(a, b, c0, c1), below_ids + lv_ids, STAIRS_ABOUT)
        pack(plan, strips, rooms, fill, lvs, rng, fill_cap=prog.get("fill_cap", 24))
        cores_done = True
    basement(plan, P, holes, prog, levels, rng, ctx)


LIGHT_COURT = {"name": "Light court", "outdoor": True,
               "about": "An open court in the middle of the building that brings light and air to the inner rooms."}
STAIRS_ABOUT = "Stairs, lifts and service risers serving every floor; also the protected escape route in a fire."


def free_segments(L, blocked):
    segs, u = [], 0.0
    for a, b in sorted(blocked):
        a, b = max(0.0, a), min(L, b)
        if a - u > 1.0:
            segs.append((u, a))
        u = max(u, b)
    if L - u > 1.0:
        segs.append((u, L))
    return segs


FILL_GROW_MAX = 3.0   # a fill room grows at most this much; past it the floor gets more rooms


def pack(plan, strips, rooms, fill, lvs, rng, cap=400, fill_cap=24):
    """Pack rooms (name, m2, about) in order along the strips (ribbon layer pieces); then the fill room."""
    def depth(st):
        return st[2] - st[1]
    tot = sum((st[4] - st[3]) * depth(st) for st in strips)
    want = sum(r[1] for r in rooms)
    k = min(1.0, 0.92 * tot / want) if want else 1.0
    queue = [(n, a * k, ab) for n, a, ab in rooms]
    fills = list(fill or [])
    if fills:
        left = max(0.0, tot - want * k)
        avg = sum(f[1] for f in fills) / len(fills)
        n_fill = max(1, int(left / avg))
        if n_fill > fill_cap:
            g = min(left / fill_cap / avg, FILL_GROW_MAX)
            fills = [(f[0], f[1] * g, f[2]) for f in fills]
    fi = [0]

    def next_fill():
        f = fills[fi[0] % len(fills)]
        return f
    for st in strips:
        r, a, b, s0, s1 = st
        D = b - a
        u, last = s0, None
        while u < s1 - 0.5:
            if queue:
                n, ar, ab = queue[0]
            elif fills:
                n, ar, ab = next_fill()
            else:
                break
            ln = max(3.0, ar / D, 0.35 * D)
            if u + ln > s1 + 0.01:
                rem = s1 - u
                if rem < max(3.0, 0.45 * ln) and last is not None:
                    last["outline_m"] = G.rpoly(r.piece(a, b, last["_s0"], s1))
                    break
                ln = rem
            e = plan.add("room", n, r.piece(a, b, u, u + ln), lvs, ab)
            if e:
                e["_s0"] = u
                last = e
            if queue:
                queue.pop(0)
            elif fills:
                fi[0] += 1
            u += ln
    for e in plan.els:
        e.pop("_s0", None)
    return queue


def basement(plan, P, holes, prog, levels, rng, ctx):
    below = [l for l in levels if l[2] < 0]
    if not below:
        return
    gi = below[0][4]
    rooms, fill = rooms_for(prog, gi, ctx, rng)
    names = (rooms or []) + list(fill)
    pieces = G.split_by_shares(P, [1.0] * min(len(names), 4))
    for k, poly in enumerate(pieces):
        n, a, ab = names[k % len(names)]
        plan.add("room", n, poly, [l[0] for l in below], ab)


def place_hall_poly(plan, poly, h, levels, rng):
    lvs = hall_levels(h, levels)
    bays = h.get("bays")
    if bays and not h.get("outdoor"):
        ux, uy = G.long_axis(poly)
        lo, hi = G.proj_range(poly, ux, uy)
        bw = pick(rng, bays.get("width", 40))
        n = bays.get("count") or max(1, min(bays.get("max", 40), int(round((hi - lo) / bw))))
        names = bays.get("names")
        pieces = G.split_by_shares(poly, [1.0] * n, (ux, uy))
        for i, pc in enumerate(pieces):
            nm = names[i % len(names)] if names else "%s %d" % (bays["name"], i + 1)
            plan.add("room", nm, pc, lvs, bays["about"], full=True)
        host = None
    else:
        host = plan.add("zone" if h.get("outdoor") else "room", h["name"], poly, lvs, h["about"],
                        outdoor=h.get("outdoor", False), full=not h.get("outdoor"))
    if host:
        x0, x1, y0, y1 = G.bbox(poly)
        for sub in h.get("inside", []):
            fx, fy, fw, fd = sub.get("at", (0.3, 0.3, 0.4, 0.4))
            rect = poly_rect(x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, (x1 - x0) * fw, (y1 - y0) * fd)
            if all(G.point_in(x, y, poly) for x, y in rect):
                plan.add("fixture", sub["name"], rect, [lvs[0]], sub.get("about"), parent=host["id"])
    above = [l for l in levels if l[2] >= 0]
    rest = [l[0] for l in above if l[0] not in lvs]
    if rest and h.get("roof"):
        plan.add("zone", h["roof"][0], poly, [rest[0]], h["roof"][1], outdoor=True)
    elif rest and h.get("over"):
        plan.add("room", h["over"][0], poly, rest, h["over"][1])


def layout_hall(plan, P, prog, levels, rng, ctx):
    """A big hall cut into bays, with a support wing along one long wall."""
    sup = pick(rng, prog.get("support", 24))
    n = len(P)
    edges = sorted(range(n), key=lambda i: -math.dist(P[i], P[(i + 1) % n]))
    ei = edges[0] if rng.random() < 0.6 or len(edges) < 2 else edges[1]
    if prog.get("support_edge") in ("far_y", "near_y") and len(edges) > 1:
        # put the support wing on a chosen long side (far_y: away from the lot's y = 0 side, e.g. the hull)
        my = lambda i: (P[i][1] + P[(i + 1) % n][1]) / 2
        ei = (max if prog["support_edge"] == "far_y" else min)(edges[:2], key=my)
    (x1, y1), (x2, y2) = P[ei], P[(ei + 1) % n]
    ln = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / ln, (x2 - x1) / ln  # inward
    c0 = nx * x1 + ny * y1
    ir = G.inradius(P)
    halls = list(prog.get("halls", []))
    if ir * 2 < sup * 2.2:
        # too thin for a hall and a wing: all hall
        support_poly, hall_poly = None, P
    else:
        support_poly = G.clip_half(P, nx, ny, c0 + sup)
        hall_poly = G.clip_half(P, -nx, -ny, -(c0 + sup))
    indoor = [h for h in halls if not h.get("outdoor")]
    outdoor = [h for h in halls if h.get("outdoor")]
    hs = indoor + outdoor[:1]
    shares = [h.get("share", 1.0) for h in hs]
    # halls are cut along the support wing, so each one keeps a wall on the wing
    pieces = G.split_by_shares(hall_poly, shares, ((x2 - x1) / ln, (y2 - y1) / ln)) if len(hs) > 1 else [hall_poly]
    hall_lvsets = []
    for h, pc in zip(hs, pieces):
        place_hall_poly(plan, pc, h, levels, rng)
    if support_poly and abs(G.area(support_poly)) > 100:
        sp = G.ccw(support_poly)
        ir2 = G.inradius(sp)
        r = G.Ribbon(sp, ir2 * 0.999, G.band_layers(ir2 * 0.999, prog.get("room_depth", 9.0), prog.get("corridor", 3.0), True))
        lv_ids = [l[0] for l in levels if l[2] >= 0]
        below_ids = [l[0] for l in levels if l[2] < 0]
        if r.ok:
            cor_name, cor_about = prog.get("corridor_name", ("Corridor", "The corridor linking the rooms on this floor to the stairs and lifts."))
            core_every = prog.get("core_every", 70.0)
            first = True
            for gkey, lvs in level_groups(levels, []):
                gi, _ = gkey
                if lvs[0].startswith("LB"):
                    continue
                rooms, fill = rooms_for(prog, gi, ctx, rng)
                strips = []
                for kind, a, b in r.layers:
                    L = r.length(a, b)
                    cores = []
                    if kind == "rooms" and (kind, a, b) == [l for l in r.layers if l[0] == "rooms"][-1] and L > 40:
                        nc = max(1, int(round(L / core_every)))
                        cores = [(L * (k + 0.5) / nc - 4, L * (k + 0.5) / nc + 4) for k in range(nc)]
                    segs = free_segments(L, cores)
                    if kind == "corridor":
                        for s0, s1 in segs:
                            plan.add("zone", cor_name, r.piece(a, b, s0, s1), lvs, cor_about)
                    else:
                        strips += [(r, a, b, s0, s1) for s0, s1 in segs]
                        if first:
                            for c0_, c1_ in cores:
                                plan.add("core", "Stairs and lifts", r.piece(a, b, c0_, c1_), below_ids + lv_ids, STAIRS_ABOUT)
                first = False
                pack(plan, strips, rooms, fill, lvs, rng, fill_cap=prog.get("fill_cap", 16))
    basement(plan, P, [], prog, levels, rng, ctx)


def layout_open(plan, P, prog, levels, rng, ctx):
    """Yards, parks and squares: open zones in strips across the lot, with small buildings and fixtures."""
    lx_, ly_ = G.long_axis(P)
    ctx["ring_len"] = (lambda r: r[1] - r[0])(G.proj_range(P, lx_, ly_))  # this piece's length, for rows of bays
    zones = prog["zones"](ctx) if callable(prog["zones"]) else list(prog["zones"])
    zones = [z for z in zones if not (z[0].startswith("?") and rng.random() < 0.5)]
    zones = [(z[0].lstrip("?"),) + tuple(z[1:]) for z in zones]
    if prog.get("shuffle_zones"):
        head, tail = zones[:1], zones[1:]
        rng.shuffle(tail)
        zones = head + tail
    L1 = levels[0][0]
    up = [l[0] for l in levels if l[2] >= 0]
    ax = None
    if prog.get("split") == "across":   # side by side along the short axis (berths, lanes)
        lx, ly = G.long_axis(P)
        ax = (ly, lx)
    pieces = G.split_by_shares(P, [z[1] for z in zones], axis=ax)
    for z, poly in zip(zones, pieces):
        name, share, about = z[0], z[1], z[2]
        opts = z[5] if len(z) > 5 else {}
        if opts.get("covered"):   # a roofed bay in a row (gate shed, hangar bay): a full-height room
            e = plan.add("room", name, poly, up, about, full=True)
        else:
            e = plan.add("zone", name, poly, [L1], about, outdoor=True)
        if not e:
            continue
        for bld in (z[3] if len(z) > 3 else []):
            fr = G.fit_rect(poly, bld["size"][0], bld["size"][1], rng, within=ctx.get("foot"))
            if not fr:
                continue
            bx, by, bw, bd = fr
            lvs = up[:bld.get("floors", 1)]
            rooms = bld["rooms"]
            tot_a = sum(r[1] for r in rooms)
            v = 0.0
            for rn, ra, rab in rooms:
                if bw >= bd:
                    lw = bw * ra / tot_a
                    plan.add("room", rn, poly_rect(bx + v, by, lw, bd), lvs, rab)
                else:
                    lw = bd * ra / tot_a
                    plan.add("room", rn, poly_rect(bx, by + v, bw, lw), lvs, rab)
                v += lw
        x0, x1, y0, y1 = G.bbox(poly)
        for fx in (z[4] if len(z) > 4 else []):
            a, b_, cw, cd = fx[2]
            rect = poly_rect(x0 + (x1 - x0) * a, y0 + (y1 - y0) * b_, (x1 - x0) * cw, (y1 - y0) * cd)
            if all(G.point_in(x, y, poly) for x, y in rect):
                plan.add("fixture", fx[0], rect, [L1], fx[1], parent=e["id"])
            else:
                fr = G.fit_rect(poly, (x1 - x0) * cw, (y1 - y0) * cd, rng, within=ctx.get("foot"))
                if fr:
                    plan.add("fixture", fx[0], poly_rect(*fr), [L1], fx[1], parent=e["id"])



# ------------------------------------------------------------------ text

def level_ranges(ids):
    if len(ids) == 1:
        return ids[0]
    return "%s–%s" % (ids[0], ids[-1])


def interior_text(plan, levels, prog):
    by_lv = {}
    for e in plan.els:
        if e["type"] not in ("room", "zone") or e["name"] in ("Corridor",):
            continue
        for lv in e.get("levels") or [e.get("level")]:
            by_lv.setdefault(lv, [])
            if e["name"] not in by_lv[lv]:
                by_lv[lv].append(e["name"])
    parts, seen = [], {}
    for l in levels:
        names = tuple(by_lv.get(l[0], []))
        seen.setdefault(names, []).append(l)
    for names, ls in seen.items():
        if not names:
            continue
        lab = ls[0][1] if len(ls) == 1 else "%s to %s" % (ls[0][1], ls[-1][1])
        tag = ls[0][0] if len(ls) == 1 else "%s–%s" % (ls[0][0], ls[-1][0])
        nm = [n for n in names if not n.startswith("Stairs")]
        cor = prog.get("corridor_name", ("Corridor",))[0]
        nm = [n for n in nm if n != cor]
        shown = nm[:9]
        more = len(nm) - len(shown)
        parts.append("%s (%s): %s%s." % (lab, tag, ", ".join(shown).lower().capitalize() if shown else "",
                                       " and %d more rooms" % more if more > 0 else ""))
    return " ".join(parts)


def text_fields(b, prog, levels, plan, rng, stats, top):
    above = [l for l in levels if l[2] >= 0]
    below = [l for l in levels if l[2] < 0]
    floor_area = 0.0
    n_rooms = 0
    for e in plan.els:
        if e["type"] == "room":
            a = abs(G.area(e["outline_m"]))
            n = len(e.get("levels") or [1]) if not e.get("full_height") else 1
            floor_area += a * n
            n_rooms += n
    ctx = {"name": b["name"], "floors": len(above), "height": both(top), "area": sqft(floor_area),
           "foot": sqft(stats["area"]), "rooms": n_rooms}
    staff_per = prog.get("m2_per_person", 25)
    ctx["people"] = "{:,}".format(int(round(floor_area / staff_per, -1 if floor_area / staff_per > 100 else 0)))
    fmt = lambda v: pick(rng, v).format(**ctx) if v else None
    f = {
        "height_m": r1(top),
        "floors": "%d above deck%s" % (len(above), ", %d below" % len(below) if below else ""),
        "structure": fmt(prog.get("structure")),
        "look": fmt(prog.get("look")),
        "entrances": fmt(prog.get("entrances")),
        "capacity": fmt(prog.get("capacity")),
        "services": fmt(prog.get("services")),
        "interior": interior_text(plan, levels, prog),
        "design_status": "proposed",
        "floor_area_m2": int(round(floor_area)),
    }
    if prog.get("floors_text"):
        f["floors"] = fmt(prog["floors_text"])
    return f


# ------------------------------------------------------------------ driver

def load_programs(district):
    mod = importlib.import_module("room_programs." + district.replace("-", "_"))
    return mod.PROGRAMS


def find_program(progs, b):
    for key, prog in progs:
        if re.search(key, b["name"]):
            return prog
    return None


def dump_like(raw, data):
    """Write the data file back in the same layout it was read in (compact one-line files stay compact)."""
    m = re.match(r'\{\n( +)"', raw)
    if m:
        txt = json.dumps(data, ensure_ascii=False, indent=len(m.group(1)))
    elif raw.startswith('{"schema": '):
        txt = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))
    else:
        txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return txt + ("\n" if raw.endswith("\n") else "")


KEEP_TEXT = ("structure", "look", "entrances", "services")


def model_path(uid):
    return os.path.join(DATA, "models", uid + ".json")


def ours(uid):
    p = model_path(uid)
    return os.path.isfile(p) and SOURCE_TAG in open(p, encoding="utf-8").read(600)


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("only", nargs="?")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    path = os.path.join(DATA, "decks", *a.file.split("/")) + ".json"
    raw = open(path, encoding="utf-8").read()
    data = json.loads(raw)
    slug = os.path.basename(a.file)
    did = "D%s-%s" % (data["deck"], slug)
    progs = load_programs(slug)
    done, missing = 0, []
    for p in data["precincts"]:
        for b in p["buildings"]:
            uid = "%s-%s" % (did, b["id"])
            if a.only and b["id"] != a.only:
                continue
            if b["kind"] == "transport" and not find_program(progs, b):
                continue
            if os.path.isfile(model_path(uid)) and not (a.only or (a.redo and ours(uid))):
                continue
            prog = find_program(progs, b)
            if not prog:
                missing.append("%s %s" % (b["id"], b["name"]))
                continue
            if a.dry:
                print("  would design %s %s" % (b["id"], b["name"]))
                continue
            rng = random.Random(seed_for(uid))
            fields, model = design(b, uid, prog, rng)
            for k, v in fields.items():
                if k in KEEP_TEXT and b.get(k) and b.get("design_status") == "proposed":
                    continue   # a redo keeps the building's description; only the numbers and room lists follow the plan
                if v is not None:
                    b[k] = v
            with open(model_path(uid), "w", encoding="utf-8", newline="\n") as f:
                json.dump(model, f, ensure_ascii=False, indent=1)
                f.write("\n")
            done += 1
            nrooms = sum(1 for e in model["elements"] if e["type"] == "room")
            print("  %-6s %-34s %6.1f m %2d levels %4d rooms" % (b["id"], b["name"][:34], fields["height_m"], len(model["levels"]), nrooms))
    if not a.dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(dump_like(raw, data))
    print("%d building(s) designed." % done)
    if missing:
        print("No program for %d: %s" % (len(missing), "; ".join(missing)))


if __name__ == "__main__":
    main()
