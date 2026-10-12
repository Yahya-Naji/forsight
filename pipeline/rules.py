"""STEP 4 — Rules engine (SYMBOLIC layer).

Assigns evidence class, confidence and signal strength BY RULE, raises and
clears validation gates, and scores risks. The LLM never sets these values.

INDEPENDENCE IS THE CENTRAL IDEA HERE. Four claims pulled from one newspaper
article are one source, not four. Counting evidence rows instead of distinct
publishers let a single Tier-4 story present itself as STRONG corroboration —
so every rule below counts DISTINCT PUBLISHERS, and falls back to distinct
documents only to break ties within a publisher.

Each rule is a pure decision function (classify, signal_strength,
forced_direction, uae_gate_satisfied) wrapped by a function that reads and
writes the database, so the rules themselves are tested without one
(tests/test_rules.py).

Usage: python rules.py              # apply
       python rules.py --dry-run    # print what would change, write nothing
"""
import argparse
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import config
import labels
import layers
from config import db

UAE_GATE_MIN_ROWS = 2        # Class A/B UAE-layer rows required to clear the gate
UAE_GATE_MIN_PUBS = 2        # ...from at least this many independent publishers


# --------------------------------------------------------------------------
# provenance primitives
# --------------------------------------------------------------------------
def _registry_tiers(sb) -> Dict[str, int]:
    return {r["id"]: r["tier"] for r in
            sb.table("source_registry").select("id,tier").execute().data}


# evidence id -> [(document id, publisher registry id)]
Sources = Dict[str, List[Tuple[str, Optional[str]]]]


def _all(build) -> List[dict]:
    """Every row of a query, past PostgREST's 1000-row page."""
    out, start = [], 0
    while True:
        page = build().range(start, start + 999).execute().data
        out += page
        if len(page) < 1000:
            return out
        start += 1000


def load_sources(sb) -> Tuple[Sources, Set[str]]:
    """All provenance in two queries, instead of one query per row and signal.

    Returns the evidence -> (document, publisher) map and the set of live
    (unarchived) evidence ids.
    """
    live = {r["id"] for r in _all(lambda: sb.table("evidence").select("id")
                                  .is_("archived_at", "null"))}
    sources: Sources = defaultdict(list)
    for r in _all(lambda: sb.table("evidence_sources")
                  .select("evidence_id,document_id,documents(registry_id)")):
        sources[r["evidence_id"]].append(
            (r["document_id"], (r.get("documents") or {}).get("registry_id")))
    return sources, live


def provenance(evidence_ids: List[str], sources: Sources, tiers: Dict[str, int],
               live: Optional[Set[str]] = None) -> Tuple[set, set, List[int]]:
    """Return (distinct document ids, distinct publisher registry ids, tiers).

    This is the only place corroboration is measured. Everything downstream
    consumes these sets rather than counting rows. When `live` is given,
    archived evidence contributes nothing: a source we have retired must not
    keep a signal strong.
    """
    docs, pubs, tier_list = set(), set(), []
    for ev in evidence_ids:
        if live is not None and ev not in live:
            continue
        for doc, reg in sources.get(ev, []):
            docs.add(doc)
            if reg:
                pubs.add(reg)
                if reg in tiers:
                    tier_list.append(tiers[reg])
    return docs, pubs, tier_list


# --------------------------------------------------------------------------
# environment layer
# --------------------------------------------------------------------------
def env_layer_check(sb, dry_run=False):
    """RULE env_layer: a row is UAE-layer only if its quote names the UAE.

    Runs before classification because the UAE gate reads this field — a
    mislabelled row could otherwise clear a gate it has no business clearing.
    """
    fixed = 0
    for ev in (sb.table("evidence").select("id,env_layer,quote_span")
               .is_("archived_at", "null").eq("env_layer", "UAE").execute().data):
        layer, changed, why = layers.resolve_env_layer(ev.get("quote_span"), "UAE")
        if changed:
            if not dry_run:
                sb.table("evidence").update({"env_layer": layer}).eq("id", ev["id"]).execute()
            print(f"RULE env_layer    {ev['id']} -> {layer} ({why})")
            fixed += 1
    if fixed:
        print(f"RULE env_layer    downgraded {fixed} mislabelled row(s)")
    return fixed


# --------------------------------------------------------------------------
# evidence class
# --------------------------------------------------------------------------
def classify(tier_list: List[int], n_publishers: int) -> Tuple[str, str]:
    """RULE class_check:
       Tier-1 publisher                  -> Class A, HIGH
       >=2 INDEPENDENT PUBLISHERS        -> Class B, MEDIUM_HIGH
       single Tier 2-3 publisher         -> Class C, MEDIUM
       single Tier 4 publisher           -> Class C, LOW (weak-signal hold)

    Class B previously triggered on >=2 evidence_sources rows, which two
    documents from the same outlet could satisfy. It now requires two
    genuinely different publishers.
    """
    if 1 in tier_list:
        return "A", "HIGH"
    if n_publishers >= 2:
        return "B", "MEDIUM_HIGH"
    if tier_list and min(tier_list) <= 3:
        return "C", "MEDIUM"
    return "C", "LOW"


def classify_evidence(sb, tiers, sources: Sources, dry_run=False) -> Dict[str, str]:
    """Apply class_check to every live row; return {evidence id: class} as
    computed this run, so the UAE gate reads the same classes even in a dry run.
    Archived rows are out of the graph; reclassifying them changes nothing
    anyone reads and costs a write per row per run."""
    changed, computed = 0, {}
    for ev in _all(lambda: sb.table("evidence").select("id,class,confidence")
                   .is_("archived_at", "null")):
        docs, pubs, tl = provenance([ev["id"]], sources, tiers)
        cls, conf = classify(tl, len(pubs))
        computed[ev["id"]] = cls
        if (cls, conf) == (ev.get("class"), ev.get("confidence")):
            continue
        changed += 1
        if not dry_run:
            sb.table("evidence").update({"class": cls, "confidence": conf}).eq("id", ev["id"]).execute()
        print(f"RULE class_check  {ev['id']} {ev.get('class')}/{ev.get('confidence')} -> "
              f"Class {cls} / {conf}  "
              f"(publishers={len(pubs)}, docs={len(docs)}, tiers={sorted(set(tl))})")
    print(f"RULE class_check  {changed} row(s) {'would change' if dry_run else 'changed'}")
    return computed


# --------------------------------------------------------------------------
# signal strength
# --------------------------------------------------------------------------
def signal_strength(n_publishers: int, has_t1: bool) -> str:
    """RULE corroboration — measured in independent publishers.

       >=3 independent publishers            -> STRONG
       >=2 independent publishers incl. T1   -> STRONG_EMERGING
        2 independent publishers             -> EMERGING
        1 publisher                          -> WEAK
    """
    if n_publishers >= 3:
        return "STRONG"
    if n_publishers >= 2 and has_t1:
        return "STRONG_EMERGING"
    if n_publishers == 2:
        return "EMERGING"
    return "WEAK"


def forced_direction(n_publishers: int, tier_list: List[int]):
    """A lone Tier-4 source can carry a signal, but not a direction: one
    outlet's framing is not a trend. Returns the forced direction, or None."""
    if n_publishers <= 1 and tier_list and min(tier_list) >= 4:
        return "UNCERTAIN"
    return None


def score_signals(sb, tiers, sources: Sources, live: Set[str], dry_run=False):
    evidence_of = defaultdict(list)
    for r in _all(lambda: sb.table("signal_evidence").select("signal_id,evidence_id")):
        evidence_of[r["signal_id"]].append(r["evidence_id"])
    changed = 0
    for sig in _all(lambda: sb.table("signals").select("id,strength,direction")):
        evs = evidence_of.get(sig["id"], [])
        docs, pubs, tl = provenance(evs, sources, tiers, live)
        strength = signal_strength(len(pubs), 1 in tl)

        update = {"strength": strength}
        note = ""
        forced = forced_direction(len(pubs), tl)
        if forced:
            update["direction"] = forced
            note = "  [single Tier-4 publisher -> direction forced UNCERTAIN]"
        if all(sig.get(k) == v for k, v in update.items()):
            continue
        changed += 1
        if not dry_run:
            sb.table("signals").update(update).eq("id", sig["id"]).execute()

        print(f"RULE corroboration {sig['id']} {sig.get('strength')} -> {strength} "
              f"({len(evs)} rows / {len(docs)} docs / {len(pubs)} publishers, "
              f"tiers={sorted(set(tl))}){note}")
    print(f"RULE corroboration {changed} signal(s) {'would change' if dry_run else 'changed'}")


# --------------------------------------------------------------------------
# UAE inference guard
# --------------------------------------------------------------------------
def uae_gate_satisfied(n_rows: int, n_publishers: int) -> bool:
    """RULE uae_inference: a UAE-specific conclusion needs UAE-specific evidence.

    Clearing the gate requires >=2 Class A/B rows at the UAE layer from >=2
    INDEPENDENT PUBLISHERS. A single row — however well sourced — is a data
    point, not a basis for a national capability claim.
    """
    return n_rows >= UAE_GATE_MIN_ROWS and n_publishers >= UAE_GATE_MIN_PUBS


def uae_inference_guard(sb, tiers, sources: Sources, classes: Dict[str, str], dry_run=False):
    uae_rows = _all(lambda: sb.table("evidence").select("id,pillar")
                    .is_("archived_at", "null").eq("env_layer", "UAE"))
    for pillar in ["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"]:
        ids = [r["id"] for r in uae_rows
               if r["pillar"] == pillar and classes.get(r["id"]) in ("A", "B")]
        _, pubs, _ = provenance(ids, sources, tiers)
        satisfied = uae_gate_satisfied(len(ids), len(pubs))

        gate_id = f"VG-{pillar[:2]}-01"
        existing = (sb.table("validation_gates").select("id,status")
                    .eq("id", gate_id).execute().data)

        if dry_run:
            now = existing[0]["status"] if existing else "absent"
            print(f"RULE uae_inference {pillar} -> {gate_id} {now} -> "
                  f"{'PASSED' if satisfied else 'OPEN'} "
                  f"({len(ids)} UAE Class A/B row(s) from {len(pubs)} publisher(s))")
            continue

        if not satisfied:
            sb.table("validation_gates").upsert({
                "id": gate_id, "gate": "CUSTOMER_VALIDATION", "status": "OPEN",
                # Reader-facing text: never the raw enum. The console renders
                # this string verbatim, so the label belongs in the data.
                "blocks": ("Any UAE-specific capability-gap claim for the "
                           f"{labels.PILLAR.get(pillar, pillar)} pillar"),
                "raised_by": "uae_inference_guard"}).execute()
            print(f"RULE uae_inference {pillar} -> {gate_id} OPEN "
                  f"({len(ids)} UAE Class A/B row(s) from {len(pubs)} publisher(s); "
                  f"need {UAE_GATE_MIN_ROWS} rows / {UAE_GATE_MIN_PUBS} publishers)")
        elif existing and existing[0]["status"] == "OPEN":
            sb.table("validation_gates").update({"status": "PASSED"}).eq("id", gate_id).execute()
            print(f"RULE uae_inference {pillar} -> {gate_id} PASSED "
                  f"({len(ids)} rows from {len(pubs)} independent publishers)")


def check_indicators(sb, dry_run=False):
    """RULE trigger: threshold = signal at STRONG_EMERGING+ backed by >1 publisher."""
    for ind in sb.table("indicators").select("*").eq("status", "WATCHING").execute().data:
        linked = (sb.table("links").select("to_id").eq("from_id", ind["id"])
                  .eq("rel", "monitors").execute().data)
        for l in linked:
            sig = sb.table("signals").select("strength").eq("id", l["to_id"]).execute().data
            if sig and sig[0]["strength"] in ("STRONG_EMERGING", "STRONG"):
                if not dry_run:
                    sb.table("indicators").update({"status": "THRESHOLD_MET"}).eq("id", ind["id"]).execute()
                print(f"TRIGGER {ind['id']} -> THRESHOLD_MET")
                break


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Symbolic rules engine")
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute every rule against live data and print what would change; write nothing")
    a = ap.parse_args()
    if a.dry_run:
        a.run_id = None   # a dry run is not a pipeline run
    config.update_run(a.run_id, stage="rules", status="RUNNING")

    sb = db()
    tiers = _registry_tiers(sb)
    env_layer_check(sb, a.dry_run)
    sources, live = load_sources(sb)
    classes = classify_evidence(sb, tiers, sources, a.dry_run)
    score_signals(sb, tiers, sources, live, a.dry_run)
    uae_inference_guard(sb, tiers, sources, classes, a.dry_run)
    check_indicators(sb, a.dry_run)

    config.update_run(a.run_id, counts={
        "rules": sb.table("evidence").select("id", count="exact", head=True).execute().count or 0})


# --------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------
# Kinds that carry information a reader can check. A photograph of a server
# room, or a publisher's logo, adds the visual authority of the source while
# carrying none of its content — which is the same failure as citing a Tier-1
# publisher for a claim it never made. The model proposes the kind; this rule
# decides whether the figure may appear in a brief.
INFORMATIVE_KINDS = {"CHART", "DIAGRAM", "MAP", "TABLE_IMAGE", "TIMELINE", "SCREENSHOT"}

# Words publishers use when they are describing artwork. A hero image whose alt
# text reads "Digital illustration of Europe map highlighting network
# connections" was classified MAP on the strength of the word "map", and it is
# decoration. When the publisher says the image is a representation, take them
# at their word.
ARTWORK = re.compile(
    r"\b(illustration|illustrative|graphic of|pictorial|conceptual|abstract|"
    r"stock (photo|image)|symbol|symbolic|artwork|artist|rendering|render of|"
    r"depict(?:ed|ion) as|glowing|silhouette|decorative|banner|hero image|"
    r"representation of a|imagery)\b", re.I)

# A caption numbered by the publisher is the strongest signal that the image is
# part of the argument: "Figure 3. Industry distribution of targeted
# enterprises" is a claim the reader can check against the plot.
NUMBERED_CAPTION = re.compile(r"^\s*(fig(?:ure)?|table|chart|exhibit)\s*\.?\s*\d+", re.I)

MIN_ALT_FOR_INTENT = 40


def figure_is_informative(kind: str, caption: str = "", alt: str = "") -> tuple:
    """(admit, reason). The model proposes `kind`; this decides admission.

    Kind alone was not enough. Every genuine figure collected in the first run
    carried a publisher's numbered caption, and every false positive was a hero
    illustration with no caption whose alt text described artwork. So admission
    needs evidence of editorial intent as well as a plausible kind — otherwise
    a stock image of a map is cited as a map.
    """
    kind = (kind or "").upper()
    caption, alt = (caption or "").strip(), (alt or "").strip()

    if kind not in INFORMATIVE_KINDS:
        return False, "kind %s is decoration, not information" % (kind or "UNKNOWN")
    if ARTWORK.search(caption) or ARTWORK.search(alt):
        return False, "described as artwork by the publisher"
    if NUMBERED_CAPTION.match(caption):
        return True, "publisher numbered it as a figure"
    if caption:
        return True, "carries a publisher caption"
    if len(alt) >= MIN_ALT_FOR_INTENT:
        return True, "substantive alt text, no caption"
    return False, ("no caption and only %d chars of alt text — cannot tell what "
                   "it shows" % len(alt))
