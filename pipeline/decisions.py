"""Jev decision gates — typed, probabilistic judgements with explicit thresholds.

Gate 3 (same-fact corroboration merge) is implemented here. Gates 1 and 2
(relevance triage, quote-supports-claim entailment) are reserved for the
decision-layer workstream and are not implemented in this file.

WHY GATE 3 MATTERS: extraction emits one evidence row per claim it finds, so a
single article yields several rows that restate one fact. Left alone, the
corroboration rules read those rows as independent support. Gate 3 collapses
them back into one row — carrying every source forward — so that independence
is measured over facts, not sentences.

  python decisions.py --gate 3 --pillar CYBERSECURITY
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from typing import List

from pydantic import BaseModel, Field

import llm
from config import db

SAME_FACT_THRESHOLD = 0.85


class SameFactVerdict(BaseModel):
    same_fact: bool
    probability: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=300)


class PairJudgement(BaseModel):
    a_id: str
    b_id: str
    same_fact: bool
    probability: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=300)


class MergeBatch(BaseModel):
    judgements: List[PairJudgement] = Field(default_factory=list)


PROMPT = """You are Gate 3 of an evidence pipeline: same-fact corroboration.

Below are evidence rows extracted from THE SAME SOURCE DOCUMENT, in the same
pillar and topic. Decide, for each listed pair, whether the two rows assert the
SAME underlying fact — restated, reworded, or split across sentences — rather
than two genuinely different facts.

Same fact: "Russia will increase hybrid attacks on NATO" / "DDIS assesses Russia
will intensify hybrid war against the West and NATO" — one assessment, restated.

Different facts: "Russia will increase hybrid attacks" / "sabotage incidents rose
last quarter" — related, but distinct assertions.

Give a probability for each pair. Be conservative: merging two genuinely
different facts destroys information, so only go above 0.85 when the rows really
are the same assertion.

PAIRS TO JUDGE:
{pairs}
"""


def _fmt(rows_by_id, pairs):
    out = []
    for a, b in pairs:
        out.append(
            "PAIR a_id=%s b_id=%s\n  A [topic %s]: %s\n  B [topic %s]: %s"
            % (a, b, rows_by_id[a].get("topic_id"), rows_by_id[a]["claim"],
               rows_by_id[b].get("topic_id"), rows_by_id[b]["claim"]))
    return "\n\n".join(out)


def _merge(sb, keep: str, drop: str):
    """Fold `drop` into `keep`, preserving every source and link."""
    for row in (sb.table("evidence_sources").select("document_id")
                .eq("evidence_id", drop).execute().data):
        sb.table("evidence_sources").upsert(
            {"evidence_id": keep, "document_id": row["document_id"]}).execute()
    for row in (sb.table("signal_evidence").select("signal_id")
                .eq("evidence_id", drop).execute().data):
        sb.table("signal_evidence").upsert(
            {"signal_id": row["signal_id"], "evidence_id": keep}).execute()
    for row in (sb.table("entity_evidence").select("entity_id")
                .eq("evidence_id", drop).execute().data):
        sb.table("entity_evidence").upsert(
            {"entity_id": row["entity_id"], "evidence_id": keep}).execute()

    sb.table("signal_evidence").delete().eq("evidence_id", drop).execute()
    sb.table("entity_evidence").delete().eq("evidence_id", drop).execute()
    sb.table("evidence_sources").delete().eq("evidence_id", drop).execute()
    sb.table("evidence").delete().eq("id", drop).execute()


def gate3_same_fact(sb, pillar: str, dry_run: bool = False) -> int:
    """Merge same-fact evidence rows that share a document, pillar and topic."""
    ev = (sb.table("evidence").select("id,claim,topic_id,pillar")
          .eq("pillar", pillar).order("id").execute().data)
    if not ev:
        print("no evidence for %s" % pillar)
        return 0
    rows_by_id = {e["id"]: e for e in ev}

    srcs = (sb.table("evidence_sources").select("evidence_id,document_id")
            .in_("evidence_id", list(rows_by_id)).execute().data)
    by_doc = defaultdict(list)
    for s in srcs:
        by_doc[s["document_id"]].append(s["evidence_id"])

    # Candidate pairs: rows sharing a DOCUMENT. Cross-document agreement is
    # corroboration and must never be merged away — that is the signal itself.
    #
    # Topic was the intended second constraint, but extraction currently assigns
    # topic_id round-robin rather than semantically (one Breaking Defense article
    # produced CS-T01/T02/T03/T04 in sequence), so gating on topic equality
    # rejects every real duplicate. The document boundary is the sound scope;
    # topic is passed to the judge as context instead of used as a filter.
    pairs = []
    for doc, ids in by_doc.items():
        ids = sorted(set(ids))
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if a in rows_by_id and b in rows_by_id:
                    pairs.append((a, b))

    if not pairs:
        print("GATE 3: no same-document candidate pairs in %s" % pillar)
        return 0
    print("GATE 3: judging %d candidate pair(s) in %s" % (len(pairs), pillar))

    result = llm.structured(PROMPT.format(pairs=_fmt(rows_by_id, pairs)),
                            MergeBatch, effort="high")

    merged, alive = 0, {i: i for i in rows_by_id}

    def root(x):
        while alive[x] != x:
            x = alive[x]
        return x

    for j in sorted(result.judgements, key=lambda x: -x.probability):
        if j.a_id not in alive or j.b_id not in alive:
            continue
        verdict = "MERGE" if (j.same_fact and j.probability >= SAME_FACT_THRESHOLD) else "keep"
        print("  p=%.2f %-5s %s + %s — %s"
              % (j.probability, verdict, j.a_id, j.b_id, j.reason[:70]))
        if verdict != "MERGE":
            continue
        keep, drop = sorted([root(j.a_id), root(j.b_id)])
        if keep == drop:
            continue
        if not dry_run:
            _merge(sb, keep, drop)
        alive[drop] = keep
        merged += 1

    print("GATE 3: merged %d row(s)%s" % (merged, " (dry run)" if dry_run else ""))
    return merged


def main():
    ap = argparse.ArgumentParser(description="Jev decision gates")
    ap.add_argument("--gate", type=int, required=True, choices=[3],
                    help="3 = same-fact corroboration merge")
    ap.add_argument("--pillar", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    gate3_same_fact(db(), a.pillar, dry_run=a.dry_run)


if __name__ == "__main__":
    main()
