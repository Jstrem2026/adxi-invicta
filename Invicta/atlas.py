"""ADXI: Invicta: blueprint explorer, progress dashboard and consistency scanner
for the Luxuria Invicta (Arcane Drift game data only, not the EX101).

    python atlas.py            start the app in your browser
    python atlas.py --scan     run the scanner only, print the summary, write reports/scan_report.md
                               (exit code 1 if it finds errors)

Needs Python 3.8+ and Shapely, the geometry library the scan uses. Install it once with
    python -m pip install -r requirements.txt
("Start ADXI Invicta.bat" does this for you on the first run.)
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    import shapely  # noqa: F401
except ImportError:
    sys.exit("ADXI: Invicta needs Shapely, the geometry library its scan uses. Install it once with:\n"
             "    python -m pip install -r \"%s\"\n"
             "then run this again." % os.path.join(HERE, "requirements.txt"))

from atlaslib.sources import find_root  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="ADXI: Invicta")
    ap.add_argument("--scan", action="store_true", help="run the consistency scan and exit")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--root", help="ArcaneDrift folder (default: the folder above this app)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    root = a.root or find_root(HERE)
    if not root:
        sys.exit("Could not find the ArcaneDrift folder (one holding Docs and Game). Use --root.")
    if a.scan:
        from atlaslib.server import build
        from atlaslib.report import report_md
        data = build(root)
        text = report_md(data)
        os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
        path = os.path.join(HERE, "reports", "scan_report.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        c = {}
        for i in data["issues"]:
            if not i["known"]:
                c[i["severity"]] = c.get(i["severity"], 0) + 1
        pr = data["progress"]
        print("ADXI: Invicta scan: %d errors, %d warnings, %d waiting on Jordan, %d not designed yet." % (
            c.get("error", 0), c.get("warning", 0), c.get("decision", 0), c.get("gap", 0)))
        print("Design coverage %.1f%% (%s km² of %s km² has precinct plans)." % (pr["planned_pct"], pr["planned_area_km2"], pr["total_area_km2"]))
        print("Full report: %s" % path)
        sys.exit(1 if c.get("error") else 0)
    from atlaslib.server import serve
    serve(root, a.port, not a.no_browser)


if __name__ == "__main__":
    main()
