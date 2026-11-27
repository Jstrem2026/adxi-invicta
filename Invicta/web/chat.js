/* ADXI: Invicta site chat panel. Only the web copy loads this (tools/export_static.py adds it).
   Talks to /api/chat (functions/api/chat.js in the adxi-invicta repo). */
(function () {
  "use strict";
  const KEY_HELPER = "adxi.helperKey", KEY_NAME = "adxi.name", KEY_ASKED = "adxi.nameAsked", KEY_CHAT = "adxi.chat", KEY_OPEN = "adxi.chatOpen";
  let history = [];   // full API conversation, sent back with each message
  let busy = false;

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function md(text) {
    // Small, safe Markdown: code blocks, inline code, bold, links, lists, paragraphs.
    const blocks = String(text).split(/```/);
    return blocks.map((b, i) => {
      if (i % 2) return `<pre><code>${esc(b.replace(/^\w*\n/, ""))}</code></pre>`;
      let h = esc(b)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?:;]|$)/g, "$1<em>$2</em>")
        .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      h = h.split(/\n{2,}/).map((p) => {
        const lines = p.split("\n");
        if (lines.every((l) => /^\s*([-*]|\d+\.)\s+/.test(l) || !l.trim())) {
          const ordered = /^\s*\d+\./.test(lines[0]);
          const items = lines.filter((l) => l.trim()).map((l) => `<li>${l.replace(/^\s*([-*]|\d+\.)\s+/, "")}</li>`).join("");
          return ordered ? `<ol>${items}</ol>` : `<ul>${items}</ul>`;
        }
        return `<p>${lines.join("<br>")}</p>`;
      }).join("");
      return h;
    }).join("");
  }

  // ---------- layout ----------
  const panel = el("aside", "chat");
  panel.setAttribute("aria-label", "Chat with Claude");
  const head = el("div", "chat-head");
  const title = el("div", "chat-title");
  title.innerHTML = '<strong>Work on the Invicta with Claude</strong><span>Ask questions or propose changes. Jordan reviews every change.</span>';
  const btnNew = el("button", "chat-btn", "New chat");
  const btnName = el("button", "chat-btn", "Name");
  const btnClose = el("button", "chat-btn chat-x", "×");
  btnClose.title = "Hide chat";
  head.append(title, btnName, btnNew, btnClose);
  const log = el("div", "chat-log");
  const form = el("form", "chat-form");
  const input = el("textarea", "chat-input");
  input.rows = 3;
  input.placeholder = "Ask about a deck or building, or suggest a change…";
  const send = el("button", "chat-send", "Send");
  send.type = "submit";
  form.append(input, send);
  panel.append(head, log, form);
  const tab = el("button", "chat-tab", "Chat with Claude");
  document.body.append(panel, tab);

  function setOpen(open) {
    document.body.classList.toggle("chat-open", open);
    localStorage.setItem(KEY_OPEN, open ? "1" : "0");
    window.dispatchEvent(new Event("resize"));
    if (open) input.focus();
  }
  tab.onclick = () => setOpen(true);
  btnClose.onclick = () => setOpen(false);
  setOpen(localStorage.getItem(KEY_OPEN) !== "0" && window.innerWidth > 900);

  // ---------- name pop-up ----------
  function askName() {
    return new Promise((resolve) => {
      const back = el("div", "chat-modal");
      const box = el("form", "chat-modal-box");
      box.innerHTML = '<h3>Your name (optional)</h3><p>If you want credit for your ideas, add a name. It appears on the proposals you make. No account or password.</p>';
      const nameIn = el("input");
      nameIn.maxLength = 60;
      nameIn.placeholder = "Name";
      nameIn.value = localStorage.getItem(KEY_NAME) || "";
      const row = el("div", "chat-modal-row");
      const skip = el("button", "chat-btn", "Skip");
      skip.type = "button";
      const ok = el("button", "chat-send", "Save");
      ok.type = "submit";
      row.append(skip, ok);
      const keyIn = el("input");
      keyIn.type = "password";
      keyIn.autocomplete = "off";
      keyIn.placeholder = "Helper key (only if Jordan gave you one)";
      keyIn.value = localStorage.getItem(KEY_HELPER) || "";
      box.append(nameIn, keyIn, row);
      back.append(box);
      document.body.append(back);
      nameIn.focus();
      const done = (save) => {
        if (save) {
          localStorage.setItem(KEY_NAME, nameIn.value.trim());
          if (keyIn.value.trim()) localStorage.setItem(KEY_HELPER, keyIn.value.trim()); else localStorage.removeItem(KEY_HELPER);
        }
        localStorage.setItem(KEY_ASKED, "1");
        back.remove();
        resolve();
      };
      skip.onclick = () => done(false);
      box.onsubmit = (e) => { e.preventDefault(); done(true); };
    });
  }
  btnName.onclick = askName;

  // ---------- conversation ----------
  function bubble(role, html) {
    const b = el("div", "msg msg-" + role);
    b.innerHTML = html;
    log.append(b);
    log.scrollTop = log.scrollHeight;
    return b;
  }
  function note(text, cls) {
    const n = el("div", "chat-note " + (cls || ""), text);
    log.append(n);
    log.scrollTop = log.scrollHeight;
    return n;
  }
  function welcome() {
    bubble("assistant", md("Hi! I can answer questions about the **Luxuria Invicta** and help you design it. Tell me what you'd like to add or change, and I'll turn it into a proposal for Jordan to review.\n\nTry: *What's designed on Deck 5 so far?*"));
  }

  function render() {
    log.innerHTML = "";
    welcome();
    for (const m of history) {
      if (m.role === "user") {
        for (const c of m.content || []) {
          if (c.type === "text") bubble("user", esc(c.text.replace(/^\[Helper:[^\]]*\]\n\n/, "")).replace(/\n/g, "<br>"));
        }
      } else {
        const t = (m.content || []).filter((c) => c.type === "text").map((c) => c.text).join("");
        if (t.trim()) bubble("assistant", md(t));
      }
    }
  }

  function save() {
    try { sessionStorage.setItem(KEY_CHAT, JSON.stringify(history)); } catch (e) { /* full: keep in memory */ }
  }
  try { history = JSON.parse(sessionStorage.getItem(KEY_CHAT) || "[]"); } catch (e) { history = []; }
  render();

  btnNew.onclick = () => { if (busy) return; history = []; save(); render(); };

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });

  form.onsubmit = async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text || busy) return;
    if (!localStorage.getItem(KEY_ASKED)) await askName();
    busy = true;
    send.disabled = true;
    input.value = "";
    bubble("user", esc(text).replace(/\n/g, "<br>"));
    const out = bubble("assistant", '<span class="chat-typing">Thinking…</span>');
    let acc = "";
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Helper-Key": localStorage.getItem(KEY_HELPER) || localStorage.getItem("adxi.adminKey") || "" },
        body: JSON.stringify({ messages: history, text, name: localStorage.getItem(KEY_NAME) || "", view: location.hash }),
      });
      if (!r.ok || !r.body) {
        let msg = "The chat isn't available right now.";
        try { msg = (await r.json()).error || msg; } catch (err) { /* keep default */ }
        out.innerHTML = md(msg);
        out.classList.add("msg-error");
        return;
      }
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf("\n\n")) >= 0) {
          const chunk = buf.slice(0, i);
          buf = buf.slice(i + 2);
          const ev = (chunk.match(/^event: (.*)$/m) || [])[1];
          const dataLine = (chunk.match(/^data: (.*)$/m) || [])[1];
          if (!ev || !dataLine) continue;
          const data = JSON.parse(dataLine);
          if (ev === "text") {
            acc += data.delta;
            out.innerHTML = md(acc);
            log.scrollTop = log.scrollHeight;
          } else if (ev === "tool") {
            log.insertBefore(el("div", "chat-note", data.label + "…"), out);
          } else if (ev === "proposal") {
            const card = el("a", "chat-proposal");
            card.href = data.url;
            card.target = "_blank";
            card.rel = "noopener";
            card.innerHTML = `<strong>${data.merged ? "Change published" : "Proposal sent to Jordan"}</strong><span>${esc(data.title)}</span>`;
            log.insertBefore(card, out);
          } else if (ev === "done") {
            history = data.messages;
            save();
          } else if (ev === "error") {
            out.innerHTML = md((acc ? acc + "\n\n" : "") + data.error);
            out.classList.add("msg-error");
          }
        }
      }
      if (!acc.trim() && !out.classList.contains("msg-error")) out.remove();
    } catch (err) {
      out.innerHTML = md("I couldn't reach the chat. Check your connection and try again.");
      out.classList.add("msg-error");
    } finally {
      busy = false;
      send.disabled = false;
      log.scrollTop = log.scrollHeight;
    }
  };
})();
