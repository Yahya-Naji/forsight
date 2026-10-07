-- ============================================================
-- SOURCE REGISTRY — the verified collection surface
-- GENERATED from pipeline/collectors/registry.py (do not hand-edit).
--   regenerate:  python pipeline/collect.py --emit-sql > supabase/migrations/030_registry_uae_layer.sql
-- Idempotent upsert: registry_id is an FK from documents, so rows are
-- never deleted — only inserted, corrected in place, or archived.
-- ============================================================

alter table source_registry add column if not exists archived_at timestamptz;
alter table source_registry add column if not exists archived_reason text;

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
('SRC-T4-001',4,'Breaking Defense','https://breakingdefense.com/tag/electronic-warfare/feed/','rss','{CYBERSECURITY,AI,ELECTRONIC_WARFARE,PROCUREMENT}','Electronic-warfare tag feed (was the whole-site feed, which was mostly off-scope once EW became the core pillar). Discovery layer only.'),
('SRC-T4-002',4,'Defense News','https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml','rss','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','Discovery layer only'),
('SRC-T4-003',4,'The Defense Post','https://thedefensepost.com/feed/','rss','{ELECTRONIC_WARFARE,AI}','Discovery layer only'),
('SRC-T4-004',4,'EDGE Group Newsroom','https://edgegroup.ae/news','scrape','{PROCUREMENT,ELECTRONIC_WARFARE}','UAE industrial announcements — company primary source'),
('SRC-T4-005',4,'Unmanned Airspace (C-UAS)','https://www.unmannedairspace.info/category/counter-uas-systems-and-policies/feed/','rss','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','C-UAS systems and policy trade reporting. The category''s own feed replaced the scraped index page.'),
('SRC-T4-006',4,'C-UAS Hub','https://cuashub.com','scrape','{ELECTRONIC_WARFARE,AI}','Counter-UAS community and vendor tracking'),
('SRC-T4-007',4,'Reuters Aerospace & Defense','https://www.reuters.com/business/aerospace-defense/','scrape','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','Discovery layer; public RSS retired, scraped index'),
('SRC-T4-008',4,'Gulf News (UAE)','https://gulfnews.com/uae','scrape','{CYBERSECURITY,PROCUREMENT}','UAE regional reporting — discovery layer'),
('SRC-T2-005',2,'Mitchell Institute for Aerospace Studies','https://www.mitchellaerospacepower.org/tag/electronic-warfare/feed/','rss','{ELECTRONIC_WARFARE,PROCUREMENT}','EW policy papers and force-design analysis'),
('SRC-T4-009',4,'Breaking Defense','https://breakingdefense.com/tag/counter-drone/feed/','rss','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','Counter-drone tag feed'),
('SRC-T4-010',4,'Breaking Defense','https://breakingdefense.com/tag/counter-uas/feed/','rss','{ELECTRONIC_WARFARE,PROCUREMENT}','Counter-UAS tag feed — programmes, directed energy, contracts'),
('SRC-T4-011',4,'DefenseScoop','https://defensescoop.com/tag/electronic-warfare/feed/','rss','{ELECTRONIC_WARFARE,CYBERSECURITY,AI}','Electronic-warfare tag feed'),
('SRC-T4-012',4,'DefenseScoop','https://defensescoop.com/tag/counter-uas/feed/','rss','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','Counter-UAS tag feed'),
('SRC-T4-013',4,'DefenseScoop','https://defensescoop.com/tag/electromagnetic-spectrum/feed/','rss','{ELECTRONIC_WARFARE,CYBERSECURITY,PROCUREMENT}','Electromagnetic-spectrum tag feed'),
('SRC-T4-014',4,'Inside GNSS','https://insidegnss.com/tag/jamming/feed/','rss','{ELECTRONIC_WARFARE,CYBERSECURITY}','GNSS jamming — engineering and policy trade press'),
('SRC-T4-015',4,'Inside GNSS','https://insidegnss.com/tag/spoofing/feed/','rss','{ELECTRONIC_WARFARE,CYBERSECURITY}','GNSS spoofing — engineering and policy trade press'),
('SRC-T4-016',4,'Naval News','https://www.navalnews.com/tag/electronic-warfare/feed/','rss','{ELECTRONIC_WARFARE}','Naval EW, jammers and decoys'),
('SRC-T4-017',4,'Air & Space Forces Magazine','https://www.airandspaceforces.com/tag/electronic-warfare/feed/','rss','{ELECTRONIC_WARFARE,PROCUREMENT}','Air Force EW, SEAD and programme reporting'),
('SRC-T4-018',4,'C4ISRNET','https://www.c4isrnet.com/arc/outboundfeeds/rss/?outputType=xml','rss','{ELECTRONIC_WARFARE,AI,CYBERSECURITY}','C4ISR, EW and autonomy — about half of items in scope'),
('SRC-T4-019',4,'The War Zone','https://www.twz.com/feed','rss','{ELECTRONIC_WARFARE,AI}','Drone threat evolution, EW in Ukraine and the Middle East'),
('SRC-T4-020',4,'Militarnyi','https://mil.in.ua/en/news/feed/','rss','{ELECTRONIC_WARFARE,AI}','Ukrainian reporting on drone and EW combat use'),
('SRC-T4-021',4,'The National (UAE)','https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml','rss','{ELECTRONIC_WARFARE,CYBERSECURITY,PROCUREMENT}','UAE-based reporting — Gulf drone, missile and GNSS incidents'),
('SRC-T4-022',4,'Defense Mirror','https://www.defensemirror.com/rss','rss','{ELECTRONIC_WARFARE,PROCUREMENT}','Radar, EW and air-defence contract news'),
('SRC-T1-018',1,'EASA','https://www.easa.europa.eu','search','{ELECTRONIC_WARFARE}','Safety Information Bulletins and action plans on GNSS interference'),
('SRC-T1-019',1,'EUROCONTROL','https://www.eurocontrol.int','search','{ELECTRONIC_WARFARE}','GNSS radio-frequency interference monitoring and workshops'),
('SRC-T1-020',1,'ICAO','https://www.icao.int','search','{ELECTRONIC_WARFARE}','Middle East regional (MID) working papers on GNSS interference, including UAE submissions. Cloudflare: needs the stealth fetch.'),
('SRC-T1-021',1,'UK Civil Aviation Authority','https://www.caa.co.uk','search','{ELECTRONIC_WARFARE}','Safety notices on GNSS interference'),
('SRC-T1-022',1,'European Defence Agency','https://eda.europa.eu','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Counter-UAS and EW capability development'),
('SRC-T2-006',2,'NATO JAPCC','https://www.japcc.org','search','{ELECTRONIC_WARFARE,CYBERSECURITY}','Air power EW, SEAD and CEMA analysis'),
('SRC-T2-007',2,'CNAS','https://www.cnas.org','search','{ELECTRONIC_WARFARE,AI}','Drone warfare and counter-UAS analysis'),
('SRC-T3-004',3,'IATA','https://www.iata.org','search','{ELECTRONIC_WARFARE}','Airline-industry reporting on GNSS jamming and spoofing'),
('SRC-T4-023',4,'Khaleej Times','https://www.khaleejtimes.com','search','{ELECTRONIC_WARFARE,PROCUREMENT}','UAE-based reporting on Gulf air defence and EDGE'),
('SRC-T2-008',2,'The Washington Institute','https://www.washingtoninstitute.org','search','{ELECTRONIC_WARFARE}','Gulf security analysis, incl. Houthi strikes on the UAE'),
('SRC-T2-009',2,'Indian Council of World Affairs','https://icwa.in','search','{ELECTRONIC_WARFARE}','Foreign-policy council; Houthi drone attacks on the UAE'),
('SRC-T2-010',2,'Gulf International Forum','https://gulfif.org','search','{ELECTRONIC_WARFARE,PROCUREMENT,AI}','Gulf policy analysis — UAE defence industry and EDGE'),
('SRC-T2-011',2,'ORF Middle East','https://orfme.org','search','{ELECTRONIC_WARFARE,PROCUREMENT,AI}','UAE defence-technology priorities'),
('SRC-T3-005',3,'RICS','https://www.rics.org','search','{ELECTRONIC_WARFARE}','Professional body; geospatial group on GNSS spoofing in the Gulf'),
('SRC-T4-024',4,'Oman Observer','https://www.omanobserver.om','search','{ELECTRONIC_WARFARE}','Gulf reporting (AFP) on GNSS disruption in the UAE'),
('SRC-T4-025',4,'European Security & Defence','https://euro-sd.com','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Defence-show reporting on EDGE C-UAS'),
('SRC-T4-026',4,'Raksha Anirveda','https://raksha-anirveda.com','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Defence news; UAE MoD anti-jamming contracts'),
('SRC-T4-027',4,'Defence Industry Europe','https://defence-industry.eu','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Defence-industry news; EDGE EW systems'),
('SRC-T4-028',4,'Army Recognition','https://www.armyrecognition.com','search','{ELECTRONIC_WARFARE,PROCUREMENT,AI}','Defence-show reporting; UMEX counter-drone systems'),
('SRC-T4-029',4,'SatellitePro ME','https://satelliteprome.com','search','{ELECTRONIC_WARFARE}','UAE spectrum regulation (TDRA)'),
('SRC-T4-030',4,'Military Times','https://www.militarytimes.com','search','{ELECTRONIC_WARFARE}','US reporting on Houthi drone attacks near Al Dhafra'),
('SRC-T4-031',4,'Ynet News','https://www.ynetnews.com','search','{ELECTRONIC_WARFARE,PROCUREMENT}','UAE air-defence procurement after the 2022 strikes'),
('SRC-T4-032',4,'Kuwait Times','https://kuwaittimes.com','search','{ELECTRONIC_WARFARE}','Gulf reporting (AFP) on the Houthi drone threat to the UAE'),
('SRC-API-001',4,'GDELT DOC 2.0 (aggregator)','https://api.gdeltproject.org/api/v2/doc/doc','api','{CYBERSECURITY,AI,ELECTRONIC_WARFARE,PROCUREMENT}','LANE B. Tier 4 by construction: an aggregator never confers authority. Used as registry_id ONLY when the article''s own domain matches no registry row.')
on conflict (id) do update set
  tier      = excluded.tier,
  publisher = excluded.publisher,
  url       = excluded.url,
  method    = excluded.method,
  pillars   = excluded.pillars,
  notes     = excluded.notes;

-- archived: kept for provenance and domain mapping, never collected
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'Generic national cyber policy; no EW coverage (and unreachable).' where id = 'SRC-T1-001';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'Cyber standards (zero trust, PQC); no EW coverage.' where id = 'SRC-T1-007';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'Enterprise IT intrusion sets; no EW coverage.' where id = 'SRC-T1-009';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'IT vulnerability alerts; no EW coverage.' where id = 'SRC-T1-010';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'General cyber reporting; no EW coverage.' where id = 'SRC-T1-011';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'IT advisories; no EW coverage.' where id = 'SRC-T1-012';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'EU cyber policy; no EW coverage.' where id = 'SRC-T1-013';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'Cryptography guidance; no EW coverage.' where id = 'SRC-T1-014';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'IT threat research; no EW coverage.' where id = 'SRC-T3-001';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'IT threat research; no EW coverage.' where id = 'SRC-T3-002';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'IT threat research; no EW coverage.' where id = 'SRC-T3-003';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'Whole-site feed, mostly off-scope; C4ISRNET (same newsroom) carries its EW coverage.' where id = 'SRC-T4-002';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'Whole-site feed, mostly off-scope; no topic feed available.' where id = 'SRC-T4-003';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'Scraped index never yielded a document.' where id = 'SRC-T4-007';
update source_registry set archived_at = coalesce(archived_at, now()), archived_reason = 'General UAE news; The National''s feed covers Gulf security better.' where id = 'SRC-T4-008';
update source_registry set archived_at = null, archived_reason = null where id in ('SRC-T1-002','SRC-T1-003','SRC-T1-004','SRC-T1-005','SRC-T1-006','SRC-T1-008','SRC-T1-015','SRC-T1-016','SRC-T1-017','SRC-T2-001','SRC-T2-002','SRC-T2-003','SRC-T2-004','SRC-T4-001','SRC-T4-004','SRC-T4-005','SRC-T4-006','SRC-T2-005','SRC-T4-009','SRC-T4-010','SRC-T4-011','SRC-T4-012','SRC-T4-013','SRC-T4-014','SRC-T4-015','SRC-T4-016','SRC-T4-017','SRC-T4-018','SRC-T4-019','SRC-T4-020','SRC-T4-021','SRC-T4-022','SRC-T1-018','SRC-T1-019','SRC-T1-020','SRC-T1-021','SRC-T1-022','SRC-T2-006','SRC-T2-007','SRC-T3-004','SRC-T4-023','SRC-T2-008','SRC-T2-009','SRC-T2-010','SRC-T2-011','SRC-T3-005','SRC-T4-024','SRC-T4-025','SRC-T4-026','SRC-T4-027','SRC-T4-028','SRC-T4-029','SRC-T4-030','SRC-T4-031','SRC-T4-032','SRC-API-001');

