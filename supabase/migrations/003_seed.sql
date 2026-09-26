-- ============================================================
-- 003 SEED — pillar topics (from the deck, UAE-scoped),
-- source registry (what to search/scrape), sample question bank,
-- and the report template.
-- ============================================================

-- ---------- TOPICS PER PILLAR ----------
insert into topics (id, pillar, name, description, uae_relevance) values
-- CYBERSECURITY (cyber as mission assurance for defence, not generic infosec)
('CS-T01','CYBERSECURITY','National CII & defence cyber posture','UAE Cyber Security Council strategy, CII framework, information-assurance standards','Defines the national baseline any defence-cyber finding must align with'),
('CS-T02','CYBERSECURITY','Connected defence-system attack surface','C2, sensor feeds, APIs, AI models, update channels as targets','Layered C-UAS and IAMD architectures are software-defined and connected'),
('CS-T03','CYBERSECURITY','Supply-chain & supplier dependency risk','Firmware, third-party software, remote support, cloud, export exposure','Foreign-sourced defence components create sovereignty and availability risk'),
('CS-T04','CYBERSECURITY','Mission assurance & zero-trust standards','Segmentation, identity, signed updates, logging, degraded-mode ops','What Tawazun should encode into acquisition gates'),
('CS-T05','CYBERSECURITY','Regional threat landscape','State/proxy actors and campaigns targeting Gulf government & CNI','UAE/Regional layer evidence for likelihood scoring'),
('CS-T06','CYBERSECURITY','Cyber-EW convergence','Combined cyber + electromagnetic attack on the engagement chain','Scenario 5 (BLACK FLAG) class events'),
-- AI
('AI-T01','AI','Defensive AI: fusion & decision support','Multi-sensor fusion, classification, prioritisation, operator workload','NATO data challenge shows fusion is the bottleneck'),
('AI-T02','AI','Hostile autonomy','Autonomous navigation, one-to-many control, terminal guidance, swarms','Compresses UAE decision windows; weakens RF assumptions'),
('AI-T03','AI','AI assurance / TEVV','Adversarial robustness, calibration, provenance, lifecycle revalidation','Evidence gates before operational use'),
('AI-T04','AI','Human control boundaries','What AI may recommend vs automate vs never decide','MoD must define; Tawazun encodes into contracts'),
('AI-T05','AI','UAE AI ecosystem & compute sovereignty','National AI strategy, local models/datasets/compute, EDGE & academia','Local capability for Level 4-5 sovereignty'),
-- ELECTRONIC WARFARE
('EW-T01','ELECTRONIC_WARFARE','Link-independent threats','Fibre-optic control, low-emission, autonomous continuation','Reduces coverage of RF-based soft-kill'),
('EW-T02','ELECTRONIC_WARFARE','GNSS denial & alternative PNT','Jamming/spoofing resilience, visual/inertial navigation','Changes value of GNSS-denial defeat layer'),
('EW-T03','ELECTRONIC_WARFARE','Cognitive/adaptive EW','ML-assisted emitter recognition, threat-library agility','Reprogramming speed as readiness'),
('EW-T04','ELECTRONIC_WARFARE','Spectrum congestion & fratricide','Deconfliction, friendly-system interference, contested spectrum','Gulf spectrum environment specifics'),
('EW-T05','ELECTRONIC_WARFARE','Emerging defeat effects','HPM, directed energy, interceptor drones — one-to-many economics','Saturation economics for UAE defence'),
-- PROCUREMENT
('PR-T01','PROCUREMENT','Acquisition velocity & modularity','Spiral/framework/marketplace mechanisms, open interfaces','High-change layers outpace conventional cycles'),
('PR-T02','PROCUREMENT','Sovereignty by function','5-level control model per capability function','Tawazun make/buy/integrate decisions'),
('PR-T03','PROCUREMENT','Contract rights & lock-in','API/data/source/update rights, exit clauses','Lock-in migrating from hardware to software'),
('PR-T04','PROCUREMENT','Export controls & supply access','Licensing risk, diversification, strategic stock','Availability under crisis'),
('PR-T05','PROCUREMENT','Localisation & industrial capability','Real capability outputs vs local content','EDGE ecosystem, co-development, tech transfer');

-- ---------- SOURCE REGISTRY (what the collector searches/scrapes) ----------
insert into source_registry (id, tier, publisher, url, method, pillars, notes) values
('SRC-T1-001',1,'UAE Cyber Security Council','https://csc.gov.ae','scrape','{CYBERSECURITY}','National strategy & alerts'),
('SRC-T1-002',1,'UAE Government portal','https://u.ae/en','search','{CYBERSECURITY,AI,PROCUREMENT}','Policies, strategies'),
('SRC-T1-003',1,'Tawazun Council','https://tawazun.ae','scrape','{PROCUREMENT}','Mandate, programmes, news'),
('SRC-T1-004',1,'US DoD','https://www.defense.gov','search','{CYBERSECURITY,AI,ELECTRONIC_WARFARE,PROCUREMENT}','Strategies, releases'),
('SRC-T1-005',1,'NATO / NCIA / ACT','https://www.ncia.nato.int','scrape','{ELECTRONIC_WARFARE,AI,CYBERSECURITY}','Exercises, challenges'),
('SRC-T1-006',1,'UK MOD / Defence Innovation','https://www.gov.uk/government/organisations/ministry-of-defence','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Market engagements, IPM'),
('SRC-T1-007',1,'NIST','https://www.nist.gov','search','{CYBERSECURITY,AI}','SP 800-207, AI RMF, 800-161'),
('SRC-T2-001',2,'RAND','https://www.rand.org','search','{AI,PROCUREMENT,ELECTRONIC_WARFARE}',''),
('SRC-T2-002',2,'CSIS','https://www.csis.org','search','{ELECTRONIC_WARFARE,PROCUREMENT}','Drone saturation series'),
('SRC-T2-003',2,'IISS','https://www.iiss.org','search','{CYBERSECURITY,PROCUREMENT}',''),
('SRC-T2-004',2,'RUSI','https://www.rusi.org','search','{ELECTRONIC_WARFARE,CYBERSECURITY}',''),
('SRC-T3-001',3,'Google/Mandiant Threat Intelligence','https://cloud.google.com/blog/topics/threat-intelligence','rss','{CYBERSECURITY}','APT reporting incl. Gulf'),
('SRC-T3-002',3,'Microsoft Security Blog','https://www.microsoft.com/en-us/security/blog','rss','{CYBERSECURITY}',''),
('SRC-T3-003',3,'MITRE ATT&CK','https://attack.mitre.org','api','{CYBERSECURITY}','Groups targeting Middle East'),
('SRC-T4-001',4,'Reuters Aerospace & Defense','https://www.reuters.com/business/aerospace-defense/','rss','{ELECTRONIC_WARFARE,AI,PROCUREMENT}','Discovery layer only'),
('SRC-T4-002',4,'Breaking Defense','https://breakingdefense.com','rss','{ELECTRONIC_WARFARE,AI,PROCUREMENT,CYBERSECURITY}','Discovery layer only'),
('SRC-T4-003',4,'EDGE Group newsroom','https://edgegroup.ae/news','scrape','{PROCUREMENT,ELECTRONIC_WARFARE}','UAE industrial announcements'),
('SRC-T4-004',4,'The Defense Post','https://thedefensepost.com','rss','{ELECTRONIC_WARFARE,AI}','Discovery layer only');

-- ---------- SAMPLE QUESTION BANK (extend to 10/pillar later) ----------
insert into questions (id, pillar, topic_id, stage, text) values
('CS-01','CYBERSECURITY','CS-T02','A_WHAT_IS_CHANGING','How does a more connected defence architecture change cyber risk for the UAE over 3-10 years?'),
('CS-02','CYBERSECURITY','CS-T03','C_UAE_MEANING','Which suppliers and software dependencies could create hidden mission risk for UAE defence systems?'),
('CS-03','CYBERSECURITY','CS-T04','D_WHAT_TO_DO','What cyber-assurance evidence should Tawazun require across APIs, AI models and sensor feeds?'),
('AI-01','AI','AI-T01','A_WHAT_IS_CHANGING','Where can AI most usefully improve defence decision support today and over 7+ years?'),
('AI-02','AI','AI-T02','B_WHAT_COULD_CHANGE','How could hostile autonomy change the time available to defend?'),
('EW-01','ELECTRONIC_WARFARE','EW-T01','A_WHAT_IS_CHANGING','How should EW evolve as drone communications become harder to detect and jam?'),
('EW-02','ELECTRONIC_WARFARE','EW-T01','B_WHAT_COULD_CHANGE','What happens if future drones rely less on GNSS and conventional RF control links?'),
('PR-01','PROCUREMENT','PR-T01','D_WHAT_TO_DO','How should Tawazun buy capability when the threat changes faster than acquisition cycles?'),
('PR-02','PROCUREMENT','PR-T02','C_UAE_MEANING','What should be sovereign, local, co-developed or externally sourced, function by function?');

-- ---------- REPORT TEMPLATE (mirrors the clean sample brief) ----------
insert into report_templates (id, name, sections) values
('TPL-BRIEF-01','Strategic Foresight Brief', '[
 {"key":"exec_summary","title":"Executive summary","inputs":["findings","risks","gates"],
  "instructions":"4-6 sentences. Lead with the change, then the enabling response. Never assert a UAE gap if a validation gate is OPEN."},
 {"key":"what_is_changing","title":"What is changing","inputs":["evidence","signals"],
  "instructions":"One bold-led paragraph per theme. Every claim cites [EV-xxx]. Only Class A/B evidence may be stated as fact; Class C must be marked as unproven."},
 {"key":"signals_outlook","title":"Signals and outlook","inputs":["signals"],
  "instructions":"Table of signals with computed strength + a 3-10 year outlook paragraph."},
 {"key":"uae_meaning","title":"What it means for the UAE","inputs":["evidence","findings","gates"],
  "instructions":"Split into operational-authority and acquisition-authority implications. Surface every OPEN validation gate verbatim."},
 {"key":"risk","title":"Risk assessment","inputs":["risks"],
  "instructions":"Risk table with L x I = score. State scores are working views pending validation."},
 {"key":"actions","title":"Recommended actions and indicators","inputs":["links","indicators"],
  "instructions":"Numbered actions with owner + the indicator table (watch / threshold / status)."},
 {"key":"references","title":"References","inputs":["evidence"],
  "instructions":"[EV-xxx] publisher, title, date - generated mechanically from evidence_sources."}
]'::jsonb);
