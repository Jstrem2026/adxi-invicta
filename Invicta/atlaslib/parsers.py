"""Readers for the source formats: canon data-sheet HTML, outline CSVs, Markdown
tables, and the constants in the game's invicta_geometry.py (read with ast, never run)."""

import ast
import csv
import html
import io
import re


class ParseError(Exception):
    pass


# ---------------------------------------------------------------- HTML data sheets

def _cell_text(c):
    return html.unescape(re.sub(r"<[^>]+>", "", c)).strip()


def html_tables(text):
    """All <table>s as lists of rows (first row is the header)."""
    out = []
    for tb in re.findall(r"<table.*?</table>", text, flags=re.S):
        rows = []
        for r in re.findall(r"<tr.*?</tr>", tb, flags=re.S):
            cells = [_cell_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, flags=re.S)]
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def html_sections(text):
    """Heading -> plain text that follows it (until the next heading)."""
    body = re.sub(r"<style.*?</style>|<script.*?</script>|<svg.*?</svg>", "", text, flags=re.S)
    parts = re.split(r"<h[23][^>]*>(.*?)</h[23]>", body, flags=re.S)
    out = {}
    for i in range(1, len(parts), 2):
        out[_cell_text(parts[i])] = re.sub(r"\s+", " ", _cell_text(re.sub(r"<(br|/p|/li|/div)[^>]*>", " ", parts[i + 1]))).strip()
    return out


def sheet_meta(text):
    m = re.search(r"Drawing no\.\s*</?[^>]*>?\s*([^<]+)", text)
    rev = re.search(r"Revision\s*(?:<[^>]+>\s*)*([^<]+)", text)
    title = re.search(r"<title>(.*?)</title>", text, flags=re.S)
    return {"drawing": m.group(1).strip() if m else None,
            "revision": rev.group(1).strip() if rev else None,
            "title": html.unescape(title.group(1).strip()) if title else None}


def kv(rows):
    return {r[0]: r[1] for r in rows[1:] if len(r) >= 2}


def num(s, default=None):
    """First number in a string ('1,560 m / 2,160 m' -> 1560.0)."""
    if s is None:
        return default
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(s))
    return float(m.group(0).replace(",", "")) if m else default


def nums(s):
    return [float(v.replace(",", "")) for v in re.findall(r"-?\d[\d,]*(?:\.\d+)?", str(s))]


def plan_districts(text):
    """District polygons and the plaza circle from a deck sheet's plan SVG.

    The sheet draws bow LEFT / port UP (a mirror of the true top view); the
    coordinates returned here are ship-frame km (x from prow, y port negative),
    which the viewer then draws bow right."""
    svgs = re.findall(r"<svg.*?</svg>", text, flags=re.S)
    if not svgs:
        raise ParseError("no plan drawing")
    s = svgs[0]
    labels = [(float(x), int(f)) for x, f in re.findall(r'<text class="note" x="([\d.]+)" y="[\d.]+"[^>]*>F(\d+)</text>', s)]
    if len(labels) < 2:
        raise ParseError("plan has no frame labels")
    (px0, f0), (px1, f1) = labels[0], labels[-1]
    k = (px1 - px0) / ((f1 - f0) * 0.5)  # px per km
    circ = re.search(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"[^>]*stroke="#ffc266"', s)
    if not circ:
        raise ParseError("plan has no plaza circle")
    cy0 = float(circ.group(2))
    X = lambda px: f0 * 0.5 + (px - px0) / k
    Y = lambda py: (py - cy0) / k
    plaza = (round(X(float(circ.group(1))), 4), round(Y(cy0), 4), round(float(circ.group(3)) / k, 4))
    polys = []
    for m in re.finditer(r'<polygon points="([^"]+)"([^>]*)/>', s):
        a = m.group(2)
        if 'stroke-width="1.2"' not in a or 'fill="none"' in a:
            continue
        pts = [tuple(map(float, p.split(","))) for p in m.group(1).split()]
        polys.append([(round(X(x), 4), round(Y(y), 4)) for x, y in pts])
    lbls = [(float(x), float(y), html.unescape(t)) for x, y, t in re.findall(r'<text class="lbl" x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*)</text>', s)]
    lbls = [(X(x), Y(y), t) for x, y, t in lbls]
    return {"px_per_km": k, "plaza_circle": plaza, "polygons": polys, "labels": lbls}


# ---------------------------------------------------------------- CSV outlines

def outline_csv(text):
    pts = []
    rd = csv.reader(io.StringIO(text))
    header = next(rd, None)
    if not header or len(header) < 2:
        raise ParseError("missing header")
    for row in rd:
        if not row or not row[0].strip():
            continue
        try:
            pts.append((float(row[0]), float(row[1])))
        except ValueError:
            raise ParseError("bad number in row %r" % (row,))
    if len(pts) < 3:
        raise ParseError("fewer than 3 points")
    return pts


def dict_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


# ---------------------------------------------------------------- Markdown

def md_tables(text):
    """[(heading, header, rows, line_no)] for every pipe table."""
    out = []
    heading = ""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            heading = ln.lstrip("#").strip()
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-", lines[i + 1]):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append((heading, header, rows, i + 1))
            i = j
            continue
        i += 1
    return out


def md_images(text):
    return re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text)


def md_links(text):
    return [l for l in re.findall(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)", text) if not re.match(r"[a-z]+:", l)]


# ---------------------------------------------------------------- invicta_geometry.py

def py_constants(text, names):
    """Literal values of module-level assignments, plus the trailing comment of
    each dict entry line (to read 'canon' / 'TUNE' markers)."""
    tree = ast.parse(text)
    out = {}
    lines = text.splitlines()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nm = node.targets[0].id
            if nm in names:
                try:
                    out[nm] = ast.literal_eval(node.value)
                except ValueError:
                    continue
                if isinstance(node.value, ast.Dict):
                    notes = {}
                    for k in node.value.keys:
                        if isinstance(k, ast.Constant):
                            line = lines[k.lineno - 1]
                            if "#" in line:
                                notes[k.value] = line.split("#", 1)[1].strip()
                    out[nm + "__comments"] = notes
    return out
