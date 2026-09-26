"""STEP 3 — Extractor (NEURAL layer): reads stored documents and emits
EvidenceCandidate/EntityCandidate JSON validated against models.py.
Anything that fails validation is rejected into the research-gap log.
Usage: python extract.py --pillar CYBERSECURITY [--limit 5]"""
import argparse, json, re
import layers
import llm
import config
from config import db
from models import ExtractionResult, ENTITY_TYPES

PROMPT = """You are the extraction agent of a strategic-foresight pipeline.
Read the document and emit STRICT JSON with keys "evidence" and "entities".

Rules (violations are rejected by a validator, so follow exactly):
- Each evidence item: claim (20-500 chars, one factual claim), env_layer (UAE|REGIONAL|GLOBAL).
  env_layer is UAE ONLY when the quote_span explicitly names the UAE, an Emirate
  (Abu Dhabi, Dubai, Sharjah...) or a UAE institution (Tawazun, aeCERT, TDRA).
  "Middle East", "Gulf" or "the region" are REGIONAL, never UAE. A regional
  observation is not a UAE observation.
  steep (subset of Social/Technological/Economic/Environmental/Political),
  pillar (must be {pillar}), topic_id (one of: {topics}),
  quote_span (VERBATIM words copied from the document, 10-400 chars).
- Do NOT assign confidence or evidence class - that is not your job.
- Only extract claims the quote_span actually supports. No speculation, no synthesis.
- entities: entity_type must be one of {entity_types}; name + attrs from the text only.
- If the document contains nothing relevant, return {{"evidence": [], "entities": []}}.

Document title: {title}
Document text:
{text}
"""

EV_PATTERN = re.compile(r"^EV-(\d+)$")
PILLAR_CODE = {"CYBERSECURITY": "CS", "AI": "AI",
               "ELECTRONIC_WARFARE": "EW", "PROCUREMENT": "PR"}


def _next_evidence_number(sb) -> int:
    """Highest numeric EV-nnn in use.

    The old code used a row count, which collided on any re-run and was thrown
    off by Lane C's non-numeric ids (EV-ATTACK-001, EV-NVD-001).
    """
    rows = sb.table("evidence").select("id").execute().data or []
    numbers = [int(m.group(1)) for m in
               (EV_PATTERN.match(r["id"]) for r in rows) if m]
    return max(numbers) if numbers else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--pillar", required=True)
    ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="extract", status="RUNNING")
    sb = db()

    topics = [t["id"] for t in sb.table("topics").select("id").eq("pillar", a.pillar).execute().data]

    # Only documents from registry rows that cover this pillar. Without this the
    # extractor reads whatever was collected most recently, regardless of pillar.
    registry_ids = [r["id"] for r in sb.table("source_registry").select("id")
                    .contains("pillars", [a.pillar]).execute().data]
    if not registry_ids:
        print("no registry sources for pillar %s" % a.pillar)
        return
    docs = (sb.table("documents").select("id,title,raw_text,registry_id")
              .in_("registry_id", registry_ids)
              .order("retrieved_at", desc=True).limit(a.limit).execute().data)
    print("extracting from %d %s document(s)" % (len(docs), a.pillar))

    n_ev = _next_evidence_number(sb)
    n_ent = (sb.table("entities").select("id", count="exact", head=True)
             .like("id", f"{PILLAR_CODE[a.pillar]}-EXT-%").execute().count or 0)
    for doc in docs:
        prompt = PROMPT.format(
            pillar=a.pillar, topics=topics,
            entity_types=ENTITY_TYPES[a.pillar],
            title=doc["title"], text=(doc["raw_text"] or "")[:30000])
        try:
            # Extraction is mechanical, not analytical — cheap deployment, low effort.
            result = llm.structured(prompt, ExtractionResult, fast=True, effort="low")
        except Exception as exc:
            print(f"REJECTED {doc['title'][:50]}: {type(exc).__name__}: {exc}")
            sb.table("research_gaps").insert({
                "pillar": a.pillar,
                "gap": f"Extraction failed for {doc['title'][:160]}: {exc}"[:500],
                "raised_by": "extract.schema"}).execute()
            continue
        for ev in result.evidence:
            if ev.pillar != a.pillar or ev.topic_id not in topics:
                print(f"  rejected claim (pillar/topic rule): {ev.claim[:60]}")
                continue
            # Deterministic layer check — the prompt asks, the rule enforces.
            layer, changed, why = layers.resolve_env_layer(ev.quote_span, ev.env_layer)
            if changed:
                print(f"  RULE env_layer UAE -> {layer} ({why})")
                ev.env_layer = layer
            n_ev += 1
            ev_id = f"EV-{n_ev:03d}"
            sb.table("evidence").insert({
                "id": ev_id, "claim": ev.claim, "class": "C",          # provisional; rules.py upgrades
                "confidence": "LOW",                                     # provisional; rules.py upgrades
                "env_layer": ev.env_layer, "steep": ev.steep,
                "pillar": ev.pillar, "topic_id": ev.topic_id,
                "question_id": ev.question_id, "quote_span": ev.quote_span}).execute()
            sb.table("evidence_sources").insert(
                {"evidence_id": ev_id, "document_id": doc["id"]}).execute()
            print(f"  + {ev_id}: {ev.claim[:70]}")

        # Entities were extracted and then dropped on the floor before this.
        for ent in result.entities:
            if ent.pillar != a.pillar or ent.entity_type not in ENTITY_TYPES[a.pillar]:
                print(f"  rejected entity (type rule): {ent.entity_type}/{ent.name[:40]}")
                continue
            n_ent += 1
            sb.table("entities").upsert({
                "id": f"{PILLAR_CODE[a.pillar]}-EXT-{n_ent:04d}",
                "pillar": ent.pillar, "entity_type": ent.entity_type,
                "name": ent.name[:300], "attrs": ent.attrs_dict()}).execute()
            print(f"  ~ {ent.entity_type}: {ent.name[:60]}")

    config.update_run(getattr(a, "run_id", None),
                      counts={"extract": _next_evidence_number(sb)})

if __name__ == "__main__":
    main()
