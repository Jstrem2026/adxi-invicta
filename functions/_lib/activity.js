// Team activity: a short record of each request Jordan and Kylee send to the site's Claude chat,
// so each can see what the other is asking, how it is going, and what changed. D1 binding DB.
// Only the design team can read it (functions/api/activity.js). It never blocks the chat: every
// call here swallows its own errors.

let ready = false;
async function ensure(env) {
  if (ready) return;
  await env.DB.prepare(`CREATE TABLE IF NOT EXISTS chat_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,          -- ms since epoch, when the request was sent
    updated INTEGER NOT NULL,     -- ms since epoch, last progress
    who TEXT NOT NULL,
    ask TEXT NOT NULL,
    place TEXT,                   -- what they had open on the map
    state TEXT NOT NULL,          -- working | done | error
    progress TEXT,                -- latest step, e.g. "Writing the change (12 KB so far)"
    reply TEXT,                   -- Claude's answer (cut to 4,000 characters)
    links TEXT                    -- JSON list of {url, title, merged}
  )`).run();
  ready = true;
}

// A short name for what was on screen, from the chat's "Looking at" context.
export function placeLabel(view) {
  try {
    const v = JSON.parse(view);
    if (v.room && v.room.name) return String(v.room.name);
    if (v.building && v.building.name) return `${v.building.id || ""} ${v.building.name}`.trim();
    return String(v.block || v.street?.name || v.precinct || v.district || v.deck || v.page || "");
  } catch (e) { return ""; }
}

export async function activityStart(env, who, ask, place) {
  if (!env.DB) return null;
  try {
    await ensure(env);
    const now = Date.now();
    const r = await env.DB.prepare("INSERT INTO chat_activity (ts, updated, who, ask, place, state, progress) VALUES (?1, ?1, ?2, ?3, ?4, 'working', 'Thinking') RETURNING id")
      .bind(now, String(who).slice(0, 60), String(ask).slice(0, 4000), String(place || "").slice(0, 200)).first();
    return r ? r.id : null;
  } catch (e) { console.error("activity start", e && e.message); return null; }
}

export async function activityUpdate(env, id, f) {
  if (!env.DB || !id) return;
  try {
    await env.DB.prepare("UPDATE chat_activity SET updated = ?2, state = COALESCE(?3, state), progress = COALESCE(?4, progress), reply = COALESCE(?5, reply), links = COALESCE(?6, links) WHERE id = ?1")
      .bind(id, Date.now(), f.state ?? null, f.progress ?? null, f.reply != null ? String(f.reply).slice(0, 4000) : null, f.links ? JSON.stringify(f.links) : null).run();
  } catch (e) { console.error("activity update", e && e.message); }
}

export async function activityList(env, limit = 40) {
  await ensure(env);
  const r = await env.DB.prepare("SELECT id, ts, updated, who, ask, place, state, progress, reply, links FROM chat_activity ORDER BY id DESC LIMIT ?1").bind(limit).all();
  return (r.results || []).map((x) => ({ ...x, links: x.links ? JSON.parse(x.links) : [] }));
}
