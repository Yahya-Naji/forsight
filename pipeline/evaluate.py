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
import hashlib
import json
import os
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
SUPPORTED = (".docx", ".pdf", ".txt", ".md", ".html", ".htm")
CACHE_DIR = "out/benchmarks"


def read_document(path: str) -> List[str]:
    """Paragraphs from a benchmark in whatever format it arrives as.

    A comparison is only useful if you can point it at the document you
    actually have — a client's PDF, a competitor's report, a Word draft.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return docx_text(path)
    if ext == ".pdf":
        return pdf_text(path)
    if ext in (".html", ".htm"):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(open(path, encoding="utf-8", errors="ignore").read(), "html.parser")
        for t in soup(["script", "style"]):
            t.decompose()
        return [l.strip() for l in soup.get_text("\n").splitlines() if l.strip()]
    if ext in (".txt", ".md"):
        return [l.strip() for l in open(path, encoding="utf-8", errors="ignore") if l.strip()]
    raise SystemExit("unsupported benchmark format %r (expected one of %s)"
                     % (ext, ", ".join(SUPPORTED)))


def pdf_text(path: str) -> List[str]:
    from pypdf import PdfReader
    out = []
    for page in PdfReader(path).pages:
        try:
            for line in (page.extract_text() or "").splitlines():
                if line.strip():
                    out.append(line.strip())
        except Exception:
            continue
    return out


def docx_text(path: str) -> List[str]:
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    out = []
    for para in re.split(r"</w:p>", x):
        t = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.S))
        t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        if t.strip():
            out.append(t.strip())
    return out


class BenchItem(BaseModel):
    id: str = Field(max_length=24)
    text: str = Field(max_length=300)


class BenchRegisters(BaseModel):
    signals: List[BenchItem] = Field(default_factory=list)
    findings: List[BenchItem] = Field(default_factory=list)
    risks: List[BenchItem] = Field(default_factory=list)
    uncertainties: List[BenchItem] = Field(default_factory=list)


EXTRACT_PROMPT = """Read this excerpt of a strategic-foresight document and pull
out its analytical registers.

  signals       — observed changes the document treats as directional
  findings      — analytical conclusions it draws
  risks         — what it says could go wrong
  uncertainties — what it says is genuinely unresolved

Rules:
- Use the document's own ids where it has them (SIG-04, F-02, R7, CU-01). Where
  it has none, mint one: S1, F1, R1, U1.
- One entry per distinct item; do not split a claim across entries.
- Quote or tightly paraphrase. Do not add anything the document does not say.
- An empty register is a valid answer. Do not invent items to fill it.

EXCERPT:
{chunk}
"""


def _llm_registers(lines: List[str]) -> Dict[str, List[dict]]:
    """Extract registers from a document with no recognisable id scheme.

    Chunked, because a full foresight report exceeds the context window and
    silently truncating it would understate the benchmark — making our recall
    look better than it is.
    """
    text = "\n".join(lines)
    size, out = 40000, {"signals": [], "findings": [], "risks": [], "uncertainties": []}
    chunks = [text[i:i + size] for i in range(0, len(text), size)]
    print("  no id scheme recognised — extracting with the model (%d chunk(s))" % len(chunks))
    for n, chunk in enumerate(chunks, 1):
        try:
            got = llm.structured(EXTRACT_PROMPT.format(chunk=chunk), BenchRegisters,
                                 fast=True, effort="medium", max_output_tokens=16000)
        except Exception as exc:
            print("    chunk %d failed: %s" % (n, exc))
            continue
        for key in out:
            for item in getattr(got, key):
                out[key].append({"id": "%s.%s" % (n, item.id), "text": item.text})
        print("    chunk %d/%d → %s" % (n, len(chunks),
              " ".join("%s %d" % (k, len(getattr(got, k))) for k in out)))
    return out


def parse_benchmark(path: str, use_cache: bool = True) -> Dict[str, List[dict]]:
    """Registers from any supported document. Cached — model extraction over a
    200-page report is not something to re-pay for on every evaluation."""
    lines = read_document(path)
    digest = hashlib.sha256(("\n".join(lines)).encode()).hexdigest()[:16]
    cache = os.path.join(CACHE_DIR, digest + ".json")
    if use_cache and os.path.exists(cache):
        print("  registers from cache (%s)" % cache)
        return json.load(open(cache))

    reg = _pattern_registers(lines)
    found = sum(len(v) for v in reg.values())
    if found < 4:
        reg = _llm_registers(lines)
    else:
        print("  registers recovered by id pattern (%d items)" % found)

    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(reg, open(cache, "w", encoding="utf-8"), indent=1)
    return reg


def _pattern_registers(lines: List[str]) -> Dict[str, List[dict]]:
    """Documents that already carry an id scheme (SIG-04, F-02, R7, CU-01)."""
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
# Numeric footnotes [12] and object references (EV-001, SIG-CS-04) both count:
# scoring a document at zero because it cites by id rather than by number would
# be an artefact of our own conventions.
NUM_CITE = re.compile(r"\[\d+\]|\b(?:EV|SIG|F|R|TR|CU|FC)-[A-Z0-9-]+\b")


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
    ap.add_argument("--benchmark", default=BENCHMARK,
                    help="document to score against: .docx .pdf .txt .md .html")
    ap.add_argument("--no-cache", action="store_true",
                    help="re-extract the benchmark registers instead of reusing the cache")
    ap.add_argument("--json", help="write the scorecard to this path")
    a = ap.parse_args()
    sb = db()

    bench = parse_benchmark(a.benchmark, use_cache=not a.no_cache)
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
    bench_sents = [l for l in read_document(a.benchmark) if len(l) > 40 and not l.startswith("•")]
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
    bench_name = os.path.basename(a.benchmark)
    if len(bench_name) > 18:
        bench_name = bench_name[:15] + "…"
    print("═" * 74)
    print("  METRIC                        THIS SYSTEM        %s" % bench_name)
    print("═" * 74)
    print("  Unsourced assertion rate      %-18s %s" % (ours_m["unsourced_rate"], bench_m["unsourced_rate"]))
    print("  Unsourced assertions          %-18d %d" % (ours_m["unsourced"], bench_m["unsourced"]))
    print("  Citations per 1k words        %-18s %s" % (ours_m["citations_per_1k_words"], bench_m["citations_per_1k_words"]))
    print("  Sentences analysed            %-18d %d" % (ours_m["sentences"], bench_m["sentences"]))
    print("  Chain completeness            %-18s n/a (not machine-readable)" % ("%.0f%%" % (chain["rate"] * 100)))
    print("  Citation entailment           see verify.py       not measurable — sources absent")
    if ours_m["sentences"] < 20 or bench_m["sentences"] < 20:
        print("  ! one document is very short; treat these rates as indicative")
    print("═" * 74)
    print("  Novel items (not in benchmark): " +
          " · ".join("%s %d" % (k, len(v)) for k, v in novel.items()))

    card = {"pillar": a.pillar, "report_id": report["id"], "benchmark": a.benchmark,
            "recall": scoped, "ours_text": ours_m, "benchmark_text": bench_m,
            "chain_completeness": chain, "novel": novel,
            "matches": {k: [m.model_dump() for m in v] for k, v in results.items()}}
    # Persist so the console can render it: a scorecard on someone's disk
    # convinces nobody.
    try:
        sb.table("scorecards").insert({
            "pillar": a.pillar, "report_id": report["id"],
            "benchmark": a.benchmark, "benchmark_label": os.path.basename(a.benchmark),
            "recall": scoped, "ours_text": ours_m, "benchmark_text": bench_m,
            "chain_completeness": chain, "novel": novel}).execute()
        print("\n  scorecard stored")
    except Exception as exc:
        print("\n  (could not store scorecard: %s)" % exc)

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(card, fh, indent=2)
        print("  scorecard written to %s" % a.json)


if __name__ == "__main__":
    main()
