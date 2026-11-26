"""One-time importer: read a precinct blueprint SVG and pull out buildings, roads and bays
in ship coordinates (x km from prow, y km port negative). Used to seed the app data.
"""
import re, sys, json, html

LANES = "ABCDEFGHIJKLMNOPQRSTUVWXY"

def attrs(s):
    return dict(re.findall(r'([\w:-]+)="([^"]*)"', s))

def parse(path):
    s = open(path, encoding="utf-8").read()
    els = []
    for m in re.finditer(r'<(rect|text|circle)\b([^>]*?)/?>([^<]*)', s):
        a = attrs(m.group(2)); a["_tag"] = m.group(1); a["_text"] = html.unescape(m.group(3)).strip()
        els.append(a)
    # frame and lane scale
    fr = [(float(e["x"]), int(e["_text"][1:])) for e in els if e["_tag"] == "text" and re.fullmatch(r"F\d+", e["_text"]) and float(e.get("y", 0)) < 330]
    ln = [(float(e["y"]), e["_text"]) for e in els if e["_tag"] == "text" and re.fullmatch(r"[A-Y]", e["_text"])]
    (px0, f0), (px1, f1) = fr[0], fr[-1]
    k = (px1 - px0) / ((f1 - f0) * 500.0)  # px per metre
    X = lambda px: (f0 * 500.0 + (px - px0) / k) / 1000.0
    py0, l0 = ln[0]
    yc0 = (LANES.index(l0) - 12) * 0.5
    Y = lambda py: yc0 + (py - (py0 - 6)) / k / 1000.0
    out = {"k_px_per_m": k, "rects": []}
    for i, e in enumerate(els):
        if e["_tag"] != "rect" or "x" not in e or e.get("fill", "").startswith("url"):
            continue
        x, y, w, h = (float(e[t]) for t in ("x", "y", "width", "height"))
        texts = []
        for f in els[i + 1:i + 4]:
            if f["_tag"] == "rect": break
            if f["_tag"] == "text" and x <= float(f.get("x", -1)) <= x + w and y <= float(f.get("y", -1)) <= y + h:
                texts.append((f.get("font-weight") == "bold", f["_text"]))
        out["rects"].append({
            "x0": round(X(x), 4), "x1": round(X(x + w), 4), "y0": round(Y(y), 4), "y1": round(Y(y + h), 4),
            "w_m": round(w / k, 1), "h_m": round(h / k, 1), "fill": e.get("fill"), "stroke": e.get("stroke"),
            "sw": e.get("stroke-width"), "texts": texts})
    # simple closed paths (M L L L Z) and polygons, as point lists in km
    out["shapes"] = []
    for m in re.finditer(r'<(path|polygon)\b([^>]*?)/?>', s):
        a = attrs(m.group(2))
        if a.get("fill", "none") in ("none",) or a.get("fill", "").startswith("url"):
            continue
        raw = a.get("d") or a.get("points") or ""
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", raw)]
        pts = [(round(X(nums[i]), 4), round(Y(nums[i + 1]), 4)) for i in range(0, len(nums) - 1, 2)]
        out["shapes"].append({"tag": m.group(1), "points_km": pts, "fill": a.get("fill"), "stroke": a.get("stroke"), "sw": a.get("stroke-width")})
    out["circles"] = [{"cx": round(X(float(e["cx"])), 4), "cy": round(Y(float(e["cy"])), 4), "r_km": round(float(e["r"]) / k / 1000, 4), "stroke": e.get("stroke")} for e in els if e["_tag"] == "circle"]
    out["labels"] = [e["_text"] for e in els if e["_tag"] == "text"]
    return out

if __name__ == "__main__":
    print(json.dumps(parse(sys.argv[1]), indent=1))
