"""Add `about` ("What it does") to rooms, zones and fixtures in existing models that lack one.

Usage: python tools/add_room_about.py D5/port-of-arrivals
Reads the sentences from tools/room_programs/<district>_about.py (ABOUT, keyed by room name).
Only adds the new field; nothing else in the model changes. Prints names it has no sentence for.
"""
import glob, json, os, re, sys, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def stems(name):
    yield name
    s = re.sub(r"\s*\d+[A-Z]?$", "", name)
    yield s
    yield re.sub(r"^Bay [A-Z]$", "Bay X", s)
    yield re.sub(r"\s*[A-Z]$", "", s)
    yield re.sub(r"\d+$", "", s).strip()


def lookup(about, name):
    for s in stems(name.strip()):
        if s in about:
            return about[s]
    return None


def main(arg):
    deck, district = arg.split("/")
    mod = importlib.import_module("room_programs." + district.replace("-", "_") + "_about")
    about = mod.ABOUT
    missing, added = {}, 0
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "models", f"{deck}-{district}-*.json"))):
        text = open(f, encoding="utf-8").read()
        d = json.loads(text)
        indent = 1 if text.startswith("{\n \"") else 2
        changed = False
        for e in d.get("elements", []):
            if e.get("type") not in ("room", "zone", "fixture", "core") or e.get("about"):
                continue
            a = lookup(about, e.get("name", ""))
            if a:
                e["about"] = a; changed = True; added += 1
            else:
                missing.setdefault(e.get("name", ""), []).append(os.path.basename(f))
        if changed:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(d, fh, indent=indent, ensure_ascii=False)
                fh.write("\n" if text.endswith("\n") else "")
    print(f"added {added}; no sentence for {len(missing)} names")
    for n, fs in sorted(missing.items()):
        print(f"  {n!r}: {len(fs)} ({fs[0]})")


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main(sys.argv[1])
