/* Walk mode for the 3D view (Jordan, 27 Nov 2026: "I can walk through walls ... I can fly!", "WHERE IS THE DOOR?").
   You walk as a person: eyes 5 ft 7 in (1.7 m) up, 20 in (0.5 m) across the shoulders, walking 3.6 mph (1.6 m/s), running 11 mph (5 m/s).
   - Walls stop you. Doors and openings are gaps in the walls that you walk through. Windows are glass, so they stop you.
   - Gravity: you stand on a floor (or on the deck outside) and fall where there is none.
   - Stairs are ramps up their treads, so walking up a flight carries you up a floor. You can't walk under a flight.
   - Lifts: standing in a lift, up and down take you to the next floor it serves.
   - A building that isn't designed yet (footprint only) is a solid block.
   Plain maths, no three.js. The 3D view also uses cutWalls() to draw the doorways, so what you see is what stops you.
   Plan frame: metres from the lot's bow-port corner, x toward the stern, y toward starboard. In the 3D world plan x is
   world x and plan y is world z, plus each building's offset (gx, gz). */
(function (root) {
  const EYE = 1.7, RADIUS = 0.25, JAMB = 0.12, STEP = 0.5, HEAD = 2.03, GRAVITY = 9.8, WALK = 1.6, RUN = 5.0, SLAB = 0.3, CELL = 4;

  function inPoly(x, y, pts) {
    let ins = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) ins = !ins;
    }
    return ins;
  }
  function bbox(pts) {
    let a = Infinity, b = -Infinity, c = Infinity, d = -Infinity;
    for (const p of pts) { a = Math.min(a, p[0]); b = Math.max(b, p[0]); c = Math.min(c, p[1]); d = Math.max(d, p[1]); }
    return [a, b, c, d];
  }
  // About how wide a ring is: twice its area over its perimeter (a long thin sliver gives its width).
  function holeWidth(pts) {
    let a = 0, per = 0;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      a += pts[j][0] * pts[i][1] - pts[i][0] * pts[j][1];
      per += Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]);
    }
    return per ? Math.abs(a) / per : 0;
  }
  const inBox = (bx, x, y, pad) => x >= bx[0] - pad && x <= bx[1] + pad && y >= bx[2] - pad && y <= bx[3] + pad;

  // A uniform grid of line segments {ax, ay, bx, by, t}, for finding the walls near a point quickly.
  function gridAdd(g, s) {
    const x0 = Math.floor((Math.min(s.ax, s.bx) - s.t) / CELL), x1 = Math.floor((Math.max(s.ax, s.bx) + s.t) / CELL);
    const y0 = Math.floor((Math.min(s.ay, s.by) - s.t) / CELL), y1 = Math.floor((Math.max(s.ay, s.by) + s.t) / CELL);
    for (let i = x0; i <= x1; i++) for (let j = y0; j <= y1; j++) {
      const k = i + "," + j;
      if (!g.has(k)) g.set(k, []);
      g.get(k).push(s);
    }
  }
  function gridNear(g, x, y, r) {
    const out = new Set();
    for (let a = Math.floor((x - r) / CELL); a <= Math.floor((x + r) / CELL); a++)
      for (let b = Math.floor((y - r) / CELL); b <= Math.floor((y + r) / CELL); b++) for (const s of g.get(a + "," + b) || []) out.add(s);
    return out;
  }

  // One wall line with the doors and openings along it cut out: the solid pieces, and the gaps (each with its door).
  function cutDoors(s, doors) {
    const dx = s.bx - s.ax, dy = s.by - s.ay, L = Math.hypot(dx, dy);
    if (L < 1e-6) return { pieces: [], gaps: [] };
    const ux = dx / L, uy = dy / L, gaps = [];
    for (const d of doors) {
      // the door lies along this wall: both its ends sit within the wall's thickness of the wall's centre line
      const off = (px, py) => Math.abs((px - s.ax) * uy - (py - s.ay) * ux);
      if (off(d.ax, d.ay) > s.t / 2 + 0.15 || off(d.bx, d.by) > s.t / 2 + 0.15) continue;
      const p0 = (d.ax - s.ax) * ux + (d.ay - s.ay) * uy, p1 = (d.bx - s.ax) * ux + (d.by - s.ay) * uy;
      const lo = Math.max(0, Math.min(p0, p1)), hi = Math.min(L, Math.max(p0, p1));
      if (hi - lo > 0.3) gaps.push({ lo, hi, door: d });
    }
    if (!gaps.length) return { pieces: [s], gaps: [] };
    gaps.sort((a, b) => a.lo - b.lo);
    const pieces = [], at = (u) => [s.ax + ux * u, s.ay + uy * u];
    let u = 0;
    for (const g of gaps) {
      if (g.lo - u > 0.05) { const a = at(u), b = at(g.lo); pieces.push(Object.assign({}, s, { ax: a[0], ay: a[1], bx: b[0], by: b[1] })); }
      u = Math.max(u, g.hi);
    }
    if (L - u > 0.05) { const a = at(u); pieces.push(Object.assign({}, s, { ax: a[0], ay: a[1] })); }
    return {
      pieces,
      gaps: gaps.map((g) => { const a = at(g.lo), b = at(g.hi); return { ax: a[0], ay: a[1], bx: b[0], by: b[1], t: s.t, wallH: s.h, door: g.door }; }),
    };
  }

  // Every floor's walls with their doorways cut out, from a model@2 plan (with fabric). For each level id:
  // {walls: [{ax, ay, bx, by, t, h}], gaps: [{ax, ay, bx, by, t, wallH, door}], doors: [{ax, ay, bx, by, h, name, kind}]}.
  function cutWalls(model) {
    const out = {}, lvl = (id) => (out[id] = out[id] || { walls: [], gaps: [], doors: [] });
    const raw = {};
    for (const e of model.elements || []) {
      if ((e.type === "door" || e.type === "opening") && e.line_m) {
        const p = e.line_m[0], q = e.line_m[e.line_m.length - 1];
        lvl(e.level).doors.push({ ax: p[0], ay: p[1], bx: q[0], by: q[1], h: e.height_m || 2.1, name: e.name || "", kind: e.type, t: 0.6 });
      } else if (e.type === "walls") {
        for (const q of e.lines_m) (raw[e.level] = raw[e.level] || []).push({ ax: q[0], ay: q[1], bx: q[2], by: q[3], t: e.thickness_m || 0.2, h: e.height_m, kind: e.kind });
      }
    }
    for (const id of Object.keys(raw)) {
      const L = lvl(id), dg = new Map();
      for (const d of L.doors) gridAdd(dg, d);
      for (const s of raw[id]) {
        const len = Math.hypot(s.bx - s.ax, s.by - s.ay), near = new Set();
        for (let k = 0; k <= Math.ceil(len / CELL); k++) {
          const f = Math.min(1, (k * CELL) / (len || 1));
          for (const d of gridNear(dg, s.ax + (s.bx - s.ax) * f, s.ay + (s.by - s.ay) * f, 1)) near.add(d);
        }
        const c = cutDoors(s, near);
        L.walls.push(...c.pieces);
        L.gaps.push(...c.gaps);
      }
    }
    return out;
  }

  // The height of a stair's surface under (x, y): one value per half-turn it makes (stacked when a tall floor's stair
  // turns more than once). Each turn: a landing, a flight up along the outline's long side, a half landing, a flight back.
  function stairHeights(st, x, y) {
    const o = st.outline_m;
    const ux = o[1][0] - o[0][0], uy = o[1][1] - o[0][1], vx = o[3][0] - o[0][0], vy = o[3][1] - o[0][1];
    const Lu = Math.hypot(ux, uy), Lv = Math.hypot(vx, vy);
    if (!Lu || !Lv) return [];
    const s = ((x - o[0][0]) * ux + (y - o[0][1]) * uy) / Lu, t = ((x - o[0][0]) * vx + (y - o[0][1]) * vy) / Lv;
    if (s < 0 || s > Lu || t < 0 || t > Lv) return [];
    const turns = st.turns || 1, n = Math.ceil(st.risers / turns), r = st.riser_m, tr = st.tread_m, land = st.landing_m;
    const out = [];
    for (let k = 0, done = 0; k < turns && done < st.risers; k++) {
      const m = Math.min(n, st.risers - done), up = Math.ceil(m / 2), base = st.z0 + done * r;
      if (t < Lv / 2) out.push(base + Math.max(0, Math.min(up, (s - land) / tr)) * r);                    // flight up
      else out.push(base + (up + Math.max(0, Math.min(m - up, (Lu - land - s) / tr))) * r);              // flight back
      done += m;
    }
    return out;
  }

  // Everything a walker bumps into or stands on, for one building.
  function building(b, model, gx, gz) {
    const W = { gx, gz, levels: [], stairs: [], lifts: [], solid: [], entrances: [], box: null };
    const r = b.rect_km;
    if (!model || !model.fabric || !model.levels || !model.levels.length) {
      const loc = (q) => [(q[0] - r[0]) * 1000, (q[1] - r[2]) * 1000];
      W.solid = b.outline_km && !b.bays_km ? b.outline_km.map((o) => o.map(loc)) : (b.bays_km || [r]).map((q) => [[q[0], q[2]], [q[1], q[2]], [q[1], q[3]], [q[0], q[3]]].map(loc));
      W.solidH = typeof b.height_m === "number" ? b.height_m : 3;
      W.box = bbox(W.solid.flat());
      return W;
    }
    const lv = model.levels.slice().sort((a, c) => a.z_m - c.z_m), byId = {};
    for (const l of lv) {
      const L = { id: l.id, name: l.name || l.id, z: l.z_m, top: l.z_m + SLAB, h: l.height_m, slabs: [], walls: new Map() };
      byId[l.id] = L;
      W.levels.push(L);
    }
    const cut = cutWalls(model);
    for (const [id, c] of Object.entries(cut)) {
      if (!byId[id]) continue;
      for (const s of c.walls) gridAdd(byId[id].walls, s);
      for (const d of c.doors) if (/entrance|outside/i.test(d.name)) W.entrances.push(Object.assign({ level: id }, d));
    }
    for (const e of model.elements || []) {
      // a hole is a stairwell, a lift shaft or a courtyard; a sliver left where two rooms almost meet is floor
      if (e.type === "slab" && byId[e.level]) byId[e.level].slabs.push({ outer: e.outline_m, holes: (e.holes_m || []).filter((h) => holeWidth(h) >= 0.5), box: bbox(e.outline_m) });
      else if (e.type === "stair" && byId[e.level]) W.stairs.push(Object.assign({}, e, { z0: byId[e.level].top, box: bbox(e.outline_m) }));
      else if (e.type === "lift" && e.levels) W.lifts.push({ outline: e.outline_m, box: bbox(e.outline_m), tops: e.levels.map((id) => byId[id] && byId[id].top).filter((v) => v !== undefined).sort((a, c) => a - c) });
    }
    const all = [];
    for (const L of W.levels) for (const sl of L.slabs) all.push(...sl.outer);
    W.box = all.length ? bbox(all) : [0, (r[1] - r[0]) * 1000, 0, (r[3] - r[2]) * 1000];
    return W;
  }

  // The surfaces under a point of building W (plan coordinates): floor heights, and whether a floor covers it at all.
  function surfaces(W, x, y) {
    const out = [];
    let covered = false;
    if (!inBox(W.box, x, y, 0.5)) return { heights: out, covered };
    for (const L of W.levels) for (const sl of L.slabs) {
      if (!inBox(sl.box, x, y, 0) || !inPoly(x, y, sl.outer)) continue;
      covered = true;
      if (!sl.holes.some((h) => inPoly(x, y, h))) out.push(L.top);
    }
    for (const st of W.stairs) {
      if (!inBox(st.box, x, y, 0)) continue;
      const hs = stairHeights(st, x, y);
      if (hs.length) { covered = true; out.push(...hs); }
    }
    for (const lf of W.lifts) {
      if (!inBox(lf.box, x, y, 0) || !inPoly(x, y, lf.outline)) continue;
      covered = true;
      out.push(...lf.tops);
    }
    return { heights: out, covered };
  }

  function make(list) {
    // list: [{b, model, gx, gz}]
    const ws = list.map((x) => building(x.b, x.model, x.gx, x.gz));
    const me = { x: 0, z: 0, feet: 0, vy: 0, yaw: 0, pitch: 0 };
    const near = (X, Z, pad) => ws.filter((W) => W.box && inBox(W.box, X - W.gx, Z - W.gz, pad));

    // All floor heights under a point, the deck outside included where no building floor covers it.
    function heightsAt(X, Z) {
      const hs = [];
      let covered = false;
      for (const W of near(X, Z, 0.5)) {
        const s = surfaces(W, X - W.gx, Z - W.gz);
        covered = covered || s.covered;
        hs.push(...s.heights);
      }
      if (!covered) hs.push(0);
      return hs;
    }
    // The floor you stand on from feet height: the highest surface at most one step above your feet.
    function floorAt(hs, feet) {
      let best = -Infinity;
      for (const h of hs) if (h <= feet + STEP && h > best) best = h;
      return best;
    }
    // Something overhead too low to walk under (the underside of a flight, a landing).
    const lowCeiling = (hs, feet) => hs.some((h) => h > feet + STEP && h < feet + HEAD);
    function levelOf(W, feet) {
      let L = W.levels[0];
      for (const l of W.levels) if (l.top - 0.6 <= feet) L = l;
      return L;
    }
    // Push the walker out of every wall nearby (on the floor where their feet are) and out of solid blocks.
    function collide(X, Z, feet) {
      for (let it = 0; it < 4; it++) {
        let moved = false;
        for (const W of near(X, Z, 1)) {
          if (W.solid.length) {
            if (feet < W.solidH) for (const pts of W.solid) if (inPoly(X - W.gx, Z - W.gz, pts) || edgeDist(X - W.gx, Z - W.gz, pts) < RADIUS) {
              const p = pushOut(X - W.gx, Z - W.gz, pts);
              X = p[0] + W.gx; Z = p[1] + W.gz; moved = true;
            }
            continue;
          }
          const L = levelOf(W, feet), x = X - W.gx, y = Z - W.gz;
          for (const s of gridNear(L.walls, x, y, RADIUS + 0.5)) {
            const dx = s.bx - s.ax, dy = s.by - s.ay, l2 = dx * dx + dy * dy;
            const f = l2 ? Math.max(0, Math.min(1, ((x - s.ax) * dx + (y - s.ay) * dy) / l2)) : 0;
            let nx = x - (s.ax + dx * f), ny = y - (s.ay + dy * f);
            // the end of a wall (a door jamb) is passed closer, as a person turns a shoulder going through a doorway
            const d = Math.hypot(nx, ny), min = (f <= 0 || f >= 1 ? JAMB : RADIUS) + s.t / 2;
            if (d >= min) continue;
            if (d < 1e-6) { const l = Math.sqrt(l2) || 1; nx = -dy / l; ny = dx / l; } else { nx /= d; ny /= d; }
            X += nx * (min - d); Z += ny * (min - d);
            moved = true;
            break;   // re-measure from the new spot
          }
        }
        if (!moved) break;
      }
      return [X, Z];
    }
    function edgeDist(x, y, pts) {
      let best = Infinity;
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], c = pts[(i + 1) % pts.length], dx = c[0] - a[0], dy = c[1] - a[1], l2 = dx * dx + dy * dy || 1;
        const f = Math.max(0, Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / l2));
        best = Math.min(best, Math.hypot(x - a[0] - dx * f, y - a[1] - dy * f));
      }
      return best;
    }
    function pushOut(x, y, pts) {
      let best = null;
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], c = pts[(i + 1) % pts.length], dx = c[0] - a[0], dy = c[1] - a[1], l2 = dx * dx + dy * dy || 1;
        const f = Math.max(0, Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / l2)), px = a[0] + dx * f, py = a[1] + dy * f;
        const d = Math.hypot(x - px, y - py);
        if (!best || d < best.d) best = { d, px, py };
      }
      // outward: away from the inside of the shape
      let nx = x - best.px, ny = y - best.py;
      const n = Math.hypot(nx, ny);
      if (n < 1e-6) return [x, y];
      nx /= n; ny /= n;
      if (inPoly(x, y, pts)) { nx = -nx; ny = -ny; }
      return [best.px + nx * (RADIUS + 0.02), best.py + ny * (RADIUS + 0.02)];
    }
    function liftHere() {
      for (const W of near(me.x, me.z, 0)) for (const lf of W.lifts) if (inPoly(me.x - W.gx, me.z - W.gz, lf.outline)) return lf;
      return null;
    }

    return {
      me, buildings: ws, EYE,
      // Stand at (X, Z) on the lowest floor there at or above the deck, facing yaw (0 = +z, the plan's y).
      place(X, Z, yaw) {
        const hs = heightsAt(X, Z).filter((h) => h >= -0.01);
        Object.assign(me, { x: X, z: Z, yaw: yaw || 0, pitch: 0, vy: 0, feet: hs.length ? Math.min(...hs) : 0 });
      },
      // The start: on the deck 20 ft (6 m) outside a ground-floor entrance, facing it. Returns the entrance, or null.
      start(fallback) {
        for (const W of ws) {
          const ents = W.entrances.filter((d) => { const L = W.levels.find((l) => l.id === d.level); return L && L.z >= -0.01 && L.z < 1; });
          ents.sort((a, c) => (/entrance/i.test(c.name) ? 1 : 0) - (/entrance/i.test(a.name) ? 1 : 0));
          for (const d of ents) {
            const mx = (d.ax + d.bx) / 2, my = (d.ay + d.by) / 2, L = Math.hypot(d.bx - d.ax, d.by - d.ay) || 1;
            const nx = -(d.by - d.ay) / L, ny = (d.bx - d.ax) / L;
            for (const sg of [1, -1]) {
              const px = mx + nx * 6 * sg, py = my + ny * 6 * sg;
              if (surfaces(W, px, py).covered) continue;   // that side is indoors
              this.place(px + W.gx, py + W.gz, Math.atan2(-nx * sg, -ny * sg));
              return Object.assign({ x: mx + W.gx, z: my + W.gz }, d);
            }
          }
        }
        this.place(fallback[0], fallback[1], fallback[2]);
        return null;
      },
      // One frame. keys: {f, b, l, r, run}. Moves in small steps so nobody slips through a wall.
      step(dt, keys) {
        dt = Math.min(dt, 0.1);
        const fx = Math.sin(me.yaw), fz = Math.cos(me.yaw);
        let mx = 0, mz = 0;
        if (keys.f) { mx += fx; mz += fz; }
        if (keys.b) { mx -= fx; mz -= fz; }
        if (keys.l) { mx += fz; mz -= fx; }
        if (keys.r) { mx -= fz; mz += fx; }
        const m = Math.hypot(mx, mz);
        if (m > 0) {
          const dist = (keys.run ? RUN : WALK) * dt, n = Math.max(1, Math.ceil(dist / 0.08));
          for (let i = 0; i < n; i++) {
            let X = me.x + (mx / m) * (dist / n), Z = me.z + (mz / m) * (dist / n);
            [X, Z] = collide(X, Z, me.feet);
            const hs = heightsAt(X, Z), f = floorAt(hs, me.feet);
            if (f === -Infinity || lowCeiling(hs, Math.max(me.feet, f))) break;   // nothing to stand on, or no headroom
            me.x = X; me.z = Z;
            if (f > me.feet) { me.feet = f; me.vy = 0; }                          // a step or a stair tread: up you go
          }
        }
        const f = floorAt(heightsAt(me.x, me.z), me.feet);
        if (f < me.feet - 1e-3) {                                                 // nothing under your feet: fall
          me.vy -= GRAVITY * dt;
          me.feet = Math.max(f, me.feet + me.vy * dt);
          if (me.feet <= f + 1e-6) me.vy = 0;
        } else me.vy = 0;
        return me;
      },
      // Ride a lift one floor up (+1) or down (-1). False when you aren't standing in a lift.
      lift(d) {
        const lf = liftHere();
        if (!lf || !lf.tops.length) return false;
        let i = 0;
        lf.tops.forEach((t, k) => { if (Math.abs(t - me.feet) < Math.abs(lf.tops[i] - me.feet)) i = k; });
        me.feet = lf.tops[Math.max(0, Math.min(lf.tops.length - 1, i + d))];
        me.vy = 0;
        return true;
      },
      inLift: () => !!liftHere(),
      // Could someone stand at (X, Z) with feet at this height? (For route finding and tests.)
      free(X, Z, feet) {
        const [x, z] = collide(X, Z, feet);
        if (Math.hypot(x - X, z - Z) > 1e-6) return false;
        const hs = heightsAt(X, Z), f = floorAt(hs, feet);
        return f > feet - STEP && !lowCeiling(hs, f);
      },
      eye: () => me.feet + EYE,
      // The floor you are on, when you are inside a designed building.
      where() {
        for (const W of near(me.x, me.z, 0)) if (W.levels.length && surfaces(W, me.x - W.gx, me.z - W.gz).covered) return levelOf(W, me.feet);
        return null;
      },
    };
  }

  const api = { make, building, surfaces, stairHeights, cutDoors, cutWalls, inPoly, holeWidth, EYE, RADIUS, WALK, RUN };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.adxiWalk = api;
})(typeof window !== "undefined" ? window : globalThis);
