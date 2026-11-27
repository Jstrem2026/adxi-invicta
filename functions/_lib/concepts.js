// Shared: add or remove concept art in Invicta/data/concepts.json through a GitHub pull request.
// Trusted helpers (and Jordan) are merged at once.
import { announce } from "./announce.js";

export const UID_RE = /^D\d-[a-z0-9-]+-P\d+-\d+[a-z]?$/i;

export function imageExt(b64) {
  const head = atob(b64.slice(0, 16));
  return head.startsWith("\xff\xd8") ? "jpg" : head.startsWith("\x89PNG") ? "png" : head.slice(8, 12) === "WEBP" ? "webp" : null;
}

export function gh(env) {
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

async function readConcepts(g) {
  try {
    const f = await g("GET", "contents/Invicta/data/concepts.json?ref=main");
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(f.content.replace(/\n/g, "")), (c) => c.charCodeAt(0))));
  } catch (e) {
    return { schema: "invicta-atlas/concepts@1", buildings: {} };
  }
}

async function openChange(env, g, { tree, message, branchName, prTitle, prBody, name, trusted, notice }) {
  const main = await g("GET", "git/ref/heads/main");
  const baseSha = main.object.sha;
  const base = await g("GET", `git/commits/${baseSha}`);
  const t = await g("POST", "git/trees", { base_tree: base.tree.sha, tree });
  const commit = await g("POST", "git/commits", { message, tree: t.sha, parents: [baseSha] });
  const branch = `${branchName}-${Date.now().toString(36)}`;
  await g("POST", "git/refs", { ref: `refs/heads/${branch}`, sha: commit.sha });
  const pr = await g("POST", "pulls", { title: prTitle, head: branch, base: "main", body: prBody });
  let merged = false;
  if (trusted) {
    const m = await g("PUT", `pulls/${pr.number}/merge`, { merge_method: "squash", commit_title: `${prTitle} (#${pr.number})` });
    merged = !!m.merged;
    if (merged) { try { await g("DELETE", `git/refs/heads/${branch}`); } catch (e) { /* fine */ } }
  }
  try { await announce(env, name, `${notice}${merged ? " (going live)" : " (waiting for Jordan)"}`, pr.html_url); } catch (e) { /* optional */ }
  return { url: pr.html_url, number: pr.number, merged };
}

export async function addConcept(env, { uid, label, title, name, b64 }, trusted) {
  const ext = imageExt(b64);
  if (!ext) throw new Error("Please use a JPEG, PNG or WebP image.");
  const g = gh(env);
  const day = new Date().toISOString().slice(0, 10);
  const short = uid.split("-").slice(-2).join("-");
  const path = `Invicta/data/concepts/${short}-${Date.now().toString(36)}.${ext}`;
  const concepts = await readConcepts(g);
  concepts.buildings = concepts.buildings || {};
  (concepts.buildings[uid] = concepts.buildings[uid] || []).push({ file: path, title, by: name, added: day, status: "concept" });
  const blob = await g("POST", "git/blobs", { content: b64, encoding: "base64" });
  return openChange(env, g, {
    tree: [
      { path, mode: "100644", type: "blob", sha: blob.sha },
      { path: "Invicta/data/concepts.json", mode: "100644", type: "blob", content: JSON.stringify(concepts, null, 2) + "\n" },
    ],
    message: `Concept art for ${label}: ${title}\n\nAdded on the site by ${name}.`,
    branchName: `concept/${short.toLowerCase()}`,
    prTitle: `Concept art: ${label}`,
    prBody: `**Proposed by:** ${name} (concept art on the site)\n\n${title}\n\nConcept art is a look reference, not canon.`,
    name, trusted, notice: `added concept art for ${label}`,
  });
}

export async function removeConcept(env, { uid, file, label }, name, trusted) {
  const g = gh(env);
  const concepts = await readConcepts(g);
  const list = (concepts.buildings || {})[uid] || [];
  const item = list.find((c) => c.file === file);
  if (!item) throw new Error("That concept art isn't on this building.");
  concepts.buildings[uid] = list.filter((c) => c.file !== file);
  if (!concepts.buildings[uid].length) delete concepts.buildings[uid];
  return openChange(env, g, {
    tree: [
      { path: "Invicta/data/concepts.json", mode: "100644", type: "blob", content: JSON.stringify(concepts, null, 2) + "\n" },
      { path: file, mode: "100644", type: "blob", sha: null },
    ],
    message: `Remove concept art from ${label}: ${item.title || file}\n\nRequested on the site by ${name}.`,
    branchName: `concept-remove/${uid.split("-").slice(-2).join("-").toLowerCase()}`,
    prTitle: `Remove concept art: ${label}`,
    prBody: `**Requested by:** ${name}\n\nRemove "${item.title || file}" (by ${item.by || "unknown"}) from ${label}.`,
    name, trusted, notice: `asked to remove concept art from ${label}`,
  });
}
