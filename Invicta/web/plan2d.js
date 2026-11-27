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
  let level = null, sizesOn = localStorage.getItem("adxi.measure") !== "off", labelsOn = localStorage.getItem("adxi.labels") !== "off", cache = {};

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

  window.adxiGetModel = (uid) => getModel(uid);
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
  // Free-standing labels (titles, notes) skip themselves when they would land on one already placed.
  let placed = [];
  function place(g, x, y, t, fs, opts) {
    const w = t.length * fs * 0.56, h = fs * 1.2, r = [x - w / 2, y - h / 2, x + w / 2, y + h / 2];
    if (placed.some((q) => r[0] < q[2] && q[0] < r[2] && r[1] < q[3] && q[1] < r[3])) return false;
    placed.push(r); textAt(g, x, y, t, fs, opts); return true;
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

  // Draw one level of a building's plan (rooms, fixtures, cores, walls, doors) into g. Shared by the
  // building page and the block page, so both show exactly the same drawing.
  function drawEls(g, els, toS, fs, o) {
    const poly = (pts) => pts.map(toS).map((q) => q.join(",")).join(" ");
    for (const e of els.filter((x) => x.type === "mass")) g.append(el("polygon", { points: poly(e.outline_m), fill: "none", stroke: "#b99cff", "stroke-width": fs / 8, "stroke-dasharray": `${fs / 2} ${fs / 3}` }));
    for (const e of els.filter((x) => x.type === "room" || x.type === "zone")) {
      const on = o.selRoom === e.id;
      const pg = el("polygon", { points: poly(e.outline_m), ...(o.onRoom ? { class: "hit", "pointer-events": "all" } : { "pointer-events": "none" }),
        fill: on ? "rgba(255,194,102,.22)" : e.status === "canon" ? "rgba(95,211,154,.18)" : "rgba(111,208,255,.14)",
        stroke: on ? "#ffc266" : "#cfe8ff", "stroke-width": on ? fs / 8 : fs / 22 });
      if (o.onRoom) pg.append(el("title", {}, e.name || e.id));
      pg.addEventListener("click", (ev) => { ev.stopPropagation(); if (o.onRoom) o.onRoom(e); });
      g.append(pg);
    }
    for (const e of els.filter((x) => x.type === "fixture")) {
      g.append(el("polygon", { points: poly(e.outline_m), fill: "rgba(232,241,251,.12)", stroke: "#e8f1fb", "stroke-width": fs / 30 }));
    }
    for (const e of els.filter((x) => x.type === "core")) {
      g.append(el("polygon", { points: poly(e.outline_m), fill: "rgba(255,184,77,.35)", stroke: "#ffb84d", "stroke-width": fs / 14 }));
    }
    for (const e of els.filter((x) => x.type === "wall")) {
      const [a, c] = [toS(e.line_m[0]), toS(e.line_m[e.line_m.length - 1])];
      g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#e8f1fb", "stroke-width": Math.max((e.thickness_m || 0.3), fs / 6), "stroke-linecap": "square" }));
    }
    for (const e of els.filter((x) => x.type === "door" || x.type === "opening")) {
      const [a, c] = [toS(e.line_m[0]), toS(e.line_m[e.line_m.length - 1])];
      g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#5fd39a", "stroke-width": fs / 4 }));
    }
  }

  async function drawBuilding(uid, sel, keepView) {
    const svg = document.getElementById("map");
    const b = typeof IX !== "undefined" && IX.buildings && IX.buildings[uid];
    if (!svg || !b || !b.rect_km) return;
    const r = b.rect_km, Lm = (r[1] - r[0]) * 1000, Wm = (r[3] - r[2]) * 1000, toS = mapper(r);
    const fs = Math.max(Lm, Wm) / 32;
    const g = el("g", { id: "plan2d", "pointer-events": "none" });
    current = { uid, r, Lm, Wm, toS, els: [], dims: true };
    plans = [current];

    const token = (drawToken = (drawToken || 0) + 1);
    const model = await getModel(uid);
    if (token !== drawToken) return;  // a newer draw started while this one waited
    const tools = document.querySelector(".mapwrap .maptools");
    document.querySelectorAll(".plan-lv").forEach((x) => x.remove());
    if (model && model.levels && model.levels.length) {
      if (sel && sel.level) level = sel.level;
      if (!level || !model.levels.some((l) => l.id === level)) level = model.levels.find((l) => l.z_m >= 0) ? model.levels.find((l) => l.z_m >= 0).id : model.levels[0].id;
      if (tools) {
        model.levels.slice().reverse().forEach((l) => {
          const bt = document.createElement("button");
          bt.className = "plan-lv" + (l.id === level ? " on" : "");
          bt.textContent = l.name.split("·")[0].trim();
          bt.title = `Show the plan of ${l.name}: floor ${both(l.z_m)} above deck, ${both(l.height_m)} high`;
          bt.onclick = () => { level = l.id; location.hash = `#/building/${uid}/${l.id}`; };
          tools.prepend(bt);
        });
        const lb = document.createElement("button");
        lb.className = "plan-lv plan-labels" + (labelsOn ? " on" : "");
        lb.textContent = labelsOn ? "Labels: on" : "Labels: off";
        lb.title = "Show or hide all the writing on the plan";
        lb.onclick = () => { labelsOn = !labelsOn; localStorage.setItem("adxi.labels", labelsOn ? "on" : "off"); lb.textContent = labelsOn ? "Labels: on" : "Labels: off"; lb.classList.toggle("on", labelsOn); drawLabels(); };
        tools.prepend(lb);
      }
      const lv = (e) => (e.levels || [e.level]).includes(level);
      const els = (model.elements || []).filter(lv);
      // Grid lines, light.
      if (model.grid_m) {
        for (let x = 0; x <= Lm + 0.01; x += model.grid_m) { const a = toS([x, 0]), c = toS([x, Wm]); g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#6fd0ff", "stroke-opacity": 0.12, "stroke-width": fs / 20 })); }
        for (let y = 0; y <= Wm + 0.01; y += model.grid_m) { const a = toS([0, y]), c = toS([Lm, y]); g.append(el("line", { x1: a[0], y1: a[1], x2: c[0], y2: c[1], stroke: "#6fd0ff", "stroke-opacity": 0.12, "stroke-width": fs / 20 })); }
      }
      drawEls(g, els, toS, fs, { selRoom: sel && sel.room, onRoom: (e) => {
        history.replaceState(null, "", `#/building/${uid}/${level}:${encodeURIComponent(e.id)}`);
        drawBuilding(uid, { level, room: e.id }, true);
      } });
      current.els = els;
      current.empty = !els.length;
      current.level = level;
      const room = sel && sel.room && els.find((e) => e.id === sel.room);
      showRoom(uid, model, room, keepView);
    } else {
      current.noPlan = true;
    }
    const old = svg.querySelector("#plan2d"); if (old) old.remove();
    svg.append(g);
    drawLabels();
  }

  // ---- A selected room: zoom to it, add it to the breadcrumb, show its details, and tell the chat.
  // Level tags: L1, L2 … above deck, LB1, LB2 … below deck (nearest the deck first); none for single-level buildings.
  function levelTag(model, levelId) {
    const lv = model.levels || [];
    if (lv.length < 2) return "";
    const me = lv.find((l) => l.id === levelId);
    if (!me) return "";
    if (me.z_m < 0) return "LB" + (lv.filter((l) => l.z_m < 0).sort((a, b) => b.z_m - a.z_m).indexOf(me) + 1);
    return "L" + (lv.filter((l) => l.z_m >= 0).sort((a, b) => a.z_m - b.z_m).indexOf(me) + 1);
  }
  function roomNumber(model, room, levelId) {  // numbered per level, in plan order
    const onLevel = (e) => (e.levels || [e.level]).includes(levelId);
    const list = (model.elements || []).filter((e) => (e.type === "room" || e.type === "zone" || e.type === "core") && onLevel(e));
    return list.indexOf(room) + 1;
  }
  function roomDesignation(uid, model, room) {
    const b = typeof IX !== "undefined" && IX.buildings && IX.buildings[uid];
    const tag = levelTag(model, level), n = roomNumber(model, room, level);
    return b && window.designation ? window.designation(b, tag, n) : `${tag}R${n}`;
  }
  function showRoom(uid, model, room) {
    setTimeout(() => window.dispatchEvent(new Event("adxi:selection")), 0);  // tell the chat what is selected
    window.adxiRoom = null;
    document.querySelectorAll(".room-card").forEach((x) => x.remove());
    const cr0 = document.querySelector(".crumbs");
    if (cr0) { cr0.querySelectorAll(".crumb-extra").forEach((x) => x.remove()); }
    if (!room) return;
    const lv = model.levels.find((l) => l.id === level) || {};
    const xs = room.outline_m.map((p) => p[0]), ys = room.outline_m.map((p) => p[1]);
    const w = Math.max(...xs) - Math.min(...xs), h = Math.max(...ys) - Math.min(...ys), a = area(room.outline_m);
    const inside = (model.elements || []).filter((e) => e.parent === room.id);
    const desig = roomDesignation(uid, model, room);
    window.adxiRoom = { designation: desig, building_uid: uid, level: lv.id, level_name: lv.name, id: room.id, name: room.name, type: room.type,
      outline_m: room.outline_m, size_m: [w, h], area_m2: Math.round(a), status: room.status, contains: inside.map((e) => `${e.id} ${e.name || e.type}`) };
    // breadcrumb: Building › Level › Room
    const cr = document.querySelector(".crumbs");
    if (cr) {
      const last = cr.querySelector("b:not(.crumb-extra)");
      if (last) {
        const a1 = document.createElement("a"); a1.href = `#/building/${uid}`; a1.textContent = last.textContent; a1.className = "crumb crumb-bld";
        last.replaceWith(a1);
      }
      const tag = levelTag(model, lv.id) || lv.name || lv.id;
      const rn = "R" + roomNumber(model, room, lv.id);
      cr.insertAdjacentHTML("beforeend", `<span class="sep crumb-extra">›</span><a class="crumb crumb-extra" href="#/building/${uid}/${lv.id}" title="${esc(lv.name || "")}">${esc(tag)}</a><span class="sep crumb-extra">›</span><b class="crumb-room crumb-extra" title="${esc(room.name || "")}">${esc(rn)}</b>`);
    }
    const panel = document.querySelector(".panel");
    if (panel) {
      panel.insertAdjacentHTML("afterbegin", `<div class="room-card"><div class="small muted">Room · ${esc(lv.name || "")}</div><h2>${esc(room.name || room.id)}</h2><div class="small" style="margin:-4px 0 8px"><b>${esc(desig)}</b></div>
        <div class="kv"><div>Size</div><div>${both(w)} × ${both(h)}</div><div>Floor area</div><div>${sqft(a)}</div>
        <div>Ceiling height</div><div>${lv.height_m ? both(lv.height_m) : "not designed yet"}</div><div>Status</div><div>${esc(room.status || "proposed")}</div>
        <div>Inside</div><div>${inside.length ? inside.map((e) => esc(e.name || e.id)).join(", ") : "nothing designed yet"}</div></div>
        <div class="small muted" style="margin-top:6px">Ask the chat to design inside this room, for example "add a reception desk 24 ft long along the north wall".</div>
        <a class="small" href="#/building/${uid}/${lv.id}">← back to the whole level</a></div>`);
    }
  }

  // ---- Labels: same size on screen at any zoom; shown only where they fit; repeated rooms grouped.
  let current = null, plans = [], labelTimer = null, drawToken = 0;
  function groupRooms(rooms) {
    // "Quarter 1".."Quarter 10" of the same size in one row become one group.
    const groups = [], used = new Set();
    const key = (e) => {
      const m = /^(.*?)\s*(\d+)$/.exec(e.name || "");
      if (!m || !isRect(e.outline_m)) return null;
      const xs = e.outline_m.map((p) => p[0]), ys = e.outline_m.map((p) => p[1]);
      return { base: m[1], n: +m[2], w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys), y0: Math.min(...ys), x0: Math.min(...xs), y1: Math.max(...ys), x1: Math.max(...xs) };
    };
    const keyed = rooms.map((e) => ({ e, k: key(e) })).filter((o) => o.k);
    for (const o of keyed) {
      if (used.has(o.e)) continue;
      const row = keyed.filter((q) => !used.has(q.e) && q.k.base === o.k.base && Math.abs(q.k.w - o.k.w) < 0.01 && Math.abs(q.k.h - o.k.h) < 0.01 && Math.abs(q.k.y0 - o.k.y0) < 0.01)
        .sort((p, q) => p.k.x0 - q.k.x0);
      // only rooms that touch each other, side by side, form one group
      const runs = [];
      for (const q of row) { const last = runs[runs.length - 1]; if (last && q.k.x0 - last[last.length - 1].k.x1 < 0.5) last.push(q); else runs.push([q]); }
      const same = runs.find((r) => r.includes(o)) || [o];
      if (same.length < 3) continue;
      same.forEach((q) => used.add(q.e));
      const ns = same.map((q) => q.k.n).sort((a, b) => a - b);
      groups.push({ label: `${o.k.base}s ${ns[0]}–${ns[ns.length - 1]}`, sub: `${one(o.k.w)} × ${one(o.k.h)} each`,
        box: [Math.min(...same.map((q) => q.k.x0)), Math.min(...same.map((q) => q.k.y0)), Math.max(...same.map((q) => q.k.x1)), Math.max(...same.map((q) => q.k.y1))], members: same.map((q) => q.e) });
    }
    return { groups, used };
  }
  function drawLabels() {
    const svg = document.getElementById("map");
    if (!svg || !plans.length) return;
    const old = svg.querySelector("#plan2d-labels"); if (old) old.remove();
    const vb = svg.getAttribute("viewBox").split(/\s+/).map(Number);
    const px = vb[2] / Math.max(1, svg.getBoundingClientRect().width);  // map units per screen pixel
    const F = 12 * px;  // 12 px text on screen
    const g = el("g", { id: "plan2d-labels", "pointer-events": "none" });
    if (!labelsOn) { svg.append(g); return; }
    placed = [];
    for (const pl of plans) labelPlan(g, pl, px, F);
    svg.append(g);
  }
  function labelPlan(g, pl, px, F) {
    const { toS, Lm, Wm } = pl;
    // Footprint measurements, once, at a steady size (building page only).
    if (pl.dims) {
      dimLine(g, toS([0, 0]), toS([Lm, 0]), both(Lm), F, F * 2.2);
      dimLine(g, toS([0, Wm]), toS([0, 0]), both(Wm), F, F * 2.2);
    }
    // Each label is sized to fit inside its own room: it grows as you zoom in, up to 16 px on screen,
    // and is hidden when it would be smaller than 8 px. It never spills outside the room.
    const MAXPX = 16, MINPX = 8;
    const sizeFor = (box, lines) => {
      const a = toS([box[0], box[1]]), b = toS([box[2], box[3]]);
      const w = Math.abs(b[0] - a[0]) * 0.88, h = Math.abs(b[1] - a[1]) * 0.8;
      const byW = w / (Math.max(...lines.map((t) => t.length)) * 0.56), byH = h / (lines.length * 1.25);
      return Math.min(byW, byH, MAXPX * px);
    };
    const fits = (box, lines) => sizeFor(box, lines) >= MINPX * px;
    const put = (box, name, sub, color) => {
      const c = toS([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]);
      const s2 = sub ? sizeFor(box, [name, sub]) : 0, s1 = sizeFor(box, [name]);
      if (sub && s2 >= MINPX * px) { textAt(g, c[0], c[1] - s2 * 0.6, name, s2, { fill: color }); textAt(g, c[0], c[1] + s2 * 0.65, sub, s2 * 0.85, { fill: "#8fb0d3" }); }
      else if (s1 >= MINPX * px) textAt(g, c[0], c[1], name, s1, { fill: color });
    };
    const bbox = (e) => { const xs = e.outline_m.map((p) => p[0]), ys = e.outline_m.map((p) => p[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };
    const rooms = pl.els.filter((e) => e.type === "room" || e.type === "zone");
    const { groups, used } = groupRooms(rooms);
    for (const e of rooms) {
      const b = bbox(e);
      const one1 = isRect(e.outline_m) ? `${one(b[2] - b[0])} × ${one(b[3] - b[1])}` : sqft(area(e.outline_m));
      if (used.has(e)) { if (fits(b, [e.name])) put(b, e.name, one1, "#e8f1fb"); continue; }  // zoomed in: each one
      put(b, e.name || e.id, one1, "#e8f1fb");
    }
    for (const gr of groups) {  // zoomed out: one label for the row
      const anyShown = gr.members.some((e) => fits(bbox(e), [e.name]));
      if (!anyShown) put(gr.box, gr.label, gr.sub, "#e8f1fb");
    }
    for (const e of pl.els.filter((x) => x.type === "core")) put(bbox(e), "Stairs & lifts", null, "#ffb84d");
    for (const e of pl.els.filter((x) => x.type === "door" || x.type === "opening")) {
      const [a, c] = [toS(e.line_m[0]), toS(e.line_m[e.line_m.length - 1])];
      textAt(g, (a[0] + c[0]) / 2, (a[1] + c[1]) / 2 - F * 1.1, `${e.name || (e.type === "door" ? "Door" : "Opening")}${e.width_m ? " · " + one(e.width_m) : ""}`, F * 0.9, { fill: "#5fd39a" });
    }
    const mid = toS([Lm / 2, Wm / 2]);
    const box = () => { const a = toS([0, 0]), b = toS([Lm, Wm]); return [Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])]; };
    const fitIn = (t, f) => Math.min(f, box()[0] * 0.9 / (t.length * 0.56));
    // A message goes inside the footprint only when it fits there and does not sit on another label.
    // On a block page it sits above the middle, clear of the name and the measurements.
    const lift = pl.dims ? 0 : -1.6;
    const msg = (t, dy) => {
      const f = fitIn(t, F); if (f < 6 * px) return;
      const y = mid[1] + (dy + lift) * f;
      if (!pl.dims && Math.abs(y - mid[1]) + f * 0.7 > box()[1] / 2) return;  // too thin: leave it out
      place(g, mid[0], y, t, f, { fill: "#8fb0d3" });
    };
    if (pl.title) { const f = fitIn(pl.title, F * 1.1), top = toS([Lm / 2, 0]); if (f >= 6 * px) place(g, top[0], top[1] - f * 0.9, pl.title, f, { fill: "#ffc266" }); }
    // Floor plans are for buildings. Streets, concourses, aprons, bays, parks and plazas never get this note.
    const roofed = !pl.kind || pl.kind === "building" || pl.kind === "utility";
    if (pl.noPlan && roofed) msg(pl.dims ? "Floor plan not designed yet · ask the chat to draw it" : "Floor plan not designed yet", pl.dims ? 2 : 0);
    if (pl.notHere) msg(pl.notHere, 0);
    if (pl.empty) msg("Nothing drawn on this level yet", 0);
  }
  // Redraw labels when the map is zoomed or moved.
  new MutationObserver((ms) => {
    if (!ms.some((m) => m.attributeName === "viewBox")) return;
    clearTimeout(labelTimer);
    labelTimer = setTimeout(() => { drawLabels(); drawSizes(); }, 60);
  }).observe(document.body, { attributes: true, subtree: true, attributeFilter: ["viewBox"] });

  function drawSizes() {
    const svg = document.getElementById("map");
    const old = svg && svg.querySelector("#sizes2d"); if (old) old.remove();
    if (!svg || !sizesOn || typeof IX === "undefined") return;
    const vb = svg.getAttribute("viewBox").split(/\s+/).map(Number), fs = 11 * vb[2] / Math.max(1, svg.getBoundingClientRect().width);
    const g = el("g", { id: "sizes2d", "pointer-events": "none" });
    // Sit each size just under its building's name, inside the open part of the shape the name uses;
    // leave it off when it would not fit there (never on top of the name or over a courtyard).
    const lbls = {};
    for (const t of svg.querySelectorAll("text[data-lbl]")) lbls[t.dataset.lbl] = t;
    for (const b of Object.values(IX.buildings || {})) {
      if (!b.rect_km) continue;
      const r = b.rect_km, w = (r[1] - r[0]) * 1000, h = (r[3] - r[2]) * 1000;
      const t = `${one(w)} × ${one(h)}`, tw = t.length * fs * 0.58;
      const lb = lbls[b.uid];
      let sp, x, y;
      if (lb) {
        sp = lb.dataset.spot.split(" ").map(Number);   // x0 y0 x1 y1 of the open part
        x = (sp[0] + sp[2]) / 2;
        const mid = (sp[1] + sp[3]) / 2;
        // a sideways name runs down the middle: the size goes under it only when the open part is wide enough
        y = lb.dataset.side === "1" ? mid : mid + (+lb.dataset.th) / 2 + fs * 0.8;
        if (lb.dataset.side === "1") { x = (sp[0] + sp[2]) / 2 + (+lb.dataset.th) / 2 + tw / 2 + fs * 0.4; }
      } else {
        sp = [Math.min(X(r[0]), X(r[1])), Math.min(Y(r[2]), Y(r[3])), Math.max(X(r[0]), X(r[1])), Math.max(Y(r[2]), Y(r[3]))];
        if (b.outline_km || b.bays_km) continue;      // hidden name (too small) or a row of bays: no single size spot
        x = (sp[0] + sp[2]) / 2; y = (sp[1] + sp[3]) / 2;
      }
      if (x < vb[0] || x > vb[0] + vb[2] || y < vb[1] || y > vb[1] + vb[3]) continue;
      if (x - tw / 2 < sp[0] || x + tw / 2 > sp[2] || y - fs * 0.6 < sp[1] || y + fs * 0.6 > sp[3]) continue;  // too small at this zoom
      textAt(g, x, y, t, fs, { fill: "#ffc266" });
    }
    svg.append(g);
  }

  // ---- Block page: every building in the block drawn with its real plan, one floor at a time.
  // Floors are matched by level code (LB2, LB1, L1, L2 ...), the same codes the building pages use.
  const tagOf = (model, l) => levelTag(model, l.id) || "L1";
  const tagKey = (t) => (/^LB(\d+)$/.test(t) ? -+t.slice(2) : +t.slice(1));
  async function drawBlock(puid, bid, want) {
    const svg = document.getElementById("map");
    const p = typeof IX !== "undefined" && IX.precincts && IX.precincts[puid];
    const blk = p && (p.blocks || []).find((k) => k.id === bid);
    if (!svg || !blk) return;
    const token = (drawToken = (drawToken || 0) + 1);
    const list = blk.contents.map((ct) => p.buildings.find((q) => q.id === ct.id)).filter((b) => b && b.rect_km);
    const models = await Promise.all(list.map((b) => getModel(b.uid)));
    if (token !== drawToken) return;
    const tags = new Set();
    models.forEach((m) => m && (m.levels || []).forEach((l) => tags.add(tagOf(m, l))));
    const all = [...tags].sort((a, b) => tagKey(a) - tagKey(b));
    const tag = all.includes(want) ? want : all.includes("L1") ? "L1" : all[0];
    const g = el("g", { id: "plan2d", "pointer-events": "none" });
    plans = [];
    list.forEach((b, i) => {
      const r = b.rect_km, Lm = (r[1] - r[0]) * 1000, Wm = (r[3] - r[2]) * 1000, toS = mapper(r), m = models[i];
      const pl = { uid: b.uid, kind: b.kind, r, Lm, Wm, toS, els: [], title: `${b.id} ${b.name}` };
      plans.push(pl);
      // No plan: the map already names it inside its own box, so no extra title above it
      // (titles above thin strips landed on the neighbours).
      if (!m || !(m.levels || []).length) { pl.noPlan = true; pl.title = null; return; }
      const lv = m.levels.find((l) => tagOf(m, l) === tag);
      const a = toS([0, 0]), c = toS([Lm, Wm]);
      g.append(el("rect", { x: Math.min(a[0], c[0]), y: Math.min(a[1], c[1]), width: Math.abs(c[0] - a[0]), height: Math.abs(c[1] - a[1]), fill: "#0b2140", stroke: "#e8f1fb", "stroke-width": Math.max(Lm, Wm) / 200 }));
      if (!lv) { pl.notHere = `No ${tag} in this building`; return; }
      pl.els = (m.elements || []).filter((e) => (e.levels || [e.level]).includes(lv.id));
      pl.empty = !pl.els.length;
      drawEls(g, pl.els, toS, Math.max(Lm, Wm) / 32, {});  // on a block page only the buildings are clickable
    });
    const tools = document.querySelector(".mapwrap .maptools");
    document.querySelectorAll(".plan-lv").forEach((x) => x.remove());
    if (tools && all.length) {
      all.slice().reverse().forEach((t) => {
        const bt = document.createElement("button");
        bt.className = "plan-lv" + (t === tag ? " on" : "");
        bt.textContent = t;
        const names = list.map((b, i) => { const m = models[i], l = m && m.levels.find((q) => tagOf(m, q) === t); return l ? `${b.name}: ${l.name}` : null; }).filter(Boolean);
        bt.title = `Show floor ${t} of every building in this block\n` + names.join("\n");
        bt.onclick = () => { location.hash = `#/block/${puid}/${bid}/${t}`; };
        tools.prepend(bt);
      });
      const lb = document.createElement("button");
      lb.className = "plan-lv plan-labels" + (labelsOn ? " on" : "");
      lb.textContent = labelsOn ? "Labels: on" : "Labels: off";
      lb.title = "Show or hide all the writing on the plan";
      lb.onclick = () => { labelsOn = !labelsOn; localStorage.setItem("adxi.labels", labelsOn ? "on" : "off"); lb.textContent = labelsOn ? "Labels: on" : "Labels: off"; lb.classList.toggle("on", labelsOn); drawLabels(); };
      tools.prepend(lb);
    }
    const old = svg.querySelector("#plan2d"); if (old) old.remove();
    svg.append(g);
    drawLabels();
  }

  function hook() {
    const h = location.hash.replace(/^#\/?/, "");
    const [kind, a] = h.split("/").map(decodeURIComponent);
    desigLegend();
    if (kind !== "building" && kind !== "block") { current = null; plans = []; drawToken++; }
    if (kind === "block") drawBlock(a, decodeURIComponent(h.split("/")[2] || ""), decodeURIComponent(h.split("/")[3] || ""));
    if (kind === "building") {
      const extra = h.split("/")[2] || "";
      const [lv, room] = decodeURIComponent(extra).split(":");
      drawBuilding(a, { level: lv || null, room: room || null });
    }
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

  // A small legend for the designation code, on every map.
  function desigLegend() {
    const wrap = document.querySelector(".mapwrap");
    if (!wrap || wrap.querySelector(".desig-legend")) return;
    const d = document.createElement("div");
    d.className = "desig-legend";
    d.title = "How designations are written";
    d.innerHTML = '<button type="button" class="dl-btn" title="What the codes mean">Codes ?</button><div class="dl-box"><b>D5F1P1B1A1L2R1</b><br>D · Deck<br>F · District<br>P · Precinct<br>B · Block<br>A · Building<br>L · Level (LB below deck)<br>R · Room</div>';
    d.querySelector(".dl-btn").onclick = () => d.classList.toggle("open");
    wrap.append(d);
    // the colour legend button sits just right of Codes
    const lg = wrap.querySelector(".map-legend");
    if (lg) lg.style.left = (d.offsetLeft + d.querySelector(".dl-btn").offsetWidth + 8) + "px";
  }

  // Redraw whenever the app renders a page.
  const app = document.getElementById("app");
  if (app) new MutationObserver(() => { if (document.getElementById("map") && !document.getElementById("map").dataset.plan) { document.getElementById("map").dataset.plan = "1"; hook(); } }).observe(app, { childList: true });
})();
