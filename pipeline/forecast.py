"""STEP 5.5 — Jev forecasting: what the evidence implies about the future.

Runs AFTER synthesis and BEFORE generation, so the brief is written with an
outlook that is already admitted, scored and traceable.

THE SPLIT, AS EVERYWHERE ELSE:
  NEURAL    the model proposes what could plausibly happen, why, and — crucially
            — what observation would prove it wrong.
  SYMBOLIC  admission decides what enters the graph, and the plausibility band
            is COMPUTED from corroboration breadth, signal strength, horizon
            distance and unresolved uncertainty. The model is never asked for a
            probability and any it volunteers is discarded.

WHY BANDS AND NOT PERCENTAGES: a model asked for "68%" will produce one, and it
will be invented. Foresight practice separates plausibility from probability.
A band derived from named inputs can be audited; a number cannot.

Usage: python forecast.py --pillar CYBERSECURITY
"""
from __future__ import annotations

import argparse
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

import config
import labels
import decisions
import llm
from config import db

PILLAR_CODE = {"CYBERSECURITY": "CS", "AI": "AI",
               "ELECTRONIC_WARFARE": "EW", "PROCUREMENT": "PR"}

HORIZONS = ("H0_3", "H3_5", "H5_10", "H7_PLUS")
# Template slots the model left unfilled: [Year], <date>, TBD, XX%, {n}.
# A bracketed object id is a citation, not an unfilled slot. Without the
# exception a forecast that happened to name [EV-012] would be dropped for
# looking like a template — and a silent drop is worse than the defect.
PLACEHOLDER = re.compile(
    r"(\[(?!(?:EV|SIG|F|R|FC|FIG|TR|CU)-)[^\]]{0,24}\]"
    r"|<[^>]{0,24}>|\{[^}]{0,24}\}|\bTBD\b|\bN/?A\b"
    r"|\bXX+\b|\bYYYY\b|\binsert\b)", re.I)

MIN_SIGNALS_PER_FORECAST = 1


# --------------------------------------------------------------------------
# what the model may propose
# --------------------------------------------------------------------------
class ForecastProposal(BaseModel):
    statement: str = Field(min_length=25, max_length=400,
                           description="a specific, checkable future condition")
    horizon: str = Field(description="H0_3 | H3_5 | H5_10 | H7_PLUS")
    env_layer: str = Field(description="UAE | REGIONAL | GLOBAL")
    signal_ids: List[str] = Field(min_length=1,
        description="ids of supporting signals, e.g. SIG-CS-04")
    evidence_ids: List[str] = Field(default_factory=list)
    uncertainty_ids: List[str] = Field(default_factory=list)
    rationale: str = Field(min_length=20, max_length=700)
    falsifier: str = Field(min_length=15, max_length=400,
                           description="the observation that would refute this")
    assumptions: Optional[str] = Field(default=None, max_length=400)
    # NOTE: no plausibility, no probability, no confidence — all computed.


class ForecastSet(BaseModel):
    forecasts: List[ForecastProposal] = Field(default_factory=list)


PROMPT = """You are the forecasting stage of a strategic-foresight pipeline for
the Tawazun Council ({pillar} pillar).

Below is the complete analytical graph for this pillar: evidence, signals,
trends, uncertainties, findings and risks. Project forward from it.

WHAT A GOOD FORECAST LOOKS LIKE
- A specific, checkable future condition, not a mood. "Fibre-optic controlled
  UAS appear in more than one regional operator's inventory" is checkable;
  "the threat landscape will grow more complex" is not.
- Anchored to named signals in the data. Every forecast cites signal ids.
- Carries a FALSIFIER: the concrete observation that would show it wrong. If you
  cannot state one, the forecast is not worth making — drop it.
- Chooses a horizon honestly: H0_3, H3_5, H5_10 or H7_PLUS.

HARD RULES
- Use ONLY the graph below. No outside knowledge, no remembered examples.
- Reference signals, evidence and uncertainties by their exact ids.
- Do NOT assign probability, likelihood, confidence or a percentage anywhere.
  Those are computed downstream from corroboration and horizon; anything you
  supply is discarded.
- env_layer is UAE only if the underlying evidence is UAE-specific. Regional or
  global evidence projects to REGIONAL or GLOBAL — a regional trend is not a
  UAE forecast.{gate_note}
- Prefer few, sharp forecasts over many vague ones. Six at most.

GRAPH
{graph}
"""

GATE_NOTE = """
- The UAE validation gate for this pillar is OPEN: there is not enough
  UAE-layer evidence. Do NOT emit any forecast with env_layer=UAE."""


# --------------------------------------------------------------------------
# graph assembly
# --------------------------------------------------------------------------
def load_graph(sb, pillar: str) -> Dict[str, list]:
    g = {}
    g["evidence"] = (sb.table("evidence")
                     .select("id,claim,class,confidence,env_layer,quote_span")
                     .eq("pillar", pillar).execute().data)
    g["signals"] = (sb.table("signals")
                    .select("id,statement,strength,direction,env_layer")
                    .eq("pillar", pillar).execute().data)
    g["trends"] = (sb.table("trends").select("id,name,statement,direction")
                   .eq("pillar", pillar).execute().data)
    g["uncertainties"] = (sb.table("uncertainties").select("id,question,why_it_matters")
                          .eq("pillar", pillar).execute().data)
    g["findings"] = (sb.table("findings").select("id,statement")
                     .eq("pillar", pillar).execute().data)
    g["risks"] = (sb.table("risks").select("id,statement,likelihood,impact,score")
                  .eq("pillar", pillar).execute().data)
    return g


def render(graph: Dict[str, list]) -> str:
    out = []
    for key, rows in graph.items():
        out.append("\n%s (%d)" % (key.upper(), len(rows)))
        for r in rows:
            body = r.get("statement") or r.get("claim") or r.get("question") or r.get("name") or ""
            extra = ""
            if r.get("strength"):
                extra = " [%s / %s]" % (labels.label(r["strength"]), labels.label(r.get("direction")))
            elif r.get("class"):
                extra = " [Class %s, %s]" % (r["class"], labels.label(r.get("env_layer")))
            out.append("  %s%s %s" % (r["id"], extra, body[:200]))
    return "\n".join(out)


# --------------------------------------------------------------------------
# SYMBOLIC calibration — the band is derived, never proposed
# --------------------------------------------------------------------------
STRENGTH_POINTS = {"STRONG": 3, "STRONG_EMERGING": 2, "EMERGING": 1, "WEAK": 0}
HORIZON_PENALTY = {"H0_3": 0, "H3_5": -1, "H5_10": -2, "H7_PLUS": -3}


def calibrate(strengths: List[str], publishers: int, horizon: str,
              n_uncertainties: int) -> tuple:
    """RULE forecast_calibration.

    A projection is only as good as the evidence beneath it and degrades with
    distance. Inputs, all named:
      + strongest supporting signal      STRONG 3 · STRONG_EMERGING 2 · EMERGING 1
      + independent publishers           >=3 +2 · 2 +1
      - horizon distance                 3-5y -1 · 5-10y -2 · 7y+ -3
      - each unresolved uncertainty      -1, capped at -2
    """
    base = max([STRENGTH_POINTS.get(s, 0) for s in strengths] or [0])
    pub = 2 if publishers >= 3 else 1 if publishers == 2 else 0
    hor = HORIZON_PENALTY.get(horizon, -2)
    unc = -min(n_uncertainties, 2)
    score = base + pub + hor + unc

    if score >= 4:
        band, conf = "LIKELY", "MEDIUM_HIGH"
    elif score >= 2:
        band, conf = "POSSIBLE", "MEDIUM"
    elif score >= 1:
        band, conf = "UNCERTAIN", "LOW"
    else:
        band, conf = "SPECULATIVE", "LOW"
    if band == "LIKELY" and publishers >= 3 and base >= 3:
        conf = "HIGH"

    return band, conf, {"signal_points": base, "publisher_points": pub,
                        "horizon_penalty": hor, "uncertainty_penalty": unc,
                        "score": score, "publishers": publishers,
                        "strengths": sorted(set(strengths))}


def publishers_behind(sb, signal_ids: List[str], evidence_ids: List[str]) -> int:
    """Distinct publishers across everything supporting the forecast."""
    ev = set(evidence_ids)
    if signal_ids:
        for r in (sb.table("signal_evidence").select("evidence_id")
                  .in_("signal_id", signal_ids).execute().data):
            ev.add(r["evidence_id"])
    if not ev:
        return 0
    rows = (sb.table("evidence_sources").select("documents(registry_id)")
            .in_("evidence_id", list(ev)).execute().data)
    return len({(r.get("documents") or {}).get("registry_id") for r in rows} - {None})


# --------------------------------------------------------------------------
def _next_id(sb, pillar: str) -> str:
    prefix = "FC-%s-" % PILLAR_CODE[pillar]
    rows = sb.table("forecasts").select("id").like("id", prefix + "%").execute().data
    used = [int(r["id"].rsplit("-", 1)[-1]) for r in rows
            if r["id"].rsplit("-", 1)[-1].isdigit()]
    return "%s%02d" % (prefix, (max(used) + 1) if used else 1)


def _gap(sb, pillar, text):
    sb.table("research_gaps").insert(
        {"pillar": pillar, "gap": text[:500], "raised_by": "forecast.admission"}).execute()
    print("  GAP  %s" % text[:96])


def _signal_lookup(sb, pillar: str) -> Dict[str, str]:
    """Signals addressable by id OR statement.

    The model references signals however it saw them in the prompt — usually the
    id, sometimes the statement. Matching one form only silently rejects sound
    forecasts, which is indistinguishable from the forecaster having nothing to
    say.
    """
    lookup = {}
    for row in sb.table("signals").select("id,statement").eq("pillar", pillar).execute().data:
        lookup[row["id"]] = row["id"]
        lookup[row["statement"]] = row["id"]
        lookup[row["statement"].strip().rstrip(".")] = row["id"]
    return lookup


def admit(sb, pillar: str, proposals: List[ForecastProposal], uae_gate_open: bool) -> int:
    sig_lookup = _signal_lookup(sb, pillar)
    valid_ev = {e["id"] for e in sb.table("evidence").select("id").eq("pillar", pillar).execute().data}
    valid_unc = {u["id"] for u in sb.table("uncertainties").select("id").eq("pillar", pillar).execute().data}
    strength_of = {s["id"]: s["strength"] for s in
                   sb.table("signals").select("id,strength").eq("pillar", pillar).execute().data}
    # Gate 4 judges the inference, so it needs the signal TEXT, not the id. Keyed
    # the same way as sig_lookup so a proposal referencing a statement rather
    # than an id still resolves.
    sig_statement = {}
    for row in sb.table("signals").select("id,statement").eq("pillar", pillar).execute().data:
        sig_statement[row["id"]] = row["statement"]
        sig_statement[row["statement"]] = row["statement"]
        sig_statement[row["statement"].strip().rstrip(".")] = row["statement"]
    if not sig_lookup:
        print("  no signals in the graph — nothing to forecast from")

    # JEV GATE 4 — does the projection follow from the signals it names?
    #
    # calibrate() scores how far to trust a forecast; it never asks whether the
    # inference holds at all. That question comes first: a projection that does
    # not follow from its signals should not be scored, because a plausibility
    # band on an unsupported leap is a number lending credibility to a guess.
    support = {}
    try:
        support = decisions.gate4_forecast_support(proposals, sig_statement)
    except Exception as exc:
        # A gate that cannot run must not silently wave everything through.
        print("  ! Jev gate 4 unavailable (%s) — forecasts admitted UNGATED"
              % str(exc)[:80])
        _gap(sb, pillar, "Jev gate 4 did not run; forecasts for this pillar were "
                         "admitted without an inference check: %s" % str(exc)[:200])

    admitted = 0
    for idx, p in enumerate(proposals):
        verdict = support.get(idx)
        if verdict is not None and (not verdict.follows
                                    or verdict.probability < decisions.FORECAST_SUPPORT_THRESHOLD):
            _gap(sb, pillar,
                 "JEV GATE 4 refused — the projection does not follow from its signals "
                 "(p=%.2f): %s%s" % (verdict.probability, p.statement[:200],
                                     (" | unsupported leap: " + verdict.unsupported_leap)
                                     if verdict.unsupported_leap else ""),
                 )
            print("  JEV gate4 REFUSED p=%.2f  %s" % (verdict.probability, p.statement[:66]))
            continue

        sigs = list(dict.fromkeys(
            sig_lookup.get(s) or sig_lookup.get(s.strip().rstrip("."))
            for s in p.signal_ids
            if sig_lookup.get(s) or sig_lookup.get(s.strip().rstrip("."))))
        if len(sigs) < MIN_SIGNALS_PER_FORECAST:
            _gap(sb, pillar, "Forecast rejected — no admitted signal behind it: %s" % p.statement)
            continue
        if PLACEHOLDER.search(p.statement) or PLACEHOLDER.search(p.falsifier or ""):
            # "By [Year], the adoption of advanced threat detection will..." was
            # admitted, calibrated POSSIBLE and carried into a report. A forecast
            # with an unfilled slot has no horizon to be judged against, and a
            # bracketed placeholder in a leadership brief destroys the reader's
            # trust in every number beside it.
            _gap(sb, pillar, "Forecast rejected — unfilled placeholder in the statement: %s"
                 % p.statement)
            continue
        if p.horizon not in HORIZONS:
            _gap(sb, pillar, "Forecast rejected — invalid horizon %r: %s" % (p.horizon, p.statement))
            continue
        layer = p.env_layer if p.env_layer in ("UAE", "REGIONAL", "GLOBAL") else "GLOBAL"
        if layer == "UAE" and uae_gate_open:
            # The gate blocks UAE-specific assertion; a forecast is an assertion
            # about the UAE's future and is covered by the same prohibition.
            _gap(sb, pillar, "UAE-layer forecast withheld while the validation gate is OPEN: %s"
                 % p.statement)
            continue

        evs = [e for e in dict.fromkeys(p.evidence_ids) if e in valid_ev]
        uncs = [u for u in dict.fromkeys(p.uncertainty_ids) if u in valid_unc]
        pubs = publishers_behind(sb, sigs, evs)
        band, conf, basis = calibrate([strength_of.get(s, "WEAK") for s in sigs],
                                      pubs, p.horizon, len(uncs))

        fid = _next_id(sb, pillar)
        sb.table("forecasts").insert({
            "id": fid, "pillar": pillar, "statement": p.statement,
            "horizon": p.horizon, "env_layer": layer,
            "plausibility": band, "confidence": conf,
            "rationale": p.rationale, "falsifier": p.falsifier,
            "assumptions": p.assumptions, "basis": basis}).execute()
        for s in sigs:
            sb.table("forecast_signals").insert({"forecast_id": fid, "signal_id": s}).execute()
        for e in evs:
            sb.table("forecast_evidence").insert({"forecast_id": fid, "evidence_id": e}).execute()
        for u in uncs:
            sb.table("forecast_uncertainties").insert({"forecast_id": fid, "uncertainty_id": u}).execute()

        print("  RULE forecast_calibration %s -> %-11s / %-11s  "
              "(%s, %d publisher(s), %s, %d uncertainty) score=%d"
              % (fid, band, conf, "+".join(basis["strengths"]) or "none",
                 pubs, p.horizon, len(uncs), basis["score"]))
        print("       %s" % p.statement[:104])
        admitted += 1
    return admitted


def main():
    ap = argparse.ArgumentParser(description="Jev forecasting — evidence to outlook")
    ap.add_argument("--pillar", required=True, choices=list(PILLAR_CODE))
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--replace", action="store_true",
                    help="delete existing forecasts for this pillar first")
    a = ap.parse_args()
    config.update_run(a.run_id, stage="forecast", status="RUNNING")
    sb = db()

    graph = load_graph(sb, a.pillar)
    if not graph["signals"]:
        print("No signals for %s — run synthesize.py before forecasting." % a.pillar)
        return
    if a.replace:
        n = len(sb.table("forecasts").select("id").eq("pillar", a.pillar).execute().data)
        sb.table("forecasts").delete().eq("pillar", a.pillar).execute()
        print("removed %d existing forecast(s)\n" % n)

    gate = (sb.table("validation_gates").select("status")
            .eq("id", "VG-%s-01" % a.pillar[:2]).execute().data)
    uae_gate_open = bool(gate) and gate[0]["status"] == "OPEN"

    print("Forecasting %s from %d signals / %d evidence / %d uncertainties"
          % (a.pillar, len(graph["signals"]), len(graph["evidence"]),
             len(graph["uncertainties"])))
    print("UAE gate: %s\n" % ("OPEN — UAE-layer forecasts blocked" if uae_gate_open else "PASSED"))

    result = llm.structured(
        PROMPT.format(pillar=labels.PILLAR[a.pillar], graph=render(graph),
                      gate_note=GATE_NOTE if uae_gate_open else ""),
        ForecastSet, effort="high", max_output_tokens=16000)
    print("proposed %d forecast(s)\n" % len(result.forecasts))

    n = admit(sb, a.pillar, result.forecasts, uae_gate_open)
    print("\nAdmitted %d/%d forecast(s)." % (n, len(result.forecasts)))
    config.update_run(a.run_id, counts={"forecast": n})


if __name__ == "__main__":
    main()
