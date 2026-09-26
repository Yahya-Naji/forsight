"""Render a generated report as a standalone HTML document.

The markdown in `reports.body_md` is the payload; the value is in what surrounds
it — every citation resolved to its claim, quote span, source and tier, plus the
verification result and the generation ledger. A report nobody can audit is just
prose.

  python export_html.py --report <uuid> --out ../design/report.html
"""
import argparse, html, json, os, re
from config import db

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "design", "templates", "report.html")

# The model writes both [EV-001] and [EV-021, EV-022]; style every id in either.
CITE = re.compile(r"\[((?:EV-[A-Z0-9-]+)(?:\s*,\s*EV-[A-Z0-9-]+)*)\]")
SIG  = re.compile(r"\b(SIG-[A-Z]{2}-\d+|R-[A-Z]{2}-\d+|F-[A-Z]{2}-\d+|TR-[A-Z]{2}-\d+)\b")


def md_to_html(md, known):
    out, in_tbl = [], False
    for line in md.splitlines():
        s = line.rstrip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            tag = "th" if not in_tbl else "td"
            if not in_tbl:
                out.append('<div class="tw"><table>'); in_tbl = True
            out.append("<tr>" + "".join(f"<{tag}>{inline(c, known)}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_tbl:
            out.append("</table></div>"); in_tbl = False
        if not s:
            continue
        if s.startswith("### "): out.append(f"<h4>{inline(s[4:], known)}</h4>")
        elif s.startswith("## "): out.append(f'<h3 id="{s[3:].lower().replace(" ","-")}">{inline(s[3:], known)}</h3>')
        elif s.startswith("# "):  continue
        elif re.match(r"^\d+\.\s", s): out.append(f"<p class='li'>{inline(s, known)}</p>")
        elif s.startswith(("- ", "* ")): out.append(f"<p class='li'>{inline(s[2:], known)}</p>")
        else: out.append(f"<p>{inline(s, known)}</p>")
    if in_tbl: out.append("</table></div>")
    return "\n".join(out)


def inline(t, known):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    def cite(m):
        i = m.group(1)
        ok = i in known
        cls = "c" if ok else "c bad"
        title = "" if ok else ' title="cites evidence that does not exist"'
        return f'<span class="{cls}" data-ev="{i}"{title}>{i}</span>'
    t = CITE.sub(cite, t)
    t = SIG.sub(lambda m: f'<span class="obj">{m.group(1)}</span>', t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sb = db()

    rep = sb.table("reports").select("*").eq("id", a.report).execute().data[0]
    ev = {e["id"]: e for e in sb.table("evidence").select("*").eq("pillar", rep["pillar"]).execute().data}
    led = sb.table("generation_ledger").select("*").eq("report_id", a.report).order("id").execute().data
    regs = {r["id"]: r for r in sb.table("source_registry").select("*").execute().data}

    src = {}
    for eid in ev:
        rows = (sb.table("evidence_sources").select("documents(title,url,registry_id)")
                .eq("evidence_id", eid).execute().data)
        for r in rows:
            d = r["documents"]; reg = regs.get(d.get("registry_id") or "", {})
            src[eid] = {"title": d["title"], "url": d["url"],
                        "pub": reg.get("publisher", "—"), "tier": reg.get("tier", 4)}

    payload = {k: {"claim": v["claim"], "cls": v["class"], "conf": v["confidence"],
                   "layer": v["env_layer"], "quote": v.get("quote_span") or "",
                   "src": src.get(k, {})} for k, v in ev.items()}

    gates = sb.table("validation_gates").select("*").execute().data

    # Paper cannot be clicked, so the apparatus becomes a printed appendix:
    # every cited row with its claim, verbatim span, publisher and tier.
    cited = sorted(set(re.findall(r"\b(EV-[A-Z0-9-]+)\b", rep["body_md"] or "")))
    apx = ['<h3>Appendix A — Evidence register</h3>']
    for i in cited:
        e = ev.get(i)
        if not e:
            apx.append(f'<div class="apx"><div class="ah">{i} — NOT IN REGISTER</div>'
                       f'<div class="ac">Cited in the body but absent from the graph; '
                       f'flagged by the citation check.</div></div>')
            continue
        s_ = src.get(i, {})
        q = html.escape((e.get("quote_span") or "")[:400])
        apx.append(
            f'<div class="apx"><div class="ah">{i} · Class {e["class"]} · {e["confidence"]} · {e["env_layer"]}</div>'
            f'<div class="ac">{html.escape(e["claim"])}</div>'
            + (f'<div class="aq">“{q}”</div>' if q else "")
            + f'<div class="as">{html.escape(s_.get("pub","—"))} · Tier {s_.get("tier","?")} · '
              f'{html.escape((s_.get("url") or "")[:95])}</div></div>')
    open_g = [g for g in gates if g["status"] == "OPEN"]
    apx.append('<h3 style="margin-top:16px">Appendix B — Validation gates</h3>')
    for g in gates:
        apx.append(f'<div class="apx"><div class="ah">{g["id"]} · {g["status"]}</div>'
                   f'<div class="ac">{html.escape(g["blocks"])}</div>'
                   f'<div class="as">raised by {html.escape(g.get("raised_by") or "—")}</div></div>')
    apx.append('<h3 style="margin-top:16px">Appendix C — Generation ledger</h3>')
    for l in led:
        apx.append(f'<div class="apx"><div class="ah">{html.escape(l["section_title"] or "")}</div>'
                   f'<div class="as">passed {json.dumps(l["rows_passed"])} · '
                   f'withheld {json.dumps(l["rows_withheld"])} · '
                   f'{"scoped" if l["scoped"] else "UNSCOPED"} · '
                   f'{l.get("chars_sent","?")} chars sent</div></div>')
    appendix = "\n".join(apx)
    body = md_to_html(rep["body_md"] or "", set(ev))
    tmpl = open(TEMPLATE, encoding="utf-8").read()
    out = (tmpl.replace("{{TITLE}}", html.escape(rep["title"]))
               .replace("{{BODY}}", body)
               .replace("{{DATA}}", json.dumps(payload))
               .replace("{{LEDGER}}", json.dumps(led, default=str))
               .replace("{{GATES}}", json.dumps(gates))
               .replace("{{STATUS}}", rep["status"])
               .replace("{{NEV}}", str(len(ev)))
               .replace("{{APPENDIX}}", appendix))
    open(a.out, "w", encoding="utf-8").write(out)
    print(f"wrote {a.out} ({len(out)} chars, {len(ev)} evidence, {len(led)} ledger rows)")


if __name__ == "__main__":
    main()
