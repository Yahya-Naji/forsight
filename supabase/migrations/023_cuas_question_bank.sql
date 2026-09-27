-- ============================================================
-- 023 COUNTER-UAS — the agreed question architecture, all four pillars
--
-- The approved scope runs forty research questions, ten per pillar, all aimed at
-- one problem: Counter-UAS readiness for the UAE. Until now the graph held
-- cybersecurity questions about cyber in general, and nothing at all for AI,
-- electronic warfare or procurement — so three pillars could not produce a
-- single evidence row and the fourth was answering a different question.
--
-- These are analytical tests, not recommendations: a question earns its place by
-- changing what we would conclude, not by being worth asking. Each is written to
-- surface what is CHANGING and what it forces, which is what the downstream
-- admission rules can actually act on.
-- ============================================================

insert into topics (id, pillar, name, description) values
('EW-T01','ELECTRONIC_WARFARE','Counter-UAS electronic warfare',
 'Detection and defeat of uncrewed systems through the electromagnetic spectrum, and what happens as drones become harder to detect and jam.'),
('EW-T02','ELECTRONIC_WARFARE','Spectrum contention and deconfliction',
 'Operating counter-UAS effects in congested, contested or deliberately jammed spectrum without degrading friendly systems.'),
('AI-T01','AI','AI in the counter-UAS engagement chain',
 'Where machine assistance changes detection, fusion, classification, prioritisation and decision support — and where it must not.'),
('AI-T02','AI','Adversarial autonomy and AI assurance',
 'Hostile autonomy compressing the defender timeline, and the evidence required before an AI function is trusted operationally.'),
('PR-T01','PROCUREMENT','Acquiring capability that changes faster than the cycle',
 'Buying, refreshing and sustaining counter-UAS layers whose threat environment moves faster than conventional acquisition.'),
('PR-T02','PROCUREMENT','Sovereignty, rights and industrial readiness',
 'Which functions require national control, and which data, software and integration rights make later adaptation possible.'),
('CS-T08','CYBERSECURITY','Counter-UAS mission assurance',
 'Cyber risk across an integrated sensor, C2, AI and effector chain, treated as mission continuity rather than IT security.')
on conflict (id) do update set name = excluded.name, description = excluded.description;

insert into questions (id, pillar, topic_id, stage, text) values
-- Electronic Warfare
('EW-01','ELECTRONIC_WARFARE','EW-T01','A_WHAT_IS_CHANGING','How must counter-UAS electronic warfare change as drone communications become harder to detect and to jam?'),
('EW-02','ELECTRONIC_WARFARE','EW-T01','B_WHAT_COULD_CHANGE','What follows if uncrewed systems stop depending on GNSS and on a continuous exploitable control link?'),
('EW-03','ELECTRONIC_WARFARE','EW-T01','A_WHAT_IS_CHANGING','What sensor mix is required when a target presents little or no electronic signature?'),
('EW-04','ELECTRONIC_WARFARE','EW-T02','A_WHAT_IS_CHANGING','How is counter-UAS effectiveness sustained in congested or deliberately contested spectrum?'),
('EW-05','ELECTRONIC_WARFARE','EW-T01','B_WHAT_COULD_CHANGE','Where does machine-assisted RF analysis measurably outperform a maintained threat library, and on what evidence?'),
('EW-06','ELECTRONIC_WARFARE','EW-T01','C_UAE_MEANING','How should electronic effects be selected alongside kinetic and other non-kinetic options rather than instead of them?'),
('EW-07','ELECTRONIC_WARFARE','EW-T02','C_UAE_MEANING','What prevents friendly-force interference as the number of defensive emitters grows?'),
('EW-08','ELECTRONIC_WARFARE','EW-T02','D_WHAT_TO_DO','Which reprogramming, threat-library and mission-data rights does adaptation at operational speed actually require?'),
('EW-09','ELECTRONIC_WARFARE','EW-T01','D_WHAT_TO_DO','What observable signposts would show that current electronic-warfare assumptions are losing coverage?'),
('EW-10','ELECTRONIC_WARFARE','EW-T02','D_WHAT_TO_DO','What minimum test evidence demonstrates an electronic-warfare capability is relevant and repeatable under UAE conditions?'),
-- Artificial Intelligence
('AI-01','AI','AI-T01','A_WHAT_IS_CHANGING','Which counter-UAS functions does AI measurably improve today, and which remain unproven over a seven-year horizon?'),
('AI-02','AI','AI-T02','B_WHAT_COULD_CHANGE','How far does hostile autonomy compress the time available to detect, classify, decide and engage?'),
('AI-03','AI','AI-T02','C_UAE_MEANING','Which counter-UAS decisions must retain explicit human authority, and on what basis is that boundary drawn?'),
('AI-04','AI','AI-T01','B_WHAT_COULD_CHANGE','Which AI functions must run locally to survive degraded, denied or compromised connectivity?'),
('AI-05','AI','AI-T02','B_WHAT_COULD_CHANGE','By what means can an adversary deceive or degrade counter-UAS AI, and what has been observed rather than theorised?'),
('AI-06','AI','AI-T02','D_WHAT_TO_DO','What evidence should be required before an AI function moves from experiment to operational use?'),
('AI-07','AI','AI-T01','A_WHAT_IS_CHANGING','How well does multi-sensor fusion actually perform, and where does it remain a capability bottleneck?'),
('AI-08','AI','AI-T01','D_WHAT_TO_DO','Which AI assets — models, data, compute, update pipelines — require national control, and at what depth?'),
('AI-09','AI','AI-T01','B_WHAT_COULD_CHANGE','How can automation reduce operator load during saturation without concentrating failure into one decision path?'),
('AI-10','AI','AI-T02','D_WHAT_TO_DO','What should trigger investment in, restriction of, or retirement of an AI capability?'),
-- Cybersecurity (counter-UAS specific; CS-01..CS-10 already hold the general cyber bank)
('CSX-01','CYBERSECURITY','CS-T08','A_WHAT_IS_CHANGING','How does an integrated sensor, C2, AI and effector chain change the cyber attack surface of an air-defence capability?'),
('CSX-02','CYBERSECURITY','CS-T08','B_WHAT_COULD_CHANGE','What follows if an adversary manipulates track, identity or engagement data rather than disabling hardware?'),
('CSX-03','CYBERSECURITY','CS-T08','A_WHAT_IS_CHANGING','Which supplier, firmware and update-channel dependencies create mission risk that perimeter security cannot address?'),
('CSX-04','CYBERSECURITY','CS-T08','D_WHAT_TO_DO','What security architecture holds across a multi-vendor, modular counter-UAS ecosystem?'),
('CSX-05','CYBERSECURITY','CS-T08','B_WHAT_COULD_CHANGE','Can the mission chain continue to function under simultaneous drone, cyber and electronic attack?'),
('CSX-06','CYBERSECURITY','CS-T08','D_WHAT_TO_DO','How are rapid software, firmware and model updates controlled without introducing new vulnerability?'),
('CSX-07','CYBERSECURITY','CS-T08','D_WHAT_TO_DO','What cyber-assurance evidence should be required for interfaces, AI models and sensor feeds?'),
('CSX-08','CYBERSECURITY','CS-T08','C_UAE_MEANING','What monitoring and forensic data must be retained for a failure to be diagnosable at all?'),
('CSX-09','CYBERSECURITY','CS-T08','C_UAE_MEANING','Which external support dependencies constrain freedom of action even where equipment is nationally owned?'),
('CSX-10','CYBERSECURITY','CS-T08','D_WHAT_TO_DO','What recurring red-team and lifecycle testing should be required after acceptance?'),
-- Procurement, sovereignty and industrial readiness
('PR-01','PROCUREMENT','PR-T01','A_WHAT_IS_CHANGING','How should capability be acquired when the threat changes faster than the acquisition cycle?'),
('PR-02','PROCUREMENT','PR-T01','D_WHAT_TO_DO','Which parts of a counter-UAS system should be modular and replaceable, and which should not?'),
('PR-03','PROCUREMENT','PR-T01','C_UAE_MEANING','How should a solution be evaluated beyond probability of kill — capacity, cost per effect, magazine depth, sustainment?'),
('PR-04','PROCUREMENT','PR-T02','D_WHAT_TO_DO','Which functions should be sovereign, co-developed, localised or externally sourced, and on what criteria?'),
('PR-05','PROCUREMENT','PR-T02','D_WHAT_TO_DO','Which data, source-code, interface and integration rights most constrain later adaptation?'),
('PR-06','PROCUREMENT','PR-T01','D_WHAT_TO_DO','How is continuous testing and technology refresh institutionalised rather than treated as one-time acceptance?'),
('PR-07','PROCUREMENT','PR-T01','C_UAE_MEANING','How is vendor competition preserved without losing integration control?'),
('PR-08','PROCUREMENT','PR-T02','B_WHAT_COULD_CHANGE','How should supply-chain and export-control exposure change sourcing decisions?'),
('PR-09','PROCUREMENT','PR-T02','D_WHAT_TO_DO','Where should research, test and localisation investment go to address a defined readiness bottleneck?'),
('PR-10','PROCUREMENT','PR-T01','D_WHAT_TO_DO','What observable thresholds should trigger redesign, recompetition, technology insertion or retirement?')
on conflict (id) do update set text = excluded.text, topic_id = excluded.topic_id, pillar = excluded.pillar;
