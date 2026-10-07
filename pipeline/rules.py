"""STEP 4 — Rules engine (SYMBOLIC layer).

Assigns evidence class, confidence and signal strength BY RULE, raises and
clears validation gates, and scores risks. The LLM never sets these values.

INDEPENDENCE IS THE CENTRAL IDEA HERE. Four claims pulled from one newspaper
article are one source, not four. Counting evidence rows instead of distinct
publishers let a single Tier-4 story present itself as STRONG corroboration —
so every rule below counts DISTINCT PUBLISHERS, and falls back to distinct
documents only to break ties within a publisher.

Usage: python rules.py
"""
import argparse
import re
from typing import Dict, List, Tuple

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


def provenance(sb, evidence_ids: List[str], tiers: Dict[str, int]) -> Tuple[set, set, List[int]]:
    """Return (distinct document ids, distinct publisher registry ids, tiers).

    This is the only place corroboration is measured. Everything downstream
    consumes these sets rather than counting rows.
    """
    if not evidence_ids:
        return set(), set(), []
    rows = (sb.table("evidence_sources")
            .select("document_id,evidence_id,documents(registry_id)")
            .in_("evidence_id", evidence_ids).execute().data)
    docs, pubs, tier_list = set(), set(), []
    for r in rows:
        docs.add(r["document_id"])
        reg = (r.get("documents") or {}).get("registry_id")
        if reg:
            pubs.add(reg)
            if reg in tiers:
                tier_list.append(tiers[reg])
    return docs, pubs, tier_list


# --------------------------------------------------------------------------
# environment layer
# --------------------------------------------------------------------------
def env_layer_check(sb):
    """RULE env_layer: a row is UAE-layer only if its quote names the UAE.

    Runs before classification because the UAE gate reads this field — a
    mislabelled row could otherwise clear a gate it has no business clearing.
    """
    fixed = 0
    for ev in (sb.table("evidence").select("id,env_layer,quote_span")
               .eq("env_layer", "UAE").execute().data):
        layer, changed, why = layers.resolve_env_layer(ev.get("quote_span"), "UAE")
        if changed:
            sb.table("evidence").update({"env_layer": layer}).eq("id", ev["id"]).execute()
            print(f"RULE env_layer    {ev['id']} -> {layer} ({why})")
            fixed += 1
    if fixed:
        print(f"RULE env_layer    downgraded {fixed} mislabelled row(s)")
    return fixed


# --------------------------------------------------------------------------
# evidence class
# --------------------------------------------------------------------------
def classify_evidence(sb, tiers=None):
    """RULE class_check:
       Tier-1 publisher                  -> Class A, HIGH
       >=2 INDEPENDENT PUBLISHERS        -> Class B, MEDIUM_HIGH
       single Tier 2-3 publisher         -> Class C, MEDIUM
       single Tier 4 publisher           -> Class C, LOW (weak-signal hold)

    Class B previously triggered on >=2 evidence_sources rows, which two
    documents from the same outlet could satisfy. It now requires two
    genuinely different publishers.
    """
    tiers = tiers or _registry_tiers(sb)
    for ev in sb.table("evidence").select("id").execute().data:
        docs, pubs, tl = provenance(sb, [ev["id"]], tiers)
        if 1 in tl:
            cls, conf = "A", "HIGH"
        elif len(pubs) >= 2:
            cls, conf = "B", "MEDIUM_HIGH"
        elif tl and min(tl) <= 3:
            cls, conf = "C", "MEDIUM"
        else:
            cls, conf = "C", "LOW"
        sb.table("evidence").update({"class": cls, "confidence": conf}).eq("id", ev["id"]).execute()
        print(f"RULE class_check  {ev['id']} -> Class {cls} / {conf}  "
              f"(publishers={len(pubs)}, docs={len(docs)}, tiers={sorted(set(tl))})")


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


def score_signals(sb, tiers=None):
    tiers = tiers or _registry_tiers(sb)
    for sig in sb.table("signals").select("id,direction").execute().data:
        evs = [r["evidence_id"] for r in sb.table("signal_evidence")
               .select("evidence_id").eq("signal_id", sig["id"]).execute().data]
        docs, pubs, tl = provenance(sb, evs, tiers)
        strength = signal_strength(len(pubs), 1 in tl)

        update = {"strength": strength}
        # A lone Tier-4 source can carry a signal, but not a direction: one
        # outlet's framing is not a trend.
        note = ""
        if len(pubs) <= 1 and tl and min(tl) >= 4:
            update["direction"] = "UNCERTAIN"
            note = "  [single Tier-4 publisher -> direction forced UNCERTAIN]"
        sb.table("signals").update(update).eq("id", sig["id"]).execute()

        print(f"RULE corroboration {sig['id']} -> {strength} "
              f"({len(evs)} rows / {len(docs)} docs / {len(pubs)} publishers, "
              f"tiers={sorted(set(tl))}){note}")


# --------------------------------------------------------------------------
# UAE inference guard
# --------------------------------------------------------------------------
def uae_inference_guard(sb, tiers=None):
    """RULE uae_inference: a UAE-specific conclusion needs UAE-specific evidence.

    Clearing the gate requires >=2 Class A/B rows at the UAE layer from >=2
    INDEPENDENT PUBLISHERS. A single row — however well sourced — is a data
    point, not a basis for a national capability claim.
    """
    tiers = tiers or _registry_tiers(sb)
    for pillar in ["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"]:
        uae = (sb.table("evidence").select("id").eq("pillar", pillar)
               .is_("archived_at", "null").eq("env_layer", "UAE").in_("class", ["A", "B"]).execute().data)
        ids = [r["id"] for r in uae]
        _, pubs, _ = provenance(sb, ids, tiers)
        satisfied = len(ids) >= UAE_GATE_MIN_ROWS and len(pubs) >= UAE_GATE_MIN_PUBS

        gate_id = f"VG-{pillar[:2]}-01"
        existing = (sb.table("validation_gates").select("id,status")
                    .eq("id", gate_id).execute().data)

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


def check_indicators(sb):
    """RULE trigger: threshold = signal at STRONG_EMERGING+ backed by >1 publisher."""
    for ind in sb.table("indicators").select("*").eq("status", "WATCHING").execute().data:
        linked = (sb.table("links").select("to_id").eq("from_id", ind["id"])
                  .eq("rel", "monitors").execute().data)
        for l in linked:
            sig = sb.table("signals").select("strength").eq("id", l["to_id"]).execute().data
            if sig and sig[0]["strength"] in ("STRONG_EMERGING", "STRONG"):
                sb.table("indicators").update({"status": "THRESHOLD_MET"}).eq("id", ind["id"]).execute()
                print(f"TRIGGER {ind['id']} -> THRESHOLD_MET")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Symbolic rules engine")
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    a = ap.parse_args()
    config.update_run(a.run_id, stage="rules", status="RUNNING")

    sb = db()
    tiers = _registry_tiers(sb)
    env_layer_check(sb)
    classify_evidence(sb, tiers)
    score_signals(sb, tiers)
    uae_inference_guard(sb, tiers)
    check_indicators(sb)

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
