// ADXI: Invicta owner review. A Cloudflare Pages Function at /api/review.
// Only Jordan can use it: every request must carry header X-Admin-Key equal to the
// ADMIN_KEY secret (set in Cloudflare Pages > Settings > Variables and secrets).
//
//   GET  /api/review                       open proposals with their changed files
//   POST /api/review {number, action, note}  action = "approve" (merge) or "reject" (close)

import { announce } from "../_lib/announce.js";
import { trustedHelper } from "../_lib/trusted.js";

export async function onRequest({ request, env }) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO) return json({ error: "Review isn't set up yet." }, 503);
  // Jordan's key or a trusted helper's (Kylee) opens the review page.
  const reviewer = await trustedHelper(env, request.headers.get("X-Admin-Key") || "");
  if (!reviewer) return json({ error: "Wrong key." }, 403);
  const gh = github(env);
  try {
    if (request.method === "GET") return json(await list(gh));
    if (request.method === "POST") {
      const body = await request.json();
      const number = parseInt(body.number, 10);
      const note = String(body.note || "").trim().slice(0, 2000);
      if (!number) return json({ error: "Which proposal?" }, 400);
      const pr = await gh.call("GET", `pulls/${number}`);
      if (pr.state !== "open") return json({ error: "That proposal is already closed." }, 409);
      if (body.action === "approve") {
        if (note) await gh.call("POST", `issues/${number}/comments`, { body: `${note}\n\n(${reviewer})` });
        const m = await gh.call("PUT", `pulls/${number}/merge`, { merge_method: "squash", commit_title: `${pr.title} (#${number})` });
        if (!m.merged) return json({ error: m.message || "GitHub didn't merge it." }, 409);
        await deleteBranch(gh, pr);
        try { await announce(env, reviewer, `approved: ${pr.title}`, pr.html_url); } catch (e) { /* optional */ }
        return json({ ok: true, merged: true, by: reviewer });
      }
      if (body.action === "reject") {
        await gh.call("POST", `issues/${number}/comments`, { body: (note || "Thanks for the idea. We decided not to use this one.") + `\n\n(${reviewer})` });
        await gh.call("PATCH", `pulls/${number}`, { state: "closed" });
        await deleteBranch(gh, pr);
        try { await announce(env, reviewer, `passed on: ${pr.title}`, pr.html_url); } catch (e) { /* optional */ }
        return json({ ok: true, closed: true });
      }
      return json({ error: "Unknown action." }, 400);
    }
    return json({ error: "Not allowed." }, 405);
  } catch (err) {
    return json({ error: String(err.message || err) }, 502);
  }
}

async function list(gh) {
  const prs = await gh.call("GET", "pulls?state=open&sort=created&direction=desc&per_page=50");
  const out = [];
  for (const pr of prs) {
    const files = await gh.call("GET", `pulls/${pr.number}/files?per_page=50`);
    const by = (pr.body || "").match(/\*\*Proposed by:\*\*\s*([^\n(]+)/);
    out.push({
      number: pr.number,
      title: pr.title,
      by: by ? by[1].trim() : pr.user.login,
      created: pr.created_at,
      url: pr.html_url,
      body: (pr.body || "").slice(0, 4000),
      mergeable: pr.mergeable_state || null,
      files: files.map((f) => ({
        path: f.filename,
        status: f.status,
        additions: f.additions,
        deletions: f.deletions,
        patch: (f.patch || "").slice(0, 20000),
      })),
    });
  }
  return { proposals: out };
}

async function deleteBranch(gh, pr) {
  if (pr.head && pr.head.ref && pr.head.ref.startsWith("proposal/") && pr.head.repo && pr.head.repo.full_name === pr.base.repo.full_name) {
    try { await gh.call("DELETE", `git/refs/heads/${pr.head.ref}`); } catch (e) { /* already gone */ }
  }
}

function github(env) {
  const base = `https://api.github.com/repos/${env.GITHUB_REPO}/`;
  return {
    async call(method, path, body) {
      const r = await fetch(base + path, {
        method,
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "adxi-invicta-site",
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (r.status === 204) return {};
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(`GitHub said ${r.status}${data.message ? ": " + data.message : ""}`);
      return data;
    },
  };
}

async function sameKey(a, b) {
  const enc = new TextEncoder();
  const [x, y] = await Promise.all([crypto.subtle.digest("SHA-256", enc.encode(a)), crypto.subtle.digest("SHA-256", enc.encode(b))]);
  const u = new Uint8Array(x), v = new Uint8Array(y);
  let diff = 0;
  for (let i = 0; i < u.length; i++) diff |= u[i] ^ v[i];
  return diff === 0 && a.length > 0;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}
