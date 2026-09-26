"""LANE C — structured APIs. These records are already typed, so they bypass
LLM extraction entirely and load straight into `entities`.

The provenance chain still has to hold: each loader also writes one document
row (pointing at the dataset) and one evidence row linked to it, so every
entity remains traceable to a Tier-1 source exactly like an extracted claim.

  python collect.py --lane c --loader attack
  python collect.py --lane c --loader nvd
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from typing import List, Optional

import httpx

from . import HEADERS, RateLimiter, TIMEOUT, log, warn

ATTACK_URL = ("https://raw.githubusercontent.com/mitre-attack/attack-stix-data/"
              "master/enterprise-attack/enterprise-attack.json")
ATTACK_REGISTRY_ID = "SRC-T1-009"

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_REGISTRY_ID = "SRC-T1-008"
NVD_KEYWORDS = ["command and control", "UAV", "GNSS", "SCADA"]

# Public NVD rate limit without an API key: 5 requests / 30s. 6s spacing is safe.
_nvd_limit = RateLimiter(6.0)

REGIONAL_TERMS = [
    "middle east", "gulf", "uae", "united arab emirates", "emirat",
    "saudi", "qatar", "kuwait", "bahrain", "oman", "yemen", "iran",
    "iraq", "israel", "jordan", "lebanon", "syria", "turkey", "egypt",
]


# --------------------------------------------------------------------------
# provenance — keeps Lane C inside the same evidence chain as Lanes A and B
# --------------------------------------------------------------------------
def _write_provenance(sb, registry_id, dataset_url, dataset_title, evidence_id,
                      claim, quote_span, topic_id, dry_run=False):
    """One document + one evidence row so structured records stay traceable."""
    if dry_run:
        log("  [dry-run] provenance %s -> %s" % (evidence_id, dataset_url))
        return evidence_id

    sb.table("documents").upsert(
        {"registry_id": registry_id, "url": dataset_url, "title": dataset_title,
         "raw_text": claim}, on_conflict="url").execute()
    doc = sb.table("documents").select("id").eq("url", dataset_url).execute().data
    if not doc:
        warn("provenance document missing after upsert: %s" % dataset_url)
        return None

    sb.table("evidence").upsert({
        "id": evidence_id,
        "claim": claim[:500],
        "class": "A",                      # rules.py recomputes from tier; Tier 1 -> A
        "confidence": "HIGH",
        "env_layer": "GLOBAL",
        "steep": ["Technological", "Political"],
        "pillar": "CYBERSECURITY",
        "topic_id": topic_id,
        "quote_span": quote_span[:400],
    }).execute()
    sb.table("evidence_sources").upsert(
        {"evidence_id": evidence_id, "document_id": doc[0]["id"]}).execute()
    log("  provenance: %s -> %s" % (evidence_id, dataset_url))
    return evidence_id


def _upsert_entity(sb, entity, evidence_id, dry_run=False):
    if dry_run:
        log("  [dry-run] entity %-22s %s" % (entity["id"], entity["name"][:46]))
        return
    sb.table("entities").upsert(entity).execute()
    if evidence_id:
        sb.table("entity_evidence").upsert(
            {"entity_id": entity["id"], "evidence_id": evidence_id}).execute()


# --------------------------------------------------------------------------
# (a) MITRE ATT&CK — STIX intrusion-sets
# --------------------------------------------------------------------------
def _attack_id(obj) -> Optional[str]:
    for ref in obj.get("external_references", []) or []:
        if ref.get("source_name") == "mitre-attack" and ref.get("external_id"):
            return ref["external_id"]
    return None


def _download_stix(url: str) -> str:
    """Stream the ~54 MB bundle to a temp file — never hold it twice in memory."""
    handle = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    total = 0
    with httpx.stream("GET", url, headers=HEADERS, timeout=120,
                      follow_redirects=True) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_bytes(chunk_size=1 << 20):
            handle.write(chunk)
            total += len(chunk)
    handle.close()
    log("  downloaded %.1f MB of STIX data" % (total / 1048576.0))
    return handle.name


def load_attack(sb, limit=None, dry_run=False) -> int:
    log("LANE C · MITRE ATT&CK enterprise STIX")
    path = _download_stix(ATTACK_URL)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    groups = [o for o in bundle.get("objects", [])
              if o.get("type") == "intrusion-set"
              and not o.get("revoked")
              and not o.get("x_mitre_deprecated")]
    log("  %d active intrusion-sets in bundle" % len(groups))

    regional = []
    for group in groups:
        haystack = (group.get("description", "") or "").lower()
        matched = [t for t in REGIONAL_TERMS if t in haystack]
        if matched:
            regional.append((group, matched))
    log("  %d reference Middle East / Gulf targeting" % len(regional))

    if limit:
        regional = regional[:limit]

    claim = ("MITRE ATT&CK lists %d active intrusion sets, of which %d reference "
             "Middle East, Gulf or UAE targeting in their threat descriptions."
             % (len(groups), len(regional)))
    quote = "; ".join(g.get("name", "?") for g, _ in regional[:12]) or "no regional matches"
    evidence_id = _write_provenance(
        sb, ATTACK_REGISTRY_ID, ATTACK_URL, "MITRE ATT&CK Enterprise (STIX)",
        "EV-ATTACK-001", claim, quote, "CS-T05", dry_run)

    count = 0
    for group, matched in regional:
        attack_id = _attack_id(group)
        if not attack_id:
            continue
        _upsert_entity(sb, {
            "id": "CS-THREAT-%s" % attack_id,
            "pillar": "CYBERSECURITY",
            "entity_type": "threat_actor",
            "name": group.get("name", attack_id),
            "attrs": {
                "attack_id": attack_id,
                "aliases": group.get("aliases", []) or [],
                "description": (group.get("description", "") or "")[:2000],
                "matched_terms": matched,
                "source": "mitre-attack/enterprise-attack",
            },
        }, evidence_id, dry_run)
        count += 1

    log("LANE C complete — %d threat_actor entities" % count)
    return count


# --------------------------------------------------------------------------
# (b) NVD — CVE records
# --------------------------------------------------------------------------
def _cvss(cve) -> Optional[float]:
    metrics = cve.get("metrics", {}) or {}
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key) or []
        if entries:
            data = entries[0].get("cvssData", {}) or {}
            if data.get("baseScore") is not None:
                return data["baseScore"]
    return None


def _description(cve) -> str:
    for desc in cve.get("descriptions", []) or []:
        if desc.get("lang") == "en":
            return desc.get("value", "")
    return ""


def load_nvd(sb, keywords=None, limit=10, days=120, dry_run=False) -> int:
    """Recent CVEs for the given keywords.

    NVD orders results oldest-first, so an unbounded keywordSearch returns
    1999-era records. A publication window (NVD caps it at 120 days) keeps the
    result set current, which is the only thing horizon scanning cares about.
    """
    keywords = keywords or NVD_KEYWORDS
    days = min(days, 120)                      # NVD rejects windows over 120 days
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=days)
    window = {"pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
              "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000")}
    log("LANE C · NVD CVE records · keywords=%s · last %d days" % (keywords, days))

    collected = []
    for keyword in keywords:
        _nvd_limit.wait()                      # public limit: no key -> space requests
        params = {"keywordSearch": keyword, "resultsPerPage": str(limit)}
        params.update(window)
        try:
            resp = httpx.get(NVD_URL, headers=HEADERS, timeout=TIMEOUT, params=params)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            warn("NVD '%s': %s" % (keyword, exc))
            continue

        vulns = payload.get("vulnerabilities", []) or []
        log("  '%s' -> %d of %s total" % (keyword, len(vulns),
                                          payload.get("totalResults", "?")))
        for item in vulns:
            cve = item.get("cve", {}) or {}
            if cve.get("id"):
                collected.append((keyword, cve))

    unique = {}
    for keyword, cve in collected:
        unique.setdefault(cve["id"], (keyword, cve))

    claim = ("NVD returns %d distinct CVE records across control-system and "
             "navigation keywords (%s) relevant to connected defence "
             "architectures." % (len(unique), ", ".join(keywords)))
    quote = ", ".join(sorted(unique.keys())[:20]) or "no records"
    evidence_id = _write_provenance(
        sb, NVD_REGISTRY_ID, NVD_URL, "NIST National Vulnerability Database (CVE 2.0 API)",
        "EV-NVD-001", claim, quote, "CS-T02", dry_run)

    count = 0
    for cve_id, (keyword, cve) in sorted(unique.items()):
        _upsert_entity(sb, {
            "id": "CS-%s" % cve_id,
            "pillar": "CYBERSECURITY",
            "entity_type": "cyber_threat",
            "name": cve_id,
            "attrs": {
                "cve_id": cve_id,
                "cvss": _cvss(cve),
                "description": _description(cve)[:2000],
                "published": cve.get("published"),
                "matched_keyword": keyword,
            },
        }, evidence_id, dry_run)
        count += 1

    log("LANE C complete — %d cyber_threat entities" % count)
    return count


def run(sb, loader, limit=None, days=120, dry_run=False) -> int:
    if loader == "attack":
        return load_attack(sb, limit=limit, dry_run=dry_run)
    if loader == "nvd":
        return load_nvd(sb, limit=limit or 10, days=days, dry_run=dry_run)
    raise SystemExit("unknown loader %r (expected 'attack' or 'nvd')" % loader)
