// ADXI: Invicta team activity: GET /api/activity. What Jordan and Kylee have asked the site's Claude
// chat, its progress and results. For the design team only (same password as the chat).
import { trustedFrom } from "../_lib/trusted.js";
import { activityList } from "../_lib/activity.js";

export async function onRequestGet({ request, env }) {
  const who = await trustedFrom(env, request);
  if (!who) return json({ error: "For the design team only." }, 403);
  if (!env.DB) return json({ items: [] });
  const now = Date.now();
  const items = (await activityList(env)).map((x) => (
    // No progress for 3 minutes while "working" means the request was cut off (page closed, connection lost).
    x.state === "working" && now - x.updated > 180_000 ? { ...x, state: "stopped" } : x));
  return json({ items, now });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
}
