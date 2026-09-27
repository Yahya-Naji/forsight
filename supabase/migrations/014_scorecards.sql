-- ============================================================
-- 014 SCORECARDS — evaluation results the console can render
--
-- evaluate.py wrote JSON to disk, which nobody but the person who ran it ever
-- saw. The comparison against a human-written report is the clearest statement
-- of what this system is for, so it belongs on screen.
-- ============================================================

create table if not exists scorecards (
  id uuid primary key default uuid_generate_v4(),
  pillar pillar not null,
  report_id uuid references reports(id) on delete set null,
  benchmark text not null,                 -- the document scored against
  benchmark_label text,                    -- its filename, for display
  recall jsonb not null default '{}',      -- per register: totals, in-scope, matched
  ours_text jsonb not null default '{}',   -- unsourced rate, citation density
  benchmark_text jsonb not null default '{}',
  chain_completeness jsonb not null default '{}',
  novel jsonb not null default '{}',
  created_at timestamptz default now()
);

create index if not exists scorecards_recent on scorecards (pillar, created_at desc);

do $$ begin
  execute 'alter table public.scorecards enable row level security';
  execute 'drop policy if exists scorecards_anon_read on public.scorecards';
  execute 'create policy scorecards_anon_read on public.scorecards for select to anon using (true)';
  execute 'revoke insert, update, delete on public.scorecards from anon';
  execute 'grant select on public.scorecards to anon';
end $$;
