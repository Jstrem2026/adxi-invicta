// Avalon, the ADXI: Invicta bot for the team's Discord server. A Cloudflare Pages Function at /api/discord.
//
// Discord sends each slash command here (the "Interactions Endpoint URL" in the Discord developer page):
//   /ask question       in a deck forum, that deck's city assistant answers about that deck; anywhere else, Avalon
//   /sentinel question  Sentinel answers, from any channel, about the whole ship
//   naming them         "Mira, ...", "..., Avalon?", @Avalon, or a reply to one of them: they answer (needs the
//                       always-on gateway in discord-gateway/, which passes messages here signed with the bot token)
//   /submit file note   puts the file in Invicta/inbox/ on a new branch and opens a pull request for Jordan
// Answers come from the repo files and the scan (read only). Nothing here changes ship data directly.
// The city assistants and Sentinel post under their own names through a channel webhook the bot makes ("Invicta Voices").
//
// Settings: DISCORD_PUBLIC_KEY, DISCORD_APP_ID and DISCORD_GUILD_ID in wrangler.toml [vars] (none are secret).
// Secret DISCORD_BOT_TOKEN (Cloudflare Pages) lets it find a forum's deck and post as a city assistant; without it
// every answer comes from Avalon. Reuses the chat's ANTHROPIC_API_KEY, GITHUB_TOKEN and GITHUB_REPO.
// Commands are registered by .github/workflows/discord-commands.yml from .github/discord/commands.json.

import Anthropic from "@anthropic-ai/sdk";

const BUDGET_MS = 25_000;          // Cloudflare keeps work going about 30 s after the reply to Discord
const MAX_ROUNDS = 6;
const MAX_FILE_CHARS = 40_000;
const MAX_SUBMIT_BYTES = 2_000_000;
const SUBMIT_TYPES = /\.(json|md|txt|csv)$/i;

export async function onRequestPost({ request, env, waitUntil }) {
  const body = await request.text();
  // A message passed on by the always-on gateway (discord-gateway/), signed with the bot token.
  if (request.headers.get("X-Avalon-Relay")) return relayed(env, request, body);
  if (!env.DISCORD_PUBLIC_KEY || !(await verify(env.DISCORD_PUBLIC_KEY, request, body))) {
    return new Response("Bad signature.", { status: 401 });
  }
  const i = JSON.parse(body);
  if (i.type === 1) return json({ type: 1 });  // Discord checking the address
  if (i.type !== 2) return json({ type: 4, data: msg("I don't know that one.") });

  // Only the team's own server. Anyone else who adds the bot gets nothing (and costs nothing).
  if (!env.DISCORD_GUILD_ID || i.guild_id !== String(env.DISCORD_GUILD_ID)) {
    return json({ type: 4, data: { ...msg("This bot only works in the ADXI: Invicta server."), flags: 64 } });
  }
  if (!env.ANTHROPIC_API_KEY || !env.GITHUB_TOKEN || !env.GITHUB_REPO) {
    return json({ type: 4, data: msg("The bot isn't set up on the site yet.") });
  }
  const user = i.member?.user || i.user || {};
  const who = String(i.member?.nick || user.global_name || user.username || "someone").replace(/[\u0000-\u001f@]/g, "").slice(0, 40);
  const opts = Object.fromEntries((i.data.options || []).map((o) => [o.name, o.value]));
  const reply = (text) => fetch(`https://discord.com/api/v10/webhooks/${i.application_id}/${i.token}/messages/@original`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(msg(text)),
  });

  const fail = (e) => reply(`Sorry, that didn't work: ${e.message}`);
  if (i.data.name === "submit") {
    waitUntil(submit(env, i.data.resolved?.attachments?.[opts.file], String(opts.note || ""), who).then(reply, fail));
  } else if (i.data.name === "ask" || i.data.name === "sentinel") {
    waitUntil((async () => {
      const deck = i.data.name === "ask" ? await deckOf(env, i.channel) : null;
      const speaker = i.data.name === "sentinel" ? CAST.sentinel : deck ? GOVERNORS[deck] : CAST.avalon;
      const question = String(opts.question || "").trim().slice(0, 1000);
      const answer = await ask(env, request, question, who, speaker);
      const text = `**${who} asked:** ${question.slice(0, 300)}\n\n${answer}`;
      // Avalon is the bot itself. Everyone else speaks through the channel webhook under their own name,
      // then the bot's "thinking" message is removed. If that fails, the bot posts it, signed.
      if (speaker !== CAST.avalon && env.DISCORD_BOT_TOKEN && (await speakAs(env, i.channel, speaker, text))) {
        await fetch(`https://discord.com/api/v10/webhooks/${i.application_id}/${i.token}/messages/@original`, { method: "DELETE" });
        return;
      }
      await reply(speaker === CAST.avalon ? text : `**${speaker.name}:**\n${text}`);
    })().catch(fail));
  } else {
    return json({ type: 4, data: msg("I don't know that command.") });
  }
  return json({ type: 5 });  // "Avalon is thinking..."
}

export function onRequestGet() {
  return json({ ok: true });
}

// ---------- answering when named (from the gateway) ----------

// Someone is talking to the cast when a message starts with a name ("Mira, ..." / "hey @Vector ..."),
// ends with one ("..., Avalon?"), @mentions the bot (Avalon), or replies to one of their messages.
function addressed(content, cast) {
  const names = cast.map((c) => c.name).join("|");
  const start = new RegExp(`^\\s*(?:(?:hey|hi|hello|ok|okay|yo|dear)[\\s,]+)?@?(${names})\\b`, "i").exec(content);
  if (start) return start[1];
  const end = new RegExp(`,\\s*@?(${names})\\s*[?.!]*\\s*$`, "i").exec(content);
  return end ? end[1] : null;
}

async function relayed(env, request, body) {
  if (!env.DISCORD_BOT_TOKEN || !(await hmacOk(env.DISCORD_BOT_TOKEN, body, request.headers.get("X-Avalon-Relay")))) {
    return new Response("Bad signature.", { status: 401 });
  }
  const m = JSON.parse(body);
  if (m.guild_id !== String(env.DISCORD_GUILD_ID)) return new Response("Not our server.", { status: 403 });
  const everyone = [CAST.avalon, CAST.sentinel, ...Object.values(GOVERNORS).filter((g) => g.name !== "Sentinel")];
  const byName = (n) => everyone.find((c) => c.name.toLowerCase() === String(n || "").toLowerCase());
  let speaker = byName(addressed(String(m.content || ""), everyone));
  if (!speaker && m.reply_to?.cast) speaker = byName(m.reply_to.name) || CAST.avalon;  // replying to one of them
  if (!speaker && m.mentioned_bot) speaker = CAST.avalon;
  if (!speaker) return new Response(null, { status: 204 });

  const channel = await discord(env, "GET", `channels/${m.channel_id}`);
  const deck = await deckOf(env, channel);
  // City assistants answer only in their own deck's forum. Avalon and Sentinel answer anywhere.
  if (speaker !== CAST.avalon && speaker !== CAST.sentinel) {
    if (String(speaker.deck) !== String(deck)) {
      const where = Object.entries(DECKS).find(([, d]) => d[1] === speaker.name);
      await discord(env, "POST", `channels/${m.channel_id}/messages`, { ...msg(`${speaker.name} answers in the ${where[0]}-${where[1][0].toLowerCase()} forum. Ask there, or ask me or Sentinel here.`), message_reference: { message_id: m.message_id } }).catch(() => {});
      return new Response(null, { status: 204 });
    }
  }
  if (speaker === CAST.sentinel && deck === "4") speaker = GOVERNORS[4];
  if (!env.ANTHROPIC_API_KEY || !env.GITHUB_TOKEN) return new Response("Not set up.", { status: 503 });

  await discord(env, "POST", `channels/${m.channel_id}/typing`).catch(() => {});
  const who = String(m.author || "someone").replace(/[\u0000-\u001f@]/g, "").slice(0, 40);
  const said = String(m.content || "").slice(0, 1500);
  const context = m.reply_to ? `[Replying to ${m.reply_to.name}: "${String(m.reply_to.content || "").slice(0, 800)}"]\n` : "";
  let answer;
  try {
    answer = await ask(env, request, context + said, who, speaker, 55_000);
  } catch (e) {
    answer = `Sorry, I couldn't answer that just now (${e.message}).`;
  }
  if (speaker === CAST.avalon || !(await speakAs(env, channel, speaker, answer))) {
    await discord(env, "POST", `channels/${m.channel_id}/messages`, {
      ...msg(speaker === CAST.avalon ? answer : `**${speaker.name}:** ${answer}`), message_reference: { message_id: m.message_id, fail_if_not_exists: false },
    });
  }
  return new Response("answered");
}

async function hmacOk(secret, body, sigHex) {
  if (!/^[0-9a-f]{64}$/i.test(sigHex || "")) return false;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  return crypto.subtle.verify("HMAC", key, hex(sigHex), new TextEncoder().encode(body));
}

// ---------- /ask ----------

// The cast, from canon (Docs/1_Canon_Source/Invicta/datasheets): Avalon is the Lead NPC on the Crown Bridge;
// each deck city has a digital assistant NPC who manages it until real people are hired into its career positions
// (Jordan, 28 Nov 2026: they are not Governors). Only names, decks and roles: personalities aren't designed yet.
const CAST = {
  avalon: { name: "Avalon", deck: null, who: "Avalon, the lead digital assistant of the Luxuria Invicta, who runs the ship from the Crown Bridge (canon)" },
  sentinel: { name: "Sentinel", deck: null, who: "Sentinel, the digital assistant who manages Bastion (Deck 4), the security and military city, until real people are hired into its career positions; second after Avalon in the ship's succession (canon). Like Avalon, you answer about any deck" },
};
const DECKS = {
  1: ["Solenne", "Aurelia", "Where the ship is governed"],
  2: ["Halcyon", "Lyra", "A city built to research, heal and discover"],
  3: ["Meridian", "Mira", "Where most people live, trade and play"],
  4: ["Bastion", "Sentinel", "The security and military city"],
  5: ["Aerion", "Vector", "The ship's port and flight deck, under the tallest ceiling aboard"],
  6: ["Machina", "Tessera", "The city that keeps the ship alive: power, water, air, gravity and the Drift Engine"],
  7: ["Claustra", "Vesper", "Holds whatever must be kept apart from the rest of the ship, in three containment layers"],
  8: ["Ferrum", "Orin", "Makes and stores everything the ship needs, from refined ore to finished escort cruisers"],
};
const GOVERNORS = Object.fromEntries(Object.entries(DECKS).map(([n, [city, gov, tag]]) => [n, n === "4" ? { ...CAST.sentinel, deck: 4 } :
  { name: gov, deck: Number(n), who: `${gov}, the digital assistant who manages ${city} (Deck ${n}) until real people are hired into its career positions. ${city}: ${tag} (canon). You answer only about Deck ${n}, ${city}; for another deck, point them to that deck's forum and its assistant, or to Avalon` }]));

const ASK_RULES = `You answer in the ADXI: Invicta Discord server, used by Jordan (owner and lead designer) and Kylee (designer). ADXI: Invicta is their design workspace for the Luxuria Invicta, the ship city of the Arcane Drift world. Each deck city is managed by a digital assistant NPC until real people are hired into its career positions; they are not Governors, so never call them that. City assistants: ${Object.entries(DECKS).map(([n, d]) => `Deck ${n} ${d[0]}: ${d[1]}`).join("; ")}. Avalon runs the whole ship.
Speak as your character, lightly: a line of voice is fine, but the facts matter most, because Jordan and Kylee are designing the ship. Don't invent backstory or personality; it isn't designed yet.
Answer questions about the ship from the repo files and the scan, using the tools. Be plain and brief: a short answer under 1,500 characters, Discord markdown, no tables.
Never invent anything that hasn't been designed: if the files don't say, say it isn't designed yet. Say whether something is canon or proposed when it matters.
Units: every number goes US first with metric in brackets, never metric first. Many files store metric only (km, m, km²): convert them yourself. Examples: 120 ft (36.6 m), 11.6 sq mi (30 km²), 21.1 mi (34.0 km).
You can't change anything. If they want a change, tell them to ask Claude on the site or in the project, or use /submit for a data file.
You have about 20 seconds, so read only what you need. Design data: Invicta/data/decks/D<n>/<district>.json. Design docs: Game/Docs/.`;

const ASK_TOOLS = [
  { name: "list_files", description: "List a folder of the repo (main). '' for the top. Folders end with '/'.",
    input_schema: { type: "object", properties: { path: { type: "string" } }, required: ["path"], additionalProperties: false } },
  { name: "read_file", description: "Read a text file from the repo (main). Long files are cut; use start_line to read on.",
    input_schema: { type: "object", properties: { path: { type: "string" }, start_line: { type: "integer" } }, required: ["path"], additionalProperties: false } },
  { name: "get_scan", description: "Progress figures and open scan issues (errors, warnings, waiting on Jordan, not designed yet).",
    input_schema: { type: "object", properties: {}, additionalProperties: false } },
];

async function ask(env, request, question, who, speaker, budget = BUDGET_MS) {
  if (!question) return "Ask me something about the ship.";
  const start = Date.now();
  const gh = github(env);
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const system = [{ type: "text", text: ASK_RULES + (await guide(gh)) }, { type: "text", text: `\n\nYou are ${speaker.who}.` }];
  const messages = [{ role: "user", content: `[From ${who}]\n\n${question}` }];
  for (let round = 0; round < MAX_ROUNDS; round++) {
    const late = Date.now() - start > budget - 8_000;
    const m = await client.messages.create({
      model: env.QUESTION_MODEL || "claude-haiku-5-5",
      max_tokens: 1200,
      system,
      tools: late ? undefined : ASK_TOOLS,
      messages,
    }, { timeout: Math.max(4_000, budget - (Date.now() - start)) });
    const uses = m.content.filter((c) => c.type === "tool_use");
    const text = m.content.filter((c) => c.type === "text").map((c) => c.text).join("\n").trim();
    if (!uses.length || late) return text || "I couldn't find an answer in time. Try asking more narrowly.";
    messages.push({ role: "assistant", content: m.content });
    const results = [];
    for (const u of uses) {
      let out;
      try { out = await runTool(gh, u.name, u.input || {}, request); } catch (e) { out = "Error: " + e.message; }
      results.push({ type: "tool_result", tool_use_id: u.id, content: String(out) });
    }
    messages.push({ role: "user", content: results });
  }
  return "That needed more digging than I can do here. Try a narrower question, or ask Claude on the site.";
}

let cachedGuide = null, guideAt = 0;
async function guide(gh) {
  if (cachedGuide !== null && Date.now() - guideAt < 10 * 60_000) return cachedGuide;
  let out = "";
  for (const p of ["Invicta/CLAUDE.md", "Invicta/data/README.md"]) {
    try { out += `\n\n<file path="${p}">\n${(await gh.raw(p)).slice(0, 30_000)}\n</file>`; } catch { /* missing is fine */ }
  }
  cachedGuide = out; guideAt = Date.now();
  return out;
}

async function runTool(gh, name, input, request) {
  if (name === "list_files") {
    const items = await gh.get(`contents/${encodePath(cleanPath(input.path || "", true))}?ref=main`);
    if (!Array.isArray(items)) return "That is a file. Use read_file.";
    return items.map((f) => (f.type === "dir" ? f.name + "/" : `${f.name} (${f.size} bytes)`)).join("\n") || "(empty)";
  }
  if (name === "read_file") {
    const raw = await gh.raw(cleanPath(input.path));
    if (/[\x00-\x08\x0E-\x1F]/.test(raw.slice(0, 2000))) return "That is a binary file.";
    const lines = raw.split("\n");
    let out = "", n = Math.max(1, input.start_line || 1);
    for (; n <= lines.length && out.length < MAX_FILE_CHARS; n++) out += `${n}\t${lines[n - 1]}\n`;
    return out + (n <= lines.length ? `\n[Cut at line ${n - 1} of ${lines.length}. Use start_line ${n}.]` : "");
  }
  if (name === "get_scan") {
    const r = await fetch(new URL("/api/all.json", request.url));
    if (!r.ok) return "The scan results aren't available right now.";
    const d = await r.json();
    const issues = (d.issues || []).filter((x) => !x.known).map((x) => ({ severity: x.severity, title: x.title, where: x.where || x.deck }));
    return JSON.stringify({ progress: d.progress, issues }).slice(0, 40_000);
  }
  throw new Error("Unknown tool " + name);
}

// ---------- /submit ----------

async function submit(env, file, note, who) {
  if (!file || !file.url) throw new Error("no file was attached.");
  const name = String(file.filename || "file.txt");
  if (!SUBMIT_TYPES.test(name)) throw new Error("send a .json, .md, .txt or .csv file.");
  if (file.size > MAX_SUBMIT_BYTES) throw new Error("the file is over 2 MB.");
  const r = await fetch(file.url);
  if (!r.ok) throw new Error(`couldn't download the file (${r.status}).`);
  const text = await r.text();
  if (text.length > MAX_SUBMIT_BYTES) throw new Error("the file is over 2 MB.");

  // Checks before it goes to Jordan.
  const checks = [];
  if (/\.json$/i.test(name)) {
    try {
      const d = JSON.parse(text);
      checks.push("Valid JSON.");
      if (d && d.schema) checks.push(`Schema: \`${String(d.schema).slice(0, 60)}\`.`);
    } catch (e) {
      throw new Error(`the JSON doesn't parse (${e.message}). Ask ChatGPT for valid JSON and try again.`);
    }
  }
  checks.push(`${text.split("\n").length} lines, ${text.length.toLocaleString("en-US")} characters.`);

  const gh = github(env);
  const day = new Date().toISOString().slice(0, 10);
  const safe = (s) => s.toLowerCase().replace(/[^a-z0-9.]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  const path = `Invicta/inbox/${day}-${safe(who) || "someone"}-${safe(name)}`;
  const base = (await gh.get("git/ref/heads/main")).object.sha;
  const baseCommit = await gh.get(`git/commits/${base}`);
  const tree = await gh.post("git/trees", { base_tree: baseCommit.tree.sha, tree: [{ path, mode: "100644", type: "blob", content: text }] });
  const title = `From Discord: ${name.slice(0, 60)} (${who})`;
  const commit = await gh.post("git/commits", { message: `${title}\n\nSent with /submit in the ADXI: Invicta Discord server.`, tree: tree.sha, parents: [base] });
  const branch = `inbox/${safe(who) || "someone"}-${Date.now().toString(36)}`;
  await gh.post("git/refs", { ref: `refs/heads/${branch}`, sha: commit.sha });
  const pr = await gh.post("pulls", {
    title, head: branch, base: "main",
    body: `**Sent by:** ${who}, with /submit in Discord\n\n**Note:** ${note.trim() || "(none)"}\n\n**File:** \`${path}\`\n\n` +
      `**Checks:** ${checks.join(" ")}\n\n` +
      "The file only lands in `Invicta/inbox/`, so merging this changes nothing on the map. " +
      "To build it into the ship, ask Claude in the project to fold this file into the right deck data and design doc.",
  });
  return `📥 Got **${name}** from ${who}. ${checks.join(" ")}\nIt's waiting for Jordan as pull request #${pr.number}: <${pr.html_url}>`;
}

// ---------- speaking as a city assistant ----------

// Which deck a channel belongs to: a forum named "1-solenne" or "deck-1-solenne", or a post inside one.
const channelNames = new Map();
async function deckOf(env, channel) {
  if (!channel) return null;
  let name = channel.name || "";
  if ([10, 11, 12].includes(channel.type) && channel.parent_id) {
    name = channelNames.get(channel.parent_id);
    if (name === undefined && env.DISCORD_BOT_TOKEN) {
      try { name = (await discord(env, "GET", `channels/${channel.parent_id}`)).name || ""; } catch { name = ""; }
      channelNames.set(channel.parent_id, name);
    }
  }
  const m = /^(?:deck-?)?([1-8])-/i.exec(name || "");
  return m ? m[1] : null;
}

// Posts as the speaker through the "Invicta Voices" webhook of the channel (or of the forum, for a post in it).
const hooks = new Map();
async function speakAs(env, channel, speaker, text) {
  try {
    const inThread = [10, 11, 12].includes(channel.type) && channel.parent_id;
    const home = inThread ? channel.parent_id : channel.id;
    let hook = hooks.get(home);
    if (!hook) {
      const list = await discord(env, "GET", `channels/${home}/webhooks`);
      hook = list.find((h) => h.name === "Invicta Voices" && h.token) || (await discord(env, "POST", `channels/${home}/webhooks`, { name: "Invicta Voices" }));
      hooks.set(home, hook);
    }
    const r = await fetch(`https://discord.com/api/v10/webhooks/${hook.id}/${hook.token}${inThread ? `?thread_id=${channel.id}` : ""}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...msg(text), username: speaker.name }),
    });
    if (!r.ok) { hooks.delete(home); return false; }
    return true;
  } catch {
    return false;
  }
}

async function discord(env, method, path, body) {
  const r = await fetch(`https://discord.com/api/v10/${path}`, {
    method, headers: { Authorization: `Bot ${env.DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(10_000),
  });
  if (!r.ok) throw new Error(`Discord said ${r.status}.`);
  return r.json();
}

// ---------- helpers ----------

async function verify(publicKeyHex, request, body) {
  const sig = request.headers.get("X-Signature-Ed25519") || "";
  const ts = request.headers.get("X-Signature-Timestamp") || "";
  if (!/^[0-9a-f]{128}$/i.test(sig) || !ts) return false;
  try {
    const key = await crypto.subtle.importKey("raw", hex(publicKeyHex), { name: "Ed25519" }, false, ["verify"]);
    return await crypto.subtle.verify("Ed25519", key, hex(sig), new TextEncoder().encode(ts + body));
  } catch {
    return false;
  }
}

function hex(s) {
  const b = new Uint8Array(s.length / 2);
  for (let k = 0; k < b.length; k++) b[k] = parseInt(s.substr(k * 2, 2), 16);
  return b;
}

function github(env) {
  const base = `https://api.github.com/repos/${env.GITHUB_REPO}/`;
  const headers = { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "adxi-invicta-discord" };
  const call = async (method, p, b) => {
    const r = await fetch(base + p, { method, headers, body: b ? JSON.stringify(b) : undefined, signal: AbortSignal.timeout(15_000) });
    if (r.status === 404) throw new Error("not found in the repo.");
    if (!r.ok) throw new Error(`GitHub said ${r.status}.`);
    return r.json();
  };
  return {
    get: (p) => call("GET", p),
    post: (p, b) => call("POST", p, b),
    raw: async (path) => {
      const r = await fetch(base + `contents/${encodePath(path)}?ref=main`, { headers: { ...headers, Accept: "application/vnd.github.raw+json" }, signal: AbortSignal.timeout(15_000) });
      if (r.status === 404) throw new Error("not found in the repo.");
      if (!r.ok) throw new Error(`GitHub said ${r.status}.`);
      return r.text();
    },
  };
}

function cleanPath(p, allowEmpty = false) {
  const s = String(p || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  if (s.split("/").some((x) => x === ".." || x === ".")) throw new Error("bad path.");
  if (!s && !allowEmpty) throw new Error("no path given.");
  return s;
}

function encodePath(p) {
  return p.split("/").map(encodeURIComponent).join("/");
}

function msg(content) {
  return { content: String(content).slice(0, 1990), allowed_mentions: { parse: [] } };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });
}
