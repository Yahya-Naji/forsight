-- ============================================================
-- 034 REPORT CITATIONS — what a report cited, frozen when it was issued
--
-- Synthesis and forecasting rebuild their objects: a daily run clears a
-- branch's signals, findings and forecasts and mints new ids (ids are never
-- reissued). A report issued yesterday still cites the old ids, and with only
-- the live graph to resolve against, its citations would stop opening.
--
-- So generation writes one row per cited id with the text, quote and source as
-- they stood when the report was written. The reading view resolves from here
-- first and falls back to the live graph only for reports written before this
-- table existed. An issued report is a record; it does not drift.
-- ============================================================

create table if not exists report_citations (
  report_id  uuid not null references reports(id) on delete cascade,
  cited_id   text not null,
  kind       text not null check (kind in
               ('evidence','finding','signal','risk','trend','gate','forecast','other')),
  text       text,
  quote      text,
  class      text,
  publisher  text,
  tier       int,
  url        text,
  doc_title  text,
  published  text,
  strength   text,
  status     text,
  frozen_at  timestamptz not null default now(),
  primary key (report_id, cited_id)
);

alter table report_citations enable row level security;
drop policy if exists report_citations_anon_read on report_citations;
create policy report_citations_anon_read on report_citations for select to anon using (true);
revoke insert, update, delete on report_citations from anon;
grant select on report_citations to anon;
