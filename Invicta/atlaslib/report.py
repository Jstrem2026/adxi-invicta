"""Plain-text scan report (Markdown), for the console, for Claude sessions, and
for reports/scan_report.md."""

SEV_NAME = {"error": "Errors", "warning": "Warnings (continuity)", "decision": "Waiting on Jordan", "gap": "Not designed yet"}


def report_md(data):
    m, issues, pr = data["model"], data["issues"], data["progress"]
    out = ["# ADXI: Invicta — scan report", "",
           "Scanned %s from `%s` (%d ms)." % (m["generated"], m["root"], data.get("scan_ms", 0)), "",
           "## Progress", "",
           "Design coverage: precinct plans cover %s km² of %s (%.1f%%)." % (pr["planned_area_km2"], pr["total_area_text"], pr["planned_pct"]), "",
           "| Level | Done | Of | State | Note |", "|---|---|---|---|---|"]
    for lv in pr["levels"]:
        out.append("| %s | %s | %s | %s | %s |" % (lv["level"], lv["have"], lv["of"] if lv["of"] is not None else "—", lv["state"], lv["note"]))
    out += ["", "Canon errata rows: %d decided, %d waiting." % (pr["errata"]["decided"], pr["errata"]["proposed"]), ""]
    counts = {}
    for i in issues:
        counts.setdefault(i["severity"], [0, 0])[1 if i["known"] else 0] += 1
    out += ["## Issues", ""]
    for sev in ("error", "warning", "decision", "gap"):
        c = counts.get(sev, [0, 0])
        out.append("- %s: %d%s" % (SEV_NAME[sev], c[0], " (+%d known)" % c[1] if c[1] else ""))
    # Open items first, by severity; items already accepted as known go in one section at the end.
    groups = [(SEV_NAME[sev], [i for i in issues if i["severity"] == sev and not i.get("known")]) for sev in ("error", "warning", "decision", "gap")]
    groups.append(("Accepted as known (no action needed)", [i for i in issues if i.get("known")]))
    for title, rows in groups:
        if not rows:
            continue
        out += ["", "### %s" % title, ""]
        for i in rows:
            line = "- **%s** — %s" % (i["title"], i["detail"])
            if i.get("path"):
                line += " `%s`" % i["path"]
            if i.get("known"):
                line += " _(known: %s)_" % i["known"]
            if i.get("fix"):
                line += " Fix: %s" % i["fix"]
            line += " [%s]" % i["id"]
            out.append(line)
    out.append("")
    return "\n".join(out)
