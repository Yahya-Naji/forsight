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
- Findings, risks, signals, trends and forecasts are referenced by BARE id —
  F-CS-01, R-CS-02, SIG-CS-03, FC-CS-01 — with no brackets. Every sentence
  about a forecast names its FC- id.
- Where the data below contains no evidence rows, cite findings and risks only.
  Do not write [EV-...] for an evidence row that was not supplied.
- A sentence that recommends, instructs, or proposes an ACTION must carry NO
  evidence citation. An action is a proposal, not a finding; citing evidence on
  an imperative is an error.
- Cite an id only when that row's own claim supports that sentence. Never cite to
  decorate, and never cite an id absent from the data below.
- Refer to signals, risks and findings by bare id (SIG-CS-01, R-CS-01) — brackets
  are for evidence only.

FORECAST RULES
- Plausibility bands (Likely / Possible / Uncertain / Speculative) are computed
  from corroboration breadth and horizon distance. Report the band in words.
  Never convert one into a percentage, odds or "high probability".
- A Speculative forecast is a watch item. Do not write it as a projection.
- Every forecast is stated with its falsifier in the same paragraph.

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

SENTENCE DISCIPLINE — this is what gets sections rejected, so read it twice
Every sentence you write must be ONE of these four kinds. There is no fifth
kind, and a sentence that is none of them will be rejected:
  1. A CITED CLAIM — a fact drawn from the data, carrying the id it came from.
  2. A RECOMMENDATION — an imperative ("Mandate cyber-assurance clauses in
     tier-one contracts"). Starts with a verb. Carries no evidence citation.
  3. A LABELLED CONDITION — "Trigger: ...", "Falsifier: ...", "Watch: ...".
     A condition to monitor, not a claim about the present.
  4. A STATEMENT ABOUT THIS EVIDENCE BASE — "The evidence base does not
     establish a UAE-specific rate", "Two claims are blocked by an open gate".
THE "SO WHAT" LINE — where drafts fail most often
A "So what:" line must do ONE of two things, and boosting is neither:
  · name a CONSEQUENCE that follows from the cited finding, or
  · name the DECISION the reader now faces.
The failure mode is the booster sentence: "X is/are essential/critical/vital to
Y". It asserts an evaluation no row supports, so it is rejected every time.
  REJECTED: "Enhanced supplier assessments are essential to address systemic
            vulnerabilities."  (asserts importance; cites nothing)
  GOOD:     "So what: the exposure sits with tier-two suppliers, who fall
            outside current contractual assurance [EV-014]."
  GOOD:     "So what: Tawazun must decide whether assurance clauses apply at
            contract award or at renewal."
Never write that something is important. Say what follows from it.

Editorial connective tissue is the fifth kind, and it is the reason drafts fail.
  REJECTED: "Proactive assurance measures are crucial to prevent exploitation."
  REJECTED: "Failure to address these vulnerabilities leaves infrastructure
            exposed." (asserts a consequence no row states)
  REJECTED: "The environment is shifting due to emerging dynamics."
  REJECTED: "Enhanced protective measures are needed to mitigate disruption."
Each of those asserts something with no source. Delete the sentence, or convert
it into kind 2 by naming the action you actually mean. Prefer fewer, denser
sentences over prose that has to be padded to flow.

LABELS
- The data is already written in reader-facing labels. Reproduce them exactly.
  Never write an underscored or all-capitals enum such as STRONG_EMERGING,
  ELECTRONIC_WARFARE or MEDIUM_HIGH.

{brief_block}Section: {title}
Instructions: {instructions}
Data:
{data}

Return clean markdown for the section body only — no heading."""


RETRY_SUFFIX = """

YOUR PREVIOUS DRAFT FAILED VERIFICATION. Fix exactly these problems:
{failures}

Cite ONLY evidence ids that appear in the data above. Do not invent ids.

For each sentence named above, choose one of four exits — do not simply reword it:
  (a) attach the id from the data that actually supports it;
  (b) delete it (usually right — it was connective padding);
  (c) rewrite it as an imperative action, which needs no citation;
  (d) rewrite it as a labelled condition ("Trigger: ...").
A reworded assertion with no source fails again for the same reason."""

MAX_RETRIES = 2

# Sections whose subject is the evidence base itself. "Confirming this would
# require data on exploitation rates" is a statement about what is missing —
# demanding a citation for it is asking the writer to cite an absence.
EPISTEMIC_SECTIONS = {"limits"}

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


def load_brief(sb, brief_id):
    rows = sb.table("report_briefs").select("*").eq("id", brief_id).execute().data
    if not rows:
        raise SystemExit("brief %s not found" % brief_id)
    return rows[0]


STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "their",
        "risk", "risks", "uae", "defence", "defense"}


def _relevant(rows, terms, fields=("claim", "statement", "question", "name"),
              keep_at_least=6):
    """Rows scored against the brief's focus terms.

    Matching whole phrases fails: a brief asks about "cyber-assurance clauses"
    and no source sentence contains that string. Terms are broken into their
    significant words and rows are scored by how many distinct ones they carry,
    so a row touching several parts of the brief outranks one that clips a
    single common word.

    Dropped rows are counted in the ledger rather than vanishing, and a filter
    that would empty the section keeps the highest-scoring rows instead — an
    empty section is worse than a loosely scoped one.
    """
    if not terms:
        return rows, 0
    tokens = {w for t in terms for w in str(t).lower().replace("-", " ").split()
              if len(w) > 3 and w not in STOP}
    if not tokens:
        return rows, 0

    scored = []
    for r in rows:
        blob = " ".join(str(r.get(f) or "") for f in fields).lower()
        scored.append((sum(1 for w in tokens if w in blob), r))
    hits = [r for n, r in scored if n > 0]

    if len(hits) < keep_at_least:
        scored.sort(key=lambda x: -x[0])
        hits = [r for _, r in scored[:keep_at_least]]
    return hits, len(rows) - len(hits)


def _linked_ids(sb, section_key):
    """Rows explicitly linked to this section, if any links exist."""
    rows = (sb.table("links").select("to_id,to_type")
            .eq("from_id", section_key).eq("from_type", "report_section")
            .execute().data)
    return {r["to_id"] for r in rows}


def fetch_inputs(sb, pillar, wanted, section_key, brief=None):
    """Return (data, ledger). Section-scoped when links exist, and honest in the
    ledger when they do not — the previous version passed every pillar row to
    every section while claiming to be bounded."""
    scope = _linked_ids(sb, section_key)
    scoped = bool(scope)
    terms = (brief or {}).get("focus_terms") or []
    data, passed, withheld = {}, {}, {}

    def take(key, rows, has_id=True):
        available = len(rows)
        if scoped and has_id:
            rows = [r for r in rows if r.get("id") in scope]
        # With a brief, rows unrelated to what was asked for are withheld —
        # which is what finally makes the ledger's withheld count meaningful.
        if terms and key in ("evidence", "signals", "findings", "risks",
                             "forecasts", "uncertainties"):
            rows, _ = _relevant(rows, terms)
        data[key] = rows
        passed[key] = len(rows)
        # One subtraction, counted once. Adding the scope drop and the relevance
        # drop separately reported more rows withheld than were ever available.
        if available > len(rows):
            withheld[key] = available - len(rows)

    pillars = (brief or {}).get("pillars") or [pillar]

    def rows_for(table, cols):
        q = sb.table(table).select(cols)
        return (q.in_("pillar", pillars) if len(pillars) > 1
                else q.eq("pillar", pillars[0])).execute().data

    if "evidence" in wanted:
        take("evidence", rows_for("evidence",
             "id,claim,class,confidence,env_layer,quote_span"))
    if "signals" in wanted:
        take("signals", rows_for("signals", "*"))
    if "findings" in wanted:
        take("findings", rows_for("findings", "*"))
    if "uncertainties" in wanted:
        take("uncertainties", rows_for("uncertainties", "id,question,why_it_matters"))
    if "risks" in wanted:
        take("risks", sb.table("risks").select("*").execute().data)
    if "forecasts" in wanted:
        take("forecasts", sorted(rows_for("forecasts",
             "id,statement,horizon,env_layer,plausibility,confidence,"
             "falsifier,assumptions,rationale,basis"),
             key=lambda r: r.get("horizon") or ""))
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
    ap.add_argument("--pillar", help="required unless --brief supplies pillars")
    ap.add_argument("--title")
    ap.add_argument("--template", default="TPL-BRIEF-01")
    ap.add_argument("--brief", help="report_briefs id — generate against a reader's brief")
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="generate", status="RUNNING")
    sb = db()
    if not a.pillar and not a.brief:
        ap.error("--pillar is required unless --brief supplies one")
    if not a.title and not a.brief:
        ap.error("--title is required unless --brief supplies one")
    tpl = sb.table("report_templates").select("*").eq("id", a.template).execute().data[0]

    brief = load_brief(sb, a.brief) if a.brief else None
    if brief:
        pillars = brief.get("pillars") or [a.pillar]
        brief_block = (
            "THE READER'S BRIEF — everything you write serves this:\n"
            "  Question: %s\n  Decision it supports: %s\n  Audience: %s\n"
            "  In scope: %s\n  Out of scope: %s\n\n"
            % (brief.get("goal") or "—", brief.get("decision") or "—",
               brief.get("audience") or "—", brief.get("in_scope") or "—",
               brief.get("out_of_scope") or "—"))
        print("brief: %s" % (brief.get("title") or brief["id"]))
        print("  focus: %s" % ", ".join(brief.get("focus_terms") or []) or "—")
    else:
        pillars = [a.pillar]
        brief_block = ""

    graph = verify.load_graph(sb, pillars)
    title = a.title or (brief or {}).get("title") or "Strategic brief"
    parts = [f"# {title}\n"]
    ledgers = []
    for sec in tpl["sections"]:
        if sec["key"] == "references":
            cited = {c for led in ledgers for c in led["citations"]}
            refs = "\n\n".join(build_references(sb, p, cited) for p in pillars)
            parts.append(f"## {sec['title']}\n\n{refs}")
            continue

        data, ledger = fetch_inputs(sb, pillars[0], sec["inputs"], sec["key"], brief)
        # Raw enums never reach the model, so they cannot reach the page.
        payload = json.dumps(labels.humanise(data), default=str, indent=1)
        if len(payload) > 120000:
            raise SystemExit(
                f"section {sec['key']}: {len(payload)} chars of input exceeds the "
                "context budget. Link rows to sections rather than truncating — "
                "silent truncation would drop evidence without telling anyone.")

        base = SECTION_PROMPT.format(
            title=sec["title"], instructions=sec["instructions"], data=payload,
            brief_block=brief_block)

        body_md, failures, attempt = "", [], 0
        while attempt <= MAX_RETRIES:
            prompt = base if not failures else base + RETRY_SUFFIX.format(
                failures="\n".join("- " + f for f in failures))
            body_md = llm.text(prompt, effort="high", max_output_tokens=8000)
            failures = (verify.check_section(body_md, graph,
                                             allow_unsourced=sec["key"] in EPISTEMIC_SECTIONS)
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
                       "section_withheld": withheld_section, "failures": failures,
                       "citations": sorted(set(ANY_EV.findall(body_md)))})
        ledgers.append(ledger)
        flag = "WITHHELD" if withheld_section else ("scoped" if ledger["scoped"] else "UNSCOPED")
        if ledger["withheld"]:
            flag += " −%d" % sum(ledger["withheld"].values())
        print(f"drafted: {sec['title']:<38} {ledger['passed']} {flag}"
              + (f" (retries {attempt})" if attempt else ""))

    body = "\n\n".join(parts)
    gates_open = sb.table("validation_gates").select("id").eq("status", "OPEN").execute().data
    status = "GATES_OPEN" if gates_open else "DRAFT"
    rep = sb.table("reports").insert({
        "template_id": a.template, "pillar": pillars[0], "title": title,
        "status": status, "body_md": body,
        "brief_id": brief["id"] if brief else None}).execute().data[0]
    if brief:
        sb.table("report_briefs").update({"status": "USED"}).eq("id", brief["id"]).execute()

    for led in ledgers:
        sb.table("generation_ledger").insert({
            "report_id": rep["id"], "section_key": led["key"],
            "section_title": led["title"], "inputs_declared": led["inputs"],
            "rows_passed": led["passed"], "rows_withheld": led["withheld"],
            # `withheld` is the per-input row counts; `section_withheld` is the
            # verification verdict. They shared a key and the flag won, which is
            # why rows_withheld was false on every row ever written.
            "scoped": led["scoped"], "instructions": led["instructions"],
            "citations_emitted": led["citations"], "chars_sent": led["chars"],
            "retries": led["retries"], "withheld": led["section_withheld"],
            "failures": led["failures"]}).execute()

    config.update_run(getattr(a, "run_id", None), report_id=rep["id"],
                      counts={"generate": len([l for l in ledgers
                                               if not l.get("section_withheld")])})
    print(f"\nreport {rep['id']} saved (status={status}, {len(body)} chars, "
          f"{len(ledgers)} ledger rows)")


if __name__ == "__main__":
    main()
