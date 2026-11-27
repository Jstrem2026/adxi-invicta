"""Write readable docs for every designed area from the data, into Invicta/docs/.

    python tools/gen_docs.py

One page per district with a precinct plan, one per precinct (every building with its exact
numbers), and one per building that has a plan (levels, rooms, walls, doors, cores, with
dimensions and areas, plus an SVG drawing per level). Run on every approved change by the
GitHub workflow, so the repo always matches the site. Feet first, metric alongside.
"""

import json
import os
import shutil
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
from atlaslib.sources import find_root  # noqa: E402
from atlaslib.server import build  # noqa: E402

FT = 3.28084
OUT = os.path.join(APP, "docs")


def ft(m):
    inch = round(m * FT * 12)
    f, i = divmod(inch, 12)
    return f"{f:,} ft {i} in" if i else f"{f:,} ft"


def both(m):
    return f"{ft(m)} ({m:,.0f} m)" if m >= 10 else f"{ft(m)} ({m * 1000:,.0f} mm)"


def area_m2(a):
    return f"{a * FT * FT:,.0f} sq ft ({a:,.0f} m²)"


def poly_area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def cell(v):
    return "not designed yet" if v in (None, "") else str(v).replace("|", "\\|").replace("\n", " ")


def plan_svg(model, level):
    L, W = model.get("footprint_m", [100, 100])
    pad = max(L, W) * 0.08
    fs = max(L, W) / 45
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad:.1f} {-pad:.1f} {L + 2 * pad:.1f} {W + 2 * pad:.1f}" font-family="Segoe UI, sans-serif">',
           f'<rect x="{-pad}" y="{-pad}" width="{L + 2 * pad}" height="{W + 2 * pad}" fill="#0a1a2e"/>',
           f'<rect x="0" y="0" width="{L}" height="{W}" fill="none" stroke="#e8f1fb" stroke-width="{fs / 6:.2f}"/>']
    g = model.get("grid_m")
    if g:
        x = 0.0
        while x <= L + 0.01:
            out.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{W}" stroke="#6fd0ff" stroke-opacity=".15" stroke-width="{fs / 20:.2f}"/>'); x += g
        y = 0.0
        while y <= W + 0.01:
            out.append(f'<line x1="0" y1="{y}" x2="{L}" y2="{y}" stroke="#6fd0ff" stroke-opacity=".15" stroke-width="{fs / 20:.2f}"/>'); y += g
    els = [e for e in model.get("elements", []) if level in (e.get("levels") or [e.get("level")])]
    col = {"room": ("rgba(111,208,255,.15)", "#cfe8ff"), "core": ("rgba(255,184,77,.35)", "#ffb84d"), "mass": ("none", "#b99cff")}
    for e in els:
        if e.get("outline_m"):
            f, s = col.get(e["type"], ("none", "#e8f1fb"))
            pts = " ".join(f"{p[0]},{p[1]}" for p in e["outline_m"])
            out.append(f'<polygon points="{pts}" fill="{f}" stroke="{s}" stroke-width="{fs / 10:.2f}"/>')
            cx = sum(p[0] for p in e["outline_m"]) / len(e["outline_m"]); cy = sum(p[1] for p in e["outline_m"]) / len(e["outline_m"])
            out.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="{fs * 0.8:.1f}" fill="#e8f1fb" text-anchor="middle">{e.get("name", e["id"])}</text>')
        elif e.get("line_m"):
            a, b = e["line_m"][0], e["line_m"][-1]
            c = "#5fd39a" if e["type"] in ("door", "opening") else "#e8f1fb"
            w = fs / 3 if e["type"] in ("door", "opening") else max(e.get("thickness_m", 0.3), fs / 6)
            out.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{c}" stroke-width="{w:.2f}"/>')
    out.append(f'<text x="{L / 2}" y="{-pad / 3:.1f}" font-size="{fs:.1f}" fill="#ffc266" text-anchor="middle">{both(L)}</text>')
    out.append(f'<text x="{-pad / 3:.1f}" y="{W / 2}" font-size="{fs:.1f}" fill="#ffc266" text-anchor="middle" transform="rotate(-90 {-pad / 3:.1f} {W / 2})">{both(W)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    root = find_root(APP)
    data = build(root)
    models = {}
    mdir = os.path.join(APP, "data", "models")
    if os.path.isdir(mdir):
        for n in sorted(os.listdir(mdir)):
            if n.endswith(".json"):
                with open(os.path.join(mdir, n), encoding="utf-8") as f:
                    m = json.load(f)
                models[m.get("building_uid") or n[:-5]] = m
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    index = ["# ADXI: Invicta, design documentation", "",
             "Generated from the data on every approved change. Do not edit by hand: change the data (or ask the site chat) instead.", "",
             "Measurements: feet first, metric in brackets. Positions: km from the prow tip (x) and across the beam (y, port negative).", ""]
    for did, ps in sorted(data["model"]["precinct_sets"].items()):
        ddir = os.path.join(OUT, did)
        os.makedirs(ddir, exist_ok=True)
        dname = ps.get("district", did)
        deck = next((dk for dk in data["model"]["decks"] if dk["n"] == ps.get("deck")), {})
        fnum = next((i + 1 for i, x in enumerate(deck.get("districts", [])) if x.get("name") == dname or x.get("id") == did.split("-", 1)[-1]), "?")
        index.append(f"- [Deck {ps.get('deck')} · {dname}]({did}/README.md): {len(ps['precincts'])} precincts")
        dpage = [f"# Deck {ps.get('deck')} · {dname}", "", f"Status: {ps.get('status')} · data: `{ps.get('file')}` · design doc: `{ps.get('doc')}`", "",
                 "| Precinct | Frames | Lanes | Area | Buildings |", "|---|---|---|---|---|"]
        for p in ps["precincts"]:
            a = p.get("area_calc") or p.get("area_km2_stated") or 0
            dpage.append(f"| [{p['id']} {p['name']}]({p['id']}.md) | {cell(p.get('frames'))} | {cell(p.get('lanes'))} | {a * 247.105:,.1f} acres ({a:,.3f} km²) | {len(p.get('buildings', []))} |")
            pp = [f"# {p['id']} {p['name']}", "", f"Deck {ps.get('deck')} · {dname} · status {p.get('status')}", "", cell(p.get("intro")), "",
                  f"Bounds: x {p['bounds_km'][0]}–{p['bounds_km'][1]} km, y {p['bounds_km'][2]} to {p['bounds_km'][3]} km", "",
                  "| ID | Designation | Building | Address | Status | Size | Ground area | Position (x, y km) | Height | Floors | Capacity |", "|---|---|---|---|---|---|---|---|---|---|---|"]
            for b in p.get("buildings", []):
                r = b.get("rect_km")
                size = f"{ft((r[1] - r[0]) * 1000)} × {ft((r[3] - r[2]) * 1000)} ({(r[1] - r[0]) * 1000:,.0f} × {(r[3] - r[2]) * 1000:,.0f} m)" if r else cell(b.get("size_text"))
                ga = area_m2((r[1] - r[0]) * (r[3] - r[2]) * 1e6) if r else "—"
                pos = f"{r[0]}–{r[1]}, {r[2]} to {r[3]}" if r else "—"
                name = b["name"]
                if b.get("uid") in models:
                    name = f"[{name}]({p['id']}/{b['id']}.md)"
                addr, desig = "—", f"D{ps.get('deck')}-F{fnum}-P{str(p['id']).lstrip('P')}"
                for blk in p.get("blocks") or []:
                    ids = [c.get("id") for c in blk.get("contents", [])]
                    if b["id"] in ids:
                        addr = f"{blk['id']}, building {ids.index(b['id']) + 1}"
                        bn = "".join(ch for ch in blk.get("name", "") if ch.isdigit())
                        desig += (f"-B{bn}" if bn else "") + f"-A{ids.index(b['id']) + 1}"
                        break
                pp.append(f"| {b['id']} | {desig} | {name} | {addr} | {b.get('status')} | {size} | {ga} | {pos} | {both(b['height_m']) if b.get('height_m') else 'not designed yet'} | {cell(b.get('floors'))} | {cell(b.get('capacity'))} |")
                m = models.get(b.get("uid"))
                if m:
                    bdir = os.path.join(ddir, p["id"]); os.makedirs(bdir, exist_ok=True)
                    bp = [f"# {b['id']} {b['name']}: plan", "", f"Footprint {both(m['footprint_m'][0])} × {both(m['footprint_m'][1])}"
                          + (f" · structural grid {both(m['grid_m'])}" if m.get("grid_m") else ""), "",
                          "## Levels", "", "| Level | Floor above deck | Height | Floor area |", "|---|---|---|---|"]
                    for lv in m.get("levels", []):
                        rooms = [e for e in m.get("elements", []) if e["type"] == "room" and lv["id"] in (e.get("levels") or [e.get("level")])]
                        bp.append(f"| {lv['name']} | {both(lv['z_m']) if lv['z_m'] >= 0 else '−' + both(-lv['z_m'])} | {both(lv['height_m'])} | {area_m2(sum(poly_area(e['outline_m']) for e in rooms)) if rooms else '—'} |")
                    bp += ["", "## Elements", "", "| ID | Designation | Type | Name | Level(s) | Size / length | Area | Status |", "|---|---|---|---|---|---|---|---|"]
                    numbered = [x for x in m.get("elements", []) if x["type"] in ("room", "zone", "core")]
                    for e in m.get("elements", []):
                        if e.get("outline_m"):
                            xs = [q[0] for q in e["outline_m"]]; ys = [q[1] for q in e["outline_m"]]
                            sz = f"{both(max(xs) - min(xs))} × {both(max(ys) - min(ys))}"; ar = area_m2(poly_area(e["outline_m"]))
                        else:
                            a_, b_ = e["line_m"][0], e["line_m"][-1]
                            sz = both(((a_[0] - b_[0]) ** 2 + (a_[1] - b_[1]) ** 2) ** 0.5) + (f", {both(e['width_m'])} wide" if e.get("width_m") else ""); ar = "—"
                        dz = f"{desig}-R{numbered.index(e) + 1}" if e in numbered else ""
                        bp.append(f"| {e['id']} | {dz} | {e['type']} | {cell(e.get('name'))} | {', '.join(e.get('levels') or [e.get('level')])} | {sz} | {ar} | {e.get('status')} |")
                    bp += ["", "## Drawings", ""]
                    for lv in m.get("levels", []):
                        fn = f"{b['id']}-{lv['id']}.svg"
                        with open(os.path.join(bdir, fn), "w", encoding="utf-8") as f:
                            f.write(plan_svg(m, lv["id"]))
                        bp += [f"### {lv['name']}", "", f"![{lv['name']}]({fn})", ""]
                    with open(os.path.join(bdir, f"{b['id']}.md"), "w", encoding="utf-8") as f:
                        f.write("\n".join(bp) + "\n")
            with open(os.path.join(ddir, f"{p['id']}.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(pp) + "\n")
        with open(os.path.join(ddir, "README.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(dpage) + "\n")
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index) + "\n")
    print("Docs written to %s" % OUT)


if __name__ == "__main__":
    main()
