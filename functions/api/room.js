// ADXI: Invicta shared helper chat. A Cloudflare Pages Function at /api/room.
// Everyone on the site sees the same room. Messages live in D1 (binding DB).
//
//   GET  /api/room?after=<id>&client=<id>&name=<name>&beat=1   new messages + who's online
//   POST /api/room  {text, name, client}                         send a message
//   DELETE /api/room?id=<id>  header X-Admin-Key                 hide a message (secret ADMIN_KEY)

const MAX_TEXT = 500;
const PER_MINUTE = 8;
const PER_DAY = 300;
const ONLINE_MS = 75_000;

export async function onRequestGet({ request, env }) {
  if (!env.DB) return json({ error: "The chat isn't set up yet." }, 503);
  const url = new URL(request.url);
  const after = Math.max(0, parseInt(url.searchParams.get("after") || "0", 10) || 0);
  const client = clean(url.searchParams.get("client"), 40);
  const name = clean(url.searchParams.get("name"), 40);
  const now = Date.now();

  if (client && url.searchParams.get("beat")) {
    await env.DB.prepare(
      "INSERT INTO presence (client, name, seen) VALUES (?1, ?2, ?3) ON CONFLICT(client) DO UPDATE SET name = ?2, seen = ?3"
    ).bind(client, name, now).run();
  }
  const rows = after
    ? await env.DB.prepare("SELECT id, ts, name, text, kind, link FROM messages WHERE id > ?1 AND hidden = 0 ORDER BY id LIMIT 100").bind(after).all()
    : await env.DB.prepare("SELECT * FROM (SELECT id, ts, name, text, kind, link FROM messages WHERE hidden = 0 ORDER BY id DESC LIMIT 60) ORDER BY id").all();
  const online = await env.DB.prepare("SELECT name FROM presence WHERE seen > ?1 ORDER BY seen DESC LIMIT 50").bind(now - ONLINE_MS).all();
  if (Math.random() < 0.02) {
    await env.DB.prepare("DELETE FROM presence WHERE seen < ?1").bind(now - 86_400_000).run();
  }
  return json({
    messages: rows.results,
    online: online.results.map((r) => r.name || "Anonymous helper"),
  });
}

export async function onRequestPost({ request, env }) {
  if (!env.DB) return json({ error: "The chat isn't set up yet." }, 503);
  let body;
  try { body = await request.json(); } catch { return json({ error: "Bad request." }, 400); }
  const text = String(body.text || "").replace(/\s+$/g, "").trim().slice(0, MAX_TEXT);
  const name = clean(body.name, 40) || "Anonymous helper";
  if (!text) return json({ error: "Empty message." }, 400);

  const ip = await hash(request.headers.get("CF-Connecting-IP") || "unknown");
  const now = Date.now();
  const counts = await env.DB.prepare(
    "SELECT SUM(ts > ?2) AS minute, COUNT(*) AS day FROM messages WHERE ip = ?1 AND ts > ?3"
  ).bind(ip, now - 60_000, now - 86_400_000).first();
  if ((counts.minute || 0) >= PER_MINUTE) return json({ error: "Slow down a little, then try again." }, 429);
  if ((counts.day || 0) >= PER_DAY) return json({ error: "You've reached today's message limit." }, 429);

  const r = await env.DB.prepare("INSERT INTO messages (ts, name, text, kind, ip) VALUES (?1, ?2, ?3, 'chat', ?4)")
    .bind(now, name, text, ip).run();
  return json({ ok: true, id: r.meta.last_row_id });
}

export async function onRequestDelete({ request, env }) {
  if (!env.DB || !env.ADMIN_KEY || request.headers.get("X-Admin-Key") !== env.ADMIN_KEY) return json({ error: "Not allowed." }, 403);
  const id = parseInt(new URL(request.url).searchParams.get("id") || "0", 10);
  await env.DB.prepare("UPDATE messages SET hidden = 1 WHERE id = ?1").bind(id).run();
  return json({ ok: true });
}

function clean(s, n) {
  return String(s || "").replace(/[\u0000-\u001f]/g, "").trim().slice(0, n);
}
async function hash(s) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("adxi-room:" + s));
  return [...new Uint8Array(d)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}
