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
  // Attach images (resized in the browser) and show what the person is looking at.
  const attach = el("button", "chat-attach", "+");
  attach.type = "button";
  attach.title = "Attach an image, PDF or Word document";
  const picker = el("input");
  picker.type = "file";
  picker.accept = "image/png,image/jpeg,image/webp,application/pdf,.pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  picker.multiple = true;
  picker.hidden = true;
  const tray = el("div", "chat-tray");
  const here = el("div", "chat-here");
  let pending = [];  // images: base64 JPEG strings
  let pendingDocs = [];  // {name, pdf: base64} or {name, text}
  const PDF_MAX = 8 * 1024 * 1024, DOCX_MAX = 10 * 1024 * 1024, TEXT_MAX = 150000;
  attach.onclick = () => picker.click();
  const readB64 = (f) => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.onerror = rej; r.readAsDataURL(f); });
  let mammothReady = null;
  const loadMammoth = () => mammothReady || (mammothReady = new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js";
    s.onload = () => res(window.mammoth); s.onerror = () => rej(new Error("Couldn't load the Word reader."));
    document.head.append(s);
  }));
  picker.onchange = async () => {
    for (const f of [...picker.files]) {
      const n = f.name.toLowerCase();
      try {
        if (n.endsWith(".pdf") || f.type === "application/pdf") {
          if (pendingDocs.length >= 2) { note("Up to 2 documents per message."); continue; }
          if (f.size > PDF_MAX) { note(`${f.name} is ${(f.size / 1048576).toFixed(1)} MB. PDFs can be up to 8 MB (about 100 pages).`, "msg-error"); continue; }
          pendingDocs.push({ name: f.name, pdf: await readB64(f) });
        } else if (n.endsWith(".docx")) {
          if (pendingDocs.length >= 2) { note("Up to 2 documents per message."); continue; }
          if (f.size > DOCX_MAX) { note(`${f.name} is too big (Word files up to 10 MB).`, "msg-error"); continue; }
          const m = await loadMammoth();
          const out = await m.extractRawText({ arrayBuffer: await f.arrayBuffer() });
          let text = (out.value || "").trim();
          if (!text) { note(`${f.name} has no readable text.`, "msg-error"); continue; }
          if (text.length > TEXT_MAX) { text = text.slice(0, TEXT_MAX); note(`${f.name} is long, so only the first ${TEXT_MAX.toLocaleString()} characters were attached.`); }
          pendingDocs.push({ name: f.name, text });
        } else if (n.endsWith(".doc")) {
          note("Old .doc files can't be read. Save it as .docx or PDF and try again.", "msg-error");
        } else {
          if (pending.length >= 3) { note("Up to 3 images per message."); continue; }
          pending.push(await shrinkImage(f));
        }
      } catch (e) { note(`Couldn't read ${f.name}.`, "msg-error"); }
    }
    picker.value = "";
    drawTray();
  };
  function drawTray() {
    tray.innerHTML = "";
    pending.forEach((b, i) => {
      const t = el("span", "chat-thumb");
      t.innerHTML = `<img src="data:image/jpeg;base64,${b}" alt=""><button type="button" title="Remove">×</button>`;
      t.querySelector("button").onclick = () => { pending.splice(i, 1); drawTray(); };
      tray.append(t);
    });
    pendingDocs.forEach((d, i) => {
      const t = el("span", "chat-thumb chat-doc");
      t.innerHTML = `<span>📄 ${esc(d.name)}</span><button type="button" title="Remove">×</button>`;
      t.querySelector("button").onclick = () => { pendingDocs.splice(i, 1); drawTray(); };
      tray.append(t);
    });
    tray.hidden = !pending.length && !pendingDocs.length;
  }
  tray.hidden = true;
  form.append(attach, picker, input, send);
  window.addEventListener("hashchange", () => setTimeout(showHere, 50));
  setTimeout(showHere, 800);

  panel.append(head, log, here, tray, form);
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
      keyIn.placeholder = "Helper key, or Jordan's owner key";
      keyIn.value = localStorage.getItem(KEY_HELPER) || "";
      box.append(nameIn, keyIn, row);
      back.append(box);
      document.body.append(back);
      nameIn.focus();
      const done = (save) => {
        if (save) {
          localStorage.setItem(KEY_NAME, nameIn.value.trim());
          if (keyIn.value.trim()) localStorage.setItem(KEY_HELPER, keyIn.value.trim()); else localStorage.removeItem(KEY_HELPER);
          setTimeout(whoami, 100);
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
  // Show whether this browser is recognised as Jordan or a trusted helper (their changes go live at once).
  const who = el("div", "chat-who");
  title.append(who);
  async function whoami() {
    try {
      const r = await fetch("/api/whoami", { headers: { "X-Helper-Key": localStorage.getItem("adxi.helperKey") || "", "X-Admin-Key": localStorage.getItem("adxi.adminKey") || "" } });
      const d = await r.json();
      who.textContent = d.name ? `✓ Recognised as ${d.name}: your changes go live right away` : "";
    } catch (e) { who.textContent = ""; }
  }
  whoami();
  window.addEventListener("storage", whoami);

  // After a change merges, wait for the site to republish, then reload the map data in place.
  function watchPublish(card) {
    const started = Date.now();
    let sawRun = false;
    const tick = async () => {
      if (Date.now() - started > 6 * 60000) { card.querySelector("strong").textContent = "Change approved · reload the page in a minute"; return; }
      try {
        const d = await (await fetch("/api/status", { cache: "no-store" })).json();
        if (d.state === "updating") sawRun = true;
        if (d.state === "updated" && (sawRun || Date.parse(d.at) > started)) {
          await new Promise((r) => setTimeout(r, 4000));  // let the new files reach the edge
          if (typeof load === "function") await load();
          card.querySelector("strong").textContent = "Change published · now showing on the map";
          return;
        }
        if (d.state === "failed") { card.querySelector("strong").textContent = "Change approved, but publishing failed (see the top bar)"; return; }
      } catch (e) { /* keep waiting */ }
      setTimeout(tick, 8000);
    };
    setTimeout(tick, 8000);
  }

  // ---------- what the person is looking at ----------
  function current() {
    // app.js keeps its lookups in top-level D and IX.
    const ix = (typeof IX !== "undefined" && IX) || {};
    const h = location.hash.replace(/^#\/?/, "") || "dashboard";
    const [kind, a, b] = h.split("/").map(decodeURIComponent);
    const ctx = { page: kind, route: "#/" + h };
    let label = { dashboard: "Progress page", issues: "Issues list", sources: "Sources list", help: "Help" }[kind] || "The whole ship";
    try {
      if (kind === "deck" && ix.decks && ix.decks[+a]) { const d = ix.decks[+a]; ctx.deck = `Deck ${d.n} ${d.name}`; label = ctx.deck; }
      if (kind === "district" && ix.districts && ix.districts[a]) { const x = ix.districts[a]; ctx.deck = `Deck ${x.deck}`; ctx.district = x.name; ctx.district_id = a; label = x.name; }
      const pr = kind === "precinct" ? ix.precincts[a] : kind === "block" ? ix.precincts[a] : kind === "building" && ix.buildings[a] ? ix.precincts[ix.buildings[a].precinct_uid] : null;
      if (pr) {
        const x = ix.districts[pr.district_id], ps = ix.psets && ix.psets[pr.district_id];
        Object.assign(ctx, { deck: `Deck ${pr.deck}`, district: x && x.name, precinct: `${pr.id} ${pr.name}`, precinct_uid: pr.uid, data_file: ps && ps.file, design_doc: ps && ps.doc });
        label = `${pr.id} ${pr.name}`;
      }
      if (kind === "block" && pr) {
        const blk = (pr.blocks || []).find((q) => q.id === b);
        ctx.block = blk ? `${blk.name} (${blk.id})` : b;
        if (blk) ctx.block_contents = (blk.contents || []).map((c) => c.id || c.name || c).slice(0, 30);
        label = blk ? `${blk.name} · ${blk.id}` : `Block ${b}`;
      }
      if (kind === "building" && ix.buildings[a]) {
        const bd = ix.buildings[a];
        ctx.building = { uid: bd.uid, id: bd.id, name: bd.name, status: bd.status, kind: bd.kind, size: bd.size_text, address: bd.address,
          blocks: bd.blocks, rect_km: bd.rect_km, height_m: bd.height_m, floors: bd.floors, capacity: bd.capacity, entrances: bd.entrances,
          structure: bd.structure, look: bd.look, services: bd.services, interior: bd.interior, notes: bd.notes };
        const cs = ((typeof D !== "undefined" && D && D.concepts && D.concepts.buildings) || {})[bd.uid];
        if (cs) ctx.building.concept_art = cs.map((c) => c.title);
        label = `${bd.id} ${bd.name}`;
      }
      const svg = document.getElementById("map");
      if (svg) ctx.map_view_km = svg.getAttribute("viewBox");
    } catch (e) { /* keep what we have */ }
    return { ctx, label };
  }
  function viewContext() { return JSON.stringify(current().ctx).slice(0, 3000); }
  function showHere() { here.textContent = "Looking at: " + current().label; }
  function shrinkImage(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const k = Math.min(1, 1568 / Math.max(img.width, img.height));
        const c = document.createElement("canvas");
        c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(img.src);
        resolve(c.toDataURL("image/jpeg", 0.85).split(",")[1]);
      };
      img.onerror = reject;
      img.src = URL.createObjectURL(file);
    });
  }

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
          if (c.type === "text") bubble("user", esc(c.text.replace(/^(\[\d+ image\(s\)[^\]]*\] )?\[Helper:[^\]]*\]\n\n/, "")).replace(/\n/g, "<br>"));
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
    const text = input.value.trim() || (pendingDocs.length ? "(see the attached document)" : pending.length ? "(see the attached image)" : "");
    if (!text || busy) return;
    const imgs = pending.slice(), docs = pendingDocs.slice();
    pending = []; pendingDocs = []; drawTray();
    if (!localStorage.getItem(KEY_ASKED)) await askName();
    busy = true;
    send.disabled = true;
    input.value = "";
    bubble("user", imgs.map((b) => `<img class="chat-img" src="data:image/jpeg;base64,${b}" alt="">`).join("") + docs.map((d) => `<div class="chat-docline">📄 ${esc(d.name)}</div>`).join("") + esc(text).replace(/\n/g, "<br>"));
    const out = bubble("assistant", '<span class="chat-typing">Thinking…</span>');
    let acc = "";
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Helper-Key": localStorage.getItem("adxi.helperKey") || "", "X-Admin-Key": localStorage.getItem("adxi.adminKey") || "" },
        body: JSON.stringify({ messages: history, text, images: imgs, docs, name: localStorage.getItem(KEY_NAME) || "", view: viewContext() }),
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
            card.innerHTML = `<strong>${data.merged ? "Change approved · publishing…" : "Proposal sent to Jordan"}</strong><span>${esc(data.title)}</span>`;
            if (data.merged) watchPublish(card);
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
