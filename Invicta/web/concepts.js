/* ADXI: Invicta site: let helpers attach concept art to a building (web copy only).
   Posts to /api/concept, which opens a proposal (or publishes at once for trusted helpers). */
(function () {
  "use strict";
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function shrink(file) {
    // Resize big images to at most 2000 px wide/high, as JPEG, so uploads stay small.
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const k = Math.min(1, 2000 / Math.max(img.width, img.height));
        const c = document.createElement("canvas");
        c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        resolve(c.toDataURL("image/jpeg", 0.85).split(",")[1]);
        URL.revokeObjectURL(img.src);
      };
      img.onerror = () => reject(new Error("That file isn't an image I can read."));
      img.src = URL.createObjectURL(file);
    });
  }

  window.adxiDeleteConcept = async function (uid, file, label) {
    if (!window.confirm(`Delete this concept art from ${label}?`)) return;
    try {
      const r = await fetch("/api/concept", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Helper-Key": localStorage.getItem("adxi.helperKey") || "", "X-Admin-Key": localStorage.getItem("adxi.adminKey") || "" },
        body: JSON.stringify({ action: "delete", uid, file, label, name: localStorage.getItem("adxi.name") || "" }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.error || "Delete failed.");
      window.alert(d.merged ? "Deleted. The site updates in a few minutes." : "Your delete request was sent to Jordan.");
    } catch (e) { window.alert(e.message); }
  };

  window.adxiAddConcept = function (uid, label) {
    const back = document.createElement("div");
    back.className = "chat-modal";
    back.innerHTML = `<form class="chat-modal-box"><h3>Add concept art</h3>
      <p>For <b>${esc(label)}</b>. Concept art shows a look or mood. It never becomes canon by itself. Jordan reviews each one.</p>
      <input type="file" accept="image/png,image/jpeg,image/webp" required>
      <input class="t" maxlength="80" placeholder="Title, e.g. Crew Lodge at night">
      <input class="n" maxlength="40" placeholder="Your name (optional)">
      <div class="chat-modal-row"><span class="msg small muted" style="flex:1"></span><button type="button" class="chat-btn">Cancel</button><button class="chat-send">Send</button></div></form>`;
    document.body.append(back);
    const form = back.querySelector("form"), msg = back.querySelector(".msg");
    back.querySelector(".n").value = localStorage.getItem("adxi.name") || "";
    back.querySelector(".chat-btn").onclick = () => back.remove();
    form.onsubmit = async (e) => {
      e.preventDefault();
      const file = form.querySelector("input[type=file]").files[0];
      if (!file) return;
      const send = form.querySelector(".chat-send");
      send.disabled = true;
      msg.textContent = "Uploading…";
      try {
        const name = form.querySelector(".n").value.trim();
        if (name) localStorage.setItem("adxi.name", name);
        const r = await fetch("/api/concept", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Helper-Key": localStorage.getItem("adxi.helperKey") || "", "X-Admin-Key": localStorage.getItem("adxi.adminKey") || "" },
          body: JSON.stringify({ uid, label, title: form.querySelector(".t").value.trim(), name, image: await shrink(file) }),
        });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.error || "Upload failed.");
        form.innerHTML = `<h3>${d.merged ? "Concept art published" : "Sent to Jordan"}</h3>
          <p>${d.merged ? "It will appear on the building in a few minutes." : "Jordan will review it. It appears on the building once approved."}</p>
          <div class="chat-modal-row"><a class="chat-btn" href="${esc(d.url)}" target="_blank" rel="noopener">View</a><button type="button" class="chat-send">Close</button></div>`;
        form.querySelector(".chat-send").onclick = () => back.remove();
      } catch (err) {
        msg.textContent = err.message;
        send.disabled = false;
      }
    };
  };
})();
