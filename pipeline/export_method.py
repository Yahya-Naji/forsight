"""The companion document: how the report was built.

The report says what the evidence supports. This says how it was decided — the
object model with its authority split, the stage-by-stage attrition with the
rule that made each refusal, the forecast calibration arithmetic, the per-section
generation ledger and the audit against the human benchmark.

It is the Engine screen rendered as a document, from the same tables and the same
numbers, so the two can never disagree. A reader who does not trust the report
reads this instead; a reader who does trust it never needs to.

  python export_method.py --report <uuid> --out ../out/method.html
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import os
from datetime import date

from config import db

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mirrors web/lib/engine.ts. The stage list is the contract with update_run().
LAYERS = {
    "SOURCE":   ("Collected",      "#0F5C6E", "#E2F1F5", "#BCDDE5", "#9ECFDA"),
    "NEURAL":   ("Model proposes", "#3D5BF5", "#EEF1FC", "#C7D2F7", "#A9BCF7"),
    "SYMBOLIC": ("Rule decides",   "#3A4468", "#EDEFF6", "#D6DBEA", "#AEB6CE"),
}

STAGES = [
    ("collect", "Collect", "SOURCE", "collectors/registry.py · map_domain",
     "Documents from lanes A, B and C, each bound to a registered publisher and tier.",
     "Pages blocked by robots.txt, paywall stubs and anything under the length floor. A "
     "publisher missing from the registry falls back to the aggregator id and is scored "
     "Tier 4 — which is why the registry is the tier-integrity surface."),
    ("extract", "Extract", "NEURAL", "extract.py",
     "The model emits claims, each bound to a verbatim quote span.",
     "Anything failing the typed schema. A claim with no quote span cannot be checked "
     "later, so it never enters."),
    ("rules", "Rules & gates", "SYMBOLIC", "rules.py",
     "Evidence class, confidence, signal strength and the UAE inference guard.",
     "Nothing outright — it downgrades. Corroboration is counted in DISTINCT PUBLISHERS, "
     "so four claims from one article are one source, and a UAE-specific claim without two "
     "independent UAE-layer rows opens a gate that blocks assertion."),
    ("synthesize", "Synthesize", "SYMBOLIC", "synthesize.py · rules.py",
     "Signals, trends, findings and risks admitted only against the rules.",
     "Proposals with too little corroboration behind them, and findings that assert "
     "importance instead of stating what is true."),
    ("strategize", "Strategise", "SYMBOLIC", "strategize.py",
     "Drivers, cross-impacts, scenarios, implications split by authority, opportunities, "
     "options, the scenario stress test, initiatives, indicators and decision requirements.",
     "Scenarios turning on fewer than two critical uncertainties, options not traceable to "
     "an admitted object, indicators with no observable threshold, and decision "
     "requirements that do not say what data leadership still needs."),
    ("forecast", "Forecast", "SYMBOLIC", "forecast.py · calibrate()",
     "Plausibility computed from corroboration and horizon, never asserted.",
     "Forecasts with no admitted signal behind them, UAE-layer forecasts while the gate is "
     "open, and statements left with an unfilled placeholder."),
    ("generate", "Generate", "NEURAL", "generate.py",
     "Section-scoped inputs, one citation per claim, redrafted until it passes.",
     "Its own drafts. A section still failing after its retries is withheld and the hole "
     "left visible."),
    ("verify", "Verify", "SYMBOLIC", "verify.py",
     "Citations resolve · gates honoured · quotes entail the sentences citing them.",
     "Publication. The audit runs after assembly and its findings are the scorecard, "
     "whether or not they are flattering."),
]

REFUSAL_STAGE = {
    "collect.lane_a": "collect", "collect.lane_b": "collect", "collect.lane_c": "collect",
    "extract.schema": "extract", "extract.quote": "extract",
    "corroboration_admission": "synthesize", "trend_admission": "synthesize",
    "finding_admission": "synthesize", "finding_substance": "synthesize",
    "risk_admission": "synthesize",
    "driver_admission": "strategize", "cross_impact_admission": "strategize",
    "scenario_admission": "strategize", "scenario_distinctness": "strategize",
    "implication_actor": "strategize", "implication_admission": "strategize",
    "opportunity_admission": "strategize", "option_admission": "strategize",
    "stress_test_admission": "strategize", "stress_test_resolution": "strategize",
    "stress_matrix_completeness": "strategize", "decision_data_needed": "strategize",
    "indicator_threshold": "strategize",
    "forecast.admission": "forecast", "forecast.placeholder": "forecast",
    "generate.indicator_threshold": "generate",
}

ONTOLOGY = [
    ("Document", "documents", "A retrieved page or PDF, bound to the publisher that issued it.",
     [], ["registry_id", "tier", "published_on"]),
    ("Figure", "figures", "A published chart, diagram or screenshot that carries information.",
     ["kind", "describes"], ["informative", "refused_reason", "reachable"]),
    ("Evidence", "evidence", "One sourced claim with the verbatim span it rests on.",
     ["claim", "quote_span"], ["class", "confidence", "env_layer"]),
    ("Signal", "signals", "A change several independent sources point at.",
     ["statement"], ["strength", "direction"]),
    ("Trend", "trends", "A direction of travel across signals.", ["statement"], ["direction"]),
    ("Finding", "findings", "What the signals mean. Must say X rather than Y.",
     ["statement"], ["substance_test"]),
    ("Risk", "risks", "A consequence with a scored likelihood and impact.",
     ["statement"], ["likelihood", "impact", "score"]),
    ("Opportunity", "opportunities", "The upside peer of a risk, scored the same way.",
     ["statement"], ["attractiveness", "feasibility", "score"]),
    ("Uncertainty", "uncertainties", "A question whose answer would move the assessment.",
     ["question", "why_it_matters"], []),
    ("Scenario", "scenarios", "A materially different future used to test decisions.",
     ["name", "one_sentence", "dimensions"], ["admitted_from"]),
    ("Option", "options", "A strategic posture, tested against every scenario.",
     ["name", "description"], ["is_working_hypothesis"]),
    ("Forecast", "forecasts", "An outlook carrying its own falsifier.",
     ["statement", "falsifier"], ["plausibility", "confidence", "basis"]),
    ("Validation gate", "validation_gates", "A prohibition. While open, the claims it names cannot be asserted.",
     [], ["status", "blocks"]),
]

CSS = """
:root{--paper:#F4F5FA;--card:#fff;--line:#E7EAF4;--soft:#EFF1F8;--ink:#12162E;--ink2:#2A2F45;
--muted:#5A6076;--faint:#8A92AE;--ghost:#9AA1B8;--accent:#3D5BF5;--wash:#EEF1FC;--navy:#0A0F2E;
--amber:#8A6D00;--amberbg:#FFF8EA;--amberline:#F0DFB4;--green:#17693A;--greenbg:#EFF9F2;
--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:15px/1.6 'Instrument Sans',system-ui,sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{max-width:1080px;margin:0 auto;padding:34px 30px 60px}
h1,h2,h3{font-family:'Space Grotesk','Instrument Sans',sans-serif;letter-spacing:-.01em}
.hero{background:var(--navy);color:#fff;border-radius:18px;padding:34px 38px;
  background-image:radial-gradient(900px 420px at 50% 130%,rgba(84,116,255,.5),rgba(84,116,255,0) 65%)}
.hero h1{font-size:34px;margin:10px 0 0;font-weight:700}
.kicker{font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:600;color:var(--faint)}
.lede{font-size:14px;color:#B8C4EE;margin-top:10px;max-width:70ch;line-height:1.55}
section{margin-top:34px}
h2{font-size:21px;margin:0 0 5px}
.sub{font-size:13.5px;color:var(--muted);max-width:72ch;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;font-family:var(--mono);font-size:9.5px;letter-spacing:1px;text-transform:uppercase;
  color:var(--faint);font-weight:600;padding:0 10px 7px 0}
td{padding:8px 10px 8px 0;border-top:1px solid var(--soft);vertical-align:top}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
.chip{display:inline-block;font-family:var(--mono);font-size:10.5px;border-radius:5px;padding:1.5px 6px;
  border:1px solid var(--line);background:var(--soft);color:var(--ink2);white-space:nowrap}
.chip.n{color:var(--accent);background:var(--wash);border-color:#C7D2F7}
.chip.s{color:#3A4468;background:#EDEFF6;border-color:#D6DBEA}
.chip.a{color:var(--amber);background:var(--amberbg);border-color:var(--amberline)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(206px,1fr));gap:9px}
.obj{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:11px 12px}
.obj .t{display:flex;justify-content:space-between;align-items:baseline}
.obj .n{font-family:'Space Grotesk';font-weight:600;font-size:13.5px}
.obj .c{font-family:var(--mono);font-size:11px;color:var(--faint)}
.obj .g{font-size:11.5px;color:var(--muted);line-height:1.45;margin:5px 0 7px}
.stage{display:grid;grid-template-columns:92px 1fr;border-top:1px solid var(--soft)}
.stage:first-child{border-top:none}
.rail{position:relative;background:#FBFCFE;border-right:1px solid var(--soft)}
.rail svg{position:absolute;inset:0;width:100%;height:100%}
.rail .ct{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);font-family:var(--mono);
  font-size:11px;font-weight:700;background:rgba(255,255,255,.94);border-radius:4px;padding:1px 5px}
.sb{padding:13px 16px 15px}
.sh{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.sh .i{font-family:var(--mono);font-size:10.5px;color:var(--ghost)}
.sh .nm{font-family:'Space Grotesk';font-weight:600;font-size:15px}
.sh .lb{font-size:10px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;border-radius:5px;padding:2px 7px}
.sh .src{margin-left:auto;font-family:var(--mono);font-size:10.5px;color:var(--ghost)}
.sd{font-size:13px;color:var(--ink2);margin-top:6px;max-width:78ch}
.sr{font-size:12.5px;color:var(--muted);margin-top:6px;max-width:78ch}
.ref{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.ref .h{font-size:10.5px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:var(--amber)}
.calc{border:1px solid var(--line);border-radius:10px;padding:11px 13px;background:#FCFCFE;margin-top:9px}
.calc .row{display:flex;gap:8px;font-size:12px;align-items:baseline}
.calc .v{font-family:var(--mono);font-weight:700;min-width:26px;text-align:right}
.calc .l{min-width:140px;color:var(--ink2)}
.calc .nt{color:var(--ghost);font-size:11.5px}
.pair{border:1px solid var(--line);border-radius:10px;padding:10px 13px;background:#FCFCFE;min-width:168px}
.pair .k{font-size:10.5px;letter-spacing:.6px;text-transform:uppercase;color:var(--faint);font-weight:700}
.pair .v{font-family:var(--mono);font-size:19px;font-weight:700}
.note{background:var(--amberbg);border:1px solid var(--amberline);border-radius:9px;padding:9px 12px;
  font-size:12.5px;color:var(--amber);line-height:1.5;margin-top:11px}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:12px;font-size:11.5px;color:var(--faint)}
@media print{
  body{background:#fff}.page{max-width:none;padding:0}
  .hero{border-radius:0}
  section{break-inside:avoid-page}
  .stage{break-inside:avoid}
}
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def half(n, peak, maxw=46):
    if not n or n <= 0 or peak <= 0:
        return 3.0
    return max(3.0, (n / peak) ** 0.5 * maxw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--pillar", default="CYBERSECURITY")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sb = db()
    P = a.pillar

    rep = sb.table("reports").select("*").eq("id", a.report).execute().data[0]
    ledger = sb.table("generation_ledger").select("*").eq("report_id", a.report).execute().data
    gaps = sb.table("research_gaps").select("raised_by,gap").eq("pillar", P).execute().data
    fcs = sb.table("forecasts").select("id,statement,horizon,plausibility,falsifier,basis") \
            .eq("pillar", P).order("id").execute().data
    gates = sb.table("validation_gates").select("id,status,blocks").execute().data
    sc = (sb.table("scorecards").select("*").order("created_at", desc=True)
          .limit(1).execute().data or [None])[0]
    srcs = sb.table("source_registry").select("id,tier,publisher").execute().data

    def count(t, pillar=True):
        try:
            q = sb.table(t).select("id")
            if pillar:
                q = q.eq("pillar", P)
            return len(q.execute().data)
        except Exception:
            try:
                return len(sb.table(t).select("id").execute().data)
            except Exception:
                return 0

    counts = {t: count(t, t not in ("documents", "risks", "scenarios", "options",
                                    "initiatives", "validation_gates"))
              for _, t, _, _, _ in ONTOLOGY}
    counts["documents"] = count("documents", False)

    by_rule = collections.Counter(g["raised_by"] or "unattributed" for g in gaps)
    flowing = {
        "collect": counts.get("documents", 0),
        "extract": counts.get("evidence", 0),
        "rules": counts.get("evidence", 0),
        "synthesize": counts.get("signals", 0) + counts.get("trends", 0)
                      + counts.get("findings", 0) + counts.get("risks", 0),
        "strategize": counts.get("scenarios", 0) + counts.get("options", 0)
                      + counts.get("opportunities", 0),
        "forecast": counts.get("forecasts", 0),
        "generate": len(ledger),
        "verify": len([l for l in ledger if not l.get("withheld")]),
    }
    peak = max([1] + list(flowing.values()))

    o = []
    w = o.append
    w("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    w("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    w("<title>How this report was built</title>")
    w("<link rel='preconnect' href='https://fonts.googleapis.com'>")
    w("<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
      "family=Instrument+Sans:wght@400;600;700&family=Space+Grotesk:wght@500;600;700&"
      "family=JetBrains+Mono:wght@400;700&display=swap'>")
    w("<style>%s</style></head><body><div class='page'>" % CSS)

    # ---------------------------------------------------------------- hero
    w("<div class='hero'><div class='kicker' style='color:#93A7E8'>Methodology companion · %s</div>"
      "<h1>A model drafts. The rules decide.</h1>"
      "<div class='lede'>This document accompanies <b>%s</b>. It records how the report was "
      "produced — the object model, what each stage refused and which rule refused it, how "
      "each forecast was calibrated, and how the finished text scored against the "
      "human-written report it is measured on. Every number here is read from the same "
      "tables the report was written from.</div></div>"
      % (esc(date.today().isoformat()), esc(rep.get("title"))))

    # ---------------------------------------------------------------- ontology
    w("<section><h2>1 · The modelled layer</h2><div class='sub'>Objects are typed and linked, "
      "so a sentence in the report can be walked back to the span it came from. The division "
      "below is what stops the model grading its own work: fields in "
      "<span class='chip n'>blue</span> are proposed by a language model, fields in "
      "<span class='chip s'>grey</span> may only ever be set by deterministic code.</div>"
      "<div class='grid'>")
    for name, table, gloss, neural, symbolic in ONTOLOGY:
        w("<div class='obj'><div class='t'><span class='n'>%s</span>"
          "<span class='c'>%s</span></div><div class='g'>%s</div>"
          % (esc(name), counts.get(table, 0), esc(gloss)))
        w(" ".join("<span class='chip n'>%s</span>" % esc(f) for f in neural)
          + " " + " ".join("<span class='chip s'>%s</span>" % esc(f) for f in symbolic))
        w("</div>")
    w("</div></section>")

    # ---------------------------------------------------------------- stages
    w("<section><h2>2 · What each stage refused</h2><div class='sub'>The rail narrows as "
      "objects are dropped. Everything leaving it was written to the refusal ledger with the "
      "rule that decided — %d refusals across this pillar. What the analysis declined to "
      "assert is part of what it reports.</div><div class='card'>" % len(gaps))
    prev = flowing.get("collect", 0)
    for i, (key, nm, layer, src, desc, refuses) in enumerate(STAGES):
        label, fg, bg, line, spine = LAYERS[layer]
        out = flowing.get(key, prev)
        iw, ow = half(prev, peak), half(out, peak)
        rules = [(r, c) for r, c in by_rule.items() if REFUSAL_STAGE.get(r) == key]
        rules.sort(key=lambda kv: -kv[1])
        dropped = sum(c for _, c in rules)
        w("<div class='stage'><div class='rail'>"
          "<svg viewBox='0 0 100 100' preserveAspectRatio='none'>"
          "<polygon points='%.1f,0 %.1f,0 %.1f,100 %.1f,100' fill='%s' fill-opacity='.85' "
          "stroke='%s' stroke-width='.5' stroke-opacity='.45'/></svg>"
          "<span class='ct' style='color:%s;border:1px solid %s'>%d</span></div>"
          % (50 - iw, 50 + iw, 50 + ow, 50 - ow, spine, fg, fg, line, out))
        w("<div class='sb'><div class='sh'><span class='i'>%02d</span>"
          "<span class='nm'>%s</span><span class='lb' style='color:%s;background:%s;"
          "border:1px solid %s'>%s</span><span class='src'>%s</span></div>"
          % (i + 1, esc(nm), fg, bg, line, esc(label), esc(src)))
        w("<div class='sd'>%s</div><div class='sr'>%s</div>" % (esc(desc), esc(refuses)))
        if dropped:
            w("<div class='ref'><span class='h'>&#8627; refused %d</span>" % dropped)
            for r, c in rules:
                w("<span class='chip a'>%s &middot; %d</span>" % (esc(r), c))
            w("</div>")
        w("</div></div>")
        prev = out
    w("</div></section>")

    # ---------------------------------------------------------------- calibration
    w("<section><h2>3 · How each forecast was calibrated</h2><div class='sub'>A plausibility "
      "label on its own is indistinguishable from a guess, and a percentage asked of a model "
      "is a confident number with nothing under it. The band is arithmetic: corroboration "
      "breadth earns points, distance and unresolved questions cost them. A reader who "
      "disagrees with a band can see which term to argue with.</div>")
    for f in fcs:
        b = f.get("basis") or {}
        terms = [("signal strength", b.get("signal_points"), " + ".join(b.get("strengths") or [])),
                 ("independent publishers", b.get("publisher_points"),
                  "%s distinct publishers behind it" % b.get("publishers", "?")),
                 ("horizon distance", b.get("horizon_penalty"), "the further out, the weaker the claim"),
                 ("open uncertainties", b.get("uncertainty_penalty"), "each unresolved question costs a point")]
        w("<div class='calc'><div style='display:flex;gap:8px;align-items:baseline'>"
          "<span class='chip'>%s</span><span style='font-size:11.5px;color:var(--muted)'>%s</span>"
          "<span style='margin-left:auto' class='chip'>score %s</span>"
          "<span class='chip a'>%s</span></div>"
          "<div style='font-size:13px;margin:7px 0 8px;max-width:76ch'>%s</div>"
          % (esc(f["id"]), esc(f.get("horizon")), b.get("score", "?"),
             esc(f.get("plausibility")), esc(f.get("statement"))))
        for lab, val, note in terms:
            if val is None:
                continue
            col = "var(--amber)" if val < 0 else "var(--green)"
            w("<div class='row'><span class='v' style='color:%s'>%s</span>"
              "<span class='l'>%s</span><span class='nt'>%s</span></div>"
              % (col, ("%d" % val if val < 0 else "+%d" % val), esc(lab), esc(note)))
        if f.get("falsifier"):
            w("<div style='margin-top:8px;padding-top:8px;border-top:1px dashed var(--line);"
              "font-size:12px;color:var(--muted)'><b style='color:var(--faint);font-size:10px;"
              "letter-spacing:.8px;text-transform:uppercase'>What would refute this</b><br>%s</div>"
              % esc(f["falsifier"]))
        w("</div>")
    w("</section>")

    # ---------------------------------------------------------------- ledger
    total_retries = sum(l.get("retries") or 0 for l in ledger)
    withheld = len([l for l in ledger if l.get("withheld")])
    w("<section><h2>4 · How the report was assembled</h2><div class='sub'>Each section was "
      "given a bounded slice of the graph and redrafted until it passed verification. "
      "%d sections, %d redrafts rejected before publication, %s.</div>"
      "<div class='card' style='padding:16px 18px'><table><thead><tr>"
      "<th>Section</th><th>Given</th><th>Held back</th><th class='num'>Redrafts</th>"
      "<th class='num'>Citations</th></tr></thead><tbody>"
      % (len(ledger), total_retries,
         "none withheld" if withheld == 0 else "%d withheld" % withheld))
    for l in ledger:
        def chips(m, cls):
            return " ".join("<span class='chip %s'>%s %d</span>" % (cls, esc(k), v)
                            for k, v in sorted((m or {}).items(), key=lambda kv: -kv[1]) if v) or "&mdash;"
        w("<tr><td><b>%s</b><br><span class='c' style='font-family:var(--mono);font-size:10.5px;"
          "color:var(--ghost)'>%s</span></td><td>%s</td><td>%s</td>"
          "<td class='num' style='color:%s'>%s</td><td class='num'>%d</td></tr>"
          % (esc(l.get("section_title")), esc(l.get("section_key")),
             chips(l.get("rows_passed"), ""), chips(l.get("rows_withheld"), "a"),
             "var(--amber)" if (l.get("retries") or 0) else "var(--ghost)",
             l.get("retries") or 0, len(l.get("citations_emitted") or [])))
    w("</tbody></table></div></section>")

    # ---------------------------------------------------------------- audit
    w("<section><h2>5 · The audit</h2>")
    open_gates = [g for g in gates if g["status"] == "OPEN"]
    if sc and sc.get("ours_text") and sc.get("benchmark_text"):
        ours, theirs = sc["ours_text"], sc["benchmark_text"]
        w("<div class='sub'>Scored against <span class='chip'>%s</span> — the human-written "
          "report this system exists to beat.</div><div style='display:flex;gap:9px;flex-wrap:wrap'>"
          % esc(sc.get("benchmark_label")))
        for k, mine, yours, low in [
                ("unsourced assertions", ours.get("unsourced"), theirs.get("unsourced"), True),
                ("citations / 1k words", ours.get("citations_per_1k_words"),
                 theirs.get("citations_per_1k_words"), False),
                ("sentences cited", ours.get("cited_sentences"), theirs.get("cited_sentences"), False)]:
            wins = (mine <= yours) if low else (mine >= yours)
            w("<div class='pair'><div class='k'>%s</div><div style='display:flex;gap:8px;"
              "align-items:baseline;margin-top:6px'><span class='v' style='color:%s'>%s</span>"
              "<span style='font-size:11.5px;color:var(--ghost)'>vs</span>"
              "<span style='font-family:var(--mono);color:var(--muted)'>%s</span></div>"
              "<div style='font-size:10.5px;color:var(--ghost);margin-top:3px'>ours &middot; "
              "the human report</div></div>"
              % (esc(k), "var(--green)" if wins else "var(--amber)", esc(mine), esc(yours)))
        w("</div>")
        rec = sc.get("recall") or {}
        if rec:
            w("<div class='note'><b>Where it is behind:</b> of the benchmark&rsquo;s in-scope "
              "items this run matched %s. Recall is the open weakness — the pipeline is "
              "stricter than the human author, and strictness costs coverage.</div>"
              % esc(" &middot; ".join("%s/%s %s" % (v.get("in_scope_matched"), v.get("in_scope"), k)
                                      for k, v in rec.items())))
    if open_gates:
        w("<div class='note'>%d validation gate%s open. While a gate is open the claims it "
          "names cannot be asserted anywhere in the report — not in a finding, not in a "
          "forecast, not in a sentence of prose.<br>%s</div>"
          % (len(open_gates), "" if len(open_gates) == 1 else "s",
             "<br>".join("<span class='chip'>%s</span> %s" % (esc(g["id"]), esc(g.get("blocks")))
                         for g in open_gates)))
    w("</section>")

    w("<section><h2>6 · Why it is built this way</h2><div class='sub' style='max-width:76ch'>"
      "A language model asked to assess evidence will also grade its own assessment, and it "
      "will do so fluently. Splitting the work removes that: the model is used where judgement "
      "about language is needed — reading a page, drafting a claim, writing a paragraph — and "
      "every decision that changes what a reader is told is made by code that can be read, "
      "rerun and disagreed with. <b>That is why the refusal counts are in this document.</b> "
      "A system that never refuses is not being careful, and the only way to show care is to "
      "show what was turned down and on what grounds.</div></section>")

    w("<footer>Generated from the live graph on %s &middot; report %s &middot; "
      "%d registered sources across %d tiers.</footer>"
      % (esc(date.today().isoformat()), esc(a.report[:8]), len(srcs),
         len({s["tier"] for s in srcs})))
    w("</div></body></html>")

    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o))
    print("wrote %s (%d chars, %d stages, %d refusals, %d forecasts, %d ledger rows)"
          % (a.out, sum(len(x) for x in o), len(STAGES), len(gaps), len(fcs), len(ledger)))


if __name__ == "__main__":
    main()
