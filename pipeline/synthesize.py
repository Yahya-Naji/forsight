"""STEP 4.5 — Synthesiser: the missing stage between evidence and the report.

Before this stage the graph stopped at `evidence`: nothing ever created a
signal, trend, finding, risk or uncertainty, so the generator had raw claims and
no analysis to write from.

The split is the same one the rest of the pipeline uses:

  NEURAL    the model may only PROPOSE groupings — which claims belong together,
            what they collectively indicate, what remains unknown.
  SYMBOLIC  admission rules decide what actually enters the graph, and every
            score (signal strength, likelihood, impact) is COMPUTED here. The
            model is never asked for one and is never believed if it offers one.

Anything the rules refuse is written to `research_gaps` rather than dropped —
what the evidence could not support is itself a finding (report §22).

Usage: python synthesize.py --pillar ELECTRONIC_WARFARE [--replace] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from pydantic import BaseModel, Field

import llm
import rules
import config
from config import db

PILLAR_CODE = {"CYBERSECURITY": "CS", "AI": "AI",
               "ELECTRONIC_WARFARE": "EW", "PROCUREMENT": "PR"}

# Admission thresholds — the symbolic contract for entering the graph.
MIN_EVIDENCE_PER_SIGNAL = 2      # a single source is a claim, not a signal
MIN_PUBLISHERS_PER_SIGNAL = 2    # ...and two rows from one publisher are one source
MIN_SIGNALS_PER_TREND = 1
MIN_SIGNALS_PER_FINDING = 1
MIN_FINDINGS_PER_RISK = 1
STRONG_CLASSES = ("A", "B")
EFFORT = os.environ.get("SYNTH_EFFORT", "high")   # reasoning effort for synthesis calls


# --------------------------------------------------------------------------
# what the model is allowed to propose
# --------------------------------------------------------------------------
class SignalProposal(BaseModel):
    key: str = Field(description="short key unique in this response: S1, S2, ...")
    statement: str = Field(min_length=20, max_length=400)
    evidence_ids: List[str] = Field(min_length=2)
    direction: str = Field(description="STRENGTHENING | UNCERTAIN | WEAKENING")
    env_layer: str = Field(description="UAE | REGIONAL | GLOBAL")
    steep: List[str] = Field(min_length=1)
    # NOTE: no strength — rules.py computes it from corroboration counts.


class TrendProposal(BaseModel):
    name: str = Field(min_length=5, max_length=120)
    statement: str = Field(min_length=20, max_length=600)
    signal_refs: List[str] = Field(min_length=1,
        description="keys (S1) of signals proposed in this response, or ids (SIG-CS-04) of existing signals")
    direction: str = "UNCERTAIN"


# A finding must assert something that could turn out to be false. The
# benchmark's findings all discriminate — X rather than Y, X causes Y, X is
# actually Z. Ours were restating topics: "enhanced cybersecurity measures are
# critical" is true with the evidence deleted, so it is not a finding.
BOOSTER_PLATITUDE = re.compile(
    r"\b(is|are|remains?|becomes?|be)\s+(increasingly\s+|a\s+|an\s+)?"
    r"(critical|crucial|essential|important|vital|pivotal|key|necessary|"
    r"paramount|priority|imperative)\b", re.I)
VAGUE_IMPERATIVE = re.compile(
    r"\b(must|should)\s+(prioriti[sz]e|enhance|improve|strengthen|adopt|embrace|"
    r"focus on|invest in|consider)\b", re.I)

# Markers of a claim that discriminates between possibilities.
DISCRIMINATING = re.compile(
    r"\b(more|less|rather than|instead of|not merely|not only|beyond|outpaces?|"
    r"faster than|slower than|outstrips?|exceeds?|"                  # comparative
    r"because|therefore|so that|drives?|causes?|creates?|compresses?|reduces?|"
    r"enables?|weakens?|undermines?|erodes?|shifts?|displaces?|"     # causal
    r"in its own right|is actually|amounts? to|means? that|"         # reframing
    r"becom\w+|determinant|enabler|bottleneck|constraint|prerequisite|"
    r"precondition|centre of gravity|center of gravity|"             # reclassifying
    r"cannot|will not|no longer|ceases? to|fails? to|"               # negation
    r"insufficient|inadequate|not enough|leaves? \w+ exposed|"       # sufficiency
    r"only)\b"                                                       # limiting
    r"|\bnot\s+(\w+\s+){0,4}alone\b"                              # "…not X alone"
    r"|\b(must|should)\s+be\s+(?!.*\b(critical|essential|important|priority)\b)",
    re.I)


def _is_platitude(text: str) -> tuple:
    """Return (rejected, reason). Deterministic, so it cannot be argued with."""
    if BOOSTER_PLATITUDE.search(text):
        return True, "asserts that something is important rather than what is true"
    if VAGUE_IMPERATIVE.search(text):
        return True, "is a generic recommendation, not an analytical conclusion"
    if not DISCRIMINATING.search(text):
        return True, ("makes no discriminating claim — it does not say X rather "
                      "than Y, X causes Y, or X is actually Z")
    return False, ""


class FindingProposal(BaseModel):
    statement: str = Field(min_length=20, max_length=600)
    signal_refs: List[str] = Field(min_length=1,
        description="keys (S1) of signals proposed in this response, or ids (SIG-CS-04) of existing signals")
    topic_ids: List[str] = Field(default_factory=list)


class RiskProposal(BaseModel):
    statement: str = Field(min_length=20, max_length=400)
    finding_refs: List[str] = Field(min_length=1,
        description="ids (F-CS-02) or exact statements of supporting findings")
    response: Optional[str] = None
    # NOTE: no likelihood/impact — computed below from the evidence base.


class UncertaintyProposal(BaseModel):
    question: str = Field(min_length=15, max_length=400)
    why_it_matters: str = Field(min_length=15, max_length=600)


class Synthesis(BaseModel):
    signals: List[SignalProposal] = Field(default_factory=list)
    trends: List[TrendProposal] = Field(default_factory=list)
    findings: List[FindingProposal] = Field(default_factory=list)
    risks: List[RiskProposal] = Field(default_factory=list)
    uncertainties: List[UncertaintyProposal] = Field(default_factory=list)


PROMPT = """You are the synthesis stage of a strategic-foresight pipeline for the
UAE (Tawazun Council), working on {scope}.

Below is the complete evidence register for this pillar. Every row is already
typed and sourced; class and confidence were assigned by a rules engine.

Your job is to GROUP, not to assert. Specifically:
- signals: what the evidence collectively indicates. Give each signal a key
  (S1, S2, ...). Each signal MUST cite at least {min_ev} DIFFERENT evidence ids
  from DIFFERENT publishers. A claim supported by one source is not a signal.
- trends: the longer-run direction several signals point in.
  Cite signals by key (S1) for signals you propose here, or by id (SIG-CS-04)
  for signals already in the graph. Never restate a signal's text as a reference.
- findings: what follows analytically. A finding must be a claim that COULD BE
  FALSE. Test it: if the sentence stays true with all the evidence deleted, it
  is not a finding.
    GOOD  "RF jamming can no longer be assumed to defeat every drone class once
           fibre-optic control spreads."
    GOOD  "GNSS interference is becoming a persistent operating condition in the
           Gulf rather than an occasional hazard."
    GOOD  "Software-defined EW moves vendor lock-in from hardware to threat
           libraries and update rights."
    BAD   "Electronic warfare is increasingly important."      (true regardless)
    BAD   "Forces must prioritise robust anti-jam measures."   (a platitude)
  Every finding must discriminate: X rather than Y, X causes Y, or X is actually
  Z. Findings that merely name a topic are rejected automatically.
- risks: what could go wrong for UAE defence readiness, traceable to findings.
- uncertainties: high-impact things the evidence genuinely does NOT settle.

Hard rules:
- Use ONLY the evidence below. Do not add outside knowledge or examples.
- Reference evidence by its exact id (EV-xxx). Inventing an id invalidates the item.
- Do NOT assign strength, likelihood, impact, confidence or score anywhere. Those
  are computed by a rules engine and any value you supply is discarded.
- Class C evidence is unproven and single-source. It may support an uncertainty
  or a weak signal; it may not carry a finding on its own.
- Do NOT assert a UAE-specific capability gap. Evidence at the GLOBAL or REGIONAL
  layer does not transfer to a UAE conclusion without UAE-layer evidence.

EVIDENCE REGISTER ({n} rows):
{register}

SIGNALS ALREADY IN THE GRAPH — reference these by id when a finding rests on
one, rather than restating them as new signals:
{existing}
"""


def _fetch_evidence(sb, pillar):
    return (sb.table("evidence")
            .select("id,claim,class,confidence,env_layer,steep,topic_id")
            .eq("pillar", pillar).is_("archived_at", "null").order("id").execute().data)


def _format_register(rows):
    # The publisher is shown because a signal needs two of them: the model
    # cannot honour a rule about sources it cannot see.
    return "\n".join(
        "%s [Class %s/%s, %s, source %s] %s" % (
            r["id"], r["class"], r["confidence"], r["env_layer"],
            r.get("publisher") or "unknown", r["claim"])
        for r in rows)




def propose(scope, evidence_rows, existing_signals) -> Synthesis:
    """NEURAL step. Returns validated proposals; nothing is trusted yet."""
    existing = "\n".join(
        "  %s [%s] %s" % (r["id"], r["strength"], r["statement"][:150])
        for r in existing_signals) or "  (none yet)"
    prompt = PROMPT.format(
        scope=scope, min_ev=MIN_EVIDENCE_PER_SIGNAL,
        n=len(evidence_rows), register=_format_register(evidence_rows),
        existing=existing)
    # Grouping evidence is the analytical step — strong deployment, high effort.
    return llm.structured(prompt, Synthesis, effort=EFFORT, max_output_tokens=16000)


# --------------------------------------------------------------------------
# SYMBOLIC admission — pure decisions, tested in tests/test_synthesize.py
# --------------------------------------------------------------------------
def signal_admission(evidence_ids, valid_ids, sources):
    """RULE corroboration_admission: a signal needs >=2 real evidence rows from
    >=2 INDEPENDENT PUBLISHERS. Two claims pulled from one article are one
    source, so they cannot make a signal — the same independence rule rules.py
    applies to class and strength. Returns (cited ids, rejection reason|None)."""
    cited = [e for e in dict.fromkeys(evidence_ids) if e in valid_ids]
    _, pubs, _ = rules.provenance(cited, sources, {})
    if len(cited) < MIN_EVIDENCE_PER_SIGNAL:
        return cited, "only %d evidence row(s)" % len(cited)
    if len(pubs) < MIN_PUBLISHERS_PER_SIGNAL:
        return cited, ("only %d independent publisher(s) behind %d evidence rows"
                       % (len(pubs), len(cited)))
    return cited, None


def finding_admission(statement, linked_signals, evidence_classes):
    """RULE finding_admission: a finding needs an admitted signal, must assert
    something that could be false, and must rest on at least one Class A/B row.
    Class C is a hypothesis; a finding built only on hypotheses is a hypothesis.
    Returns (raised_by, reason) for a rejection, or None."""
    if len(linked_signals) < MIN_SIGNALS_PER_FINDING:
        return "finding_admission", "no admitted signal behind it"
    rejected, why = _is_platitude(statement)
    if rejected:
        return "finding_substance", why
    if not set(evidence_classes) & set(STRONG_CLASSES):
        return "finding_class", "rests only on Class C/D evidence — a hypothesis, not a finding"
    return None


def risk_score(evidence_ids, by_id):
    """RULE risk_scoring: likelihood and impact are COMPUTED, never proposed.

    likelihood — how well corroborated the underlying evidence is:
        3  two or more Class A/B evidence rows behind the supporting signals
        2  exactly one Class A/B row
        1  Class C/D only
    impact — how much of the pillar's problem space the finding touches:
        3  supporting evidence spans 3+ distinct topics
        2  spans 2 topics
        1  spans 1 topic
    """
    strong = [e for e in evidence_ids if by_id.get(e, {}).get("class") in STRONG_CLASSES]
    topics = {by_id.get(e, {}).get("topic_id") for e in evidence_ids} - {None}
    likelihood = 3 if len(strong) >= 2 else 2 if len(strong) == 1 else 1
    impact = 3 if len(topics) >= 3 else 2 if len(topics) == 2 else 1
    return likelihood, impact, len(strong), len(topics)


# --------------------------------------------------------------------------
# ids are never reused
# --------------------------------------------------------------------------
CITED_ID = re.compile(r"\b((?:SIG|TR|F|R|CU)-[A-Z]{2}-)(\d+)\b")


class IdMinter:
    """Mints ids above the highest ever seen — in the tables or cited by any
    stored report. Highest-plus-one over the live table alone would reissue
    SIG-CS-01 after a --replace, and every old report citing SIG-CS-01 would
    silently point at a different signal. Built before anything is cleared."""

    def __init__(self, sb):
        self.top = defaultdict(int)
        for table in ("signals", "trends", "findings", "risks", "uncertainties"):
            for r in rules._all(lambda: sb.table(table).select("id")):
                self._see(r["id"])
        for r in rules._all(lambda: sb.table("reports").select("body_md")):
            self._see(r.get("body_md") or "")

    def _see(self, text):
        for prefix, n in CITED_ID.findall(text):
            self.top[prefix] = max(self.top[prefix], int(n))

    def next(self, prefix):
        self.top[prefix] += 1
        return "%s%02d" % (prefix, self.top[prefix])


# --------------------------------------------------------------------------
# writes — skipped entirely in a dry run
# --------------------------------------------------------------------------
class Writer:
    def __init__(self, sb, pillar, dry_run, topic=None):
        self.sb, self.pillar, self.dry_run, self.topic = sb, pillar, dry_run, topic
        self.gaps = 0

    def insert(self, table, row):
        if not self.dry_run:
            self.sb.table(table).insert(row).execute()

    def gap(self, text, raised_by):
        self.gaps += 1
        self.insert("research_gaps", {"pillar": self.pillar, "gap": text[:500],
                                      "raised_by": raised_by})
        # A dry run is for reading the decisions, so it shows them whole.
        print("  GAP  %s: %s" % (raised_by, text if self.dry_run else text[:88]))


def clear_pillar(sb, pillar):
    """--replace: remove this pillar's synthesis and everything hanging off it.
    Called only after the model has answered, so a failed call never leaves the
    pillar empty."""
    ids = {}
    for table in ("signals", "trends", "findings", "risks", "uncertainties"):
        ids[table] = [r["id"] for r in rules._all(
            lambda: sb.table(table).select("id").eq("pillar", pillar))]
    clear_ids(sb, ids, pillar)


def derived_only_from(links, sources):
    """Targets every one of whose incoming links comes from `sources` — the
    objects that lose all support when `sources` are removed, and only those."""
    incoming = defaultdict(set)
    for frm, to in links:
        incoming[to].add(frm)
    return {to for to, frms in incoming.items() if frms and frms <= set(sources)}


def branch_ids(sb, topic_ids):
    """--replace --node: the synthesis that belongs to these topics alone.

    A signal is cleared only if every evidence row behind it sits in these
    topics; trends and findings only if every signal behind them is cleared;
    risks only if every finding behind them is. Anything with support outside
    the branch survives."""
    topics = set(topic_ids)
    topic_of = {r["id"]: r["topic_id"] for r in
                rules._all(lambda: sb.table("evidence").select("id,topic_id"))}
    evidence_of = defaultdict(list)
    for r in rules._all(lambda: sb.table("signal_evidence").select("signal_id,evidence_id")):
        evidence_of[r["signal_id"]].append(r["evidence_id"])
    signals = {s for s, evs in evidence_of.items()
               if evs and all(topic_of.get(e) in topics for e in evs)}
    links = rules._all(lambda: sb.table("links").select("from_id,to_id"))
    sig_links = [(l["from_id"], l["to_id"]) for l in links if l["from_id"].startswith("SIG-")]
    derived = derived_only_from(sig_links, signals)
    find_links = [(l["from_id"], l["to_id"]) for l in links if l["from_id"].startswith("F-")]
    findings = {d for d in derived if d.startswith("F-")}
    risks = {r for r in derived_only_from(find_links, findings) if r.startswith("R-")}
    uncertainties = [r["id"] for chunk in _chunks(list(topics)) for r in
                     sb.table("uncertainties").select("id").in_("topic_id", chunk).execute().data]
    return {"signals": sorted(signals),
            "trends": sorted(d for d in derived if d.startswith("TR-")),
            "findings": sorted(findings), "risks": sorted(risks),
            "uncertainties": uncertainties}


def clear_ids(sb, ids, label):
    """Delete synthesis objects and everything hanging off them, in dependency order."""
    every = [i for v in ids.values() for i in v]
    for chunk in _chunks(ids["findings"]):
        sb.table("implications").delete().in_("finding_id", chunk).execute()
    for chunk in _chunks(ids["trends"]):
        sb.table("cross_impacts").delete().in_("from_trend", chunk).execute()
        sb.table("cross_impacts").delete().in_("to_trend", chunk).execute()
    for chunk in _chunks(ids["uncertainties"]):
        sb.table("scenario_uncertainties").delete().in_("uncertainty_id", chunk).execute()
    for chunk in _chunks(every):
        sb.table("links").delete().in_("from_id", chunk).execute()
        sb.table("links").delete().in_("to_id", chunk).execute()
    for table in ("risks", "findings", "trends", "uncertainties", "signals"):
        for chunk in _chunks(ids[table]):
            sb.table(table).delete().in_("id", chunk).execute()
    print("cleared %s: %s" % (label, ", ".join("%d %s" % (len(v), k) for k, v in ids.items())))


def _chunks(items, n=200):
    for i in range(0, len(items), n):
        yield items[i:i + n]


# --------------------------------------------------------------------------
# admission against the graph
# --------------------------------------------------------------------------
def admit_signals(w, minter, proposals, evidence_rows, sources, evidence_of):
    valid_ids = {r["id"] for r in evidence_rows}
    code = PILLAR_CODE[w.pillar]
    admitted = {}
    for prop in proposals:
        unknown = [e for e in prop.evidence_ids if e not in valid_ids]
        if unknown:
            print("  drop unknown evidence ids %s" % unknown)
        cited, reason = signal_admission(prop.evidence_ids, valid_ids, sources)
        if reason:
            w.gap("Proposed signal not admitted (%s): %s" % (reason, prop.statement),
                  "corroboration_admission")
            continue
        sig_id = minter.next("SIG-%s-" % code)
        w.insert("signals", {
            "id": sig_id, "pillar": w.pillar, "statement": prop.statement,
            "strength": "WEAK",                 # placeholder; rules.py recomputes
            "direction": prop.direction if prop.direction in
                         ("STRENGTHENING", "UNCERTAIN", "WEAKENING") else "UNCERTAIN",
            "steep": prop.steep, "env_layer": prop.env_layer,
        })
        for ev_id in cited:
            w.insert("signal_evidence", {"signal_id": sig_id, "evidence_id": ev_id})
        evidence_of[sig_id] = cited
        admitted[prop.statement] = sig_id
        if prop.key:
            admitted[prop.key.strip()] = sig_id
        print("  RULE corroboration_admission %s <- %d evidence %s"
              % (sig_id, len(cited), cited))
    return admitted


def _signal_lookup(existing_signals, signal_map):
    """Every signal in the pillar, addressable by id OR by statement text.

    The model references signals however it saw them in the prompt; matching on
    one form only silently discards good findings.
    """
    lookup = dict(signal_map)
    for sig_id in signal_map.values():
        lookup[sig_id] = sig_id
    for row in existing_signals:
        lookup[row["id"]] = row["id"]
        lookup[row["statement"]] = row["id"]
        lookup[row["statement"].strip().rstrip(".")] = row["id"]
    return lookup


def _resolve(lookup, refs):
    return list(dict.fromkeys(
        lookup.get(s) or lookup.get(s.strip().rstrip("."))
        for s in refs if lookup.get(s) or lookup.get(s.strip().rstrip("."))))


def admit_trends(w, minter, proposals, lookup):
    code = PILLAR_CODE[w.pillar]
    for prop in proposals:
        linked = _resolve(lookup, prop.signal_refs)
        if len(linked) < MIN_SIGNALS_PER_TREND:
            w.gap("Proposed trend had no admitted signal behind it: %s" % prop.name,
                  "trend_admission")
            continue
        tr_id = minter.next("TR-%s-" % code)
        w.insert("trends", {
            "id": tr_id, "pillar": w.pillar, "name": prop.name,
            "statement": prop.statement,
            "direction": prop.direction if prop.direction in
                         ("STRENGTHENING", "UNCERTAIN", "WEAKENING") else "UNCERTAIN",
        })
        for sig_id in linked:
            w.insert("links", {"from_id": sig_id, "from_type": "signal",
                               "to_id": tr_id, "to_type": "trend", "rel": "feeds"})
        print("  RULE trend_admission %s <- %d signal(s)" % (tr_id, len(linked)))


def admit_findings(w, minter, proposals, lookup, evidence_of, by_id):
    code = PILLAR_CODE[w.pillar]
    admitted = {}
    for prop in proposals:
        linked = _resolve(lookup, prop.signal_refs)
        classes = [by_id.get(e, {}).get("class") for s in linked for e in evidence_of.get(s, [])]
        rejection = finding_admission(prop.statement, linked, classes)
        if rejection:
            raised_by, why = rejection
            w.gap("Finding rejected — %s: %s" % (why, prop.statement), raised_by)
            continue
        f_id = minter.next("F-%s-" % code)
        w.insert("findings", {"id": f_id, "statement": prop.statement, "pillar": w.pillar})
        for sig_id in linked:
            w.insert("links", {"from_id": sig_id, "from_type": "signal",
                               "to_id": f_id, "to_type": "finding", "rel": "derivedFrom"})
        admitted[prop.statement] = (f_id, linked)
        print("  RULE finding_admission %s <- %d signal(s)" % (f_id, len(linked)))
    return admitted


def admit_risks(w, minter, proposals, finding_lookup, evidence_of, by_id):
    code = PILLAR_CODE[w.pillar]
    for prop in proposals:
        linked = [finding_lookup[s] for s in prop.finding_refs if s in finding_lookup]
        if len(linked) < MIN_FINDINGS_PER_RISK:
            w.gap("Proposed risk had no admitted finding behind it: %s" % prop.statement,
                  "risk_admission")
            continue
        finding_ids = [f for f, _ in linked]
        ev_ids = {e for _, sigs in linked for s in sigs for e in evidence_of.get(s, [])}
        likelihood, impact, n_strong, n_topics = risk_score(ev_ids, by_id)
        r_id = minter.next("R-%s-" % code)
        w.insert("risks", {"id": r_id, "statement": prop.statement, "pillar": w.pillar,
                           "likelihood": likelihood, "impact": impact,
                           "response": prop.response})
        for f_id in finding_ids:
            w.insert("links", {"from_id": f_id, "from_type": "finding",
                               "to_id": r_id, "to_type": "risk", "rel": "feeds"})
        print("  RULE risk_scoring %s -> L%d x I%d = %d "
              "(%d Class A/B evidence, %d topics)"
              % (r_id, likelihood, impact, likelihood * impact, n_strong, n_topics))


def admit_uncertainties(w, minter, proposals):
    # No admission rule yet: every proposed uncertainty is recorded.
    code = PILLAR_CODE[w.pillar]
    for prop in proposals:
        cu_id = minter.next("CU-%s-" % code)
        w.insert("uncertainties", {"id": cu_id, "pillar": w.pillar, "topic_id": w.topic,
                                   "question": prop.question,
                                   "why_it_matters": prop.why_it_matters})
        print("  %s %s" % (cu_id, prop.question[:80]))


def _existing_graph(sb, signal_ids):
    """Existing signals (with their evidence) and the findings derived from
    them (with their signals), for the model to build on when not replacing."""
    signals, evidence_of = [], defaultdict(list)
    for chunk in _chunks(sorted(signal_ids)):
        signals += sb.table("signals").select("id,statement,strength").in_("id", chunk).execute().data
        for r in sb.table("signal_evidence").select("signal_id,evidence_id") \
                   .in_("signal_id", chunk).execute().data:
            evidence_of[r["signal_id"]].append(r["evidence_id"])
    signals.sort(key=lambda r: r["id"])
    signals_of = defaultdict(list)
    for chunk in _chunks(sorted(signal_ids)):
        for l in sb.table("links").select("from_id,to_id").in_("from_id", chunk) \
                   .like("to_id", "F-%").execute().data:
            signals_of[l["to_id"]].append(l["from_id"])
    findings = []
    for chunk in _chunks(sorted(signals_of)):
        findings += sb.table("findings").select("id,statement").in_("id", chunk).execute().data
    return signals, evidence_of, findings, signals_of


def synthesize_scope(sb, minter, scope, pillar, evidence_rows, sources, replace,
                     dry_run, topic=None, proposed=None):
    """Propose, then admit, for one scope: a whole pillar or one topic."""
    ev_ids = {r["id"] for r in evidence_rows}
    if replace:
        signals, evidence_of, findings, signals_of = [], defaultdict(list), [], {}
    else:
        sig_ids = {r["signal_id"] for chunk in _chunks(sorted(ev_ids)) for r in
                   sb.table("signal_evidence").select("signal_id").in_("evidence_id", chunk)
                   .execute().data}
        signals, evidence_of, findings, signals_of = _existing_graph(sb, sig_ids)
    if proposed is None:
        proposed = propose(scope, evidence_rows, signals)
    print("\n== %s: %d evidence rows -> proposed %d signals, %d trends, %d findings, "
          "%d risks, %d uncertainties" % (scope, len(evidence_rows), len(proposed.signals),
                                         len(proposed.trends), len(proposed.findings),
                                         len(proposed.risks), len(proposed.uncertainties)))
    w = Writer(sb, pillar, dry_run, topic)
    by_id = {r["id"]: r for r in evidence_rows}
    signal_map = admit_signals(w, minter, proposed.signals, evidence_rows, sources, evidence_of)
    lookup = _signal_lookup(signals, signal_map)
    admit_trends(w, minter, proposed.trends, lookup)
    finding_map = admit_findings(w, minter, proposed.findings, lookup, evidence_of, by_id)
    finding_lookup = dict(finding_map)
    for f in findings:
        finding_lookup[f["id"]] = finding_lookup[f["statement"]] = (f["id"], signals_of.get(f["id"], []))
    for f_id, sigs in finding_map.values():
        finding_lookup[f_id] = (f_id, sigs)
    admit_risks(w, minter, proposed.risks, finding_lookup, evidence_of, by_id)
    admit_uncertainties(w, minter, proposed.uncertainties)
    n_sig = len(set(signal_map.values()))
    statement_of = {v: k for k, v in signal_map.items() if not re.fullmatch(r"S\d+", k)}
    statement_of.update({r["id"]: r["statement"] for r in signals})
    return {"scope": scope, "evidence": len(evidence_rows),
            "signal_rows": [(sid, statement_of.get(sid, ""), evidence_of.get(sid, []))
                            for sid in dict.fromkeys(list(statement_of))],
            "signals": (n_sig, len(proposed.signals)),
            "findings": (len(finding_map), len(proposed.findings)), "gaps": w.gaps}


# --------------------------------------------------------------------------
# branch-level findings: the analytical step a single topic cannot carry
# --------------------------------------------------------------------------
class FindingPass(BaseModel):
    findings: List[FindingProposal] = Field(default_factory=list)
    risks: List[RiskProposal] = Field(default_factory=list)


FINDING_PROMPT = """You are the analytical stage of a strategic-foresight system for the UAE's
Tawazun Council. Electronic Warfare is the core subject; Cybersecurity, AI and
Procurement matter only through their effect on EW.

Scope: the {branch} branch of the EW tree. Below are the admitted SIGNALS in this
branch. Each shows its computed strength (from independent publishers) and the
classes of the evidence behind it (A = Tier-1 fact, B = corroborated, C = single
source, unproven).

Write the FINDINGS a senior defence analyst would put in front of leadership:
claims that connect several signals into a judgement that could turn out to be
wrong. Then the RISKS those findings create for UAE defence readiness.

A finding must:
- rest on at least two signals where possible, cited by id (SIG-EW-04);
- discriminate: X rather than Y, X causes Y, X is becoming Z, X no longer holds;
- be falsifiable — if it stays true with the evidence deleted, it is not a finding;
- rest on at least one signal backed by Class A or B evidence;
- say what changes for EW capability, not that something "is important".

The standard to meet — findings of this kind:
  GOOD "RF jamming remains valuable, but it can no longer be assumed to defeat every
        drone class once fibre-optic control and visual navigation spread."
  GOOD "GNSS interference in the Gulf is shifting from an occasional hazard to a
        persistent operating condition, so navigation resilience becomes a
        baseline requirement rather than an upgrade."
  GOOD "Adaptation speed — how fast threat libraries and software can be updated —
        is becoming a readiness determinant, not a procurement detail."
  BAD  "Electronic warfare is increasingly important."            (true regardless)
  BAD  "The UAE must prioritise counter-UAS investment."          (a recommendation)
  BAD  "The UAE lacks adequate jamming coverage."                 (UAE gap — not allowed)

Hard rules:
- Use only the signals below; cite them by exact id. Invented ids are rejected.
- Never assert a UAE-specific capability gap: that needs UAE-layer evidence this
  graph does not yet hold.
- Do not assign likelihood, impact, strength or confidence — they are computed.
- Risks cite the findings they follow from, by exact statement.
- Prefer three strong findings to six weak ones.

SIGNALS ({n}):
{signals}
"""


def branch_prompt(branch_name, signal_rows, evidence_rows, sources, tiers):
    by_id = {r["id"]: r for r in evidence_rows}
    lines = []
    for sid, statement, evs in signal_rows:
        _, pubs, tl = rules.provenance(evs, sources, tiers)
        classes = "".join(sorted({by_id.get(e, {}).get("class", "?") for e in evs}))
        lines.append("  %s [%s, classes %s, %d publishers] %s" % (
            sid, rules.signal_strength(len(pubs), 1 in tl), classes, len(pubs), statement))
    return FINDING_PROMPT.format(branch=branch_name, n=len(lines), signals="\n".join(lines))


def branch_findings(sb, minter, branch_id, branch_name, pillar, signal_rows, evidence_rows,
                    sources, tiers, dry_run, proposed=None):
    """One call over a branch's signals; findings and risks admitted by the same rules."""
    by_id = {r["id"]: r for r in evidence_rows}
    evidence_of = {sid: evs for sid, _, evs in signal_rows}
    lines = []
    for sid, statement, evs in signal_rows:
        _, pubs, tl = rules.provenance(evs, sources, tiers)
        classes = "".join(sorted({by_id.get(e, {}).get("class", "?") for e in evs}))
        lines.append("  %s [%s, classes %s, %d publishers] %s" % (
            sid, rules.signal_strength(len(pubs), 1 in tl), classes, len(pubs), statement))
    if proposed is None:
        proposed = llm.structured(branch_prompt(branch_name, signal_rows, evidence_rows, sources, tiers),
                                  FindingPass, effort=EFFORT, max_output_tokens=16000)
    print("\n== branch %s: %d signals -> proposed %d findings, %d risks"
          % (branch_name, len(lines), len(proposed.findings), len(proposed.risks)))
    w = Writer(sb, pillar, dry_run)
    lookup = {sid: sid for sid, _, _ in signal_rows}
    lookup.update({st: sid for sid, st, _ in signal_rows if st})
    finding_map = admit_findings(w, minter, proposed.findings, lookup, evidence_of, by_id)
    finding_lookup = dict(finding_map)
    for f_id, sigs in finding_map.values():
        finding_lookup[f_id] = (f_id, sigs)
    admit_risks(w, minter, proposed.risks, finding_lookup, evidence_of, by_id)
    return {"scope": "branch " + branch_name, "evidence": len(evidence_rows),
            "signals": (len(lines), len(lines)),
            "findings": (len(finding_map), len(proposed.findings)), "gaps": w.gaps}


def _with_publishers(rows, sources):
    for r in rows:
        pubs = sorted({reg for _, reg in sources.get(r["id"], []) if reg})
        r["publisher"] = ", ".join(pubs) if pubs else None
    return rows


def main():
    ap = argparse.ArgumentParser(description="Evidence -> signals/trends/findings/risks")
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    scope = ap.add_mutually_exclusive_group(required=True)
    scope.add_argument("--pillar", choices=list(PILLAR_CODE),
                       help="one call over the whole pillar's evidence")
    scope.add_argument("--node", help="a tree node (EW, EA, CUAS, ...): one call per topic in "
                                      "its branch, homed or cross-linked")
    ap.add_argument("--replace", action="store_true",
                    help="clear the scope's signals/trends/findings/risks/uncertainties "
                         "and rebuild them")
    ap.add_argument("--dry-run", action="store_true",
                    help="call the model and run admission, print the outcome, write nothing")
    ap.add_argument("--workers", type=int, default=4, help="parallel model calls in --node mode")
    a = ap.parse_args()
    run_id = None if a.dry_run else a.run_id
    config.update_run(run_id, stage="synthesize", status="RUNNING")
    sb = db()
    sources, _ = rules.load_sources(sb)
    minter = IdMinter(sb)       # before any clearing, so cleared ids stay retired
    note = (" (replace)" if a.replace else "") + (" — DRY RUN, nothing is written" if a.dry_run else "")

    if a.pillar:
        evidence_rows = _with_publishers(_fetch_evidence(sb, a.pillar), sources)
        if len(evidence_rows) < MIN_EVIDENCE_PER_SIGNAL:
            print("Only %d evidence rows for %s — collect and extract more before "
                  "synthesising." % (len(evidence_rows), a.pillar))
            return
        print("Synthesising %s from %d evidence rows%s" % (a.pillar, len(evidence_rows), note))
        signals = [] if a.replace else rules._all(
            lambda: sb.table("signals").select("id,statement,strength").eq("pillar", a.pillar))
        proposed = propose("the %s pillar" % a.pillar, evidence_rows, signals)
        if a.replace and not a.dry_run:
            clear_pillar(sb, a.pillar)
        results = [synthesize_scope(sb, minter, "the %s pillar" % a.pillar, a.pillar,
                                    evidence_rows, sources, a.replace, a.dry_run,
                                    proposed=proposed)]
    else:
        topic_ids = [r["topic_id"] for r in
                     sb.rpc("node_topics", {"root": a.node}).execute().data]
        if not topic_ids:
            print("Node %s reaches no live topics." % a.node)
            return
        topics = {t["id"]: t for t in sb.table("topics").select("id,name,pillar,node_id")
                  .in_("id", topic_ids).execute().data}
        rows = _with_publishers(rules._all(
            lambda: sb.table("evidence").select("id,claim,class,confidence,env_layer,steep,topic_id")
            .in_("topic_id", topic_ids).is_("archived_at", "null").order("id")), sources)
        by_topic = defaultdict(list)
        for r in rows:
            by_topic[r["topic_id"]].append(r)
        work = [t for t in sorted(topic_ids) if len(by_topic[t]) >= MIN_EVIDENCE_PER_SIGNAL]
        skipped = sorted(set(topic_ids) - set(work))
        print("Synthesising node %s: %d topics, %d evidence rows%s" % (a.node, len(topic_ids), len(rows), note))
        if skipped:
            print("skipped (fewer than %d evidence rows): %s" % (MIN_EVIDENCE_PER_SIGNAL, ", ".join(skipped)))
        scope_of = {t: "topic %s, %s (%s pillar)" % (t, topics[t]["name"], topics[t]["pillar"]) for t in work}

        # The model calls are independent and slow; admission is sequential so
        # ids and lookups stay deterministic.
        existing = {}
        if not a.replace:
            for t in work:
                ev = {r["id"] for r in by_topic[t]}
                sig_ids = {r["signal_id"] for c in _chunks(sorted(ev)) for r in
                           sb.table("signal_evidence").select("signal_id").in_("evidence_id", c)
                           .execute().data}
                existing[t] = _existing_graph(sb, sig_ids)[0]
        with ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
            futures = {t: pool.submit(propose, scope_of[t], by_topic[t], existing.get(t, []))
                       for t in work}
            proposals = {}
            for t, f in futures.items():
                try:
                    proposals[t] = f.result()
                except Exception as exc:          # one topic failing must not sink the branch
                    print("  model call failed for %s: %s" % (t, exc))
        if a.replace and not a.dry_run:
            clear_ids(sb, branch_ids(sb, [t for t in work if t in proposals]), "node %s" % a.node)
        results = [synthesize_scope(sb, minter, scope_of[t], topics[t]["pillar"], by_topic[t],
                                    sources, a.replace, a.dry_run, topic=t, proposed=proposals[t])
                   for t in work if t in proposals]

        # Branch pass: findings across each branch's signals, grouped by home branch.
        branch_names = {n["id"]: n["name"] for n in
                        sb.table("nodes").select("id,name").eq("kind", "branch").execute().data}
        tiers = rules._registry_tiers(sb)
        by_branch = defaultdict(list)
        for t, r in zip([t for t in work if t in proposals], results):
            by_branch[topics[t]["node_id"]].append((t, r))
        lens_pillar = {"CYBER": "CYBERSECURITY", "AI": "AI", "PROCUREMENT": "PROCUREMENT"}
        jobs = {}
        for b, members in by_branch.items():
            sig_rows = [row for _, r in members for row in r["signal_rows"]]
            if len(sig_rows) >= 2 and b in branch_names:
                jobs[b] = (sig_rows, [row for t, _ in members for row in by_topic[t]])
        print("\nbranch pass: %d branches, %d at a time" % (len(jobs), a.workers), flush=True)
        with ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
            futures = {b: pool.submit(llm.structured,
                                      branch_prompt(branch_names[b], sr, er, sources, tiers),
                                      FindingPass, effort=EFFORT, max_output_tokens=16000)
                       for b, (sr, er) in jobs.items()}
            for b, f in futures.items():
                try:
                    results.append(branch_findings(sb, minter, b, branch_names[b],
                                                   lens_pillar.get(b, "ELECTRONIC_WARFARE"), *jobs[b],
                                                   sources, tiers, a.dry_run, proposed=f.result()))
                except Exception as exc:
                    print("  branch pass failed for %s: %s" % (b, exc), flush=True)

    print("\n%-58s %8s %9s %9s %5s" % ("scope", "evidence", "signals", "findings", "gaps"))
    for r in results:
        print("%-58s %8d %4d/%-4d %4d/%-4d %5d" % (r["scope"][:58], r["evidence"],
              r["signals"][0], r["signals"][1], r["findings"][0], r["findings"][1], r["gaps"]))
    print("\n%s. Run rules.py next — it computes signal strength from corroboration."
          % ("Dry run: nothing written" if a.dry_run else "Done"))


if __name__ == "__main__":
    main()
