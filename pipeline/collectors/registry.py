"""The verified source registry — SINGLE SOURCE OF TRUTH.

This module is authoritative for three things that must never drift apart:
  1. the rows seeded into `source_registry` (emit with `--emit-sql`),
  2. the domain -> registry_id mapping used by Lane B, and
  3. the tier each publisher carries into rules.py (evidence class depends on it).

Publisher sources + 1 aggregator (GDELT); see ARCHIVED for rows no longer collected. Tier follows the FETC deck:
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

    ("SRC-T1-012", 1, "CISA (US)", "https://www.cisa.gov/cybersecurity-advisories/all.xml",
     "rss", [CY], "US cyber defence agency advisories, KEV additions and joint guidance"),
    ("SRC-T1-013", 1, "ENISA (EU)", "https://www.enisa.europa.eu/media/news-items/RSS",
     "rss", [CY, AI], "EU cyber agency threat landscape and certification schemes"),
    ("SRC-T1-014", 1, "NSA Cybersecurity (US)", "https://www.nsa.gov/Cybersecurity",
     "search", [CY], "CNSA 2.0 quantum-resistant algorithm suite and NSS guidance"),
    ("SRC-T1-015", 1, "US GAO", "https://www.gao.gov",
     "search", [PR, EW, AI], "Independent audit of defence acquisition, counter-UAS "
     "programmes and modular open systems"),
    ("SRC-T1-016", 1, "Congressional Research Service", "https://crsreports.congress.gov",
     "search", [PR, EW], "Legislative and authority analysis on counter-UAS"),
    ("SRC-T1-017", 1, "NATO Allied Command Transformation", "https://www.act.nato.int",
     "search", [EW, AI], "Layered counter-UAS experimentation campaign"),

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
    ("SRC-T4-001", 4, "Breaking Defense", "https://breakingdefense.com/tag/electronic-warfare/feed/",
     "rss", ALL, "Electronic-warfare tag feed (was the whole-site feed, which was "
                 "mostly off-scope once EW became the core pillar). Discovery layer only."),
    ("SRC-T4-002", 4, "Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml",
     "rss", [EW, AI, PR], "Discovery layer only"),
    ("SRC-T4-003", 4, "The Defense Post", "https://thedefensepost.com/feed/",
     "rss", [EW, AI], "Discovery layer only"),
    ("SRC-T4-004", 4, "EDGE Group Newsroom", "https://edgegroup.ae/news",
     "scrape", [PR, EW], "UAE industrial announcements — company primary source"),
    ("SRC-T4-005", 4, "Unmanned Airspace (C-UAS)", "https://www.unmannedairspace.info/category/counter-uas-systems-and-policies/feed/",
     "rss", [EW, AI, PR], "C-UAS systems and policy trade reporting. The category's "
                          "own feed replaced the scraped index page."),
    ("SRC-T4-006", 4, "C-UAS Hub", "https://cuashub.com",
     "scrape", [EW, AI], "Counter-UAS community and vendor tracking"),
    ("SRC-T4-007", 4, "Reuters Aerospace & Defense", "https://www.reuters.com/business/aerospace-defense/",
     "scrape", [EW, AI, PR], "Discovery layer; public RSS retired, scraped index"),
    ("SRC-T4-008", 4, "Gulf News (UAE)", "https://gulfnews.com/uae",
     "scrape", [CY, PR], "UAE regional reporting — discovery layer"),


    # ---------------- EW-core feeds (026) --------------------------------------
    # Topic feeds rather than whole-site feeds: tested 2026-10-07, most items in
    # each are EW, spectrum or counter-UAS. Same publisher on several rows is
    # deliberate — one row per feed, one tier per publisher.
    ("SRC-T2-005", 2, "Mitchell Institute for Aerospace Studies", "https://www.mitchellaerospacepower.org/tag/electronic-warfare/feed/",
     "rss", [EW, PR], "EW policy papers and force-design analysis"),
    ("SRC-T4-009", 4, "Breaking Defense", "https://breakingdefense.com/tag/counter-drone/feed/",
     "rss", [EW, AI, PR], "Counter-drone tag feed"),
    ("SRC-T4-010", 4, "Breaking Defense", "https://breakingdefense.com/tag/counter-uas/feed/",
     "rss", [EW, PR], "Counter-UAS tag feed — programmes, directed energy, contracts"),
    ("SRC-T4-011", 4, "DefenseScoop", "https://defensescoop.com/tag/electronic-warfare/feed/",
     "rss", [EW, CY, AI], "Electronic-warfare tag feed"),
    ("SRC-T4-012", 4, "DefenseScoop", "https://defensescoop.com/tag/counter-uas/feed/",
     "rss", [EW, AI, PR], "Counter-UAS tag feed"),
    ("SRC-T4-013", 4, "DefenseScoop", "https://defensescoop.com/tag/electromagnetic-spectrum/feed/",
     "rss", [EW, CY, PR], "Electromagnetic-spectrum tag feed"),
    ("SRC-T4-014", 4, "Inside GNSS", "https://insidegnss.com/tag/jamming/feed/",
     "rss", [EW, CY], "GNSS jamming — engineering and policy trade press"),
    ("SRC-T4-015", 4, "Inside GNSS", "https://insidegnss.com/tag/spoofing/feed/",
     "rss", [EW, CY], "GNSS spoofing — engineering and policy trade press"),
    ("SRC-T4-016", 4, "Naval News", "https://www.navalnews.com/tag/electronic-warfare/feed/",
     "rss", [EW], "Naval EW, jammers and decoys"),
    ("SRC-T4-017", 4, "Air & Space Forces Magazine", "https://www.airandspaceforces.com/tag/electronic-warfare/feed/",
     "rss", [EW, PR], "Air Force EW, SEAD and programme reporting"),
    ("SRC-T4-018", 4, "C4ISRNET", "https://www.c4isrnet.com/arc/outboundfeeds/rss/?outputType=xml",
     "rss", [EW, AI, CY], "C4ISR, EW and autonomy — about half of items in scope"),
    ("SRC-T4-019", 4, "The War Zone", "https://www.twz.com/feed",
     "rss", [EW, AI], "Drone threat evolution, EW in Ukraine and the Middle East"),
    ("SRC-T4-020", 4, "Militarnyi", "https://mil.in.ua/en/news/feed/",
     "rss", [EW, AI], "Ukrainian reporting on drone and EW combat use"),
    ("SRC-T4-021", 4, "The National (UAE)", "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml",
     "rss", [EW, CY, PR], "UAE-based reporting — Gulf drone, missile and GNSS incidents"),
    ("SRC-T4-022", 4, "Defense Mirror", "https://www.defensemirror.com/rss",
     "rss", [EW, PR], "Radar, EW and air-defence contract news"),

    # ---------------- EW document publishers (026) ----------------------------
    # Reached document by document (`collect.py --lane a --url ...`, list in
    # docs/ew-document-seed.txt), not swept. Registered so each document keeps
    # its publisher's tier instead of falling to the aggregator.
    ("SRC-T1-018", 1, "EASA", "https://www.easa.europa.eu",
     "search", [EW], "Safety Information Bulletins and action plans on GNSS interference"),
    ("SRC-T1-019", 1, "EUROCONTROL", "https://www.eurocontrol.int",
     "search", [EW], "GNSS radio-frequency interference monitoring and workshops"),
    ("SRC-T1-020", 1, "ICAO", "https://www.icao.int",
     "search", [EW], "Middle East regional (MID) working papers on GNSS interference, "
                     "including UAE submissions. Cloudflare: needs the stealth fetch."),
    ("SRC-T1-021", 1, "UK Civil Aviation Authority", "https://www.caa.co.uk",
     "search", [EW], "Safety notices on GNSS interference"),
    ("SRC-T1-022", 1, "European Defence Agency", "https://eda.europa.eu",
     "search", [EW, PR], "Counter-UAS and EW capability development"),
    ("SRC-T2-006", 2, "NATO JAPCC", "https://www.japcc.org",
     "search", [EW, CY], "Air power EW, SEAD and CEMA analysis"),
    ("SRC-T2-007", 2, "CNAS", "https://www.cnas.org",
     "search", [EW, AI], "Drone warfare and counter-UAS analysis"),
    ("SRC-T3-004", 3, "IATA", "https://www.iata.org",
     "search", [EW], "Airline-industry reporting on GNSS jamming and spoofing"),
    ("SRC-T4-023", 4, "Khaleej Times", "https://www.khaleejtimes.com",
     "search", [EW, PR], "UAE-based reporting on Gulf air defence and EDGE"),

    # ---------------- AGGREGATOR — Lane B fallback only ------------------------
    ("SRC-API-001", 4, "GDELT DOC 2.0 (aggregator)", "https://api.gdeltproject.org/api/v2/doc/doc",
     "api", ALL, "LANE B. Tier 4 by construction: an aggregator never confers "
                 "authority. Used as registry_id ONLY when the article's own "
                 "domain matches no registry row."),
]

GDELT_REGISTRY_ID = "SRC-API-001"

# Out of scope since EW became the core pillar (026). Archived rows stay in the
# registry so documents already collected keep their publisher and tier, and so
# Lane B still maps their domains correctly; they are simply never collected.
ARCHIVED = {
    "SRC-T1-001": "Generic national cyber policy; no EW coverage (and unreachable).",
    "SRC-T1-007": "Cyber standards (zero trust, PQC); no EW coverage.",
    "SRC-T1-009": "Enterprise IT intrusion sets; no EW coverage.",
    "SRC-T1-010": "IT vulnerability alerts; no EW coverage.",
    "SRC-T1-011": "General cyber reporting; no EW coverage.",
    "SRC-T1-012": "IT advisories; no EW coverage.",
    "SRC-T1-013": "EU cyber policy; no EW coverage.",
    "SRC-T1-014": "Cryptography guidance; no EW coverage.",
    "SRC-T3-001": "IT threat research; no EW coverage.",
    "SRC-T3-002": "IT threat research; no EW coverage.",
    "SRC-T3-003": "IT threat research; no EW coverage.",
    "SRC-T4-002": "Whole-site feed, mostly off-scope; C4ISRNET (same newsroom) carries its EW coverage.",
    "SRC-T4-003": "Whole-site feed, mostly off-scope; no topic feed available.",
    "SRC-T4-007": "Scraped index never yielded a document.",
    "SRC-T4-008": "General UAE news; The National's feed covers Gulf security better.",
}

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
    # A publisher missing from the registry does not merely go unlabelled: it
    # falls back to the GDELT aggregator id and is scored Tier 4, so a CISA
    # advisory was being classed as weakly as a news aggregator repost. Tier
    # decides evidence class downstream, which makes an absent mapping a
    # correctness bug rather than a cosmetic one.
    "cisa.gov": "SRC-T1-012",
    # GAO landed as Tier 4 for want of a registry row, exactly as CISA had.
    # Tier decides evidence class, so an absent mapping silently downgrades an
    # audit authority to the standing of a news aggregator.
    "gao.gov": "SRC-T1-015",
    "files.gao.gov": "SRC-T1-015",
    "crsreports.congress.gov": "SRC-T1-016",
    "act.nato.int": "SRC-T1-017",
    "ac.nato.int": "SRC-T1-005",
    "ncia.nato.int": "SRC-T1-005",
    "enisa.europa.eu": "SRC-T1-013",
    "nsa.gov": "SRC-T1-014",
    # 026: mirrors and asset hosts of registered publishers
    "everycrsreport.com": "SRC-T1-016",        # verbatim CRS mirror; crsreports blocks scripts
    "ad.easa.europa.eu": "SRC-T1-018",
    "assets.publishing.service.gov.uk": "SRC-T1-006",
    "csrc.nist.gov": "SRC-T1-007",
    "nvlpubs.nist.gov": "SRC-T1-007",
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
         "pillars": pil, "notes": n,
         "archived_at": "static" if i in ARCHIVED else None}
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
        "-- SOURCE REGISTRY — the verified collection surface\n"
        "-- GENERATED from pipeline/collectors/registry.py (do not hand-edit).\n"
        "--   regenerate:  python pipeline/collect.py --emit-sql > "
        "supabase/migrations/<next>_registry_<name>.sql\n"
        "-- Idempotent upsert: registry_id is an FK from documents, so rows are\n"
        "-- never deleted — only inserted, corrected in place, or archived.\n"
        "-- ============================================================\n\n"
        "alter table source_registry add column if not exists archived_at timestamptz;\n"
        "alter table source_registry add column if not exists archived_reason text;\n\n"
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
    # Archive state follows ARCHIVED both ways, so removing an id revives it.
    archive = ["\n-- archived: kept for provenance and domain mapping, never collected"]
    for i, reason in sorted(ARCHIVED.items()):
        archive.append(
            "update source_registry set archived_at = coalesce(archived_at, now()), "
            "archived_reason = '%s' where id = '%s';" % (_sql_escape(reason), i))
    live = ",".join("'%s'" % i for (i, *_rest) in SOURCES if i not in ARCHIVED)
    archive.append("update source_registry set archived_at = null, archived_reason = null "
                   "where id in (%s);" % live)
    return head + ",\n".join(rows) + tail + "\n".join(archive) + "\n"
