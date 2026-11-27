"""What each building is for (Jordan, 27 Nov 2026: "I need a description of the purpose of every building").

Every building stores a short "purpose" paragraph in its data file: what the building is for, who uses
it and what happens there. This tool keeps the design docs in step with the data:

    python tools/purposes.py              rewrite the "What each building is for" section of every
                                          district's design doc (and its mirror) from the data files
    python tools/purposes.py --load DIR   first store purposes from DIR/<deck>-<district>.json files
                                          ({"P2-12": "...", "Rack Hall": "... {p} ... {notes}"});
                                          a key is a building id, or a name without its number for a
                                          whole family of numbered buildings; {p} is the precinct name and
                                          {notes} the building's notes. Purposes already in the data win.

seed_deck5_districts.py keeps each building's purpose when it rebuilds a district and calls doc_section().
"""
import json
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECKS = os.path.join(APP, "data", "decks")
sys.path.insert(0, APP)
from atlaslib.purposes import family, doc_section, put_section, write_docs, keep_purposes  # noqa: E402,F401
def dump_like(raw, data):
    m = re.match(r'\{\n( +)"', raw)
    if m:
        txt = json.dumps(data, ensure_ascii=False, indent=len(m.group(1)))
    elif raw.startswith('{"schema": '):
        txt = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))
    else:
        txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return txt + ("\n" if raw.endswith("\n") else "")


def main():
    src = sys.argv[sys.argv.index("--load") + 1] if "--load" in sys.argv else None
    for deck in sorted(os.listdir(DECKS)):
        for fn in sorted(os.listdir(os.path.join(DECKS, deck))):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(DECKS, deck, fn)
            raw = open(path, encoding="utf-8").read()
            data = json.loads(raw)
            missing = []
            if src:
                sp = os.path.join(src, "%s-%s" % (deck, fn))
                given = json.load(open(sp, encoding="utf-8")) if os.path.isfile(sp) else {}
                for p in data["precincts"]:
                    for b in p["buildings"]:
                        if b.get("purpose"):
                            continue
                        t = given.get(b["id"]) or given.get(family(b["name"]))
                        if t:
                            notes = (b.get("notes") or "").split(" · ")[0].strip().rstrip(".")
                            b["purpose"] = t.replace("{p}", p["name"]).replace("{notes}", notes)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(dump_like(raw, data))
            for p in data["precincts"]:
                missing += [b["id"] for b in p["buildings"] if not b.get("purpose")]
            write_docs(data)
            n = sum(len(p["buildings"]) for p in data["precincts"])
            print("%s/%-22s %d of %d buildings have a purpose%s" % (deck, fn[:-5], n - len(missing), n,
                  (" · missing: " + ", ".join(missing[:12])) if missing else ""))


if __name__ == "__main__":
    main()
