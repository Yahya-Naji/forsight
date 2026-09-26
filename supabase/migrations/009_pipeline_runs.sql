-- ============================================================
-- 009 PIPELINE RUNS — one row per requested pipeline execution
--
-- The dashboard can request a run, but it must never pretend one happened.
-- A row starts QUEUED and only the Python pipeline moves it to RUNNING/DONE;
-- if no dispatch channel is configured the row stays QUEUED, which is the
-- honest state rather than a fabricated success.
--
-- `stage` holds the canonical stage key the UI checklist lights up against.
-- ============================================================

create table if not exists pipeline_runs (
  id uuid primary key default uuid_generate_v4(),
  pillar pillar not null,
  template_id text references report_templates(id),
  title text,
  status text not null default 'QUEUED'
    check (status in ('QUEUED','RUNNING','DONE','FAILED')),
  -- collect | gate1 | extract | gate2 | rules | synthesize | generate | verify
  stage text,
  counts jsonb not null default '{}',
  error text,
  report_id uuid references reports(id),
  requested_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create index if not exists pipeline_runs_recent on pipeline_runs (requested_at desc);
create index if not exists pipeline_runs_pillar on pipeline_runs (pillar, requested_at desc);
