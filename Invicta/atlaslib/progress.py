"""Progress of designing the Invicta, level by level, measured from the data."""

from . import geometry as G


def progress(model, issues):
    decks = model["decks"]
    psets = model["precinct_sets"]
    total_area = sum(d.get("net_area_calc") or d.get("net_area_stated") or 0 for d in decks)
    districts = [x for d in decks for x in d["districts"]]
    real = [x for x in districts if not x["is_plaza"]]
    planned = [x for x in real if x.get("precinct_set")]
    precincts = [p for ps in psets.values() for p in ps["precincts"]]
    buildings = [b for p in precincts for b in p["buildings"]]
    blocks = [blk for p in precincts for blk in p.get("blocks", [])]
    used_blocks = [blk for blk in blocks if blk["contents"]]
    est_blocks = int(round(total_area / 0.25))
    status = {}
    for b in buildings:
        status[b.get("status", "proposed")] = status.get(b.get("status", "proposed"), 0) + 1
    detailed = [b for b in buildings if b.get("height_m") and b.get("kind") != "transport"]
    planned_area = sum(x["area_km2"] or 0 for x in planned)
    per_deck = []
    for d in decks:
        ds = [x for x in d["districts"] if not x["is_plaza"]]
        pa = sum(x["area_km2"] or 0 for x in ds if x.get("precinct_set"))
        n_b = sum(len(p["buildings"]) for ps in psets.values() if ps["deck"] == d["n"] for p in ps["precincts"])
        n_p = sum(len(ps["precincts"]) for ps in psets.values() if ps["deck"] == d["n"])
        per_deck.append({
            "n": d["n"], "name": d["name"], "role": d.get("role", ""),
            "net_area": d.get("net_area_calc") or d.get("net_area_stated"),
            "districts": len(ds), "districts_planned": sum(1 for x in ds if x.get("precinct_set")),
            "planned_area": pa, "precincts": n_p, "buildings": n_b,
            "canon_sheet": bool(d.get("key")),
            "issues": sum(1 for i in issues if i["severity"] in ("error", "warning") and not i["known"]
                          and (i.get("entity") or "").startswith("D%d" % d["n"])),
        })
    levels = [
        {"level": "Ship", "have": 1, "of": 1, "state": "canon", "note": "Sheet S0, hull plan and side profile (Rev B)"},
        {"level": "Deck cities", "have": sum(1 for d in decks if d.get("key")), "of": 8, "state": "canon", "note": "Data sheets S1 to S8 with plans"},
        {"level": "Districts", "have": len(real), "of": len(real), "state": "canon",
         "note": "%d districts plus %d central plazas, all with areas, roles and shapes" % (len(real), len(districts) - len(real))},
        {"level": "Precincts", "have": len(planned), "of": len(real), "state": "proposed" if planned else "not started",
         "note": "%d of %d districts have a precinct plan (%d precincts)" % (len(planned), len(real), len(precincts))},
        {"level": "Blocks", "have": len(used_blocks), "of": est_blocks, "state": "proposed" if used_blocks else "not started",
         "note": "%d of about %s blocks (500 × 500 m) hold something" % (len(used_blocks), "{:,}".format(est_blocks))},
        {"level": "Buildings", "have": len(buildings), "of": None, "state": "proposed" if buildings else "not started",
         "note": "%d placed; %d canon, %d proposed, %d assumption" % (len(buildings), status.get("canon", 0), status.get("proposed", 0), status.get("assumption", 0))},
        {"level": "Architecture", "have": len(detailed), "of": len([b for b in buildings if b.get("kind") != "transport"]), "state": "started" if detailed else "not started",
         "note": "Buildings with a height (floors, structure and interiors not designed yet)"},
    ]
    sev = {}
    for i in issues:
        k = i["severity"] + ("_known" if i["known"] else "")
        sev[k] = sev.get(k, 0) + 1
    er = model.get("errata") or {}
    return {
        "total_area_km2": round(total_area, 1), "total_area_text": G.fmt_area_km2(total_area),
        "planned_area_km2": round(planned_area, 1), "planned_pct": round(100 * planned_area / total_area, 2) if total_area else 0,
        "levels": levels, "decks": per_deck, "issues": sev,
        "errata": {"decided": er.get("decided", 0), "proposed": er.get("proposed", 0)},
        "buildings_by_status": status,
    }
