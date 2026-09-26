-- ============================================================
-- 010 RLS — read-only anon access for the console
--
-- The dashboard ships the ANON key to the browser, so every table it reads is
-- RLS-protected and granted SELECT only. No INSERT/UPDATE/DELETE policy exists
-- for anon on any table: with RLS enabled and no permissive policy for those
-- commands, writes are refused even if the anon key leaks.
--
-- The pipeline and the /api/generate route use the SERVICE key, which bypasses
-- RLS entirely and is never exposed to the browser.
--
-- Safe to re-run: policies are dropped before being recreated.
-- ============================================================

do $$
declare
  t text;
  readable text[] := array[
    'evidence','evidence_sources','documents','source_registry','topics',
    'signals','validation_gates','reports','pipeline_runs',
    -- also read by the console: pillar pages, signal rails, report apparatus
    'questions','signal_evidence','findings','risks','entities',
    'entity_evidence','trends','uncertainties','generation_ledger','research_gaps'
  ];
begin
  foreach t in array readable loop
    if to_regclass('public.' || t) is null then
      raise notice 'skipping %, not present', t;
      continue;
    end if;
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_read', t);
    execute format(
      'create policy %I on public.%I for select to anon using (true)',
      t || '_anon_read', t);
    execute format('revoke insert, update, delete on public.%I from anon', t);
    execute format('grant select on public.%I to anon', t);
  end loop;
end $$;
