/* ADXI: Invicta site: header spot showing when the site is updating (web copy only).
   Reads /api/status (latest publish run). */
(function () {
  "use strict";
  const bar = document.querySelector(".top .actions") || document.querySelector(".top");
  if (!bar) return;
  const spot = document.createElement("a");
  spot.className = "upd";
  spot.target = "_blank";
  spot.rel = "noopener";
  spot.hidden = true;
  bar.prepend(spot);
  let sawUpdating = false, timer = null;

  const ago = (t) => {
    const m = Math.round((Date.now() - Date.parse(t)) / 60000);
    return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`;
  };

  async function check() {
    let next = 60000;
    try {
      const d = await (await fetch("/api/status", { cache: "no-store" })).json();
      spot.href = d.url || "#";
      spot.title = d.title ? `Latest change: ${d.title}` : "";
      spot.className = "upd upd-" + d.state;
      if (d.state === "updating") {
        sawUpdating = true;
        spot.innerHTML = '<span class="upd-dot"></span>Updating…';
        spot.hidden = false;
        next = 10000;
      } else if (d.state === "updated") {
        if (sawUpdating) {
          spot.innerHTML = '<span class="upd-dot"></span>Updated · <u>reload</u>';
          spot.removeAttribute("target");
          spot.href = "#";
          spot.onclick = (e) => { e.preventDefault(); location.reload(); };
        } else {
          spot.innerHTML = `<span class="upd-dot"></span>Updated ${ago(d.at)}`;
        }
        spot.hidden = false;
      } else if (d.state === "failed") {
        spot.innerHTML = '<span class="upd-dot"></span>Update failed';
        spot.hidden = false;
      } else {
        spot.hidden = true;
      }
    } catch (e) { /* offline: leave it */ }
    clearTimeout(timer);
    timer = setTimeout(check, document.hidden ? 300000 : next);
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden) check(); });
  check();
})();
