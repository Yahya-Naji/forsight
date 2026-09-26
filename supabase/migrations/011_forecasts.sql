-- ============================================================
-- 011 FORECASTS — the Jev forward-looking layer
--
-- A forecast is a typed projection over the existing graph, produced BEFORE
-- report generation so the brief can be written with the outlook already
-- admitted, scored and traceable.
--
-- Two deliberate choices:
--
-- 1. PLAUSIBILITY BANDS, NOT PERCENTAGES. A model asked for "73%" will supply
--    one, and the number will be fiction. Foresight practice distinguishes
--    plausibility from probability; the band is computed from corroboration
--    breadth, signal strength, horizon distance and unresolved uncertainty —
--    never proposed by the model.
--
-- 2. EVERY FORECAST CARRIES A FALSIFIER. A projection that no observation
--    could refute is not analysis. `falsifier` is NOT NULL for that reason.
-- ============================================================

do $$ begin
  create type plausibility as enum ('SPECULATIVE','UNCERTAIN','POSSIBLE','LIKELY');
exception when duplicate_object then null; end $$;

create table if not exists forecasts (
  id text primary key,                         -- 'FC-CS-01'
  pillar pillar not null,
  statement text not null,
  horizon horizon not null,
  env_layer env_layer not null default 'GLOBAL',
  -- COMPUTED by forecast.py. The model may not set either.
  plausibility plausibility not null,
  confidence confidence not null,
  rationale text,                              -- why, in the model's words
  falsifier text not null,                     -- what observation would refute it
  assumptions text,
  -- the inputs the band was derived from, so a reader can audit the score
  basis jsonb not null default '{}',
  created_at timestamptz default now()
);

create table if not exists forecast_signals (
  forecast_id text references forecasts(id) on delete cascade,
  signal_id text references signals(id) on delete cascade,
  primary key (forecast_id, signal_id)
);

create table if not exists forecast_evidence (
  forecast_id text references forecasts(id) on delete cascade,
  evidence_id text references evidence(id) on delete cascade,
  primary key (forecast_id, evidence_id)
);

create table if not exists forecast_uncertainties (
  forecast_id text references forecasts(id) on delete cascade,
  uncertainty_id text references uncertainties(id) on delete cascade,
  primary key (forecast_id, uncertainty_id)
);

create index if not exists forecasts_pillar on forecasts (pillar, horizon);

do $$
declare t text;
begin
  foreach t in array array['forecasts','forecast_signals','forecast_evidence',
                           'forecast_uncertainties'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_read', t);
    execute format('create policy %I on public.%I for select to anon using (true)',
                   t || '_anon_read', t);
    execute format('revoke insert, update, delete on public.%I from anon', t);
    execute format('grant select on public.%I to anon', t);
  end loop;
end $$;
