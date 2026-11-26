"""Where the app reads from. Every path is relative to the ArcaneDrift root
(the folder that holds Docs, Game and Invicta). The app only reads these
files; it never writes to them."""

import os
import glob

CANON = "Docs/1_Canon_Source/Invicta"
GAME_DOCS = "Game/Docs"
MIRROR_DOCS = "Docs/2_Design_Docs"

DECK_NAMES = {1: "Solenne", 2: "Halcyon", 3: "Meridian", 4: "Bastion",
              5: "Aerion", 6: "Machina", 7: "Claustra", 8: "Ferrum"}

FIXED = {
    "ship_sheet": CANON + "/datasheets/00-Ship.html",
    "crown_sheet": CANON + "/datasheets/09-Crown-Bridge.html",
    "zones_csv": CANON + "/architecture/zone_reservations_km.csv",
    "frames_csv": CANON + "/architecture/frames_F0_F68.csv",
    "hull_plan_csv": CANON + "/architecture/hull_plan_km.csv",
    "hull_side_csv": CANON + "/architecture/hull_side_profile_km.csv",
    "hull_side_revB_csv": GAME_DOCS + "/geometry_revB/hull_side_profile_km_revB.csv",
    "revB_readme": GAME_DOCS + "/geometry_revB/README.txt",
    "errata_md": GAME_DOCS + "/02_Canon_Errata.md",
    "reference_md": GAME_DOCS + "/Invicta_Ship_Reference.md",
    "precincts_md": GAME_DOCS + "/Port_of_Arrivals_Precincts.md",
    "game_geometry_py": "Game/Tools/InvictaGraybox/invicta_geometry.py",
}


def deck_paths(n):
    name = DECK_NAMES[n]
    return {
        "sheet": "%s/datasheets/%02d-Deck-%d-%s.html" % (CANON, n, n, name),
        "sheet_pdf": "%s/datasheets/pdf/%02d-Deck-%d-%s.pdf" % (CANON, n, n, name),
        "net_canon": "%s/architecture/deck%d_%s_net_km.csv" % (CANON, n, name),
        "gross_canon": "%s/architecture/deck%d_%s_gross_km.csv" % (CANON, n, name),
        "net_revB": "%s/geometry_revB/deck%d_%s_net_km_revB.csv" % (GAME_DOCS, n, name),
        "gross_revB": "%s/geometry_revB/deck%d_%s_gross_km_revB.csv" % (GAME_DOCS, n, name),
        "render": "%s/assets/renders-and-art/Luxuria-Invicta-%02d-%s.png" % (CANON, n, name),
        "emblem": "%s/blueprints/emblems/d%d.png" % (CANON, n),
    }


class Root:
    def __init__(self, root):
        self.root = os.path.abspath(root)

    def abs(self, rel):
        return os.path.join(self.root, *rel.split("/"))

    def exists(self, rel):
        return os.path.isfile(self.abs(rel))

    def read(self, rel):
        with open(self.abs(rel), encoding="utf-8") as f:
            return f.read()

    def mtime(self, rel):
        try:
            return os.path.getmtime(self.abs(rel))
        except OSError:
            return None

    def glob(self, pattern):
        base = self.root
        out = []
        for p in glob.glob(os.path.join(base, *pattern.split("/"))):
            out.append(os.path.relpath(p, base).replace(os.sep, "/"))
        return sorted(out)


def find_root(start):
    """Walk up from start until a folder holding both Docs and Game is found."""
    p = os.path.abspath(start)
    for _ in range(6):
        if os.path.isdir(os.path.join(p, "Docs")) and os.path.isdir(os.path.join(p, "Game")):
            return p
        p = os.path.dirname(p)
    return None
