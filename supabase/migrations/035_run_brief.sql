-- ============================================================
-- 035 A RUN CARRIES ITS BRIEF
--
-- /api/generate passed the brief id only in the GitHub dispatch, so the run row
-- itself did not know which brief it was for. A local runner reading the queue
-- then wrote a generic pillar report instead of the one the client asked for.
-- The row is the request; it now holds the brief.
-- ============================================================

alter table pipeline_runs add column if not exists brief_id uuid references report_briefs(id) on delete set null;
create index if not exists pipeline_runs_brief_idx on pipeline_runs(brief_id);
