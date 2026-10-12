"""Freeze what a report cites, at the moment it is issued (migration 034).

Synthesis and forecasting rebuild their objects, so the ids a report cites can
disappear from the live graph the next day. generate.py calls freeze() right
after saving a report; the reading view resolves citations from the frozen rows.

  python citations.py --report <uuid>     # freeze one report
  python citations.py --missing           # freeze every report without rows
"""
from __future__ import annotations

import argparse
import re

from config import db

CITE_ID = re.compile(r"\b(?:EV|F|SIG|R|TR|VG|FC|CU|U|FIG)-[A-Z0-9]+(?:-[A-Z0-9]+)?\b")


def cited_ids(body_md: str) -> list:
    """Ids cited in the prose. The references list is excluded: it is rebuilt
    from these rows, and it cites nothing the prose does not."""
    prose = body_md.split("\n## References", 1)[0]
    return sorted(set(CITE_ID.findall(prose)))


def _chunks(items, n=150):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _rows(sb, table, cols, ids):
    out = []
    for c in _chunks(ids):
        out += sb.table(table).select(cols).in_("id", c).execute().data
    return out


def resolve(sb, ids) -> list:
    """One row per id that exists in the live graph, shaped for report_citations."""
    by = lambda p: [i for i in ids if i.startswith(p + "-")]
    rows = []

    ev = by("EV")
    if ev:
        docs = {}
        for c in _chunks(ev):
            for l in (sb.table("evidence_sources")
                      .select("evidence_id,documents(title,url,published_on,registry_id)")
                      .in_("evidence_id", c).execute().data):
                if l.get("documents") and l["evidence_id"] not in docs:
                    docs[l["evidence_id"]] = l["documents"]
        reg_ids = sorted({d["registry_id"] for d in docs.values() if d.get("registry_id")})
        regs = {r["id"]: r for r in _rows(sb, "source_registry", "id,publisher,tier", reg_ids)}
        for e in _rows(sb, "evidence", "id,claim,quote_span,class", ev):
            d = docs.get(e["id"]) or {}
            g = regs.get(d.get("registry_id")) or {}
            rows.append({"cited_id": e["id"], "kind": "evidence", "text": e["claim"],
                         "quote": e.get("quote_span"), "class": e.get("class"),
                         "publisher": g.get("publisher"), "tier": g.get("tier"),
                         "url": d.get("url"), "doc_title": d.get("title"),
                         "published": d.get("published_on")})

    for f in _rows(sb, "findings", "id,statement", by("F")):
        rows.append({"cited_id": f["id"], "kind": "finding", "text": f["statement"]})
    for s in _rows(sb, "signals", "id,statement,strength", by("SIG")):
        rows.append({"cited_id": s["id"], "kind": "signal", "text": s["statement"],
                     "strength": s.get("strength")})
    for r in _rows(sb, "risks", "id,statement", by("R")):
        rows.append({"cited_id": r["id"], "kind": "risk", "text": r["statement"]})
    for t in _rows(sb, "trends", "id,name,statement", by("TR")):
        rows.append({"cited_id": t["id"], "kind": "trend", "text": t.get("statement") or t.get("name")})
    for g in _rows(sb, "validation_gates", "id,gate,status", by("VG")):
        rows.append({"cited_id": g["id"], "kind": "gate", "text": g["gate"], "status": g.get("status")})
    for f in _rows(sb, "forecasts", "id,statement", by("FC")):
        rows.append({"cited_id": f["id"], "kind": "forecast", "text": f["statement"]})
    return rows


def freeze(sb, report_id: str, body_md: str) -> int:
    """Write the frozen citation rows for one report. Idempotent."""
    rows = resolve(sb, cited_ids(body_md))
    for r in rows:
        r["report_id"] = report_id
    for c in _chunks(rows, 200):
        sb.table("report_citations").upsert(c, on_conflict="report_id,cited_id").execute()
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="Freeze a report's citations")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--report")
    g.add_argument("--missing", action="store_true")
    a = ap.parse_args()
    sb = db()
    if a.report:
        reports = sb.table("reports").select("id,body_md").eq("id", a.report).execute().data
    else:
        have = {r["report_id"] for r in sb.table("report_citations").select("report_id").execute().data}
        reports = [r for r in sb.table("reports").select("id,body_md").execute().data if r["id"] not in have]
    for r in reports:
        ids = cited_ids(r.get("body_md") or "")
        n = freeze(sb, r["id"], r.get("body_md") or "")
        print("report %s: %d of %d cited ids frozen%s" % (
            r["id"][:8], n, len(ids), "" if n == len(ids) else " (the rest no longer exist)"))


if __name__ == "__main__":
    main()
