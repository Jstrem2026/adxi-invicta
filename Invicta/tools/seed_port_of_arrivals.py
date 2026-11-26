"""One-time seed (26 Nov 2026): build data/decks/D5/port-of-arrivals.json from the
Port of Arrivals precinct plans (Game/Docs/Port_of_Arrivals_Precincts.md) and the
precinct blueprint SVGs (Game/Docs/art/blueprints/precincts/*.svg).

The JSON is the app's working copy from here on. The scanner keeps checking it
against the .md tables, so a later change to either side shows up as an issue.

Usage:  python tools/seed_port_of_arrivals.py <ArcaneDrift root> <output json>
"""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from import_precinct_svg import parse  # noqa: E402

ALIASES = {"SERVICE SHAFT SITE": "SHAFT", "SERVICE SHAFTS": "SHAFT", "ARRIVAL HANGAR": "ARRIVAL",
           "CROSS-LINE STOP": "", "GATE CONCOURSE": "GATE CONCOURSE (COVERED WALKWAY, 98 FT)",
           "APRON YARDS": "APRON YARDS · BAGGAGE, FUEL, GROUND HANDLING",
           "ATRIUM EDGE PARK": "@PATH", "PICKUP LANES": "PICKUP", "STATION WALK": "STATION WALK"}
SVG_FILES = {"P1": "p1-bow-docks", "P2": "p2-arrivals", "P3": "p3-stern-docks", "P4": "p4-freight",
             "P5": "p5-terminals", "P6": "p6-concourse", "P7": "p7-station", "P8": "p8-shuttle-yards"}


def norm(s):
    return re.sub(r"\s+", " ", s.upper().replace("’", "'").strip())


def md_sections(md):
    out = []
    for m in re.finditer(r"^## (P\d) · (.+?) — F(\d+) to F(\d+), lanes ([A-Y])–([A-Y])(.*)$", md, re.M):
        start = m.end()
        nxt = re.search(r"^## ", md[start:], re.M)
        body = md[start:start + nxt.start()] if nxt else md[start:]
        rows = []
        for line in body.splitlines():
            if line.startswith("|") and not re.match(r"\|\s*-", line) and not line.startswith("| Item"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                rows.append(cells + [""] * (3 - len(cells)))
        intro = [l for l in body.splitlines() if l and not l.startswith(("|", "!"))]
        out.append({"id": m.group(1), "name": m.group(2), "f0": int(m.group(3)), "f1": int(m.group(4)),
                    "l0": m.group(5), "l1": m.group(6), "extra": m.group(7).strip(), "rows": rows,
                    "intro": intro})
    return out


def metric_dims(size):
    for m in re.finditer(r"\(([\d.,\s×x]+)\s*m\)", size):
        dims = [float(v.replace(",", "")) for v in re.split(r"\s*[×x]\s*", m.group(1).strip())]
        if len(dims) >= 2:
            return dims
    m = re.search(r"([\d,]+) × ([\d,]+) ft", size)  # feet only: convert, round to 10 m
    if m:
        return [round(float(v.replace(",", "")) * 0.3048, -1) for v in m.groups()]
    return None


def status_of(size, notes):
    t = (size + " " + notes).lower()
    if "canon" in t and "not" not in t:
        return "canon"
    if "assum" in t:
        return "assumption"
    if "placeholder" in t:
        return "placeholder"
    return "proposed"


def kind_of(name):
    n = name.lower()
    for k, words in (("park", ("park", "garden")), ("plaza", ("plaza", "forecourt", "square")),
                     ("bays", ("berths", "marina", "row a", "row b", "gates", "depot·")),
                     ("utility", ("utility", "shaft", "plant", "waste")),
                     ("transport", ("road", "boulevard", "street", "walk", "taxiway", "locks", "keelway", "pickup", "concourse", "apron", "stop", "lifts", "rank"))):
        if any(w in n for w in words):
            return k
    return "building"


KIND_OVERRIDES = {"TUG PARK": "transport", "POD DEPOT": "transport", "FUEL DEPOT": "utility", "FUEL FARM": "utility"}


def main(root, out_path):
    md_path = os.path.join(root, "Game", "Docs", "Port_of_Arrivals_Precincts.md")
    md = open(md_path, encoding="utf-8").read()
    secs = md_sections(md)
    ref = open(os.path.join(root, "Game", "Docs", "Invicta_Ship_Reference.md"), encoding="utf-8").read()
    summary = {}
    for line in ref.splitlines():
        m = re.match(r"\| (P\d) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([\d.]+) km² \(([\d.]+) sq mi\) \| ([^|]+) \|", line)
        if m:
            summary[m.group(1)] = {"area_km2": float(m.group(5)), "role": m.group(7).strip(), "lanes_text": m.group(4).strip()}
    order = re.search(r"Build order[^:]*: (.+)", md).group(1)
    build_order = re.findall(r"(P\d)", order)

    precincts = []
    for sec in secs:
        pid = sec["id"]
        svg_rel = "Game/Docs/art/blueprints/precincts/%s.svg" % SVG_FILES[pid]
        d = parse(os.path.join(root, *svg_rel.split("/")))
        rects = d["rects"]
        outline = next((r for r in rects if r["stroke"] == "#fff" and r["sw"] == "3"), None)
        if outline:
            bounds = [outline["x0"], outline["x1"], outline["y0"], outline["y1"]]
        else:  # P1 is drawn as a polygon (hull taper): take frame span + lanes, clipped later by the deck outline
            bounds = [None, None, None, None]
        # candidate shapes inside the precinct
        cands = []
        for r in rects:
            if r is outline or r["fill"] in ("#0b2a4a", "#7fb0de", "none", "#fff", "#05111f"):
                continue
            if r["sw"] is None and not r["texts"]:
                continue
            label = " ".join(t for b, t in r["texts"] if b) or (r["texts"][0][1] if r["texts"] else "")
            cands.append({"label": norm(label), "r": r, "used": False})
        # P8 park drawn as a path
        svg_txt = open(os.path.join(root, *svg_rel.split("/")), encoding="utf-8").read()
        k = d["k_px_per_m"]
        b = []
        streets = []
        for row in sec["rows"]:
            name, size, notes = row[0], row[1], row[2]
            nm = norm(re.sub(r"\*", "", name))
            dims = metric_dims(size)
            entry = {"name": re.sub(r"\*", "", name), "size_text": size, "notes": notes.replace("**", ""),
                     "status": status_of(size, notes), "kind": KIND_OVERRIDES.get(norm(name), kind_of(name))}
            if dims:
                entry["size_m"] = dims[:2]
                if len(dims) > 2:
                    entry["height_m"] = dims[2]
            bays = re.match(r"(\d+) bays, each", size)
            if bays:
                entry["kind"] = "bays"
                entry["bay_count"] = int(bays.group(1))
            key = ALIASES.get(nm, nm)
            hits = []
            if nm == "ARRIVAL HANGAR":
                hits = [c for c in cands if not c["used"] and c["r"]["fill"] == "#ff8a3d" and abs(c["r"]["w_m"] - 80) < 1][:1]
            elif " / " in nm:  # one row naming several shapes, e.g. "Bow Garden / Stern Garden"
                for part in nm.split(" / "):
                    hits += [c for c in cands if not c["used"] and c["label"] == part][:1]
                if hits:
                    entry["kind"] = "bays" if len(hits) > 1 else entry["kind"]
                    entry["bay_count"] = len(hits)
                    entry["bay_names"] = [h["label"].title() for h in hits]
            if hits:
                pass
            elif entry.get("kind") == "bays" or nm.startswith("SHUTTLE GATES"):
                # unlabeled (or G/C/F-numbered) repeated rects of the bay size
                want = dims[:2] if dims else None
                pool = [c for c in cands if not c["used"] and want and abs(c["r"]["w_m"] - want[0]) < 1 and abs(c["r"]["h_m"] - want[1]) < 1
                        and (c["label"] == "" or re.fullmatch(r"(FRIGATE )?[GCFM]\d+", c["label"]))]
                n = entry.get("bay_count") or (16 if nm.startswith("SHUTTLE GATES") else len(pool))
                if nm.startswith("SHUTTLE GATES"):
                    entry["kind"] = "bays"; entry["bay_count"] = 16
                # rows A/B in P8 share a size: split by y
                if nm in ("HANGAR ROW A", "HANGAR ROW B"):
                    ys = sorted({round(c["r"]["y0"], 3) for c in pool})
                    rows_by_y = collections.defaultdict(list)
                    for c in pool:
                        rows_by_y[round(c["r"]["y0"], 3)].append(c)
                    pool = [c for y in ys for c in rows_by_y[y]]
                hits = pool[:n]
            elif key == "@PATH":
                sh = [x for x in d["shapes"] if x["tag"] == "path" and x["fill"] == "#2f6b4a"]
                if sh:
                    xs = [q[0] for q in sh[0]["points_km"]]; ys = [q[1] for q in sh[0]["points_km"]]
                    entry["rect_km"] = [min(xs), max(xs), min(ys), max(ys)]
            else:
                for c in cands:
                    if not c["used"] and key and (c["label"] == key or c["label"].startswith(key + " ") or c["label"].startswith(key + " ·")):
                        hits = [c]
                        break
                if not hits and nm == "CROSS-LINE STOP":
                    hits = [c for c in cands if not c["used"] and c["label"] == "" and abs(c["r"]["w_m"] - 300) < 1][:1]
                if not hits and nm.startswith("BONDED WAREHOUSE"):
                    hits = [c for c in cands if not c["used"] and c["label"] == "BONDED"][:1]
                if not hits and nm == "YARD LOCKS":
                    hits = [c for c in cands if not c["used"] and abs(c["r"]["w_m"] - 600) < 1 and abs(c["r"]["h_m"] - 150) < 1][:1]
            for c in hits:
                c["used"] = True
            if hits:
                if len(hits) == 1 and entry["kind"] != "bays":
                    r = hits[0]["r"]
                    entry["rect_km"] = [r["x0"], r["x1"], r["y0"], r["y1"]]
                else:
                    entry["bays_km"] = [[c["r"]["x0"], c["r"]["x1"], c["r"]["y0"], c["r"]["y1"]] for c in hits]
                    entry["rect_km"] = [min(x[0] for x in entry["bays_km"]), max(x[1] for x in entry["bays_km"]),
                                        min(x[2] for x in entry["bays_km"]), max(x[3] for x in entry["bays_km"])]
            b.append(entry)
        # second shaft in P2 ("Service shafts | two")
        for e in b:
            if norm(e["name"]) == "SERVICE SHAFTS":
                extra = [c for c in cands if not c["used"] and c["label"] == "SHAFT"]
                if extra and "rect_km" in e:
                    e["bays_km"] = [e["rect_km"]] + [[c["r"]["x0"], c["r"]["x1"], c["r"]["y0"], c["r"]["y1"]] for c in extra]
                    e["rect_km"] = [min(x[0] for x in e["bays_km"]), max(x[1] for x in e["bays_km"]), min(x[2] for x in e["bays_km"]), max(x[3] for x in e["bays_km"])]
                    e["bay_count"] = len(e["bays_km"])
                    e["kind"] = "utility"
                    for c in extra:
                        c["used"] = True
        # labelled roads and streets become the street layer
        for c in cands:
            if c["used"]:
                continue
            r = c["r"]
            lab = c["label"]
            if r["fill"] in ("#2c3440", "#4a3f2a", "#0f2f4f", "#5a6b7d", "#22384f", "#3a4a3a", "#30404f") or re.search(r"ROAD|STREET|BOULEVARD|KEELWAY|CONCOURSE|TAXIWAY|PICKUP|WALK", lab):
                w = min(r["w_m"], r["h_m"])
                streets.append({"name": lab.title() if lab else "", "width_m": w, "rect_km": [r["x0"], r["x1"], r["y0"], r["y1"]], "fill": r["fill"]})
                c["used"] = True
        def street_name(st):
            x0, x1, y0, y1 = st["rect_km"]
            vertical = (y1 - y0) > (x1 - x0)
            f = st["fill"]
            if f == "#4a3f2a":
                return "Arrivals Boulevard" if pid in ("P2", "P5", "P7") else "Boulevard"
            if f == "#0f2f4f":
                return "Keelway"
            if f == "#5a6b7d":
                return "Gate Concourse" if pid == "P2" else "Dock Concourse"
            if f == "#22384f":
                return "Apron yards"
            if f == "#30404f":
                return "Pickup lanes"
            if f == "#3a4a3a":
                return "Yard Taxiway"
            if f == "#4a4a2a":
                return "Concourse Promenade"
            if vertical:
                fr = round((x0 + x1) / 2 / 0.5)
                if abs((x0 + x1) / 2 - fr * 0.5) < 0.03:
                    return "Cross-line" if fr == 52 and (x1 - x0) > 0.045 else "F%d Street" % fr
            if pid == "P2" and not vertical:
                return "Gate Road" if y0 < -5.5 else "Dock Road"
            return "Street"
        for c in cands:  # unlabelled promenade (P6)
            if not c["used"] and c["r"]["fill"] == "#4a4a2a":
                r = c["r"]; c["used"] = True
                streets.append({"name": "", "width_m": min(r["w_m"], r["h_m"]), "rect_km": [r["x0"], r["x1"], r["y0"], r["y1"]], "fill": r["fill"]})
        for st in streets:
            nm0 = re.sub(r"\s*\(.*$|\s*·.*$", "", st["name"]).strip()
            st["name"] = nm0.title() if nm0 and nm0 != nm0.title() else (nm0 or street_name(st))
            if st["name"].startswith("Keelway"):
                st["name"] = "Keelway"
        # md rows that are roads: take their geometry from the street layer
        for e in b:
            if "rect_km" in e or "bays_km" in e:
                continue
            want = norm(e["name"])
            if want == "STREETS":
                m = [st for st in streets if re.fullmatch(r"F\d+ Street", st["name"])]
            else:
                m = [st for st in streets if norm(st["name"]).startswith(want.rstrip("S")) or want.startswith(norm(st["name"]))]
            if m:
                e["kind"] = "transport"
                if len(m) == 1:
                    e["rect_km"] = m[0]["rect_km"]
                else:
                    e["bays_km"] = [x["rect_km"] for x in m]
                    e["rect_km"] = [min(x[0] for x in e["bays_km"]), max(x[1] for x in e["bays_km"]), min(x[2] for x in e["bays_km"]), max(x[3] for x in e["bays_km"])]
                for x in m:
                    x["feature"] = e["id"] if "id" in e else e["name"]
        # dock doors (orange strips on the hull) belong to the bay group they sit against
        for c in cands:
            r = c["r"]
            if c["used"] or r["fill"] != "#ff8a3d" or r["h_m"] > 20:
                continue
            for e in sorted(b, key=lambda e: "bays_km" not in e):
                if "bays_km" not in e and "rect_km" in e and e["rect_km"][0] - 1e-3 <= r["x0"] and r["x1"] <= e["rect_km"][1] + 1e-3 and e["kind"] == "transport":
                    e.setdefault("doors_km", []).append([r["x0"], r["x1"], r["y0"], r["y1"]])
                    c["used"] = True
                    break
                if "bays_km" in e and any(bx[0] - 1e-3 <= r["x0"] and r["x1"] <= bx[1] + 1e-3 for bx in e["bays_km"]):
                    e.setdefault("doors_km", []).append([r["x0"], r["x1"], r["y0"], r["y1"]])
                    c["used"] = True
                    break
        poly = next((x["points_km"] for x in d["shapes"] if x["stroke"] == "#fff" and x["sw"] == "3"), None)
        if outline:
            poly = [[bounds[0], bounds[2]], [bounds[1], bounds[2]], [bounds[1], bounds[3]], [bounds[0], bounds[3]]]
        bounds = [min(q[0] for q in poly), max(q[0] for q in poly), min(q[1] for q in poly), max(q[1] for q in poly)]
        excl = [[c["cx"], c["cy"], c["r_km"]] for c in d["circles"] if c["stroke"] == "#ffc266" and c["r_km"] > 1]
        leftovers = [c["label"] or "(unlabelled %gx%g m)" % (c["r"]["w_m"], c["r"]["h_m"]) for c in cands if not c["used"] and "ATRIUM PLAZA" not in c["label"]]
        lanes = "%s–%s" % (sec["l0"], sec["l1"])
        p = {"id": pid, "name": sec["name"], "frames": "F%d–F%d" % (sec["f0"], sec["f1"]), "lanes": lanes,
             "bounds_km": bounds, "polygon_km": poly, "status": "proposed",
             "area_km2_stated": summary.get(pid, {}).get("area_km2"), "role": summary.get(pid, {}).get("role", ""),
             "intro": " ".join(sec["intro"]).strip(), "build_order": build_order.index(pid) + 1 if pid in build_order else None,
             "blueprint": svg_rel[:-4] + ".png", "blueprint_svg": svg_rel,
             "buildings": [], "streets": streets}
        if excl:
            p["exclude_circles_km"] = excl
            p["exclude_note"] = "Atrium Plaza (canon) is not part of the precinct"
        p["streets"] = [st for st in streets if "feature" not in st]
        for st in p["streets"]:
            st.pop("fill", None)
        if sec["extra"]:
            p["lanes_note"] = sec["extra"].strip(" ()")
        for i, e in enumerate(b, 1):
            e = dict(id="%s-%02d" % (pid, i), **e)
            p["buildings"].append(e)
        if leftovers:
            print(pid, "not imported from the SVG:", leftovers)
        precincts.append(p)
    data = {"schema": "invicta-atlas/precincts@1", "deck": 5, "district": "Port of Arrivals",
            "status": "proposed", "version": "v2", "updated": "2026-11-26",
            "doc": "Game/Docs/Port_of_Arrivals_Precincts.md",
            "overview_blueprint": "Game/Docs/art/blueprints/port-of-arrivals-precincts.png",
            "note": "Seeded 26 Nov 2026 from the precinct plans and blueprint SVGs. Proposed, awaiting Jordan.",
            "precincts": precincts}
    json.dump(data, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
