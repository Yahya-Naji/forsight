-- ============================================================
-- 012 FORECAST SECTION — put the outlook in the brief
--
-- Inserted after "Signals and outlook" and before "What it means for the UAE":
-- the reader should meet the projection immediately after the signals it rests
-- on, and before any UAE-specific interpretation of it.
-- ============================================================

update report_templates
set sections = (
  select jsonb_agg(section order by ord)
  from (
    select section, ord from (
      select value as section, ordinality * 10 as ord
      from jsonb_array_elements(sections) with ordinality
    ) existing
    union all
    select
      jsonb_build_object(
        'key', 'forecast',
        'title', 'Forecast and outlook',
        'inputs', jsonb_build_array('forecasts', 'signals', 'gates'),
        'instructions',
          'One short paragraph per forecast, ordered by horizon. State the ' ||
          'plausibility band and the horizon in words, never as a percentage — ' ||
          'the band is computed from corroboration and horizon distance, not ' ||
          'estimated. Give each forecast its falsifier in the same paragraph, ' ||
          'phrased as what would show it wrong. A SPECULATIVE forecast must be ' ||
          'presented as a watch item, not a projection. Close with a table: ' ||
          'forecast id, horizon, plausibility, falsifier.'
      ),
      -- 30 = after signals_outlook (ord 30), before uae_meaning (ord 40)
      35
  ) merged
)
where id = 'TPL-BRIEF-01'
  and not exists (
    select 1 from jsonb_array_elements(sections) s
    where s->>'key' = 'forecast'
  );
