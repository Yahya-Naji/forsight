-- ============================================================
-- 005 FORESIGHT OBJECTS — the rest of the analytical chain
--
-- 001 modelled: question -> evidence -> signal -> finding -> risk -> indicator.
-- The FETC methodology (report §5.1) runs sixteen node types:
--
--   Question -> Evidence -> Signal -> Trend/Driver -> Cross-Impact ->
--   Critical Uncertainty -> Scenario -> MoD Implication -> Tawazun Implication ->
--   Risk/Opportunity -> Option -> Stress Test -> Initiative -> Action ->
--   Indicator/Trigger -> Decision Requirement
--
-- This migration adds the ten that were missing. Every table is NEW; nothing in
-- 001-004 is altered except two additive columns on `signals` and `risks`.
-- Typed rows here are what lets the generator write sections 9-21 of the report
-- from the graph instead of from the model's memory.
-- ============================================================

-- ---------- shared enums ----------
do $$ begin
  create type horizon as enum ('H0_3','H3_5','H5_10','H7_PLUS');
exception when duplicate_object then null; end $$;

do $$ begin
  create type actor as enum ('MOD','TAWAZUN');       -- implications are split by authority
exception when duplicate_object then null; end $$;

do $$ begin
  create type robustness as enum ('ROBUST','CONDITIONAL','FRAGILE');
exception when duplicate_object then null; end $$;

-- ---------- §9 trends, drivers, cross-impacts ----------
create table if not exists trends (
  id text primary key,                  -- 'TR-EW-01'
  pillar pillar not null,
  name text not null,
  statement text not null,
  direction signal_direction not null default 'UNCERTAIN',
  horizon horizon,
  created_at timestamptz default now()
);

create table if not exists drivers (
  id text primary key,                  -- 'DRV-01'
  name text not null,
  description text,
  pillar pillar
);

-- The report's "Multi-Dimensional Obsolescence Risk" is a cross-impact: two
-- trends that are individually manageable and jointly are not.
create table if not exists cross_impacts (
  id text primary key,                  -- 'CI-01'
  from_trend text references trends(id),
  to_trend text references trends(id),
  statement text not null,
  severity smallint check (severity between 1 and 3)
);

-- ---------- §10 critical uncertainties ----------
create table if not exists uncertainties (
  id text primary key,                  -- 'CU-01'
  pillar pillar,
  question text not null,               -- "what we do not know"
  why_it_matters text not null,
  created_at timestamptz default now()
);

-- ---------- §11 scenarios ----------
-- Dimensions stay jsonb: the report writes a threat/AI/EW/cyber paragraph per
-- scenario, and a fixed column per pillar would not survive a new pillar.
create table if not exists scenarios (
  id text primary key,                  -- 'S1'
  name text not null,
  one_sentence text not null,
  dimensions jsonb not null default '{}',   -- {threat, ai, ew, cyber, mod, tawazun}
  horizon horizon,
  created_at timestamptz default now()
);

create table if not exists scenario_uncertainties (
  scenario_id text references scenarios(id) on delete cascade,
  uncertainty_id text references uncertainties(id),
  primary key (scenario_id, uncertainty_id)
);

-- ---------- §12/§13 implications, split by authority ----------
-- The report insists MoD implications and Tawazun implications never merge:
-- MoD owns the operational question, Tawazun owns the enabling environment.
create table if not exists implications (
  id text primary key,                  -- 'IMP-MOD-01'
  actor actor not null,
  pillar pillar,
  statement text not null,
  finding_id text references findings(id)
);

-- ---------- §15 opportunities (risks already exist in 001) ----------
create table if not exists opportunities (
  id text primary key,                  -- 'O1'
  statement text not null,
  pillar pillar,
  attractiveness smallint check (attractiveness between 1 and 3),
  feasibility smallint check (feasibility between 1 and 3),
  score smallint generated always as (attractiveness * feasibility) stored
);

-- ---------- §16/§17 options and scenario stress testing ----------
create table if not exists options (
  id text primary key,                  -- 'OPT-A'
  name text not null,
  description text not null,
  is_working_hypothesis boolean not null default false
);

create table if not exists stress_tests (
  option_id text references options(id) on delete cascade,
  scenario_id text references scenarios(id) on delete cascade,
  result robustness not null,
  note text,
  primary key (option_id, scenario_id)
);

-- ---------- §18/§19 initiatives and actions ----------
-- Initiatives are Class D by definition: proposed constructs for Tawazun
-- consideration, never descriptions of current policy. The column is fixed so
-- the generator cannot present one as an existing commitment.
create table if not exists initiatives (
  id text primary key,                  -- 'INIT-01'
  name text not null,
  objective text not null,
  class evidence_class not null default 'D' check (class = 'D'),
  owner text,
  horizon horizon,
  created_at timestamptz default now()
);

create table if not exists actions (
  id text primary key,                  -- 'ACT-01'
  initiative_id text references initiatives(id) on delete cascade,
  statement text not null,
  owner text,
  horizon horizon,
  sequence smallint
);

-- ---------- §21 leadership decision requirements ----------
create table if not exists decision_requirements (
  id text primary key,                  -- 'PDC-1'
  title text not null,
  decision text not null,
  why_first text,
  data_needed text,
  priority smallint
);

-- ---------- additive columns on existing tables ----------
alter table signals add column if not exists steep text[] not null default '{}';
alter table signals add column if not exists env_layer env_layer;
alter table signals add column if not exists planning_horizon horizon;
alter table risks  add column if not exists pillar pillar;

-- ---------- registers the methodology requires (report §5.6) ----------
-- Rejected extractions and unresolved contradictions are analytical output, not
-- errors: the Research Gap Register is what lets the report state what it could
-- NOT establish, which is the discipline the human report applies in §22.
create table if not exists research_gaps (
  id bigserial primary key,
  pillar pillar,
  question_id text references questions(id),
  gap text not null,
  raised_by text,                       -- rule or stage that noticed it
  created_at timestamptz default now()
);

create table if not exists controversies (
  id text primary key,                  -- 'CTR-01'
  statement text not null,
  position_a text not null,
  position_b text not null,
  resolution text,
  status text not null default 'OPEN'
);

-- ---------- indexes on the hot paths ----------
create index if not exists trends_pillar        on trends (pillar);
create index if not exists implications_actor   on implications (actor, pillar);
create index if not exists opportunities_pillar on opportunities (pillar);
create index if not exists research_gaps_pillar on research_gaps (pillar);
