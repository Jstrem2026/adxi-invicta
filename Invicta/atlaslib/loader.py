"""Build the app model (ship > deck > district > precinct > block > building)
fresh from the source files every time it is asked. Nothing is cached on disk,
so whatever the docs and data files say right now is what the app shows."""

import json
import math
import os
import re
import time

from . import geometry as G
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
            # blocks: 500 m between two frame lines x one 500 m lane band
            blocks = []
            f0 = int(math.floor(bx[0] / G.FRAME_KM + 1e-9))
            f1 = int(math.ceil(bx[1] / G.FRAME_KM - 1e-9))
            i0 = int(math.floor((bx[2] + 0.25) / 0.5 + 1e-9)) + 12
            i1 = int(math.ceil((bx[3] + 0.25) / 0.5 - 1e-9)) + 12
            for f in range(f0, f1):
                for i in range(i0, i1):
                    if not 0 <= i < len(G.LANES):
                        continue
                    lane = G.LANES[i]
                    yc = (i - 12) * 0.5
                    cell = [f * 0.5, (f + 1) * 0.5, yc - 0.25, yc + 0.25]
                    part = G.clip(shape, G.rect_poly(cell))
                    a = G.polygon_area(part) if len(part) >= 3 else 0
                    if a and excl:
                        a -= sum(G.circle_overlap_area(part, c[0], c[1], c[2], 0.01) for c in excl)
                    if a < 0.0005:
                        continue
                    blocks.append({"id": "D%d-F%d-%s" % (n, f, lane), "frame": f, "lane": lane, "cell_km": cell,
                                   "part_km": [list(q) for q in part], "area_km2": round(a, 4), "contents": []})
            # buildings
            for b in p["buildings"]:
                b["uid"] = "%s-%s" % (p["uid"].rsplit("-", 1)[0], b["id"])
                r = b.get("rect_km")
                if r:
                    cxy = ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)
                    b["address"] = G.address(n, *cxy)
                    shapes = b.get("bays_km") or [r]
                    b["footprint_km2"] = round(sum((s[1] - s[0]) * (s[3] - s[2]) for s in shapes), 4)
                    b["blocks"] = []
                    for blk in blocks:
                        ov = sum(G.rect_overlap(s, blk["cell_km"]) for s in shapes)
                        if ov > 1e-7:
                            b["blocks"].append(blk["id"])
                            blk["contents"].append({"id": b["id"], "share": round(ov / max(b["footprint_km2"], 1e-9), 3)})
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
            "load_ms": 0,
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
