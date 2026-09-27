-- Figures: images that carry information, cited like any other evidence.
--
-- The rule that matters here is that a figure is NOT automatically evidence. A
-- chart of intrusion-set growth is evidence; the stock photo of a server room
-- at the top of the same article is decoration. Putting the photo in a
-- leadership brief borrows the authority of the publisher without carrying any
-- of its information, which is exactly the failure the evidence classes exist
-- to prevent. So `informative` is decided by rule from `kind`, never by the
-- model directly, and only informative figures are offered to a report.
--
-- Provenance comes through document_id. A figure inherits its publisher, tier
-- and date from the document it was found in, so a cited figure is traceable
-- the same way a cited claim is.

do $$ begin
  create type figure_kind as enum (
    'CHART',          -- plotted data
    'DIAGRAM',        -- architecture, flow, taxonomy
    'MAP',            -- geographic
    'TABLE_IMAGE',    -- a table rendered as a picture
    'SCREENSHOT',     -- interface or artefact capture
    'TIMELINE',
    'PHOTO',          -- photograph — decoration unless it IS the evidence
    'LOGO',
    'UNKNOWN');
exception when duplicate_object then null; end $$;

create table if not exists figures (
  id            text primary key,                  -- FIG-001
  document_id   uuid not null references documents(id) on delete cascade,
  pillar        pillar not null,
  url           text not null,
  caption       text,                              -- figcaption, when the page had one
  alt           text,
  kind          figure_kind not null default 'UNKNOWN',

  -- Decided by rule from `kind` (see rules.figure_is_informative). A model may
  -- propose the kind; it may never set this column.
  informative   boolean not null default false,

  -- What the figure actually shows, in one sentence, for a reader who cannot
  -- see it. Doubles as the alt text in the exported report.
  describes     text,

  width         int,
  height        int,
  credit        text,

  -- A figure that no longer loads must not be rendered into a brief: a broken
  -- image reads as a broken report. Checked before export, not at collection.
  reachable     boolean,
  content_type  text,
  bytes         int,
  checked_at    timestamptz,

  created_at    timestamptz default now(),
  unique (document_id, url)
);

create index if not exists figures_pillar_idx      on figures(pillar);
create index if not exists figures_document_idx    on figures(document_id);
create index if not exists figures_informative_idx on figures(pillar, informative);

-- Which evidence rows a figure supports. A figure cited next to a claim should
-- be the figure that shows that claim, not merely one from the same article.
create table if not exists evidence_figures (
  evidence_id text not null references evidence(id) on delete cascade,
  figure_id   text not null references figures(id)  on delete cascade,
  primary key (evidence_id, figure_id)
);

alter table figures enable row level security;
alter table evidence_figures enable row level security;

do $$ begin
  drop policy if exists figures_anon_read on figures;
  create policy figures_anon_read on figures for select to anon using (true);
  drop policy if exists evidence_figures_anon_read on evidence_figures;
  create policy evidence_figures_anon_read on evidence_figures for select to anon using (true);
end $$;

-- Why a figure was refused. Refusals are analytical output, not noise: "76
-- images refused as decoration, 3 of them classified as charts but carrying no
-- publisher caption" is a statement about source quality the reader can audit.
alter table figures add column if not exists refused_reason text;
