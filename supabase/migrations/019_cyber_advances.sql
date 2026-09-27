-- ============================================================
-- 019 CYBERSECURITY CAPABILITY ADVANCES
--
-- The existing cyber topics describe standing areas of concern: CII posture,
-- attack surface, supply chain, assurance standards, regional threat, cyber-EW
-- convergence. None of them asks what has CHANGED.
--
-- A decision brief needs that distinction. "Supply-chain risk exists" supports
-- no decision, because it was true last year and will be true next year. "The
-- intrusion chain now begins with AI-assisted executive impersonation rather
-- than credential theft" supports a decision, because something moved and the
-- current control set was designed before it moved.
--
-- So this topic collects advances specifically — new attacker capability, new
-- defensive capability, and new mandated standards — and the questions are
-- written to surface the date and the delta, not the condition.
-- ============================================================

insert into topics (id, pillar, name, description) values
('CS-T07', 'CYBERSECURITY', 'Cyber capability advances',
 'What has measurably changed in offensive capability, defensive capability or '
 'mandated standards, with a date attached. Standing conditions belong in the '
 'other topics; this one is about the delta.')
on conflict (id) do update set name = excluded.name, description = excluded.description;

insert into questions (id, pillar, topic_id, stage, text) values
('CS-04','CYBERSECURITY','CS-T07','A_WHAT_IS_CHANGING',
 'What new offensive techniques have been documented in the last year that defeat controls which previously worked?'),
('CS-05','CYBERSECURITY','CS-T07','A_WHAT_IS_CHANGING',
 'How is AI being used by attackers to change the cost, speed or scale of intrusion, and what has been observed rather than predicted?'),
('CS-06','CYBERSECURITY','CS-T07','A_WHAT_IS_CHANGING',
 'Which new defensive capabilities, tools or architectures have been fielded and what measurable effect have they had?'),
('CS-07','CYBERSECURITY','CS-T07','A_WHAT_IS_CHANGING',
 'What cyber standards, certifications or regulatory mandates have changed for defence suppliers, and on what timetable?'),
('CS-08','CYBERSECURITY','CS-T07','A_WHAT_IS_CHANGING',
 'What progress has been made on post-quantum cryptography migration and what deadlines now apply?'),
('CS-09','CYBERSECURITY','CS-T07','A_WHAT_IS_CHANGING',
 'Which operational technology and edge-device vulnerabilities have moved from theoretical to actively exploited?'),
('CS-10','CYBERSECURITY','CS-T07','B_WHAT_COULD_CHANGE',
 'Given the observed rate of change in attacker capability, what becomes possible for an adversary within three to five years?')
on conflict (id) do update set text = excluded.text, topic_id = excluded.topic_id;
