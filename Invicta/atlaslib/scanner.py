"""The consistency scanner. Runs every check against a freshly loaded model and
returns a list of issues. Severities:
  error    - broken or contradictory data (a file that won't load, a building outside the hull)
  warning  - a continuity problem between sources (two documents disagree)
  decision - something waiting on Jordan (proposed, assumption, placeholder)
  gap      - not designed yet (shown so nothing is invented to fill it)
"""

import hashlib
import math
import os
import re
import fnmatch

from . import geometry as G
from . import parsers as P
from .sources import FIXED, GAME_DOCS, MIRROR_DOCS

SEV_ORDER = {"error": 0, "warning": 1, "decision": 2, "gap": 3}


class Scan:
    def __init__(self, model, root):
        self.m = model
        self.root = root
        self.rules = model.get("rules", {})
        self.tol = dict({"area_pct": 2.0, "area_abs_km2": 0.15, "length_m": 15, "conversion_pct": 1.5},
                        **self.rules.get("tolerances", {}))
        self.issues = []

    def add(self, sev, cat, title, detail, entity=None, path=None, fix=None):
        key = "|".join([cat, title, entity or "", path or "", detail if sev in ("error", "warning") else ""])
        iid = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        known = None
        for ack in self.rules.get("acknowledged", []):
            if ack.get("match") and (ack["match"] in detail or ack["match"] in title or ack["match"] == iid):
                known = ack.get("reason", "acknowledged")
        self.issues.append({"id": iid, "severity": sev, "category": cat, "title": title, "detail": detail,
                            "entity": entity, "path": path, "fix": fix, "known": known})

    def area_close(self, a, b):
        if a is None or b is None:
            return True
        return abs(a - b) <= max(self.tol["area_abs_km2"], abs(b) * self.tol["area_pct"] / 100.0)

    # ------------------------------------------------------------------ run
    def run(self):
        for p in self.m.get("load_problems", []):
            self.add(p["severity"], "data", p["title"], p["detail"], p.get("entity"), p.get("path"))
        checks = [self.ship_checks, self.deck_checks, self.district_checks, self.transit_checks,
                  self.zone_checks, self.game_checks, self.precinct_checks, self.building_checks,
                  self.docs_vs_data, self.reference_checks, self.unit_checks, self.mirror_checks,
                  self.link_checks, self.term_checks, self.decision_checks, self.block_checks, self.gap_checks]
        for c in checks:
            try:
                c()
            except Exception as e:  # a broken check must not hide the others
                self.add("error", "data", "A check could not run", "%s stopped: %s: %s" % (c.__name__, type(e).__name__, e))
        self.issues.sort(key=lambda i: (SEV_ORDER[i["severity"]], i["known"] is not None, i["category"], i["title"]))
        return self.issues

    # ------------------------------------------------------------------ ship
    def ship_checks(self):
        s = self.m["ship"]
        dims = {d["item"]: d["value"] for d in s.get("dimensions", [])}
        sheet = FIXED["ship_sheet"]
        hp = s.get("hull_plan")
        if hp and dims:
            L = max(p[0] for p in hp) - min(p[0] for p in hp)
            W = 2 * max(abs(p[1]) for p in hp)
            Ls = P.num(dims.get("Length overall"))
            Ws = P.num(dims.get("Beam, maximum"))
            if Ls and abs(L - Ls) > 0.05:
                self.add("warning", "geometry", "Ship length differs from the hull plan",
                         "Sheet S0 says %.1f km; hull_plan_km.csv spans %.2f km." % (Ls, L), "ship", sheet)
            if Ws and abs(W - Ws) > 0.05:
                self.add("warning", "geometry", "Ship beam differs from the hull plan",
                         "Sheet S0 says %.1f km; hull_plan_km.csv is %.2f km wide." % (Ws, W), "ship", sheet)
        side = s.get("hull_side")
        if side and dims:
            H = max(p[1] for p in side) - min(p[1] for p in side)
            Hs = P.num(dims.get("Hull height, keel to dorsal plating"))
            if Hs and abs(H - Hs) > 0.05:
                self.add("warning", "geometry", "Hull height differs from the side profile",
                         "Sheet S0 says %.1f km; the Rev B side profile is %.2f km tall." % (Hs, H), "ship", FIXED["hull_side_revB_csv"])
        fr = s.get("frames")
        if fr is not None:
            if len(fr) != 69:
                self.add("error", "geometry", "Frame table is not F0 to F68",
                         "frames_F0_F68.csv has %d rows; canon is 69 frames." % len(fr), "ship", FIXED["frames_csv"])
            for row in fr:
                f = int(P.num(row.get("frame"), -1))
                x = P.num(row.get("x_km"))
                if x is not None and abs(x - f * 0.5) > 1e-6:
                    self.add("error", "geometry", "Frame position is off the 500 m grid",
                             "F%d is at x %.3f km, expected %.1f." % (f, x, f * 0.5), "ship", FIXED["frames_csv"])
        # S0 deck table vs each deck sheet
        dt = s.get("deck_table")
        if dt:
            h = dt["header"]
            for row in dt["rows"]:
                n = P.num(row[0])
                if not n or row[0].startswith("Total"):
                    continue
                deck = self.deck(int(n))
                if not deck or not deck.get("key"):
                    continue
                pairs = [("Net floor area (km²)", deck.get("net_area_stated"), "net floor area", "km²"),
                         ("Floor (m)", deck.get("floor_m"), "floor elevation", "m"),
                         ("Ceiling (m)", deck.get("ceiling_m"), "ceiling elevation", "m"),
                         ("Clear (m)", deck.get("clear_m"), "clear height", "m"),
                         ("Design pop.", deck.get("population"), "design population", "")]
                for col, val, label, unit in pairs:
                    if col in h:
                        sv = P.num(row[h.index(col)])
                        if sv is not None and val is not None and abs(sv - val) > 0.01 * max(1, abs(sv)) * 0.01:
                            self.add("warning", "continuity", "Ship sheet and deck sheet disagree",
                                     "Deck %d %s: S0 says %s %s, S%d says %s %s." % (n, label, _f(sv), unit, n, _f(val), unit),
                                     "D%d" % n, sheet)
            tot = next((r for r in dt["rows"] if r[0].startswith("Total")), None)
            if tot and "Net floor area (km²)" in h:
                tv = P.num(tot[h.index("Net floor area (km²)")])
                sm = sum(P.num(r[h.index("Net floor area (km²)")]) or 0 for r in dt["rows"] if not r[0].startswith("Total"))
                if tv and abs(tv - sm) > 0.05:
                    self.add("warning", "continuity", "Ship total floor area does not add up",
                             "S0 total says %.1f km², the decks add to %.1f km²." % (tv, sm), "ship", sheet)
        # elevations table vs game constants
        for e in s.get("elevations", []):
            m = re.match(r"Deck (\d)", e["level"])
            if m:
                n = int(m.group(1))
                lo, hi = (P.nums(e["range"]) + [None, None])[:2]
                deck = self.deck(n)
                if deck and deck.get("ceiling_m") and hi and abs(hi - deck["ceiling_m"]) > 0.5:
                    self.add("warning", "continuity", "Elevation table disagrees with deck sheet",
                             "S0 elevations put Deck %d's top at %s m; S%d's ceiling is %s m." % (n, _f(hi), n, _f(deck["ceiling_m"])), "D%d" % n, sheet)

    def deck(self, n):
        return next((d for d in self.m["decks"] if d["n"] == n), None)

    # ------------------------------------------------------------------ decks
    def deck_checks(self):
        total_calc = 0
        for d in self.m["decks"]:
            n = d["n"]
            sheet = d["paths"]["sheet"]
            if not d.get("key"):
                continue
            if d.get("net_area_calc"):
                total_calc += d["net_area_calc"]
            na = d.get("net_area_stated")
            if na and d.get("net_area_calc") and not self.area_close(d["net_area_calc"], na):
                rb = d["outline_source"].endswith("_revB.csv")
                self.add("decision" if rb else "warning", "geometry",
                         "Deck floor area changed in Revision B" if rb else "Deck outline area differs from its sheet",
                         "Deck %d %s: sheet S%d says %s km²; %s outline measures %s km²." % (
                             n, d["name"], n, _f(na), "the Rev B" if rb else "the", _f(d["net_area_calc"])),
                         d["id"], d["outline_source"])
            elif na and d.get("net_area_calc") and abs(d["net_area_calc"] - na) > 0.05 and d["outline_source"].endswith("_revB.csv"):
                self.add("decision", "continuity", "Deck sheet still shows the Revision A floor area",
                         "Deck %d %s: sheet S%d says %s km², Rev B outline measures %s km² (errata C1). The canon sheet is read-only; the game uses Rev B." % (
                             n, d["name"], n, _f(na), _f(d["net_area_calc"])), d["id"], sheet)
            if d.get("floor_m") is not None and d.get("clear_m") is not None and abs(d["ceiling_m"] - d["floor_m"] - d["clear_m"]) > 0.5:
                self.add("warning", "continuity", "Clear height does not match floor and ceiling",
                         "Deck %d: %s to %s m is %s m, the sheet says %s m clear." % (n, _f(d["floor_m"]), _f(d["ceiling_m"]),
                                                                                    _f(d["ceiling_m"] - d["floor_m"]), _f(d["clear_m"])), d["id"], sheet)
            stack = P.num(d["key"].get("Floor-to-floor stack height"))
            if stack and d.get("clear_m") and abs(stack - d["clear_m"] - 60) > 0.5:
                self.add("warning", "continuity", "Stack height is not clear height plus the 60 m service layer",
                         "Deck %d: stack %s m, clear %s m." % (n, _f(stack), _f(d["clear_m"])), d["id"], sheet)
            fr = P.nums(d["key"].get("Frames", ""))
            go = d.get("outline_gross")
            if len(fr) >= 2 and go:
                gx0, gx1 = min(p[0] for p in go), max(p[0] for p in go)
                if abs(gx0 - fr[0] * 0.5) > 0.3 or abs(gx1 - fr[1] * 0.5) > 0.3:
                    self.add("warning", "geometry", "Deck frame range differs from its outline",
                             "Deck %d: sheet says F%d to F%d (%.1f to %.1f km), gross outline runs %.2f to %.2f km." % (
                                 n, fr[0], fr[1], fr[0] * 0.5, fr[1] * 0.5, gx0, gx1), d["id"], sheet)
            # population sums
            people = sum(x["people"] or 0 for x in d["districts"])
            if d.get("population") and abs(people - d["population"]) > 1:
                self.add("warning", "continuity", "District populations do not add up to the deck",
                         "Deck %d: districts hold %s people, the sheet's design population is %s." % (n, _f(people), _f(d["population"])), d["id"], sheet)
        revb_total = P.num(re.search(r"Total net city floor: ([\d,.]+)", self.m["_docs"].get("revB_readme") or "") and
                           re.search(r"Total net city floor: ([\d,.]+)", self.m["_docs"].get("revB_readme") or "").group(1))
        if revb_total and abs(total_calc - revb_total) > 0.3:
            self.add("warning", "geometry", "Total city floor differs from the Rev B notes",
                     "The eight outlines measure %.1f km²; geometry_revB/README.txt says %.1f km²." % (total_calc, revb_total), "ship", FIXED["revB_readme"])

    # ------------------------------------------------------------------ districts
    def district_checks(self):
        for d in self.m["decks"]:
            n = d["n"]
            sheet = d["paths"]["sheet"]
            dists = d["districts"]
            if not dists:
                continue
            asum = sum(x["area_km2"] or 0 for x in dists)
            na = d.get("net_area_stated")
            if na and abs(asum - na) > 0.05:
                self.add("warning", "continuity", "Districts do not add up to the deck floor",
                         "Deck %d: districts add to %s km², the deck's net floor is %s km²." % (n, _f(asum), _f(na)), d["id"], sheet)
            for x in dists:
                if na and x["share"]:
                    sh = P.num(x["share"])
                    calc = 100.0 * (x["area_km2"] or 0) / na
                    if sh is not None and abs(sh - calc) > 0.15:
                        self.add("warning", "continuity", "District share is wrong",
                                 "%s: %s km² of %s km² is %.1f%%, the schedule says %s." % (x["name"], _f(x["area_km2"]), _f(na), calc, x["share"]), x["id"], sheet)
                if x["area_km2"] and x["people"] is not None and x["per_km2"] is not None:
                    dens = x["people"] / x["area_km2"]
                    if abs(dens - x["per_km2"]) > 1.5:
                        self.add("warning", "continuity", "District density is wrong",
                                 "%s: %s people on %s km² is %.0f per km², the schedule says %s." % (x["name"], _f(x["people"]), _f(x["area_km2"]), dens, _f(x["per_km2"])), x["id"], sheet)
                if x.get("area_calc") is not None and not self.area_close(x["area_calc"], x["area_km2"]):
                    self.add("warning", "geometry", "District shape on the plan does not match its area",
                             "%s: the schedule says %s km², the drawn shape measures %s km²." % (x["name"], _f(x["area_km2"]), _f(x["area_calc"])), x["id"], sheet)
                if x.get("plan_note") == "label drawn inside another district's shape":
                    self.add("warning", "continuity", "District label drawn in the wrong place",
                             "Sheet S%d's plan prints the %s label inside a neighbouring district's shape. The app matched %s to the shape whose area fits (%s km²)." % (
                                 n, x["name"].upper(), x["name"], _f(x.get("area_calc"))), x["id"], sheet)
                # centre address inside the district
                m = re.match(r"D(\d)-F(\d+)-([A-Y])$", x["centre"] or "")
                if not m:
                    self.add("warning", "data", "District centre address is not in D-F-lane form", "%s: '%s'." % (x["name"], x["centre"]), x["id"], sheet)
                    continue
                if int(m.group(1)) != n:
                    self.add("warning", "continuity", "District centre address names the wrong deck", "%s on Deck %d: %s." % (x["name"], n, x["centre"]), x["id"], sheet)
                px, py = int(m.group(2)) * 0.5, G.lane_centre_km(m.group(3))
                if x.get("polygon_km") and not _near_poly(px, py, x["polygon_km"], 0.25):
                    self.add("warning", "geometry", "District centre address is outside the district",
                             "%s: %s (x %.1f km, y %.1f km) is not inside its shape on the plan." % (x["name"], x["centre"], px, py), x["id"], sheet)
            if d.get("district_total") and d["district_total"]["area"] is not None and abs(d["district_total"]["area"] - asum) > 0.05:
                self.add("warning", "continuity", "District schedule total row is wrong",
                         "Deck %d: rows add to %s km², the Total row says %s." % (n, _f(asum), _f(d["district_total"]["area"])), d["id"], sheet)
            for x in dists:
                if x.get("revB"):
                    self.add("decision", "continuity", "District area changed in Revision B",
                             "%s: sheet S%d says %s km²; Revision B says %s km² (%s). The canon sheet stays as it is; the game uses Rev B." % (
                                 x["name"], n, _f(x["area_km2"]), _f(x["revB"]["area_km2"]), x["revB"]["source"]), x["id"], sheet)

    # ------------------------------------------------------------------ transit
    def transit_checks(self):
        for d in self.m["decks"]:
            n = d["n"]
            sheet = d["paths"]["sheet"]
            go = d.get("outline_gross")
            bow = min(p[0] for p in go) if go else None
            for st in d.get("keelway", []):
                f = P.num(st["frame"])
                fb = P.num(st["from_bow"])
                if f is None or fb is None or bow is None:
                    continue
                expect = f * 0.5 - bow
                if abs(expect - fb) > 0.15:
                    self.add("warning", "continuity", "Keelway stop distance does not match its frame",
                             "Deck %d %s stop: F%d is %.1f km from the deck bow (bow at %.2f km), the sheet says %s." % (
                                 n, st["stop"], f, expect, bow, st["from_bow"]) + (" (Strike Hangars Keelway stop)" if st["stop"] == "Strike Hangars" else ""),
                             d["id"], sheet)
                if not st["address"].startswith("D%d-F%d-" % (n, f)):
                    self.add("warning", "continuity", "Keelway stop address does not match its frame",
                             "Deck %d %s: frame %s, address %s." % (n, st["stop"], st["frame"], st["address"]), d["id"], sheet)
            for st in d.get("crossline", []):
                off = P.num(st["offset"])
                m = re.match(r"D\d-F\d+-([A-Y])", st["address"])
                if off is not None and m and G.lane_at(off) != m.group(1):
                    self.add("warning", "continuity", "Cross-line stop address does not match its offset",
                             "Deck %d %s: %s km from the centreline is lane %s, the address says %s." % (n, st["stop"], st["offset"], G.lane_at(off), st["address"]), d["id"], sheet)

    # ------------------------------------------------------------------ zone CSV
    def zone_checks(self):
        zones = self.m.get("zones") or []
        for z in zones:
            n = int(P.num(z.get("deck"), 0))
            deck = self.deck(n)
            if not deck:
                continue
            x = next((d for d in deck["districts"] if d["name"] == z["name"]), None)
            if not x:
                self.add("warning", "continuity", "Zone CSV names a district the sheet does not have",
                         "zone_reservations_km.csv: '%s' on Deck %d." % (z["name"], n), deck["id"], FIXED["zones_csv"])
                continue
            a = P.num(z.get("net_area_km2"))
            target = x["revB"]["area_km2"] if x.get("revB") else x["area_km2"]
            if a is not None and abs(a - target) > 0.05:
                self.add("warning", "continuity", "Zone CSV area differs from the current value",
                         "zone_reservations_km.csv gives %s %s km²; the current value is %s km²." % (z["name"], _f(a), _f(target)), x["id"], FIXED["zones_csv"])
            if x.get("polygon_km"):
                cx, cy = P.num(z["centroid_x_km"]), P.num(z["centroid_y_km"])
                if not _near_poly(cx, cy, x["polygon_km"], 0.3):
                    self.add("warning", "geometry", "Zone CSV centre is outside the district",
                             "%s: zone_reservations_km.csv centre (%.2f, %.2f km) is not inside the shape on sheet S%d." % (z["name"], cx, cy, n), x["id"], FIXED["zones_csv"])
        for d in self.m["decks"]:
            for x in d["districts"]:
                if not any(z["name"] == x["name"] and int(P.num(z["deck"], 0)) == d["n"] for z in zones):
                    self.add("warning", "continuity", "District missing from the zone CSV",
                             "%s (Deck %d) has no row in zone_reservations_km.csv." % (x["name"], d["n"]), x["id"], FIXED["zones_csv"])

    # ------------------------------------------------------------------ game constants
    def game_checks(self):
        g = self.m.get("game") or {}
        path = FIXED["game_geometry_py"]
        for n, v in (g.get("DECKS") or {}).items():
            deck = self.deck(int(n))
            if not deck or deck.get("floor_m") is None:
                continue
            name, fl, ce = v
            if name != deck["name"]:
                self.add("warning", "continuity", "Game names a deck differently", "Deck %s: game '%s', sheet '%s'." % (n, name, deck["name"]), deck["id"], path)
            if abs(fl - deck["floor_m"]) > 0.5 or abs(ce - deck["ceiling_m"]) > 0.5:
                self.add("error", "continuity", "Game deck elevations differ from canon",
                         "Deck %s %s: game %s/%s m, sheet S%s %s/%s m." % (n, name, fl, ce, n, _f(deck["floor_m"]), _f(deck["ceiling_m"])), deck["id"], path)
        stops = g.get("AERION_KEELWAY_STOPS") or {}
        d5 = self.deck(5)
        if d5 and stops:
            sheet = {s["stop"]: int(P.num(s["frame"])) for s in d5.get("keelway", [])}
            for nm, f in stops.items():
                if nm not in sheet:
                    self.add("warning", "continuity", "Game has a Keelway stop the sheet does not", "Aerion: '%s' at F%d." % (nm, f), "D5", path)
                elif sheet[nm] != f:
                    self.add("error", "continuity", "Game Keelway stop frame differs from canon",
                             "Aerion %s: game F%d, sheet S5 F%d." % (nm, f, sheet[nm]), "D5", path)
            for nm in sheet:
                if nm not in stops:
                    self.add("warning", "continuity", "Sheet has a Keelway stop the game does not", "Aerion: '%s'." % nm, "D5", path)
        if g.get("FRAME_SPACING_KM") not in (None, 0.5):
            self.add("error", "continuity", "Game frame spacing is not 500 m", "FRAME_SPACING_KM = %s." % g["FRAME_SPACING_KM"], None, path)

    # ------------------------------------------------------------------ precincts
    def precinct_checks(self):
        for did, ps in self.m["precinct_sets"].items():
            deck = self.deck(ps["deck"])
            dist = next((x for x in deck["districts"] if x["id"] == did), None) if deck else None
            if not dist:
                continue
            target = dist["revB"]["area_km2"] if dist.get("revB") else dist["area_km2"]
            stated = sum(p.get("area_km2_stated") or 0 for p in ps["precincts"])
            calc = sum(p.get("area_calc") or 0 for p in ps["precincts"])
            if stated and abs(stated - target) > 0.15:
                self.add("warning", "continuity", "Precinct areas do not add up to the district",
                         "%s: precincts add to %s km², the district is %s km²." % (dist["name"], _f(stated), _f(target)), did, ps["file"])
            if calc and not self.area_close(calc, target):
                self.add("warning", "geometry", "Precinct shapes do not fill the district",
                         "%s: the precinct shapes measure %s km² together, the district is %s km²." % (dist["name"], _f(calc), _f(target)), did, ps["file"])
            for p in ps["precincts"]:
                if p.get("area_km2_stated") is not None and not self.area_close(p["area_calc"], p["area_km2_stated"]):
                    self.add("warning", "geometry", "Precinct shape does not match its stated area",
                             "%s %s: stated %s km², its shape (clipped to the deck outline) measures %s km²." % (p["id"], p["name"], _f(p["area_km2_stated"]), _f(p["area_calc"])), p["uid"], ps["file"])
                if dist.get("polygon_km"):
                    frac = _fraction_inside(p["shape_km"], dist["polygon_km"])
                    if frac is not None and frac < 0.97:
                        self.add("warning", "geometry", "Precinct reaches outside its district",
                                 "%s %s: only %.0f%% of it lies inside the %s shape on sheet S%d (canon, Rev A)." % (p["id"], p["name"], frac * 100, dist["name"], deck["n"]), p["uid"], ps["file"])
                fl = re.match(r"F(\d+)–F(\d+)", p.get("frames", ""))
                bx = p.get("bounds_km")
                if fl and bx and bx[0] is not None:
                    if abs(bx[1] - int(fl.group(2)) * 0.5) > 0.2 or abs(bx[0] - int(fl.group(1)) * 0.5) > 0.2:
                        self.add("warning", "continuity", "Precinct frame range differs from its drawing",
                                 "%s %s: named %s, drawn from %.2f to %.2f km (F%.1f to F%.1f)." % (p["id"], p["name"], p["frames"], bx[0], bx[1], bx[0] / 0.5, bx[1] / 0.5), p["uid"], ps["file"])
            ps_list = ps["precincts"]
            for i in range(len(ps_list)):
                for j in range(i + 1, len(ps_list)):
                    a, b = ps_list[i], ps_list[j]
                    if len(a["shape_km"]) < 3 or len(b["shape_km"]) < 3:
                        continue
                    ov = G.polygon_area(G.clip(a["shape_km"], b["polygon_km"] if b.get("polygon_km") else G.rect_poly(b["bounds_km"])))
                    if ov > 0.01:
                        self.add("error", "geometry", "Precincts overlap",
                                 "%s %s and %s %s share %.2f km²." % (a["id"], a["name"], b["id"], b["name"], ov), a["uid"], ps["file"])

    # ------------------------------------------------------------------ buildings
    def building_checks(self):
        for did, ps in self.m["precinct_sets"].items():
            deck = self.deck(ps["deck"])
            hull = deck.get("outline_net") if deck else None
            for p in ps["precincts"]:
                for c in p.get("exclude_circles_km", []):  # no block may cover a reserved plaza
                    for blk in p.get("blocks") or []:
                        pts = blk.get("part_km") or []
                        if len(pts) >= 3 and G.circle_overlap_area(pts, c[0], c[1], c[2], 0.005) > 0.0005:
                            self.add("error", "geometry", "Block covers a reserved plaza",
                                     "%s in %s %s overlaps the excluded circle (%s)." % (blk["id"], p["id"], p["name"], p.get("exclude_note", "")), p["uid"], ps["file"])
                solid = [b for b in p["buildings"] if b.get("rect_km") and b["kind"] != "transport"]
                for b in p["buildings"]:
                    r = b.get("rect_km")
                    who = "%s %s" % (b["id"], b["name"])
                    if not r:
                        self.add("warning", "data", "Building has no position",
                                 "%s is listed in the precinct plan but is not placed on the drawing." % who, b["uid"], ps["file"])
                        continue
                    shapes = b.get("bays_km") or [r]
                    for s in shapes:
                        pts = G.rect_poly(s)
                        inset = 0.002
                        corners = [(s[0] + inset, s[2] + inset), (s[1] - inset, s[2] + inset), (s[1] - inset, s[3] - inset), (s[0] + inset, s[3] - inset)]
                        if hull and not all(G.point_in_poly(x, y, hull) for x, y in corners):
                            self.add("error", "geometry", "Building pokes through the hull",
                                     "%s reaches outside the Deck %d city floor (Rev B outline)." % (who, deck["n"]), b["uid"], ps["file"])
                            break
                        edge_tol = 0.06 if b["kind"] == "transport" else 0.0  # edge roads are shared with the neighbour
                        if not all(_near_poly(x, y, p["shape_km"], edge_tol) for x, y in corners):
                            self.add("warning", "geometry", "Building reaches outside its precinct",
                                     "%s sticks out of %s %s." % (who, p["id"], p["name"]), b["uid"], ps["file"])
                            break
                        for c in p.get("exclude_circles_km", []):
                            if any((x - c[0]) ** 2 + (y - c[1]) ** 2 < c[2] ** 2 for x, y in corners):
                                self.add("error", "geometry", "Building sits on a canon plaza",
                                         "%s reaches into the excluded circle (%s)." % (who, p.get("exclude_note", "")), b["uid"], ps["file"])
                                break
                    sz = b.get("size_m")
                    if sz and len(sz) >= 2:
                        if b.get("bays_km"):
                            if b.get("bay_names"):
                                drawn = None
                            else:
                                s0 = b["bays_km"][0]
                                drawn = ((s0[1] - s0[0]) * 1000, (s0[3] - s0[2]) * 1000)
                        else:
                            drawn = ((r[1] - r[0]) * 1000, (r[3] - r[2]) * 1000)
                        if drawn:
                            ok = (abs(drawn[0] - sz[0]) <= self.tol["length_m"] and abs(drawn[1] - sz[1]) <= self.tol["length_m"]) or \
                                 (abs(drawn[0] - sz[1]) <= self.tol["length_m"] and abs(drawn[1] - sz[0]) <= self.tol["length_m"])
                            if not ok:
                                self.add("warning", "continuity", "Building drawn at a different size than listed",
                                         "%s: listed %g × %g m, drawn %.0f × %.0f m." % (who, sz[0], sz[1], drawn[0], drawn[1]), b["uid"], ps["file"])
                    if b.get("bay_count") and b.get("bays_km") and len(b["bays_km"]) != b["bay_count"]:
                        self.add("warning", "continuity", "Bay count differs from the drawing",
                                 "%s: listed %d, drawn %d." % (who, b["bay_count"], len(b["bays_km"])), b["uid"], ps["file"])
                # overlaps between solid buildings
                for i in range(len(solid)):
                    for j in range(i + 1, len(solid)):
                        a, c = solid[i], solid[j]
                        ov = sum(G.rect_overlap(s1, s2) for s1 in (a.get("bays_km") or [a["rect_km"]]) for s2 in (c.get("bays_km") or [c["rect_km"]]))
                        if ov > 2e-5:  # 20 m²
                            self.add("warning", "geometry", "Buildings overlap",
                                     "%s %s and %s %s overlap by %s." % (a["id"], a["name"], c["id"], c["name"], G.fmt_area_km2(ov)), a["uid"], ps["file"])
                for b in solid:
                    if b["kind"] in ("plaza", "park"):
                        continue  # squares and parks are meant to sit on the boulevards
                    for st in p.get("streets", []):
                        ov = sum(G.rect_overlap(s, st["rect_km"]) for s in (b.get("bays_km") or [b["rect_km"]]))
                        if ov > 2e-5:
                            self.add("warning", "geometry", "Building sits on a street",
                                     "%s %s overlaps %s by %s." % (b["id"], b["name"], st["name"], G.fmt_area_km2(ov)), b["uid"], ps["file"])

    # ------------------------------------------------------------------ docs vs data
    def docs_vs_data(self):
        md = self.m["_docs"].get("precincts_md")
        for did, ps in self.m["precinct_sets"].items():
            if not ps.get("doc"):
                self.add("warning", "docs", "Precinct data has no design doc", "%s names no doc." % ps["file"], did, ps["file"])
                continue
            text = md if ps["doc"] == FIXED["precincts_md"] else None
            if text is None:
                rel = ps["doc"]
                full = os.path.join(self.root, *rel.split("/"))
                if not os.path.isfile(full):
                    self.add("error", "docs", "Precinct design doc is missing", "%s points to %s, which does not exist." % (ps["file"], rel), did, ps["file"])
                    continue
                text = open(full, encoding="utf-8").read()
            secs = {}
            # A precinct section counts even before it has a building table ("What it holds is not designed yet").
            for n, ln in enumerate(text.splitlines(), 1):
                hm = re.match(r"#+\s*((P\d+) · (.+?) — (F\d+) to (F\d+), lanes ([A-Y])–([A-Y]))", ln)
                if hm:
                    secs.setdefault(hm.group(2), (re.match(r"(P\d+) · (.+?) — (F\d+) to (F\d+), lanes ([A-Y])–([A-Y])", hm.group(1)), [], n))
            for heading, header, rows, line in P.md_tables(text):
                m = re.match(r"(P\d+) · (.+?) — (F\d+) to (F\d+), lanes ([A-Y])–([A-Y])", heading)
                if m:
                    secs[m.group(1)] = (m, rows, line)
            for p in ps["precincts"]:
                if p["id"] not in secs:
                    self.add("warning", "docs", "Precinct is in the app but not in the doc",
                             "%s %s has no section in %s." % (p["id"], p["name"], ps["doc"]), p["uid"], ps["doc"])
                    continue
                m, rows, line = secs[p["id"]]
                if m.group(2).strip() != p["name"]:
                    self.add("warning", "docs", "Precinct name differs between doc and app", "%s: doc '%s', app '%s'." % (p["id"], m.group(2), p["name"]), p["uid"], ps["doc"])
                if "%s–%s" % (m.group(3), m.group(4)) != p["frames"] or "%s–%s" % (m.group(5), m.group(6)) != p["lanes"]:
                    self.add("warning", "docs", "Precinct frames or lanes differ between doc and app",
                             "%s: doc %s–%s lanes %s–%s, app %s lanes %s." % (p["id"], m.group(3), m.group(4), m.group(5), m.group(6), p["frames"], p["lanes"]), p["uid"], ps["doc"])
                doc_rows = {_norm(r[0]): r for r in rows if r}
                atlas = {_norm(b["name"]): b for b in p["buildings"]}
                for k, r in doc_rows.items():
                    if k not in atlas:
                        self.add("warning", "docs", "Doc lists a building the app does not have",
                                 "%s: '%s' (%s line %d)." % (p["id"], r[0].replace("**", ""), os.path.basename(ps["doc"]), line), p["uid"], ps["doc"],
                                 fix="Add it to %s, or remove it from the doc." % ps["file"])
                    else:
                        b = atlas[k]
                        if len(r) > 1 and b.get("size_text") and r[1].replace("**", "") != b["size_text"].replace("**", ""):
                            self.add("warning", "docs", "Building size differs between doc and app",
                                     "%s %s: doc '%s', app '%s'." % (b["id"], b["name"], r[1], b["size_text"]), b["uid"], ps["doc"])
                for k, b in atlas.items():
                    if k not in doc_rows:
                        self.add("warning", "docs", "The app has a building the doc does not list",
                                 "%s %s is in %s but not in %s." % (b["id"], b["name"], ps["file"], ps["doc"]), b["uid"], ps["file"],
                                 fix="Add a row to the doc, or remove it from the app data.")

    # ------------------------------------------------------------------ reference doc
    def reference_checks(self):
        ref = self.m["_docs"].get("reference_md") or ""
        path = FIXED["reference_md"]
        g = self.m.get("game") or {}
        for heading, header, rows, line in P.md_tables(ref):
            if heading.startswith("2. Deck heights"):
                for r in rows:
                    mm = re.match(r"\**(\d) (\w+)", r[0])
                    if not mm:
                        continue
                    n = int(mm.group(1))
                    deck = self.deck(n)
                    fl = re.search(r"\(([\d,]+) m\)", r[2])
                    ce = re.search(r"\(([\d,]+) m\)", r[3])
                    if deck and fl and ce and deck.get("floor_m") is not None:
                        if abs(P.num(fl.group(1)) - deck["floor_m"]) > 0.5 or abs(P.num(ce.group(1)) - deck["ceiling_m"]) > 0.5:
                            self.add("warning", "docs", "Ship Reference deck heights differ from canon",
                                     "Deck %d: reference %s/%s m, sheet %s/%s m." % (n, fl.group(1), ce.group(1), _f(deck["floor_m"]), _f(deck["ceiling_m"])), deck["id"], path)
            if heading.startswith("3. Deck 5"):
                d5 = self.deck(5)
                for r in rows:
                    nm = re.sub(r"\s*\(.*?\)\s*$", "", r[0]).strip()
                    x = next((d for d in d5["districts"] if d["name"] == nm), None) if d5 else None
                    am = re.search(r"\(([\d.]+) km²", r[1])
                    if x and am:
                        want = x["revB"]["area_km2"] if x.get("revB") else x["area_km2"]
                        if abs(float(am.group(1)) - want) > 0.05:
                            self.add("warning", "docs", "Ship Reference district area differs",
                                     "%s: reference %s km², current %s km²." % (nm, am.group(1), _f(want)), x["id"], path)
                        if len(r) > 3 and r[3] != x["centre"]:
                            self.add("warning", "docs", "Ship Reference district address differs",
                                     "%s: reference %s, sheet %s." % (nm, r[3], x["centre"]), x["id"], path)
                    elif not x:
                        self.add("warning", "docs", "Ship Reference names an unknown Deck 5 district", "'%s'." % r[0], "D5", path)
            if heading.startswith("5. Port of Arrivals precincts"):
                ps = self.m["precinct_sets"].get("D5-port-of-arrivals")
                for r in rows:
                    p = next((q for q in ps["precincts"] if q["id"] == r[0]), None) if ps else None
                    if not p:
                        continue
                    if r[1] != p["name"]:
                        self.add("warning", "docs", "Ship Reference precinct name differs", "%s: reference '%s', app '%s'." % (p["id"], r[1], p["name"]), p["uid"], path)
                    if r[2] != p["frames"]:
                        self.add("warning", "docs", "Ship Reference precinct frames differ", "%s: reference %s, app %s." % (p["id"], r[2], p["frames"]), p["uid"], path)
                    am = re.match(r"([\d.]+) km²", r[4])
                    if am and p.get("area_km2_stated") is not None and abs(float(am.group(1)) - p["area_km2_stated"]) > 0.05:
                        self.add("warning", "docs", "Ship Reference precinct area differs", "%s: reference %s, app %s km²." % (p["id"], r[4], _f(p["area_km2_stated"])), p["uid"], path)
        # Hall of Arrivals sizes in the reference vs the game constants
        arr = g.get("ARRIVAL") or {}
        hall = re.search(r"\| Hall of Arrivals \| [^|]+\| ([\d.]+) × ([\d.]+) × ([\d.]+) m", ref)
        if hall and arr:
            want = (arr.get("hall_length_m"), arr.get("hall_depth_m"), arr.get("hall_height_m"))
            got = tuple(float(v) for v in hall.groups())
            if any(a is not None and abs(a - b) > 0.01 for a, b in zip(want, got)):
                self.add("error", "continuity", "Hall of Arrivals size differs between reference and game",
                         "Reference %s; invicta_geometry.py ARRIVAL %s." % (" × ".join(_f(v) for v in got), " × ".join(_f(v) for v in want)), "D5", path)

    # ------------------------------------------------------------------ unit conversions in the docs
    def unit_checks(self):
        tol = self.tol["conversion_pct"] / 100.0
        for rel in _invicta_docs(self.root):
            try:
                text = open(os.path.join(self.root, *rel.split("/")), encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for ln_no, line in enumerate(text.splitlines(), 1):
                for mm in re.finditer(r"([\d,.]+(?:\s*×\s*[\d,.]+)*)\s*ft\s*\(([\d,.]+(?:\s*×\s*[\d,.]+)*)\s*m\b", line):
                    ft = [P.num(v) for v in re.split(r"\s*×\s*", mm.group(1))]
                    m = [P.num(v) for v in re.split(r"\s*×\s*", mm.group(2))]
                    if len(ft) == len(m):
                        for a, b in zip(ft, m):
                            if b and a and abs(a / 3.28084 - b) > max(b * tol, 1.0):
                                self.add("warning", "units", "Feet and metres disagree",
                                         "%s line %d: '%s' (%s ft is %.0f m)." % (os.path.basename(rel), ln_no, mm.group(0), _f(a), a / 3.28084), None, rel)
                                break
                for mm in re.finditer(r"([\d,.]+)\s*mi\b[^()]{0,25}\(([\d,.]+)\s*km\b", line):
                    a, b = P.num(mm.group(1)), P.num(mm.group(2))
                    if a and b and abs(a * 1.609344 - b) > max(b * tol, 0.02):
                        self.add("warning", "units", "Miles and kilometres disagree",
                                 "%s line %d: '%s' (%s mi is %.2f km)." % (os.path.basename(rel), ln_no, mm.group(0), _f(a), a * 1.609344), None, rel)
                for mm in re.finditer(r"([\d,.]+)\s*sq mi\s*\(([\d,.]+)\s*km²", line):
                    a, b = P.num(mm.group(1)), P.num(mm.group(2))
                    if a and b and abs(a * 2.589988 - b) > max(b * tol, 0.06):
                        self.add("warning", "units", "Square miles and km² disagree",
                                 "%s line %d: '%s' (%s sq mi is %.1f km²)." % (os.path.basename(rel), ln_no, mm.group(0), _f(a), a * 2.589988), None, rel)
                if re.search(r"\b\d[\d,.]*\s*(?:m|km|km²)\b", line) and not re.search(r"ft|mi\b|acres|sq mi|tons", line) and rel.endswith(("Ship_Reference.md", "Precincts.md")) and line.startswith("|"):
                    self.add("warning", "units", "Measurement without US units",
                             "%s line %d gives metric only: %s" % (os.path.basename(rel), ln_no, line.strip()[:140]), None, rel)

    # ------------------------------------------------------------------ mirrored docs
    def mirror_checks(self):
        for mr in self.rules.get("mirrors", []):
            a, b = mr["a"], mr["b"]
            A = _list_files(self.root, a, mr.get("patterns", ["*"]))
            B = _list_files(self.root, b, mr.get("patterns", ["*"]))
            if not os.path.isdir(os.path.join(self.root, *b.split("/"))):
                self.add("warning", "docs", "Mirror folder is missing", "%s should mirror %s." % (b, a), None, b)
                continue
            for rel in sorted(set(A) | set(B)):
                pa = os.path.join(self.root, *(a + "/" + rel).split("/"))
                pb = os.path.join(self.root, *(b + "/" + rel).split("/"))
                if rel not in B:
                    self.add("warning", "docs", "File missing from the mirror", "%s/%s has no copy in %s." % (a, rel, b), None, a + "/" + rel)
                elif rel not in A:
                    self.add("warning", "docs", "Mirror has a file the game docs do not", "%s/%s has no original in %s." % (b, rel, a), None, b + "/" + rel)
                else:
                    if _digest(pa) != _digest(pb):
                        newer = a if os.path.getmtime(pa) >= os.path.getmtime(pb) else b
                        self.add("warning", "docs", "Mirrored copies differ",
                                 "%s differs between %s and %s (newer in %s)." % (rel, a, b, newer), None, a + "/" + rel,
                                 fix="Copy the newer one over the other.")

    # ------------------------------------------------------------------ broken links
    def link_checks(self):
        for rel in _invicta_docs(self.root):
            full = os.path.join(self.root, *rel.split("/"))
            try:
                text = open(full, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            base = os.path.dirname(full)
            for link in set(P.md_images(text) + P.md_links(text)):
                target = link.split("#")[0]
                if not target:
                    continue
                if not os.path.exists(os.path.join(base, *target.split("/"))):
                    self.add("error", "docs", "Broken link or image", "%s points to %s, which does not exist." % (rel, link), None, rel)
        for did, ps in self.m["precinct_sets"].items():
            for key in ("overview_blueprint",):
                if ps.get(key) and not os.path.isfile(os.path.join(self.root, *ps[key].split("/"))):
                    self.add("error", "docs", "Blueprint file is missing", "%s: %s." % (ps["file"], ps[key]), did, ps["file"])
            for p in ps["precincts"]:
                for key in ("blueprint", "blueprint_svg"):
                    if p.get(key) and not os.path.isfile(os.path.join(self.root, *p[key].split("/"))):
                        self.add("error", "docs", "Blueprint file is missing", "%s %s: %s." % (p["id"], p["name"], p[key]), p["uid"], ps["file"])

    # ------------------------------------------------------------------ retired terms
    def term_checks(self):
        for rule in self.rules.get("retired_terms", []):
            term = rule["term"]
            for where in rule.get("where", []):
                base = os.path.join(self.root, *where.split("/"))
                for dirpath, _, files in os.walk(base):
                    for f in files:
                        if not f.endswith((".md", ".html", ".txt", ".csv", ".py")) or f in rule.get("ignore_files", []):
                            continue
                        full = os.path.join(dirpath, f)
                        try:
                            text = open(full, encoding="utf-8").read()
                        except (OSError, UnicodeDecodeError):
                            continue
                        hits = len(re.findall(re.escape(term), text))
                        if hits:
                            rel = os.path.relpath(full, self.root).replace(os.sep, "/")
                            canon = rel.startswith("Docs/1_Canon_Source")
                            self.add("warning", "continuity", "Retired term still in use",
                                     "'%s' appears %d time%s in %s. %s says use '%s'.%s" % (
                                         term, hits, "" if hits == 1 else "s", rel, rule.get("source", ""), rule.get("use", ""),
                                         " This is a read-only canon sheet; Revision B overrides it." if canon else ""), None, rel)

    # ------------------------------------------------------------------ decisions waiting on Jordan
    def decision_checks(self):
        er = self.m.get("errata") or {}
        if er.get("proposed"):
            ids = [i["id"] for i in er["items"] if i["state"] == "proposed"]
            self.add("decision", "decision", "Canon errata waiting for a decision",
                     "%d errata rows are proposed (⏳) and %d decided (✅). Waiting: %s." % (er["proposed"], er["decided"], ", ".join(ids)), None, FIXED["errata_md"])
        for did, ps in self.m["precinct_sets"].items():
            if ps.get("status") == "proposed":
                self.add("decision", "decision", "Precinct plan waiting for approval",
                         "%s: %d precincts and %d buildings are proposed (%s), not yet canon." % (
                             ps["district"], len(ps["precincts"]), sum(len(p["buildings"]) for p in ps["precincts"]), ps.get("version", "")), did, ps["file"])
            for p in ps["precincts"]:
                for b in p["buildings"]:
                    if b.get("status") in ("assumption", "placeholder"):
                        self.add("decision", "decision", "Building rests on an assumption",
                                 "%s %s: %s (%s)." % (b["id"], b["name"], b.get("notes") or "", b["status"]), b["uid"], ps["file"])
        arr = (self.m.get("game") or {}).get("ARRIVAL") or {}
        notes = (self.m.get("game") or {}).get("ARRIVAL__comments") or {}
        tune = [k for k, c in notes.items() if c.upper().startswith("TUNE")]
        if tune:
            self.add("decision", "decision", "Game sizes still marked TUNE",
                     "invicta_geometry.py ARRIVAL has %d placeholder values: %s." % (len(tune), ", ".join("%s = %s" % (k, arr.get(k)) for k in tune)), "D5", FIXED["game_geometry_py"])

    # ------------------------------------------------------------------ not designed yet
    def block_checks(self):
        """Blocks must never cut through a building (Jordan, 26 Nov 2026)."""
        from .loader import is_road
        eps = 1e-6
        for did, ps in self.m["precinct_sets"].items():
            for p in ps["precincts"]:
                blocks = p.get("blocks", [])
                for b in p["buildings"]:
                    if not b.get("rect_km") or is_road(b):
                        continue
                    for k, part in enumerate(b.get("bays_km") or [b["rect_km"]]):
                        holders = [blk["id"] for blk in blocks if G.rect_overlap(part, blk["cell_km"]) > 1e-7]
                        inside = [blk["id"] for blk in blocks if blk["cell_km"][0] - eps <= part[0] and part[1] <= blk["cell_km"][1] + eps
                                  and blk["cell_km"][2] - eps <= part[2] and part[3] <= blk["cell_km"][3] + eps]
                        if not inside:
                            what = "%s %s" % (b["id"], b["name"]) + (" (%s %d)" % (b.get("bay_label", "bay"), k + 1) if b.get("bays_km") else "")
                            self.add("error", "geometry", "Block cuts through a building",
                                     "%s is split across blocks %s. A building must sit wholly inside one block." % (what, ", ".join(holders) or "none"),
                                     b["uid"], ps["file"], fix="Move or resize the building so it clears the block edge, or move the street that bounds the block.")
                            break

    def gap_checks(self):
        for d in self.m["decks"]:
            undesigned = [x for x in d["districts"] if x["design_status"] == "not designed yet"]
            if undesigned:
                self.add("gap", "design-gap", "Districts with no precinct plan yet",
                         "Deck %d %s: %s." % (d["n"], d["name"], ", ".join("%s (%s km²)" % (x["name"], _f(x["area_km2"])) for x in undesigned)), d["id"], None)
        for did, ps in self.m["precinct_sets"].items():
            for p in ps["precincts"]:
                fields = ("height_m", "floors", "structure", "entrances")
                missing = [b for b in p["buildings"] if b["kind"] not in ("transport",) and not b.get("height_m")]
                if missing:
                    self.add("gap", "design-gap", "Buildings with no height or architecture yet",
                             "%s %s: %d of %d buildings have a footprint but no height, floors or structure." % (
                                 p["id"], p["name"], len(missing), len(p["buildings"])), p["uid"], ps["file"])
                empty = [blk["id"] for blk in p.get("blocks", []) if not blk["contents"]]
                if empty:
                    self.add("gap", "design-gap", "Empty blocks",
                             "%s %s: %d of %d blocks hold nothing yet (%s)." % (p["id"], p["name"], len(empty), len(p["blocks"]), ", ".join(empty[:12]) + (" …" if len(empty) > 12 else "")), p["uid"], ps["file"])


# ---------------------------------------------------------------------- helpers

def _f(v):
    if v is None:
        return "?"
    if abs(v - round(v)) < 1e-9:
        return "{:,}".format(int(round(v)))
    return "{:,.2f}".format(v).rstrip("0").rstrip(".")


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.replace("**", "").lower()).strip()


def _near_poly(x, y, pts, tol):
    if G.point_in_poly(x, y, pts):
        return True
    if tol <= 0:
        # on the boundary counts as inside
        tol = 1e-6
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L))
        if math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)) <= tol:
            return True
    return False


def _fraction_inside(shape, poly, step=0.05):
    if len(shape) < 3:
        return None
    bx = G.bbox(shape)
    tot = ins = 0
    y = bx[2] + step / 2
    while y < bx[3]:
        x = bx[0] + step / 2
        while x < bx[1]:
            if G.point_in_poly(x, y, shape):
                tot += 1
                if _near_poly(x, y, poly, 0.03):
                    ins += 1
            x += step
        y += step
    return ins / tot if tot else None


def _invicta_docs(root):
    out = []
    for rel in ("Game/Docs/Invicta_Ship_Reference.md", "Game/Docs/Port_of_Arrivals_Precincts.md",
                "Game/Docs/02_Canon_Errata.md", "Game/Docs/05_World_and_Content.md", "Game/Docs/M2_Progress.md"):
        if os.path.isfile(os.path.join(root, *rel.split("/"))):
            out.append(rel)
    return out


def _list_files(root, base, patterns):
    full = os.path.join(root, *base.split("/"))
    out = []
    for dirpath, _, files in os.walk(full):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), full).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, pat) and rel.count("/") == pat.count("/") for pat in patterns):
                out.append(rel)
    return out


def _digest(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(model, root):
    return Scan(model, root).run()
