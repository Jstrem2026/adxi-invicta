"""Building purposes (Jordan, 27 Nov 2026): the "What each building is for" section of a design doc.

Shared by tools/purposes.py, tools/seed_deck5_districts.py and the scanner, which checks that each
design doc lists the same purposes as its data file.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
START, END = "<!-- purposes:start -->", "<!-- purposes:end -->"


def family(name):
    """The name without its trailing number: Rack Hall 7 -> Rack Hall."""
    return re.sub(r"\s*\d+[A-Z]?$", "", name or "").strip()


def doc_section(data):
    """Markdown section listing every building's purpose, precinct by precinct."""
    out = [START, "## What each building is for", "",
           "Each building's purpose (Jordan asked for one for every building, 27 Nov 2026). These describe "
           "the use of each building as planned; they follow each building's own status.", ""]
    for p in data["precincts"]:
        rows = [b for b in p["buildings"] if b.get("purpose")]
        if not rows:
            continue
        out.append("### %s %s" % (p["id"], p["name"]))
        out.append("")
        for b in rows:
            out.append("- **%s %s**: %s" % (b["id"], b["name"], b["purpose"]))
        out.append("")
    out.append(END)
    return "\n".join(out)


def put_section(doc_text, section):
    if START in doc_text and END in doc_text:
        a = doc_text.index(START)
        b = doc_text.index(END) + len(END)
        return doc_text[:a] + section + doc_text[b:]
    return doc_text.rstrip("\n") + "\n\n" + section + "\n"


def write_docs(data):
    rel = data.get("doc")
    if not rel:
        return
    for base in ("Game/Docs", "Docs/2_Design_Docs"):
        path = os.path.join(ROOT, base, rel.split("/", 2)[2]) if rel.startswith("Game/Docs/") else None
        if not path or not os.path.isfile(path):
            continue
        s = open(path, encoding="utf-8").read()
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(put_section(s, doc_section(data)))


def keep_purposes(old, new):
    """Copy purposes from an earlier version of a data file onto the rebuilt one (by id and name, then name)."""
    by_both, by_name = {}, {}
    for p in old.get("precincts", []):
        for b in p["buildings"]:
            if b.get("purpose"):
                by_both[(b["id"], b["name"])] = b["purpose"]
                by_name.setdefault(b["name"], b["purpose"])
    for p in new["precincts"]:
        for b in p["buildings"]:
            if not b.get("purpose"):
                t = by_both.get((b["id"], b["name"])) or by_name.get(b["name"])
                if t:
                    b["purpose"] = t


def doc_part(text):
    """The purposes section of a doc, or None."""
    if START in text and END in text:
        return text[text.index(START):text.index(END) + len(END)]
    return None
