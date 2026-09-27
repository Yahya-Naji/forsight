-- ============================================================
-- 015 TOPIC SOURCES — which sources feed which topic
--
-- The registry says what a source covers at PILLAR level, which is too coarse:
-- "Cybersecurity" spans national CII posture and supply-chain firmware, and the
-- publishers worth reading differ. Binding sources to a topic lets collection
-- be aimed rather than swept, and lets the console show an analyst exactly
-- where a topic's evidence is expected to come from.
--
-- Also records whether a source last answered, so a dead scrape is visible in
-- the console instead of surfacing as an unexplained absence of evidence.
-- ============================================================

create table if not exists topic_sources (
  topic_id text not null references topics(id) on delete cascade,
  registry_id text not null references source_registry(id) on delete cascade,
  added_at timestamptz default now(),
  primary key (topic_id, registry_id)
);

create index if not exists topic_sources_registry on topic_sources (registry_id);

-- Result of the most recent reachability test, per source.
alter table source_registry add column if not exists last_tested_at timestamptz;
alter table source_registry add column if not exists last_test_ok boolean;
alter table source_registry add column if not exists last_test_note text;

-- Topics created from the console carry no seeded description; make the
-- columns explicitly optional rather than relying on them being nullable.
alter table topics alter column description drop not null;
alter table topics alter column uae_relevance drop not null;

do $$
declare t text;
begin
  foreach t in array array['topic_sources'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_read', t);
    execute format('create policy %I on public.%I for select to anon using (true)',
                   t || '_anon_read', t);
    execute format('revoke insert, update, delete on public.%I from anon', t);
    execute format('grant select on public.%I to anon', t);
  end loop;
end $$;
