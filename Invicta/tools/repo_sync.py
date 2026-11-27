"""Copy the Invicta files between the ArcaneDrift folder and the adxi-invicta repo.

    python tools/repo_sync.py out     ArcaneDrift -> repo   (then commit and push in the repo)
    python tools/repo_sync.py in      repo -> ArcaneDrift   (after pulling approved changes)
    add --dry-run to only list what would change.

The repo keeps the same paths as the ArcaneDrift folder, so the app runs in either.
Only the files in SCOPE are ever copied. The rest of Game/ and all of Website/ never
go to the repo. "in" never writes canon (Docs/1_Canon_Source), which changes only
through errata, and never deletes anything on this PC.

Needs Python 3.8+ and nothing else.
"""

import argparse
import filecmp
import glob
import os
import shutil
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
from atlaslib.sources import find_root  # noqa: E402

DEFAULT_REPO = r"C:\Studio\adxi-invicta"

# Folders copied whole, and single files. Paths are relative to the ArcaneDrift folder.
# Add a new Invicta design doc here (both Game/Docs and its Docs/2_Design_Docs mirror).
INVICTA_DOCS = [
    "02_Canon_Errata.md",
    "Invicta_Ship_Reference.md",
    "Port_of_Arrivals_Precincts.md",
]
FOLDERS = [
    "Invicta",
    "Docs/1_Canon_Source/Invicta",
    "Game/Docs/geometry_revB",
    "Game/Docs/art/blueprints",
    "Docs/2_Design_Docs/geometry_revB",
    "Docs/2_Design_Docs/art/blueprints",
]
FILES = (["Game/Docs/" + n for n in INVICTA_DOCS]
         + ["Docs/2_Design_Docs/" + n for n in INVICTA_DOCS]
         + ["Game/Tools/InvictaGraybox/invicta_geometry.py"])
SKIP_DIRS = {"__pycache__", ".git", "site", "reports", ".claude"}
SKIP_FILES = {"Thumbs.db", "desktop.ini", ".DS_Store"}
NEVER = ("Website/", "Game/ArcaneDrift/", "Game/Data/")
CANON = "Docs/1_Canon_Source/"


def scope_files(base):
    out = set()
    # every precinct design doc (e.g. Canal_Gardens_Precincts.md), in Game/Docs and its mirror
    for d in ("Game/Docs", "Docs/2_Design_Docs"):
        for n in glob.glob(os.path.join(base, *d.split("/"), "*_Precincts.md")):
            out.add(d + "/" + os.path.basename(n))
    for rel in FILES:
        if os.path.isfile(os.path.join(base, *rel.split("/"))):
            out.add(rel)
    for folder in FOLDERS:
        top = os.path.join(base, *folder.split("/"))
        for d, dirs, names in os.walk(top):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for n in names:
                if n in SKIP_FILES or n.endswith(".pyc"):
                    continue
                out.add(os.path.relpath(os.path.join(d, n), base).replace(os.sep, "/"))
    bad = [r for r in out if r.startswith(NEVER)]
    if bad:
        sys.exit("Refusing: out-of-scope files matched: %s" % bad[:5])
    return out


def main():
    ap = argparse.ArgumentParser(description="Sync Invicta files with the adxi-invicta repo")
    ap.add_argument("direction", choices=["out", "in"])
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--root", help="ArcaneDrift folder (default: the folder above this app)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root or find_root(APP) or "")
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit("No git repo at %s. Clone https://github.com/Jstrem2026/adxi-invicta there first." % repo)
    if a.direction == "out" and not a.dry_run:
        # Bring in approved changes from the site first, so a stale local copy never overwrites them.
        import auto_pull
        auto_pull.main()
        print("Pulled approved site changes first (see %s)." % auto_pull.LOG)
    src, dst = (root, repo) if a.direction == "out" else (repo, root)

    want = scope_files(src)
    copied, removed, skipped = [], [], []
    for rel in sorted(want):
        if a.direction == "in" and rel.startswith(CANON):
            if not os.path.isfile(os.path.join(dst, *rel.split("/"))) or \
                    not filecmp.cmp(os.path.join(src, *rel.split("/")), os.path.join(dst, *rel.split("/")), shallow=False):
                skipped.append(rel)
            continue
        s = os.path.join(src, *rel.split("/"))
        d = os.path.join(dst, *rel.split("/"))
        if os.path.isfile(d) and filecmp.cmp(s, d, shallow=False):
            continue
        copied.append(rel)
        if not a.dry_run:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
    if a.direction == "out":  # never delete in the repo: files missing here may be new work from the site
        for rel in sorted(scope_files(repo) - want):
            removed.append(rel)

    verb = "Would copy" if a.dry_run else "Copied"
    print("%s %d file(s) %s." % (verb, len(copied), "to the repo" if a.direction == "out" else "to ArcaneDrift"))
    for r in copied:
        print("  + " + r)
    for r in removed:
        print("  ? " + r + "  (in the repo but not here; kept. Run 'in' to bring it here)")
    if skipped:
        print("Canon files differ but were NOT copied (canon is read-only; use errata):")
        for r in skipped:
            print("  ! " + r)


if __name__ == "__main__":
    main()
