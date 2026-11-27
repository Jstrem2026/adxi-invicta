/* ADXI: Invicta: 2D plans on the map.
   - Building pages: the footprint's measurements, and the building's plan (levels, rooms, walls,
     doors, cores) from Invicta/data/models/<uid>.json when one exists, one level at a time.
   - Precinct and block pages: a "Sizes" button that labels every building with its size.
   Everything is drawn from stored numbers; nothing is guessed. Feet first, metres in brackets. */
(function () {
  "use strict";
  const FT = 3.28084;
  const ftin = (m) => {  // 12.5 m -> 41 ft 0 in
    const inch = Math.round(m * FT * 12);
    const f = Math.floor(inch / 12), i = inch % 12;
    return i ? `${f.toLocaleString()} ft ${i} in` : `${f.toLocaleString()} ft`;
  };
  const isMetric = () => localStorage.getItem("adxi.units") === "metric";
  const mmm = (m) => m < 10 ? `${Math.round(m * 1000).toLocaleString()} mm` : `${m >= 100 ? Math.round(m).toLocaleString() : m.toFixed(1)} m`;
  const both = (m) => isMetric() ? mmm(m) : `${ftin(m)} (${m >= 10 ? Math.round(m).toLocaleString() : m.toFixed(1)} m)`;
  const one = (m) => isMetric() ? mmm(m) : ftin(m);
  const sqft = (m2) => isMetric() ? `${Math.round(m2).toLocaleString()} m²` : `${Math.round(m2 * FT * FT).toLocaleString()} sq ft`;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const NS = "http://www.w3.org/2000/svg";
  let level = null, sizesOn = localStorage.getItem("adxi.measure") !== "off", cache = {};

  function area(poly) {
    let a = 0;
    for (let i = 0; i < poly.length; i++) { const p = poly[i], q = poly[(i + 1) % poly.length]; a += p[0] * q[1] - q[0] * p[1]; }
    return Math.abs(a) / 2;
  }
  function centroid(poly) {
    const n = poly.length; return [poly.reduce((s, p) => s + p[0], 0) / n, poly.reduce((s, p) => s + p[1], 0) / n];
  }
  function isRect(poly) {
    if (poly.length !== 4) return false;
    const xs = new Set(poly.map((p) => p[0])), ys = new Set(poly.map((p) => p[1]));
    return xs.size === 2 && ys.size === 2;
  }

  async function getModel(uid) {
    const D_ = typeof D !== "undefined" ? D : null;
    if (D_ && D_.models && D_.models[uid]) return D_.models[uid];
    if (window.ADXI_STATIC) return null;
    if (uid in cache) return cache[uid];
    try {
      const r = await fetch("/file?path=" + encodeURIComponent(`Invicta/data/models/${uid}.json`), { cache: "no-store" });
      cache[uid] = r.ok ? await r.json() : null;
    } catch (e) { cache[uid] = null; }
    return cache[uid];
  }

  // Map coordinates: app.js draws ship km with X(x) and Y(y) (metres on screen, bow right, port up).
  function mapper(rect) {
    return (p) => [X(rect[0] + p[0] / 1000), Y(rect[2] + p[1] / 1000)];
  }
  function el(tag, attrs, text) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  }
  function textAt(g, x, y, t, fs, opts) {
    const o = opts || {};
    g.append(el("text", { x, y, "font-size": fs, fill: o.fill || "#e8f1fb", "text-anchor": o.anchor || "middle", "dominant-baseline": "middle",
      "paint-order": "stroke", stroke: "#071425", "stroke-width": fs / 4, transform: o.rot ? `rotate(${o.rot} ${x} ${y})` : "" }, t));
  }
  function dimLine(g, a, b, label, fs, off) {
    // Measurement line between screen points a and b, pushed out by `off` screen units, with end ticks and a label.
    const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L * off, ny = dx / L * off;
    const A = [a[0] + nx, a[1] + ny], B = [b[0] + nx, b[1] + ny], c = "#ffc266", sw = fs / 10;
    g.append(el("line", { x1: A[0], y1: A[1], x2: B[0], y2: B[1], stroke: c, "stroke-width": sw }));
    for (const [P, Q] of [[a, A], [b, B]]) g.append(el("line", { x1: P[0], y1: P[1], x2: Q[0] + nx * 0.3, y2: Q[1] + ny * 0.3, stroke: c, "stroke-width": sw }));
    const ang = Math.atan2(dy, dx) * 180 / Math.PI, rot = ang > 90 || ang < -90 ? ang + 180 : ang;
    textAt(g, (A[0] + B[0]) / 2 + nx * 0.6, (A[1] + B[1]) / 2 + ny * 0.6, label, fs, { fill: c, rot });
  }

  async function drawBuilding(uid) {
    const svg = document.getElementById("map");
    const b = typeof IX !== "undefined" && IX.buildings && IX.buildings[uid];
    if (!svg || !b || !b.rect_km) return;
    const r = b.rect_km, Lm = (r[1] - r[0]) * 1000, Wm = (r[3] - r[2]) * 1000, toS = mapper(r);
    const fs = Math.max(Lm, Wm) / 32;
    const g = el("g", { id: "plan2d", "pointer-events": "none" });
    // Footprint measurements (length along the ship, width across it).
    dimLine(g, toS([0, 0]), toS([Lm, 0]), both(Lm), fs, fs * 2.2);
    dimLine(g, toS([0, Wm]), toS([0, 0]), both(Wm), fs, fs * 2.2);

    const model = await getModel(uid);
    const tools = document.querySelector(".mapwrap .maptools");
    document.querySelectorAll(".plan-lv").forEach((x) => x.remove());
    if (model && model.levels && model.levels.length) {
      if (!level || !model.levels.some((l) => l.id === level)) level = model.levels.find((l) => l.z_m >= 0) ? model.levels.find((l) => l.z_m >= 0).id : model.levels[0].id;
      if (tools) {
        model.levels.slice().reverse().forEach((l) => {
          const bt = document.createElement("button");
          bt.className = "plan-lv" + (l.id === level ? " on" : "");
          bt.textContent = l.name.split("·")[0].trim();
          bt.title = `Show the plan of ${l.name}: floor ${both(l.z_m)} above deck, ${both(l.height_m)} high`;
          bt.onclick = () => { level = l.id; drawBuilding(uid); };
          tools.prepend(bt);
        });
      }
      const lv = (e) => (e.levels || [e.level]).includes(level);
      const els = (model.elements || []).filter(lv);
      // Grid lines, light.
      if (model.grid_m) {
        for (let x = 0; x <= Lm + 0.01; x += model.grid_m) { const a = toS([x, 0]), c = toS([x, Wm]); g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#6fd0ff", "stroke-opacity": 0.12, "stroke-width": fs / 20 })); }
        for (let y = 0; y <= Wm + 0.01; y += model.grid_m) { const a = toS([0, y]), c = toS([Lm, y]); g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#6fd0ff", "stroke-opacity": 0.12, "stroke-width": fs / 20 })); }
      }
      const poly = (pts) => pts.map(toS).map((q) => q.join(",")).join(" ");
      for (const e of els.filter((x) => x.type === "mass")) g.append(el("polygon", { points: poly(e.outline_m), fill: "none", stroke: "#b99cff", "stroke-width": fs / 8, "stroke-dasharray": `${fs / 2} ${fs / 3}` }));
      for (const e of els.filter((x) => x.type === "room")) {
        g.append(el("polygon", { points: poly(e.outline_m), fill: e.status === "canon" ? "rgba(95,211,154,.18)" : "rgba(111,208,255,.14)", stroke: "#cfe8ff", "stroke-width": fs / 14 }));
        const c = toS(centroid(e.outline_m)), a = area(e.outline_m);
        const xs = e.outline_m.map((p) => p[0]), ys = e.outline_m.map((p) => p[1]);
        const size = isRect(e.outline_m) ? `${one(Math.max(...xs) - Math.min(...xs))} × ${one(Math.max(...ys) - Math.min(...ys))}` : sqft(a);
        textAt(g, c[0], c[1] - fs * 0.6, e.name || e.id, fs * 0.8);
        textAt(g, c[0], c[1] + fs * 0.5, size, fs * 0.6, { fill: "#8fb0d3" });
      }
      for (const e of els.filter((x) => x.type === "core")) {
        g.append(el("polygon", { points: poly(e.outline_m), fill: "rgba(255,184,77,.35)", stroke: "#ffb84d", "stroke-width": fs / 10 }));
        const c = toS(centroid(e.outline_m)); textAt(g, c[0], c[1], e.name || "Stairs / lifts", fs * 0.55);
      }
      for (const e of els.filter((x) => x.type === "wall")) {
        const [a, c] = [toS(e.line_m[0]), toS(e.line_m[e.line_m.length - 1])];
        g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#e8f1fb", "stroke-width": Math.max((e.thickness_m || 0.3), fs / 6), "stroke-linecap": "square" }));
      }
      for (const e of els.filter((x) => x.type === "door" || x.type === "opening")) {
        const [a, c] = [toS(e.line_m[0]), toS(e.line_m[e.line_m.length - 1])];
        g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#5fd39a", "stroke-width": fs / 3 }));
        textAt(g, (a[0] + c[0]) / 2, (a[1] + c[1]) / 2 - fs * 0.7, `${e.type === "door" ? "Door" : "Opening"}${e.width_m ? " " + one(e.width_m) : ""}`, fs * 0.5, { fill: "#5fd39a" });
      }
      if (!els.length) { const c = toS([Lm / 2, Wm / 2]); textAt(g, c[0], c[1], "Nothing drawn on this level yet", fs, { fill: "#8fb0d3" }); }
    } else {
      const c = toS([Lm / 2, Wm / 2]);
      textAt(g, c[0], c[1] + fs * 1.5, "Floor plan not designed yet · ask the chat to draw it", fs * 0.7, { fill: "#8fb0d3" });
    }
    const old = svg.querySelector("#plan2d"); if (old) old.remove();
    svg.append(g);
  }

  function drawSizes() {
    const svg = document.getElementById("map");
    const old = svg && svg.querySelector("#sizes2d"); if (old) old.remove();
    if (!svg || !sizesOn || typeof IX === "undefined") return;
    const vb = svg.getAttribute("viewBox").split(/\s+/).map(Number), fs = vb[2] / 90;
    const g = el("g", { id: "sizes2d", "pointer-events": "none" });
    for (const b of Object.values(IX.buildings || {})) {
      if (!b.rect_km) continue;
      const r = b.rect_km, cx = (X(r[0]) + X(r[1])) / 2, cy = (Y(r[2]) + Y(r[3])) / 2;
      if (cx < vb[0] || cx > vb[0] + vb[2] || cy < vb[1] || cy > vb[1] + vb[3]) continue;
      const w = (r[1] - r[0]) * 1000, h = (r[3] - r[2]) * 1000;
      textAt(g, cx, cy, `${one(w)} × ${one(h)}`, fs * 0.8, { fill: "#ffc266" });
    }
    svg.append(g);
  }

  function hook() {
    const h = location.hash.replace(/^#\/?/, "");
    const [kind, a] = h.split("/").map(decodeURIComponent);
    if (kind === "building") drawBuilding(a);
    if (kind === "precinct" || kind === "block" || kind === "district" || kind === "street") {
      const tools = document.querySelector(".mapwrap .maptools");
      if (tools && !tools.querySelector(".plan-sizes")) {
        const bt = document.createElement("button");
        bt.className = "plan-sizes" + (sizesOn ? " on" : "");
        const lab = () => (bt.textContent = sizesOn ? "Measurements: on" : "Measurements: off");
        lab();
        bt.title = "Show or hide the length and width of every building on the map";
        bt.onclick = () => { sizesOn = !sizesOn; localStorage.setItem("adxi.measure", sizesOn ? "on" : "off"); bt.classList.toggle("on", sizesOn); lab(); drawSizes(); };
        tools.prepend(bt);
      }
      drawSizes();
    }
  }
  // Units switch in the header: US (feet) or Metric (m and mm, as in Australian practice). Saved per browser.
  function unitsSwitch() {
    const bar = document.querySelector(".top .actions") || document.querySelector(".top");
    if (!bar || bar.querySelector(".units")) return;
    const bt = document.createElement("button");
    bt.className = "units";
    const label = () => (bt.textContent = isMetric() ? "Units: metric" : "Units: feet");
    label();
    bt.title = "Switch between feet and metric";
    bt.onclick = () => {
      localStorage.setItem("adxi.units", isMetric() ? "us" : "metric");
      localStorage.setItem("adxi.unitsChosen", "1");
      label();
      if (typeof route === "function") route();
    };
    bar.prepend(bt);
    window.adxiUnitsLabel = label;
  }
  unitsSwitch();

  // Redraw whenever the app renders a page.
  const app = document.getElementById("app");
  if (app) new MutationObserver(() => { if (document.getElementById("map") && !document.getElementById("map").dataset.plan) { document.getElementById("map").dataset.plan = "1"; hook(); } }).observe(app, { childList: true });
})();
