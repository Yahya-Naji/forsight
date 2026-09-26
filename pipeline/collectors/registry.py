"""The verified source registry — SINGLE SOURCE OF TRUTH.

This module is authoritative for three things that must never drift apart:
  1. the rows seeded into `source_registry` (emit with `--emit-sql`),
  2. the domain -> registry_id mapping used by Lane B, and
  3. the tier each publisher carries into rules.py (evidence class depends on it).

26 publisher sources + 1 aggregator (GDELT). Tier follows the FETC deck:
  Tier 1 official/primary · Tier 2 institutional research
  Tier 3 operational/industry intel · Tier 4 exploratory/weak-signal discovery
"""
from __future__ import annotations

CY, AI, EW, PR = "CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"
ALL = [CY, AI, EW, PR]

# id, tier, publisher, url, method, pillars, notes
SOURCES = [
    # ---------------- TIER 1 — official / primary authoritative ----------------
    ("SRC-T1-001", 1, "UAE Cyber Security Council", "https://csc.gov.ae",
     "search", [CY], "National cyber strategy, advisories, CII framework. "
                     "Direct scrape unreachable (TLS handshake fails) — reached "
                     "via site-scoped search."),
    ("SRC-T1-002", 1, "UAE Government Portal (u.ae)", "https://u.ae/en",
     "search", [CY, AI, PR], "National strategies and policy texts"),
    ("SRC-T1-003", 1, "Tawazun Council", "https://www.tawazun.ae",
     "scrape", [PR, CY], "Mandate, programmes, industrial participation news. "
                         "The apex domain fails TLS SNI — the www host is required."),
    ("SRC-T1-004", 1, "US Department of Defense", "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=20",
     "rss", ALL, "DoD newsroom feed — strategies, contracts, releases"),
    ("SRC-T1-005", 1, "NATO NCIA", "https://www.ncia.nato.int",
     "search", [EW, AI, CY], "TIE/LCI experimentation, C-UAS data challenges. "
                             "Scraping blocked site-wide (403) — reached via "
                             "site-scoped search."),
    ("SRC-T1-006", 1, "UK Ministry of Defence", "https://www.gov.uk/government/organisations/ministry-of-defence",
     "search", [EW, PR], "Market engagements, Integrated Procurement Model"),
    ("SRC-T1-007", 1, "NIST CSRC", "https://csrc.nist.gov",
     "search", [CY, AI], "SP 800-207 zero trust, SP 800-161 supply chain, AI RMF"),
    ("SRC-T1-008", 1, "NIST National Vulnerability Database", "https://services.nvd.nist.gov/rest/json/cves/2.0",
     "api", [CY], "LANE C — CVE records load straight to entities"),
    ("SRC-T1-009", 1, "MITRE ATT&CK", "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json",
     "api", [CY], "LANE C — STIX intrusion-sets load straight to entities"),
    ("SRC-T1-010", 1, "UAE TDRA / aeCERT", "https://tdra.gov.ae/en/aecert/alerts",
     "scrape", [CY], "National CERT advisories and incident guidance"),
    ("SRC-T1-011", 1, "UK NCSC", "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml",
     "rss", [CY, AI], "National cyber authority reporting and threat assessments"),

    # ---------------- TIER 2 — international / academic / strategic ------------
    ("SRC-T2-001", 2, "RAND Corporation", "https://www.rand.org",
     "search", [AI, PR, EW], "Methodology and capability analysis"),
    ("SRC-T2-002", 2, "CSIS", "https://www.csis.org",
     "search", [EW, PR], "Drone saturation and salvo-economics series"),
    ("SRC-T2-003", 2, "IISS", "https://www.iiss.org",
     "search", [CY, PR], "Regional balance, military capability assessments"),
    ("SRC-T2-004", 2, "RUSI", "https://www.rusi.org",
     "search", [EW, CY], "EW, drones and lessons-learned analysis"),

    # ---------------- TIER 3 — operational & industry intelligence -------------
    ("SRC-T3-001", 3, "Cisco Talos Intelligence", "https://feeds.feedburner.com/feedburner/Talos",
     "rss", [CY], "Threat research and campaign reporting. Replaced the Google "
                  "TI/Mandiant feed, whose RSS endpoint now returns HTML."),
    ("SRC-T3-002", 3, "Microsoft Security Blog", "https://www.microsoft.com/en-us/security/blog/feed/",
     "rss", [CY, AI], "Nation-state actor tracking and MSTIC reporting"),
    ("SRC-T3-003", 3, "Palo Alto Unit 42", "https://unit42.paloaltonetworks.com/feed/",
     "rss", [CY], "Threat research, Middle East campaign reporting"),

    # ---------------- TIER 4 — exploratory / weak-signal discovery -------------
    ("SRC-T4-001", 4, "Breaking Defense", "https://breakingdefense.com/feed/",
     "rss", ALL, "Discovery layer only — never anchors a finding"),
    ("SRC-T4-002", 4, "Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml",
     "rss", [EW, AI, PR], "Discovery layer only"),
    ("SRC-T4-003", 4, "The Defense Post", "https://thedefensepost.com/feed/",
     "rss", [EW, AI], "Discovery layer only"),
    ("SRC-T4-004", 4, "EDGE Group Newsroom", "https://edgegroup.ae/news",
     "scrape", [PR, EW], "UAE industrial announcements — company primary source"),
    ("SRC-T4-005", 4, "Unmanned Airspace (C-UAS)", "https://www.unmannedairspace.info/category/counter-uas-systems-and-policies/",
     "scrape", [EW, AI], "C-UAS systems and policy trade reporting"),
    ("SRC-T4-006", 4, "C-UAS Hub", "https://cuashub.com",
     "scrape", [EW, AI], "Counter-UAS community and vendor tracking"),
    ("SRC-T4-007", 4, "Reuters Aerospace & Defense", "https://www.reuters.com/business/aerospace-defense/",
     "scrape", [EW, AI, PR], "Discovery layer; public RSS retired, scraped index"),
    ("SRC-T4-008", 4, "Gulf News (UAE)", "https://gulfnews.com/uae",
     "scrape", [CY, PR], "UAE regional reporting — discovery layer"),

    # ---------------- AGGREGATOR — Lane B fallback only ------------------------
    ("SRC-API-001", 4, "GDELT DOC 2.0 (aggregator)", "https://api.gdeltproject.org/api/v2/doc/doc",
     "api", ALL, "LANE B. Tier 4 by construction: an aggregator never confers "
                 "authority. Used as registry_id ONLY when the article's own "
                 "domain matches no registry row."),
]

GDELT_REGISTRY_ID = "SRC-API-001"

# Hosts that belong to a registered publisher but differ from its registry url.
# Without these, Lane B would bounce a known Tier-1 article to the Tier-4
# aggregator fallback and silently downgrade its evidence class.
DOMAIN_ALIASES = {
    "war.gov": "SRC-T1-004",              # DoD newsroom now serves from war.gov
    "defense.gov": "SRC-T1-004",
    "nato.int": "SRC-T1-005",
    "ncsc.gov.uk": "SRC-T1-011",
    "nist.gov": "SRC-T1-007",
    "talosintelligence.com": "SRC-T3-001",
    "blog.talosintelligence.com": "SRC-T3-001",
    "gov.uk": "SRC-T1-006",
}

# Paywalled / subscription-pending — deliberately NOT seeded. See README.
DEFERRED_PAYWALLED = [
    ("Janes", "https://www.janes.com", "Subscription required — pending decision"),
    ("Shephard Media", "https://www.shephardmedia.com", "Subscription required"),
    ("Aviation Week / ShowNews", "https://aviationweek.com", "Trade-show dailies paywalled"),
]


def as_dicts():
    """Registry rows in the same shape Supabase returns, so the collectors can
    run identically against the live table or this static copy (--dry-run)."""
    return [
        {"id": i, "tier": t, "publisher": p, "url": u, "method": m,
         "pillars": pil, "notes": n}
        for (i, t, p, u, m, pil, n) in SOURCES
    ]


def _sql_escape(value):
    return value.replace("'", "''")


def emit_sql():
    """Generate the idempotent seed migration from SOURCES.

    Upsert rather than delete-then-insert: `documents.registry_id` is a foreign
    key, so deleting a row would break provenance on anything already collected.
    """
    head = (
        "-- ============================================================\n"
        "-- 004 SOURCE REGISTRY v2 — the verified collection surface\n"
        "-- GENERATED from pipeline/collectors/registry.py (do not hand-edit).\n"
        "--   regenerate:  python collect.py --emit-sql > "
        "supabase/migrations/004_source_registry_v2.sql\n"
        "-- Idempotent upsert: registry_id is an FK from documents, so rows are\n"
        "-- never deleted — only inserted or corrected in place.\n"
        "-- ============================================================\n\n"
        "insert into source_registry (id, tier, publisher, url, method, pillars, notes) values\n"
    )
    rows = []
    for (i, t, p, u, m, pil, n) in SOURCES:
        pillars = "{" + ",".join(pil) + "}"
        rows.append(
            "('%s',%d,'%s','%s','%s','%s','%s')"
            % (i, t, _sql_escape(p), _sql_escape(u), m, pillars, _sql_escape(n))
        )
    tail = (
        "\non conflict (id) do update set\n"
        "  tier      = excluded.tier,\n"
        "  publisher = excluded.publisher,\n"
        "  url       = excluded.url,\n"
        "  method    = excluded.method,\n"
        "  pillars   = excluded.pillars,\n"
        "  notes     = excluded.notes;\n"
    )
    return head + ",\n".join(rows) + tail
