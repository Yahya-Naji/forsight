-- ============================================================
-- 027 EW TOPIC SOURCES — which sources feed each EW-core topic
--
-- Binds the 025 topics to the 026 registry. Only live (non-archived)
-- sources are bound. Search-method rows (GAO, CRS, RUSI, CSIS...) are
-- bound too: they collect once SERPER_API_KEY is set, and until then the
-- console shows them as bound but silent rather than hiding the gap.
-- ============================================================

insert into topic_sources (topic_id, registry_id)
select t, r from (values
  -- Electronic Warfare: the core
  ('EW-T10','SRC-T4-001'), ('EW-T10','SRC-T4-011'), ('EW-T10','SRC-T4-016'),
  ('EW-T10','SRC-T4-017'), ('EW-T10','SRC-T2-004'), ('EW-T10','SRC-T2-005'),
  ('EW-T11','SRC-T4-010'), ('EW-T11','SRC-T4-012'), ('EW-T11','SRC-T4-005'),
  ('EW-T11','SRC-T2-002'),
  ('EW-T12','SRC-T4-001'), ('EW-T12','SRC-T4-013'), ('EW-T12','SRC-T4-017'),
  ('EW-T13','SRC-T4-011'), ('EW-T13','SRC-T4-016'), ('EW-T13','SRC-T4-018'),
  ('EW-T14','SRC-T4-014'), ('EW-T14','SRC-T4-015'), ('EW-T14','SRC-T4-021'),
  ('EW-T15','SRC-T4-013'), ('EW-T15','SRC-T1-015'), ('EW-T15','SRC-T1-005'),
  ('EW-T16','SRC-T4-009'), ('EW-T16','SRC-T4-010'), ('EW-T16','SRC-T4-012'),
  ('EW-T16','SRC-T4-005'), ('EW-T16','SRC-T4-006'), ('EW-T16','SRC-T1-017'),
  ('EW-T17','SRC-T4-019'), ('EW-T17','SRC-T4-020'), ('EW-T17','SRC-T4-009'),
  ('EW-T17','SRC-T2-004'),
  ('EW-T18','SRC-T4-017'), ('EW-T18','SRC-T2-005'), ('EW-T18','SRC-T4-016'),
  ('EW-T19','SRC-T4-019'), ('EW-T19','SRC-T4-020'), ('EW-T19','SRC-T4-021'),
  ('EW-T19','SRC-T4-009'), ('EW-T19','SRC-T2-002'),
  -- Cybersecurity → EW
  ('CS-T10','SRC-T4-011'), ('CS-T10','SRC-T4-013'), ('CS-T10','SRC-T2-004'),
  ('CS-T11','SRC-T4-012'), ('CS-T11','SRC-T4-009'), ('CS-T11','SRC-T4-005'),
  ('CS-T12','SRC-T1-008'), ('CS-T12','SRC-T4-011'), ('CS-T12','SRC-T4-018'),
  ('CS-T13','SRC-T4-018'), ('CS-T13','SRC-T4-012'),
  ('CS-T14','SRC-T1-015'), ('CS-T14','SRC-T4-013'),
  -- AI → EW
  ('AI-T10','SRC-T4-011'), ('AI-T10','SRC-T4-018'), ('AI-T10','SRC-T2-001'),
  ('AI-T11','SRC-T4-012'), ('AI-T11','SRC-T4-018'), ('AI-T11','SRC-T1-005'),
  ('AI-T12','SRC-T4-019'), ('AI-T12','SRC-T4-020'), ('AI-T12','SRC-T4-009'),
  ('AI-T13','SRC-T1-015'), ('AI-T13','SRC-T2-001'),
  -- Procurement → EW
  ('PR-T10','SRC-T1-015'), ('PR-T10','SRC-T1-016'), ('PR-T10','SRC-T4-017'),
  ('PR-T11','SRC-T1-015'), ('PR-T11','SRC-T4-010'), ('PR-T11','SRC-T4-012'),
  ('PR-T12','SRC-T1-003'), ('PR-T12','SRC-T4-004'), ('PR-T12','SRC-T2-003'),
  ('PR-T13','SRC-T1-006'), ('PR-T13','SRC-T4-013'), ('PR-T13','SRC-T1-017'),
  ('PR-T14','SRC-T2-002'), ('PR-T14','SRC-T4-010'), ('PR-T14','SRC-T4-022')
) as b(t, r)
where exists (select 1 from source_registry s where s.id = b.r and s.archived_at is null)
on conflict do nothing;
