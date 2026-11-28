/* ADXI: Invicta: how the 3D view looks (Jordan, 28 Nov 2026: "make the 3D view look realistic").
   This file only changes how things are drawn: materials, light, shadows and the camera finish. It never changes
   what is drawn; the shapes still come from the stored plans (web/view3d.js) and Walk mode (web/walk.js) is untouched.

   Three looks, picked in the 3D bar and remembered on this device:
   - Realistic: textured materials, daylight from the deck's ceiling, reflections, soft shadows, ambient occlusion
     (dark corners where surfaces meet), distance haze, a glow on lights, filmic tone mapping. For laptops and PCs.
   - Balanced: the same, without ambient occlusion and at a lower resolution, so it stays smooth on phones and tablets.
     Phones and tablets start on this one.
   - Simple: the old flat look. Fastest; use it if a device struggles.

   Textures are drawn by this file (no image files, so nothing to license and nothing to download). They are mapped by
   world position in metres (triplanar), so a stone panel is the same size on every wall, box and stair.
   Finishes come only from words in the building's "look" text (see FINISH in view3d.js); nothing is invented. Lights
   that the look text names (for example "navigation lights") are drawn where the plan allows; see navLights(). */
(function () {
  "use strict";
  const KEY = "adxi.look";
  const V = "0.170.0";
  const LOOKS = { real: "Realistic", balanced: "Balanced (phones)", simple: "Simple" };
  const smallDevice = () => matchMedia("(pointer: coarse)").matches || Math.min(screen.width, screen.height) < 820;
  function current() {
    let v = null;
    try { v = localStorage.getItem(KEY); } catch (e) { /* private mode */ }
    return LOOKS[v] ? v : smallDevice() ? "balanced" : "real";
  }
  function set(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode */ } }
  function tier(v) {
    if (v === "simple") return { name: v, simple: true };
    const real = v === "real";
    return { name: v, simple: false, pixelRatio: Math.min(devicePixelRatio, real ? 2 : 1.5), shadowSize: real ? 2048 : 1024,
      ao: real, bloom: true, texSize: real ? 512 : 256, samples: 4, physicalGlass: real };
  }

  // ---- Post-processing modules, loaded the first time a realistic look is opened (same three.js version as view3d.js).
  let P = null;
  async function lib() {
    if (P) return P;
    const u = (p) => `https://esm.sh/three@${V}/examples/jsm/${p}`;
    const [ec, rp, gt, ub, op] = await Promise.all([
      import(u("postprocessing/EffectComposer.js")), import(u("postprocessing/RenderPass.js")), import(u("postprocessing/GTAOPass.js")),
      import(u("postprocessing/UnrealBloomPass.js")), import(u("postprocessing/OutputPass.js"))]);
    P = { EffectComposer: ec.EffectComposer, RenderPass: rp.RenderPass, GTAOPass: gt.GTAOPass, UnrealBloomPass: ub.UnrealBloomPass, OutputPass: op.OutputPass };
    return P;
  }

  // ---- Procedural textures. One RGBA texture per pattern: R = colour variation (0.5 = no change), G = roughness
  // variation, B = height (joints and grooves are low, used for bump). All tile seamlessly.
  function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
  function noiseField(n, cells, seed) {
    // tileable value noise, a few octaves
    const out = new Float32Array(n * n), r = rng(seed);
    let amp = 1, total = 0;
    for (let o = 0; o < 4; o++, cells *= 2, amp *= 0.5) {
      const g = new Float32Array(cells * cells).map(() => r());
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const fx = (x / n) * cells, fy = (y / n) * cells, x0 = Math.floor(fx), y0 = Math.floor(fy);
        const tx = fx - x0, ty = fy - y0, sx = tx * tx * (3 - 2 * tx), sy = ty * ty * (3 - 2 * ty);
        const at = (i, j) => g[((j % cells + cells) % cells) * cells + ((i % cells + cells) % cells)];
        const a = at(x0, y0) + (at(x0 + 1, y0) - at(x0, y0)) * sx, b = at(x0, y0 + 1) + (at(x0 + 1, y0 + 1) - at(x0, y0 + 1)) * sx;
        out[y * n + x] += (a + (b - a) * sy) * amp;
      }
      total += amp;
    }
    for (let i = 0; i < out.length; i++) out[i] /= total;
    return out;
  }
  // Each pattern: the tile's size in metres [u, v] and a function giving [colour, roughness, height] at a pixel.
  const PATTERNS = {
    // pale stone or concrete cladding panels, 5 x 2.5 ft (1.5 x 0.75 m), with 3/8 in (10 mm) joints, every other row offset
    panel: { tile: [3, 1.5], draw(n, N, M) {
      const rows = 2, cols = 2, j = Math.max(1, Math.round(n * 0.006));
      const tint = rng(7), tints = Array.from({ length: rows * cols * 2 }, () => (tint() - 0.5) * 0.08);
      return (x, y) => {
        const row = Math.floor((y / n) * rows), off = row % 2 ? n / (cols * 2) : 0, xx = (x + off) % n, col = Math.floor((xx / n) * cols);
        const ly = y % (n / rows), lx = xx % (n / cols), joint = ly < j || lx < j;
        const v = N[y * n + x], m = M[y * n + x];
        return joint ? [0.33, 0.85, 0.05] : [0.5 + tints[row * cols * 2 + col] + (v - 0.5) * 0.18 + (m - 0.5) * 0.06, 0.45 + (m - 0.5) * 0.5, 0.95 - (v - 0.5) * 0.06];
      };
    } },
    // brick, 8 x 2 2/3 in (203 x 68 mm) running bond with mortar joints
    brick: { tile: [0.86, 0.6], draw(n, N) {
      const rows = 8, cols = 4, j = Math.max(1, Math.round(n * 0.012)), tint = rng(11), tints = Array.from({ length: rows * cols }, () => (tint() - 0.5) * 0.25);
      return (x, y) => {
        const row = Math.floor((y / n) * rows), off = row % 2 ? n / (cols * 2) : 0, xx = (x + off) % n, col = Math.floor((xx / n) * cols);
        const joint = y % (n / rows) < j || xx % (n / cols) < j, v = N[y * n + x];
        return joint ? [0.62, 0.9, 0.1] : [0.5 + tints[row * cols + col] + (v - 0.5) * 0.25, 0.7 + (v - 0.5) * 0.3, 0.9];
      };
    } },
    // timber boards, 6 in (150 mm) wide, with grain
    plank: { tile: [2.4, 0.6], draw(n, N) {
      const rows = 4, j = Math.max(1, Math.round(n * 0.004)), tint = rng(5), tints = Array.from({ length: rows }, () => (tint() - 0.5) * 0.2);
      return (x, y) => {
        const row = Math.floor((y / n) * rows), joint = y % (n / rows) < j, v = N[y * n + x];
        const grain = Math.sin((y / n) * 160 + v * 9) * 0.06;
        return joint ? [0.3, 0.8, 0.1] : [0.5 + tints[row] + grain + (v - 0.5) * 0.15, 0.6 + (v - 0.5) * 0.3, 0.9];
      };
    } },
    // metal cladding: brushed panels 4 x 10 ft (1.2 x 3 m) with fine seams
    metal: { tile: [2.4, 3], draw(n, N, M) {
      const j = Math.max(1, Math.round(n * 0.003));
      return (x, y) => {
        const joint = x % (n / 2) < j || y < j, brush = N[(y * 7) % n * n + x] - 0.5;
        return joint ? [0.35, 0.6, 0.1] : [0.5 + brush * 0.08 + (M[y * n + x] - 0.5) * 0.08, 0.35 + brush * 0.2, 0.9];
      };
    } },
    // void ore armour plates (design reference: dark gunmetal-blue plates with a bronze sheen), 6 x 3 m, deep seams
    plate: { tile: [6, 3], draw(n, N, M) {
      const j = Math.max(2, Math.round(n * 0.008)), tint = rng(3), tints = Array.from({ length: 8 }, () => (tint() - 0.5) * 0.1);
      return (x, y) => {
        const row = Math.floor((y / n) * 2), off = row % 2 ? n / 4 : 0, xx = (x + off) % n, col = Math.floor((xx / n) * 2);
        const joint = y % (n / 2) < j || xx % (n / 2) < j, v = N[y * n + x];
        return joint ? [0.2, 0.7, 0.0] : [0.5 + tints[row * 2 + col] + (v - 0.5) * 0.1, 0.4 + (M[y * n + x] - 0.5) * 0.4, 0.95];
      };
    } },
    // cast concrete: no joints, mottled, a few pores
    concrete: { tile: [4, 4], draw(n, N, M) {
      const pores = rng(13);
      const pit = new Uint8Array(n * n); for (let i = 0; i < n * n * 0.004; i++) pit[Math.floor(pores() * n * n)] = 1;
      return (x, y) => {
        const v = N[y * n + x], m = M[y * n + x], p = pit[y * n + x];
        return [0.5 + (v - 0.5) * 0.28 + (m - 0.5) * 0.12 - p * 0.15, 0.75 + (m - 0.5) * 0.4, p ? 0.4 : 0.9 + (v - 0.5) * 0.05];
      };
    } },
    // paving slabs, 10 x 10 ft (3 x 3 m), for the deck floor, yards and plazas
    paving: { tile: [6, 6], draw(n, N, M) {
      const j = Math.max(1, Math.round(n * 0.004)), tint = rng(17), tints = Array.from({ length: 4 }, () => (tint() - 0.5) * 0.1);
      return (x, y) => {
        const c = Math.floor((x / n) * 2) + 2 * Math.floor((y / n) * 2), joint = x % (n / 2) < j || y % (n / 2) < j;
        const v = N[y * n + x], m = M[y * n + x];
        return joint ? [0.3, 0.9, 0.1] : [0.5 + tints[c] + (v - 0.5) * 0.25, 0.8 + (m - 0.5) * 0.3, 0.9];
      };
    } },
    // road surface: fine aggregate
    asphalt: { tile: [3, 3], draw(n, N, M) {
      const r = rng(19);
      return (x, y) => { const s = r(); return [0.5 + (N[y * n + x] - 0.5) * 0.2 + (s - 0.5) * 0.12, 0.85 + (M[y * n + x] - 0.5) * 0.2, 0.85 + s * 0.1]; };
    } },
    // lawn
    grass: { tile: [3, 3], draw(n, N, M) {
      const r = rng(23);
      return (x, y) => { const s = r(); return [0.5 + (N[y * n + x] - 0.5) * 0.35 + (s - 0.5) * 0.18, 0.95, 0.6 + s * 0.4]; };
    } },
  };
  const texCache = {};
  function texture(THREE, name, size, renderer) {
    const k = name + size;
    if (texCache[k]) return texCache[k];
    const pat = PATTERNS[name], n = size;
    const N = noiseField(n, 4, name.length * 31 + 1), M = noiseField(n, 2, name.length * 17 + 5);
    const at = pat.draw(n, N, M), data = new Uint8Array(n * n * 4);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const [c, r, h] = at(x, y), i = (y * n + x) * 4;
      data[i] = Math.max(0, Math.min(255, c * 255)); data[i + 1] = Math.max(0, Math.min(255, r * 255)); data[i + 2] = Math.max(0, Math.min(255, h * 255)); data[i + 3] = 255;
    }
    const t = new THREE.DataTexture(data, n, n, THREE.RGBAFormat);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;
    t.anisotropy = renderer ? Math.min(8, renderer.capabilities.getMaxAnisotropy()) : 1;
    t.needsUpdate = true;
    return (texCache[k] = { tex: t, tile: pat.tile });
  }

  // ---- Triplanar mapping: every textured material samples its pattern by world position, so instanced boxes
  // (walls, panes, treads) and extruded plans all get panels at their real size.
  const VERT_DECL = "varying vec3 vTpPos;\nvarying vec3 vTpNrm;\n";
  function triplanar(THREE, mat, tx, opts) {
    const o = Object.assign({ colour: 1, rough: 1, bump: 0.01 }, opts || {});
    mat.userData.tp = { tex: tx.tex, scale: new THREE.Vector2(1 / tx.tile[0], 1 / tx.tile[1]), o };
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.tpMap = { value: tx.tex };
      sh.uniforms.tpScale = { value: mat.userData.tp.scale };
      sh.uniforms.tpAmt = { value: new THREE.Vector3(o.colour, o.rough, o.bump) };
      sh.vertexShader = VERT_DECL + sh.vertexShader.replace("#include <worldpos_vertex>", `#include <worldpos_vertex>
        vec4 tpW = vec4(transformed, 1.0);
        vec3 tpN = objectNormal;
        #ifdef USE_INSTANCING
          tpW = instanceMatrix * tpW;
          tpN = mat3(instanceMatrix) * tpN;
        #endif
        vTpPos = (modelMatrix * tpW).xyz;
        vTpNrm = normalize(mat3(modelMatrix) * tpN);`);
      sh.fragmentShader = VERT_DECL + `uniform sampler2D tpMap; uniform vec2 tpScale; uniform vec3 tpAmt;
        vec3 tpPerturb(vec3 p, vec3 n, vec2 dH, float fd) {
          vec3 sx = dFdx(p), sy = dFdy(p), r1 = cross(sy, n), r2 = cross(n, sx);
          float det = dot(sx, r1) * fd;
          vec3 g = sign(det) * (dH.x * r1 + dH.y * r2), q = abs(det) * n - g;
          return dot(q, q) > 1e-20 ? normalize(q) : n;   // a face thinner than a pixel: no bump (avoids a broken normal)
        }
        vec4 tpSample(vec3 p, vec3 nw, vec2 s) {
          vec3 b = pow(abs(nw), vec3(4.0)); b /= (b.x + b.y + b.z + 1e-5);
          return texture2D(tpMap, p.zy * s) * b.x + texture2D(tpMap, p.xz * s.xx) * b.y + texture2D(tpMap, p.xy * s) * b.z;
        }
        ` + sh.fragmentShader
        .replace("#include <map_fragment>", `#include <map_fragment>
          vec4 tpS = tpSample(vTpPos, vTpNrm, tpScale);
          float tpMacro = tpSample(vTpPos, vTpNrm, tpScale * 0.071).r;   // a second, much larger scale so the tiling doesn't show
          diffuseColor.rgb *= clamp(1.0 + ((tpS.r - 0.5) * 2.0 + (tpMacro - 0.5) * 0.8) * tpAmt.x, 0.2, 1.8);`)
        .replace("#include <roughnessmap_fragment>", `#include <roughnessmap_fragment>
          roughnessFactor = clamp(roughnessFactor * mix(1.0, 0.4 + tpS.g * 1.2, tpAmt.y), 0.03, 1.0);`)
        .replace("#include <normal_fragment_maps>", `#include <normal_fragment_maps>
          // bump fades out with distance and at grazing angles, where it would only sparkle
          float tpFade = (1.0 - smoothstep(40.0, 220.0, length(vViewPosition))) * smoothstep(0.08, 0.35, abs(dot(normal, normalize(vViewPosition))));
          normal = tpPerturb(-vViewPosition, normal, clamp(vec2(dFdx(tpS.b), dFdy(tpS.b)), -0.25, 0.25) * tpAmt.z * tpFade, faceDirection);`);
    };
    mat.customProgramCacheKey = () => "tp";
    mat.needsUpdate = true;
    return mat;
  }

  // ---- Which pattern a finish uses.
  const PATTERN_OF = { sandstone: "panel", limestone: "panel", marble: "panel", stone: "panel", concrete: "concrete", brick: "brick",
    timber: "plank", metal: "metal", white: "concrete", "void ore": "plate" };

  // ---- Dress a building's materials (view3d.js makes them; this turns them into textured, physically based ones).
  // m: { wall, room, glass, core, slab, frame, entrance, lift, fix, roof, yard, green, rail } (any may be missing).
  function dress(THREE, m, f, t, renderer) {
    if (!t || t.simple) return m;
    const tx = (n) => texture(THREE, n, t.texSize, renderer);
    const wallName = (f.names || []).find((n) => PATTERN_OF[n] && n !== "metal") || (f.names || []).find((n) => PATTERN_OF[n]);
    const wallPat = wallName ? PATTERN_OF[wallName] : "concrete";   // no finish written: plain, smooth render
    if (m.wall) {
      Object.assign(m.wall, { roughness: wallPat === "metal" || wallPat === "plate" ? 0.4 : 0.7, metalness: wallPat === "metal" || wallPat === "plate" ? 0.7 : 0 });
      if (wallPat === "plate") { m.wall.color.set(0x2b3442); }
      triplanar(THREE, m.wall, tx(wallPat), { colour: 0.9, bump: 0.012 });
    }
    if (m.room) triplanar(THREE, m.room, tx(wallPat), { colour: 0.7 });
    if (m.slab) { m.slab.color.set(0xa9a59d); m.slab.roughness = 0.55; triplanar(THREE, m.slab, tx("concrete"), { colour: 0.7, bump: 0.004 }); }
    if (m.core) { m.core.color.set(0xb3aea4); m.core.roughness = 0.6; triplanar(THREE, m.core, tx("concrete"), { colour: 0.6, bump: 0.004 }); }   // stairs: cast concrete
    if (m.roof && !f.greenRoof) { m.roof.roughness = 0.85; triplanar(THREE, m.roof, tx("concrete"), { colour: 0.8, bump: 0.006 }); }
    if (m.roof && f.greenRoof) triplanar(THREE, m.roof, tx("grass"), { colour: 1, bump: 0.02 });
    if (m.yard) { m.yard.color.set(0x8d8a84); triplanar(THREE, m.yard, tx("paving"), { colour: 0.8, bump: 0.006 }); }
    if (m.green) { m.green.color.set(0x4a6e36); triplanar(THREE, m.green, tx("grass"), { colour: 1, bump: 0.02 }); }
    if (m.fix) { m.fix.roughness = 0.6; triplanar(THREE, m.fix, tx("concrete"), { colour: 0.4 }); }
    if (m.frame) Object.assign(m.frame, { roughness: 0.35, metalness: 0.6 });                      // door frames: painted metal, still the legend's green
    if (m.entrance) Object.assign(m.entrance, { emissiveIntensity: 1.6, roughness: 0.3, metalness: 0.3 });   // glows through the bloom
    if (m.rail) Object.assign(m.rail, { roughness: 0.3, metalness: 0.9 });
    if (m.lift) Object.assign(m.lift, { roughness: 0.15, metalness: 0.2, opacity: 0.3 });
    if (m.glass) {
      // glass: clear, a little blue-green, mostly reflection (scene.environment); physically refracting on Realistic
      Object.assign(m.glass, { color: new THREE.Color(0xb9d3dc), roughness: 0.04, metalness: 0.1, opacity: 0.32, envMapIntensity: 0.9, depthWrite: false });
      if (t.physicalGlass && m.glass.isMeshPhysicalMaterial) Object.assign(m.glass, { transmission: 0.9, ior: 1.5, thickness: 0.02, opacity: 1, transparent: true, specularIntensity: 1 });
    }
    return m;
  }
  // A physical glass material for the Realistic look (MeshPhysicalMaterial), otherwise null so view3d.js keeps its own.
  function glassMaterial(THREE, t) {
    if (!t || t.simple) return null;
    return new THREE.MeshPhysicalMaterial({ color: 0xb9d3dc, roughness: 0.04, metalness: 0.1, transparent: true, opacity: 0.32, side: THREE.DoubleSide });
  }

  // ---- Ground surfaces in an area view: "paving" for the precinct ground, "asphalt" for streets (keeps the map colour).
  function surface(THREE, mat, kind, t, renderer) {
    if (!t || t.simple) return mat;
    mat.roughness = kind === "asphalt" ? 0.9 : 0.85;
    return triplanar(THREE, mat, texture(THREE, kind, t.texSize, renderer), { colour: 0.6, bump: 0.004 });
  }

  // ---- Navigation lights, only when the look text names them: a ring of small lamps round the top of the topmost
  // room or core, 10 ft (3 m) apart. Red on the port half and green on the starboard half (the ship's port is -y,
  // the usual red-to-port, green-to-starboard rule). The lamps are drawn, not lighting the scene.
  function navLights(THREE, group, model, look, t) {
    if (!/navigation lights?|nav lights?/i.test(String(look || "")) || !model || !model.levels) return 0;
    const lv = model.levels.slice().sort((a, c) => a.z_m - c.z_m), top = lv[lv.length - 1];
    const els = (model.elements || []).filter((e) => e.outline_m && (e.levels || [e.level]).includes(top.id) && ["room", "zone", "core", "mass"].includes(e.type));
    if (!els.length) return 0;
    // the outline of the topmost thing (the biggest one there)
    const area = (o) => Math.abs(o.reduce((s, p, i) => { const q = o[(i + 1) % o.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0) / 2);
    let pts = els.reduce((a, e) => (area(e.outline_m) > area(a) ? e.outline_m : a), els[0].outline_m);
    // the cab: the room named as one, if there is one
    const cab = els.find((e) => /cab|control/i.test(e.name || ""));
    if (cab) pts = cab.outline_m;
    const lamps = [];
    const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.round(L / 3));
      for (let k = 0; k < n; k++) { const f = k / n; lamps.push([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]); }
    }
    const zTop = top.z_m + top.height_m + 0.45;   // just above the roof slab
    for (const [port, colour] of [[true, 0xff0800], [false, 0x00ff40]]) {
      const mine = lamps.filter((p) => (p[1] < cy) === port);
      if (!mine.length) continue;
      const mat = new THREE.MeshStandardMaterial({ color: 0x111111, emissive: colour, emissiveIntensity: t && !t.simple ? 6 : 1.5 });
      const im = new THREE.InstancedMesh(new THREE.SphereGeometry(0.3, 10, 8), mat, mine.length);
      const o = new THREE.Object3D();
      mine.forEach((p, i) => { o.position.set(p[0], zTop, p[1]); o.updateMatrix(); im.setMatrixAt(i, o.matrix); });
      im.userData.noShadow = true;
      group.add(im);
    }
    return lamps.length;
  }

  // ---- The deck's own light. A deck with a sky ceiling is lit from its daylight-panel ceiling (Deck 5 is 1,969 ft
  // (600 m) up); one that "has no sky ceiling" (Decks 6 and 7) gets a dimmer, cooler working light.
  function deckOf(sc) {
    const uid = (sc && sc.precinct && sc.precinct.uid) || "";
    const n = +((uid.match(/^D(\d)/) || [])[1]);
    try { return (typeof IX !== "undefined" && IX.decks && IX.decks[n]) || null; } catch (e) { return null; }
  }
  // An environment for reflections: the inside of an enclosed deck. Bright ceiling panels above, a hazy city round
  // the edges, the deck floor below. Rendered once to a cube map; no image file.
  function deckEnvironment(THREE, renderer, sky) {
    const env = new THREE.Scene();
    const box = new THREE.Mesh(new THREE.BoxGeometry(100, 40, 100), new THREE.MeshBasicMaterial({ color: sky ? 0x8d98a3 : 0x4a525a, side: THREE.BackSide }));
    box.position.y = 10; env.add(box);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(100, 100), new THREE.MeshBasicMaterial({ color: sky ? 0x7d7b76 : 0x4a4c50 }));   // light bouncing up off the deck floor
    floor.rotation.x = -Math.PI / 2; floor.position.y = -9.9; env.add(floor);
    // a grid of ceiling panels, brighter than white (HDR), so glass and metal show the ceiling's light
    const pc = new THREE.Color(sky ? 0xfff3e2 : 0xd8e4ee).multiplyScalar(sky ? 2.4 : 1.4);
    const panel = new THREE.MeshBasicMaterial({ color: pc });
    for (let i = -3; i <= 3; i++) for (let j = -3; j <= 3; j++) {
      const p = new THREE.Mesh(new THREE.PlaneGeometry(11, 11), panel);
      p.rotation.x = Math.PI / 2; p.position.set(i * 13, 29.8, j * 13); env.add(p);
    }
    const pm = new THREE.PMREMGenerator(renderer);
    const rt = pm.fromScene(env, 0.035);
    pm.dispose();
    return rt.texture;
  }
  function ceilingTexture(THREE, sky) {
    // the ceiling seen from below: a grid of daylight panels with dark seams between them
    const n = 256, data = new Uint8Array(n * n * 4), seam = 6;
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const s = x % (n / 2) < seam || y % (n / 2) < seam, i = (y * n + x) * 4, v = s ? 238 : 255;
      data[i] = v; data[i + 1] = v; data[i + 2] = v; data[i + 3] = 255;
    }
    const t = new THREE.DataTexture(data, n, n, THREE.RGBAFormat);
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true; t.needsUpdate = true;
    return t;
  }

  // ---- Set up a scene's light, shadows, haze and finish. Returns { render, resize, follow, dispose }.
  // a: { THREE, renderer, scene, camera, sc, area: [Lm, Wm], size, t }
  function stage(a) {
    const { THREE, renderer, scene, camera, t } = a;
    const [Lm, Wm] = a.area, size = a.size;
    const deck = deckOf(a.sc), sky = !deck || !/no sky ceiling/i.test(deck.summary || "");
    const clear = deck && deck.clear_m ? deck.clear_m : 380;
    renderer.setPixelRatio(t.pixelRatio);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = sky ? 0.9 : 0.8;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Haze: the air of a deck 20+ miles long. Things a mile off are soft; things 2 miles off fade into it.
    const haze = new THREE.Color(sky ? 0xb3b9bf : 0x59626b);
    scene.background = haze;
    const hazeDensity = sky ? 0.00036 : 0.00045;   // as a person on the deck sees it (Walk)
    scene.fog = new THREE.FogExp2(haze, hazeDensity);
    scene.environment = deckEnvironment(THREE, renderer, sky);
    scene.environmentIntensity = sky ? 0.5 : 0.4;

    // The deck floor beyond the area, so the scene stands on the deck and not on a floating plate.
    const pv = texture(THREE, "paving", t.texSize, renderer);
    const floorMat = triplanar(THREE, new THREE.MeshStandardMaterial({ color: 0x55585c, roughness: 0.85 }), pv, { colour: 0.5, bump: 0.004 });
    // (cut into 1,640 ft (500 m) squares: one huge triangle loses depth precision on some GPUs and hides the ground above it)
    const span = Math.max(24000, size * 14);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(span, span, 48, 48), floorMat);
    floor.rotation.x = -Math.PI / 2; floor.position.set(Lm / 2, -0.3, Wm / 2); floor.receiveShadow = true; floor.userData.noAO = true;
    scene.add(floor);
    // The ceiling, at the deck's clear height (Deck 5: 1,969 ft (600 m)), lit panels on a sky deck.
    const ct = ceilingTexture(THREE, sky); ct.repeat.set(span / 120, span / 120);
    const ceil = new THREE.Mesh(new THREE.PlaneGeometry(span, span, 48, 48), new THREE.MeshBasicMaterial({ map: ct, color: new THREE.Color(sky ? 0xfff4e4 : 0x6c7680).multiplyScalar(sky ? 0.95 : 0.6) }));
    ceil.rotation.x = Math.PI / 2; ceil.position.set(Lm / 2, clear, Wm / 2); ceil.userData.noAO = true;
    scene.add(ceil);

    // see far enough for the haze to swallow the floor and ceiling before their edges
    camera.far = Math.max(camera.far, span * 0.6); camera.updateProjectionMatrix();

    // Light: soft skylight from the ceiling (hemisphere), plus one strong, high, slightly angled key for shadows,
    // as if the brightest panels were a little to the bow and port.
    scene.add(new THREE.HemisphereLight(sky ? 0xfff2df : 0xcfdbe6, sky ? 0x8a8478 : 0x4b4f55, sky ? 0.45 : 0.3));   // ground colour: light bounced off floors, so ceilings indoors aren't black
    const key = new THREE.DirectionalLight(sky ? 0xfff1dc : 0xdfe8f0, sky ? 1.5 : 0.9);
    const dir = new THREE.Vector3(-0.45, 1, -0.3).normalize();
    key.castShadow = true;
    key.shadow.mapSize.set(t.shadowSize, t.shadowSize);
    key.shadow.bias = -0.0004; key.shadow.normalBias = 0.04;
    scene.add(key, key.target);
    const aim = (cx, cz, half) => {
      // centre the shadow box on (cx, cz), half wide; snapped to whole shadow texels so edges don't shimmer
      const texel = (half * 2) / t.shadowSize;
      cx = Math.round(cx / texel) * texel; cz = Math.round(cz / texel) * texel;
      key.target.position.set(cx, 0, cz);
      key.position.set(cx + dir.x * 1500, dir.y * 1500, cz + dir.z * 1500);
      const c = key.shadow.camera;
      if (c.right !== half) { c.left = -half; c.right = half; c.top = half; c.bottom = -half; c.near = 10; c.far = 3200; c.updateProjectionMatrix(); }
    };
    const centre = new THREE.Vector3(Lm / 2, 0, Wm / 2);
    const whole = Math.min(Math.max(Lm, Wm) * 0.75 + 30, 1500);
    aim(Lm / 2, Wm / 2, whole);

    // Every building part casts and receives shadows (glass, lift shafts and lamps don't cast).
    const shadows = () => scene.traverse((o) => {
      if (!o.isMesh || o === floor || o === ceil) return;
      const m = o.material, see = m && m.transparent && (m.opacity < 0.9 || m.transmission);
      o.castShadow = !see && !o.userData.noShadow && !(m && m.isMeshBasicMaterial);
      o.receiveShadow = !(m && m.isMeshBasicMaterial);
    });

    // Post-processing: render -> ambient occlusion (Realistic) -> bloom on bright lights -> tone mapping and colour.
    let composer = null, gtao = null;
    const w = () => a.stage.clientWidth, h = () => a.stage.clientHeight;
    if (P) {
      const rt = new THREE.WebGLRenderTarget(w() * t.pixelRatio, h() * t.pixelRatio, { type: THREE.HalfFloatType, samples: t.samples });
      composer = new P.EffectComposer(renderer, rt);
      composer.setPixelRatio(t.pixelRatio); composer.setSize(w(), h());
      composer.addPass(new P.RenderPass(scene, camera));
      if (t.ao) {
        gtao = new P.GTAOPass(scene, camera, w(), h());
        gtao.blendIntensity = 0.85;
        gtao.updateGtaoMaterial({ radius: 1.2, distanceExponent: 1.5, thickness: 1.5, scale: 1, samples: 12 });
        gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 4, rings: 2, samples: 12 });
        // glass, see-through shafts and the far-off deck floor and ceiling don't make dark corners: hide them while the
        // occlusion pass looks at the scene
        const render = gtao.render.bind(gtao);
        let seeThrough = null;
        gtao.render = (...args) => {
          if (!seeThrough) { seeThrough = []; scene.traverse((o) => { if (o.material && (o.material.transparent || o.userData.noAO)) seeThrough.push(o); }); }
          const hidden = seeThrough.filter((o) => o.visible);
          hidden.forEach((o) => (o.visible = false));
          render(...args);
          hidden.forEach((o) => (o.visible = true));
        };
        composer.addPass(gtao);
      }
      if (t.bloom) composer.addPass(new P.UnrealBloomPass(new THREE.Vector2(w(), h()), 0.5, 0.45, 1.6));   // only lamps and lit signs glow, never a sunlit wall
      composer.addPass(new P.OutputPass());
    }
    return {
      shadows,
      follow(x, z, walking) {
        if (walking) { aim(x, z, 70); scene.fog.density = hazeDensity; return; }
        aim(Lm / 2, Wm / 2, whole);
        // Orbit: thin the haze when the camera is far out over a big precinct, so it still shows (about 10% haze on it)
        scene.fog.density = Math.min(hazeDensity, 0.3 / Math.max(1, camera.position.distanceTo(centre)));
      },
      render() { if (composer) composer.render(); else renderer.render(scene, camera); },
      resize() { if (composer) composer.setSize(w(), h()); },
      dispose() { if (composer) composer.dispose(); },
    };
  }

  // ---- The "Look" picker in the 3D bar.
  function picker(onChange) {
    const lab = document.createElement("label");
    lab.className = "v3d-look";
    lab.title = "Realistic: textures, daylight, shadows and haze (laptops and PCs). Balanced: the same, lighter, for phones and tablets. Simple: the old flat look, fastest.";
    lab.innerHTML = `Look <select>${Object.entries(LOOKS).map(([k, v]) => `<option value="${k}"${k === current() ? " selected" : ""}>${v}</option>`).join("")}</select>`;
    lab.querySelector("select").onchange = (e) => { set(e.target.value); onChange(e.target.value); };
    return lab;
  }

  window.adxiLook = { current, tier, lib, dress, glassMaterial, surface, navLights, stage, picker, texture, triplanar };
})();
