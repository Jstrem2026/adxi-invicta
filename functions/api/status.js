// ADXI: Invicta: is the site updating? A Cloudflare Pages Function at /api/status.
// Reads the latest "Scan and publish the site" run on main from GitHub Actions.
// Returns {state: "updating" | "updated" | "failed" | "unknown", at, title, url}.

export async function onRequestGet({ env }) {
  if (!env.GITHUB_REPO) return json({ state: "unknown" });
  try {
    const headers = { Accept: "application/vnd.github+json", "User-Agent": "adxi-invicta-site" };
    if (env.GITHUB_TOKEN) headers.Authorization = `Bearer ${env.GITHUB_TOKEN}`;
    const r = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/actions/runs?branch=main&event=push&per_page=1`, { headers });
    if (!r.ok) return json({ state: "unknown" });
    const run = ((await r.json()).workflow_runs || [])[0];
    if (!run) return json({ state: "unknown" });
    const state = run.status !== "completed" ? "updating" : run.conclusion === "success" ? "updated" : "failed";
    return json({
      state,
      at: run.status !== "completed" ? run.run_started_at || run.created_at : run.updated_at,
      title: (run.display_title || "").slice(0, 120),
      url: run.html_url,
    });
  } catch (e) {
    return json({ state: "unknown" });
  }
}

function json(obj) {
  return new Response(JSON.stringify(obj), {
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=10" },
  });
}
