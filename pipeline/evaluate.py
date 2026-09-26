"""STEP 10 — Evaluation: score the agent's output against the human report.

The benchmark is FETC's human-written Counter-UAS V1.0. It is an EW-led
document; our graph currently covers CYBERSECURITY. Comparing every benchmark
signal against a cyber-only graph would report ~0% recall and mean nothing, so
each benchmark item is first classified by domain and recall is reported BOTH
in-scope and overall. An evaluation that flatters or damns itself by construction
is worthless.

What is measured deterministically (no model, both documents, same code):
  · unsourced assertion rate
  · citation density
What is measured with a model (semantic matching, both directions):
  · signal / finding / risk / uncertainty recall
  · novelty — items we found that the benchmark does not contain
What cannot be measured:
  · entailment on the human report — its sources are not in our graph, so there
    is nothing to check its citations against. Stated, not estimated.

  python evaluate.py --pillar CYBERSECURITY
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

import llm
import verify
from config import db

BENCHMARK = "docs/source/counter-uas-report-v1.0.docx"


# --------------------------------------------------------------------------
# benchmark extraction
# --------------------------------------------------------------------------
def docx_text(path: str) -> List[str]:
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    out = []
    for para in re.split(r"</w:p>", x):
        t = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.S))
        t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        if t.strip():
            out.append(t.strip())
    return out


def parse_benchmark(path: str) -> Dict[str, List[dict]]:
    lines = docx_text(path)
    joined = "\n".join(lines)
    reg = {"signals": [], "findings": [], "risks": [], "uncertainties": []}

    for m in re.finditer(r"^(SIG-\d+)\s*\|\s*([^|]+)\|", joined, re.M):
        reg["signals"].append({"id": m.group(1), "text": m.group(2).strip()})
    for m in re.finditer(r"Finding (F-\d+):\s*(.+)", joined):
        reg["findings"].append({"id": m.group(1), "text": m.group(2).strip()[:300]})
    for m in re.finditer(r"^(R\d+)\s*—\s*(.+?)\s*—\s*Score", joined, re.M):
        reg["risks"].append({"id": m.group(1), "text": m.group(2).strip()})
    for m in re.finditer(r"^(CU-\d+)\s*—\s*(.+)", joined, re.M):
        reg["uncertainties"].append({"id": m.group(1), "text": m.group(2).strip()[:300]})

    for k in reg:                                   # dedupe, keep first mention
        seen, uniq = set(), []
        for r in reg[k]:
            if r["id"] not in seen:
                seen.add(r["id"]); uniq.append(r)
        reg[k] = uniq
    return reg


# --------------------------------------------------------------------------
# deterministic text metrics — identical code on both documents
# --------------------------------------------------------------------------
NUM_CITE = re.compile(r"\[\d+\]")


def text_metrics(sentences: List[str], citation_re) -> dict:
    words = sum(len(s.split()) for s in sentences)
    cited = [s for s in sentences if citation_re.search(s)]
    unsourced = 0
    for s in sentences:
        if citation_re.search(s):
            continue
        if not verify.ASSERTIVE.search(s):
            continue
        if any(h in s.lower() for h in verify.HEDGES):
            continue
        if verify.is_recommendation(s):
            continue
        unsourced += 1
    return {"sentences": len(sentences), "words": words,
            "cited_sentences": len(cited), "unsourced": unsourced,
            "citations_per_1k_words": round(len(cited) / max(words, 1) * 1000, 1),
            "unsourced_rate": round(unsourced / max(len(sentences), 1), 3)}


# --------------------------------------------------------------------------
# semantic matching
# --------------------------------------------------------------------------
class Match(BaseModel):
    benchmark_id: str
    domain: str = Field(description="CYBERSECURITY | AI | ELECTRONIC_WARFARE | PROCUREMENT | CROSS_CUTTING")
    matched: bool
    our_id: Optional[str] = None
    note: str = Field(max_length=200)


class MatchSet(BaseModel):
    matches: List[Match] = Field(default_factory=list)


MATCH_PROMPT = """Compare a human-written foresight report's register against an
automated system's output.

For EACH benchmark item below:
1. `domain` — which pillar it belongs to: CYBERSECURITY, AI, ELECTRONIC_WARFARE,
   PROCUREMENT, or CROSS_CUTTING if it spans several.
2. `matched` — true only if one of OUR items expresses substantially the same
   analytical point. Same topic area is NOT a match; the claim must correspond.
3. `our_id` — the matching id, when matched.

Be strict. A generous match makes the evaluation worthless. Judge the claim, not
the vocabulary.

BENCHMARK ITEMS ({kind}):
{benchmark}

OUR ITEMS ({kind}):
{ours}
"""


def match_register(kind: str, bench: List[dict], ours: List[dict]) -> List[Match]:
    if not bench:
        return []
    ours_txt = "\n".join("  %s %s" % (o["id"], o["text"][:190]) for o in ours) or "  (none)"
    bench_txt = "\n".join("  %s %s" % (b["id"], b["text"][:190]) for b in bench)
    return llm.structured(
        MATCH_PROMPT.format(kind=kind, benchmark=bench_txt, ours=ours_txt),
        MatchSet, effort="high", max_output_tokens=16000).matches


# --------------------------------------------------------------------------
def our_register(sb, pillar: str) -> Dict[str, List[dict]]:
    g = {}
    g["signals"] = [{"id": r["id"], "text": r["statement"]} for r in
                    sb.table("signals").select("id,statement").eq("pillar", pillar).execute().data]
    g["findings"] = [{"id": r["id"], "text": r["statement"]} for r in
                     sb.table("findings").select("id,statement").eq("pillar", pillar).execute().data]
    g["risks"] = [{"id": r["id"], "text": r["statement"]} for r in
                  sb.table("risks").select("id,statement").eq("pillar", pillar).execute().data]
    g["uncertainties"] = [{"id": r["id"], "text": r["question"]} for r in
                          sb.table("uncertainties").select("id,question").eq("pillar", pillar).execute().data]
    return g


def chain_completeness(sb, pillar: str) -> dict:
    """Share of our findings with a full evidence -> signal -> finding path."""
    findings = sb.table("findings").select("id").eq("pillar", pillar).execute().data
    if not findings:
        return {"findings": 0, "complete": 0, "rate": 0.0}
    complete = 0
    for f in findings:
        sigs = [l["from_id"] for l in sb.table("links").select("from_id")
                .eq("to_id", f["id"]).eq("from_type", "signal").execute().data]
        if not sigs:
            continue
        ev = sb.table("signal_evidence").select("evidence_id").in_("signal_id", sigs).execute().data
        if ev:
            complete += 1
    return {"findings": len(findings), "complete": complete,
            "rate": round(complete / len(findings), 3)}


def main():
    ap = argparse.ArgumentParser(description="Score the agent against the human report")
    ap.add_argument("--pillar", required=True)
    ap.add_argument("--report", help="reports.id to score; default = latest for the pillar")
    ap.add_argument("--benchmark", default=BENCHMARK)
    ap.add_argument("--json", help="write the scorecard to this path")
    a = ap.parse_args()
    sb = db()

    bench = parse_benchmark(a.benchmark)
    ours = our_register(sb, a.pillar)
    print("benchmark : %s" % a.benchmark)
    print("  registers: " + " · ".join("%s %d" % (k, len(v)) for k, v in bench.items()))
    print("  ours     : " + " · ".join("%s %d" % (k, len(v)) for k, v in ours.items()))
    print()

    rows = (sb.table("reports").select("id,title,body_md")
            .eq("pillar", a.pillar).order("created_at", desc=True).limit(1).execute().data
            if not a.report else
            sb.table("reports").select("id,title,body_md").eq("id", a.report).execute().data)
    if not rows:
        raise SystemExit("no report for %s" % a.pillar)
    report = rows[0]

    # ---- deterministic, same code both sides -----------------------------
    ours_m = text_metrics(verify.sentences_of(report["body_md"] or ""), verify.OBJECT_REF)
    bench_sents = [l for l in docx_text(a.benchmark) if len(l) > 40 and not l.startswith("•")]
    bench_m = text_metrics(bench_sents, NUM_CITE)

    # ---- semantic recall, per register -----------------------------------
    results, scoped = {}, {}
    for kind in ("signals", "findings", "risks", "uncertainties"):
        ms = match_register(kind, bench[kind], ours[kind])
        results[kind] = ms
        in_scope = [m for m in ms if m.domain in (a.pillar, "CROSS_CUTTING")]
        scoped[kind] = {
            "benchmark_total": len(bench[kind]),
            "in_scope": len(in_scope),
            "in_scope_matched": sum(1 for m in in_scope if m.matched),
            "overall_matched": sum(1 for m in ms if m.matched),
        }
        s = scoped[kind]
        rate = s["in_scope_matched"] / s["in_scope"] if s["in_scope"] else None
        print("  %-14s benchmark %-3d | in scope %-3d | matched %-3d | in-scope recall %s"
              % (kind, s["benchmark_total"], s["in_scope"], s["in_scope_matched"],
                 ("%.0f%%" % (rate * 100)) if rate is not None else "n/a"))

    chain = chain_completeness(sb, a.pillar)
    matched_ours = {m.our_id for ms in results.values() for m in ms if m.matched and m.our_id}
    novel = {k: [o["id"] for o in v if o["id"] not in matched_ours] for k, v in ours.items()}

    print()
    print("═" * 74)
    print("  METRIC                        THIS SYSTEM        HUMAN V1.0")
    print("═" * 74)
    print("  Unsourced assertion rate      %-18s %s" % (ours_m["unsourced_rate"], bench_m["unsourced_rate"]))
    print("  Unsourced assertions          %-18d %d" % (ours_m["unsourced"], bench_m["unsourced"]))
    print("  Citations per 1k words        %-18s %s" % (ours_m["citations_per_1k_words"], bench_m["citations_per_1k_words"]))
    print("  Sentences analysed            %-18d %d" % (ours_m["sentences"], bench_m["sentences"]))
    print("  Chain completeness            %-18s n/a (not machine-readable)" % ("%.0f%%" % (chain["rate"] * 100)))
    print("  Citation entailment           see verify.py       not measurable — sources absent")
    print("═" * 74)
    print("  Novel items (not in benchmark): " +
          " · ".join("%s %d" % (k, len(v)) for k, v in novel.items()))

    card = {"pillar": a.pillar, "report_id": report["id"], "benchmark": a.benchmark,
            "recall": scoped, "ours_text": ours_m, "benchmark_text": bench_m,
            "chain_completeness": chain, "novel": novel,
            "matches": {k: [m.model_dump() for m in v] for k, v in results.items()}}
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(card, fh, indent=2)
        print("\n  scorecard written to %s" % a.json)


if __name__ == "__main__":
    main()
