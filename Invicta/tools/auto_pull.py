"""Pull approved changes from the adxi-invicta repo into the ArcaneDrift folder.

Run by the Windows scheduled task "ADXI Invicta auto-pull" every 5 minutes:
    pythonw tools/auto_pull.py

Safe by design:
- git pull --ff-only only; if the repo clone has uncommitted work or can't fast-forward, it skips.
- Only files that changed in the repo since the last pull are copied, and only if your
  local copy still matches the old repo version. If you edited the file locally, it is
  left alone and logged as a conflict.
- Never touches canon (Docs/1_Canon_Source) and never deletes anything.
Log: %LOCALAPPDATA%\\adxi-invicta\\auto_pull.log
"""

import datetime
import os
import shutil
import subprocess
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP, "tools"))
sys.path.insert(0, APP)
from repo_sync import DEFAULT_REPO, FOLDERS, FILES, CANON  # noqa: E402
from atlaslib.sources import find_root  # noqa: E402

LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", APP), "adxi-invicta")
LOG = os.path.join(LOG_DIR, "auto_pull.log")
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
    try:  # keep the log small
        if os.path.getsize(LOG) > 500_000:
            with open(LOG, encoding="utf-8") as f:
                tail = f.readlines()[-2000:]
            with open(LOG, "w", encoding="utf-8") as f:
                f.writelines(tail)
    except OSError:
        pass


def git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, creationflags=NO_WINDOW)
    out = r.stdout if binary else r.stdout.decode("utf-8", "replace").strip()
    return r.returncode, out, r.stderr.decode("utf-8", "replace").strip()


def in_scope(rel):
    if rel.startswith(CANON):
        return False
    if rel.endswith("_Precincts.md") and rel.count("/") == 2 and rel.startswith(("Game/Docs/", "Docs/2_Design_Docs/")):
        return True
    return rel in FILES or any(rel.startswith(f + "/") for f in FOLDERS)


def main():
    repo = DEFAULT_REPO
    root = find_root(APP)
    if not root or not os.path.isdir(os.path.join(repo, ".git")):
        return log("skip: repo or ArcaneDrift folder not found")
    code, dirty, _ = git(repo, "status", "--porcelain", "--untracked-files=no")
    if code or dirty:
        return log("skip: the repo clone has uncommitted changes")
    _, old, _ = git(repo, "rev-parse", "HEAD")
    code, _, err = git(repo, "pull", "--ff-only", "-q")
    if code:
        return log("skip: pull failed: " + err[:300])
    _, new, _ = git(repo, "rev-parse", "HEAD")
    if new == old:
        return  # nothing new; stay quiet
    _, names, _ = git(repo, "diff", "--name-only", old, new)
    copied, conflicts = [], []
    for rel in [n for n in names.splitlines() if n and in_scope(n)]:
        src = os.path.join(repo, *rel.split("/"))
        dst = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(src):
            continue  # removed in the repo: never delete locally
        c, before, _ = git(repo, "show", "%s:%s" % (old, rel), binary=True)
        before = before if c == 0 else None
        local = open(dst, "rb").read() if os.path.isfile(dst) else None
        incoming = open(src, "rb").read()
        if local == incoming:
            continue
        if local is not None and local != before:
            conflicts.append(rel)  # edited here too: keep the local version
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    log("pulled %s..%s: copied %d file(s)%s%s" % (old[:7], new[:7], len(copied),
        (": " + ", ".join(copied)) if copied else "",
        ("; CONFLICT, kept your local version of: " + ", ".join(conflicts)) if conflicts else ""))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never crash silently in the background
        log("error: %s: %s" % (type(e).__name__, e))
