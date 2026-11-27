"""Export a read-only static copy of the app for web hosting (Cloudflare Pages).

    python tools/export_static.py                 writes ./site
    python tools/export_static.py --out dist      writes ./dist

It runs the same build and scan as the local app, then writes:

    index.html, static/      the browser app, with a small shim so it reads files
                             instead of the local /api and /file endpoints
    api/all.json             the model, scan and progress (what /api/all returns)
    api/report.md            the scan report
    file/<path>              only the source files the app links to, and only from
                             the allowed folders below (never game code or the website)
    _headers                 Cloudflare Pages headers

Exit code 1 when the scan finds errors, so a CI build can stop on them.
Needs Python 3.8+ and nothing else.
"""

import argparse
import json
import os
import re
import shutil
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

from atlaslib.sources import find_root  # noqa: E402
from atlaslib.server import build, SERVE_EXT, WEB  # noqa: E402
from atlaslib.report import report_md  # noqa: E402

# Only files under these folders may be published. Everything else the model
# mentions (for example Game/Tools/...) is listed in the app but not copied.
ALLOWED = (
    "Docs/1_Canon_Source/Invicta/",
    "Docs/2_Design_Docs/",
    "Invicta/data/",
    "Game/Docs/02_Canon_Errata.md",
    "Game/Docs/Invicta_Ship_Reference.md",
    "Game/Docs/Port_of_Arrivals_Precincts.md",
    "Game/Docs/geometry_revB/",
    "Game/Docs/art/blueprints/",
)
NEVER = ("Website/", "Game/Tools/", "Game/ArcaneDrift/", "Game/Data/")

SHIM = """<script>
/* Static web copy: read the exported files instead of the local server. */
window.ADXI_STATIC = true;
(function () {
  var f = window.fetch.bind(window);
  window.fetch = function (u, o) {
    if (u === "/api/all") u = "api/all.json";
    else if (u === "/api/report.md") u = "api/report.md";
    return f(u, o);
  };
  function fix(a) {
    var h = a.getAttribute("href") || "";
    if (h.indexOf("/file?path=") === 0) {
      var p = decodeURIComponent(h.slice(11));
      a.setAttribute("href", PUBLISHED[p] ? "file/" + p.split("/").map(encodeURIComponent).join("/") : "#");
      if (!PUBLISHED[p]) { a.title = "Not in the web copy"; a.removeAttribute("target"); a.classList.add("muted"); }
    } else if (h === "/api/report.md") a.setAttribute("href", "api/report.md");
  }
  new MutationObserver(function () {
    document.querySelectorAll('a[href^="/file?path="], a[href="/api/report.md"]').forEach(fix);
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
</script>
"""


def referenced_paths(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            referenced_paths(v, out)
    elif isinstance(obj, list):
        for v in obj:
            referenced_paths(v, out)
    elif isinstance(obj, str) and re.match(r"^(Docs|Game|Invicta)/[^\n]+\.[A-Za-z0-9]+$", obj):
        out.add(obj)


def allowed(rel):
    if any(rel.startswith(n) for n in NEVER):
        return False
    return any(rel == a or (a.endswith("/") and rel.startswith(a)) for a in ALLOWED)


def main():
    ap = argparse.ArgumentParser(description="Export the static web copy")
    ap.add_argument("--out", default=os.path.join(APP, "site"))
    ap.add_argument("--root", help="ArcaneDrift folder (default: the folder above this app)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    root = os.path.abspath(a.root or find_root(APP) or "")
    if not os.path.isdir(os.path.join(root, "Docs")):
        sys.exit("Could not find the ArcaneDrift folder (one holding Docs). Use --root.")
    out = os.path.abspath(a.out)
    if os.path.isdir(out):  # empty it (keep the folder itself)
        for n in os.listdir(out):
            p = os.path.join(out, n)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(os.path.join(out, "api"), exist_ok=True)

    data = build(root)
    cp = os.path.join(APP, "data", "concepts.json")  # concept art per building
    if os.path.isfile(cp):
        with open(cp, encoding="utf-8") as f:
            data["concepts"] = json.load(f)
    data["model"]["root"] = "(web copy)"  # never publish a local disk path
    data["static_export"] = True

    refs = set()
    referenced_paths(data, refs)
    published, skipped = {}, []
    for rel in sorted(refs):
        src = os.path.join(root, *rel.split("/"))
        ext = os.path.splitext(rel)[1].lower()
        if allowed(rel) and ext in SERVE_EXT and os.path.isfile(src):
            dst = os.path.join(out, "file", *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            published[rel] = 1
        else:
            skipped.append(rel)

    with open(os.path.join(out, "api", "all.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    with open(os.path.join(out, "api", "report.md"), "w", encoding="utf-8") as f:
        f.write(report_md(data))

    shutil.copytree(WEB, os.path.join(out, "static"))
    with open(os.path.join(WEB, "index.html"), encoding="utf-8") as f:
        html = f.read()
    html = html.replace('"/static/', '"static/')
    shim = "<script>var PUBLISHED = %s;</script>\n%s" % (json.dumps(published), SHIM)
    html = html.replace('<script src="static/app.js">', shim + '<script src="static/app.js">', 1)
    html = html.replace('<button id="rescan"', '<button id="rescan" hidden', 1)
    # Site-only extras that need the Cloudflare functions: the Claude chat (/api/chat)
    # and the shared helpers chat (/api/room). The local app has neither.
    # Jordan's private review page (needs /api/review and the ADMIN_KEY secret).
    if os.path.isfile(os.path.join(WEB, "review.html")):
        shutil.copy2(os.path.join(WEB, "review.html"), os.path.join(out, "review.html"))
    for extra in ("concepts", "chat", "room"):
        if os.path.isfile(os.path.join(WEB, extra + ".css")):
            html = html.replace("</head>", '<link rel="stylesheet" href="static/%s.css">\n</head>' % extra, 1)
        if os.path.isfile(os.path.join(WEB, extra + ".js")):
            html = html.replace("</body>", '<script src="static/%s.js"></script>\n</body>' % extra, 1)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    with open(os.path.join(out, "_headers"), "w", encoding="utf-8") as f:
        f.write("/*\n  X-Content-Type-Options: nosniff\n"
                "  Referrer-Policy: no-referrer\n\n/api/*\n  Cache-Control: no-cache\n")

    c = {}
    for i in data["issues"]:
        if not i["known"]:
            c[i["severity"]] = c.get(i["severity"], 0) + 1
    size = sum(os.path.getsize(os.path.join(d, n)) for d, _, ns in os.walk(out) for n in ns)
    print("Static copy written to %s (%d source files, %.1f MB)." % (out, len(published), size / 1e6))
    if skipped:
        print("Not published (outside the allowed folders or missing): %s" % ", ".join(skipped))
    print("Scan: %d errors, %d warnings, %d waiting on Jordan, %d not designed yet." % (
        c.get("error", 0), c.get("warning", 0), c.get("decision", 0), c.get("gap", 0)))
    sys.exit(1 if c.get("error") else 0)


if __name__ == "__main__":
    main()
