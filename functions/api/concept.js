// ADXI: Invicta: add or remove concept art on a building. A Cloudflare Pages Function at /api/concept.
// POST {uid, label, title, name, image (base64)}               add
// POST {action: "delete", uid, file, label, name}              remove
// Trusted helpers and Jordan (X-Helper-Key) go live at once; others go to /review.

import { trustedFrom } from "../_lib/trusted.js";
import { UID_RE, addConcept, removeConcept } from "../_lib/concepts.js";

const MAX_BYTES = 4_000_000;
const PER_DAY = 10;

export async function onRequestPost({ request, env }) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO || !env.LIMITS) return json({ error: "Uploads aren't set up yet." }, 503);
  let body;
  try { body = await request.json(); } catch { return json({ error: "Bad request." }, 400); }
  const uid = String(body.uid || "");
  if (!UID_RE.test(uid)) return json({ error: "Unknown building." }, 400);
  const label = clean(body.label, 80) || uid;
  const trusted = await trustedFrom(env, request);
  const name = trusted || clean(body.name, 40) || "Anonymous helper";

  const day = new Date().toISOString().slice(0, 10);
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const key = `c:${day}:${ip}`;
  const used = Number((await env.LIMITS.get(key)) || 0);
  if (used >= PER_DAY && !trusted) return json({ error: "You've reached today's limit." }, 429);
  await env.LIMITS.put(key, String(used + 1), { expirationTtl: 172800 });

  try {
    if (body.action === "delete") {
      const file = String(body.file || "");
      if (!/^Invicta\/data\/concepts\/[A-Za-z0-9._-]+$/.test(file)) return json({ error: "Bad file." }, 400);
      return json({ ok: true, ...(await removeConcept(env, { uid, file, label }, name, trusted)) });
    }
    const b64 = String(body.image || "").replace(/\s/g, "");
    if (!b64 || b64.length * 3 / 4 > MAX_BYTES) return json({ error: "The image is missing or larger than 4 MB." }, 400);
    const title = clean(body.title, 80) || `${label} concept`;
    return json({ ok: true, ...(await addConcept(env, { uid, label, title, name, b64 }, trusted)) });
  } catch (err) {
    return json({ error: String(err.message || err) }, 502);
  }
}

function clean(s, n) { return String(s || "").replace(/[\u0000-\u001f]/g, "").trim().slice(0, n); }
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
}
