-- ============================================================
-- 001 CORE ONTOLOGY — shared upper model for all four pillars
-- Neurosymbolic Foresight POC · Supabase (Postgres)
-- ============================================================

create extension if not exists "uuid-ossp";

-- Pillars are fixed by the deck
create type pillar as enum ('CYBERSECURITY','AI','ELECTRONIC_WARFARE','PROCUREMENT');
create type env_layer as enum ('UAE','REGIONAL','GLOBAL');
create type evidence_class as enum ('A','B','C','D');       -- A fact / B corroborated / C hypothesis / D policy construct
create type confidence as enum ('LOW','MEDIUM','MEDIUM_HIGH','HIGH');
create type signal_strength as enum ('WEAK','EMERGING','STRONG_EMERGING','STRONG');
create type signal_direction as enum ('STRENGTHENING','UNCERTAIN','WEAKENING');
create type gate_type as enum ('FETC_REVIEW','CUSTOMER_VALIDATION','EXPERT_VALIDATION');
create type gate_status as enum ('OPEN','PASSED','FAILED');
create type pipeline_stage as enum ('A_WHAT_IS_CHANGING','B_WHAT_COULD_CHANGE','C_UAE_MEANING','D_WHAT_TO_DO');

-- Topics: the focus areas of each pillar (seeded from the deck + Counter-UAS template)
create table topics (
  id text primary key,                 -- e.g. 'CS-T01'
  pillar pillar not null,
  name text not null,
  description text,
  uae_relevance text                   -- why this matters for the UAE specifically
);

-- Strategic questions (the question bank)
create table questions (
  id text primary key,                 -- e.g. 'CS-01'
  pillar pillar not null,
  topic_id text references topics(id),
  stage pipeline_stage not null,
  text text not null
);

-- Source registry: WHERE the agent searches/scrapes (tiered)
create table source_registry (
  id text primary key,                 -- e.g. 'SRC-T1-001'
  tier smallint not null check (tier between 1 and 4),
  publisher text not null,
  url text not null,
  method text not null default 'search',   -- search | rss | scrape | api
  pillars pillar[] not null,
  notes text
);

-- A concrete retrieved document
create table documents (
  id uuid primary key default uuid_generate_v4(),
  registry_id text references source_registry(id),
  url text not null,
  title text,
  published_on date,
  retrieved_at timestamptz default now(),
  raw_text text,
  unique(url)
);

-- Evidence: a typed, sourced claim (the atom of the system)
create table evidence (
  id text primary key,                 -- e.g. 'EV-001'
  claim text not null,
  class evidence_class not null,
  confidence confidence not null,
  env_layer env_layer not null,
  steep text[] not null default '{}',  -- Social/Technological/Economic/Environmental/Political
  pillar pillar not null,
  topic_id text references topics(id),
  question_id text references questions(id),
  quote_span text,
  created_at timestamptz default now()
);

-- Evidence <-> documents (a claim can be corroborated by several docs)
create table evidence_sources (
  evidence_id text references evidence(id) on delete cascade,
  document_id uuid references documents(id),
  primary key (evidence_id, document_id)
);

create table signals (
  id text primary key,                 -- 'SIG-EW-04'
  pillar pillar not null,
  statement text not null,
  strength signal_strength not null,   -- COMPUTED by rules, never set by the LLM
  direction signal_direction not null,
  horizon text,
  created_at timestamptz default now()
);

create table signal_evidence (
  signal_id text references signals(id) on delete cascade,
  evidence_id text references evidence(id),
  primary key (signal_id, evidence_id)
);

create table findings (
  id text primary key,                 -- 'F-EW-01'
  statement text not null,
  pillar pillar not null
);

create table risks (
  id text primary key,                 -- 'R-EW-01'
  statement text not null,
  likelihood smallint check (likelihood between 1 and 3),
  impact smallint check (impact between 1 and 3),
  score smallint generated always as (likelihood * impact) stored,
  response text
);

create table validation_gates (
  id text primary key,                 -- 'VG-001'
  gate gate_type not null,
  status gate_status not null default 'OPEN',
  blocks text not null,                -- what claim/section this gate blocks
  raised_by text                       -- rule name
);

create table indicators (
  id text primary key,                 -- 'IND-EW-01'
  watch text not null,
  threshold text not null,
  action text not null,
  status text not null default 'WATCHING'  -- WATCHING | THRESHOLD_MET | FIRED
);

-- Generic typed links (question->finding, finding->risk, risk->initiative...)
create table links (
  from_id text not null,
  from_type text not null,
  to_id text not null,
  to_type text not null,
  rel text not null,                   -- feeds | derivedFrom | mitigatedBy | monitors ...
  primary key (from_id, to_id, rel)
);

-- Report templates and generated reports
create table report_templates (
  id text primary key,
  name text not null,
  sections jsonb not null              -- ordered [{key,title,instructions,inputs:[entity types]}]
);

create table reports (
  id uuid primary key default uuid_generate_v4(),
  template_id text references report_templates(id),
  pillar pillar,
  title text not null,
  status text not null default 'DRAFT',  -- DRAFT | GATES_OPEN | FINAL
  body_md text,
  created_at timestamptz default now()
);
