-- ============================================================
-- 006 ROW LEVEL SECURITY — read-only anon access for the dashboard
--
-- The Next.js app ships the ANON key to the browser, so every table it reads
-- must be RLS-protected and explicitly granted SELECT. The pipeline uses the
-- SERVICE key, which bypasses RLS entirely — writes stay server-side.
--
-- Safe to re-run: policies are dropped before being recreated.
-- ============================================================

do $$
declare
  t text;
  readable text[] := array[
    -- core ontology
    'topics','questions','source_registry','documents',
    'evidence','evidence_sources','signals','signal_evidence',
    'findings','risks','validation_gates','indicators','links',
    'entities','entity_evidence','report_templates','reports',
    -- foresight objects (005)
    'trends','drivers','cross_impacts','uncertainties','scenarios',
    'scenario_uncertainties','implications','opportunities','options',
    'stress_tests','initiatives','actions','decision_requirements',
    'research_gaps','controversies'
  ];
begin
  foreach t in array readable loop
    if to_regclass('public.' || t) is null then
      raise notice 'skipping %, table not present', t;
      continue;
    end if;

    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_read', t);
    execute format(
      'create policy %I on public.%I for select to anon using (true)',
      t || '_anon_read', t);
    execute format('grant select on public.%I to anon', t);
  end loop;
end $$;

-- No insert/update/delete policy is created for anon anywhere. With RLS on and
-- no permissive policy for those commands, writes from the browser are refused
-- even if the anon key leaks.

-- The dashboard lists documents for traceability but never needs the scraped
-- body; exposing it would ship tens of MB to the browser.
create or replace view public.document_refs as
  select d.id, d.url, d.title, d.published_on, d.retrieved_at,
         d.registry_id, s.publisher, s.tier
    from public.documents d
    left join public.source_registry s on s.id = d.registry_id;

grant select on public.document_refs to anon;
