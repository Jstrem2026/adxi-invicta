"""Build the app model (ship > deck > district > precinct > block > building)
fresh from the source files every time it is asked. Nothing is cached on disk,
so whatever the docs and data files say right now is what the app shows."""

import json
import math
import os
import re
import time

from . import geometry as G
from . import footprints as FP
from .categories import categorize, KEYS as CATEGORY_KEYS, legend as category_legend
from . import parsers as P
from .sources import CANON, DECK_NAMES, FIXED, MIRROR_DOCS, GAME_DOCS, deck_paths, Root

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("’", "")).strip("-")


class Loader:
    def __init__(self, root):
        self.r = Root(root)
        self.problems = []  # data failures found while loading: (severity, title, detail, path)
        self.used = {}      # rel path -> role, for the Sources list

    # -------------------------------------------------------------- helpers
    def fail(self, sev, title, detail, path=None, entity=None):
        self.problems.append({"severity": sev, "category": "data", "title": title, "detail": detail,
                              "path": path, "entity": entity})

    def text(self, rel, role, required=True):
        self.used[rel] = role
        if not self.r.exists(rel):
            if required:
                self.fail("error", "Missing source file", "%s is not where the app expects it." % rel, rel)
            return None
        try:
            return self.r.read(rel)
        except UnicodeDecodeError as e:
            self.fail("error", "Unreadable source file", "%s is not UTF-8 text (%s)." % (rel, e), rel)
        except OSError as e:
            self.fail("error", "Unreadable source file", "%s: %s" % (rel, e), rel)
        return None

    def outline(self, rel, role, required=True):
        t = self.text(rel, role, required)
        if t is None:
            return None
        try:
            return P.outline_csv(t)
        except P.ParseError as e:
            self.fail("error", "Bad outline CSV", "%s: %s." % (rel, e), rel)
            return None

    # -------------------------------------------------------------- ship
    def ship(self):
        out = {"name": "Luxuria Invicta", "sheet": FIXED["ship_sheet"]}
        t = self.text(FIXED["ship_sheet"], "Canon ship data sheet (S0)")
        if t:
            out["meta"] = P.sheet_meta(t)
            tabs = P.html_tables(t)
            for tb in tabs:
                h = tb[0][0]
                if h == "Dimension":
                    out["dimensions"] = [{"item": r[0], "value": r[1], "basis": r[2] if len(r) > 2 else ""} for r in tb[1:]]
                elif h == "Deck":
                    out["deck_table"] = {"header": tb[0], "rows": tb[1:]}
                elif h == "Item":
                    out["structure"] = [{"item": r[0], "value": r[1]} for r in tb[1:]]
                elif h == "Level":
                    out["elevations"] = [{"level": r[0], "range": r[1], "deck": r[2]} for r in tb[1:]]
                elif h == "Mass item":
                    out["mass"] = [{"item": r[0], "value": r[1]} for r in tb[1:]]
                elif h == "Volume item":
                    out["volume"] = [{"item": r[0], "value": r[1], "note": r[2] if len(r) > 2 else ""} for r in tb[1:]]
            sec = P.html_sections(t)
            out["consistency_note"] = next((v for k, v in sec.items() if "CONSISTENCY" in k.upper()), "")
        out["hull_plan"] = self.outline(FIXED["hull_plan_csv"], "Canon hull plan (top view)")
        side = self.outline(FIXED["hull_side_revB_csv"], "Rev B hull side profile")
        out["hull_side"] = side
        self.outline(FIXED["hull_side_csv"], "Canon hull side profile (Rev A)")
        # Rev C concept hull (proposed 28 Nov 2026): traced from Jordan's six-view concept sheet,
        # never smaller than the hull above, so the decks are unchanged.
        out["hull_plan_concept"] = self.outline(FIXED["hull_plan_revC_csv"], "Rev C concept hull plan (top view)", required=False)
        out["hull_side_concept"] = self.outline(FIXED["hull_side_revC_csv"], "Rev C concept hull side profile", required=False)
        out["concept_sheet"] = FIXED["concept_sheet"]
        out["revC_readme"] = FIXED["revC_readme"]
        ft = self.text(FIXED["frames_csv"], "Canon frame table F0-F68")
        if ft:
            try:
                out["frames"] = P.dict_csv(ft)
            except Exception as e:  # noqa
                self.fail("error", "Bad frame table", str(e), FIXED["frames_csv"])
        return out

    # -------------------------------------------------------------- game constants
    def game_constants(self):
        t = self.text(FIXED["game_geometry_py"], "Game geometry module (Unreal graybox)")
        if not t:
            return {}
        try:
            return P.py_constants(t, {"DECKS", "AERION_KEELWAY_STOPS", "ARRIVAL", "FRAME_SPACING_KM", "LANES",
                                      "KEELWAY_SPEED_KMH", "SHIP_CENTRE_X_KM", "SHIP_CENTRE_Z_KM"})
        except SyntaxError as e:
            self.fail("error", "Game geometry module does not parse", str(e), FIXED["game_geometry_py"])
            return {}

    # -------------------------------------------------------------- decks
    def deck(self, n, precinct_sets, rules):
        dp = deck_paths(n)
        name = DECK_NAMES[n]
        d = {"n": n, "name": name, "id": "D%d" % n, "paths": dp, "districts": [], "keelway": [], "crossline": [],
             "systems": [], "drones": "", "key": {}}
        t = self.text(dp["sheet"], "Canon deck data sheet S%d" % n)
        net_rb = self.outline(dp["net_revB"], "Rev B net city floor outline, deck %d" % n)
        d["outline_net"] = net_rb or self.outline(dp["net_canon"], "Canon net outline, deck %d" % n)
        d["outline_gross"] = self.outline(dp["gross_revB"], "Rev B gross outline, deck %d" % n, required=False) or \
            self.outline(dp["gross_canon"], "Canon gross outline, deck %d" % n)
        d["outline_net_canon"] = self.outline(dp["net_canon"], "Canon net outline, deck %d" % n)
        d["outline_source"] = dp["net_revB"] if net_rb else dp["net_canon"]
        d["net_area_calc"] = round(G.polygon_area(d["outline_net"]), 2) if d["outline_net"] else None
        for k in ("render", "emblem", "sheet_pdf"):
            self.used[dp[k]] = "Deck %d %s" % (n, k)
            d["has_" + k] = self.r.exists(dp[k])
        art = "%s/art/emblems/d%d.png" % (GAME_DOCS, n)   # Jordan's full-size deck city emblem (27 Nov 2026)
        if self.r.exists(art):
            self.used[art] = "Deck %d emblem (full size)" % n
            d["emblem_art"] = art
        d["emblem_web"] = "emblems/d%d.webp" % n if os.path.isfile(os.path.join(APP_DIR, "web", "emblems", "d%d.webp" % n)) else None
        if not t:
            return d
        d["meta"] = P.sheet_meta(t)
        tabs = P.html_tables(t)
        for tb in tabs:
            h = tb[0]
            if h[0] == "Item":
                d["key"] = P.kv(tb)
            elif h[0] == "District":
                for r in tb[1:]:
                    if r[0] == "Total":
                        d["district_total"] = {"area": P.num(r[1]), "people": P.num(r[3])}
                        continue
                    nm = re.sub(r"\s*\(plaza\)\s*$", "", r[0])
                    d["districts"].append({
                        "id": "D%d-%s" % (n, slug(nm)), "name": nm, "is_plaza": "(plaza)" in r[0],
                        "area_km2": P.num(r[1]), "share": r[2], "people": P.num(r[3]), "per_km2": P.num(r[4]),
                        "what": r[5], "centre": r[6], "workers": r[7] if len(r) > 7 else ""})
            elif h[0] == "Stop" and "From deck bow" in h:
                d["keelway"] = [{"stop": r[0], "frame": r[1], "from_bow": r[2], "address": r[3]} for r in tb[1:]]
            elif h[0] == "Stop":
                d["crossline"] = [{"stop": r[0], "frame": r[1], "offset": r[2], "address": r[3]} for r in tb[1:]]
            elif h[0] == "Peacetime load":
                d["systems"] = [{"load": r[0], "draw": r[1]} for r in tb[1:]]
        sec = P.html_sections(t)
        d["drones"] = next((v for k, v in sec.items() if "DRONES" in k.upper()), "")
        d["summary"] = ""
        m = re.search(r"</h1>\s*<p[^>]*>(.*?)</p>", t, flags=re.S)
        if m:
            d["summary"] = P._cell_text(m.group(1))
        key = d["key"]
        d["title"] = key.get("Name", "Deck %d · %s" % (n, name))
        d["role"] = key.get("Role", "")
        d["landmark"] = key.get("Landmark", "")
        d["governor"] = key.get("Governor", "")
        fc = P.nums(key.get("Floor / ceiling elevation", ""))
        d["floor_m"], d["ceiling_m"] = (fc[0], fc[1]) if len(fc) >= 2 else (None, None)
        d["clear_m"] = P.num(key.get("Clear height"))
        d["net_area_stated"] = P.num(key.get("Net floor area"))
        d["population"] = P.num(key.get("Design population"))
        # district shapes from the plan drawing
        try:
            plan = P.plan_districts(t)
        except P.ParseError as e:
            self.fail("error", "Deck plan drawing could not be read", "Sheet S%d: %s." % (n, e), dp["sheet"], "D%d" % n)
            plan = None
        if plan:
            cx, cy, rr = plan["plaza_circle"]
            # Match districts to shapes: a shape holding exactly one district label takes
            # that district; the rest go by closest area (the label may sit in a neighbour).
            info = []
            for poly in plan["polygons"]:
                labs = [l[2].upper() for l in plan["labels"] if G.point_in_poly(l[0], l[1], poly) and "·" not in l[2]]
                info.append({"poly": poly, "labels": labs,
                             "net": G.polygon_area(poly) - G.circle_overlap_area(poly, cx, cy, rr, 0.02)})
            free = list(info)
            pending = []
            for dist in d["districts"]:
                if dist["is_plaza"]:
                    dist["circle_km"] = [cx, cy, rr]
                    dist["area_calc"] = round(math.pi * rr * rr, 2)
                    continue
                want = dist["name"].upper()
                if not any(l[2].upper() == want for l in plan["labels"]):
                    dist["plan_note"] = "no label on the plan"
                hit = next((x for x in free if x["labels"] == [want]), None)
                if hit:
                    free.remove(hit)
                    dist["polygon_km"] = hit["poly"]
                    dist["area_calc"] = round(hit["net"], 2)
                else:
                    pending.append(dist)
            for dist in pending:
                if not free:
                    break
                hit = min(free, key=lambda x: abs(x["net"] - (dist["area_km2"] or 0)))
                free.remove(hit)
                dist["polygon_km"] = hit["poly"]
                dist["area_calc"] = round(hit["net"], 2)
                if dist.get("plan_note") is None:
                    holder = [x for x in info if dist["name"].upper() in x["labels"]]
                    dist["plan_note"] = "label drawn inside another district's shape" if holder and holder[0] is not hit else "matched by area"
            for dist in d["districts"]:
                if not dist["is_plaza"] and "polygon_km" not in dist:
                    self.fail("warning", "District has no shape on the plan",
                              "Sheet S%d lists %s but no area of its plan drawing could be matched to it." % (n, dist["name"]),
                              dp["sheet"], dist["id"])
        # Revision B overrides (errata) and precinct sets
        for dist in d["districts"]:
            ov = rules.get("revB_overrides", {}).get(dist["id"])
            if ov:
                dist["revB"] = ov
            ps = precinct_sets.get(dist["id"])
            dist["precinct_set"] = ps["file"] if ps else None
            dist["design_status"] = ps["status"] if ps else ("canon (plaza)" if dist["is_plaza"] else "not designed yet")
        # zone reservation CSV (Rev A placement)
        return d

    # -------------------------------------------------------------- crown bridge
    def crown(self):
        t = self.text(FIXED["crown_sheet"], "Canon Crown Bridge data sheet")
        out = {"sheet": FIXED["crown_sheet"], "key": {}, "levels": []}
        art = "%s/art/emblems/bridge.png" % GAME_DOCS
        if self.r.exists(art):
            self.used[art] = "Bridge emblem (full size)"
            out["emblem_art"] = art
        out["emblem_web"] = "emblems/bridge.webp" if os.path.isfile(os.path.join(APP_DIR, "web", "emblems", "bridge.webp")) else None
        if not t:
            return out
        out["meta"] = P.sheet_meta(t)
        for tb in P.html_tables(t):
            if tb[0][0] == "Item":
                out["key"] = P.kv(tb)
            elif tb[0][0] == "Level":
                out["levels"] = [dict(zip(["level", "name", "function", "footprint", "area", "height"], r)) for r in tb[1:]]
        return out

    # -------------------------------------------------------------- precinct sets (app data)
    def precinct_sets(self):
        sets = {}
        for p in sorted(_glob(os.path.join(DATA_DIR, "decks"), ".json")):
            rel = "Invicta/data/" + os.path.relpath(p, DATA_DIR).replace(os.sep, "/")
            self.used[rel] = "App design data (precincts, buildings)"
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError) as e:
                self.fail("error", "App data file does not load", "%s: %s" % (rel, e), rel)
                continue
            missing = [k for k in ("deck", "district", "precincts") if k not in data]
            if missing:
                self.fail("error", "App data file is missing fields", "%s lacks %s." % (rel, ", ".join(missing)), rel)
                continue
            did = "D%d-%s" % (data["deck"], slug(data["district"]))
            data["file"] = rel
            data["district_id"] = did
            sets[did] = data
        return sets

    def build_precincts(self, pset, deck):
        outline = deck.get("outline_net")
        n = deck["n"]
        for p in pset["precincts"]:
            p["deck"] = n
            p["uid"] = "D%d-%s-%s" % (n, slug(pset["district"]), p["id"])
            poly = [tuple(q) for q in (p.get("polygon_km") or G.rect_poly(p["bounds_km"]))]
            shape = G.clip(outline, poly) if outline else poly
            excl = p.get("exclude_circles_km", [])
            area = G.polygon_area(shape) - sum(G.circle_overlap_area(shape, c[0], c[1], c[2], 0.01) for c in excl)
            p["shape_km"] = [list(q) for q in shape]
            p["area_calc"] = round(area, 2)
            bx = G.bbox(shape) if shape else p["bounds_km"]
            p["bbox_km"] = bx
            # blocks: start from the 500 m frame x lane grid, but a grid line only becomes a
            # block edge where it crosses no building. Blocks never cut through a building.
            blocks = make_blocks(n, shape, bx, p["buildings"], excl, p.get("streets", []))
            # buildings
            for b in p["buildings"]:
                b["uid"] = "%s-%s" % (p["uid"].rsplit("-", 1)[0], b["id"])
                if b.get("category") not in CATEGORY_KEYS:
                    if b.get("category"):
                        b["category_bad"] = b["category"]   # the scan reports it
                    b["category"] = categorize(b)
                    b["category_auto"] = True   # worked out from the name: not stored in the data file yet
                r = b.get("rect_km")
                if r:
                    cxy = ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)
                    b["address"] = G.address(n, *cxy)
                    shapes = b.get("bays_km") or [r]
                    b["footprint_km2"] = round(FP.footprint_area(b), 4)
                    box_km2 = sum((s[1] - s[0]) * (s[3] - s[2]) for s in shapes)
                    b["blocks"] = []
                    for blk in blocks:
                        ov = sum(G.rect_overlap(s, blk["cell_km"]) for s in shapes)
                        if ov > 1e-7:
                            b["blocks"].append(blk["id"])
                            ct = {"id": b["id"], "share": round(ov / max(box_km2, 1e-9), 3)}
                            if b.get("bays_km"):
                                ct["parts"] = sum(1 for s in b["bays_km"] if G.rect_overlap(s, blk["cell_km"]) > 0.999 * (s[1] - s[0]) * (s[3] - s[2]))
                                ct["of"] = len(b["bays_km"])
                            blk["contents"].append(ct)
                    b["block"] = b["blocks"][0] if len(b["blocks"]) == 1 else None
                    if b.get("bays_km"):
                        b["bay_label"] = bay_label(b)
            for st in p.get("streets", []):
                st["blocks"] = [blk["id"] for blk in blocks if G.rect_overlap(st["rect_km"], blk["cell_km"]) > 1e-8]
            p["blocks"] = blocks
        return pset

    # -------------------------------------------------------------- everything
    def model(self):
        t0 = time.time()
        rules = load_rules()
        ship = self.ship()
        game = self.game_constants()
        psets = self.precinct_sets()
        decks = [self.deck(n, psets, rules) for n in range(1, 9)]
        for did, ps in psets.items():
            deck = next((d for d in decks if d["n"] == ps["deck"]), None)
            if deck is None:
                self.fail("error", "Precinct data names a deck that does not exist", "%s: deck %r." % (ps["file"], ps["deck"]), ps["file"])
                continue
            if not any(x["id"] == did for x in deck["districts"]):
                self.fail("error", "Precinct data names an unknown district",
                          "%s: '%s' is not a district on Deck %d (sheet S%d)." % (ps["file"], ps["district"], deck["n"], deck["n"]), ps["file"])
            self.build_precincts(ps, deck)
        zones_t = self.text(FIXED["zones_csv"], "Canon zone reservations (Rev A)")
        zones = P.dict_csv(zones_t) if zones_t else []
        crown = self.crown()
        docs = {}
        for key in ("errata_md", "reference_md", "precincts_md"):
            docs[key] = self.text(FIXED[key], {"errata_md": "Canon errata, Revision B (game)",
                                               "reference_md": "Invicta ship reference (game)",
                                               "precincts_md": "Port of Arrivals precinct plans (game)"}[key])
        docs["revB_readme"] = self.text(FIXED["revB_readme"], "Rev B geometry notes")
        errata = errata_summary(docs.get("errata_md") or "")
        model = {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "root": self.r.root,
            "ship": ship, "game": {k: v for k, v in game.items()}, "decks": decks, "crown": crown,
            "precinct_sets": psets, "zones": zones, "errata": errata, "rules": rules,
            "categories": category_legend(), "load_ms": 0,
        }
        model["sources"] = [{"path": p, "role": role, "exists": self.r.exists(p) or os.path.isfile(_atlas_abs(p)),
                             "mtime": self.r.mtime(p) or _mtime(_atlas_abs(p))} for p, role in sorted(self.used.items())]
        model["load_problems"] = self.problems
        model["_docs"] = docs
        model["load_ms"] = int((time.time() - t0) * 1000)
        return model


def _glob(d, ext):
    out = []
    for base, _, files in os.walk(d):
        out += [os.path.join(base, f) for f in files if f.endswith(ext)]
    return out


ROAD_WORDS = re.compile(r"road|street|boulevard|concourse|lane|taxiway|apron|promenade|cross-line", re.I)


def is_road(b):
    """Roads and walkways listed among the buildings. Blocks may be cut by these."""
    return b.get("kind") == "transport" and bool(ROAD_WORDS.search(b.get("name", "")))


def block_obstacles(buildings):
    """Footprints that a block edge must not cut: each building, or each bay of a bay row."""
    out = []
    for b in buildings:
        if not b.get("rect_km") or is_road(b):
            continue
        out.extend(b.get("bays_km") or [b["rect_km"]])
    return out


BAY_WORDS = [("berth", "Berth"), ("hangar", "Hangar"), ("gate", "Gate"), ("marina", "Slip"), ("shaft", "Shaft"),
             ("garden", "Garden"), ("street", "Street"), ("depot", "Bay")]


def bay_label(b):
    """Generic name for one bay of a row, e.g. 'Berth' for 'Corvette Berths' (shown as Berth 1, Berth 2 ...)."""
    name = b.get("name", "").lower()
    return next((v for k, v in BAY_WORDS if k in name), "Bay")


def subtract_circles(part, excl, steps=360):
    """Cut reserved circles (for example a canon plaza) out of a block outline, so no block
    is drawn over them. Works on the convex outlines blocks have: the outline outside each
    circle is kept and the circle's arc is traced where it passes through the block."""
    for cx, cy, r in excl or []:
        if len(part) < 3:
            return part
        inside = lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2 < r * r - 1e-12
        if not any(inside(q) for q in part) and G.circle_overlap_area(part, cx, cy, r, 0.01) <= 1e-6:
            continue
        if all(inside(q) for q in part):
            return []
        k0 = next(i for i, q in enumerate(part) if not inside(q))   # start outside the circle
        part = part[k0:] + part[:k0]
        out = []
        n = len(part)

        def cross(a, b):  # where segment a-b crosses the circle
            dx, dy = b[0] - a[0], b[1] - a[1]
            fx, fy = a[0] - cx, a[1] - cy
            A, B, C = dx * dx + dy * dy, 2 * (fx * dx + fy * dy), fx * fx + fy * fy - r * r
            if A < 1e-18 or B * B - 4 * A * C <= 0:
                return []   # the segment's line misses (or only touches) the circle: no crossing
            disc = (B * B - 4 * A * C) ** 0.5
            ts = sorted(t for t in ((-B - disc) / (2 * A), (-B + disc) / (2 * A)) if 0 <= t <= 1)
            return [(a[0] + t * dx, a[1] + t * dy) for t in ts]

        pending = None  # angle where the outline entered the circle
        for i in range(n):
            a, b = part[i], part[(i + 1) % n]
            if not inside(a):
                out.append(tuple(a))
            for q in cross(a, b):
                ang = math.atan2(q[1] - cy, q[0] - cx)
                if pending is None:
                    out.append(q)
                    pending = ang
                else:
                    # trace the arc from the entry point to this exit point, the way that stays in the block
                    d = ang - pending
                    while d > math.pi:
                        d -= 2 * math.pi
                    while d < -math.pi:
                        d += 2 * math.pi
                    mid = (pending + d / 2)
                    mq = (cx + r * math.cos(mid), cy + r * math.sin(mid))
                    if not G.point_in_poly(mq[0], mq[1], part):
                        d = d - 2 * math.pi if d > 0 else d + 2 * math.pi
                    k = max(2, int(abs(d) / (2 * math.pi) * steps))
                    for j in range(1, k):
                        t = pending + d * j / k
                        out.append((cx + r * 1.002 * math.cos(t), cy + r * 1.002 * math.sin(t)))  # just outside, so chords never dip in
                    out.append(q)
                    pending = None
        part = [list(q) for q in out] if len(out) >= 3 else []
    return part


def make_blocks(n, shape, bx, buildings, excl, streets=()):
    """City blocks. The precinct is cut first along its streets and roads (both edges of
    each, so the roadway itself is not part of any block), then blocks longer than
    1 km are cut again on frame or lane grid lines. A cut is only made where it runs
    clear of every building, so a building always sits wholly inside one block."""
    eps = 1e-6
    obst = block_obstacles(buildings)
    roads = [s["rect_km"] for s in streets if s.get("rect_km")]
    for b in buildings:
        if b.get("rect_km") and is_road(b):
            roads.extend(b.get("bays_km") or [b["rect_km"]])
    roads = [r for r in roads if min(r[1] - r[0], r[3] - r[2]) <= 0.3]   # linear roads only
    cuts = []
    for r in roads:
        if r[1] - r[0] >= r[3] - r[2]:
            cuts += [("y", r[2]), ("y", r[3])]
        else:
            cuts += [("x", r[0]), ("x", r[1])]
    grid_x = [k * G.FRAME_KM for k in range(int(bx[0] / G.FRAME_KM) - 1, int(bx[1] / G.FRAME_KM) + 2)]
    grid_y = [(i - 12) * 0.5 + 0.25 for i in range(-1, len(G.LANES))]
    MIN = 0.12   # an empty strip thinner than 120 m (about 400 ft) is not made a block

    def is_roadway(reg):
        return any(r[0] - eps <= reg[0] and reg[1] <= r[1] + eps and r[2] - eps <= reg[2] and reg[3] <= r[3] + eps for r in roads)

    def has_building(reg):
        return any(o[0] >= reg[0] - eps and o[1] <= reg[1] + eps and o[2] >= reg[2] - eps and o[3] <= reg[3] + eps for o in obst)

    def ok_piece(reg):
        w, h = reg[1] - reg[0], reg[3] - reg[2]
        return min(w, h) >= MIN or is_roadway(reg) or has_building(reg)

    def clear(ax, c, reg):
        x0, x1, y0, y1 = reg
        lo, hi = (x0, x1) if ax == "x" else (y0, y1)
        if not (lo + eps < c < hi - eps):
            return False
        a, b = cut(reg, ax, c)
        if not (ok_piece(a) and ok_piece(b)):
            return False
        for o in obst:
            if o[0] < x1 - eps and o[1] > x0 + eps and o[2] < y1 - eps and o[3] > y0 + eps:
                a, b = (o[0], o[1]) if ax == "x" else (o[2], o[3])
                if a < c - eps and b > c + eps:
                    return False
        return True

    def cut(reg, ax, c):
        x0, x1, y0, y1 = reg
        return ([x0, c, y0, y1], [c, x1, y0, y1]) if ax == "x" else ([x0, x1, y0, c], [x0, x1, c, y1])

    def split(reg):
        for ax, c in cuts:
            if clear(ax, c, reg):
                a, b = cut(reg, ax, c)
                return split(a) + split(b)
        for ax, lines in (("x", grid_x), ("y", grid_y)):
            lo, hi = (reg[0], reg[1]) if ax == "x" else (reg[2], reg[3])
            if hi - lo <= 1.0 + eps:
                continue
            mid = (lo + hi) / 2
            for c in sorted(lines, key=lambda v: abs(v - mid)):
                if clear(ax, c, reg):
                    a, b = cut(reg, ax, c)
                    return split(a) + split(b)
        return [reg]

    out, seen = [], {}
    for cell in split(list(bx)):
        if is_roadway(cell):
            continue
        part = G.clip(shape, G.rect_poly(cell))
        if excl and len(part) >= 3:
            part = subtract_circles(part, excl)   # reserved plazas are never part of a block
        a = G.polygon_area(part) if len(part) >= 3 else 0
        if a < 0.002:
            continue
        f = int(math.floor(cell[0] / G.FRAME_KM + 1e-6))
        f_end = max(f + 1, int(math.ceil(cell[1] / G.FRAME_KM - 1e-6)))
        i = max(0, min(len(G.LANES) - 1, int(math.floor((cell[2] + 0.25) / 0.5 + 1e-6)) + 12))
        i_end = max(i, min(len(G.LANES) - 1, int(math.ceil((cell[3] + 0.25) / 0.5 - 1e-6)) + 12 - 1))
        bid = "D%d-F%d-%s" % (n, f, G.LANES[i])
        seen[bid] = seen.get(bid, 0) + 1
        out.append({"id": bid, "frame": f, "frame_end": f_end, "lane": G.LANES[i], "lane_end": G.LANES[i_end],
                    "cell_km": [round(v, 4) for v in cell], "part_km": [list(q) for q in part],
                    "area_km2": round(a, 4), "contents": []})
    # ids: frame and lane of the block's bow-port corner; a letter is added when two share one
    count = {}
    # number by grid cell (frame, then lane), so a block trimmed by an edge street keeps its place
    out.sort(key=lambda b: (b["frame"], round(b["cell_km"][0] / 0.05), b["cell_km"][2]))
    for k, b in enumerate(out):
        if seen[b["id"]] > 1:
            count[b["id"]] = count.get(b["id"], 0) + 1
            b["id"] += "abcdefghijklmnopqrstuvwxyz"[count[b["id"]] - 1]
        b["name"] = "Block %d" % (k + 1)
    return out


def _atlas_abs(rel):
    if rel.startswith("Invicta/"):
        return os.path.join(APP_DIR, *rel.split("/")[1:])
    return ""


def _mtime(p):
    try:
        return os.path.getmtime(p) if p else None
    except OSError:
        return None


def load_rules():
    p = os.path.join(DATA_DIR, "rules.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def errata_summary(md):
    decided = proposed = 0
    items = []
    for heading, header, rows, line in P.md_tables(md):
        if "State" not in header:
            continue
        si = header.index("State")
        for r in rows:
            if si < len(r):
                st = r[si]
                if "✅" in st:
                    decided += 1
                    items.append({"id": r[0], "state": "decided", "section": heading})
                elif "⏳" in st:
                    proposed += 1
                    items.append({"id": r[0], "state": "proposed", "item": r[1] if len(r) > 1 else "", "section": heading})
    return {"decided": decided, "proposed": proposed, "items": items}
