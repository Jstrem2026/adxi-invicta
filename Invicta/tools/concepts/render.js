// Concept render of one building from its 3D plan (tools/concepts/render.mjs drives this page).
// A dark hangar-deck mood: graphite walls with lit window bands, glowing floor lines, streets with markings,
// neighbours in the background. It shows the building's real outline, floors, cores and open-air zones.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const W = 1280, H = 800;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, H);
renderer.setPixelRatio(1);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
document.body.prepend(renderer.domElement);

function rand(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
function hash(str) { let h = 2166136261; for (const c of str) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

// ---------- textures
function windowTexture(R, opts) {
  const c = document.createElement("canvas"); c.width = 256; c.height = 64;
  const g = c.getContext("2d");
  g.fillStyle = opts.wall; g.fillRect(0, 0, 256, 64);
  // panel seams
  g.strokeStyle = "rgba(255,255,255,0.05)"; g.lineWidth = 1;
  for (let x = 0; x < 256; x += 32) { g.beginPath(); g.moveTo(x + .5, 0); g.lineTo(x + .5, 64); g.stroke(); }
  const cols = opts.cols || 8, y0 = opts.y0 || 18, hh = opts.wh || 26;
  for (let i = 0; i < cols; i++) {
    const x = i * (256 / cols) + 3, w = 256 / cols - 6;
    const lit = R() < opts.lit;
    const warm = R() < 0.75;
    g.fillStyle = lit ? (warm ? `rgba(255,${200 + R() * 40 | 0},${130 + R() * 60 | 0},${0.75 + R() * .25})` : `rgba(170,215,255,${0.6 + R() * .3})`) : "rgba(20,28,38,0.95)";
    g.fillRect(x, y0, w, hh);
    if (lit) { g.fillStyle = "rgba(255,255,255,0.08)"; g.fillRect(x, y0, w, 3); }
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}
function groundTexture() {
  const c = document.createElement("canvas"); c.width = c.height = 512;
  const g = c.getContext("2d");
  g.fillStyle = "#1a1f25"; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 3000; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * 0.025})`; g.fillRect(Math.random() * 512, Math.random() * 512, 2, 2); }
  g.strokeStyle = "rgba(160,180,200,0.10)"; g.lineWidth = 2;
  for (let x = 0; x <= 512; x += 128) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 512); g.stroke(); g.beginPath(); g.moveTo(0, x); g.lineTo(512, x); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// ---------- geometry helpers (ship plan x -> world x, plan y -> world z)
function shapeOf(ring, holes) {
  const s = new THREE.Shape(ring.map(([x, y]) => new THREE.Vector2(x, -y)));
  for (const h of holes || []) s.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, -y))));
  return s;
}
function inPoly(p, poly) {
  let ins = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > p[1]) !== (yj > p[1]) && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}
function prism(ring, holes, z0, h, mats) {
  const geo = new THREE.ExtrudeGeometry(shapeOf(ring, holes), { depth: Math.max(h, 0.05), bevelEnabled: false, curveSegments: 4 });
  geo.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(geo, mats);
  m.position.y = z0;
  return m;
}
function bbox(ring) {
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const [x, y] of ring) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  return [x0, x1, y0, y1];
}
function scatter(ring, n, R, holes) {
  const [x0, x1, y0, y1] = bbox(ring), out = [];
  for (let k = 0; k < n * 6 && out.length < n; k++) {
    const p = [x0 + R() * (x1 - x0), y0 + R() * (y1 - y0)];
    if (inPoly(p, ring) && !(holes || []).some((h) => inPoly(p, h))) out.push(p);
  }
  return out;
}

const KW = {
  green: /lawn|garden|grass|green|field|park(?!ing)|grove|wood|tree|hedge|parterre|flower|herb|planted|meadow|orchard|pitch|sports/i,
  trees: /grove|wood|tree|garden|park(?!ing)|orchard|avenue|shade|rim|walk|quiet/i,
  water: /lake|pool|water|rill|fountain|pond|reflect|splash/i,
  container: /container|stack|crate|module yard|stores yard|cargo|pallet|loading lane|marshalling|modules|turret mounts|parts|empties|returns|inspection hold/i,
  mast: /antenna|mast|sensor|aerial|beacon|radar/i,
  craft: /apron|bay|launch|taxi|flight line|pad|ramp|queue|recovery|arming|line-up|parking/i,
  crane: /crane|quay|gantry|hoist/i,
  tank: /tank|fuel|propellant|cell farm/i,
  berm: /berm|bund|blast|wall/i,
  berth: /^berth \d/i,
};

export async function renderScene(S) {
  const R = rand(hash(S.uid));
  const scene = new THREE.Scene();
  const fogCol = new THREE.Color(0x0a0e13);
  scene.background = fogCol;
  const span = Math.max(S.size[0], S.size[1]);
  scene.fog = new THREE.FogExp2(fogCol, 1.25 / (span * 3.2 + 900));
  const accent = new THREE.Color(S.accent);

  scene.add(new THREE.HemisphereLight(0xa9bdd4, 0x14181d, 0.9));
  const key = new THREE.DirectionalLight(0xd8e4f0, 1.5); key.position.set(-0.4, 1, 0.25).multiplyScalar(1000); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffb070, 0.35); fill.position.set(0.6, 0.4, -0.5).multiplyScalar(1000); scene.add(fill);

  // ground
  const gt = groundTexture(); gt.repeat.set(40, 40);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(20000, 20000), new THREE.MeshStandardMaterial({ map: gt, roughness: 0.92, metalness: 0.05 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.05; scene.add(ground);

  // streets: lighter asphalt, edge lines and a dashed yellow centre line
  const stMat = new THREE.MeshStandardMaterial({ color: 0x262c33, roughness: 0.85 });
  const lineMat = new THREE.MeshBasicMaterial({ color: 0xcfd8e0 });
  const yelMat = new THREE.MeshBasicMaterial({ color: 0xe8b830 });
  for (const [x0, x1, y0, y1] of S.streets || []) {
    const w = x1 - x0, d = y1 - y0;
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.1, d), stMat); m.position.set((x0 + x1) / 2, 0.0, (y0 + y1) / 2); scene.add(m);
    const along = w > d, L = along ? w : d, Wd = along ? d : w;
    for (const side of [-1, 1]) {
      const e = new THREE.Mesh(new THREE.BoxGeometry(along ? L : 0.4, 0.12, along ? 0.4 : L), lineMat);
      e.position.set((x0 + x1) / 2 + (along ? 0 : side * (Wd / 2 - 1.5)), 0.02, (y0 + y1) / 2 + (along ? side * (Wd / 2 - 1.5) : 0)); scene.add(e);
    }
    for (let u = -L / 2 + 4; u < L / 2 - 4; u += 14) {
      const dsh = new THREE.Mesh(new THREE.BoxGeometry(along ? 7 : 0.45, 0.13, along ? 0.45 : 7), yelMat);
      dsh.position.set((x0 + x1) / 2 + (along ? u : 0), 0.03, (y0 + y1) / 2 + (along ? 0 : u)); scene.add(dsh);
    }
  }

  // shared materials
  const wallCol = S.category === "medical" ? "#cfd5da" : S.category === "homes" ? "#4a4038" : S.category === "parks" ? "#3b4a3e" : "#2a3038";
  const wallTex = windowTexture(R, { wall: wallCol, lit: S.category === "utilities" || S.category === "industry" ? 0.35 : 0.6, cols: 8 });
  const shopTex = windowTexture(R, { wall: wallCol, lit: 0.9, cols: 4, y0: 8, wh: 46 });
  const rc = document.createElement("canvas"); rc.width = rc.height = 128;
  { const g = rc.getContext("2d"); g.fillStyle = "#3a414a"; g.fillRect(0, 0, 128, 128); g.strokeStyle = "rgba(0,0,0,.35)"; g.lineWidth = 2;
    for (let k = 0; k <= 128; k += 32) { g.beginPath(); g.moveTo(k, 0); g.lineTo(k, 128); g.stroke(); g.beginPath(); g.moveTo(0, k); g.lineTo(128, k); g.stroke(); }
    for (let i = 0; i < 400; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * .04})`; g.fillRect(Math.random() * 128, Math.random() * 128, 3, 3); } }
  const roofTex = new THREE.CanvasTexture(rc); roofTex.wrapS = roofTex.wrapT = THREE.RepeatWrapping; roofTex.repeat.set(1 / 24, 1 / 24); roofTex.colorSpace = THREE.SRGBColorSpace;
  const roofMat = new THREE.MeshStandardMaterial({ map: roofTex, roughness: 0.85, metalness: 0.25 });
  const skyMat = new THREE.MeshStandardMaterial({ color: 0x0c1015, emissive: 0x9fd2ff, emissiveIntensity: 1.1 });
  const bandMat = new THREE.MeshStandardMaterial({ color: 0x101418, emissive: 0xbfe6ff, emissiveIntensity: 2.2 });
  const accMat = new THREE.MeshStandardMaterial({ color: 0x101418, emissive: accent, emissiveIntensity: 2.4 });
  const coreMat = new THREE.MeshStandardMaterial({ color: 0x3a414a, roughness: 0.8, metalness: 0.3 });
  const unitMat = new THREE.MeshStandardMaterial({ color: 0x4a525c, roughness: 0.7, metalness: 0.5 });
  const BAND = [roofMat, bandMat], ACC = [roofMat, accMat];
  function wallMats(tex, h, tile) {
    const t = tex.clone(); t.needsUpdate = true; t.repeat.set(1 / tile, 1 / h);
    return [roofMat, new THREE.MeshStandardMaterial({ map: t, emissiveMap: t, emissive: 0xffffff, emissiveIntensity: 0.55, roughness: 0.6, metalness: 0.3 })];
  }

  const rings = S.rings, holes = S.holes || [];
  const ringHoles = (ring) => holes.filter((h) => inPoly(h[0], ring));
  const open = S.open !== undefined ? S.open : ["park", "plaza", "yard"].includes(S.kind);
  const levels = (S.levels && S.levels.length) ? S.levels : [{ z: 0, h: S.height || 8 }];

  // ---------- neighbours (context)
  const nbWall = windowTexture(R, { wall: "#22272e", lit: 0.35, cols: 8 });
  const nbMat = (h) => wallMats(nbWall, Math.min(h, 4.5), 26);
  const parkMat = new THREE.MeshStandardMaterial({ color: 0x3a7042, roughness: 1, emissive: 0x0c2410, emissiveIntensity: 0.6 });
  const pavMat = new THREE.MeshStandardMaterial({ color: 0x343a41, roughness: 0.95 });
  for (const n of S.neighbours || []) {
    for (const ring of n.rings) {
      const hs = (n.holes || []).filter((h) => inPoly(h[0], ring));
      if (n.h <= 0.5) { scene.add(prism(ring, hs, 0.02, 0.25, n.kind === "park" ? parkMat : pavMat)); continue; }
      const mats = nbMat(n.h);
      const m = prism(ring, hs, 0, n.h, mats); scene.add(m);
      scene.add(prism(ring, hs, n.h, 0.4, BAND));
    }
  }

  // ---------- the building
  const tall = levels[levels.length - 1].z + levels[levels.length - 1].h;
  if (!open) {
    for (const ring of rings) {
      const hs = ringHoles(ring);
      levels.forEach((l, i) => {
        const band = i === 0 ? ACC : (i % 3 === 0 ? ACC : BAND);
        scene.add(prism(ring, hs, l.z, 0.45, band));
        const mats = wallMats(i === 0 ? shopTex : wallTex, l.h - 0.45, i === 0 ? 30 : 24);
        scene.add(prism(ring, hs, l.z + 0.45, l.h - 0.45, mats));
      });
      scene.add(prism(ring, hs, tall, 0.6, BAND));       // lit parapet line
      // rooftop plant units
      const pts = scatter(ring, Math.min(40, Math.max(4, Math.round(Math.abs(S.size[0] * S.size[1]) / 9000))), R, hs);
      for (const [x, y] of pts) {
        const w = 4 + R() * 10, d = 4 + R() * 8, h = 1.5 + R() * 3;
        const u = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), unitMat); u.position.set(x, tall + 0.6 + h / 2, y); scene.add(u);
      }
    }
    for (const h of holes) {
      scene.add(prism(h, [], 0.03, 0.3, parkMat));
      for (const [x, y] of scatter(h, Math.min(80, Math.abs(bbox(h)[1] - bbox(h)[0]) * Math.abs(bbox(h)[3] - bbox(h)[2]) / 500), R)) {
        const th = 5 + R() * 6;
        const c = new THREE.Mesh(new THREE.SphereGeometry(th * 0.35, 7, 5), new THREE.MeshStandardMaterial({ color: 0x2f6b3a, roughness: 1 })); c.position.set(x, th * 0.6, y); scene.add(c);
      }
    }
    for (const e of S.els || []) {
      if (e.t === "hall") {
        const [x0, x1, y0, y1] = bbox(e.p), along = x1 - x0 > y1 - y0, L = along ? x1 - x0 : y1 - y0, Wd = along ? y1 - y0 : x1 - x0;
        const n = Math.max(1, Math.min(12, Math.round(Wd / 18)));
        for (let k = 0; k < n; k++) {
          const off = -Wd / 2 + (k + 0.5) * Wd / n, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
          const sk = new THREE.Mesh(new THREE.BoxGeometry(along ? L * 0.8 : 3, 0.5, along ? 3 : L * 0.8), skyMat);
          const p = [cx + (along ? 0 : off), cy + (along ? off : 0)];
          if (inPoly(p, e.p)) { sk.position.set(p[0], tall + 0.75, p[1]); scene.add(sk); }
        }
      }
      if (e.t === "core") { const m = prism(e.p, [], tall, 4.5, [coreMat, coreMat]); scene.add(m); scene.add(prism(e.p, [], tall + 4.5, 0.3, ACC)); }
      if (e.t === "zone") scene.add(prism(e.p, [], 0.05, 0.3, KW.green.test(e.n) ? parkMat : pavMat));
    }
  } else {
    const lotMat = S.kind === "park" ? parkMat : S.kind === "plaza" ? new THREE.MeshStandardMaterial({ color: 0x4b525a, roughness: 0.9 }) : new THREE.MeshStandardMaterial({ color: 0x353c44, roughness: 0.9 });
    for (const ring of rings) scene.add(prism(ring, ringHoles(ring), 0.02, 0.3, lotMat));
    const trunk = new THREE.MeshStandardMaterial({ color: 0x3a2c22, roughness: 1 });
    const leafs = [0x2f6b3a, 0x3d7d42, 0x2a5e40, 0x4b8a46].map((c) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.95 }));
    const waterMat = new THREE.MeshStandardMaterial({ color: 0x0f3a55, roughness: 0.08, metalness: 0.6, emissive: 0x0a2a40, emissiveIntensity: 0.6 });
    const boxCols = [0x8a4b2d, 0x2c6e7a, 0x5d6670, 0x2d4f8a, 0x9b7b2f, 0x6b2f2f].map((c) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.7, metalness: 0.3 }));
    const craftMat = new THREE.MeshStandardMaterial({ color: 0x8c96a2, roughness: 0.45, metalness: 0.7 });
    const paint = new THREE.MeshBasicMaterial({ color: 0xd8c04a });
    for (const e of S.els || []) {
      if (e.t === "zone") {
        const n = e.n;
        const isW = KW.water.test(n) && !KW.tank.test(n), isG = KW.green.test(n);
        scene.add(prism(e.p, [], 0.3, 0.12, isW ? waterMat : isG ? parkMat : pavMat));
        const [x0, x1, y0, y1] = bbox(e.p), A = Math.abs((x1 - x0) * (y1 - y0));
        if (KW.berth.test(n)) {
          // a docked escort cruiser (canon 2,000 x 420 m), lying along the berth
          const along = x1 - x0 > y1 - y0, Lz = Math.min(2000, (along ? x1 - x0 : y1 - y0) * 0.92), Wz = Math.min(420, (along ? y1 - y0 : x1 - x0) * 0.8);
          const hullMat = new THREE.MeshStandardMaterial({ color: 0x5b6470, roughness: 0.5, metalness: 0.7 });
          const g = new THREE.CylinderGeometry(Wz * 0.5, Wz * 0.5, Lz, 8, 1); g.scale(1, 1, 0.45);
          const hull = new THREE.Mesh(g, hullMat); hull.position.set((x0 + x1) / 2, Wz * 0.25, (y0 + y1) / 2);
          if (along) hull.rotation.z = Math.PI / 2; else hull.rotation.x = Math.PI / 2;
          scene.add(hull);
          const tower = new THREE.Mesh(new THREE.BoxGeometry(along ? Lz * 0.12 : Wz * 0.3, Wz * 0.18, along ? Wz * 0.3 : Lz * 0.12), hullMat);
          tower.position.set((x0 + x1) / 2, Wz * 0.5, (y0 + y1) / 2); scene.add(tower);
          for (const sd of [-1, 1]) {   // a line of running lights down each flank
            const lt = new THREE.Mesh(new THREE.BoxGeometry(along ? Lz * 0.9 : 1.5, 1.5, along ? 1.5 : Lz * 0.9), BAND[1]);
            lt.position.set((x0 + x1) / 2 + (along ? 0 : sd * Wz * 0.505), Wz * 0.25, (y0 + y1) / 2 + (along ? sd * Wz * 0.505 : 0)); scene.add(lt);
          }
        } else if (KW.trees.test(n) && !isW) {
          for (const [x, y] of scatter(e.p, Math.min(220, A / 260), R)) {
            const h = 6 + R() * 9;
            const t = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.5, h * 0.45, 5), trunk); t.position.set(x, h * 0.22, y); scene.add(t);
            const c = new THREE.Mesh(new THREE.SphereGeometry(h * 0.32, 7, 5), leafs[(R() * 4) | 0]); c.position.set(x, h * 0.62, y); c.scale.y = 1.15; scene.add(c);
          }
        } else if (KW.container.test(n)) {
          for (const [x, y] of scatter(e.p, Math.min(260, A / 220), R)) {
            const st = 1 + ((R() * 4) | 0);
            for (let k = 0; k < st; k++) { const b = new THREE.Mesh(new THREE.BoxGeometry(12.2, 2.6, 2.5), boxCols[(R() * 6) | 0]); b.position.set(x, 1.3 + k * 2.6, y); scene.add(b); }
          }
        } else if (KW.mast.test(n)) {
          for (const [x, y] of scatter(e.p, Math.min(60, A / 1500), R)) {
            const h = 15 + R() * 30;
            const m = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.8, h, 6), unitMat); m.position.set(x, h / 2, y); scene.add(m);
            const tip = new THREE.Mesh(new THREE.SphereGeometry(0.9, 6, 4), accMat); tip.position.set(x, h + 0.5, y); scene.add(tip);
            if (R() < 0.5) { const dish = new THREE.Mesh(new THREE.CylinderGeometry(4, 1, 1.5, 12), craftMat); dish.position.set(x, h * 0.7, y); dish.rotation.z = 0.8; scene.add(dish); }
          }
        } else if (KW.craft.test(n)) {
          for (const [x, y] of scatter(e.p, Math.min(40, A / 2500), R)) {
            const s = 10 + R() * 14;
            const g = new THREE.ConeGeometry(s * 0.45, s, 3); g.rotateX(Math.PI / 2); g.scale(1, 0.28, 1);
            const c = new THREE.Mesh(g, craftMat); c.position.set(x, 1.6, y); c.rotation.y = R() < 0.5 ? 0 : Math.PI / 2; scene.add(c);
            const pad = new THREE.Mesh(new THREE.RingGeometry(s * 0.7, s * 0.75, 24), paint); pad.rotation.x = -Math.PI / 2; pad.position.set(x, 0.45, y); scene.add(pad);
          }
        } else if (KW.tank.test(n)) {
          for (const [x, y] of scatter(e.p, Math.min(24, A / 2500), R)) {
            const r = 6 + R() * 8, h = 8 + R() * 10;
            const t = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 20), new THREE.MeshStandardMaterial({ color: 0xb9c0c8, roughness: 0.5, metalness: 0.6 })); t.position.set(x, h / 2, y); scene.add(t);
            { const band = new THREE.Mesh(new THREE.CylinderGeometry(r + 0.1, r + 0.1, 0.5, 20), accMat); band.position.set(x, h * 0.8, y); scene.add(band); }
          }
        } else if (KW.crane.test(n)) {
          const [cx, cy] = [(x0 + x1) / 2, (y0 + y1) / 2], L = Math.max(x1 - x0, y1 - y0) * 0.6, along = x1 - x0 > y1 - y0;
          for (const s of [-1, 1]) {
            const leg = new THREE.Mesh(new THREE.BoxGeometry(2, 40, 2), new THREE.MeshStandardMaterial({ color: 0xc89a2a, roughness: 0.6 }));
            leg.position.set(cx + (along ? s * L / 2 : 0), 20, cy + (along ? 0 : s * L / 2)); scene.add(leg);
          }
          const beam = new THREE.Mesh(new THREE.BoxGeometry(along ? L : 3, 3, along ? 3 : L), new THREE.MeshStandardMaterial({ color: 0xc89a2a, roughness: 0.6 }));
          beam.position.set(cx, 40, cy); scene.add(beam);
        } else if (KW.berm.test(n)) {
          scene.add(prism(e.p, [], 0.3, 6, new THREE.MeshStandardMaterial({ color: 0x3c4038, roughness: 1 })));
        }
      } else if (e.t === "room") {
        const h = Math.max(3.5, Math.min(e.h || 4, 12));
        scene.add(prism(e.p, [], 0, 0.4, ACC));
        scene.add(prism(e.p, [], 0.4, h, wallMats(shopTex, h, 14)));
        scene.add(prism(e.p, [], h + 0.4, 0.3, BAND));
      } else if (e.t === "fix") {
        const h = 3 + R() * 6;
        scene.add(prism(e.p, [], 0, h, [unitMat, unitMat]));
        scene.add(prism(e.p, [], h, 0.3, ACC));
      }
    }
  }

  // the deck around: giant support columns with light rings, far off in the haze
  const colMat = new THREE.MeshStandardMaterial({ color: 0x1c2229, roughness: 0.8, metalness: 0.4 });
  for (let k = 0; k < 7; k++) {
    const a = R() * Math.PI * 2, d = span * 1.6 + 900 + R() * 1600, r = 40 + R() * 40;
    const col = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 1.2, 1300, 16), colMat); col.position.set(Math.cos(a) * d, 650, Math.sin(a) * d); scene.add(col);
    for (let y = 60; y < 600; y += 120) { const ringL = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.02, r * 1.02, 2, 16, 1, true), BAND[1]); ringL.position.set(Math.cos(a) * d, y, Math.sin(a) * d); scene.add(ringL); }
  }
  // street lamps and a few people-scale lights near the building for scale
  const lampMat = new THREE.MeshStandardMaterial({ color: 0x222, emissive: 0xffd8a0, emissiveIntensity: 3 });
  for (const ring of rings) {
    for (let i = 0; i < ring.length; i += Math.max(1, Math.floor(ring.length / 10))) {
      const [x, y] = ring[i];
      const l = new THREE.Mesh(new THREE.SphereGeometry(0.8, 6, 4), lampMat); l.position.set(x * 1.04, 7, y * 1.04); scene.add(l);
    }
  }

  // ---------- camera: a three-quarter aerial view, side picked from the building's id
  const az = (Math.floor(R() * 4) + 0.5) * Math.PI / 2 + (R() - 0.5) * 0.6;
  const el = (open ? 38 : 20 + R() * 8) * Math.PI / 180;
  const rad = Math.hypot(S.size[0], S.size[1], tall) / 2;
  const fov = 32;
  const dist = rad / Math.tan((fov / 2) * Math.PI / 180) * (open ? 1.0 : 0.95);
  const cam = new THREE.PerspectiveCamera(fov, W / H, 1, 60000);
  const tgt = new THREE.Vector3(0, tall * 0.3, 0);
  cam.position.set(tgt.x + Math.cos(az) * Math.cos(el) * dist, tgt.y + Math.sin(el) * dist, tgt.z + Math.sin(az) * Math.cos(el) * dist);
  cam.lookAt(tgt);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, cam));
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), 0.65, 0.5, 0.62));
  composer.addPass(new OutputPass());
  composer.render();
  composer.render();
  document.getElementById("cap").innerHTML = `${S.id} · ${S.name}<small>${S.precinct} · ${S.district} · Deck 5 Aerion</small>`;
  return true;
}
window.renderScene = renderScene;
window.__ready = true;
