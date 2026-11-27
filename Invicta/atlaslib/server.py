"""A small local web server (standard library only). It rebuilds the model and
re-runs the scanner on every /api/all request, so the page always shows the
files as they are on disk right now. Listens on 127.0.0.1 only."""

import json
import mimetypes
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .loader import Loader, APP_DIR, DATA_DIR
from . import fabric as FB
from .scanner import scan
from .progress import progress
from .report import report_md

WEB = os.path.join(APP_DIR, "web")
SERVE_EXT = {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".html", ".md", ".csv", ".txt", ".json", ".webp"}
_lock = threading.Lock()


def build(root):
    with _lock:
        t = time.time()
        model = Loader(root).model()
        issues = scan(model, root)
        prog = progress(model, issues)
        model.pop("_docs", None)
        return {"model": model, "issues": issues, "progress": prog, "scan_ms": int((time.time() - t) * 1000)}


def make_handler(root):
    root = os.path.abspath(root)

    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, code, body, ctype="text/plain; charset=utf-8", extra=None):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            try:
                if u.path in ("/", "/index.html"):
                    return self.static("index.html")
                if u.path.startswith("/static/"):
                    return self.static(u.path[len("/static/"):])
                if u.path == "/api/all":
                    return self.send(200, json.dumps(build(root), ensure_ascii=False), "application/json; charset=utf-8")
                if u.path == "/api/report.md":
                    data = build(root)
                    return self.send(200, report_md(data), "text/markdown; charset=utf-8")
                if u.path == "/api/model":  # a building's plan with its fabric (walls, doors, windows, stairs)
                    uid = q.get("uid", [""])[0]
                    p = os.path.join(DATA_DIR, "models", os.path.basename(uid) + ".json")
                    if not uid or not os.path.isfile(p):
                        return self.send(404, "No plan for %s" % uid)
                    with open(p, encoding="utf-8") as f:
                        m = json.load(f)
                    return self.send(200, json.dumps(FB.with_fabric(m), ensure_ascii=False, separators=(",", ":")),
                                     "application/json; charset=utf-8")
                if u.path == "/file":
                    return self.file(q.get("path", [""])[0])
            except Exception as e:  # show the problem instead of a blank page
                return self.send(500, "App error: %s: %s" % (type(e).__name__, e))
            self.send(404, "Not found")

        def static(self, rel):
            p = os.path.normpath(os.path.join(WEB, rel))
            if not p.startswith(WEB) or not os.path.isfile(p):
                return self.send(404, "Not found")
            ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            with open(p, "rb") as f:
                self.send(200, f.read(), ctype)

        def file(self, rel):
            """Read-only view of a source file under the ArcaneDrift root."""
            rel = rel.replace("\\", "/").lstrip("/")
            p = os.path.normpath(os.path.join(root, *rel.split("/")))
            if not (p == root or p.startswith(root + os.sep)) or not os.path.isfile(p):
                return self.send(404, "Not found: %s" % rel)
            ext = os.path.splitext(p)[1].lower()
            if ext not in SERVE_EXT:
                return self.send(403, "This file type is not shown in the app.")
            ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
            if ext in (".md", ".csv", ".txt"):
                ctype = "text/plain; charset=utf-8"
            with open(p, "rb") as f:
                self.send(200, f.read(), ctype)

    return H


def serve(root, port=8765, open_browser=True):
    srv = None
    for p in range(port, port + 10):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), make_handler(root))
            port = p
            break
        except OSError:
            continue
    if srv is None:
        raise SystemExit("No free port between %d and %d." % (port, port + 9))
    url = "http://127.0.0.1:%d/" % port
    print("ADXI: Invicta running at %s  (reading %s)" % (url, root))
    print("Press Ctrl+C to stop.")
    if open_browser:
        import webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
