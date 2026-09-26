-- ============================================================
-- 013 REPORT EDITS — conversational revision, still under verification
--
-- A reader can highlight a passage, discuss it, and have the assistant rewrite
-- it. The danger is obvious: a chat that can edit a verified report is a hole
-- straight through the discipline the rest of the system enforces.
--
-- So an edit is a PROPOSAL until it passes the same checks generation does —
-- citations resolve, nothing unsourced, no open gate contradicted. The verdict
-- is stored with the edit, and every applied edit keeps the text it replaced,
-- so any sentence in a report can be traced to who or what put it there.
-- ============================================================

do $$ begin
  create type edit_status as enum ('PROPOSED','APPLIED','REJECTED','SUPERSEDED');
exception when duplicate_object then null; end $$;

create table if not exists report_edits (
  id uuid primary key default uuid_generate_v4(),
  report_id uuid not null references reports(id) on delete cascade,
  -- the exact text selected by the reader; how the passage is located
  original_text text not null,
  proposed_text text,
  question text,                       -- what the reader asked
  answer text,                         -- what the assistant replied
  status edit_status not null default 'PROPOSED',
  -- deterministic verdict on proposed_text: citations, unsourced, gates
  verification jsonb not null default '{}',
  rejected_reason text,
  citations text[] not null default '{}',
  created_at timestamptz default now(),
  applied_at timestamptz
);

create index if not exists report_edits_report on report_edits (report_id, created_at desc);

-- Conversation turns, so a thread survives a page reload and the assistant can
-- see what was already discussed about this passage.
create table if not exists report_chat (
  id bigserial primary key,
  report_id uuid not null references reports(id) on delete cascade,
  selection text,
  role text not null check (role in ('user','assistant')),
  content text not null,
  edit_id uuid references report_edits(id),
  created_at timestamptz default now()
);

create index if not exists report_chat_thread on report_chat (report_id, created_at);

do $$
declare t text;
begin
  foreach t in array array['report_edits','report_chat'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_read', t);
    execute format('create policy %I on public.%I for select to anon using (true)',
                   t || '_anon_read', t);
    execute format('revoke insert, update, delete on public.%I from anon', t);
    execute format('grant select on public.%I to anon', t);
  end loop;
end $$;
