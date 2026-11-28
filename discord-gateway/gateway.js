// Avalon's always-on ear for the ADXI: Invicta Discord server.
// One Durable Object holds the Discord gateway connection. For each new message in the team's server that
// might be talking to the cast (names Avalon, Sentinel or a Governor, @mentions the bot, or replies to one of
// them), it sends the message to the site, signed with an HMAC of the bot token. The site decides who answers.
// A cron trigger pokes it every minute, so it reconnects by itself after Cloudflare restarts it.

const INTENTS = 1 | 512 | 32768;  // GUILDS, GUILD_MESSAGES, MESSAGE_CONTENT
const CAST = /\b(avalon|sentinel|aurelia|lyra|mira|vector|tessera|vesper|orin)\b/i;

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(env.GATEWAY.get(env.GATEWAY.idFromName("main")).fetch("https://gateway/poke"));
  },
  async fetch(request, env) {
    if (new URL(request.url).pathname === "/status") {
      return env.GATEWAY.get(env.GATEWAY.idFromName("main")).fetch("https://gateway/status");
    }
    return new Response("Avalon's gateway. Nothing to see here.", { status: 404 });
  },
};

export class Gateway {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.ws = null;
    this.seq = null;
    this.botId = null;
    this.lastAck = 0;
    this.timer = null;
    this.connectedAt = 0;
  }

  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path === "/status") {
      return Response.json({ connected: !!this.ws, since: this.connectedAt ? new Date(this.connectedAt).toISOString() : null });
    }
    // Reconnect if the socket is gone or has stopped answering heartbeats.
    if (!this.ws || (this.lastAck && Date.now() - this.lastAck > 120_000)) await this.connect();
    return new Response("ok");
  }

  async connect() {
    if (!this.env.DISCORD_BOT_TOKEN) return;
    try { this.ws?.close(1000); } catch { /* already closed */ }
    this.ws = null;
    clearInterval(this.timer);
    const r = await fetch("https://gateway.discord.gg/?v=10&encoding=json", { headers: { Upgrade: "websocket" } });
    const ws = r.webSocket;
    if (!ws) throw new Error("Discord didn't open a websocket (" + r.status + ")");
    ws.accept();
    this.ws = ws;
    this.connectedAt = Date.now();
    this.lastAck = Date.now();
    ws.addEventListener("message", (e) => this.onMessage(JSON.parse(e.data)).catch((err) => console.log("message error", err.message)));
    ws.addEventListener("close", (e) => { console.log("gateway closed", e.code, e.reason); if (this.ws === ws) { this.ws = null; clearInterval(this.timer); } });
    ws.addEventListener("error", () => { if (this.ws === ws) { this.ws = null; clearInterval(this.timer); } });
  }

  send(op, d) {
    this.ws?.send(JSON.stringify({ op, d }));
  }

  async onMessage(p) {
    if (p.s != null) this.seq = p.s;
    if (p.op === 10) {  // Hello: start heartbeats, then identify
      clearInterval(this.timer);
      this.timer = setInterval(() => this.send(1, this.seq), p.d.heartbeat_interval);
      this.send(2, { token: this.env.DISCORD_BOT_TOKEN, intents: INTENTS, properties: { os: "cloudflare", browser: "invicta", device: "invicta" } });
    } else if (p.op === 11) {
      this.lastAck = Date.now();
    } else if (p.op === 1) {
      this.send(1, this.seq);
    } else if (p.op === 7 || p.op === 9) {  // Reconnect / invalid session: start again
      await this.connect();
    } else if (p.op === 0 && p.t === "READY") {
      this.botId = p.d.user.id;
    } else if (p.op === 0 && p.t === "MESSAGE_CREATE") {
      await this.onDiscordMessage(p.d);
    }
  }

  async onDiscordMessage(m) {
    if (m.author?.bot || m.webhook_id || m.guild_id !== String(this.env.DISCORD_GUILD_ID)) return;
    const content = String(m.content || "");
    const mentioned = this.botId && (m.mentions || []).some((u) => u.id === this.botId);
    const ref = m.referenced_message;
    const replyToCast = ref && (ref.webhook_id || ref.author?.id === this.botId);
    if (!mentioned && !replyToCast && !CAST.test(content)) return;
    const body = JSON.stringify({
      relay: 1,
      guild_id: m.guild_id,
      channel_id: m.channel_id,
      message_id: m.id,
      content: content.slice(0, 2000),
      author: m.member?.nick || m.author.global_name || m.author.username,
      mentioned_bot: !!mentioned,
      reply_to: ref ? { name: ref.author?.username || "", content: String(ref.content || "").slice(0, 1500), cast: !!replyToCast } : null,
    });
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(this.env.DISCORD_BOT_TOKEN), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const sig = [...new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body)))].map((b) => b.toString(16).padStart(2, "0")).join("");
    const r = await fetch(this.env.SITE_URL, { method: "POST", headers: { "Content-Type": "application/json", "X-Avalon-Relay": sig }, body });
    if (!r.ok) console.log("site said", r.status, await r.text());
  }
}
