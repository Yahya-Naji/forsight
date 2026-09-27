-- ============================================================
-- 016 REPORT BRIEFS — what the reader actually asked for
--
-- Generation was bound to a pillar and one fixed template, so the only
-- question it could answer was "summarise this pillar". A brief captures the
-- real request — the decision being supported, who reads it, what is in and
-- out of scope — and generation works from that.
--
-- It also gives section scoping something to scope BY: with a brief, the
-- generation ledger's "rows withheld" stops being zero, because there is
-- finally a basis for withholding.
-- ============================================================

do $$ begin
  create type brief_status as enum ('DRAFTING','READY','USED');
exception when duplicate_object then null; end $$;

create table if not exists report_briefs (
  id uuid primary key default uuid_generate_v4(),
  title text,
  -- the question the report exists to answer, in the reader's words
  goal text,
  -- the decision it supports; a brief with no decision produces a summary
  decision text,
  audience text,
  pillars pillar[] not null default '{}',
  horizon horizon,
  focus_terms text[] not null default '{}',   -- drives relevance scoping
  in_scope text,
  out_of_scope text,
  depth text not null default 'STANDARD'      -- BRIEF | STANDARD | DEEP
    check (depth in ('BRIEF','STANDARD','DEEP')),
  status brief_status not null default 'DRAFTING',
  transcript jsonb not null default '[]',     -- the intake conversation
  created_at timestamptz default now()
);

create table if not exists brief_messages (
  id bigserial primary key,
  brief_id uuid not null references report_briefs(id) on delete cascade,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz default now()
);

create index if not exists brief_messages_thread on brief_messages (brief_id, created_at);

alter table reports add column if not exists brief_id uuid references report_briefs(id);

do $$
declare t text;
begin
  foreach t in array array['report_briefs','brief_messages'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_read', t);
    execute format('create policy %I on public.%I for select to anon using (true)',
                   t || '_anon_read', t);
    execute format('revoke insert, update, delete on public.%I from anon', t);
    execute format('grant select on public.%I to anon', t);
  end loop;
end $$;
