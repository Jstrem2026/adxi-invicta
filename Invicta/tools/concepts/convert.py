"""Turn rendered PNGs into the WebP concept images the site shows, and record them on each building.

    python tools/concepts/convert.py D5/atrium-plaza PNG_DIR

Writes Invicta/data/renders/D<deck>/<district>/<id>.webp (1280 x 800, quality 80) and sets the building's
"concept_render" field to that path. The PNGs are left where they are.
"""
import json
import os
import re
import sys

from PIL import Image

APP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(APP, "data")


def main():
    file, png_dir = sys.argv[1], sys.argv[2]
    path = os.path.join(DATA, "decks", *file.split("/")) + ".json"
    raw = open(path, encoding="utf-8").read()
    data = json.loads(raw)
    rel_dir = "Invicta/data/renders/%s" % file
    out_dir = os.path.join(DATA, "renders", *file.split("/"))
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    for p in data["precincts"]:
        for b in p["buildings"]:
            src = os.path.join(png_dir, b["id"] + ".png")
            if not os.path.isfile(src):
                continue
            Image.open(src).convert("RGB").save(os.path.join(out_dir, b["id"] + ".webp"), "WEBP", quality=80, method=6)
            b["concept_render"] = "%s/%s.webp" % (rel_dir, b["id"])
            n += 1
    sys.path.insert(0, os.path.join(APP, "tools"))
    from design_rooms import dump_like
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump_like(raw, data))
    print("%d concept renders written to %s" % (n, rel_dir))


if __name__ == "__main__":
    main()
