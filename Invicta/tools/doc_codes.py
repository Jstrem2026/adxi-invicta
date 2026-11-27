"""Put each building's designation code next to its name in the precinct design docs.

    python tools/doc_codes.py          update Game/Docs/*_Precincts.md and their Docs/2_Design_Docs mirrors

In every precinct section ("## P2 · Arrivals — F41 to F46, lanes A–C") the building table gets a last
column "Code" holding the designation, for example D5F3P2B5A1, the same code the app shows. Block tables
get the block code (D3F2P1B1). Rows are matched by name, so nothing else in the table changes. Run it after
buildings are added or moved; the scan does not need it, it is for people reading the docs.
"""
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
from atlaslib.sources import find_root  # noqa: E402
from atlaslib.server import build  # noqa: E402

HEAD = re.compile(r"^## (P\d+) · ")


def codes_for(ps, deck):
    """{precinct id: ({building name: code}, {block cell text: code})}"""
    did = ps.get("district_id") or ""
    fnum = next((i + 1 for i, x in enumerate(deck.get("districts", []))
                 if x.get("name") == ps.get("district") or x.get("id") == did.split("-", 1)[-1]), "?")
    out = {}
    for p in ps["precincts"]:
        base = "D%sF%sP%s" % (ps.get("deck"), fnum, str(p["id"]).lstrip("P"))
        names, blocks = {}, {}
        for blk in p.get("blocks") or []:
            bn = "".join(ch for ch in blk.get("name", "") if ch.isdigit())
            if bn:
                blocks["B%s" % bn] = base + "B" + bn
        for b in p.get("buildings", []):
            code = base
            for blk in p.get("blocks") or []:
                ids = [c.get("id") for c in blk.get("contents", [])]
                if b["id"] in ids:
                    bn = "".join(ch for ch in blk.get("name", "") if ch.isdigit())
                    code += ("B%s" % bn if bn else "") + "A%d" % (ids.index(b["id"]) + 1)
                    break
            names[b["name"].strip().lower()] = code
        out[p["id"]] = (names, blocks)
    return out


def update(text, codes):
    lines = text.split("\n")
    pid = None
    i = 0
    while i < len(lines):
        m = HEAD.match(lines[i])
        if lines[i].startswith("## "):
            pid = m.group(1) if m else None
        if pid in codes and lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-", lines[i + 1]):
            names, blocks = codes[pid]
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            has = header[-1] == "Code"
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            found = []
            for r in rows:
                k = r[0].replace("**", "").strip()
                c = names.get(k.lower()) or blocks.get(k.split(" ")[0]) or ""
                found.append(c)
            if any(found):
                if not has:
                    header.append("Code")
                lines[i] = "| " + " | ".join(header) + " |"
                lines[i + 1] = "|" + "---|" * len(header)
                for n, r in enumerate(rows):
                    if has:
                        r = r[:-1]
                    r = r + [found[n] or "—"]
                    lines[i + 2 + n] = "| " + " | ".join(r) + " |"
            i = j
            continue
        i += 1
    return "\n".join(lines)


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    root = find_root(APP)
    data = build(root)
    decks = {d["n"]: d for d in data["model"]["decks"]}
    for did, ps in data["model"]["precinct_sets"].items():
        doc = ps.get("doc")
        if not doc:
            continue
        codes = codes_for(ps, decks.get(ps.get("deck"), {}))
        for rel in (doc, doc.replace("Game/Docs/", "Docs/2_Design_Docs/", 1)):
            full = os.path.join(root, *rel.split("/"))
            if not os.path.isfile(full):
                continue
            raw = open(full, "rb").read()
            crlf = b"\r\n" in raw
            text = raw.decode("utf-8").replace("\r\n", "\n")
            new = update(text, codes)
            if new != text:
                open(full, "wb").write((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
                print("Updated", rel)


if __name__ == "__main__":
    main()
