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

Usage: python synthesize.py --pillar ELECTRONIC_WARFARE
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from typing import List, Optional

from pydantic import BaseModel, Field

import llm
import config
from config import db

PILLAR_CODE = {"CYBERSECURITY": "CS", "AI": "AI",
               "ELECTRONIC_WARFARE": "EW", "PROCUREMENT": "PR"}

# Admission thresholds — the symbolic contract for entering the graph.
MIN_EVIDENCE_PER_SIGNAL = 2      # a single source is a claim, not a signal
MIN_SIGNALS_PER_TREND = 1
MIN_SIGNALS_PER_FINDING = 1
MIN_FINDINGS_PER_RISK = 1
STRONG_CLASSES = ("A", "B")


# --------------------------------------------------------------------------
# what the model is allowed to propose
# --------------------------------------------------------------------------
class SignalProposal(BaseModel):
    statement: str = Field(min_length=20, max_length=400)
    evidence_ids: List[str] = Field(min_length=2)
    direction: str = Field(description="STRENGTHENING | UNCERTAIN | WEAKENING")
    env_layer: str = Field(description="UAE | REGIONAL | GLOBAL")
    steep: List[str] = Field(min_length=1)
    # NOTE: no strength — rules.py computes it from corroboration counts.


class TrendProposal(BaseModel):
    name: str = Field(min_length=5, max_length=120)
    statement: str = Field(min_length=20, max_length=600)
    signal_statements: List[str] = Field(min_length=1)
    direction: str = "UNCERTAIN"


class FindingProposal(BaseModel):
    statement: str = Field(min_length=20, max_length=600)
    signal_statements: List[str] = Field(min_length=1)
    topic_ids: List[str] = Field(default_factory=list)


class RiskProposal(BaseModel):
    statement: str = Field(min_length=20, max_length=400)
    finding_statements: List[str] = Field(min_length=1)
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
UAE (Tawazun Council), working on the {pillar} pillar.

Below is the complete evidence register for this pillar. Every row is already
typed and sourced; class and confidence were assigned by a rules engine.

Your job is to GROUP, not to assert. Specifically:
- signals: what the evidence collectively indicates. Each signal MUST cite at
  least {min_ev} DIFFERENT evidence ids from the register. A claim supported by
  one source is not a signal.
- trends: the longer-run direction several signals point in.
- findings: what follows analytically, each traceable to named signals.
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
"""


def _fetch_evidence(sb, pillar):
    return (sb.table("evidence")
            .select("id,claim,class,confidence,env_layer,steep,topic_id")
            .eq("pillar", pillar).order("id").execute().data)


def _format_register(rows):
    return "\n".join(
        "%s [Class %s/%s, %s] %s" % (r["id"], r["class"], r["confidence"],
                                     r["env_layer"], r["claim"])
        for r in rows)


def propose(pillar, evidence_rows) -> Synthesis:
    """NEURAL step. Returns validated proposals; nothing is trusted yet."""
    prompt = PROMPT.format(
        pillar=pillar, min_ev=MIN_EVIDENCE_PER_SIGNAL,
        n=len(evidence_rows), register=_format_register(evidence_rows))
    # Grouping evidence is the analytical step — strong deployment, high effort.
    return llm.structured(prompt, Synthesis, effort="high", max_output_tokens=16000)


# --------------------------------------------------------------------------
# SYMBOLIC admission + computed scores
# --------------------------------------------------------------------------
def _gap(sb, pillar, text, raised_by):
    sb.table("research_gaps").insert(
        {"pillar": pillar, "gap": text[:500], "raised_by": raised_by}).execute()
    print("  GAP  %s: %s" % (raised_by, text[:88]))


def _next_id(sb, table, prefix):
    rows = sb.table(table).select("id").like("id", prefix + "%").execute().data
    used = []
    for r in rows:
        tail = r["id"].rsplit("-", 1)[-1]
        if tail.isdigit():
            used.append(int(tail))
    return "%s%02d" % (prefix, (max(used) + 1) if used else 1)


def admit_signals(sb, pillar, proposals, evidence_rows):
    """RULE corroboration_admission: a signal needs >=2 DISTINCT, REAL evidence
    rows from this pillar. Strength is left at WEAK for rules.py to compute."""
    valid_ids = {r["id"] for r in evidence_rows}
    code = PILLAR_CODE[pillar]
    admitted = {}

    for prop in proposals:
        cited = [e for e in dict.fromkeys(prop.evidence_ids) if e in valid_ids]
        unknown = [e for e in prop.evidence_ids if e not in valid_ids]
        if unknown:
            print("  drop unknown evidence ids %s" % unknown)
        if len(cited) < MIN_EVIDENCE_PER_SIGNAL:
            _gap(sb, pillar,
                 "Proposed signal has only %d corroborating source(s) and was not "
                 "admitted: %s" % (len(cited), prop.statement),
                 "corroboration_admission")
            continue

        sig_id = _next_id(sb, "signals", "SIG-%s-" % code)
        sb.table("signals").insert({
            "id": sig_id, "pillar": pillar, "statement": prop.statement,
            "strength": "WEAK",                 # placeholder; rules.py recomputes
            "direction": prop.direction if prop.direction in
                         ("STRENGTHENING", "UNCERTAIN", "WEAKENING") else "UNCERTAIN",
            "steep": prop.steep, "env_layer": prop.env_layer,
        }).execute()
        for ev_id in cited:
            sb.table("signal_evidence").insert(
                {"signal_id": sig_id, "evidence_id": ev_id}).execute()

        admitted[prop.statement] = sig_id
        print("  RULE corroboration_admission %s <- %d evidence %s"
              % (sig_id, len(cited), cited))
    return admitted


def admit_trends(sb, pillar, proposals, signal_map):
    code = PILLAR_CODE[pillar]
    for prop in proposals:
        linked = [signal_map[s] for s in prop.signal_statements if s in signal_map]
        if len(linked) < MIN_SIGNALS_PER_TREND:
            _gap(sb, pillar, "Proposed trend had no admitted signal behind it: %s"
                 % prop.name, "trend_admission")
            continue
        tr_id = _next_id(sb, "trends", "TR-%s-" % code)
        sb.table("trends").insert({
            "id": tr_id, "pillar": pillar, "name": prop.name,
            "statement": prop.statement,
            "direction": prop.direction if prop.direction in
                         ("STRENGTHENING", "UNCERTAIN", "WEAKENING") else "UNCERTAIN",
        }).execute()
        for sig_id in linked:
            sb.table("links").insert({"from_id": sig_id, "from_type": "signal",
                                      "to_id": tr_id, "to_type": "trend",
                                      "rel": "feeds"}).execute()
        print("  RULE trend_admission %s <- %d signal(s)" % (tr_id, len(linked)))


def admit_findings(sb, pillar, proposals, signal_map):
    code = PILLAR_CODE[pillar]
    admitted = {}
    for prop in proposals:
        linked = [signal_map[s] for s in prop.signal_statements if s in signal_map]
        if len(linked) < MIN_SIGNALS_PER_FINDING:
            _gap(sb, pillar, "Proposed finding had no admitted signal behind it: %s"
                 % prop.statement, "finding_admission")
            continue
        f_id = _next_id(sb, "findings", "F-%s-" % code)
        sb.table("findings").insert(
            {"id": f_id, "statement": prop.statement, "pillar": pillar}).execute()
        for sig_id in linked:
            sb.table("links").insert({"from_id": sig_id, "from_type": "signal",
                                      "to_id": f_id, "to_type": "finding",
                                      "rel": "derivedFrom"}).execute()
        admitted[prop.statement] = (f_id, linked)
        print("  RULE finding_admission %s <- %d signal(s)" % (f_id, len(linked)))
    return admitted


def _score_risk(sb, finding_ids, signal_ids, evidence_rows):
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
    by_id = {r["id"]: r for r in evidence_rows}
    ev_ids = set()
    for sig_id in signal_ids:
        rows = (sb.table("signal_evidence").select("evidence_id")
                .eq("signal_id", sig_id).execute().data)
        ev_ids.update(r["evidence_id"] for r in rows)

    strong = [e for e in ev_ids
              if by_id.get(e, {}).get("class") in STRONG_CLASSES]
    topics = {by_id.get(e, {}).get("topic_id") for e in ev_ids} - {None}

    likelihood = 3 if len(strong) >= 2 else 2 if len(strong) == 1 else 1
    impact = 3 if len(topics) >= 3 else 2 if len(topics) == 2 else 1
    return likelihood, impact, len(strong), len(topics)


def admit_risks(sb, pillar, proposals, finding_map, evidence_rows):
    code = PILLAR_CODE[pillar]
    for prop in proposals:
        linked = [finding_map[s] for s in prop.finding_statements if s in finding_map]
        if len(linked) < MIN_FINDINGS_PER_RISK:
            _gap(sb, pillar, "Proposed risk had no admitted finding behind it: %s"
                 % prop.statement, "risk_admission")
            continue

        finding_ids = [f for f, _ in linked]
        signal_ids = [s for _, sigs in linked for s in sigs]
        likelihood, impact, n_strong, n_topics = _score_risk(
            sb, finding_ids, signal_ids, evidence_rows)

        r_id = _next_id(sb, "risks", "R-%s-" % code)
        sb.table("risks").insert({
            "id": r_id, "statement": prop.statement, "pillar": pillar,
            "likelihood": likelihood, "impact": impact,
            "response": prop.response}).execute()
        for f_id in finding_ids:
            sb.table("links").insert({"from_id": f_id, "from_type": "finding",
                                      "to_id": r_id, "to_type": "risk",
                                      "rel": "feeds"}).execute()
        print("  RULE risk_scoring %s -> L%d x I%d = %d "
              "(%d Class A/B evidence, %d topics)"
              % (r_id, likelihood, impact, likelihood * impact, n_strong, n_topics))


def admit_uncertainties(sb, pillar, proposals):
    code = PILLAR_CODE[pillar]
    for prop in proposals:
        cu_id = _next_id(sb, "uncertainties", "CU-%s-" % code)
        sb.table("uncertainties").insert({
            "id": cu_id, "pillar": pillar, "question": prop.question,
            "why_it_matters": prop.why_it_matters}).execute()
        print("  %s %s" % (cu_id, prop.question[:80]))


def main():
    ap = argparse.ArgumentParser(description="Evidence -> signals/trends/findings/risks")
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--pillar", required=True, choices=list(PILLAR_CODE))
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="synthesize", status="RUNNING")
    sb = db()

    evidence_rows = _fetch_evidence(sb, a.pillar)
    if len(evidence_rows) < MIN_EVIDENCE_PER_SIGNAL:
        print("Only %d evidence rows for %s — collect and extract more before "
              "synthesising." % (len(evidence_rows), a.pillar))
        return
    print("Synthesising %s from %d evidence rows\n" % (a.pillar, len(evidence_rows)))

    proposed = propose(a.pillar, evidence_rows)
    print("proposed: %d signals, %d trends, %d findings, %d risks, %d uncertainties\n"
          % (len(proposed.signals), len(proposed.trends), len(proposed.findings),
             len(proposed.risks), len(proposed.uncertainties)))

    signal_map = admit_signals(sb, a.pillar, proposed.signals, evidence_rows)
    admit_trends(sb, a.pillar, proposed.trends, signal_map)
    finding_map = admit_findings(sb, a.pillar, proposed.findings, signal_map)
    admit_risks(sb, a.pillar, proposed.risks, finding_map, evidence_rows)
    admit_uncertainties(sb, a.pillar, proposed.uncertainties)

    print("\nAdmitted %d/%d signals. Run rules.py next — it computes signal "
          "strength from corroboration." % (len(signal_map), len(proposed.signals)))


if __name__ == "__main__":
    main()
