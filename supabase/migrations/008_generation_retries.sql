-- ============================================================
-- 008 GENERATION RETRIES — record the regenerate-on-failure loop
--
-- A section whose citations do not resolve is regenerated with the failures
-- fed back, and withheld if it still fails. Those attempts are analytical
-- record, not logging: "withheld after 2 retries" is the system declining to
-- publish rather than shipping a broken citation.
-- ============================================================

alter table generation_ledger add column if not exists retries smallint not null default 0;
alter table generation_ledger add column if not exists withheld boolean not null default false;
alter table generation_ledger add column if not exists failures jsonb not null default '[]';
