/* ADXI: Invicta shared helper chat (web copy only; tools/export_static.py adds it).
   A floating room everyone on the site shares. Talks to /api/room. */
(function () {
  "use strict";
  const KEY_NAME = "adxi.name", KEY_ASKED = "adxi.nameAsked", KEY_CLIENT = "adxi.client", KEY_OPEN = "adxi.roomOpen", KEY_SEEN = "adxi.roomSeen";
  let client = localStorage.getItem(KEY_CLIENT);
  if (!client) { client = Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem(KEY_CLIENT, client); }
  let lastId = 0, open = false, timer = null, lastBeat = 0, unread = 0;
  const seen = Number(localStorage.getItem(KEY_SEEN) || 0);

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const name = () => localStorage.getItem(KEY_NAME) || "";

  // ---------- layout ----------
  const btn = el("button", "room-btn");
  btn.innerHTML = '<span class="room-dot"></span><span class="room-btn-label">Helpers chat</span><span class="room-badge" hidden></span>';
  const panel = el("section", "room");
  panel.setAttribute("aria-label", "Helpers chat");
  const head = el("div", "room-head");
  const title = el("div", "room-title");
  title.innerHTML = '<strong>Helpers chat</strong><span class="room-online">Connecting…</span>';
  const close = el("button", "room-x", "×");
  close.title = "Close";
  head.append(title, close);
  const who = el("div", "room-who");
  const whoLabel = el("span", null, "Posting as");
  const whoIn = el("input");
  whoIn.maxLength = 40;
  whoIn.placeholder = "Anonymous helper (add a name)";
  whoIn.value = name();
  who.append(whoLabel, whoIn);
  const log = el("div", "room-log");
  const form = el("form", "room-form");
  const input = el("input", "room-input");
  input.maxLength = 500;
  input.placeholder = "Message everyone working on the Invicta…";
  const send = el("button", "room-send", "Send");
  send.type = "submit";
  form.append(input, send);
  const note = el("div", "room-note", "Public: anyone on the site can read this. Be kind.");
  panel.append(head, who, log, form, note);
  document.body.append(panel, btn);

  whoIn.addEventListener("change", () => {
    localStorage.setItem(KEY_NAME, whoIn.value.trim());
    localStorage.setItem(KEY_ASKED, "1");
    lastBeat = 0;
  });

  function setOpen(v) {
    open = v;
    panel.classList.toggle("open", v);
    btn.classList.toggle("hidden", v);
    localStorage.setItem(KEY_OPEN, v ? "1" : "0");
    if (v) { unread = 0; badge(); localStorage.setItem(KEY_SEEN, String(lastId)); input.focus(); log.scrollTop = log.scrollHeight; }
    schedule(0);
  }
  btn.onclick = () => setOpen(true);
  close.onclick = () => setOpen(false);

  function badge() {
    const b = btn.querySelector(".room-badge");
    b.hidden = !unread;
    b.textContent = unread > 9 ? "9+" : String(unread);
  }

  const time = (ts) => new Date(ts).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  function add(m) {
    const row = el("div", "room-msg" + (m.kind === "proposal" ? " room-proposal" : ""));
    const meta = el("div", "room-meta");
    meta.append(el("strong", null, m.name), el("span", null, " · " + time(m.ts)));
    const body = el("div", "room-text");
    if (m.kind === "proposal" && m.link && /^https:\/\/github\.com\//.test(m.link)) {
      body.append(document.createTextNode(m.text + " "));
      const a = el("a", null, "View proposal");
      a.href = m.link; a.target = "_blank"; a.rel = "noopener";
      body.append(a);
    } else {
      body.textContent = m.text;
    }
    row.append(meta, body);
    const stick = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
    log.append(row);
    while (log.children.length > 200) log.firstChild.remove();
    if (stick) log.scrollTop = log.scrollHeight;
  }

  async function poll() {
    try {
      const now = Date.now();
      const beat = now - lastBeat > 30000;
      const q = new URLSearchParams({ after: String(lastId), client, name: name() });
      if (beat) q.set("beat", "1");
      const r = await fetch("/api/room?" + q, { cache: "no-store" });
      if (r.ok) {
        if (beat) lastBeat = now;
        const d = await r.json();
        const first = lastId === 0;
        for (const m of d.messages) {
          add(m);
          lastId = Math.max(lastId, m.id);
          if (!open && !first && m.id > seen) unread++;
        }
        if (first && !open) unread = d.messages.filter((m) => m.id > seen && seen > 0).length;
        if (open) localStorage.setItem(KEY_SEEN, String(lastId));
        badge();
        const n = d.online.length;
        panel.querySelector(".room-online").textContent = n === 1 ? "1 helper online" : n + " helpers online";
        btn.querySelector(".room-btn-label").textContent = n > 1 ? `Helpers chat · ${n} online` : "Helpers chat";
      } else {
        panel.querySelector(".room-online").textContent = "Chat unavailable";
      }
    } catch (e) {
      panel.querySelector(".room-online").textContent = "Reconnecting…";
    }
    schedule();
  }
  function schedule(ms) {
    clearTimeout(timer);
    const wait = ms != null ? ms : document.hidden ? 60000 : open ? 4000 : 20000;
    timer = setTimeout(poll, wait);
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden) schedule(0); });

  form.onsubmit = async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    send.disabled = true;
    try {
      const r = await fetch("/api/room", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, name: whoIn.value.trim(), client }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { add({ name: "Notice", ts: Date.now(), text: d.error || "Couldn't send that.", kind: "chat" }); }
      else { input.value = ""; schedule(0); }
    } catch (err) {
      add({ name: "Notice", ts: Date.now(), text: "Couldn't reach the chat.", kind: "chat" });
    } finally {
      send.disabled = false;
      input.focus();
    }
  };

  setOpen(localStorage.getItem(KEY_OPEN) === "1");
})();
