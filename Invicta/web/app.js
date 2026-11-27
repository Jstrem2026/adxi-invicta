/* ADXI: Invicta front end. Plain JavaScript, no libraries.
   Every map is a true top view: bow RIGHT, port UP (matches the Unreal level).
   Ship frame from the data: x km from the prow tip, y km across (port negative). */
"use strict";

const SHIP_L = 34.0;               // km, prow tip to stern
const M_FT = 3.28084, KM2_SQMI = 1 / 2.589988, M2_ACRE = 1 / 4046.8564224;
const LANES = "ABCDEFGHIJKLMNOPQRSTUVWXY";
const KIND_FILL = { building: "#3b5b7f", utility: "#4a4f57", park: "#2f6b4a", plaza: "#4a4128", transport: "#2c3440", bays: "#6b4a2b" };
let D = null;                      // everything from /api/all
let IX = {};                       // lookups
let precinctMode = "blocks";
let showKnown = true;
let issueFilter = { sev: "all", q: "" };

// ------------------------------------------------------------------ formatting
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const n0 = v => Math.round(v).toLocaleString("en-US");
const nd = (v, d) => Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
// Units: "us" (feet first, metres in brackets) or "metric" (Australian practice: m, mm for small sizes).
const metric = () => { try { return localStorage.getItem("adxi.units") === "metric"; } catch (e) { return false; } };
const mm = v => v < 10 ? `${n0(v * 1000)} mm` : `${v >= 100 ? n0(v) : nd(v, 1)} m`;
function len(m) {                   // US first, metric in brackets (or metric only)
  if (m == null || isNaN(m)) return "—";
  if (metric()) return m >= 1600 ? `${nd(m / 1000, 2)} km` : mm(m);
  if (m >= 1600) return `${nd(m / 1609.344, 2)} mi (${nd(m / 1000, 2)} km)`;
  return `${n0(m * M_FT)} ft (${m >= 10 ? n0(m) : nd(m, 1)} m)`;
}
function dims(w, h, ht) {
  const vals = [w, h, ht].filter(v => v != null);
  if (metric()) return vals.every(v => v < 10) ? `${vals.map(v => n0(v * 1000)).join(" × ")} mm` : `${vals.map(v => n0(v)).join(" × ")} m`;
  const ft = vals.map(v => n0(v * M_FT)).join(" × ");
  const m = vals.map(v => n0(v)).join(" × ");
  return `${ft} ft (${m} m)`;
}
function area(km2) {
  if (km2 == null || isNaN(km2)) return "—";
  if (metric()) return km2 >= 0.5 ? `${nd(km2, 2)} km²` : km2 * 1e6 >= 10000 ? `${nd(km2 * 100, 1)} ha (${n0(km2 * 1e6)} m²)` : `${n0(km2 * 1e6)} m²`;
  if (km2 >= 0.5) return `${nd(km2 * KM2_SQMI, 2)} sq mi (${nd(km2, 2)} km²)`;
  return `${nd(km2 * 1e6 * M2_ACRE, 1)} acres (${n0(km2 * 1e6)} m²)`;
}
function badge(status) {
  const s = (status || "").toLowerCase();
  if (s.startsWith("not")) return `<span class="badge b-not">not designed yet</span>`;
  if (s.startsWith("canon")) return `<span class="badge b-canon">${esc(status)}</span>`;
  if (s.startsWith("assum")) return `<span class="badge b-assumption">assumption</span>`;
  if (s.startsWith("placeholder") || s.startsWith("tune")) return `<span class="badge b-placeholder">placeholder</span>`;
  if (s.startsWith("started")) return `<span class="badge b-started">started</span>`;
  return `<span class="badge b-proposed">${esc(status || "proposed")}</span>`;
}
const ND = `<span class="notdesigned">not designed yet</span>`;
const fileLink = (rel, label) => rel ? `<a href="/file?path=${encodeURIComponent(rel)}" target="_blank" rel="noopener">${esc(label || rel.split("/").pop())}</a>` : "";
// US + metric for a canon text value such as "1,560 m / 2,160 m" or "33 x 12.1 km, 311.2 km²"
function usText(v) {
  if (!v) return "";
  let out = String(v);
  const conv = [];
  out.replace(/([\d,]+(?:\.\d+)?)\s*km²/g, (m, a) => { conv.push(`${nd(parseFloat(a.replace(/,/g, "")) * KM2_SQMI, 1)} sq mi`); });
  if (!conv.length) out.replace(/([\d,]+(?:\.\d+)?)\s*(km|m)\b(?!²|³)/g, (m, a, u) => {
    const x = parseFloat(a.replace(/,/g, "")) * (u === "km" ? 1000 : 1);
    conv.push(u === "km" ? `${nd(x / 1609.344, 2)} mi` : `${n0(x * M_FT)} ft`);
  });
  return conv.length ? `${esc(conv.join(" / "))} <span class="muted">(${esc(v)})</span>` : esc(v);
}

// ------------------------------------------------------------------ data
async function load() {
  document.getElementById("rescan").disabled = true;
  try {
    const r = await fetch("/api/all", { cache: "no-store" });
    if (!r.ok) throw new Error(await r.text());
    D = await r.json();
  } catch (e) {
    document.getElementById("app").innerHTML = `<div class="note">The app could not read the files: ${esc(e.message)}</div>`;
    return;
  } finally { document.getElementById("rescan").disabled = false; }
  index();
  // Concept art (data/concepts.json): mood and look references per building, never canon.
  if (!D.concepts) {
    try { const c = await fetch("/file?path=Invicta/data/concepts.json", { cache: "no-store" }); D.concepts = c.ok ? await c.json() : {}; } catch (e) { D.concepts = {}; }
  }
  const open = D.issues.filter(i => (i.severity === "error" || i.severity === "warning") && !i.known).length;
  const errs = D.issues.filter(i => i.severity === "error" && !i.known).length;
  const pill = document.getElementById("issue-pill");
  pill.textContent = open || "";
  pill.classList.toggle("warn", !errs);  // red only when there are real errors, yellow for warnings
  pill.title = errs ? `${errs} errors` : `${open} warnings, no errors`;
  document.getElementById("scan-time").textContent = `Read ${D.model.generated} · ${D.scan_ms} ms`;
  route();
}
function index() {
  IX = { decks: {}, districts: {}, psets: {}, precincts: {}, buildings: {} };
  for (const d of D.model.decks) {
    IX.decks[d.n] = d;
    for (const x of d.districts) { x.deck = d.n; IX.districts[x.id] = x; }
  }
  for (const [did, ps] of Object.entries(D.model.precinct_sets)) {
    IX.psets[did] = ps;
    for (const p of ps.precincts) {
      p.district_id = did; IX.precincts[p.uid] = p;
      for (const b of p.buildings) { b.precinct_uid = p.uid; IX.buildings[b.uid] = b; }
    }
  }
}
function issuesFor(id) {
  if (!id) return [];
  return D.issues.filter(i => i.entity && (i.entity === id || i.entity.startsWith(id + "-")));
}
function issueHTML(i) {
  return `<div class="issue ${i.severity}${i.known ? " known" : ""}">
    <div class="t"><span class="sev-${i.severity}">${sevName(i.severity)}</span> · ${esc(i.title)}</div>
    <div>${esc(i.detail)}</div>
    ${i.fix ? `<div class="meta">Fix: ${esc(i.fix)}</div>` : ""}
    <div class="meta">${i.path ? fileLink(i.path, i.path) : ""}${i.entity && entityHref(i.entity) ? ` · <a href="${entityHref(i.entity)}">show on map</a>` : ""}${i.known ? ` · known: ${esc(i.known)}` : ""} · ${i.id}</div></div>`;
}
const sevName = s => ({ error: "Error", warning: "Warning", decision: "Waiting on Jordan", gap: "Not designed yet" }[s] || s);
function entityHref(e) {
  if (IX.buildings[e]) return `#/building/${e}`;
  if (IX.precincts[e]) return `#/precinct/${e}`;
  if (IX.districts[e]) return `#/district/${e}`;
  const m = /^D(\d)$/.exec(e); if (m) return `#/deck/${m[1]}`;
  if (e === "ship") return "#/ship";
  return "";
}
function issueBlock(id, title) {
  const list = issuesFor(id);
  if (!list.length) return `<h3>${title || "Issues here"}</h3><div class="muted small">None found.</div>`;
  const order = { error: 0, warning: 1, decision: 2, gap: 3 };
  list.sort((a, b) => order[a.severity] - order[b.severity]);
  return `<h3>${title || "Issues here"} (${list.length})</h3>` + list.map(issueHTML).join("");
}

// ------------------------------------------------------------------ routing
function route() {
  if (!D) return;
  const h = location.hash.replace(/^#\/?/, "") || "dashboard";
  const [kind, a, b] = h.split("/").map(decodeURIComponent);
  const tab = { dashboard: "dashboard", issues: "issues", sources: "sources", help: "help" }[kind] || "explore";
  document.querySelectorAll("#tabs a").forEach(x => x.classList.toggle("active", x.dataset.tab === tab));
  const app = document.getElementById("app");
  try {
    if (kind === "dashboard") app.innerHTML = dashboard();
    else if (kind === "issues") { app.innerHTML = issuesPage(); bindIssues(); }
    else if (kind === "sources") app.innerHTML = sourcesPage();
    else if (kind === "help") app.innerHTML = helpPage();
    else explore(kind, a, b);
  } catch (e) {
    app.innerHTML = `<div class="note">Could not show this page: ${esc(e.message)}</div>`;
    console.error(e);
  }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
document.getElementById("rescan").addEventListener("click", load);

// ------------------------------------------------------------------ dashboard
function dashboard() {
  const P = D.progress, m = D.model;
  const sev = P.issues;
  const levels = P.levels.map(l => {
    const pct = l.of ? Math.min(100, 100 * l.have / l.of) : null;
    return `<tr><td><b>${esc(l.level)}</b></td><td>${badge(l.state)}</td>
      <td style="width:28%">${pct == null ? `<span class="muted">${n0(l.have)} so far</span>` : `<div class="bar"><span style="width:${pct.toFixed(1)}%"></span></div><span class="small muted">${n0(l.have)} of ${n0(l.of)} · ${pct < 1 && pct > 0 ? pct.toFixed(2) : pct.toFixed(0)}%</span>`}</td>
      <td class="small">${esc(l.note)}</td></tr>`;
  }).join("");
  const decks = P.decks.map(d => {
    const pct = d.net_area ? 100 * d.planned_area / d.net_area : 0;
    return `<tr class="click" onclick="location.hash='#/deck/${d.n}'"><td><b>${d.n} ${esc(d.name)}</b><div class="small muted">${esc(d.role)}</div></td>
      <td>${area(d.net_area)}</td><td>${d.districts_planned} of ${d.districts}</td><td>${d.precincts || "—"}</td><td>${d.buildings || "—"}</td>
      <td style="width:18%"><div class="bar"><span style="width:${pct.toFixed(1)}%"></span></div><span class="small muted">${pct.toFixed(1)}% planned</span></td>
      <td>${d.issues ? `<span class="sev-warning">${d.issues}</span>` : "<span class='muted'>0</span>"}</td></tr>`;
  }).join("");
  const next = [];
  for (const ps of Object.values(D.model.precinct_sets)) {
    const ordered = ps.precincts.slice().sort((a, b) => (a.build_order || 99) - (b.build_order || 99));
    next.push(`<h3>${esc(ps.district)} · build order (${esc(ps.status)})</h3><ol class="small">` +
      ordered.map(p => `<li><a href="#/precinct/${p.uid}">${p.id} ${esc(p.name)}</a> · ${p.buildings.length} buildings · ${area(p.area_km2_stated)}</li>`).join("") + "</ol>");
  }
  return `<h1>Building the Invicta</h1>
  <div class="grid cards">
    <div class="card"><div class="lbl">Design coverage</div><div class="big">${P.planned_pct.toFixed(1)}%</div><div class="small muted">${area(P.planned_area_km2)} of ${esc(P.total_area_text)} has precinct plans</div></div>
    <div class="card"><div class="lbl">Buildings placed</div><div class="big">${n0(P.levels.find(l => l.level === "Buildings").have)}</div><div class="small muted">${Object.entries(P.buildings_by_status).map(([k, v]) => `${v} ${k}`).join(", ") || "none yet"}</div></div>
    <a class="card" href="#/issues"><div class="lbl">Errors · warnings</div><div class="big"><span class="sev-error">${sev.error || 0}</span> · <span class="sev-warning">${sev.warning || 0}</span></div><div class="small muted">${sev.decision || 0} waiting on Jordan · ${sev.gap || 0} not designed yet${sev.warning_known ? ` · ${sev.warning_known} known` : ""}</div></a>
    <div class="card"><div class="lbl">Canon errata (Rev B)</div><div class="big">${P.errata.decided} · ${P.errata.proposed}</div><div class="small muted">rows decided · rows waiting for a decision</div></div>
  </div>
  <h2>Progress by level</h2>
  <div class="card"><table><tr><th>Level</th><th>State</th><th>Progress</th><th>What it means</th></tr>${levels}</table></div>
  <h2>Deck cities</h2>
  <div class="card"><table><tr><th>Deck</th><th>Net floor</th><th>Districts planned</th><th>Precincts</th><th>Buildings</th><th>Planned area</th><th>Open issues</th></tr>${decks}</table></div>
  <h2>Next up</h2><div class="card">${next.join("") || "<div class='muted'>No precinct plans yet.</div>"}
  <div class="small muted">Anything not listed is not designed yet. The app shows it as such and does not fill it in.</div></div>`;
}

// ------------------------------------------------------------------ issues and sources
function issuesPage() {
  const cats = [...new Set(D.issues.map(i => i.category))].sort();
  const btn = (k, label) => `<button data-sev="${k}" class="${issueFilter.sev === k ? "on" : ""}">${label}</button>`;
  const counts = s => D.issues.filter(i => i.severity === s && (showKnown || !i.known)).length;
  return `<h1>Scanner</h1>
  <div class="filters">${btn("all", "All")}${btn("error", `Errors (${counts("error")})`)}${btn("warning", `Warnings (${counts("warning")})`)}${btn("decision", `Waiting on Jordan (${counts("decision")})`)}${btn("gap", `Not designed yet (${counts("gap")})`)}
  <input id="q" placeholder="Search (title, file, place…)" value="${esc(issueFilter.q)}">
  <label class="small"><input type="checkbox" id="known" ${showKnown ? "checked" : ""}> show known</label>
  <a href="/api/report.md" target="_blank">Download report (.md)</a></div>
  <div class="small muted">Categories: ${cats.map(esc).join(", ")}. Every scan reads the files fresh; press Rescan after editing.</div>
  <div id="issue-list"></div>`;
}
function bindIssues() {
  const draw = () => {
    const q = issueFilter.q.toLowerCase();
    const list = D.issues.filter(i => (issueFilter.sev === "all" || i.severity === issueFilter.sev) && (showKnown || !i.known) &&
      (!q || (i.title + " " + i.detail + " " + (i.path || "") + " " + (i.entity || "") + " " + i.category).toLowerCase().includes(q)));
    document.getElementById("issue-list").innerHTML = list.map(issueHTML).join("") || "<div class='muted'>Nothing matches.</div>";
  };
  document.querySelectorAll("[data-sev]").forEach(b => b.onclick = () => { issueFilter.sev = b.dataset.sev; route(); });
  document.getElementById("q").oninput = e => { issueFilter.q = e.target.value; draw(); };
  document.getElementById("known").onchange = e => { showKnown = e.target.checked; route(); };
  draw();
}
function sourcesPage() {
  const rows = D.model.sources.map(s => `<tr><td>${s.exists ? fileLink(s.path, s.path) : `<span class="sev-error">${esc(s.path)}</span>`}</td><td>${esc(s.role)}</td>
    <td>${s.exists ? "✓" : "<span class='sev-error'>missing</span>"}</td><td class="small">${s.mtime ? new Date(s.mtime * 1000).toLocaleString() : ""}</td></tr>`).join("");
  return `<h1>Sources</h1><p class="muted">The app reads these files every time it loads and never writes to them. Folder: <code>${esc(D.model.root)}</code></p>
  <div class="card"><table><tr><th>File</th><th>Used for</th><th>Found</th><th>Last changed</th></tr>${rows}</table></div>`;
}
function helpPage() {
  return `<div class="help"><h1>How the app works</h1>
  <p><b>ADXI: Invicta</b>: AD stands for Arcane Drift and XI for version 11.</p>
  <p>The app is a window onto the Invicta files. It reads the canon data sheets, the Revision B geometry, the game's <code>invicta_geometry.py</code>, the design docs in <code>Game/Docs</code>, and its own design data in <code>Invicta/data</code>, every time you press Rescan. Nothing is cached, and the app never changes the source files.</p>
  <h2>Exploring</h2><ul>
  <li><b>Ship</b>: click a deck in the side view (vertical scale ×2.5) or in the list.</li>
  <li><b>Deck city</b>: click a district. Districts with a precinct plan are solid; hatched ones are not designed yet.</li>
  <li><b>District</b>: click a precinct.</li>
  <li><b>Precinct</b>: in <i>Blocks</i> mode, click a block (the land between streets); in <i>Buildings</i> mode, click a building directly.</li>
  <li><b>Block</b>: click a building to see everything known about it. Unknown details say <i>not designed yet</i>.</li>
  <li>Scroll to zoom, drag to move, <i>Fit</i> to reset.</li></ul>
  <h2>Conventions</h2><ul>
  <li>Every plan is a true top view: <b>bow right, port up</b>, matching the Unreal level. The canon sheets draw bow left (a mirror); the app flips them.</li>
  <li>Measurements: US units first, metric in brackets.</li>
  <li>Addresses (D5-F43-F) name the nearest frame line and the lane, as canon does. A <b>block</b> is a city block: the land between streets. Blocks follow the 500 m frame and lane grid where they can, but a block edge never cuts through a building, so each building sits wholly inside one block. Each block has a plain name (Block 1, Block 2 …) and an id from the frame and lane at its bow-port corner, for example <code>D5-F43-A</code>. Anything without its own name gets a generic one (Street A, Berth 3, Hangar 12).</li>
  <li>Lanes A to Y are 500 m bands centred every 500 m; M is on the centreline, A is the port edge.</li></ul>
  <h2>Scanner</h2><ul>
  <li><span class="sev-error">Error</span>: broken or contradictory data (missing file, building through the hull, game and canon disagree).</li>
  <li><span class="sev-warning">Warning</span>: two sources disagree, a doc and the data drifted apart, a mirror copy differs, units do not convert.</li>
  <li><span class="sev-decision">Waiting on Jordan</span>: proposed, assumed or placeholder values.</li>
  <li><span class="sev-gap">Not designed yet</span>: areas with no plan. Listed so they are never filled in by guesswork.</li></ul>
  <p>To mark an issue as known, add its id or a phrase from it to <code>acknowledged</code> in <code>Invicta/data/rules.json</code>.</p>
  <h2>Working with Claude</h2>
  <p>Design sessions follow <code>Invicta/CLAUDE.md</code>: new precincts and buildings go into <code>Invicta/data</code> and into the design doc in the same change, then <code>python atlas.py --scan</code> must come back with no new errors.</p></div>`;
}

// ------------------------------------------------------------------ map helpers
const X = x => (SHIP_L - x) * 1000;     // bow right: prow tip (x=0) at the right edge
const Y = y => y * 1000;                 // port (negative y) up
const pt = p => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`;
const pathOf = pts => pts && pts.length ? "M" + pts.map(pt).join("L") + "Z" : "";
function rectEl(r, attrs) {             // r = [x0, x1, y0, y1] in km
  const x = X(r[1]), y = Y(r[2]), w = (r[1] - r[0]) * 1000, h = (r[3] - r[2]) * 1000;
  return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" ${attrs || ""}/>`;
}
function bboxOf(pts) {
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  return [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
}
function vbFor(b, padKm) {             // viewBox for a ship-frame bbox
  const p = padKm == null ? Math.max(b[1] - b[0], b[3] - b[2]) * 0.06 : padKm;
  return [X(b[1] + p), Y(b[2] - p), (b[1] - b[0] + 2 * p) * 1000, (b[3] - b[2] + 2 * p) * 1000];
}
function label(x, y, text, size, opts) {
  opts = opts || {};
  return `<text x="${X(x).toFixed(1)}" y="${Y(y).toFixed(1)}" font-size="${size.toFixed(1)}" fill="${opts.fill || "#e8f1fb"}" text-anchor="${opts.anchor || "middle"}" dominant-baseline="middle" font-weight="${opts.weight || 600}">${esc(text)}</text>`;
}
function labelR(x, y, text, size, opts) {
  opts = opts || {};
  return `<text transform="rotate(-90 ${X(x).toFixed(1)} ${Y(y).toFixed(1)})" x="${X(x).toFixed(1)}" y="${Y(y).toFixed(1)}" font-size="${size.toFixed(1)}" fill="${opts.fill || "#e8f1fb"}" text-anchor="middle" dominant-baseline="middle" font-weight="${opts.weight || 600}">${esc(text)}</text>`;
}
// fit a label in a box, turning it sideways when the box is tall; never drops a label
function boxLabel(r, text, fs, opts) {
  const w = (r[1] - r[0]) * 1000, h = (r[3] - r[2]) * 1000, cx = (r[0] + r[1]) / 2, cy = (r[2] + r[3]) / 2;
  const tall = h > w * 1.3;
  const along = tall ? h : w, across = tall ? w : h;
  let s = Math.min(fs, (along * 0.92) / Math.max(1, text.length * 0.58), across * 0.8);
  s = Math.max(s, fs * 0.12);
  return tall ? labelR(cx, cy, text, s, opts) : label(cx, cy, text, s, opts);
}
function fitText(name, wKm, hKm, fs) {
  const w = wKm * 1000, h = hKm * 1000;
  let s = fs;
  if (name.length * s * 0.56 > w * 0.92) s = (w * 0.92) / (name.length * 0.56);
  return s >= fs * 0.5 && s <= h * 0.8 ? s : 0;
}
function frameGrid(b, everyFrames, fs, showLanes) {
  let g = "";
  const f0 = Math.ceil(b[0] / 0.5), f1 = Math.floor(b[1] / 0.5);
  while ((f1 - f0) / everyFrames > 26) everyFrames *= 2;
  for (let f = f0; f <= f1; f++) {
    if (f % everyFrames) continue;
    g += `<line x1="${X(f * 0.5)}" y1="${Y(b[2])}" x2="${X(f * 0.5)}" y2="${Y(b[3])}" stroke="#1d4f86" stroke-width="${fs / 10}" stroke-dasharray="${fs / 3} ${fs / 3}"/>`;
    g += label(f * 0.5, b[2] - fs * 0.0009, `F${f}`, fs * 0.8, { fill: "#7fb0de", weight: 400 });
  }
  if (showLanes) {
    for (let i = 0; i < 25; i++) {
      const yc = (i - 12) * 0.5;
      if (yc - 0.25 < b[2] - 0.01 || yc + 0.25 > b[3] + 0.01) { if (yc < b[2] || yc > b[3]) continue; }
      g += label(b[1] + fs * 0.0011, yc, LANES[i], fs * 0.75, { fill: "#7fb0de", weight: 400 });
    }
  }
  return g;
}
function scaleBar(vb) {
  const w = vb[2];
  const steps = [100, 200, 500, 1000, 2000, 5000];
  const ft = [500, 1000, 2000, 5000, 10000, 20000];
  const target = w / 6;
  let mi = 0; for (let i = 0; i < steps.length; i++) if (steps[i] <= target) mi = i;
  const m = steps[mi];
  const fs = w / 70;
  const x = vb[0] + w * 0.03, y = vb[1] + vb[3] - fs * 1.6;
  return `<g><rect x="${x}" y="${y}" width="${m}" height="${fs / 3}" fill="#e8f1fb"/>
    <text x="${x}" y="${y - fs * 0.5}" font-size="${fs * 0.8}" fill="#cfe3f7">${m >= 1000 ? (m / 1000) + " km" : m + " m"} (${n0(m * M_FT)} ft)</text>
    <text x="${x + vb[2] - vb[2] * 0.06}" y="${y}" font-size="${fs * 0.8}" fill="#7fb0de" text-anchor="end">◀ stern · bow ▶ · port ▲</text></g>`;
}
function mapShell(svgInner, vb, tools, legend, hint) {
  return `<div class="mapwrap"><svg id="map" viewBox="${vb.map(v => v.toFixed(1)).join(" ")}" data-vb="${vb.join(",")}" preserveAspectRatio="xMidYMid meet">
    <defs><pattern id="hatch" width="160" height="160" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="160" height="160" fill="#16283d"/><line x1="0" y1="0" x2="0" y2="160" stroke="#2b4563" stroke-width="40"/></pattern>
    <pattern id="hatchS" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="40" height="40" fill="#16283d"/><line x1="0" y1="0" x2="0" y2="40" stroke="#2b4563" stroke-width="10"/></pattern></defs>
    ${svgInner}${scaleBar(vb)}</svg>
    <div class="maptools">${tools || ""}<button onclick="fitMap()">Fit</button></div>
    <div class="maphint">${("ontouchstart" in window) ? (hint || "Scroll to zoom · drag to move").replace(/[Ss]croll to zoom/, "pinch to zoom").replace(/^p/, (hint ? "p" : "P")) : (hint || "Scroll to zoom · drag to move")}</div></div>${legend ? `<div class="legend">${legend}</div>` : ""}`;
}
function bindMap() {
  const svg = document.getElementById("map");
  if (!svg) return;
  let vb = svg.getAttribute("viewBox").split(/\s+/).map(Number);
  const set = () => svg.setAttribute("viewBox", vb.join(" "));
  svg.addEventListener("wheel", e => {
    e.preventDefault();
    const r = svg.getBoundingClientRect();
    const s = Math.max(r.width / vb[2], r.height / vb[3]);
    const k = e.deltaY > 0 ? 1.2 : 1 / 1.2;
    const mx = vb[0] + (e.clientX - r.left - (r.width - vb[2] * Math.min(r.width / vb[2], r.height / vb[3])) / 2) / Math.min(r.width / vb[2], r.height / vb[3]);
    const my = vb[1] + (e.clientY - r.top - (r.height - vb[3] * Math.min(r.width / vb[2], r.height / vb[3])) / 2) / Math.min(r.width / vb[2], r.height / vb[3]);
    vb = [mx - (mx - vb[0]) * k, my - (my - vb[1]) * k, vb[2] * k, vb[3] * k]; set();
  }, { passive: false });
  let drag = null, moved = false;
  svg.addEventListener("mousedown", e => { drag = [e.clientX, e.clientY, vb[0], vb[1]]; moved = false; });
  window.onmousemove = e => {
    if (!drag) return;
    const r = svg.getBoundingClientRect(); const s = Math.min(r.width / vb[2], r.height / vb[3]);
    const dx = e.clientX - drag[0], dy = e.clientY - drag[1];
    if (Math.abs(dx) + Math.abs(dy) > 4) { moved = true; svg.classList.add("dragging"); }
    vb[0] = drag[2] - dx / s; vb[1] = drag[3] - dy / s; set();
  };
  window.onmouseup = () => { drag = null; svg.classList.remove("dragging"); };
  svg.addEventListener("click", e => { if (moved) { e.stopPropagation(); e.preventDefault(); moved = false; } }, true);
  // Touch: one finger pans, two fingers pinch to zoom. A tap still clicks.
  let t0 = null;
  const toMap = (cx, cy) => {
    const r = svg.getBoundingClientRect(), s = Math.min(r.width / vb[2], r.height / vb[3]);
    return [vb[0] + (cx - r.left - (r.width - vb[2] * s) / 2) / s, vb[1] + (cy - r.top - (r.height - vb[3] * s) / 2) / s, s];
  };
  const snap = (ts) => {
    if (ts.length === 1) return { n: 1, x: ts[0].clientX, y: ts[0].clientY, vb: vb.slice() };
    const x = (ts[0].clientX + ts[1].clientX) / 2, y = (ts[0].clientY + ts[1].clientY) / 2;
    return { n: 2, x, y, d: Math.hypot(ts[0].clientX - ts[1].clientX, ts[0].clientY - ts[1].clientY), vb: vb.slice(), m: toMap(x, y) };
  };
  svg.addEventListener("touchstart", e => { t0 = snap(e.touches); moved = false; }, { passive: true });
  svg.addEventListener("touchmove", e => {
    if (!t0) return;
    e.preventDefault();
    const ts = e.touches;
    if (ts.length !== t0.n) { t0 = snap(ts); return; }
    const r = svg.getBoundingClientRect();
    if (t0.n === 1) {
      const s = Math.min(r.width / t0.vb[2], r.height / t0.vb[3]);
      const dx = ts[0].clientX - t0.x, dy = ts[0].clientY - t0.y;
      if (Math.abs(dx) + Math.abs(dy) > 6) moved = true;
      vb = [t0.vb[0] - dx / s, t0.vb[1] - dy / s, t0.vb[2], t0.vb[3]];
    } else {
      const d = Math.hypot(ts[0].clientX - ts[1].clientX, ts[0].clientY - ts[1].clientY) || 1;
      const k = t0.d / d, [mx, my] = t0.m;
      vb = [mx - (mx - t0.vb[0]) * k, my - (my - t0.vb[1]) * k, t0.vb[2] * k, t0.vb[3] * k];
      moved = true;
    }
    set();
  }, { passive: false });
  svg.addEventListener("touchend", e => { t0 = e.touches.length ? snap(e.touches) : null; }, { passive: true });
}
function fitMap() { const s = document.getElementById("map"); if (s) s.setAttribute("viewBox", s.dataset.vb.split(",").join(" ")); }
window.fitMap = fitMap;
function go(h) { location.hash = h; }
window.go = go;

// ------------------------------------------------------------------ explore
function crumbs(parts) {
  return `<div class="crumbs">` + parts.map((p, i) => i === parts.length - 1 ? `<b>${esc(p[0])}</b>` : `<a href="${p[1]}">${esc(p[0])}</a><span class="sep">›</span>`).join("") + `</div>`;
}
function explore(kind, a, b) {
  let html;
  if (kind === "deck") html = deckView(+a);
  else if (kind === "district") html = districtView(a);
  else if (kind === "precinct") html = precinctView(a);
  else if (kind === "block") html = blockView(a, b);
  else if (kind === "building") html = buildingView(a);
  else if (kind === "street") html = streetView(a, +b);
  else if (kind === "crown") html = crownView();
  else html = shipView();
  document.getElementById("app").innerHTML = html;
  bindMap();
}
function layout(cr, map, panel) {
  return crumbs(cr) + `<div class="explore"><div>${map}</div><div class="panel">${panel}</div></div>`;
}
const deckCrumb = d => [`Deck ${d.n} · ${d.name}`, `#/deck/${d.n}`];

// ---- ship
function shipView() {
  const s = D.model.ship, ex = 2.5;
  const side = s.hull_side || [];
  const SY = z => -z * 1000 * ex;
  let g = `<path d="M${side.map(p => `${X(p[0])},${SY(p[1])}`).join("L")}Z" fill="#0f3a6b" stroke="#cfe3f7" stroke-width="20"/>`;
  for (const d of D.model.decks) {
    if (d.floor_m == null || !d.outline_gross) continue;
    const xs = d.outline_gross.map(p => p[0]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const planned = d.districts.some(x => x.precinct_set);
    g += `<g class="hit" onclick="go('#/deck/${d.n}')"><rect x="${X(x1)}" y="${SY(d.ceiling_m / 1000)}" width="${(x1 - x0) * 1000}" height="${(d.ceiling_m - d.floor_m) * ex}" fill="${planned ? "#2273b8" : "#1b5c9c"}" stroke="#cfe3f7" stroke-width="12"/>
      <text x="${X((x0 + x1) / 2)}" y="${SY((d.floor_m + d.ceiling_m) / 2000)}" font-size="${Math.min(520, (d.ceiling_m - d.floor_m) * ex * 0.55)}" fill="#fff" text-anchor="middle" dominant-baseline="middle" font-weight="700">${d.n} · ${esc(d.name.toUpperCase())}</text></g>`;
  }
  // top plan underneath
  const plan = s.hull_plan || [];
  const off = 8200;
  g += `<g transform="translate(0,${off})"><path d="${pathOf(plan)}" fill="#0f3a6b" stroke="#cfe3f7" stroke-width="20"/>${D.model.decks.map(d => d.outline_net ? `<path class="hit" onclick="go('#/deck/${d.n}')" d="${pathOf(d.outline_net)}" fill="none" stroke="#6fd0ff" stroke-opacity=".35" stroke-width="18"/>` : "").join("")}
    <text x="${X(17)}" y="${Y(-7.2)}" font-size="520" fill="#7fb0de" text-anchor="middle">TOP VIEW · hull plan with the 8 deck outlines</text></g>`;
  g += `<text x="${X(17)}" y="${SY(4.1) - 700}" font-size="520" fill="#7fb0de" text-anchor="middle">SIDE VIEW · vertical scale ×${ex} · click a deck</text>`;
  const vb = [-1000, SY(4.1) - 1500, 36000, 4100 * ex + 1500 + off + 7000];
  const dims = (s.dimensions || []).slice(0, 10).map(r => `<div>${esc(r.item)}</div><div>${usText(r.value)}</div>`).join("");
  const decks = D.model.decks.map(d => `<li onclick="go('#/deck/${d.n}')"><span><b>${d.n} ${esc(d.name)}</b> <span class="muted small">${esc(d.role)}</span></span><span class="small">${area(d.net_area_calc)}</span></li>`).join("");
  const panel = `<h1>${esc(s.name)}</h1><div class="small muted">${esc((s.meta || {}).title || "")} · ${fileLink(s.sheet, "Sheet S0")}</div>
    <h3>Key dimensions (canon)</h3><div class="kv">${dims}</div>
    <h3>Deck cities</h3><ul class="list">${decks}<li onclick="go('#/crown')"><span><b>Crown Bridge</b> <span class="muted small">detachable command ship</span></span><span class="small">14 levels</span></li></ul>
    <h3>Structure</h3><div class="kv">${(s.structure || []).map(r => `<div>${esc(r.item)}</div><div>${esc(r.value)}</div>`).join("")}</div>
    ${issueBlock("ship", "Ship-level issues")}`;
  return layout([["Invicta", "#/ship"]], mapShell(g, vb, "", "", "Click a deck · scroll to zoom"), panel);
}

// ---- crown bridge
function crownView() {
  const c = D.model.crown;
  const levels = (c.levels || []).map(l => `<tr><td>${esc(l.level)}</td><td><b>${esc(l.name)}</b><div class="small muted">${esc(l.function)}</div></td><td>${usText(l.footprint)}</td><td>${esc(l.area)}</td><td>${esc(l.height)}</td></tr>`).join("");
  return crumbs([["Invicta", "#/ship"], ["Crown Bridge", ""]]) + `<div class="card"><h1>Crown Bridge</h1><div class="small muted">${fileLink(c.sheet, "Crown Bridge data sheet")} · canon</div>
    <div class="kv" style="margin-top:10px">${Object.entries(c.key || {}).map(([k, v]) => `<div>${esc(k)}</div><div>${usText(v)}</div>`).join("")}</div>
    <h3>Levels</h3><table><tr><th>Level</th><th>Name</th><th>Footprint</th><th>Area</th><th>Height</th></tr>${levels}</table>
    <div class="note" style="margin-top:10px">The Crown Bridge has levels but no plan drawings yet. Room layouts are not designed yet.</div></div>`;
}

// ---- deck
function districtFill(x) {
  if (x.is_plaza) return "#4a3513";
  if (x.precinct_set) return "#2273b8";
  return "url(#hatch)";
}
function deckView(n) {
  const d = IX.decks[n];
  if (!d) return `<div class="note">No Deck ${n}.</div>`;
  const out = d.outline_net || [];
  const b = out.length ? bboxOf(out) : [0, 34, -6.5, 6.5];
  const vb = vbFor([b[0], b[1], -6.6, 6.6], 0.9);
  const fs = vb[2] / 75;
  let g = `<path d="${pathOf(d.outline_gross || out)}" fill="#0b2a4a" stroke="#cfe3f7" stroke-width="${fs / 8}" stroke-dasharray="${fs / 2} ${fs / 3}"/>`;
  g += `<path d="${pathOf(out)}" fill="#0f3a6b" stroke="#fff" stroke-width="${fs / 5}"/>`;
  g += frameGrid([b[0], b[1], -6.4, 6.4], 4, fs, true);
  for (const x of d.districts) {
    if (x.is_plaza || !x.polygon_km) continue;
    g += `<path class="hit" onclick="go('#/district/${x.id}')" d="${pathOf(x.polygon_km)}" fill="${districtFill(x)}" stroke="#cfe3f7" stroke-width="${fs / 6}"><title>${esc(x.name)} · ${esc(x.design_status)}</title></path>`;
  }
  const pl = d.districts.find(x => x.is_plaza);
  if (pl && pl.circle_km) {
    const [cx, cy, r] = pl.circle_km;
    g += `<circle class="hit" onclick="go('#/district/${pl.id}')" cx="${X(cx)}" cy="${Y(cy)}" r="${r * 1000}" fill="#0a2343" stroke="#ffc266" stroke-width="${fs / 6}" stroke-dasharray="${fs / 2} ${fs / 3}"><title>${esc(pl.name)}</title></circle>
      <circle cx="${X(cx)}" cy="${Y(cy)}" r="800" fill="#06182f" stroke="#6fd0ff" stroke-width="${fs / 6}"/>`;
  }
  // Keelway and stops
  const stops = (d.keelway || []).map(s => parseInt(String(s.frame).replace(/\D/g, ""), 10)).filter(v => !isNaN(v));
  if (stops.length) {
    g += `<line x1="${X(Math.min(...stops) * 0.5)}" y1="0" x2="${X(Math.max(...stops) * 0.5)}" y2="0" stroke="#6fd0ff" stroke-width="${fs / 3}"/>`;
    for (const s of d.keelway) {
      const f = parseInt(String(s.frame).replace(/\D/g, ""), 10);
      g += `<circle cx="${X(f * 0.5)}" cy="0" r="${fs / 2}" fill="#0a2343" stroke="#6fd0ff" stroke-width="${fs / 6}"><title>Keelway: ${esc(s.stop)} (${esc(s.address)})</title></circle>`;
    }
  }
  for (const s of d.crossline || []) {
    const f = parseInt(String(s.frame).replace(/\D/g, ""), 10), off = parseFloat(s.offset);
    if (!isNaN(off) && off !== 0) g += `<line x1="${X(f * 0.5)}" y1="0" x2="${X(f * 0.5)}" y2="${Y(off)}" stroke="#6fd0ff" stroke-width="${fs / 6}" stroke-dasharray="${fs / 2} ${fs / 3}"/><circle cx="${X(f * 0.5)}" cy="${Y(off)}" r="${fs / 2}" fill="#0a2343" stroke="#6fd0ff" stroke-width="${fs / 6}"><title>Cross-line: ${esc(s.stop)}</title></circle>`;
  }
  for (const x of d.districts) {
    if (x.is_plaza && x.circle_km) { g += label(x.circle_km[0], x.circle_km[1] - x.circle_km[2] - 0.35, x.name.toUpperCase(), fs * 0.8, { fill: "#ffc266" }); continue; }
    if (!x.polygon_km) continue;
    const bb = bboxOf(x.polygon_km);
    let cx = (bb[0] + bb[1]) / 2, cy = (bb[2] + bb[3]) / 2;
    if (x.is_plaza) continue;
    if (Math.abs(cy) < 0.6 && bb[2] < -1 && bb[3] > 1) cy = bb[2] / 2;   // keep labels off the Keelway
    const flat = fitText(x.name.toUpperCase(), bb[1] - bb[0], bb[3] - bb[2], fs);
    const tall = flat ? 0 : fitText(x.name.toUpperCase(), bb[3] - bb[2], bb[1] - bb[0], fs);
    const sub = x.precinct_set ? "precinct plan" : "not designed yet", subFill = x.precinct_set ? "#6fd0ff" : "#8fa3b8";
    if (flat || !tall) {
      const s = flat || fs * 0.5;
      g += label(cx, cy, x.name.toUpperCase(), s, {});
      g += label(cx, cy + s * 0.0013, sub, s * 0.7, { fill: subFill, weight: 400 });
    } else {
      g += `<g transform="rotate(-90 ${X(cx)} ${Y(cy)})">${label(cx, cy, x.name.toUpperCase(), tall, {})}</g>`;
    }
  }
  const legend = `<span><i style="background:#2273b8"></i>has a precinct plan</span><span><i style="background:#2b4563"></i>not designed yet</span><span><i style="background:#4a3513;border-color:#ffc266"></i>central plaza (canon)</span><span><b style="color:#6fd0ff">━</b> Keelway and stops</span>`;
  const k = d.key || {};
  const keyRows = ["Gross outline", "Net floor area", "Floor / ceiling elevation", "Clear height", "Floor-to-floor stack height", "Design population", "Frames", "Atrium", "Governor", "Deck Chief"]
    .filter(r => k[r]).map(r => `<div>${esc(r)}</div><div>${usText(k[r])}</div>`).join("");
  const dl = d.districts.map(x => `<li onclick="go('#/district/${x.id}')"><span><b>${esc(x.name)}</b> ${x.is_plaza ? '<span class="small muted">plaza</span>' : ""}<br><span class="small muted">${esc(x.what)}</span></span><span class="small" style="text-align:right">${area(x.revB ? x.revB.area_km2 : x.area_km2)}<br>${badge(x.design_status)}</span></li>`).join("");
  const stopsT = (d.keelway || []).map(s => `<div>${esc(s.stop)}</div><div>${esc(s.frame)} · ${esc(s.address)} · ${usText(s.from_bow)} from deck bow</div>`).join("");
  const panel = `<h1>${esc(d.title || ("Deck " + n))}</h1><div class="small muted">${esc(d.role)} · landmark: ${esc(d.landmark)}</div>
    <p class="small">${esc(d.summary || "")}</p>
    <div class="small">${fileLink(d.paths.sheet, `Sheet S${n}`)} ${d.has_sheet_pdf ? "· " + fileLink(d.paths.sheet_pdf, "PDF") : ""} ${d.has_render ? "· " + fileLink(d.paths.render, "render") : ""} · outline: ${fileLink(d.outline_source, d.outline_source.endsWith("_revB.csv") ? "Rev B" : "canon")}</div>
    <h3>Key data</h3><div class="kv">${keyRows}<div>Net floor (outline)</div><div>${area(d.net_area_calc)}</div></div>
    <h3>Districts (${d.districts.length})</h3><ul class="list">${dl}</ul>
    <h3>Keelway</h3><div class="kv">${stopsT || "<div class='muted'>none listed</div>"}</div>
    <h3>Systems (peacetime)</h3><div class="kv">${(d.systems || []).map(s => `<div>${esc(s.load)}</div><div>${esc(s.draw)}</div>`).join("")}</div>
    <h3>Drones</h3><div class="small">${esc(d.drones)}</div>
    ${issueBlock("D" + n, "Issues on this deck")}`;
  return layout([["Invicta", "#/ship"], deckCrumb(d)], mapShell(g, vb, "", legend, "Click a district · scroll to zoom"), panel);
}

// ---- district
function districtView(id) {
  const x = IX.districts[id];
  if (!x) return `<div class="note">Unknown district ${esc(id)}.</div>`;
  const d = IX.decks[x.deck];
  const ps = IX.psets[id];
  const shape = x.polygon_km || (x.circle_km ? circlePts(x.circle_km) : null);
  const b = shape ? bboxOf(shape) : bboxOf(d.outline_net);
  const vb = vbFor(b, Math.max(b[1] - b[0], b[3] - b[2]) * 0.1);
  const fs = vb[2] / 60;
  let g = `<path d="${pathOf(d.outline_net)}" fill="#0b2140" stroke="#cfe3f7" stroke-width="${fs / 6}"/>`;
  for (const o of d.districts) if (o.polygon_km && o.id !== id) g += `<path class="hit" onclick="go('#/district/${o.id}')" d="${pathOf(o.polygon_km)}" fill="#0f2a48" stroke="#2b4f78" stroke-width="${fs / 8}"><title>${esc(o.name)}</title></path>`;
  g += frameGrid([b[0] - 0.5, b[1] + 0.5, b[2] - 0.3, b[3] + 0.3], 1, fs * 0.8, true);
  if (shape) g += `<path d="${pathOf(shape)}" fill="${ps ? "#123d63" : "url(#hatch)"}" stroke="#fff" stroke-width="${fs / 4}"/>`;
  if (ps) {
    for (const p of ps.precincts) {
      const pb = bboxOf(p.shape_km);
      g += `<path class="hit" onclick="go('#/precinct/${p.uid}')" d="${pathOf(p.shape_km)}" fill="${p.status === "canon" ? "#2a6a4a" : "#1f5f99"}" fill-opacity=".85" stroke="#e8f1fb" stroke-width="${fs / 6}"><title>${p.id} ${esc(p.name)}</title></path>`;
      for (const c of p.exclude_circles_km || []) g += `<circle cx="${X(c[0])}" cy="${Y(c[1])}" r="${c[2] * 1000}" fill="#0a2343" stroke="#ffc266" stroke-width="${fs / 6}" stroke-dasharray="${fs / 2} ${fs / 3}"/>`;
      const s = fitText(`${p.id} ${p.name.toUpperCase()}`, pb[1] - pb[0], pb[3] - pb[2], fs) || fitText(p.id, pb[1] - pb[0], pb[3] - pb[2], fs);
      if (s) g += label((pb[0] + pb[1]) / 2, (pb[2] + pb[3]) / 2, s < fs * 0.6 ? p.id : `${p.id} ${p.name.toUpperCase()}`, s, {});
    }
  } else if (shape) {
    const s = fitText("NOT DESIGNED YET", b[1] - b[0], b[3] - b[2], fs);
    g += label((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, "NOT DESIGNED YET", s || fs * 0.6, { fill: "#9fb4c9" });
  }
  if (x.circle_km) g += `<circle cx="${X(x.circle_km[0])}" cy="${Y(x.circle_km[1])}" r="800" fill="#06182f" stroke="#6fd0ff" stroke-width="${fs / 6}"/>` + label(x.circle_km[0], x.circle_km[1], "SPINE ATRIUM", fs * 0.7, { fill: "#6fd0ff" });
  const cur = x.revB ? x.revB.area_km2 : x.area_km2;
  let body = `<div class="kv">
    <div>Status</div><div>${badge(x.design_status)}</div>
    <div>Area</div><div>${area(cur)}${x.revB ? `<div class="small muted">Rev B. Sheet S${d.n} says ${area(x.area_km2)}; ${esc(x.revB.source)}</div>` : ""}</div>
    <div>Shape on plan</div><div>${area(x.area_calc)}${x.plan_note ? `<div class="small sev-warning">${esc(x.plan_note)}</div>` : ""}</div>
    <div>Share of deck</div><div>${esc(x.share)}</div>
    <div>People</div><div>${x.people == null ? "—" : n0(x.people)} <span class="muted small">(${x.per_km2 == null ? "" : n0(x.per_km2) + " per km²"}, capacity)</span></div>
    <div>What is there</div><div>${esc(x.what)}</div>
    <div>Centre address</div><div>${esc(x.centre)}</div>
    <div>Who works here</div><div>${esc(x.workers)}</div></div>`;
  if (ps) {
    body += `<h3>Precincts (${ps.precincts.length}) ${badge(ps.status)}</h3><div class="small muted">${esc(ps.note || "")} ${fileLink(ps.doc, "design doc")} ${ps.overview_blueprint ? "· " + fileLink(ps.overview_blueprint, "blueprint") : ""}</div>
      <ul class="list">${ps.precincts.map(p => `<li onclick="go('#/precinct/${p.uid}')"><span><b>${p.id} ${esc(p.name)}</b><br><span class="small muted">${esc(p.role)}</span></span><span class="small" style="text-align:right">${esc(p.frames)} · ${esc(p.lanes)}<br>${area(p.area_km2_stated)}</span></li>`).join("")}</ul>`;
  } else if (x.is_plaza) {
    body += `<div class="note" style="margin-top:10px">Central plaza around the Spine Atrium (canon). Its buildings are named on the sheet (${esc(x.what)}) but have no plan yet: not designed yet.</div>`;
  } else {
    body += `<div class="note" style="margin-top:10px">Not designed yet. Canon gives this district's area, role, centre and workforce (above) and its shape on Sheet S${d.n}. It has no precincts, blocks or buildings yet. The app will show them once a precinct plan exists in <code>Invicta/data</code>.</div>`;
  }
  const panel = `<h1>${esc(x.name)}</h1><div class="small muted">Deck ${d.n} · ${esc(d.name)} · ${fileLink(d.paths.sheet, "Sheet S" + d.n)}</div>${body}${issueBlock(id, "Issues in this district")}`;
  return layout([["Invicta", "#/ship"], deckCrumb(d), [x.name, ""]], mapShell(g, vb, "", ps ? "Click a precinct" : "", ""), panel);
}
function circlePts(c) { const out = []; for (let i = 0; i < 48; i++) { const a = i / 48 * 2 * Math.PI; out.push([c[0] + c[2] * Math.cos(a), c[1] + c[2] * Math.sin(a)]); } return out; }

// ---- precinct drawing shared by precinct, block and building views
function drawPrecinct(p, fs, opts) {
  opts = opts || {};
  const d = IX.decks[p.deck];
  let g = `<path d="${pathOf(d.outline_net)}" fill="#0b2140" stroke="#cfe3f7" stroke-width="${fs / 5}"/>`;
  g += `<path d="${pathOf(p.shape_km)}" fill="#123d63" stroke="#fff" stroke-width="${fs / 4}"/>`;
  for (const c of p.exclude_circles_km || []) g += `<circle cx="${X(c[0])}" cy="${Y(c[1])}" r="${c[2] * 1000}" fill="#0a2343" stroke="#ffc266" stroke-width="${fs / 5}" stroke-dasharray="${fs / 2} ${fs / 3}"/>`;
  (p.streets || []).forEach((st, i) => {
    const sel = opts.selectedStreet === i;
    g += `<g class="hit" onclick="go('#/street/${p.uid}/${i}')"><title>${esc(st.name)} · click for details</title>` +
      rectEl(st.rect_km, `fill="${/keelway/i.test(st.name) ? "#0f2f4f" : /boulevard|promenade/i.test(st.name) ? "#4a3f2a" : "#2c3440"}"${sel ? ` stroke="#ffc266" stroke-width="${fs / 3}"` : ""}`) + "</g>";
  });
  // blocks sit under the buildings, so both can be clicked
  if (opts.blocks) g += blocksLayer(p, fs, true, opts.blocks.selected);
  // buildings
  for (const b of p.buildings) {
    if (!b.rect_km) continue;
    const fill = KIND_FILL[b.kind] || KIND_FILL.building;
    const stroke = b.status === "canon" ? "#5fd39a" : (b.uid === opts.selected ? "#ffc266" : "#e8f1fb");
    const sw = b.uid === opts.selected ? fs / 2.5 : fs / 9;
    const hit = opts.buildingsClickable ? `class="hit" onclick="go('#/building/${b.uid}')"` : "";
    const shapes = b.bays_km || [b.rect_km];
    g += `<g ${hit}><title>${b.id} ${esc(b.name)}${opts.buildingsClickable ? " · click for details" : ""}</title>` + shapes.map(s => rectEl(s, `fill="${fill}" stroke="${stroke}" stroke-width="${sw}"`)).join("");
    for (const dr of b.doors_km || []) g += rectEl(dr, `fill="#ff8a3d"`);
    g += "</g>";
    if (opts.labels !== false) {
      if (b.bays_km) {
        // each bay gets its own name, or a numbered generic one
        const base = b.bay_label || "Bay";
        const tag = i => base === "Street" ? String.fromCharCode(65 + i) : i + 1;   // Street A, Street B … ; Berth 1, Berth 2 …
        b.bays_km.forEach((s, i) => { g += boxLabel(s, (b.bay_names && b.bay_names[i]) || `${base} ${tag(i)}`, fs * 0.4, { weight: 400 }); });
        const r = b.rect_km, wide = (r[1] - r[0]) >= (r[3] - r[2]);
        if (b.bays_km.length > 3 && !b.bay_names) g += wide ? label((r[0] + r[1]) / 2, r[2] - fs * 0.0006, b.name.toUpperCase(), fs * 0.5, { fill: "#cfe3f7" })
                  : labelR(r[0] - fs * 0.0006, (r[2] + r[3]) / 2, b.name.toUpperCase(), fs * 0.5, { fill: "#cfe3f7" });
      } else g += boxLabel(b.rect_km, b.name.toUpperCase(), fs * 0.75, {});
    }
  }
  if (opts.labels !== false) for (const st of p.streets || []) {
    const r = st.rect_km, w = r[1] - r[0], h = r[3] - r[2];
    g += boxLabel(r, st.name, fs * 0.55, { fill: "#cfd8e3", weight: 400 });
  }
  return g;
}
function blocksLayer(p, fs, clickable, selected) {
  let g = "";
  for (const blk of p.blocks || []) {
    const sel = blk.id === selected;
    g += `<path ${clickable ? `class="hit" onclick="go('#/block/${p.uid}/${blk.id}')"` : ""} d="${pathOf(blk.part_km)}" fill="${sel ? "rgba(255,194,102,.18)" : clickable ? "rgba(111,208,255,.04)" : "none"}" stroke="${sel ? "#ffc266" : "#6fd0ff"}" stroke-opacity="${sel ? 1 : .45}" stroke-width="${sel ? fs / 3 : fs / 10}"><title>${blk.name} (${blk.id}) · ${blk.contents.length} item(s)</title></path>`;
    const c = blk.cell_km;
    g += `<text x="${(X(c[0]) - fs * 0.25).toFixed(1)}" y="${(Y(c[2]) + fs * 0.45).toFixed(1)}" font-size="${(fs * 0.4).toFixed(1)}" fill="#6fd0ff" fill-opacity=".8" text-anchor="end" font-weight="600" pointer-events="none">${esc(blk.name)}</text>`;
  }
  return g;
}

// ---- precinct
function precinctView(uid) {
  const p = IX.precincts[uid];
  if (!p) return `<div class="note">Unknown precinct ${esc(uid)}.</div>`;
  const x = IX.districts[p.district_id], d = IX.decks[p.deck], ps = IX.psets[p.district_id];
  const b = p.bbox_km;
  const vb = vbFor(b, Math.max(b[1] - b[0], b[3] - b[2]) * 0.07);
  const fs = vb[2] / 55;
  let g = frameGrid([b[0], b[1], b[2], b[3]], 1, fs * 0.8, true);
  g += drawPrecinct(p, fs, { buildingsClickable: precinctMode === "buildings" });
  g += blocksLayer(p, fs, precinctMode === "blocks");
  const tools = `<button class="${precinctMode === "blocks" ? "on" : ""}" onclick="setMode('blocks')">Select blocks</button><button class="${precinctMode === "buildings" ? "on" : ""}" onclick="setMode('buildings')">Select buildings</button>`;
  const legend = Object.entries(KIND_FILL).map(([k, c]) => `<span><i style="background:${c}"></i>${k}</span>`).join("") + `<span><i style="background:none;border-color:#5fd39a"></i>canon (green outline)</span><span><i style="background:#ff8a3d;border:0"></i>dock door</span><span><i style="background:none;border-color:#6fd0ff"></i>block</span>`;
  const groups = {};
  for (const bd of p.buildings) (groups[bd.kind] = groups[bd.kind] || []).push(bd);
  const bl = Object.entries(groups).map(([k, list]) => `<h3>${esc(k)} (${list.length})</h3><ul class="list">` + list.map(bd =>
    `<li onclick="go('#/building/${bd.uid}')"><span>${bd.id} <b>${esc(bd.name)}</b>${bd.bay_count ? ` <span class="small muted">× ${bd.bay_count}</span>` : ""}</span><span class="small">${bd.size_m ? dims(bd.size_m[0], bd.size_m[1]) : ""} ${badge(bd.status)}</span></li>`).join("") + "</ul>").join("");
  const used = (p.blocks || []).filter(k => k.contents.length).length;
  const panel = `<h1>${p.id} · ${esc(p.name)}</h1><div class="small muted">${esc(x.name)} · Deck ${d.n} ${esc(d.name)} · ${badge(p.status)}</div>
    <p class="small">${esc(p.intro || p.role)}</p>
    <div class="kv"><div>Frames</div><div>${esc(p.frames)}</div><div>Lanes</div><div>${esc(p.lanes)}${p.lanes_note ? ` <span class="small muted">(${esc(p.lanes_note)})</span>` : ""}</div>
    <div>Area (stated)</div><div>${area(p.area_km2_stated)}</div><div>Area (measured)</div><div>${area(p.area_calc)} <span class="small muted">clipped to the Rev B deck outline</span></div>
    <div>Size</div><div>${len((b[1] - b[0]) * 1000)} × ${len((b[3] - b[2]) * 1000)}</div>
    <div>Blocks</div><div>${(p.blocks || []).length} (${used} with something in them)</div>
    <div>Build order</div><div>${p.build_order || "—"}</div>
    <div>Sources</div><div>${fileLink(ps.doc, "precinct plans doc")} · ${fileLink(p.blueprint, "blueprint PNG")} · ${fileLink(p.blueprint_svg, "SVG")} · ${fileLink(ps.file, "app data")}</div></div>
    ${bl}${issueBlock(uid, "Issues in this precinct")}`;
  return layout([["Invicta", "#/ship"], deckCrumb(d), [x.name, `#/district/${x.id}`], [`${p.id} ${p.name}`, ""]],
    mapShell(g, vb, tools, legend, precinctMode === "blocks" ? "Click a block (blocks are bounded by streets and never cut through a building) · or switch to Select buildings" : "Click a building"), panel);
}
window.setMode = m => { precinctMode = m; route(); };

// ---- block
function blockView(puid, bid) {
  const p = IX.precincts[puid];
  const blk = p && (p.blocks || []).find(k => k.id === bid);
  if (!blk) return `<div class="note">Unknown block ${esc(bid)}.</div>`;
  const x = IX.districts[p.district_id], d = IX.decks[p.deck];
  const c = blk.cell_km;
  const vb = vbFor(c, 0.12);
  const fs = vb[2] / 40;
  let g = drawPrecinct(p, fs, { buildingsClickable: true, labels: true, blocks: { selected: bid } });
  // dim everything outside this block
  const outer = `M${vb[0] - 4 * vb[2]},${vb[1] - 4 * vb[3]}h${9 * vb[2]}v${9 * vb[3]}h${-9 * vb[2]}Z`;
  g += `<path d="${outer} ${pathOf(blk.part_km)}" fill="rgba(5,12,22,.55)" fill-rule="evenodd" pointer-events="none"/>`;
  // bow right: the lower frame number is on the right
  g += label(c[0], c[2] - 0.04, `${nd(c[0], 2)} km`, fs * 0.6, { fill: "#ffc266" }) + label(c[1], c[2] - 0.04, `${nd(c[1], 2)} km`, fs * 0.6, { fill: "#ffc266" });
  g += label(c[1] + 0.03, (c[2] + c[3]) / 2, blk.lane === blk.lane_end ? `lane ${blk.lane}` : `lanes ${blk.lane}–${blk.lane_end}`, fs * 0.6, { fill: "#ffc266", anchor: "end" });
  const items = blk.contents.map(ct => {
    const bd = p.buildings.find(q => q.id === ct.id);
    return `<li onclick="go('#/building/${bd.uid}')"><span>${bd.id} <b>${esc(bd.name)}</b> <span class="small muted">${esc(bd.kind)}</span></span><span class="small">${ct.of ? (ct.parts < ct.of ? `${ct.parts} of ${ct.of} ${esc((bd.bay_label || "bay").toLowerCase())}s here ` : "") : ct.share < 0.995 ? Math.round(ct.share * 100) + "% of it here " : ""}${badge(bd.status)}</span></li>`;
  }).join("");
  const streets = (p.streets || []).filter(s => (s.blocks || []).includes(bid)).map(s => esc(s.name)).join(", ");
  const panel = `<h1>${esc(blk.name)} <span class="muted small">${esc(blk.id)}</span></h1><div class="small muted">${p.id} ${esc(p.name)} · ${esc(x.name)} · Deck ${d.n}</div>
    <div class="kv" style="margin-top:8px"><div>Size</div><div>${dims((c[1] - c[0]) * 1000, (c[3] - c[2]) * 1000)}</div>
    <div>Frames</div><div>F${blk.frame} to F${blk.frame_end} (${nd(c[0], 2)} to ${nd(c[1], 2)} km from the prow)</div>
    <div>Lanes</div><div>${blk.lane === blk.lane_end ? blk.lane : blk.lane + " to " + blk.lane_end} (${nd(c[2], 2)} to ${nd(c[3], 2)} km ${c[3] <= 0 ? "to port" : c[2] >= 0 ? "to starboard" : "across the centreline"})</div>
    <div>Usable area</div><div>${area(blk.area_km2)}</div>
    <div>Streets</div><div>${streets || "<span class='muted'>none</span>"}</div></div>
    <h3>In this block (${blk.contents.length})</h3>${items ? `<ul class="list">${items}</ul>` : `<div class="note">Nothing placed in this block yet: not designed yet.</div>`}
    <div class="small muted" style="margin-top:8px">Click a building on the map or in the list for its details.</div>`;
  return layout([["Invicta", "#/ship"], deckCrumb(d), [x.name, `#/district/${x.id}`], [`${p.id} ${p.name}`, `#/precinct/${p.uid}`], [`${blk.name} · ${blk.id}`, ""]],
    mapShell(g, vb, "", "", "Click a building"), panel);
}

// ---- building
function fileSrc(rel) {
  return window.ADXI_STATIC ? "file/" + rel.split("/").map(encodeURIComponent).join("/") : "/file?path=" + encodeURIComponent(rel);
}
function conceptBlock(uid, b) {
  const list = ((D.concepts || {}).buildings || {})[uid] || [];
  const add = window.adxiAddConcept ? `<button class="concept-add" onclick="adxiAddConcept('${uid}', '${esc(b.id)} ${esc(b.name).replace(/'/g, "")}')">Add concept art</button>` : "";
  if (!list.length && !add) return "";
  return `<h3>Concept art</h3>
    ${list.map(c => `<figure class="concept"><a href="${fileSrc(c.file)}" target="_blank" rel="noopener"><img src="${fileSrc(c.file)}" alt="${esc(c.title || "Concept art")}" loading="lazy"></a>
      <figcaption><span class="concept-tag">CONCEPT · not canon</span> ${esc(c.title || "")} <span class="small muted">by ${esc(c.by || "a helper")}${c.added ? ", " + esc(c.added) : ""}</span>${window.adxiDeleteConcept ? ` <button class="concept-del" onclick="adxiDeleteConcept('${uid}', '${esc(c.file)}', '${esc(b.id)} ${esc(b.name).replace(/'/g, "")}')">Delete</button>` : ""}</figcaption></figure>`).join("")}
    ${list.length ? "" : `<div class="small muted">No concept art yet.</div>`}${add}`;
}
// Copy helpers for the building panel.
function copyText(t, btn) {
  const done = () => { if (btn) { const o = btn.textContent; btn.textContent = "✓"; setTimeout(() => (btn.textContent = o), 1200); } };
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(t).then(done, () => fallbackCopy(t, done));
  else fallbackCopy(t, done);
}
function fallbackCopy(t, done) {
  const a = document.createElement("textarea"); a.value = t; a.style.position = "fixed"; a.style.opacity = "0";
  document.body.append(a); a.select(); try { document.execCommand("copy"); done(); } catch (e) { /* ignore */ } a.remove();
}
function copyFrom(btn) { copyText(btn.dataset.copy || "", btn); }
function copyBuilding(btn) {
  const panel = btn.closest(".panel") || document;
  const clean = (el) => { const c = el.cloneNode(true); c.querySelectorAll(".cp").forEach((x) => x.remove()); return c.textContent.replace(/\s+/g, " ").trim(); };
  const lines = [clean(panel.querySelector("h1")), clean(panel.querySelector("h1 + div"))];
  panel.querySelectorAll(".kv").forEach((kv, i) => {
    if (i === 1) lines.push("", "Architecture");
    const cells = [...kv.children];
    for (let j = 0; j + 1 < cells.length; j += 2) lines.push(`${clean(cells[j])}: ${clean(cells[j + 1])}`);
  });
  copyText(lines.join(String.fromCharCode(10)), btn);
}
window.copyFrom = copyFrom; window.copyBuilding = copyBuilding;
function streetView(puid, i) {
  const p = IX.precincts[puid];
  const st = p && (p.streets || [])[i];
  if (!st) return `<div class="note">Unknown street.</div>`;
  const x = IX.districts[p.district_id], d = IX.decks[p.deck], r = st.rect_km;
  const vb = vbFor(r, Math.max(0.15, Math.max(r[1] - r[0], r[3] - r[2]) * 0.4));
  const fs = vb[2] / 45;
  const g = drawPrecinct(p, fs, { buildingsClickable: true, selectedStreet: i, blocks: { selected: null } });
  const L = Math.max(r[1] - r[0], r[3] - r[2]) * 1000, Wd = Math.min(r[1] - r[0], r[3] - r[2]) * 1000;
  const panel = `<h1>${esc(st.name)}</h1><div class="small muted">Street · ${p.id} ${esc(p.name)} · ${esc(x.name)} · Deck ${d.n} ${esc(d.name)}</div>
    <div class="kv" style="margin-top:8px">
      <div>Length</div><div>${len(L)}</div>
      <div>Width</div><div>${st.width_m != null ? len(st.width_m) : len(Wd)}</div>
      <div>Area</div><div>${area((r[1] - r[0]) * (r[3] - r[2]))}</div>
      <div>Blocks</div><div>${(st.blocks || []).map(k => `<a href="#/block/${p.uid}/${k}">${esc(k)}</a>`).join(", ") || ND}</div>
      <div>Position</div><div>${nd(r[0], 2)}–${nd(r[1], 2)} km from the prow, ${nd(r[2], 2)} to ${nd(r[3], 2)} km across</div></div>`;
  return layout([["Invicta", "#/ship"], deckCrumb(d), [x.name, `#/district/${x.id}`], [`${p.id} ${p.name}`, `#/precinct/${p.uid}`], [st.name, ""]],
    mapShell(g, vb, "", "", "Click any building, block or street"), panel);
}
function buildingView(uid) {
  const b = IX.buildings[uid];
  if (!b) return `<div class="note">Unknown building ${esc(uid)}.</div>`;
  const p = IX.precincts[b.precinct_uid], x = IX.districts[p.district_id], d = IX.decks[p.deck], ps = IX.psets[p.district_id];
  const r = b.rect_km;
  const vb = r ? vbFor(r, Math.max(0.15, Math.max(r[1] - r[0], r[3] - r[2]) * 0.6)) : vbFor(p.bbox_km);
  const fs = vb[2] / 45;
  let g = drawPrecinct(p, fs, { buildingsClickable: true, selected: uid, blocks: { selected: null } });
  g += blocksLayer(p, fs, false);
  const w = r ? (r[1] - r[0]) * 1000 : null, h = r ? (r[3] - r[2]) * 1000 : null;
  const sz = b.size_m;
  const arch = [["Height", b.height_m != null ? len(b.height_m) : null], ["Floors", b.floors], ["Structure", b.structure], ["Entrances", b.entrances],
    ["Materials / look", b.look], ["Capacity", b.capacity], ["Services", b.services], ["Interior layout", b.interior]]
    .map(([k, v]) => {
      if (v == null || v === "") return `<div>${k}</div><div>${ND}</div>`;
      const t = String(v), long = t.length > 80;
      return `<div>${k}</div><div class="kvv"><span class="${long ? "clamp" : ""}" ${long ? `onclick="this.classList.toggle('open')" title="Tap to expand"` : ""}>${esc(t)}</span><button class="cp" title="Copy" data-copy="${esc(k + ": " + t)}" onclick="copyFrom(this)">⧉</button></div>`;
    }).join("");
  const blocks = (b.blocks || []).map(k => { const bk = (p.blocks || []).find(q => q.id === k); return `<a href="#/block/${p.uid}/${k}">${esc(bk ? bk.name : "")} · ${k}</a>`; }).join(", ");
  const firstBlock = (b.blocks || [])[0];
  const panel = `<h1>${esc(b.name)} <button class="cp cp-all" title="Copy all building information" onclick="copyBuilding(this)">⧉</button></h1><div class="small muted">${b.id} · ${p.id} ${esc(p.name)} · ${esc(x.name)} · Deck ${d.n} ${esc(d.name)}</div>
    <div style="margin:8px 0">${badge(b.status)} <span class="badge" style="color:#cfd8e3">${esc(b.kind)}</span></div>
    <div class="kv">
      <div>Address</div><div>${esc(b.address || "—")} <span class="small muted">(centre)</span></div>
      <div>Footprint</div><div>${sz ? dims(sz[0], sz[1]) : r ? dims(w, h) : ND}${b.bay_count ? ` <span class="small muted">each, × ${b.bay_count}</span>` : ""}</div>
      ${r && sz && !b.bays_km && (Math.abs(w - sz[0]) > 15 && Math.abs(w - sz[1]) > 15) ? `<div>Drawn</div><div class="sev-warning">${dims(w, h)}</div>` : ""}
      <div>Ground area</div><div>${b.footprint_km2 != null ? area(b.footprint_km2) : ND}</div>
      <div>Listed as</div><div>${esc(b.size_text || "")}</div>
      <div>Notes</div><div>${esc(b.notes || "") || "<span class='muted'>—</span>"}</div>
      <div>${(b.blocks || []).length > 1 ? "Blocks" : "Block"}</div><div>${blocks || ND}</div>
      ${b.bay_names ? `<div>Parts</div><div>${b.bay_names.map(esc).join(", ")}</div>` : ""}
      ${b.doors_km ? `<div>Dock doors</div><div>${b.doors_km.length} in the hull, ${dims((b.doors_km[0][1] - b.doors_km[0][0]) * 1000, (b.doors_km[0][3] - b.doors_km[0][2]) * 1000)} as drawn</div>` : ""}
      <div>Position</div><div>${r ? `${nd(r[0], 2)}–${nd(r[1], 2)} km from the prow, ${nd(r[2], 2)} to ${nd(r[3], 2)} km across` : ND}</div></div>
    <details class="sect" open><summary><h3>Architecture</h3></summary><div class="kv">${arch}</div></details>
    ${conceptBlock(uid, b)}
    <h3>Sources</h3><div class="small">${fileLink(ps.doc, "precinct plans doc")} (${esc(p.id)} table) · ${fileLink(p.blueprint, "blueprint")} · ${fileLink(ps.file, "app data")}</div>
    ${issueBlock(uid, "Issues with this building")}`;
  const cr = [["Invicta", "#/ship"], deckCrumb(d), [x.name, `#/district/${x.id}`], [`${p.id} ${p.name}`, `#/precinct/${p.uid}`]];
  if (firstBlock) cr.push([`Block ${firstBlock}`, `#/block/${p.uid}/${firstBlock}`]);
  cr.push([b.name, ""]);
  return layout(cr, mapShell(g, vb, "", "", "Click another building"), panel);
}

load();
