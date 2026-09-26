-- ============================================================
-- 007 GENERATION LEDGER — what the model was given, per section
--
-- The claim "each section is drafted only from the rows linked to it" was
-- previously unverifiable: generation left no record of what it passed or
-- withheld. This table is that record, written by generate.py as it runs, and
-- read by the report's trace view.
--
-- It is analytical output, not logging: "10 rows withheld" is the evidence
-- that generation was bounded.
-- ============================================================

create table if not exists generation_ledger (
  id bigserial primary key,
  report_id uuid references reports(id) on delete cascade,
  section_key text not null,
  section_title text,
  inputs_declared text[] not null default '{}',
  rows_passed jsonb not null default '{}',   -- {evidence: 12, signals: 4}
  rows_withheld jsonb not null default '{}', -- {evidence: 10}
  scoped boolean not null default false,     -- false = no section links existed
  instructions text,
  citations_emitted text[] not null default '{}',
  chars_sent int,
  created_at timestamptz default now()
);

create index if not exists gen_ledger_report on generation_ledger (report_id);

do $$ begin
  execute 'alter table public.generation_ledger enable row level security';
  execute 'drop policy if exists generation_ledger_anon_read on public.generation_ledger';
  execute 'create policy generation_ledger_anon_read on public.generation_ledger
           for select to anon using (true)';
  execute 'grant select on public.generation_ledger to anon';
end $$;
