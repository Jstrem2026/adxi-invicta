// ADXI: Invicta: add concept art to a building. A Cloudflare Pages Function at /api/concept.
// POST {uid, label, title, name, image (base64 JPEG/PNG/WebP)}
// Commits the image to Invicta/data/concepts/ and an entry to Invicta/data/concepts.json
// as a pull request for Jordan, or merges it at once for a trusted helper (X-Helper-Key).

import { trustedHelper } from "../_lib/trusted.js";
import { announce } from "../_lib/announce.js";

const MAX_BYTES = 4_000_000;
const PER_DAY = 10;

export async function onRequestPost({ request, env }) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO || !env.LIMITS) return json({ error: "Uploads aren't set up yet." }, 503);
  let body;
  try { body = await request.json(); } catch { return json({ error: "Bad request." }, 400); }
  const uid = String(body.uid || "");
  if (!/^D\d-[a-z0-9-]+-P\d+-\d+[a-z]?$/i.test(uid)) return json({ error: "Unknown building." }, 400);
  const label = clean(body.label, 80) || uid;
  const title = clean(body.title, 80) || `${label} concept`;
  const trusted = await trustedHelper(env, request.headers.get("X-Helper-Key") || "");
  const name = trusted || clean(body.name, 40) || "Anonymous helper";
  const b64 = String(body.image || "").replace(/\s/g, "");
  const bytes = Math.floor(b64.length * 3 / 4);
  if (!b64 || bytes > MAX_BYTES) return json({ error: "The image is missing or larger than 4 MB." }, 400);
  const head = atob(b64.slice(0, 16));
  const ext = head.startsWith("\xff\xd8") ? "jpg" : head.startsWith("\x89PNG") ? "png" : head.slice(8, 12) === "WEBP" ? "webp" : null;
  if (!ext) return json({ error: "Please upload a JPEG, PNG or WebP image." }, 400);

  const day = new Date().toISOString().slice(0, 10);
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const key = `c:${day}:${ip}`;
  const used = Number((await env.LIMITS.get(key)) || 0);
  if (used >= PER_DAY && !trusted) return json({ error: "You've reached today's upload limit." }, 429);
  await env.LIMITS.put(key, String(used + 1), { expirationTtl: 172800 });

  const gh = github(env);
  try {
    const short = uid.split("-").slice(-2).join("-");
    const path = `Invicta/data/concepts/${short}-${Date.now().toString(36)}.${ext}`;
    const main = await gh("GET", "git/ref/heads/main");
    const baseSha = main.object.sha;
    const base = await gh("GET", `git/commits/${baseSha}`);
    let concepts = { schema: "invicta-atlas/concepts@1", buildings: {} };
    try {
      const f = await gh("GET", "contents/Invicta/data/concepts.json?ref=main");
      concepts = JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(f.content.replace(/\n/g, "")), (c) => c.charCodeAt(0))));
    } catch (e) { /* first one */ }
    concepts.buildings = concepts.buildings || {};
    (concepts.buildings[uid] = concepts.buildings[uid] || []).push({ file: path, title, by: name, added: day, status: "concept" });
    const blob = await gh("POST", "git/blobs", { content: b64, encoding: "base64" });
    const tree = await gh("POST", "git/trees", {
      base_tree: base.tree.sha,
      tree: [
        { path, mode: "100644", type: "blob", sha: blob.sha },
        { path: "Invicta/data/concepts.json", mode: "100644", type: "blob", content: JSON.stringify(concepts, null, 2) + "\n" },
      ],
    });
    const commit = await gh("POST", "git/commits", { message: `Concept art for ${label}: ${title}\n\nAdded on the site by ${name}.`, tree: tree.sha, parents: [baseSha] });
    const branch = `concept/${short.toLowerCase()}-${Date.now().toString(36)}`;
    await gh("POST", "git/refs", { ref: `refs/heads/${branch}`, sha: commit.sha });
    const pr = await gh("POST", "pulls", {
      title: `Concept art: ${label}`,
      head: branch,
      base: "main",
      body: `**Proposed by:** ${name} (concept art upload on the site)\n\n${title}\n\nConcept art is a look reference, not canon.\n\n![concept](https://raw.githubusercontent.com/${env.GITHUB_REPO}/${branch}/${path})`,
    });
    let merged = false;
    if (trusted) {
      const m = await gh("PUT", `pulls/${pr.number}/merge`, { merge_method: "squash", commit_title: `Concept art: ${label} (#${pr.number})` });
      merged = !!m.merged;
      if (merged) { try { await gh("DELETE", `git/refs/heads/${branch}`); } catch (e) { /* fine */ } }
    }
    try { await announce(env, name, `${merged ? "added concept art (going live)" : "sent concept art"} for ${label}`, pr.html_url); } catch (e) { /* optional */ }
    return json({ ok: true, url: pr.html_url, merged });
  } catch (err) {
    return json({ error: "Upload failed: " + String(err.message || err) }, 502);
  }
}

function github(env) {
  const base = `https://api.github.com/repos/${env.GITHUB_REPO}/`;
  return async (method, path, body) => {
    const r = await fetch(base + path, {
      method,
      headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "adxi-invicta-site" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (r.status === 204) return {};
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(`GitHub said ${r.status}${d.message ? ": " + d.message : ""}`);
    return d;
  };
}
function clean(s, n) { return String(s || "").replace(/[\u0000-\u001f]/g, "").trim().slice(0, n); }
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
}
