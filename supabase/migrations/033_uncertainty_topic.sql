-- ============================================================
-- 033 UNCERTAINTY TOPIC — synthesis runs per topic (synthesize.py --node), so
-- an uncertainty records the topic it was raised in. That is what lets
-- `--replace --node` clear one branch's uncertainties without touching the
-- rest of the pillar. Null for uncertainties raised by a whole-pillar run.
-- ============================================================
alter table uncertainties add column if not exists topic_id text references topics(id);
create index if not exists uncertainties_topic on uncertainties (topic_id);
