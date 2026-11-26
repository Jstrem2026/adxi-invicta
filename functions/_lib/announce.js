// Shared helper: post a notice into the site's shared chat room (D1 binding DB).
export async function announce(env, name, text, link) {
  if (!env.DB) return;
  const who = String(name || "").replace(/[\u0000-\u001f]/g, "").trim().slice(0, 40) || "Anonymous helper";
  await env.DB.prepare("INSERT INTO messages (ts, name, text, kind, link) VALUES (?1, ?2, ?3, 'proposal', ?4)")
    .bind(Date.now(), who, String(text).slice(0, 500), link).run();
}
