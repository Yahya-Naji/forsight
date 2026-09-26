"""STEP 5 — Generator (NEURAL layer, bounded).

The model receives the template instruction and the graph rows linked to one
section — nothing else. It cannot reach the rest of the register, the web, or
its own memory of the subject.

Three disciplines are enforced here rather than hoped for:
  · citations belong on factual claims, never on imperatives;
  · Class C is unproven and must be hedged, Class D marked as proposed;
  · an OPEN gate is stated once and never contradicted.

Every section writes a row to `generation_ledger` recording what was passed and
what was withheld, so "bounded generation" is auditable instead of asserted.

Usage: python generate.py --pillar CYBERSECURITY --title "..."
"""
import argparse
import json
import re

import labels
import llm
import verify
import config
from config import db

CITATION = re.compile(r"\[(EV-[A-Z0-9-]+)\]")
# The reference list must survive a model that drops the brackets.
ANY_EV = re.compile(r"\b(EV-[A-Z0-9-]+)\b")

SECTION_PROMPT = """You draft ONE section of a strategic foresight brief for the
Tawazun Council (UAE). Write ONLY from the JSON data below — no outside
knowledge, no remembered examples, no invented facts.

CITATION RULES
- Cite ONLY ids that appear in the data below. Inventing an id is the worst
  failure this system can produce.
- EVIDENCE is cited in SQUARE BRACKETS, always: [EV-004], [EV-NVD-001].
  Never (EV-004), never a bare EV-004. The brackets are what the reference
  builder and the citation audit read.
- Findings, risks, signals and trends are referenced by BARE id — F-CS-01,
  R-CS-02, SIG-CS-03 — with no brackets.
- Where the data below contains no evidence rows, cite findings and risks only.
  Do not write [EV-...] for an evidence row that was not supplied.
- A sentence that recommends, instructs, or proposes an ACTION must carry NO
  evidence citation. An action is a proposal, not a finding; citing evidence on
  an imperative is an error.
- Cite an id only when that row's own claim supports that sentence. Never cite to
  decorate, and never cite an id absent from the data below.
- Refer to signals, risks and findings by bare id (SIG-CS-01, R-CS-01) — brackets
  are for evidence only.

EVIDENCE CLASS RULES
- Class A and B may be stated as fact.
- Class C is UNPROVEN and SINGLE-SOURCE. Any sentence resting only on Class C
  must be hedged in its own words — "may", "could", "single-source and unproven",
  "not yet corroborated". Never state Class C as established fact.
- Class D is a proposed construct, not current policy. Say so.

VALIDATION GATES
- If validation_gates lists OPEN gates, state ONCE in a single sentence that the
  blocked claims require customer validation, naming what is blocked.
- Never repeat that statement. Never assert anything a gate blocks, in any wording.

OPENING RULE — enforced automatically; a generic opener is rejected and redrafted
- The first sentence must lead with a CONCRETE FACT from the data: a number, a
  named actor, a named standard or a named system, plus its citation.
- GOOD: "Thirty-six of 176 catalogued intrusion sets reference Middle East, Gulf
  or UAE targeting [EV-001]."
- REJECTED: "Enhanced cybersecurity measures are critical...", "In today's
  landscape...", "It is imperative that...", "Organisations must...".
  If your first sentence would still read sensibly with all the data deleted,
  it is the wrong sentence.

LABELS
- The data is already written in reader-facing labels. Reproduce them exactly.
  Never write an underscored or all-capitals enum such as STRONG_EMERGING,
  ELECTRONIC_WARFARE or MEDIUM_HIGH.

Section: {title}
Instructions: {instructions}
Data:
{data}

Return clean markdown for the section body only — no heading."""


RETRY_SUFFIX = """

YOUR PREVIOUS DRAFT FAILED VERIFICATION. Fix exactly these problems:
{failures}

Cite ONLY evidence ids that appear in the data above. If no id supports a
sentence, either remove the sentence or rewrite it as an action, which needs no
citation. Do not invent ids."""

MAX_RETRIES = 2

BANNED_OPENERS = (
    "enhanced", "in today", "it is imperative", "organisations must",
    "organizations must", "in an era", "as the world", "increasingly",
    "is critical to", "are critical to", "plays a vital role", "in recent years",
)


def opener_failures(markdown: str, section_key: str):
    """The executive summary must open on a fact, not a platitude.

    Instructed in the prompt and enforced here, because instruction alone did
    not hold: the model reliably opened with "Enhanced cybersecurity measures
    are critical..." until this check started rejecting it.
    """
    if section_key != "exec_summary":
        return []
    lines = [l.strip() for l in markdown.splitlines() if l.strip()
             and not l.strip().startswith(("#", "|", "-", "*", ">"))]
    if not lines:
        return []
    first = lines[0]
    low = first.lower()
    out = []
    if any(low.startswith(b) or b in low[:60] for b in BANNED_OPENERS):
        out.append("The opening sentence is generic (\"%s\"). Open with a concrete "
                   "fact from the data — a number, named actor or named standard — "
                   "and cite it." % first[:90])
    if not re.search(r"\d|\[EV-|\bF-[A-Z]{2}-\d|\bR-[A-Z]{2}-\d|\bSIG-[A-Z]{2}-\d", first):
        out.append("The opening sentence contains no specific fact or citation.")
    return out


def _dedupe_gates(rows):
    """Four identical gates printed in a row reads as a broken template. One
    entry per distinct blocked claim, with the ids it covers."""
    seen = {}
    for g in rows:
        seen.setdefault(g["blocks"], []).append(g["id"])
    return [{"gate_ids": ids, "blocks": blocks} for blocks, ids in seen.items()]


def _linked_ids(sb, section_key):
    """Rows explicitly linked to this section, if any links exist."""
    rows = (sb.table("links").select("to_id,to_type")
            .eq("from_id", section_key).eq("from_type", "report_section")
            .execute().data)
    return {r["to_id"] for r in rows}


def fetch_inputs(sb, pillar, wanted, section_key):
    """Return (data, ledger). Section-scoped when links exist, and honest in the
    ledger when they do not — the previous version passed every pillar row to
    every section while claiming to be bounded."""
    scope = _linked_ids(sb, section_key)
    scoped = bool(scope)
    data, passed, withheld = {}, {}, {}

    def take(key, rows, has_id=True):
        available = len(rows)
        if scoped and has_id:
            rows = [r for r in rows if r.get("id") in scope]
        data[key] = rows
        passed[key] = len(rows)
        if available - len(rows):
            withheld[key] = available - len(rows)

    if "evidence" in wanted:
        take("evidence", sb.table("evidence").select(
            "id,claim,class,confidence,env_layer,quote_span")
            .eq("pillar", pillar).execute().data)
    if "signals" in wanted:
        take("signals", sb.table("signals").select("*").eq("pillar", pillar).execute().data)
    if "findings" in wanted:
        take("findings", sb.table("findings").select("*").eq("pillar", pillar).execute().data)
    if "risks" in wanted:
        take("risks", sb.table("risks").select("*").execute().data)
    if "indicators" in wanted:
        rows = sb.table("indicators").select("*").execute().data
        # An indicator with no threshold cannot be monitored; rendering "TBD"
        # in a leadership brief presents a gap as if it were a control.
        usable = [r for r in rows if (r.get("threshold") or "").strip()
                  and (r.get("threshold") or "").strip().upper() not in ("TBD", "N/A", "-")]
        for r in rows:
            if r not in usable:
                sb.table("research_gaps").insert({
                    "pillar": pillar,
                    "gap": f"Indicator {r['id']} has no concrete threshold and was "
                           f"omitted from the report: {r.get('watch', '')[:180]}",
                    "raised_by": "generate.indicator_threshold"}).execute()
        take("indicators", usable)
        if len(rows) - len(usable):
            withheld["indicators"] = len(rows) - len(usable)
    if "links" in wanted:
        take("links", sb.table("links").select("*").execute().data, has_id=False)
    if "gates" in wanted:
        gates = sb.table("validation_gates").select("*").eq("status", "OPEN").execute().data
        # A cybersecurity brief has no business quoting the procurement gate.
        mine = [g for g in gates if pillar in (g.get("blocks") or "")
                or g["id"].startswith(f"VG-{pillar[:2]}-")]
        data["validation_gates"] = _dedupe_gates(mine)
        passed["gates"] = len(data["validation_gates"])
        if len(gates) - len(mine):
            withheld["gates"] = len(gates) - len(mine)

    return data, {"scoped": scoped, "passed": passed, "withheld": withheld}


def build_references(sb, pillar, cited=None):
    """One entry per DOCUMENT, listing every evidence id drawn from it.

    Keyed by evidence id, a single article appeared four times as four near
    identical lines. A reference list names sources, not rows.
    """
    by_doc = {}
    for ev in sb.table("evidence").select("id").eq("pillar", pillar).order("id").execute().data:
        if cited is not None and ev["id"] not in cited:
            continue
        srcs = (sb.table("evidence_sources")
                .select("documents(title,url,published_on,registry_id)")
                .eq("evidence_id", ev["id"]).execute().data)
        for s in srcs:
            d = s["documents"]
            rec = by_doc.setdefault(d["url"], {"doc": d, "ids": []})
            if ev["id"] not in rec["ids"]:
                rec["ids"].append(ev["id"])

    pubs = {r["id"]: r["publisher"] for r in
            sb.table("source_registry").select("id,publisher").execute().data}
    lines = []
    for url, rec in sorted(by_doc.items(), key=lambda kv: min(kv[1]["ids"])):
        d = rec["doc"]
        ids = ", ".join(sorted(rec["ids"]))
        pub = pubs.get(d.get("registry_id") or "", "")
        date = f", {d['published_on']}" if d.get("published_on") else ""
        lines.append(f"[{ids}] {d['title']} — {pub}{date}. {url}")
    return "\n\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--pillar", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--template", default="TPL-BRIEF-01")
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="generate", status="RUNNING")
    sb = db()
    tpl = sb.table("report_templates").select("*").eq("id", a.template).execute().data[0]

    graph = verify.load_graph(sb, a.pillar)
    parts = [f"# {a.title}\n"]
    ledgers = []
    for sec in tpl["sections"]:
        if sec["key"] == "references":
            cited = {c for led in ledgers for c in led["citations"]}
            parts.append(f"## {sec['title']}\n\n{build_references(sb, a.pillar, cited)}")
            continue

        data, ledger = fetch_inputs(sb, a.pillar, sec["inputs"], sec["key"])
        # Raw enums never reach the model, so they cannot reach the page.
        payload = json.dumps(labels.humanise(data), default=str, indent=1)
        if len(payload) > 120000:
            raise SystemExit(
                f"section {sec['key']}: {len(payload)} chars of input exceeds the "
                "context budget. Link rows to sections rather than truncating — "
                "silent truncation would drop evidence without telling anyone.")

        base = SECTION_PROMPT.format(
            title=sec["title"], instructions=sec["instructions"], data=payload)

        body_md, failures, attempt = "", [], 0
        while attempt <= MAX_RETRIES:
            prompt = base if not failures else base + RETRY_SUFFIX.format(
                failures="\n".join("- " + f for f in failures))
            body_md = llm.text(prompt, effort="high", max_output_tokens=8000)
            failures = (verify.check_section(body_md, graph)
                        + opener_failures(body_md, sec["key"]))
            if not failures:
                break
            attempt += 1
            if attempt <= MAX_RETRIES:
                print(f"  ! {sec['key']}: {len(failures)} verification failure(s), "
                      f"retry {attempt}/{MAX_RETRIES}")
                for f in failures[:3]:
                    print(f"      {f[:110]}")

        withheld_section = bool(failures)
        if withheld_section:
            # Better a visible hole than a plausible paragraph on a citation
            # that does not exist.
            body_md = ("_Section withheld: failed verification after "
                       f"{MAX_RETRIES} retries (see generation ledger)._")
            print(f"  ✗ {sec['key']}: WITHHELD after {MAX_RETRIES} retries")

        parts.append(f"## {sec['title']}\n\n{body_md}")
        ledger.update({"key": sec["key"], "title": sec["title"],
                       "inputs": sec["inputs"], "instructions": sec["instructions"],
                       "chars": len(payload), "retries": attempt,
                       "withheld": withheld_section, "failures": failures,
                       "citations": sorted(set(ANY_EV.findall(body_md)))})
        ledgers.append(ledger)
        flag = "WITHHELD" if withheld_section else ("scoped" if ledger["scoped"] else "UNSCOPED")
        print(f"drafted: {sec['title']:<38} {ledger['passed']} {flag}"
              + (f" (retries {attempt})" if attempt else ""))

    body = "\n\n".join(parts)
    gates_open = sb.table("validation_gates").select("id").eq("status", "OPEN").execute().data
    status = "GATES_OPEN" if gates_open else "DRAFT"
    rep = sb.table("reports").insert({
        "template_id": a.template, "pillar": a.pillar, "title": a.title,
        "status": status, "body_md": body}).execute().data[0]

    for led in ledgers:
        sb.table("generation_ledger").insert({
            "report_id": rep["id"], "section_key": led["key"],
            "section_title": led["title"], "inputs_declared": led["inputs"],
            "rows_passed": led["passed"], "rows_withheld": led["withheld"],
            "scoped": led["scoped"], "instructions": led["instructions"],
            "citations_emitted": led["citations"], "chars_sent": led["chars"],
            "retries": led["retries"], "withheld": led["withheld"],
            "failures": led["failures"]}).execute()

    config.update_run(getattr(a, "run_id", None), report_id=rep["id"],
                      counts={"generate": len([l for l in ledgers if not l["withheld"]])})
    print(f"\nreport {rep['id']} saved (status={status}, {len(body)} chars, "
          f"{len(ledgers)} ledger rows)")


if __name__ == "__main__":
    main()
