-- ============================================================
-- 028 EXTRACTED PILLARS — which pillars have already read a document
--
-- extract.py used to take the newest N documents every run, so a re-run read
-- the same documents again and duplicated their evidence. Each pillar reads a
-- document once (a RUSI paper feeds EW and the three lenses separately).
-- ============================================================

alter table documents add column if not exists extracted_pillars text[] not null default '{}';

-- Documents that already produced evidence count as read by that pillar.
update documents d set extracted_pillars = sub.pillars
  from (select es.document_id, array_agg(distinct e.pillar::text) as pillars
          from evidence_sources es join evidence e on e.id = es.evidence_id
         group by es.document_id) sub
 where d.id = sub.document_id and d.extracted_pillars = '{}';
