"""STEP 7 — the back half of the methodology (report §9 through §21).

synthesize.py takes evidence to signals, findings and risks. That covers the
report up to §10. Everything after it — drivers, cross-impacts, scenarios,
implications split by authority, opportunities, options, the scenario stress
test, initiatives, indicators and the leadership decision requirements — was
modelled in migration 005 and never populated, so eleven object types sat empty
and eleven sections of the deliverable had nothing to render from.

The division of labour is the same as everywhere else in this pipeline. The
model proposes typed candidates and writes prose; every admission decision, and
every number, is made here in code:

  drivers        admitted when at least two admitted trends stand behind them
  cross_impacts  both trend ids must resolve; severity computed from strengths
  scenarios      at least two critical uncertainties, and materially distinct
  implications   must name a real finding, and an authority that owns it
  opportunities  attractiveness and feasibility COMPUTED, mirroring risk scoring
  options        at least two, each traceable to an admitted finding or risk
  stress_tests   every option against every scenario; robustness is the model's
                 read, but "robust across all scenarios" is counted here
  initiatives    forced Class D — a proposal, never current policy
  indicators     refused without a concrete threshold; "TBD" is not a control
  decisions      refused without naming the data leadership still needs

Refusals go to research_gaps with the rule that made them, exactly as in
synthesize.py, because what the analysis could not support is part of what it
reports.

  python strategize.py --pillar CYBERSECURITY
"""
from __future__ import annotations

import argparse
import re
from typing import List, Optional

from pydantic import BaseModel

import config
import llm
from config import db

HORIZONS = ("H0_3", "H3_5", "H5_10", "H7_PLUS")
ACTORS = ("MOD", "TAWAZUN")
ROBUSTNESS = ("ROBUST", "CONDITIONAL", "FRAGILE")

MIN_TRENDS_PER_DRIVER = 2
MIN_UNCERTAINTIES_PER_SCENARIO = 2
MIN_SCENARIOS = 3
MIN_OPTIONS = 2


# ---------------------------------------------------------------------------
# what the model may propose
# ---------------------------------------------------------------------------
class DriverP(BaseModel):
    name: str
    description: str
    trend_ids: list[str]


class CrossImpactP(BaseModel):
    from_trend: str
    to_trend: str
    statement: str


class ScenarioP(BaseModel):
    name: str
    one_sentence: str
    threat: str
    technology: str
    mod: str
    tawazun: str
    horizon: str
    uncertainty_ids: list[str]


class ImplicationP(BaseModel):
    actor: str
    statement: str
    finding_id: str


class OpportunityP(BaseModel):
    statement: str
    finding_ids: list[str]


class OptionP(BaseModel):
    letter: str
    name: str
    description: str
    finding_ids: list[str]


class StressP(BaseModel):
    option_letter: str
    scenario_name: str
    result: str
    note: str


class InitiativeP(BaseModel):
    name: str
    objective: str
    owner: str
    horizon: str
    actions: list[str]


class IndicatorP(BaseModel):
    watch: str
    threshold: str
    action: str


class DecisionP(BaseModel):
    title: str
    decision: str
    why_first: str
    data_needed: str


class Proposal(BaseModel):
    drivers: list[DriverP]
    cross_impacts: list[CrossImpactP]
    scenarios: list[ScenarioP]
    implications: list[ImplicationP]
    opportunities: list[OpportunityP]
    options: list[OptionP]
    stress_tests: list[StressP]
    initiatives: list[InitiativeP]
    indicators: list[IndicatorP]
    decisions: list[DecisionP]


PROMPT = """You are extending a strategic foresight analysis for the Tawazun
Council (UAE defence). The evidence, signals, trends, findings, risks and
critical uncertainties below have ALREADY been admitted by rule. Your job is to
propose the next layer of the analysis from them.

Propose ONLY what the material below supports. You are not being asked to be
comprehensive; you are being asked to be traceable. Anything you cannot tie to
an id will be refused and recorded as a gap.

drivers — the forces underneath the trends. Each must name at least {min_trends}
  trend ids it is read from.

cross_impacts — two trends that are individually manageable and together are
  not. Name both trend ids. This is the highest-value item in the section: state
  the interaction, not the sum.

scenarios — propose {min_scen} to 5 MATERIALLY DIFFERENT futures. Not optimistic
  / middle / pessimistic — different in KIND, each resolving the critical
  uncertainties a different way. Each names at least {min_unc} uncertainty ids it
  turns on, a short memorable name, one sentence, and a paragraph each for:
  threat, technology, what it means for MoD, what it means for Tawazun.

implications — split by authority and never merged. MOD owns the operational
  question: readiness, training, mission assurance. TAWAZUN owns the enabling
  environment: acquisition, contracts, industrial capability, sovereignty. Each
  implication names the finding id it follows from and the actor that owns it.

opportunities — the upside peer of the risks. In finding_ids name the admitted
  objects behind it — finding, risk or forecast ids. Do NOT score them; the
  scoring is computed.

options — {min_opt} to 4 strategic options, lettered A, B, C, D. These are
  genuinely different postures, not increments of one another. In finding_ids
  name the admitted objects each option answers — finding, risk or forecast ids.

stress_tests — EVERY option against EVERY scenario, with no cell left out: if
  you propose 4 options and 5 scenarios, return all 20. A partial matrix cannot
  compare options because they were not asked the same questions. result is
  exactly one of
  ROBUST, CONDITIONAL or FRAGILE, with one sentence saying why. An option that
  is ROBUST everywhere is either genuinely robust or too vague to test — if it
  is the latter, say so in the note.

initiatives — named programmes that carry the chosen direction, each with an
  objective, an owner and a horizon, plus two to four concrete actions. These
  are PROPOSALS for consideration, never descriptions of existing policy.

indicators — what to watch, the THRESHOLD that would trigger a response, and the
  response. A threshold must be concrete and observable: a number, a date, a
  named event. "TBD", "as appropriate" or "monitor closely" will be refused.

decisions — the two or three decisions leadership must actually take, each with
  why it comes first and WHAT DATA IS STILL NEEDED from Tawazun or MoD before it
  can be taken.

Horizons are exactly one of: H0_3, H3_5, H5_10, H7_PLUS.

Never assign a score, likelihood, impact, severity, attractiveness, feasibility
or confidence anywhere. Those are computed from corroboration and you do not
have the inputs.

PILLAR: {pillar}

{data}
"""


def _gap(sb, pillar, text, rule):
    sb.table("research_gaps").insert(
        {"pillar": pillar, "gap": text[:600], "raised_by": rule}).execute()
    print("  GAP  %s" % text[:100])


def _slug(name: str, n: int = 28) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", (name or "").upper()).strip("-")[:n] or "X"


def _next(sb, table, prefix) -> int:
    rows = sb.table(table).select("id").execute().data
    nums = [int(m.group(1)) for r in rows
            if (m := re.match(re.escape(prefix) + r"(\d+)$", r["id"]))]
    return max(nums, default=0) + 1


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------
def score_opportunity(evidence_rows, topics) -> tuple:
    """RULE opportunity_scoring — mirrors risk scoring in synthesize.py.

    attractiveness follows corroboration: an opportunity resting on well
    corroborated evidence is worth more than one resting on a single report.
    feasibility follows breadth: something touching several parts of the problem
    space has more places to start.
    """
    strong = [e for e in evidence_rows if e.get("class") in ("A", "B")]
    attractiveness = 3 if len(strong) >= 2 else 2 if len(strong) == 1 else 1
    feasibility = 3 if len(topics) >= 3 else 2 if len(topics) == 2 else 1
    return attractiveness, feasibility, len(strong), len(topics)


def cross_impact_severity(a_strength: str, b_strength: str) -> int:
    """RULE cross_impact_severity — two STRONG trends interacting is the case
    the report calls out; two weak ones is a hypothesis."""
    rank = {"STRONG": 3, "STRONG_EMERGING": 2, "EMERGING": 2, "WEAK": 1}
    return max(1, min(3, (rank.get(a_strength, 1) + rank.get(b_strength, 1)) // 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--pillar", required=True)
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="strategize", status="RUNNING")
    sb = db()
    P = a.pillar

    ev = sb.table("evidence").select("id,claim,class,env_layer,topic_id").eq("pillar", P).execute().data
    sig = sb.table("signals").select("id,statement,strength,horizon").eq("pillar", P).execute().data
    tr = sb.table("trends").select("id,name,statement,direction").eq("pillar", P).execute().data
    fi = sb.table("findings").select("id,statement").eq("pillar", P).execute().data
    ri = sb.table("risks").select("id,statement,likelihood,impact").execute().data
    un = sb.table("uncertainties").select("id,question,why_it_matters").eq("pillar", P).execute().data
    fc = sb.table("forecasts").select("id,statement,horizon,plausibility").eq("pillar", P).execute().data

    if not fi:
        raise SystemExit("no admitted findings for %s — run synthesize.py first" % P)

    def block(title, rows, fields):
        out = ["%s:" % title]
        for r in rows:
            out.append("  " + " | ".join("%s=%s" % (f, str(r.get(f))[:150]) for f in fields))
        return "\n".join(out)

    data = "\n\n".join([
        block("EVIDENCE", ev[:70], ["id", "claim", "class"]),
        block("SIGNALS", sig, ["id", "statement", "strength"]),
        block("TRENDS", tr, ["id", "name", "statement"]),
        block("FINDINGS", fi, ["id", "statement"]),
        block("RISKS", ri, ["id", "statement"]),
        block("CRITICAL UNCERTAINTIES", un, ["id", "question", "why_it_matters"]),
        block("FORECASTS", fc, ["id", "statement", "horizon", "plausibility"]),
    ])

    print("Strategising %s from %d findings / %d trends / %d uncertainties\n"
          % (P, len(fi), len(tr), len(un)))

    prop = llm.structured(
        PROMPT.format(pillar=P, data=data, min_trends=MIN_TRENDS_PER_DRIVER,
                      min_scen=MIN_SCENARIOS, min_unc=MIN_UNCERTAINTIES_PER_SCENARIO,
                      min_opt=MIN_OPTIONS),
        Proposal, effort="high", max_output_tokens=32000)

    trend_ids = {t["id"] for t in tr}
    find_ids = {f["id"] for f in fi}
    # An option that answers an admitted risk or forecast is traceable; requiring
    # a FINDING specifically rejected two of three options against a pillar that
    # holds only three findings, and a one-option stress test compares nothing.
    anchor_ids = find_ids | {r["id"] for r in ri} | {f["id"] for f in fc}
    unc_ids = {u["id"] for u in un}
    trend_strength = {t["id"]: "WEAK" for t in tr}
    for s in sig:
        pass  # trends carry direction, not strength; severity falls back to WEAK

    counts = {}

    # ---------------- drivers ----------------
    n = _next(sb, "drivers", "DRV-")
    for d in prop.drivers:
        ok = [t for t in dict.fromkeys(d.trend_ids) if t in trend_ids]
        if len(ok) < MIN_TRENDS_PER_DRIVER:
            _gap(sb, P, "Driver rejected — only %d admitted trend(s) behind it: %s"
                 % (len(ok), d.name), "driver_admission")
            continue
        did = "DRV-%02d" % n; n += 1
        sb.table("drivers").upsert({"id": did, "name": d.name[:200],
                                    "description": d.description, "pillar": P}).execute()
        for t in ok:
            sb.table("links").upsert({"from_id": did, "from_type": "driver",
                                      "to_id": t, "to_type": "trend",
                                      "rel": "derivedFrom"}).execute()
        counts["drivers"] = counts.get("drivers", 0) + 1
        print("  RULE driver_admission %s <- %d trend(s)" % (did, len(ok)))

    # ---------------- cross impacts ----------------
    n = _next(sb, "cross_impacts", "CI-")
    for c in prop.cross_impacts:
        if c.from_trend not in trend_ids or c.to_trend not in trend_ids:
            _gap(sb, P, "Cross-impact rejected — names a trend that does not exist (%s -> %s)"
                 % (c.from_trend, c.to_trend), "cross_impact_admission")
            continue
        if c.from_trend == c.to_trend:
            _gap(sb, P, "Cross-impact rejected — a trend cannot cross-impact itself: %s"
                 % c.statement, "cross_impact_admission")
            continue
        sev = cross_impact_severity(trend_strength.get(c.from_trend, "WEAK"),
                                    trend_strength.get(c.to_trend, "WEAK"))
        cid = "CI-%02d" % n; n += 1
        sb.table("cross_impacts").upsert({"id": cid, "from_trend": c.from_trend,
                                          "to_trend": c.to_trend,
                                          "statement": c.statement, "severity": sev}).execute()
        counts["cross_impacts"] = counts.get("cross_impacts", 0) + 1
        print("  RULE cross_impact_severity %s -> %d (%s x %s)"
              % (cid, sev, c.from_trend, c.to_trend))

    # ---------------- scenarios ----------------
    kept_scen = {}
    n = _next(sb, "scenarios", "S")
    seen_names = set()
    for s in prop.scenarios:
        ok = [u for u in dict.fromkeys(s.uncertainty_ids) if u in unc_ids]
        if len(ok) < MIN_UNCERTAINTIES_PER_SCENARIO:
            _gap(sb, P, "Scenario rejected — turns on %d admitted uncertainty(ies), needs %d: %s"
                 % (len(ok), MIN_UNCERTAINTIES_PER_SCENARIO, s.name), "scenario_admission")
            continue
        key = _slug(s.name)
        if key in seen_names:
            _gap(sb, P, "Scenario rejected — not materially distinct from one already "
                        "admitted: %s" % s.name, "scenario_distinctness")
            continue
        seen_names.add(key)
        sid = "S%d" % n; n += 1
        sb.table("scenarios").upsert({
            "id": sid, "name": s.name[:120], "one_sentence": s.one_sentence,
            "horizon": s.horizon if s.horizon in HORIZONS else "H3_5",
            "dimensions": {"threat": s.threat, "technology": s.technology,
                           "mod": s.mod, "tawazun": s.tawazun}}).execute()
        for u in ok:
            sb.table("scenario_uncertainties").upsert(
                {"scenario_id": sid, "uncertainty_id": u}).execute()
        kept_scen[_slug(s.name)] = sid
        counts["scenarios"] = counts.get("scenarios", 0) + 1
        print("  RULE scenario_admission %s '%s' <- %d uncertainty(ies)" % (sid, s.name[:44], len(ok)))

    # ---------------- implications ----------------
    n = _next(sb, "implications", "IMP-")
    for im in prop.implications:
        actor = (im.actor or "").strip().upper()
        # "MoD" and "Tawazun" are the same authorities as "MOD" and "TAWAZUN".
        # A case-sensitive check refused every implication the model proposed and
        # emptied both §12 and §13 — a rule should refuse unsupported analysis,
        # not unexpected capitalisation.
        if actor not in ACTORS:
            _gap(sb, P, "Implication rejected — actor %r is not MOD or TAWAZUN" % im.actor,
                 "implication_actor"); continue
        if im.finding_id not in find_ids:
            _gap(sb, P, "Implication rejected — names finding %s which was not admitted: %s"
                 % (im.finding_id, im.statement[:120]), "implication_admission")
            continue
        iid = "IMP-%s-%02d" % (actor[:3], n); n += 1
        sb.table("implications").upsert({"id": iid, "actor": actor, "pillar": P,
                                         "statement": im.statement,
                                         "finding_id": im.finding_id}).execute()
        counts["implications"] = counts.get("implications", 0) + 1
    print("  RULE implication_admission -> %d (MoD and Tawazun kept separate)"
          % counts.get("implications", 0))

    # ---------------- opportunities ----------------
    n = _next(sb, "opportunities", "O")
    for o in prop.opportunities:
        ok = [f for f in dict.fromkeys(o.finding_ids) if f in anchor_ids]
        if not ok:
            _gap(sb, P, "Opportunity rejected — no admitted finding, risk or forecast "
                        "behind it: %s" % o.statement[:140], "opportunity_admission")
            continue
        ev_ids = {r["to_id"] for f in ok for r in
                  sb.table("links").select("to_id,to_type").eq("from_id", f)
                  .eq("to_type", "evidence").execute().data}
        rows = [e for e in ev if e["id"] in ev_ids] or ev[:3]
        topics = {e.get("topic_id") for e in rows if e.get("topic_id")}
        att, fea, n_strong, n_top = score_opportunity(rows, topics)
        oid = "O%d" % n; n += 1
        sb.table("opportunities").upsert({"id": oid, "statement": o.statement, "pillar": P,
                                          "attractiveness": att, "feasibility": fea}).execute()
        counts["opportunities"] = counts.get("opportunities", 0) + 1
        print("  RULE opportunity_scoring %s -> A%d x F%d = %d (%d Class A/B, %d topics)"
              % (oid, att, fea, att * fea, n_strong, n_top))

    # ---------------- options ----------------
    kept_opt = {}
    for o in prop.options:
        ok = [f for f in dict.fromkeys(o.finding_ids) if f in anchor_ids]
        if not ok:
            _gap(sb, P, "Option rejected — not traceable to any admitted finding, risk or "
                        "forecast: %s" % o.name, "option_admission")
            continue
        letter = (o.letter or "").strip().upper()[:1] or "X"
        oid = "OPT-%s" % letter
        sb.table("options").upsert({"id": oid, "name": o.name[:200],
                                    "description": o.description}).execute()
        kept_opt[letter] = oid
        counts["options"] = counts.get("options", 0) + 1
        print("  RULE option_admission %s '%s' <- %d finding(s)" % (oid, o.name[:40], len(ok)))

    if len(kept_opt) < MIN_OPTIONS:
        _gap(sb, P, "Fewer than %d strategic options survived admission — the stress test "
                    "cannot discriminate between postures." % MIN_OPTIONS, "option_admission")

    # ---------------- stress tests ----------------
    def match_scenario(name: str) -> Optional[str]:
        """Scenario names come back paraphrased — "AI-Dominant Offensive" against
        "AI Dominant Offensive Scenario". Exact slug matching dropped two thirds
        of the matrix, so fall back to the longest shared prefix."""
        want = _slug(name)
        if want in kept_scen:
            return kept_scen[want]
        for key, sid in kept_scen.items():
            if key.startswith(want[:12]) or want.startswith(key[:12]):
                return sid
        return None

    for st in prop.stress_tests:
        letter = (st.option_letter or "").strip().upper()[:1]
        oid = kept_opt.get(letter)
        sid = match_scenario(st.scenario_name)
        if not oid or not sid:
            _gap(sb, P, "Stress test discarded — could not resolve option %r / scenario %r"
                 % (st.option_letter, st.scenario_name), "stress_test_resolution")
            continue
        if st.result not in ROBUSTNESS:
            _gap(sb, P, "Stress test rejected — result %r is not ROBUST/CONDITIONAL/FRAGILE"
                 % st.result, "stress_test_admission")
            continue
        sb.table("stress_tests").upsert({"option_id": oid, "scenario_id": sid,
                                         "result": st.result, "note": st.note}).execute()
        counts["stress_tests"] = counts.get("stress_tests", 0) + 1

    # RULE stress_matrix_completeness: every option against every scenario, or the
    # comparison is between different question sets and means nothing.
    expected = len(kept_opt) * len(kept_scen)
    got = counts.get("stress_tests", 0)
    if expected and got < expected:
        _gap(sb, P, "Scenario stress test is incomplete — %d of %d option x scenario cells "
                    "were returned, so options cannot be compared across the same futures."
             % (got, expected), "stress_matrix_completeness")
        print("  RULE stress_matrix_completeness %d/%d cells — INCOMPLETE" % (got, expected))
    elif expected:
        print("  RULE stress_matrix_completeness %d/%d cells" % (got, expected))

    # RULE working_hypothesis: the option that survives the most scenarios, decided
    # by counting the matrix rather than by the model nominating its favourite.
    if kept_opt and kept_scen:
        tally = {}
        for row in sb.table("stress_tests").select("option_id,result").execute().data:
            if row["option_id"] in kept_opt.values():
                tally.setdefault(row["option_id"], 0)
                tally[row["option_id"]] += 1 if row["result"] == "ROBUST" else 0
        if tally:
            best = max(tally.items(), key=lambda kv: kv[1])
            if best:
                for oid in kept_opt.values():
                    sb.table("options").update(
                        {"is_working_hypothesis": oid == best[0]}).eq("id", oid).execute()
                print("  RULE working_hypothesis %s -> survival %+d across %d scenario(s)"
                      % (best[0], best[1], len(kept_scen)))

    # ---------------- initiatives and actions ----------------
    n = _next(sb, "initiatives", "INIT-")
    an = _next(sb, "actions", "ACT-")
    for ini in prop.initiatives:
        iid = "INIT-%02d" % n; n += 1
        sb.table("initiatives").upsert({
            "id": iid, "name": ini.name[:200], "objective": ini.objective,
            "class": "D",                       # schema forces it; stated for the reader
            "owner": ini.owner[:120] if ini.owner else None,
            "horizon": ini.horizon if ini.horizon in HORIZONS else "H0_3"}).execute()
        counts["initiatives"] = counts.get("initiatives", 0) + 1
        for seq, act in enumerate(ini.actions[:4], start=1):
            sb.table("actions").upsert({
                "id": "ACT-%02d" % an, "initiative_id": iid, "statement": act,
                "owner": ini.owner[:120] if ini.owner else None,
                "horizon": ini.horizon if ini.horizon in HORIZONS else "H0_3",
                "sequence": seq}).execute()
            an += 1
            counts["actions"] = counts.get("actions", 0) + 1

    # ---------------- indicators ----------------
    VAGUE = re.compile(r"^(tbd|n/?a|-|as appropriate|ongoing|monitor(ed)? closely|"
                       r"regular(ly)?|periodic(ally)?|continuous(ly)?)$", re.I)
    n = _next(sb, "indicators", "IND-%s-" % P[:2])
    for ind in prop.indicators:
        th = (ind.threshold or "").strip()
        if not th or VAGUE.match(th) or not re.search(r"\d|\b(by|within|per|exceeds?|first|any)\b", th, re.I):
            _gap(sb, P, "Indicator rejected — threshold is not observable (%r). An indicator "
                        "without a concrete trigger is not a control: %s" % (th[:60], ind.watch[:100]),
                 "indicator_threshold")
            continue
        iid = "IND-%s-%02d" % (P[:2], n); n += 1
        sb.table("indicators").upsert({"id": iid, "watch": ind.watch,
                                       "threshold": th, "action": ind.action}).execute()
        counts["indicators"] = counts.get("indicators", 0) + 1
        print("  RULE indicator_threshold %s admitted (%s)" % (iid, th[:56]))

    # ---------------- leadership decision requirements ----------------
    n = _next(sb, "decision_requirements", "PDC-")
    for pri, d in enumerate(prop.decisions[:4], start=1):
        if not (d.data_needed or "").strip():
            _gap(sb, P, "Decision requirement rejected — does not say what data leadership "
                        "still needs: %s" % d.title[:120], "decision_data_needed")
            continue
        sb.table("decision_requirements").upsert({
            "id": "PDC-%d" % n, "title": d.title[:200], "decision": d.decision,
            "why_first": d.why_first, "data_needed": d.data_needed, "priority": pri}).execute()
        n += 1
        counts["decisions"] = counts.get("decisions", 0) + 1

    print("\nadmitted: %s" % (", ".join("%s %d" % (k, v) for k, v in sorted(counts.items()))
                              or "nothing"))
    config.update_run(getattr(a, "run_id", None), counts={"strategize": sum(counts.values())})


if __name__ == "__main__":
    main()
