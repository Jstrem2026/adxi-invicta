/* ADXI: Invicta front end. Plain JavaScript, no libraries.
   Every map is a true top view: bow RIGHT, port UP (matches the Unreal level).
   Ship frame from the data: x km from the prow tip, y km across (port negative). */
"use strict";

const SHIP_L = 34.0;               // km, prow tip to stern
const M_FT = 3.28084, KM2_SQMI = 1 / 2.589988, M2_ACRE = 1 / 4046.8564224;
const LANES = "ABCDEFGHIJKLMNOPQRSTUVWXY";
// Map colour legend (Jordan, 27 Nov 2026): every building is coloured by what it is used for.
// The list comes from the app data (atlaslib/categories.py), so 2D and 3D always agree.
let CAT = {};
const catKey = b => (b && CAT[b.category]) ? b.category : "offices";
const catOf = b => CAT[(b && b.category) || "offices"] || { fill: "#3b5b7f", edge: "#e8f1fb", text: "#e8f1fb", label: "" };
const streetKey = st => /keelway/i.test(st.name) ? "keelway" : /boulevard|promenade/i.test(st.name) ? "parks" : "transit";
const streetCat = st => CAT[/keelway/i.test(st.name) ? "keelway" : /boulevard|promenade/i.test(st.name) ? "parks" : "transit"] || { fill: "#2c3440", text: "#cfd8e3" };
window.adxiCat = b => catOf(b);
window.adxiStreetCat = st => streetCat(st);
function catLegend() {
  return (D.model.categories || []).map(c => legendItem(c.key, c.label, `background:${c.fill};border-color:${c.edge}`)).join("");
}
// One legend entry with a tick box that shows or hides everything of that kind on the map (Jordan, 27 Nov 2026).
function legendItem(key, text, swatch) {
  return `<label class="lg-item"><input type="checkbox" data-lg="${key}" ${hiddenCats().has(key) ? "" : "checked"} onchange="toggleCat(this)"><i style="${swatch}"></i>${esc(text)}</label>`;
}
function hiddenCats() { try { return new Set(JSON.parse(localStorage.getItem("adxi.hide") || "[]")); } catch { return new Set(); } }
function applyHidden() {
  const svg = document.getElementById("map");
  if (svg) svg.setAttribute("data-hide", [...hiddenCats()].join(" "));
}
window.toggleCat = el => {
  const h = hiddenCats();
  el.checked ? h.delete(el.dataset.lg) : h.add(el.dataset.lg);
  try { localStorage.setItem("adxi.hide", JSON.stringify([...h])); } catch {}
  applyHidden();
};
// CSS that hides each kind when its box is unticked
(function () {
  const keys = ["transit", "keelway", "police", "fire", "medical", "homes", "shops", "offices", "industry", "utilities", "parks", "schools", "block", "door"];
  const st = document.createElement("style");
  st.textContent = keys.map(k => `#map[data-hide~="${k}"] [data-cat="${k}"]`).join(",") + "{display:none}";
  document.head.append(st);
})();
// A building's footprint: its shaped outline (curves, L and U shapes, courtyards as holes) when it has one,
// otherwise its box, or one box per bay for a bay row.
// Deck city and Bridge emblems (Jordan, 27 Nov 2026): a small copy in web/emblems, the full size art in Game/Docs/art/emblems.
const staticSrc = rel => (window.ADXI_STATIC ? "static/" : "/static/") + rel;
function emblem(o, size, cls) {
  if (!o || !o.emblem_web) return "";
  const img = `<img class="${cls || "emblem"}" src="${staticSrc(o.emblem_web)}" width="${size}" height="${size}" alt="" loading="lazy">`;
  return o.emblem_art ? `<a href="${fileSrc(o.emblem_art)}" target="_blank" rel="noopener" title="Emblem (full size)">${img}</a>` : img;
}
// the building's purpose under its name in building lists (full text on hover)
const purposeLine = b => b.purpose ? `<span class="purpose-line" title="${esc(b.purpose)}">${esc(b.purpose)}</span>` : "";
function shapeEl(b, attrs) {
  if (b.outline_km && !b.bays_km) {
    const d = b.outline_km.map(pathOf).join("") + (b.holes_km || []).map(pathOf).join("");
    return `<path d="${d}" fill-rule="evenodd" ${attrs || ""}/>`;
  }
  return (b.bays_km || (b.rect_km ? [b.rect_km] : [])).map(r => rectEl(r, attrs)).join("");
}
let D = null;                      // everything from /api/all
let IX = {};                       // lookups
let showKnown = true;
let issueFilter = { sev: "all", q: "" };

// ------------------------------------------------------------------ formatting
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const n0 = v => Math.round(v).toLocaleString("en-US");
const nd = (v, d) => Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
// Units: "us" (feet first, metres in brackets) or "metric" (Australian practice: m, mm for small sizes).
// First visit with no choice saved: pick by where the device is. US devices get feet; everyone else
// (Kylee in Western Australia, for example) gets metric. Signing in or the Units button overrides it.
(function defaultUnits() {
  try {
    if (localStorage.getItem("adxi.units")) return;
    const langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];
    const region = ((/[-_]([A-Za-z]{2})\b/.exec(langs[0] || "") || [])[1] || "").toUpperCase();
    const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || "");
    const usZone = /^America\/|^US\/|^Pacific\/Honolulu$/.test(tz);
    const us = ["US", "LR", "MM"].includes(region) ? (usZone || !tz) : (!region && usZone);
    localStorage.setItem("adxi.units", us ? "us" : "metric");
  } catch (e) { /* storage blocked: keep feet */ }
})();
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
  // How long the scan of every file took when this copy was made (on the publish build for the website), not page load time.
  const took = D.scan_ms >= 10000 ? `${Math.round(D.scan_ms / 1000)} s` : D.scan_ms >= 1000 ? `${(D.scan_ms / 1000).toFixed(1)} s` : `${D.scan_ms} ms`;
  const st = document.getElementById("scan-time");
  st.textContent = `Scanned ${D.model.generated} in ${took}`;
  st.title = "When the design files were last scanned, and how long that scan took. The page itself loads separately.";
  route();
}
function index() {
  IX = { decks: {}, districts: {}, psets: {}, precincts: {}, buildings: {} };
  CAT = Object.fromEntries((D.model.categories || []).map(c => [c.key, c]));
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
function decisionQuestion(i) {
  const t = i.title, d = i.detail || "";
  if (t === "Precinct plan waiting for approval") return { q: `Approve this precinct plan as canon? ${d}`, a: ["Yes, approve it as canon", "Not yet, keep it proposed"] };
  if (t === "Building rests on an assumption") return { q: `Keep this as designed? ${d}`, a: ["Yes, approve it", "Keep it as an assumption for now", "Change it (I'll say how)"] };
  if (t === "Canon errata waiting for a decision") return { q: `${d.split(". Waiting")[0]}. What should happen to the waiting ones?`, a: ["Approve them all", "Go through them one at a time", "Leave them for later"] };
  if (t === "Game sizes still marked TUNE") return { q: `Some game sizes are still placeholders. ${d.slice(0, 160)}${d.length > 160 ? "…" : ""} Keep them?`, a: ["Keep them as they are (mark settled)", "Go through them one at a time", "Leave them for later"] };
  if (/Revision B|Rev B|Revision A/i.test(t + d)) return { q: `Use the Revision B number? ${d}`, a: ["Yes, use Revision B", "No, keep the sheet number"] };
  return { q: d, a: ["Yes", "No", "Explain it first"] };
}
function answerDecision(id, n) {
  const i = D.issues.find(x => x.id === id);
  if (!i || !window.adxiAsk) return;
  const pick = decisionQuestion(i).a[n];
  window.adxiAsk(`Scan item [${i.id}] ${i.title}: ${i.detail}${i.path ? ` (${i.path})` : ""}${String.fromCharCode(10)}My answer: ${pick}. Make the change now.`);
}
function issueHTML(i) {
  if (i.severity === "decision" && !i.known && window.adxiAsk) {
    const dq = decisionQuestion(i);
    return `<div class="issue decision">
    <div class="t"><span class="sev-decision">Question for Jordan</span> · ${esc(i.title)}</div>
    <div class="dq">${esc(dq.q)}</div>
    <div class="issue-act">${dq.a.map((a, n) => `<button onclick="answerDecision('${i.id}', ${n})">${esc(a)}</button>`).join(" ")}</div>
    <div class="meta">${i.path ? fileLink(i.path, i.path) : ""}${i.entity && entityHref(i.entity) ? ` · <a href="${entityHref(i.entity)}">show on map</a>` : ""} · ${i.id}</div></div>`;
  }
  return `<div class="issue ${i.severity}${i.known ? " known" : ""}">
    <div class="t">${i.known ? `<span class="muted">Accepted</span>` : `<span class="sev-${i.severity}">${sevName(i.severity)}</span>`} · ${esc(i.title)}</div>
    <div>${esc(i.detail)}</div>
    ${i.fix ? `<div class="meta">Fix: ${esc(i.fix)}</div>` : ""}
    <div class="meta">${i.path ? fileLink(i.path, i.path) : ""}${i.entity && entityHref(i.entity) ? ` · <a href="${entityHref(i.entity)}">show on map</a>` : ""}${i.known ? ` · known: ${esc(i.known)}` : ""} · ${i.id}</div>
    ${window.adxiAsk && !i.known && i.severity !== "gap" ? `<div class="issue-act"><button onclick="askIssue('${i.id}', false)">${i.severity === "decision" ? "Answer with Claude" : "Fix with Claude"}</button>${D.issues.filter(x => x.title === i.title && !x.known).length > 1 ? ` <button onclick="askIssue('${i.id}', true)">Fix all ${D.issues.filter(x => x.title === i.title && !x.known).length} like this</button>` : ""}</div>` : ""}</div>`;
}
// Hand an issue (or every issue with the same title) to the site chat, which offers the choices and then applies the one picked.
function askIssue(id, all) {
  const i = D.issues.find(x => x.id === id);
  if (!i || !window.adxiAsk) return;
  const group = all ? D.issues.filter(x => x.title === i.title && !x.known) : [i];
  const lines = group.map(x => `- [${x.id}] ${x.title}: ${x.detail}${x.path ? ` (${x.path})` : ""}`).join(String.fromCharCode(10));
  window.adxiAsk(`Help me resolve ${all ? `these ${group.length} scan issues` : "this scan issue"}:${String.fromCharCode(10)}${lines}${String.fromCharCode(10)}Give me the choices as a short numbered list (for example: fix the data, record it as canon errata, or accept it as known with a reason), then do the one I pick.`);
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
  const all = issuesFor(id), list = all.filter(i => !i.known), known = all.filter(i => i.known);
  const order = { error: 0, warning: 1, decision: 2, gap: 3 };
  list.sort((a, b) => order[a.severity] - order[b.severity]);
  const folded = known.length ? `<details class="known-list"><summary>Accepted as known, no action needed (${known.length})</summary>${known.map(issueHTML).join("")}</details>` : "";
  if (!list.length) return `<h3>${title || "Issues here"}</h3><div class="muted small">None open.</div>${folded}`;
  return `<h3>${title || "Issues here"} (${list.length})</h3>` + list.map(issueHTML).join("") + folded;
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
  const counts = s => D.issues.filter(i => i.severity === s && !i.known).length;
  return `<h1>Scanner</h1>
  <div class="filters">${btn("all", "All")}${btn("error", `Errors (${counts("error")})`)}${btn("warning", `Warnings (${counts("warning")})`)}${btn("decision", `Waiting on Jordan (${counts("decision")})`)}${btn("gap", `Not designed yet (${counts("gap")})`)}
  <input id="q" placeholder="Search (title, file, place…)" value="${esc(issueFilter.q)}">
  <a href="/api/report.md" target="_blank">Download report (.md)</a></div>
  <div class="small muted">Categories: ${cats.map(esc).join(", ")}. Every scan reads the files fresh; press Rescan after editing.</div>
  <div id="issue-list"></div>`;
}
function bindIssues() {
  const draw = () => {
    const q = issueFilter.q.toLowerCase();
    const match = i => (issueFilter.sev === "all" || i.severity === issueFilter.sev) &&
      (!q || (i.title + " " + i.detail + " " + (i.path || "") + " " + (i.entity || "") + " " + i.category).toLowerCase().includes(q));
    const list = D.issues.filter(i => !i.known && match(i)), known = D.issues.filter(i => i.known && match(i));
    // Items already accepted as known never show as open or waiting; they sit folded at the end.
    document.getElementById("issue-list").innerHTML = (list.map(issueHTML).join("") || "<div class='muted'>Nothing open here.</div>") +
      (known.length ? `<details class="known-list"><summary>Accepted as known, no action needed (${known.length})</summary>${known.map(issueHTML).join("")}</details>` : "");
  };
  document.querySelectorAll("[data-sev]").forEach(b => b.onclick = () => { issueFilter.sev = b.dataset.sev; route(); });
  document.getElementById("q").oninput = e => { issueFilter.q = e.target.value; draw(); };
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
  return `<text${opts.cat ? ` data-cat="${opts.cat}"` : ""} x="${X(x).toFixed(1)}" y="${Y(y).toFixed(1)}" font-size="${size.toFixed(1)}" fill="${opts.fill || "#e8f1fb"}" text-anchor="${opts.anchor || "middle"}" dominant-baseline="middle" font-weight="${opts.weight || 600}">${esc(text)}</text>`;
}
function labelR(x, y, text, size, opts) {
  opts = opts || {};
  return `<text${opts.cat ? ` data-cat="${opts.cat}"` : ""} transform="rotate(-90 ${X(x).toFixed(1)} ${Y(y).toFixed(1)})" x="${X(x).toFixed(1)}" y="${Y(y).toFixed(1)}" font-size="${size.toFixed(1)}" fill="${opts.fill || "#e8f1fb"}" text-anchor="middle" dominant-baseline="middle" font-weight="${opts.weight || 600}">${esc(text)}</text>`;
}
// fit a label in a box, turning it sideways when the box is tall; never drops a label (streets, bays)
function boxLabel(r, text, fs, opts) {
  const w = (r[1] - r[0]) * 1000, h = (r[3] - r[2]) * 1000, cx = (r[0] + r[1]) / 2, cy = (r[2] + r[3]) / 2;
  const tall = h > w * 1.3;
  const along = tall ? h : w, across = tall ? w : h;
  let s = Math.min(fs, (along * 0.92) / Math.max(1, text.length * 0.62), across * 0.8);
  s = Math.max(s, fs * 0.12);
  return tall ? labelR(cx, cy, text, s, opts) : label(cx, cy, text, s, opts);
}

function fitText(name, wKm, hKm, fs) {
  const w = wKm * 1000, h = hKm * 1000;
  let s = fs;
  if (name.length * s * 0.56 > w * 0.92) s = (w * 0.92) / (name.length * 0.56);
  return s >= fs * 0.5 && s <= h * 0.8 ? s : 0;
}

// ---- building labels that fit their shape (Jordan, 27 Nov 2026: "fix the words")
// A shaped building (L, U, courtyard, curved, from its plan) gets its name in the biggest open part of
// its own outline, never over a courtyard or outside its edges. Long names wrap onto 2 or 3 lines and
// turn sideways in tall spaces. A name that still can't be read is shortened to the building id, and
// left off only when even that won't fit (hovering still shows the full name).
const CH = 0.62, LH = 1.15;           // average capital width and line height, in font sizes
function inRing(pts, x, y) {
  let ins = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i], [xj, yj] = pts[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}
function inShape(b, x, y) {
  if (!b.outline_km) return true;
  let n = 0;
  for (const r of b.outline_km) if (inRing(r, x, y)) n++;
  for (const r of b.holes_km || []) if (inRing(r, x, y)) n++;
  return n % 2 === 1;
}
// Split words into n lines as evenly as possible.
function wrapLines(text, n) {
  const words = text.split(/\s+/).filter(Boolean);
  if (n <= 1 || words.length < 2) return [words.join(" ")];
  n = Math.min(n, words.length);
  const total = text.length, lines = [];
  let cur = [];
  for (let i = 0; i < words.length; i++) {
    cur.push(words[i]);
    const left = words.length - i - 1, need = n - lines.length - 1;
    if (need > 0 && (left === need || cur.join(" ").length >= total / n)) { lines.push(cur.join(" ")); cur = []; }
  }
  if (cur.length) lines.push(cur.join(" "));
  return lines;
}
// The best way to write text in a w × h box (metres): size, lines and whether it turns sideways.
function bestFit(text, w, h, fs) {
  let best = null;
  for (const side of [false, true]) {
    const along = side ? h : w, across = side ? w : h;
    for (let n = 1; n <= 3; n++) {
      const lines = wrapLines(text, n);
      if (lines.length < n) break;
      const longest = Math.max(...lines.map(l => l.length));
      const s = Math.min(fs, (along * 0.9) / Math.max(1, longest * CH), (across * 0.86) / (lines.length * LH));
      if (!best || s > best.s * 1.02) best = { s, lines, side };
    }
  }
  return best;
}
// Biggest open rectangles inside a building's own shape (on a grid), best first for this label.
const SPOT = new WeakMap();
function labelSpots(b) {
  if (SPOT.has(b)) return SPOT.get(b);
  const r = b.rect_km;
  let out;
  if (!b.outline_km) out = [r];
  else {
    const N = 28, dx = (r[1] - r[0]) / N, dy = (r[3] - r[2]) / N;
    const ok = [];
    for (let j = 0; j < N; j++) {
      const row = [];
      for (let i = 0; i < N; i++) {
        const x0 = r[0] + i * dx, y0 = r[2] + j * dy;
        // a cell counts only when its middle and all four corners (pulled in a little) are inside
        row.push(inShape(b, x0 + dx / 2, y0 + dy / 2) && inShape(b, x0 + dx * 0.1, y0 + dy * 0.1) && inShape(b, x0 + dx * 0.9, y0 + dy * 0.1) &&
          inShape(b, x0 + dx * 0.1, y0 + dy * 0.9) && inShape(b, x0 + dx * 0.9, y0 + dy * 0.9));
      }
      ok.push(row);
    }
    // every maximal rectangle of open cells (histogram method)
    out = [];
    const hgt = new Array(N).fill(0);
    for (let j = 0; j < N; j++) {
      for (let i = 0; i < N; i++) hgt[i] = ok[j][i] ? hgt[i] + 1 : 0;
      for (let i = 0; i < N; i++) {
        if (!hgt[i]) continue;
        let mh = Infinity;
        for (let k = i; k < N && hgt[k]; k++) {
          mh = Math.min(mh, hgt[k]);
          if (k + 1 < N && hgt[k + 1] >= mh) continue;   // keep widening while the height holds
          out.push([r[0] + i * dx, r[0] + (k + 1) * dx, r[2] + (j - mh + 1) * dy, r[2] + (j + 1) * dy]);
        }
      }
    }
    if (!out.length) out = [r];
  }
  SPOT.set(b, out);
  return out;
}
// Text for one building name inside its shape; "" when nothing readable fits.
function shapeLabel(b, text, fs, minS, opts) {
  let best = null;
  const tryText = t => {
    for (const s of labelSpots(b)) {
      const f = bestFit(t, (s[1] - s[0]) * 1000, (s[3] - s[2]) * 1000, fs);
      if (f && (!best || f.s > best.s)) best = Object.assign(f, { spot: s, text: t });
    }
  };
  tryText(text);
  if ((!best || best.s < minS) && !opts.noId && b.id && b.id !== text) { const keep = best; best = null; tryText(b.id); if (!best || (keep && keep.s >= best.s)) best = keep; }
  if (!best || best.s < minS) return "";
  const s = best.spot, cx = (s[0] + s[1]) / 2, cy = (s[2] + s[3]) / 2, n = best.lines.length;
  const halo = opts.halo ? ` stroke="${opts.halo}" stroke-width="${(best.s / 6).toFixed(1)}" paint-order="stroke" stroke-linejoin="round"` : "";
  const tspans = best.lines.map((l, i) => `<tspan x="${X(cx).toFixed(1)}" dy="${(i ? best.s * LH : -best.s * LH * (n - 1) / 2).toFixed(1)}">${esc(l)}</tspan>`).join("");
  const rot = best.side ? ` transform="rotate(-90 ${X(cx).toFixed(1)} ${Y(cy).toFixed(1)})"` : "";
  // where the name sits, for the measurement line that goes under it (plan2d.js drawSizes)
  const bx = [Math.min(X(s[0]), X(s[1])), Math.min(Y(s[2]), Y(s[3])), Math.max(X(s[0]), X(s[1])), Math.max(Y(s[2]), Y(s[3]))].map(v => v.toFixed(1)).join(" ");
  const tag = b.uid ? ` data-lbl="${b.uid}" data-spot="${bx}" data-th="${(best.s * LH * n).toFixed(1)}" data-side="${best.side ? 1 : 0}"` : "";
  return `<text${tag}${opts.cat ? ` data-cat="${opts.cat}"` : ""}${rot} x="${X(cx).toFixed(1)}" y="${Y(cy).toFixed(1)}" font-size="${best.s.toFixed(1)}" fill="${opts.fill}" text-anchor="middle" dominant-baseline="middle" font-weight="${opts.weight || 600}"${halo}>${tspans}</text>`;
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
    ${legend ? `<div class="map-legend"><button type="button" class="dl-btn" onclick="this.parentNode.classList.toggle('open')" title="What the colours mean · untick a colour to hide it">Legend</button><div class="lg-box">${legend}</div></div>` : ""}
    <div class="maphint">${("ontouchstart" in window) ? (hint || "Scroll to zoom · drag to move").replace(/[Ss]croll to zoom/, "pinch to zoom").replace(/^p/, (hint ? "p" : "P")) : (hint || "Scroll to zoom · drag to move")}</div></div>`;
}
// Clickable areas stand out (Jordan, 27 Nov 2026): every clickable next-level area gets a clear outline
// drawn on top of the coloured detail, the detail underneath is dimmed a little, and the area under
// the mouse (or the one you are on) gets a bold red ring. Works on every level from the same .hit marks.
function ringLayer(svg) {
  const old = svg.querySelector("#rings"); if (old) old.remove();
  const hits = [...svg.querySelectorAll(".hit")];
  if (!hits.length) return;
  const NS = "http://www.w3.org/2000/svg", layer = document.createElementNS(NS, "g");
  layer.id = "rings";
  for (const h of hits) {
    const shapes = h.matches("path,rect,circle,polygon") ? [h] : [...h.querySelectorAll("path,rect,circle,polygon")];
    if (!shapes.length) continue;
    const grp = document.createElementNS(NS, "g");
    grp.setAttribute("class", "ring" + (h.dataset.sel ? " sel" : ""));
    if (h.dataset.cat) grp.dataset.cat = h.dataset.cat;
    const t = h.querySelector("title"); if (t) grp.append(t.cloneNode(true));
    for (const sh of shapes) {
      const c = sh.cloneNode(false);
      for (const a of ["class", "onclick", "style", "stroke-dasharray", "fill-opacity", "opacity", "pointer-events"]) c.removeAttribute(a);
      c.setAttribute("fill", "transparent");
      const tr = sh.closest("[transform]");
      if (tr && tr !== svg && !h.contains(tr) && tr !== sh) c.setAttribute("transform", tr.getAttribute("transform"));
      grp.append(c);
    }
    grp.addEventListener("click", e => { e.stopPropagation(); h.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    layer.append(grp);
  }
  svg.classList.add("has-rings");
  svg.append(layer);
}
function bindMap() {
  const svg = document.getElementById("map");
  if (!svg) return;
  ringLayer(svg);
  applyHidden();
  let vb = svg.getAttribute("viewBox").split(/\s+/).map(Number);
  const set = () => svg.setAttribute("viewBox", vb.join(" "));
  fitMapHeight();
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
// Make the map box the shape of what it shows, so a long thin block is not lost in empty space.
// Between 300 px and the normal height (72% of the screen, at most 760 px).
function fitMapHeight() {
  const svg = document.getElementById("map");
  if (!svg || !svg.dataset.vb) return;
  const v = svg.dataset.vb.split(",").map(Number), w = svg.getBoundingClientRect().width;
  if (!w || !v[2]) return;
  const max = Math.min(window.innerHeight * (window.innerWidth <= 700 ? 0.58 : 0.72), 760), min = Math.min(340, max);
  svg.style.height = Math.round(Math.max(min, Math.min(max, w * v[3] / v[2] * 1.08))) + "px";
}
window.addEventListener("resize", () => { clearTimeout(fitMapHeight.t); fitMapHeight.t = setTimeout(fitMapHeight, 80); });
function fitMap() { const s = document.getElementById("map"); if (s) s.setAttribute("viewBox", s.dataset.vb.split(",").join(" ")); }
window.fitMap = fitMap;
function go(h) { location.hash = h; }
window.go = go;

// ------------------------------------------------------------------ explore
function crumbs(parts) {
  // Codes only (Jordan): D5 › F3 › P2 › B5 › A1 (› LB1 › R208 added for a room). Names are in the panel; each code shows its name on hover.
  const h = location.hash.replace(/^#\/?/, "");
  const [kind, a, b] = h.split("/").map(decodeURIComponent);
  const out = [];
  try {
    let d = null, x = null, p = null, blk = null, bd = null;
    if (kind === "deck") d = IX.decks[+a];
    if (kind === "district") { x = IX.districts[a]; d = x && IX.decks[x.deck]; }
    if (kind === "precinct" || kind === "block" || kind === "street") p = IX.precincts[a];
    if (kind === "building") { bd = IX.buildings[a]; p = bd && IX.precincts[bd.precinct_uid]; }
    if (p) { d = IX.decks[p.deck]; x = IX.districts[p.district_id]; }
    if (p && kind === "block") blk = (p.blocks || []).find(q => q.id === b);
    if (bd) blk = (p.blocks || []).find(q => q.id === (bd.blocks || [])[0]);
    if (d) out.push([`D${d.n}`, `#/deck/${d.n}`, `Deck ${d.n} · ${d.name}`]);
    if (x && d) out.push([`F${(d.districts || []).findIndex(q => q.id === x.id) + 1}`, `#/district/${x.id}`, x.name]);
    if (p) out.push([`P${String(p.id).replace(/^P/, "")}`, `#/precinct/${p.uid}`, `${p.id} ${p.name}`]);
    if (blk) out.push([`B${(/(\d+)/.exec(blk.name || "") || [])[1] || "?"}`, `#/block/${p.uid}/${blk.id}`, `${blk.name} (grid ${blk.id})`]);
    if (kind === "street" && p) { const st = (p.streets || [])[+b]; out.push([`S${+b + 1}`, "", st ? st.name : "Street"]); }
    if (bd) out.push([`A${blk ? blockNo(p, blk.id, bd) : "?"}`, `#/building/${bd.uid}`, `${bd.id} ${bd.name}`]);
  } catch (e) { /* fall back to names */ }
  if (!out.length) out.push(...parts.slice(1).map(q => [q[0], q[1], q[0]]));
  out.unshift(["Invicta", "#/ship", "The whole ship"]);
  return `<div class="crumbs">` + out.map((q, i) => {
    const mid = i > 1 && i < out.length - 2 ? " mid" : "";
    return i === out.length - 1 ? `<b title="${esc(q[2])}">${esc(q[0])}</b>` : `<a class="crumb${mid}" href="${q[1]}" title="${esc(q[2])}">${esc(q[0])}</a><span class="sep${mid}">›</span>`;
  }).join("") + `</div>`;
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
  const decks = D.model.decks.map(d => `<li onclick="go('#/deck/${d.n}')"><span>${d.emblem_web ? `<img class="emblem-sm" src="${staticSrc(d.emblem_web)}" alt="">` : ""}<b>${d.n} ${esc(d.name)}</b> <span class="muted small">${esc(d.role)}</span></span><span class="small">${area(d.net_area_calc)}</span></li>`).join("");
  const panel = `<h1>${esc(s.name)}</h1><div class="small muted">${esc((s.meta || {}).title || "")} · ${fileLink(s.sheet, "Sheet S0")}</div>
    <h3>Key dimensions (canon)</h3><div class="kv">${dims}</div>
    <h3>Deck cities</h3><ul class="list">${decks}<li onclick="go('#/crown')"><span>${D.model.crown && D.model.crown.emblem_web ? `<img class="emblem-sm" src="${staticSrc(D.model.crown.emblem_web)}" alt="">` : ""}<b>Crown Bridge</b> <span class="muted small">detachable command ship</span></span><span class="small">14 levels</span></li></ul>
    <h3>Structure</h3><div class="kv">${(s.structure || []).map(r => `<div>${esc(r.item)}</div><div>${esc(r.value)}</div>`).join("")}</div>
    ${issueBlock("ship", "Ship-level issues")}`;
  return layout([["Invicta", "#/ship"]], mapShell(g, vb, "", "", "Click a deck · scroll to zoom"), panel);
}

// ---- crown bridge
function crownView() {
  const c = D.model.crown;
  const levels = (c.levels || []).map(l => `<tr><td>${esc(l.level)}</td><td><b>${esc(l.name)}</b><div class="small muted">${esc(l.function)}</div></td><td>${usText(l.footprint)}</td><td>${esc(l.area)}</td><td>${esc(l.height)}</td></tr>`).join("");
  return crumbs([["Invicta", "#/ship"], ["Crown Bridge", ""]]) + `<div class="card"><div class="emblem-head">${emblem(c, 96)}<h1>Crown Bridge</h1></div><div class="small muted">${fileLink(c.sheet, "Crown Bridge data sheet")} · canon</div>
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
    if (IX.psets[x.id]) g += precinctsContext(IX.psets[x.id], fs / 4);
  }
  const pl = d.districts.find(x => x.is_plaza);
  if (pl && pl.circle_km) {
    const [cx, cy, r] = pl.circle_km;
    g += `<circle class="hit" onclick="go('#/district/${pl.id}')" cx="${X(cx)}" cy="${Y(cy)}" r="${r * 1000}" fill="#0a2343" stroke="#ffc266" stroke-width="${fs / 6}" stroke-dasharray="${fs / 2} ${fs / 3}"><title>${esc(pl.name)}</title></circle>`;
    if (IX.psets[pl.id]) g += precinctsContext(IX.psets[pl.id], fs / 4);   // drawn only; the circle above takes the click
    g += `<circle pointer-events="none" cx="${X(cx)}" cy="${Y(cy)}" r="800" fill="#06182f" stroke="#6fd0ff" stroke-width="${fs / 6}"/>`;
  }
  // Keelway and stops
  const stops = (d.keelway || []).map(s => parseInt(String(s.frame).replace(/\D/g, ""), 10)).filter(v => !isNaN(v));
  if (stops.length) {
    g += `<line x1="${X(Math.min(...stops) * 0.5)}" y1="0" x2="${X(Math.max(...stops) * 0.5)}" y2="0" stroke="#6fd0ff" stroke-width="${fs / 3}"/>`;
    for (const s of d.keelway) {
      const f = parseInt(String(s.frame).replace(/\D/g, ""), 10);
      g += `<circle pointer-events="none" cx="${X(f * 0.5)}" cy="0" r="${fs / 2}" fill="#0a2343" stroke="#6fd0ff" stroke-width="${fs / 6}"/>`;
    }
  }
  for (const s of d.crossline || []) {
    const f = parseInt(String(s.frame).replace(/\D/g, ""), 10), off = parseFloat(s.offset);
    if (!isNaN(off) && off !== 0) g += `<line x1="${X(f * 0.5)}" y1="0" x2="${X(f * 0.5)}" y2="${Y(off)}" stroke="#6fd0ff" stroke-width="${fs / 6}" stroke-dasharray="${fs / 2} ${fs / 3}"/><circle pointer-events="none" cx="${X(f * 0.5)}" cy="${Y(off)}" r="${fs / 2}" fill="#0a2343" stroke="#6fd0ff" stroke-width="${fs / 6}"/>`;
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
  const legend = `<span><i style="background:#2273b8"></i>has a precinct plan</span><span><i style="background:#2b4563"></i>not designed yet</span><span><i style="background:#4a3513;border-color:#ffc266"></i>central plaza (canon)</span><span><b style="color:#6fd0ff">━</b> Keelway and stops</span>` + (Object.values(IX.psets).some(ps => ps.deck == n) ? catLegend() : "");
  const k = d.key || {};
  const keyRows = ["Gross outline", "Net floor area", "Floor / ceiling elevation", "Clear height", "Floor-to-floor stack height", "Design population", "Frames", "Atrium", "Governor", "Deck Chief"]
    .filter(r => k[r]).map(r => `<div>${esc(r)}</div><div>${usText(k[r])}</div>`).join("");
  const dl = d.districts.map(x => `<li onclick="go('#/district/${x.id}')"><span><b>${esc(x.name)}</b> ${x.is_plaza ? '<span class="small muted">plaza</span>' : ""}<br><span class="small muted">${esc(x.what)}</span></span><span class="small" style="text-align:right">${area(x.revB ? x.revB.area_km2 : x.area_km2)}<br>${badge(x.design_status)}</span></li>`).join("");
  const stopsT = (d.keelway || []).map(s => `<div>${esc(s.stop)}</div><div>${esc(s.frame)} · ${esc(s.address)} · ${usText(s.from_bow)} from deck bow</div>`).join("");
  const panel = `<div class="emblem-head">${emblem(d, 84)}<h1>${esc(d.title || ("Deck " + n))}</h1></div><div class="small muted">${esc(d.role)} · landmark: ${esc(d.landmark)}</div>
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

// Everything inside a precinct (streets, buildings, names), drawn for context only: nothing here takes
// clicks or hovers. Map rule (Jordan, 27 Nov 2026): every view draws everything down to the buildings,
// but only the next level down can be clicked.
function precinctContents(p, fs) {
  let g = `<g pointer-events="none">`;
  for (const c of p.exclude_circles_km || []) g += `<circle cx="${X(c[0])}" cy="${Y(c[1])}" r="${c[2] * 1000}" fill="#0a2343" stroke="#ffc266" stroke-width="${fs / 6}" stroke-dasharray="${fs / 2} ${fs / 3}"/>`;
  for (const st of p.streets || []) if (st.rect_km) g += rectEl(st.rect_km, `data-cat="${streetKey(st)}" fill="${streetCat(st).fill}" fill-opacity=".8"`);
  for (const bd of p.buildings || []) {
    const c = catOf(bd);
    g += shapeEl(bd, `data-cat="${catKey(bd)}" fill="${c.fill}" fill-opacity=".85" stroke="${bd.category === "medical" ? c.edge : "#071425"}" stroke-width="${fs / 14}"`);
    const r = bd.rect_km;
    if (r && !bd.bays_km) {
      g += shapeLabel(bd, bd.name, fs * 0.45, fs * 0.2, { fill: c.text, noId: true, cat: catKey(bd) });
    }
  }
  return g + "</g>";
}
// Precinct outlines with everything inside them, for context only (used on the deck view).
function precinctsContext(ps, fs) {
  let g = `<g pointer-events="none">`;
  for (const p of ps.precincts) g += `<path d="${pathOf(p.shape_km)}" fill="${p.status === "canon" ? "#2a6a4a" : "#1f5f99"}" fill-opacity=".6" stroke="#e8f1fb" stroke-opacity=".7" stroke-width="${fs / 12}"/>` + precinctContents(p, fs / 2);
  return g + "</g>";
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
  for (const o of d.districts) if (o.polygon_km && o.id !== id) g += `<path pointer-events="none" d="${pathOf(o.polygon_km)}" fill="#0f2a48" stroke="#2b4f78" stroke-width="${fs / 8}"/>`;
  g += frameGrid([b[0] - 0.5, b[1] + 0.5, b[2] - 0.3, b[3] + 0.3], 1, fs * 0.8, true);
  if (shape) g += `<path d="${pathOf(shape)}" fill="${ps ? "#123d63" : "url(#hatch)"}" stroke="#fff" stroke-width="${fs / 4}"/>`;
  if (ps) {
    for (const p of ps.precincts) {
      const pb = bboxOf(p.shape_km);
      g += `<path class="hit" onclick="go('#/precinct/${p.uid}')" d="${pathOf(p.shape_km)}" fill="${p.status === "canon" ? "#2a6a4a" : "#1f5f99"}" fill-opacity=".85" stroke="#e8f1fb" stroke-width="${fs / 6}"><title>${p.id} ${esc(p.name)}</title></path>`;
      g += precinctContents(p, fs);
      const s = fitText(`${p.id} ${p.name.toUpperCase()}`, pb[1] - pb[0], pb[3] - pb[2], fs) || fitText(p.id, pb[1] - pb[0], pb[3] - pb[2], fs);
      if (s) g += label((pb[0] + pb[1]) / 2, (pb[2] + pb[3]) / 2, s < fs * 0.6 ? p.id : `${p.id} ${p.name.toUpperCase()}`, s, {}).replace("<text ", `<text pointer-events="none" paint-order="stroke" stroke="#071425" stroke-width="${(s / 5).toFixed(1)}" `);
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
  return layout([["Invicta", "#/ship"], deckCrumb(d), [x.name, ""]], mapShell(g, vb, "", ps ? catLegend() : "", ps ? "Click a precinct" : ""), panel);
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
    g += (opts.streetsClickable ? `<g class="hit" data-cat="${streetKey(st)}" onclick="go('#/street/${p.uid}/${i}')"><title>${esc(st.name)} · click for details</title>` : `<g data-cat="${streetKey(st)}" pointer-events="none">`) +
      rectEl(st.rect_km, `fill="${streetCat(st).fill}"${sel ? ` stroke="#ffc266" stroke-width="${fs / 3}"` : ""}`) + "</g>";
  });
  if (opts.blocks) g += blocksLayer(p, fs, false, opts.blocks.selected);
  // buildings
  for (const b of p.buildings) {
    if (!b.rect_km) continue;
    const c = catOf(b);
    const stroke = b.uid === opts.selected ? "#ffc266" : b.status === "canon" ? "#5fd39a" : b.category === "medical" ? c.edge : "#e8f1fb";
    const sw = b.uid === opts.selected ? fs / 2.5 : b.category === "medical" ? fs / 5 : fs / 9;
    const click = opts.clickBuildings ? opts.clickBuildings(b) : false;
    g += (click ? `<g class="hit" data-cat="${catKey(b)}"${b.uid === opts.selected ? ` data-sel="1"` : ""} onclick="go('#/building/${b.uid}')"><title>${b.id} ${esc(b.name)} · ${esc(c.label)}${b.shape ? " · " + esc(b.shape) : ""} · click for details</title>` : `<g data-cat="${catKey(b)}" pointer-events="none">`) +
      shapeEl(b, `fill="${c.fill}" stroke="${stroke}" stroke-width="${sw}"`);
    for (const dr of b.doors_km || []) g += rectEl(dr, `data-cat="door" fill="#ff8a3d"`);
    g += "</g>";
    if (opts.labels !== false) {
      if (b.bays_km) {
        // each bay gets its own name, or a numbered generic one
        const base = b.bay_label || "Bay";
        const tag = i => base === "Street" ? String.fromCharCode(65 + i) : i + 1;   // Street A, Street B … ; Berth 1, Berth 2 …
        b.bays_km.forEach((s, i) => { g += boxLabel(s, (b.bay_names && b.bay_names[i]) || `${base} ${tag(i)}`, fs * 0.4, { weight: 400, fill: c.text, cat: catKey(b) }); });
        const r = b.rect_km, wide = (r[1] - r[0]) >= (r[3] - r[2]);
        if (b.bays_km.length > 3 && !b.bay_names) g += wide ? label((r[0] + r[1]) / 2, r[2] - fs * 0.0006, b.name.toUpperCase(), fs * 0.5, { fill: "#cfe3f7", cat: catKey(b) })
                  : labelR(r[0] - fs * 0.0006, (r[2] + r[3]) / 2, b.name.toUpperCase(), fs * 0.5, { fill: "#cfe3f7", cat: catKey(b) });
      } else g += shapeLabel(b, b.name.toUpperCase(), fs * 0.75, fs * 0.25, { fill: c.text, halo: c.fill, cat: catKey(b) });
    }
  }
  if (opts.labels !== false) for (const st of p.streets || []) {
    const r = st.rect_km, w = r[1] - r[0], h = r[3] - r[2];
    g += boxLabel(r, st.name, fs * 0.55, { fill: streetCat(st).text, weight: 400, cat: streetKey(st) });
  }
  return g;
}
function blocksLayer(p, fs, clickable, selected) {
  let g = "";
  for (const blk of p.blocks || []) {
    const sel = blk.id === selected;
    g += `<path data-cat="block" ${clickable ? `class="hit"${sel ? ` data-sel="1"` : ""} onclick="go('#/block/${p.uid}/${blk.id}')"` : `pointer-events="none"`} d="${pathOf(blk.part_km)}" fill="${sel ? "rgba(255,194,102,.18)" : clickable ? "rgba(111,208,255,.04)" : "none"}" stroke="${sel ? "#ffc266" : "#6fd0ff"}" stroke-opacity="${sel ? 1 : .45}" stroke-width="${sel ? fs / 3 : fs / 10}">${clickable ? `<title>${blk.name} (${blk.id}) · ${blk.contents.length} item(s)</title>` : ""}</path>`;
    const c = blk.cell_km;
    g += `<text data-cat="block" x="${(X(c[0]) - fs * 0.25).toFixed(1)}" y="${(Y(c[2]) + fs * 0.45).toFixed(1)}" font-size="${(fs * 0.4).toFixed(1)}" fill="#6fd0ff" fill-opacity=".8" text-anchor="end" font-weight="600" pointer-events="none">${esc(blk.name)}</text>`;
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
  g += drawPrecinct(p, fs, {});
  g += blocksLayer(p, fs, true);
  const tools = "";
  const legend = catLegend() + `<span><i style="background:none;border-color:#5fd39a"></i>canon (green outline)</span>` + legendItem("door", "dock door", "background:#ff8a3d;border:0") + legendItem("block", "block outlines and names", "background:none;border-color:#6fd0ff");
  const groups = {};
  for (const bd of p.buildings) (groups[bd.kind] = groups[bd.kind] || []).push(bd);
  const bl = Object.entries(groups).map(([k, list]) => `<h3>${esc(k)} (${list.length})</h3><ul class="list">` + list.map(bd =>
    `<li onclick="go('#/building/${bd.uid}')"><span>${bd.id} <b>${esc(bd.name)}</b>${bd.bay_count ? ` <span class="small muted">× ${bd.bay_count}</span>` : ""}${purposeLine(bd)}</span><span class="small">${bd.size_m ? dims(bd.size_m[0], bd.size_m[1]) : ""} ${badge(bd.status)}</span></li>`).join("") + "</ul>").join("");
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
    mapShell(g, vb, tools, legend, "Click a block (blocks are bounded by streets and never cut through a building)"), panel);
}

// ---- block
function blockView(puid, bid) {
  const p = IX.precincts[puid];
  const blk = p && (p.blocks || []).find(k => k.id === bid);
  if (!blk) return `<div class="note">Unknown block ${esc(bid)}.</div>`;
  const x = IX.districts[p.district_id], d = IX.decks[p.deck];
  const c = blk.cell_km;
  const vb = vbFor(c, 0.12);
  const fs = vb[2] / 40;
  const here = new Set(blk.contents.map(ct => ct.id));
  let g = drawPrecinct(p, fs, { clickBuildings: q => here.has(q.id), labels: true, blocks: { selected: bid } });
  // dim everything outside this block
  const outer = `M${vb[0] - 4 * vb[2]},${vb[1] - 4 * vb[3]}h${9 * vb[2]}v${9 * vb[3]}h${-9 * vb[2]}Z`;
  g += `<path d="${outer} ${pathOf(blk.part_km)}" fill="rgba(5,12,22,.55)" fill-rule="evenodd" pointer-events="none"/>`;
  // bow right: the lower frame number is on the right
  g += label(c[0], c[2] - 0.04, `${nd(c[0], 2)} km`, fs * 0.6, { fill: "#ffc266" }) + label(c[1], c[2] - 0.04, `${nd(c[1], 2)} km`, fs * 0.6, { fill: "#ffc266" });
  g += label(c[1] + 0.03, (c[2] + c[3]) / 2, blk.lane === blk.lane_end ? `lane ${blk.lane}` : `lanes ${blk.lane}–${blk.lane_end}`, fs * 0.6, { fill: "#ffc266", anchor: "end" });
  const items = blk.contents.map(ct => {
    const bd = p.buildings.find(q => q.id === ct.id);
    return `<li onclick="go('#/building/${bd.uid}')"><span>${bd.id} <b>${esc(bd.name)}</b> <span class="small muted">${esc(bd.kind)}</span>${purposeLine(bd)}</span><span class="small">${ct.of ? (ct.parts < ct.of ? `${ct.parts} of ${ct.of} ${esc((bd.bay_label || "bay").toLowerCase())}s here ` : "") : ct.share < 0.995 ? Math.round(ct.share * 100) + "% of it here " : ""}${badge(bd.status)}</span></li>`;
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
  return layout([["Invicta", "#/ship"], deckCrumb(d), [x.name, `#/district/${x.id}`], [`${p.id} ${p.name}`, `#/precinct/${p.uid}`], [blk.name, ""]],
    mapShell(g, vb, "", catLegend(), "Click a building"), panel);
}

// ---- building
function fileSrc(rel) {
  return window.ADXI_STATIC ? "file/" + rel.split("/").map(encodeURIComponent).join("/") : "/file?path=" + encodeURIComponent(rel);
}
function conceptBlock(uid, b) {
  const list = (((D.concepts || {}).buildings || {})[uid] || []).slice();
  // Concept render made from the building's own 3D plan (tools/concepts, Jordan 27 Nov 2026): shown first.
  if (b.concept_render) list.unshift({ file: b.concept_render, title: "Concept render from the 3D plan", by: "ADXI renderer", render: true });
  const add = window.adxiAddConcept ? `<button class="concept-add" onclick="adxiAddConcept('${uid}', '${esc(b.id)} ${esc(b.name).replace(/'/g, "")}')">Add concept art</button>` : "";
  if (!list.length && !add) return "";
  return `<h3>Concept art</h3>
    ${list.map(c => `<figure class="concept"><a href="${fileSrc(c.file)}" target="_blank" rel="noopener"><img src="${fileSrc(c.file)}" alt="${esc(c.title || "Concept art")}" loading="lazy"></a>
      <figcaption><span class="concept-tag">CONCEPT · not canon</span> ${esc(c.title || "")} <span class="small muted">by ${esc(c.by || "a helper")}${c.added ? ", " + esc(c.added) : ""}</span>${window.adxiDeleteConcept && !c.render ? ` <button class="concept-del" onclick="adxiDeleteConcept('${uid}', '${esc(c.file)}', '${esc(b.id)} ${esc(b.name).replace(/'/g, "")}')">Delete</button>` : ""}</figcaption></figure>`).join("")}
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
  const pu = panel.querySelector(".purpose");
  if (pu) lines.push("Purpose: " + clean(pu).replace(/^Purpose\s*/, ""));
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
  const g = drawPrecinct(p, fs, { selectedStreet: i, blocks: { selected: null } });
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
// Designation (Jordan, 27 Nov 2026): D<deck> F<district> P<precinct> B<block> A<building> L<level> R<room>, no dashes,
// e.g. D5F1P1B1A1L2R1. District = its place in the deck's canon list; precinct = its P number; block = its Block
// number; building = its place in the block; level = L1, L2 … above deck and LB1, LB2 … below deck (left out for
// single-level buildings); room = its place on that level of the building's plan.
function designation(b, levelTag, room) {
  const p = IX.precincts[b.precinct_uid], d = IX.decks[p.deck];
  const f = (d.districts || []).findIndex(x => x.id === p.district_id) + 1;
  const bid = (b.blocks || [])[0], blk = (p.blocks || []).find(q => q.id === bid);
  const bn = blk ? (/(\d+)/.exec(blk.name || "") || [])[1] : null;
  const an = bid ? blockNo(p, bid, b) : null;
  let out = `D${p.deck}F${f || "?"}P${String(p.id).replace(/^P/, "")}` + (bn ? `B${bn}` : "") + (an && an !== "—" ? `A${an}` : "");
  if (levelTag) out += levelTag;
  if (room != null) out += `R${room}`;
  return out;
}
window.designation = designation;
// Address = the street-bounded block plus the building's number in it; grid position = frame and lane at its centre.
function blockNo(p, bid, b) {
  const blk = (p.blocks || []).find(q => q.id === bid);
  const ids = blk ? (blk.contents || []).map(c => c.uid || c.id || c).filter(Boolean) : [];
  const i = ids.findIndex(x => x === b.uid || x === b.id);
  return i >= 0 ? i + 1 : (p.buildings.filter(x => (x.blocks || [])[0] === bid).indexOf(b) + 1 || "—");
}
function gridPos(addr) {
  const m = /^D\d+-F(\d+)-([A-Z])$/.exec(addr || "");
  return m ? `F${m[1]} lane ${m[2]}` : addr;
}
// "What it looks like": a short summary built only from the building's stored architecture fields.
function firstSentences(t, n, max) {
  const parts = String(t || "").replace(/\s+/g, " ").trim().match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g) || [];
  let out = parts.slice(0, n).join("").trim();
  if (out.length > max) out = out.slice(0, max).replace(/\s+\S*$/, "") + "…";
  return out;
}
function looksLike(uid, b) {
  const bits = [];
  const size = b.size_m ? dims(b.size_m[0], b.size_m[1]) : b.rect_km ? dims((b.rect_km[1] - b.rect_km[0]) * 1000, (b.rect_km[3] - b.rect_km[2]) * 1000) : "";
  const hf = [b.height_m != null ? `${len(b.height_m)} tall` : "", b.floors ? `${b.floors} floors` : ""].filter(Boolean).join(", ");
  if (hf || size) bits.push(`<p>${esc([hf, size ? `on a ${size} lot` : ""].filter(Boolean).join(", "))}.</p>`);
  if (b.look) bits.push(`<p>${esc(firstSentences(b.look, 3, 420))}</p>`);
  if (b.structure) bits.push(`<p class="small muted">Built as: ${esc(firstSentences(b.structure, 1, 200))}</p>`);
  const pm = D.models && D.models[uid], pi = D.model_index && D.model_index[uid];
  const plan = pm ? { levels: pm.levels.length, parts: pm.elements.length } : pi ? { levels: pi[0], parts: pi[1] } : null;
  const has = !!(b.look || b.height_m != null || b.floors || b.structure);
  return `<details class="sect looks" open><summary><h3>What it looks like</h3></summary>
    ${has ? bits.join("") : `<p class="muted">Not designed yet: no look, height or floors are stored. Tell Claude what it should look like and it will add them.</p>`}
    <div class="small muted">${!D.models && !D.model_index ? "" : plan ? `Full plan stored: ${plan.levels} levels, ${plan.parts} parts.` : "No room plan yet, so 3D shows the footprint only."} <button class="v3d-open" onclick="window.adxi3D && adxi3D.open()">Open in 3D</button></div></details>`;
}

function buildingView(uid) {
  const b = IX.buildings[uid];
  if (!b) return `<div class="note">Unknown building ${esc(uid)}.</div>`;
  const p = IX.precincts[b.precinct_uid], x = IX.districts[p.district_id], d = IX.decks[p.deck], ps = IX.psets[p.district_id];
  const r = b.rect_km;
  const vb = r ? vbFor(r, Math.max(0.15, Math.max(r[1] - r[0], r[3] - r[2]) * 0.6)) : vbFor(p.bbox_km);
  const fs = vb[2] / 45;
  let g = drawPrecinct(p, fs, { selected: uid, blocks: { selected: null } });
  g += blocksLayer(p, fs, false);
  const w = r ? (r[1] - r[0]) * 1000 : null, h = r ? (r[3] - r[2]) * 1000 : null;
  const sz = b.size_m;
  const arch = [["Height", b.height_m != null ? len(b.height_m) : null], ["Floors", b.floors], ["Structure", b.structure], ["Entrances", b.entrances],
    ["Materials / look", b.look], ["Capacity", b.capacity], ["Services", b.services], ["Interior layout", b.interior]]
    .map(([k, v]) => {
      if (v == null || v === "") return `<div>${k}</div><div>${ND}</div>`;
      const t = String(v), long = t.length > 220;
      return `<div>${k}</div><div class="kvv"><span class="${long ? "clamp" : ""}" ${long ? `onclick="this.classList.toggle('open')" title="Tap to expand"` : ""}>${esc(t)}</span><button class="cp" title="Copy" data-copy="${esc(k + ": " + t)}" onclick="copyFrom(this)">⧉</button></div>`;
    }).join("");
  const blocks = (b.blocks || []).map(k => { const bk = (p.blocks || []).find(q => q.id === k); return `<a href="#/block/${p.uid}/${k}">${esc(bk ? bk.name : "")} · ${k}</a>`; }).join(", ");
  const firstBlock = (b.blocks || [])[0];
  const panel = `<h1>${esc(b.name)} <button class="cp cp-all" title="Copy all building information" onclick="copyBuilding(this)">⧉</button></h1><div class="small muted">${b.id} · ${p.id} ${esc(p.name)} · ${esc(x.name)} · Deck ${d.n} ${esc(d.name)}</div>
    <div style="margin:8px 0">${badge(b.status)} <span class="badge" style="color:#cfd8e3">${esc(b.kind)}</span></div>
    <div class="purpose"><b>Purpose</b> ${b.purpose ? esc(b.purpose) : `<span class="muted">${ND}</span>`}</div>
    ${looksLike(uid, b)}
    <div class="kv">
      <div>Designation</div><div><b>${esc(designation(b))}</b> <span class="small muted">(deck · district · precinct · block · building)</span></div>
      <div>Address</div><div>${firstBlock ? `${esc(firstBlock)}, building ${blockNo(p, firstBlock, b)}` : esc(b.address || "—")}</div>
      <div>Grid position</div><div>${b.address ? `${esc(gridPos(b.address))} <span class="small muted">(frame line and lane at the centre)</span>` : ND}</div>
      <div>Footprint</div><div>${sz ? dims(sz[0], sz[1]) : r ? dims(w, h) : ND}${b.bay_count ? ` <span class="small muted">each, × ${b.bay_count}</span>` : ""}</div>
      ${r && sz && !b.bays_km && (Math.abs(w - sz[0]) > 15 && Math.abs(w - sz[1]) > 15) ? `<div>Drawn</div><div class="sev-warning">${dims(w, h)}</div>` : ""}
      <div>Used for</div><div><i class="swatch" style="background:${catOf(b).fill};border-color:${catOf(b).edge}"></i> ${esc(catOf(b).label)}${b.category_auto ? ` <span class="small muted">(from its name)</span>` : ""}</div>
      <div>Shape</div><div>${b.shape ? esc(b.shape) : b.bays_km ? "a row of bays" : "rectangle"}</div>
      <div>Ground area</div><div>${b.footprint_km2 != null ? area(b.footprint_km2) : ND}${b.holes_km ? ` <span class="small muted">(courtyard not counted)</span>` : ""}</div>
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
  if (firstBlock) { const fb = (p.blocks || []).find(q => q.id === firstBlock); cr.push([fb ? fb.name : "Block", `#/block/${p.uid}/${firstBlock}`]); }
  cr.push([b.name, ""]);
  return layout(cr, mapShell(g, vb, "", catLegend(), "Click another building"), panel);
}

load();
