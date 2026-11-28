"""City planner (Jordan, 28 Nov 2026): check a district against its purpose and fill the gaps.

    python tools/city_planner.py D5-port-of-arrivals            check only: print what is there and what is missing
    python tools/city_planner.py D5-port-of-arrivals --report   also write Game/Docs/<District>_Planner.md (and its mirror)
    python tools/city_planner.py D5-port-of-arrivals --apply    add the planner's proposals to the district data and its
                                                                design doc as 'proposed', after saving a backup

The district's program (what it needs to do its job) is in data/city_programs.json. --apply never moves,
resizes or removes anything already designed: it only adds new items, or doors to an item that has none.
The backup of the data file goes to backups/ (not in git) and the old file stays in git history.
After --apply run: python tools/purposes.py, python tools/doc_codes.py, python atlas.py --scan.
"""
import copy
import datetime
import json
import os
import re
import shutil
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(APP)
sys.path.insert(0, APP)
from atlaslib import planner as PL  # noqa: E402
from atlaslib import geometry as G  # noqa: E402

TICK, GAP, NOTE = "✅", "⚠️", "ℹ️"


def L(km):
    return G.fmt_len_m(km * 1000)


def dump_like(raw, data):
    """Write the data back in the same layout as the file it came from (the district files are one line)."""
    m = re.match(r'\{\n( +)"', raw)
    if m:
        txt = json.dumps(data, ensure_ascii=False, indent=len(m.group(1)))
    elif raw.startswith('{"schema": '):
        txt = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))
    else:
        txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return txt + ("\n" if raw.endswith("\n") else "")


def _w(dr):
    return G.fmt_len_m(dr["width_m"]) if dr["width_m"] else "see note"


def report(d, prog, res, props, after=None, gaps=()):
    """The planner's findings in plain words (Markdown)."""
    name = d["district"]
    o = ["# %s: city planner check" % name, "",
         "Made by `Invicta/tools/city_planner.py` on %s from the program in `Invicta/data/city_programs.json`. "
         "It checks the district against what it is for and lists what is missing. Items marked "
         "**proposed** are the planner's suggestions; nothing already designed was moved or removed." % datetime.date.today().isoformat(), "",
         "**What this district is for** (%s): %s" % (prog["source"], prog["purpose"]), ""]
    o += ["## 1. Doors in the hull", "",
          "| Kind of door | Used by | Doors | Widths | Opened by | Check |", "|---|---|---|---|---|---|"]
    for c in res["classes"]:
        cl = c["cls"]
        drs = [dr for dr in res["doors"] if dr["cls"] == cl["id"]]
        widths = sorted({_w(dr) for dr in drs})
        ok = NOTE + " left for Jordan" if cl.get("min", 1) == 0 else (TICK if c["ok"] else GAP)
        why = ""
        if c["no_doors"]:
            why = " %s has no door to space." % ", ".join(b["name"] for b in c["no_doors"])
        elif not c["ok"] and cl.get("min", 1):
            why = " Needs at least %d." % cl["min"]
        o.append("| %s | %s | %d | %s | %s | %s%s |" % (cl["name"], cl["use"], c["count"], ", ".join(widths) or "none",
                                                     ", ".join(sorted({b["name"] for b in c["control"]})) or "nobody yet", ok, why))
    o += ["", "Pressure zones: the hull front has %d zones (one per 1,640 ft (500 m) frame). %d of them have a crew airlock." %
          (len(res["zones"]), sum(1 for z in res["zones"] if z["airlocks"])), ""]
    for c in prog["door_classes"]:
        if c.get("why"):
            o.append("- **%s:** %s" % (c["name"], c["why"]))
    o += ["", "## 2. Help within reach of every door", "",
          "| Service | Must be within | Doors out of reach | Furthest |", "|---|---|---|---|"]
    for rr in res["response"]:
        far = rr["far"]
        worst = max((x[2] or 0 for x in far), default=0)
        o.append("| %s | %s | %s %d of %d | %s |" % (rr["rule"]["name"], L(rr["rule"]["within_km"]), TICK if not far else GAP,
                                                    len(far), rr["count"], L(worst) if far else "-"))
    cl = res["clearance"]
    if cl:
        worst = max((x[2] or 0 for x in cl["far"]), default=0)
        o.append("| %s | %s | %s %d of %d | %s |" % (cl["rule"]["name"], L(cl["rule"]["within_km"]), TICK if not cl["far"] else GAP,
                                                    len(cl["far"]), cl["count"], L(worst) if cl["far"] else "-"))
    o += [""] + ["- **%s:** %s" % (r["name"], r["why"]) for r in prog.get("response", []) + ([cl["rule"]] if cl else [])]
    if prog.get("response_neighbours"):
        o += ["", "Fire, police and medical buildings just over the district line count too (%s)." %
              ", ".join(sorted({b["_district"] for b in prog.get("_near", [])}))]
    o += ["", "Distances are straight lines from the middle of each door to the nearest wall of the building. All are planner assumptions for Jordan to confirm.", "",
          "## 3. Security and services the port must have", "", "| Need | Found in | Check |", "|---|---|---|"]
    for m in res["must_have"]:
        o.append("| %s | %s | %s |" % (m["rule"]["name"], ", ".join(b["name"] for b in m["got"][:5]) or "nothing yet", TICK if m["ok"] else GAP))
    miss = [m for m in res["per_precinct"] if not m["ok"]]
    o += ["", "Every precinct has its own utility plant and service shaft." if not miss else
          "Precincts missing a basic service: " + "; ".join("%s %s (%s)" % (m["precinct"]["id"], m["precinct"]["name"], m["rule"]["name"]) for m in miss)]
    o += ["", "## 4. What the planner adds (proposed)", ""]
    if not props:
        o.append("Nothing: the district meets its program.")
    for x in props:
        if "building" in x:
            b = x["building"]
            r = b["rect_km"]
            o.append("- **%s %s** in %s, %s, at %s. %s%s" % (b["id"], b["name"], x["precinct"], b["size_text"],
                                                          G.address(5, (r[0] + r[1]) / 2, (r[2] + r[3]) / 2), b["purpose"],
                                                          (" No room found in: %s." % ", ".join(x["no_room"])) if x.get("no_room") else ""))
        else:
            o.append("- **%s %s**: %d new doors in the hull (%s)." % (x["add_to"], x["name"], len(x["value"]), x["note"]))
    if after is not None:
        o += ["", "### After the additions", ""]
        nofit = list(gaps)
        gaps = [c["cls"]["name"] for c in after["classes"] if not c["ok"] and c["cls"].get("min", 1)]
        gaps += ["%s (%d doors out of reach)" % (rr["rule"]["name"], len(rr["far"])) for rr in after["response"] if rr["far"]]
        if after["clearance"] and after["clearance"]["far"]:
            gaps.append("Border clearance (%d doors out of reach)" % len(after["clearance"]["far"]))
        gaps += [m["rule"]["name"] for m in after["must_have"] if not m["ok"]]
        gaps += ["%s zone %s has no crew airlock" % (z["precinct"], z["frame"]) for z in after["zones"] if not z["airlocks"]]
        o.append("Still missing: " + "; ".join(gaps) + "." if gaps else "%s Every check passes." % TICK)
        if nofit:
            o += ["", "The planner found no free land for these (every lot near those doors is taken):", ""] + ["- %s." % g for g in nofit]
    o += ["", "## 5. Left for Jordan", ""]
    o += ["- %s: %s" % (c["name"], c["why"]) for c in prog["door_classes"] if c.get("min", 1) == 0 and c.get("why")]
    o += ["- Escape craft and lifeboats are not designed anywhere on the ship yet, so the planner does not place any.",
          "- Room plans, heights and looks of the new items are not designed yet."]
    if prog.get("decisions"):
        o += ["", "## 6. Decided by Jordan", ""] + ["- %s" % x for x in prog["decisions"]]
    return "\n".join(o) + "\n"


def add_doc_rows(doc_text, props, d):
    """Add a row for each new item to its precinct's table in the design doc."""
    lines = doc_text.split("\n")
    for x in props:
        if "building" not in x:
            continue
        b = x["building"]
        p = next(q for q in d["precincts"] if q["id"] == x["precinct"])
        head = next((i for i, ln in enumerate(lines) if ln.startswith("## %s · " % p["id"])), None)
        if head is None:
            continue
        i = head + 1
        while i < len(lines) and not lines[i].startswith("|"):
            i += 1
        while i < len(lines) and lines[i].startswith("|"):
            i += 1
        cols = lines[head + 1:i][-1].count("|") - 1 if i > head + 1 else 4
        row = ["%s" % b["name"], b["size_text"], "**Proposed** by the city planner · %s" % b["notes"]] + [""] * max(0, cols - 3)
        lines.insert(i, "| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    did = argv[0]
    progs, prog = PL.load_program(APP, did)
    path, raw, d = PL.load_district(APP, prog)
    res = PL.check(d, prog)
    gaps = []
    props = PL.propose(d, prog, res, gaps)
    d2 = copy.deepcopy(d)
    PL.apply(d2, props)
    after = PL.check(d2, prog)
    text = report(d, prog, res, props, after, gaps)
    print(text)
    if "--report" in argv or "--apply" in argv:
        rel = "Game/Docs/%s_Planner.md" % d["district"].replace(" ", "_")
        for out in (os.path.join(ROOT, rel), os.path.join(ROOT, rel.replace("Game/Docs/", "Docs/2_Design_Docs/"))):
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "w", encoding="utf-8", newline="\n").write(text)
        print("Wrote", rel, "and its mirror")
    if "--apply" in argv:
        bk = os.path.join(APP, "backups")
        os.makedirs(bk, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        shutil.copy2(path, os.path.join(bk, "%s-before-planner-%s.json" % (did, stamp)))
        done = PL.apply(d, props)
        d["updated"] = datetime.date.today().isoformat()
        open(path, "w", encoding="utf-8", newline="\n").write(dump_like(raw, d))
        doc = os.path.join(ROOT, d["doc"])
        dt = open(doc, encoding="utf-8").read()
        shutil.copy2(doc, os.path.join(bk, "%s-before-planner-%s.md" % (os.path.basename(doc)[:-3], stamp)))
        nt = add_doc_rows(dt, done, d)
        for out in (doc, doc.replace(os.path.join("Game", "Docs"), os.path.join("Docs", "2_Design_Docs"))):
            open(out, "w", encoding="utf-8", newline="\n").write(nt)
        print("Added %d items to %s (backup in %s)" % (len(done), prog["file"], bk))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
