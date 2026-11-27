/* ADXI: Invicta: 3D view, built from the same stored data as the 2D plans.
   - A building with a plan (Invicta/data/models/<uid>.json): every level, room, core, mass, wall and door,
     stacked at its stored floor height. Colours and finishes come from the building's "look" text.
   - A building without a plan: its footprint as a plain grey box, at its stored height if it has one,
     otherwise a flat placeholder. Grey and dashed means "not designed yet". Nothing is invented.
   - An area (precinct or block): the ground, streets and every building in it.
   Controls: Orbit (drag to turn, wheel or pinch to zoom, right-drag to pan) or Walk (W A S D or arrows to move,
   drag to look, Q / E to change level). Three.js is loaded from esm.sh the first time 3D is opened. */
(function () {
  "use strict";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const FT = 3.28084;
  const isMetric = () => localStorage.getItem("adxi.units") === "metric";
  const len = (m) => isMetric() ? `${Math.round(m * 10) / 10} m` : `${Math.round(m * FT).toLocaleString()} ft (${Math.round(m)} m)`;
  let THREE = null, Orbit = null;

  async function lib() {
    if (THREE) return;
    THREE = await import("https://esm.sh/three@0.170.0");
    Orbit = (await import("https://esm.sh/three@0.170.0/examples/jsm/controls/OrbitControls.js")).OrbitControls;
  }

  // ---- Finishes from the building's "look" text. Only words that are actually written there are used.
  const FINISH = [
    [/\bglass|glazed|glazing|curtain wall/i, "glass", 0xa9d6ee],
    [/\bsandstone/i, "sandstone", 0xd9c39a],
    [/\blimestone|travertine/i, "limestone", 0xe5dccb],
    [/\bmarble/i, "marble", 0xf1eee8],
    [/\bstone/i, "stone", 0xcdbfa6],
    [/\bconcrete/i, "concrete", 0xb7b7b2],
    [/\bbrick/i, "brick", 0xa65a3f],
    [/\btimber|wood/i, "timber", 0xa87a4f],
    [/\bbrass|bronze|gold/i, "brass", 0xc9a45c],
    [/\btitanium|steel|metal|alumin/i, "metal", 0x9aa4ad],
    [/\bwhite\b/i, "white", 0xf2f2ee],
    [/\bcopper/i, "copper", 0xb87333],
  ];
  function finishes(look) {
    const t = String(look || "");
    const hits = FINISH.filter(([re]) => re.test(t));
    const walls = hits.find(([, n]) => n !== "glass" && n !== "brass" && n !== "copper");
    const trim = hits.find(([, n]) => n === "brass" || n === "copper" || n === "metal");
    return {
      names: hits.map(([, n]) => n),
      wall: walls ? walls[2] : 0xd8dde3,
      glass: hits.some(([, n]) => n === "glass"),
      trim: trim ? trim[2] : 0x8a96a3,
      greenRoof: /green roof|roof garden|garden roof|planted roof/i.test(t),
      fromLook: hits.length > 0,
    };
  }

  // ---- Building geometry. Ship frame: x km from the prow (toward the stern), y km across (starboard +).
  // Scene: X = ship x in metres, Z = ship y in metres, Y = up. Model frame: metres from the building's bow-port corner.
  function polyShape(pts, holes) {
    const s = new THREE.Shape();
    pts.forEach((p, i) => (i ? s.lineTo(p[0], p[1]) : s.moveTo(p[0], p[1])));
    s.closePath();
    for (const hl of holes || []) {            // courtyards and other open space inside the outline
      const hp = new THREE.Path();
      hl.forEach((p, i) => (i ? hp.lineTo(p[0], p[1]) : hp.moveTo(p[0], p[1])));
      hp.closePath();
      s.holes.push(hp);
    }
    return s;
  }
  function inPoly(q, pts) {
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const [xi, yi] = pts[i], [xj, yj] = pts[j];
      if ((yi > q[1]) !== (yj > q[1]) && q[0] < ((xj - xi) * (q[1] - yi)) / (yj - yi || 1e-12) + xi) inside = !inside;
    }
    return inside;
  }
  function prism(pts, z0, h, mat, edges, holes) {
    // Extrude a plan outline (x, y metres) from height z0 up by h. Shape is drawn in X/Y then laid flat.
    const geo = new THREE.ExtrudeGeometry(polyShape(pts, holes), { depth: Math.max(h, 0.05), bevelEnabled: false });
    geo.rotateX(Math.PI / 2);         // shape y -> scene z, extrusion -> down
    geo.translate(0, z0 + Math.max(h, 0.05), 0);
    const g = new THREE.Group();
    g.add(new THREE.Mesh(geo, mat));
    if (edges) g.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), edges));
    return g;
  }
  function wallBox(line, z0, h, t, mat) {
    const [a, b] = [line[0], line[line.length - 1]];
    const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const m = new THREE.Mesh(new THREE.BoxGeometry(L, h, t), mat);
    m.position.set((a[0] + b[0]) / 2, z0 + h / 2, (a[1] + b[1]) / 2);
    m.rotation.y = -Math.atan2(b[1] - a[1], b[0] - a[0]);
    return m;
  }

  function buildBuilding(b, model, origin) {
    const g = new THREE.Group();
    const r = b.rect_km;
    g.position.set((r[0] - origin[0]) * 1000, 0, (r[2] - origin[1]) * 1000);
    const f = finishes(b.look);
    const info = { levels: [], designed: !!(model && model.levels && model.levels.length), finishes: f };
    if (!info.designed) {
      // Not designed: its footprint (shaped outline with courtyards, or its box), in its map colour, dashed edges.
      const Lm = (r[1] - r[0]) * 1000, Wm = (r[3] - r[2]) * 1000;
      const h = typeof b.height_m === "number" ? b.height_m : 3;
      const cat = window.adxiCat ? window.adxiCat(b) : null;
      const mat = new THREE.MeshStandardMaterial({ color: cat ? new THREE.Color(cat.fill) : 0x6b7480, transparent: true, opacity: 0.55, roughness: 1 });
      const line = new THREE.LineDashedMaterial({ color: 0xb8c2cc, dashSize: Math.max(Lm, Wm) / 40, gapSize: Math.max(Lm, Wm) / 60 });
      const loc = (q) => [(q[0] - r[0]) * 1000, (q[1] - r[2]) * 1000];
      const parts = b.outline_km && !b.bays_km ? b.outline_km.map((o) => o.map(loc)) : (b.bays_km || [r]).map((q) => [[q[0], q[2]], [q[1], q[2]], [q[1], q[3]], [q[0], q[3]]].map(loc));
      const holes = (b.holes_km || []).map((o) => o.map(loc));
      for (const pts of parts) {
        const mine = holes.filter((hl) => inPoly(hl[0], pts));
        const box = prism(pts, 0, h, mat, line, mine);
        box.children[1].computeLineDistances();
        g.add(box);
      }
      info.placeholderHeight = typeof b.height_m !== "number";
      return { group: g, info };
    }
    const lv = model.levels.slice().sort((a, c) => a.z_m - c.z_m);
    const byId = Object.fromEntries(lv.map((l) => [l.id, l]));
    const matWall = new THREE.MeshStandardMaterial({ color: f.wall, roughness: 0.75, metalness: 0.05, side: THREE.DoubleSide });
    const matRoom = new THREE.MeshStandardMaterial({ color: f.wall, roughness: 0.8, transparent: true, opacity: 0.55, side: THREE.DoubleSide });
    const matGlass = new THREE.MeshStandardMaterial({ color: 0xa9d6ee, roughness: 0.1, metalness: 0.4, transparent: true, opacity: 0.35, side: THREE.DoubleSide });
    const matCore = new THREE.MeshStandardMaterial({ color: 0xe0a24a, roughness: 0.7 });
    const matSlab = new THREE.MeshStandardMaterial({ color: 0x8d949c, roughness: 0.9 });
    const matDoor = new THREE.MeshStandardMaterial({ color: 0x5fd39a, roughness: 0.6, transparent: true, opacity: 0.35, depthWrite: false });
    const matFix = new THREE.MeshStandardMaterial({ color: 0xc8d2dc, roughness: 0.9 });
    const matRoof = new THREE.MeshStandardMaterial({ color: f.greenRoof ? new THREE.Color(0x5f8f4e) : new THREE.Color(f.wall).multiplyScalar(0.82), roughness: 0.95 });
    const matYard = new THREE.MeshStandardMaterial({ color: 0x3e4955, roughness: 1 });
    const matGreen = new THREE.MeshStandardMaterial({ color: 0x4f7a45, roughness: 1 });
    const edge = new THREE.LineBasicMaterial({ color: 0x1b2633, transparent: true, opacity: 0.45 });
    matRoom.opacity = 0.85;
    const roomMat = matRoom, massMat = f.glass ? matGlass : matRoom;
    for (const l of lv) {
      const lg = new THREE.Group();
      lg.userData = { id: l.id, name: l.name, z: l.z_m, h: l.height_m };
      const on = (e) => (e.levels || [e.level]).includes(l.id);
      const els = (model.elements || []).filter(on);
      for (const e of els) {
        if (e.type === "mass") {
          // A mass spans its levels; draw its part on this level so levels can be hidden one by one.
          lg.add(prism(e.outline_m, l.z_m, l.height_m, massMat, edge));
        } else if (e.outdoor) {
          // yards, aprons, gardens: flat ground, not a room
          lg.add(prism(e.outline_m, l.z_m - 0.02, 0.12, /garden|park|courtyard|green/i.test(e.name) ? matGreen : matYard, null));
        } else if ((e.type === "room" || e.type === "zone") && e.full_height) {
          // one tall hall through several levels: draw it once, from its lowest level to the top of its highest
          const ls = (e.levels || []).map((id) => byId[id]).filter(Boolean).sort((a, c) => a.z_m - c.z_m);
          if (ls[0] && ls[0].id === l.id) {
            const top = ls[ls.length - 1].z_m + ls[ls.length - 1].height_m;
            lg.add(prism(e.outline_m, l.z_m, 0.3, matSlab, null));
            lg.add(prism(e.outline_m, l.z_m + 0.3, top - l.z_m - 0.3, roomMat, edge));
          }
        } else if (e.type === "room" || e.type === "zone") {
          lg.add(prism(e.outline_m, l.z_m, 0.3, matSlab, null));                      // floor
          lg.add(prism(e.outline_m, l.z_m + 0.3, l.height_m - 0.3, roomMat, edge));   // room volume
        } else if (e.type === "core") {
          lg.add(prism(e.outline_m, l.z_m, l.height_m, matCore, edge));
        } else if (e.type === "fixture" && e.outline_m) {
          lg.add(prism(e.outline_m, l.z_m + 0.3, Math.min(e.height_m || 1.1, l.height_m), matFix, edge));
        } else if (e.type === "wall" && e.line_m) {
          lg.add(wallBox(e.line_m, l.z_m, e.height_m || l.height_m, e.thickness_m || 0.3, matWall));
        } else if ((e.type === "door" || e.type === "opening") && e.line_m) {
          lg.add(wallBox(e.line_m, l.z_m + 0.3, Math.min(e.height_m || 3, l.height_m), 0.5, matDoor));
        }
      }
      g.add(lg);
      info.levels.push(lg);
    }
    // Roof: on top of every element's highest level.
    const tops = {};
    for (const e of model.elements || []) {
      if (!e.outline_m || e.outdoor || !["room", "zone", "core", "mass"].includes(e.type)) continue;
      const ls = (e.levels || [e.level]).map((id) => byId[id]).filter(Boolean);
      if (!ls.length) continue;
      const top = ls.reduce((a, c) => (c.z_m + c.height_m > a.z_m + a.height_m ? c : a));
      if (top.z_m + top.height_m <= 0) continue;
      (tops[top.id] = tops[top.id] || []).push(e);
    }
    for (const [id, list] of Object.entries(tops)) {
      const l = byId[id];
      const rg = new THREE.Group(); rg.userData = { roofOf: id };
      for (const e of list) rg.add(prism(e.outline_m, l.z_m + l.height_m, 0.4, matRoof, null));
      info.levels.find((x) => x.userData.id === id).add(rg);
    }
    return { group: g, info };
  }

  // ---- What to show: one building, or every building in a precinct or block.
  function scope() {
    const h = location.hash.replace(/^#\/?/, "");
    const [kind, a, b] = h.split("/").map(decodeURIComponent);
    if (kind === "building" && IX.buildings[a]) return { kind, title: IX.buildings[a].name, buildings: [IX.buildings[a]], precinct: IX.precincts[IX.buildings[a].precinct_uid] };
    if ((kind === "precinct" || kind === "street") && IX.precincts[a]) { const p = IX.precincts[a]; return { kind: "precinct", title: `${p.id} ${p.name}`, buildings: p.buildings || [], precinct: p, area: p.bbox_km }; }
    if (kind === "block" && IX.precincts[a]) {
      const p = IX.precincts[a], blk = (p.blocks || []).find((q) => q.id === b);
      return { kind, title: blk ? blk.name || blk.id : b, buildings: (p.buildings || []).filter((x) => (x.blocks || [x.block]).includes(b)), precinct: p, area: blk && blk.cell_km };
    }
    return null;
  }

  // ---- The viewer window.
  let state = null;
  async function open() {
    const sc = scope();
    if (!sc) return;
    close();
    const ov = document.createElement("div");
    ov.className = "v3d";
    ov.innerHTML = `<div class="v3d-bar"><b>3D · ${esc(sc.title)}</b>
      <span class="v3d-modes"><button data-m="orbit" class="on" title="Drag to turn, scroll or pinch to zoom, right-drag to pan">Orbit</button><button data-m="walk" title="W A S D or arrow keys to move, drag to look, Q and E to go down or up a level">Walk</button></span>
      <label class="v3d-cut" hidden>Show up to <select></select></label>
      <button class="v3d-x" title="Close the 3D view">✕</button></div>
      <div class="v3d-stage"><div class="v3d-msg">Loading 3D…</div></div>
      <div class="v3d-key"></div>
      <div class="v3d-walkpad" hidden><button data-k="f">▲</button><button data-k="l">◀</button><button data-k="b">▼</button><button data-k="r">▶</button><button data-k="u">E ↑</button><button data-k="d">Q ↓</button></div>`;
    document.body.append(ov);
    ov.querySelector(".v3d-x").onclick = close;
    state = { ov, keys: {}, stop: false };
    try { await lib(); } catch (e) { ov.querySelector(".v3d-msg").textContent = "Couldn't load the 3D library. Check the connection and try again."; return; }
    if (!state || state.ov !== ov) return;
    ov.querySelector(".v3d-msg").remove();
    const stage = ov.querySelector(".v3d-stage");
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(stage.clientWidth, stage.clientHeight);
    stage.append(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1a2c);
    scene.add(new THREE.HemisphereLight(0xdfefff, 0x2a3440, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-400, 800, -300); scene.add(sun);

    // Origin: the bow-port corner of the area (or of the building).
    const rects = sc.buildings.filter((b) => b.rect_km).map((b) => b.rect_km);
    const ar = sc.area || (rects.length ? [Math.min(...rects.map((r) => r[0])), Math.max(...rects.map((r) => r[1])), Math.min(...rects.map((r) => r[2])), Math.max(...rects.map((r) => r[3]))] : null);
    if (!ar) { stage.innerHTML = `<div class="v3d-msg">Nothing here has a footprint yet.</div>`; return; }
    const origin = [ar[0], ar[2]];
    const Lm = (ar[1] - ar[0]) * 1000, Wm = (ar[3] - ar[2]) * 1000;

    // Ground: the precinct or block area, and streets at their stored widths.
    const pad = sc.kind === "building" ? Math.max(Lm, Wm) * 0.25 : 0;
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(Lm + pad * 2, Wm + pad * 2), new THREE.MeshStandardMaterial({ color: 0x24303c, roughness: 1 }));
    ground.rotation.x = -Math.PI / 2; ground.position.set(Lm / 2, -0.05, Wm / 2); scene.add(ground);
    const p = sc.precinct;
    if (p && p.shape_km && sc.kind !== "building") {
      const pts = p.shape_km.map((q) => [(q[0] - origin[0]) * 1000, (q[1] - origin[1]) * 1000]);
      scene.add(prism(pts, -0.04, 0.02, new THREE.MeshStandardMaterial({ color: 0x2c3a47, roughness: 1 }), new THREE.LineBasicMaterial({ color: 0x6fd0ff })));
    }
    for (const st of (p && p.streets) || []) {
      if (!st.rect_km) continue;
      const q = st.rect_km.map((v, i) => (v - origin[i < 2 ? 0 : 1]) * 1000);
      const x0 = Math.max(q[0], -pad), x1 = Math.min(q[1], Lm + pad), y0 = Math.max(q[2], -pad), y1 = Math.min(q[3], Wm + pad);
      if (x1 <= x0 || y1 <= y0) continue;
      const sc2 = window.adxiStreetCat ? window.adxiStreetCat(st) : null;
      scene.add(prism([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], -0.02, 0.03, new THREE.MeshStandardMaterial({ color: sc2 ? new THREE.Color(sc2.fill) : 0x3b4450, roughness: 1 }), null));
    }

    // Buildings.
    const built = [];
    for (const b of sc.buildings) {
      if (!b.rect_km) continue;
      const model = window.adxiGetModel ? await window.adxiGetModel(b.uid) : null;
      if (!state || state.ov !== ov) return;
      const r = buildBuilding(b, model, origin);
      scene.add(r.group);
      built.push({ b, ...r });
    }

    // Level cut (one building with levels): hide the levels above the chosen one to look inside.
    const one = sc.kind === "building" && built[0] && built[0].info.levels.length ? built[0] : null;
    if (one) {
      const cut = ov.querySelector(".v3d-cut"), sel = cut.querySelector("select");
      cut.hidden = false;
      sel.innerHTML = `<option value="all">All levels</option>` + one.info.levels.slice().reverse().map((l) => `<option value="${esc(l.userData.id)}">${esc(String(l.userData.name || l.userData.id).split("·")[0].trim())}</option>`).join("");
      sel.onchange = () => {
        const z = sel.value === "all" ? Infinity : one.info.levels.find((l) => l.userData.id === sel.value).userData.z;
        one.info.levels.forEach((l) => { l.visible = l.userData.z <= z; l.children.forEach((c) => { if (c.userData.roofOf) c.visible = sel.value === "all" || l.userData.z < z; }); });
      };
    }

    // Key: what the colours mean, and what is missing.
    const designed = built.filter((x) => x.info.designed), notDesigned = built.filter((x) => !x.info.designed);
    const f = built[0] ? built[0].info.finishes : null;
    ov.querySelector(".v3d-key").innerHTML = [
      sc.kind === "building" && f ? (f.fromLook ? `Finishes from the Architecture "look": ${esc(f.names.join(", "))}.` : `No finishes in the Architecture "look" yet, so walls are plain grey.`) : "",
      designed.length ? `<span class="sw core"></span>stairs and lifts <span class="sw door"></span>doors` : "",
      notDesigned.length ? `Footprints are coloured by use, as on the map legend. <span class="sw none"></span>${notDesigned.length === built.length && sc.kind === "building" ? "No plan yet: footprint only" : `${notDesigned.length} of ${built.length} buildings have no plan yet (footprint only)`}${notDesigned.some((x) => x.info.placeholderHeight) ? ", flat where no height is set" : ""}.` : "",
    ].filter(Boolean).join(" · ");

    // Camera and controls.
    const size = Math.max(Lm, Wm, 50);
    const camera = new THREE.PerspectiveCamera(50, stage.clientWidth / stage.clientHeight, 0.3, size * 20);
    camera.position.set(-size * 0.55, size * 0.6, Wm + size * 0.55);
    const orbit = new Orbit(camera, renderer.domElement);
    orbit.target.set(Lm / 2, 0, Wm / 2);
    orbit.maxPolarAngle = Math.PI * 0.495;
    orbit.update();
    let mode = "orbit", yaw = 0, pitch = 0, floorIdx = 0;
    const floors = one ? one.info.levels.map((l) => l.userData.z) : [0];
    const startWalk = () => {
      floorIdx = Math.max(0, floors.findIndex((z) => z >= 0));
      camera.position.set(-8, floors[floorIdx] + 1.7, Wm / 2);
      yaw = Math.PI / 2; pitch = 0;
    };
    ov.querySelectorAll(".v3d-modes button").forEach((bt) => bt.onclick = () => {
      mode = bt.dataset.m;
      ov.querySelectorAll(".v3d-modes button").forEach((x) => x.classList.toggle("on", x === bt));
      orbit.enabled = mode === "orbit";
      ov.querySelector(".v3d-walkpad").hidden = mode !== "walk";
      if (mode === "walk") startWalk(); else { camera.position.set(-size * 0.55, size * 0.6, Wm + size * 0.55); orbit.update(); }
    });
    // Walk: drag to look.
    let drag = null;
    renderer.domElement.addEventListener("pointerdown", (e) => { if (mode === "walk") drag = [e.clientX, e.clientY]; });
    addEventListener("pointerup", () => (drag = null));
    renderer.domElement.addEventListener("pointermove", (e) => {
      if (mode !== "walk" || !drag) return;
      yaw -= (e.clientX - drag[0]) * 0.005; pitch = Math.max(-1.4, Math.min(1.4, pitch - (e.clientY - drag[1]) * 0.005));
      drag = [e.clientX, e.clientY];
    });
    const level = (d) => { floorIdx = Math.max(0, Math.min(floors.length - 1, floorIdx + d)); camera.position.y = floors[floorIdx] + 1.7; };
    state.onKey = (e, down) => {
      if (e.key === "Escape" && down) return close();
      const k = { w: "f", arrowup: "f", s: "b", arrowdown: "b", a: "l", arrowleft: "l", d: "r", arrowright: "r" }[e.key.toLowerCase()];
      if (k) { state.keys[k] = down; e.preventDefault(); }
      if (down && mode === "walk" && e.key.toLowerCase() === "e") level(1);
      if (down && mode === "walk" && e.key.toLowerCase() === "q") level(-1);
    };
    ov.querySelectorAll(".v3d-walkpad button").forEach((bt) => {
      const k = bt.dataset.k;
      if (k === "u" || k === "d") { bt.onclick = () => level(k === "u" ? 1 : -1); return; }
      bt.onpointerdown = () => (state.keys[k] = true);
      bt.onpointerup = bt.onpointerleave = () => (state.keys[k] = false);
    });
    state.resize = () => { renderer.setSize(stage.clientWidth, stage.clientHeight); camera.aspect = stage.clientWidth / stage.clientHeight; camera.updateProjectionMatrix(); };
    addEventListener("resize", state.resize);
    let last = performance.now();
    const tick = (now) => {
      if (!state || state.ov !== ov) { renderer.dispose(); return; }
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      if (mode === "walk") {
        const sp = 6 * dt * (state.keys.shift ? 3 : 1), fx = Math.sin(yaw), fz = Math.cos(yaw);
        if (state.keys.f) { camera.position.x += fx * sp; camera.position.z += fz * sp; }
        if (state.keys.b) { camera.position.x -= fx * sp; camera.position.z -= fz * sp; }
        if (state.keys.l) { camera.position.x += fz * sp; camera.position.z -= fx * sp; }
        if (state.keys.r) { camera.position.x -= fz * sp; camera.position.z += fx * sp; }
        camera.lookAt(camera.position.x + Math.sin(yaw) * Math.cos(pitch), camera.position.y + Math.sin(pitch), camera.position.z + Math.cos(yaw) * Math.cos(pitch));
      } else orbit.update();
      renderer.render(scene, camera);
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  function close() {
    if (!state) return;
    removeEventListener("resize", state.resize);
    state.ov.remove();
    state = null;
  }
  addEventListener("keydown", (e) => state && state.onKey && state.onKey(e, true));
  addEventListener("keyup", (e) => state && state.onKey && state.onKey(e, false));
  addEventListener("hashchange", close);

  // ---- The 3D button on building, block and precinct maps.
  function addButton() {
    const h = location.hash.replace(/^#\/?/, "");
    const kind = h.split("/")[0];
    const tools = document.querySelector(".mapwrap .maptools");
    if (!tools || tools.querySelector(".v3d-btn") || !["building", "block", "precinct", "street"].includes(kind)) return;
    const bt = document.createElement("button");
    bt.className = "v3d-btn";
    bt.textContent = "3D";
    bt.title = "See this in 3D, built from the stored plans and levels";
    bt.onclick = open;
    tools.prepend(bt);
  }
  new MutationObserver(addButton).observe(document.documentElement, { childList: true, subtree: true });
  window.adxi3D = { open, close };
})();
