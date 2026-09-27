-- ============================================================
-- 024 SOURCE REGISTRY v4 — adds GAO, CRS and NATO ACT as Tier 1
-- GENERATED from pipeline/collectors/registry.py (do not hand-edit).
--   regenerate:  python collect.py --emit-sql > supabase/migrations/004_source_registry_v2.sql
-- Idempotent upsert: registry_id is an FK from documents, so rows are
-- never deleted — only inserted or corrected in place.
-- ============================================================

insert into source_registry (id, tier, publisher, url, method, pillars, notes) values
('SRC-T1-001',1,'UAE Cyber Security Council','https://csc.gov.ae','search','{CYBERSECURITY}','National cyber strategy, advisories, CII framework. Direct scrape unreachable (TLS handshake fails) — reached via site-scoped search.'),
('SRC-T1-002',1,'UAE Government Portal (u.ae)','https://u.ae/en','search','{CYBERSECURITY,AI,PROCUREMENT}','National strategies and policy texts'),
('SRC-T1-003',1,'Tawazun Council','https://www.tawazun.ae','scrape','{PROCUREMENT,CYBERSECURITY}','Mandate, programmes, industrial participation news. The apex domain fails TLS SNI — the www host is required.'),
('SRC-T1-004',1,'US Department of Defense','https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=20','rss','{CYBERSECURITY,AI,ELECTRONIC_WARFARE,PROCUREMENT}','DoD newsroom feed — strategies, contracts, releases'),
('SRC-T1-005',1,'NATO NCIA','https://www.ncia.nato.int','search','{ELECTRONIC_WARFARE,AI,CYBERSECURITY}','TIE/LCI experimentation, C-UAS data challenges. Scraping blocked site-wide (403) — reached via site-scoped search.'),
('SRC-T1-006',1,'UK Ministry of Defence','https://www.gov.uk/government/organisations/ministry-of-defence','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Market engagements, Integrated Procurement Model'),
('SRC-T1-007',1,'NIST CSRC','https://csrc.nist.gov','search','{CYBERSECURITY,AI}','SP 800-207 zero trust, SP 800-161 supply chain, AI RMF'),
('SRC-T1-008',1,'NIST National Vulnerability Database','https://services.nvd.nist.gov/rest/json/cves/2.0','api','{CYBERSECURITY}','LANE C — CVE records load straight to entities'),
('SRC-T1-009',1,'MITRE ATT&CK','https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json','api','{CYBERSECURITY}','LANE C — STIX intrusion-sets load straight to entities'),
('SRC-T1-010',1,'UAE TDRA / aeCERT','https://tdra.gov.ae/en/aecert/alerts','scrape','{CYBERSECURITY}','National CERT advisories and incident guidance'),
('SRC-T1-011',1,'UK NCSC','https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml','rss','{CYBERSECURITY,AI}','National cyber authority reporting and threat assessments'),
('SRC-T1-012',1,'CISA (US)','https://www.cisa.gov/cybersecurity-advisories/all.xml','rss','{CYBERSECURITY}','US cyber defence agency advisories, KEV additions and joint guidance'),
('SRC-T1-013',1,'ENISA (EU)','https://www.enisa.europa.eu/media/news-items/RSS','rss','{CYBERSECURITY,AI}','EU cyber agency threat landscape and certification schemes'),
('SRC-T1-014',1,'NSA Cybersecurity (US)','https://www.nsa.gov/Cybersecurity','search','{CYBERSECURITY}','CNSA 2.0 quantum-resistant algorithm suite and NSS guidance'),
('SRC-T1-015',1,'US GAO','https://www.gao.gov','search','{PROCUREMENT,ELECTRONIC_WARFARE,AI}','Independent audit of defence acquisition, counter-UAS programmes and modular open systems'),
('SRC-T1-016',1,'Congressional Research Service','https://crsreports.congress.gov','search','{PROCUREMENT,ELECTRONIC_WARFARE}','Legislative and authority analysis on counter-UAS'),
('SRC-T1-017',1,'NATO Allied Command Transformation','https://www.act.nato.int','search','{ELECTRONIC_WARFARE,AI}','Layered counter-UAS experimentation campaign'),
('SRC-T2-001',2,'RAND Corporation','https://www.rand.org','search','{AI,PROCUREMENT,ELECTRONIC_WARFARE}','Methodology and capability analysis'),
('SRC-T2-002',2,'CSIS','https://www.csis.org','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Drone saturation and salvo-economics series'),
('SRC-T2-003',2,'IISS','https://www.iiss.org','search','{CYBERSECURITY,PROCUREMENT}','Regional balance, military capability assessments'),
('SRC-T2-004',2,'RUSI','https://www.rusi.org','search','{ELECTRONIC_WARFARE,CYBERSECURITY}','EW, drones and lessons-learned analysis'),
('SRC-T3-001',3,'Cisco Talos Intelligence','https://feeds.feedburner.com/feedburner/Talos','rss','{CYBERSECURITY}','Threat research and campaign reporting. Replaced the Google TI/Mandiant feed, whose RSS endpoint now returns HTML.'),
('SRC-T3-002',3,'Microsoft Security Blog','https://www.microsoft.com/en-us/security/blog/feed/','rss','{CYBERSECURITY,AI}','Nation-state actor tracking and MSTIC reporting'),
('SRC-T3-003',3,'Palo Alto Unit 42','https://unit42.paloaltonetworks.com/feed/','rss','{CYBERSECURITY}','Threat research, Middle East campaign reporting'),
('SRC-T4-001',4,'Breaking Defense','https://breakingdefense.com/feed/','rss','{CYBERSECURITY,AI,ELECTRONIC_WARFARE,PROCUREMENT}','Discovery layer only — never anchors a finding'),
('SRC-T4-002',4,'Defense News','https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml','rss','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','Discovery layer only'),
('SRC-T4-003',4,'The Defense Post','https://thedefensepost.com/feed/','rss','{ELECTRONIC_WARFARE,AI}','Discovery layer only'),
('SRC-T4-004',4,'EDGE Group Newsroom','https://edgegroup.ae/news','scrape','{PROCUREMENT,ELECTRONIC_WARFARE}','UAE industrial announcements — company primary source'),
('SRC-T4-005',4,'Unmanned Airspace (C-UAS)','https://www.unmannedairspace.info/category/counter-uas-systems-and-policies/','scrape','{ELECTRONIC_WARFARE,AI}','C-UAS systems and policy trade reporting'),
('SRC-T4-006',4,'C-UAS Hub','https://cuashub.com','scrape','{ELECTRONIC_WARFARE,AI}','Counter-UAS community and vendor tracking'),
('SRC-T4-007',4,'Reuters Aerospace & Defense','https://www.reuters.com/business/aerospace-defense/','scrape','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','Discovery layer; public RSS retired, scraped index'),
('SRC-T4-008',4,'Gulf News (UAE)','https://gulfnews.com/uae','scrape','{CYBERSECURITY,PROCUREMENT}','UAE regional reporting — discovery layer'),
('SRC-API-001',4,'GDELT DOC 2.0 (aggregator)','https://api.gdeltproject.org/api/v2/doc/doc','api','{CYBERSECURITY,AI,ELECTRONIC_WARFARE,PROCUREMENT}','LANE B. Tier 4 by construction: an aggregator never confers authority. Used as registry_id ONLY when the article''s own domain matches no registry row.')
on conflict (id) do update set
  tier      = excluded.tier,
  publisher = excluded.publisher,
  url       = excluded.url,
  method    = excluded.method,
  pillars   = excluded.pillars,
  notes     = excluded.notes;

