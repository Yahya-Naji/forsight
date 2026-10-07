"""STEP 3 — Extractor (NEURAL layer): reads stored documents and emits
EvidenceCandidate/EntityCandidate JSON validated against models.py.
Anything that fails validation is rejected into the research-gap log.
Usage: python extract.py --pillar CYBERSECURITY [--limit 5]"""
import argparse, json, re
import layers
import llm
import config
from config import db
from postgrest.exceptions import APIError
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
  pillar (must be {pillar}), topic_id (one of the topics below),
  quote_span (VERBATIM words copied from the document, 10-400 chars),
  ew_hook (VERBATIM words from inside quote_span that tie the claim to the
  topic's EW functions: a jammer, a drone, a radar, GNSS, a waveform, the
  spectrum, a counter-UAS system... A country, company, "AI", "cyber" or
  "defence" on its own is not a hook).
- Electronic Warfare is the core of this system. Every topic below exists for
  its effect on EW. Extract a claim ONLY if it bears on a topic's EW functions
  and you can give its ew_hook. Generic IT security, general AI news, budgets
  and politics with no EW content are not extracted, however interesting.
{lens_rule}
- Do NOT assign confidence or evidence class - that is not your job.
- Only extract claims the quote_span actually supports. No speculation, no synthesis.
- Extract EVERY distinct claim that passes the EW test — figures, dates,
  capabilities, programmes, observed effects, stated plans. A substantive report
  section usually yields 5-15; a short news item 2-5. One claim per document is
  almost always too few.
- entities: entity_type must be one of {entity_types}; name + attrs from the text only.
- If the document contains nothing relevant, return {{"evidence": [], "entities": []}}.

Topics (id [EW functions] name — EW impact):
{topics}

Document title: {title}
Document text:
{text}
"""

EV_PATTERN = re.compile(r"^EV-(\d+)$")
CHUNK = 30000

# A lens run sees only its own topics, so without this it files general EW
# claims (a new drone's range) under whichever lens topic is nearest.
_LENS = ("- This run extracts the {angle} angle on EW ONLY: the claim itself must be "
         "about {what}. A claim about EW, drones or air defence in general, with no "
         "{angle} element, is NOT extracted here — the Electronic Warfare run takes it.")
LENS_RULE = {
    "CYBERSECURITY": _LENS.format(angle="cyber", what="cyber intrusion, protocols, "
                                  "software, firmware, data integrity or supply-chain integrity"),
    "AI": _LENS.format(angle="AI", what="machine learning, autonomy, AI classification "
                       "or decision support, or the assurance of AI"),
    "PROCUREMENT": _LENS.format(angle="acquisition", what="contracts, programmes, "
                                "budgets for EW or counter-UAS, rights, export controls, "
                                "sovereignty, industry or testing for acceptance"),
}


def _norm(text: str) -> str:
    text = (text or "").lower()
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u00a0", " ")):
        text = text.replace(a, b)
    return " ".join(text.split()).strip(" .,;:'\"")


def _letters(text: str) -> str:
    # Letters and digits only: PDF text breaks words across lines ("elec- tronic",
    # "counter- UAS"), which defeats an exact match on a quote that is verbatim.
    return re.sub(r"[^a-z0-9]", "", _norm(text))


def _within(part: str, whole: str) -> bool:
    return len(_letters(part)) >= 3 and _letters(part) in _letters(whole)
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


def _insert_evidence(sb, n_ev: int, row: dict) -> "tuple[int, str]":
    """Insert under the next free EV-nnn; returns (number, id).

    Pillar jobs run in parallel (analyse.yml, the console's Run button), so
    another job can take the number between our read and our insert. On a
    duplicate key, re-read the highest number in use and try the next one.
    """
    for _ in range(8):
        n_ev += 1
        ev_id = f"EV-{n_ev:03d}"
        try:
            sb.table("evidence").insert({"id": ev_id, **row}).execute()
            return n_ev, ev_id
        except APIError as e:
            if getattr(e, "code", None) != "23505":
                raise
            n_ev = _next_evidence_number(sb)
    raise RuntimeError("could not claim a free evidence id after 8 attempts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--pillar", required=True)
    ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="extract", status="RUNNING")
    sb = db()

    topic_rows = (sb.table("topics").select("id,name,description,ew_functions,ew_impact")
                  .eq("pillar", a.pillar).is_("retired_at", "null").order("id").execute().data)
    topics = [t["id"] for t in topic_rows]
    # Names and EW links, not bare ids: given only "AI-T05" the model filed
    # drone-range claims under the UAE AI ecosystem.
    topic_text = "\n".join(
        "%s [%s] %s — %s" % (t["id"], ", ".join(t["ew_functions"]), t["name"],
                             t.get("ew_impact") or t.get("description") or "")
        for t in topic_rows)

    # Only documents from registry rows that cover this pillar. Without this the
    # extractor reads whatever was collected most recently, regardless of pillar.
    registry_ids = [r["id"] for r in sb.table("source_registry").select("id")
                    .contains("pillars", [a.pillar]).is_("archived_at", "null")
                    .execute().data]
    if not registry_ids:
        print("no registry sources for pillar %s" % a.pillar)
        return
    # Unread for this pillar only: extracted_pillars records every pillar that
    # has read a document, so a re-run moves on instead of duplicating evidence.
    docs = (sb.table("documents").select("id,title,raw_text,registry_id,extracted_pillars")
              .in_("registry_id", registry_ids)
              .not_.contains("extracted_pillars", [a.pillar])
              .order("retrieved_at", desc=True).limit(a.limit).execute().data)
    print("extracting from %d %s document(s)" % (len(docs), a.pillar))

    n_ev = _next_evidence_number(sb)
    n_ent = (sb.table("entities").select("id", count="exact", head=True)
             .like("id", f"{PILLAR_CODE[a.pillar]}-EXT-%").execute().count or 0)
    for doc in docs:
        raw = doc["raw_text"] or ""
        result = ExtractionResult()
        failed = False
        # Long reports are read in chunks rather than cut at the first 30k chars.
        for start in range(0, max(len(raw), 1), CHUNK):
            prompt = PROMPT.format(
                pillar=a.pillar, topics=topic_text, lens_rule=LENS_RULE.get(a.pillar, ""),
                entity_types=ENTITY_TYPES[a.pillar],
                title=doc["title"], text=raw[start:start + CHUNK])
            try:
                # Cheap deployment, but medium effort: at low effort it returned one
                # claim per document and paraphrased the EW hook it had to copy.
                part = llm.structured(prompt, ExtractionResult, fast=True, effort="medium")
            except Exception as exc:
                print(f"REJECTED {doc['title'][:50]}: {type(exc).__name__}: {exc}")
                sb.table("research_gaps").insert({
                    "pillar": a.pillar,
                    "gap": f"Extraction failed for {doc['title'][:160]}: {exc}"[:500],
                    "raised_by": "extract.schema"}).execute()
                failed = True
                break
            result.evidence += part.evidence
            result.entities += part.entities
        if failed:
            continue
        for ev in result.evidence:
            if ev.pillar != a.pillar or ev.topic_id not in topics:
                print(f"  rejected claim (pillar/topic rule): {ev.claim[:60]}")
                continue
            # The quote must really be in the document, and the EW hook really in
            # the quote. A claim that cannot point at its EW words is a stretch.
            if not _within(ev.quote_span, raw):
                print(f"  rejected claim (quote not in document): {ev.claim[:60]}")
                continue
            if not _within(ev.ew_hook, ev.quote_span):
                print(f"  rejected claim (no EW hook in quote, hook={ev.ew_hook[:30]!r}): {ev.claim[:50]}")
                continue
            # Deterministic layer check — the prompt asks, the rule enforces.
            layer, changed, why = layers.resolve_env_layer(ev.quote_span, ev.env_layer)
            if changed:
                print(f"  RULE env_layer UAE -> {layer} ({why})")
                ev.env_layer = layer
            n_ev, ev_id = _insert_evidence(sb, n_ev, {
                "claim": ev.claim, "class": "C",                         # provisional; rules.py upgrades
                "confidence": "LOW",                                     # provisional; rules.py upgrades
                "env_layer": ev.env_layer, "steep": ev.steep,
                "pillar": ev.pillar, "topic_id": ev.topic_id,
                "question_id": ev.question_id, "quote_span": ev.quote_span})
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

        # Marked read only once its evidence is stored, so a crash mid-document
        # leaves it unread and the next run picks it up again.
        sb.table("documents").update(
            {"extracted_pillars": sorted(set((doc.get("extracted_pillars") or []) + [a.pillar]))}
        ).eq("id", doc["id"]).execute()

    config.update_run(getattr(a, "run_id", None),
                      counts={"extract": _next_evidence_number(sb)})

if __name__ == "__main__":
    main()
