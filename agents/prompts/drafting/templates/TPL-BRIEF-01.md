---
agent: section-drafter
team: drafting
source: report_templates.TPL-BRIEF-01 (Postgres)
---

# Strategic Foresight Brief — section instructions

Each block is substituted into `{instructions}` of the section-drafter prompt. Generated from the database by `pipeline/export_prompts.py`.

## exec_summary — Executive summary

Inputs: `findings, risks, gates`

4-6 sentences. Lead with the change, then the enabling response. Never assert a UAE gap if a validation gate is OPEN.

## what_is_changing — What is changing

Inputs: `evidence, signals`

One bold-led paragraph per theme. Every claim cites [EV-xxx]. Only Class A/B evidence may be stated as fact; Class C must be marked as unproven.

## signals_outlook — Signals and outlook

Inputs: `signals`

Table of signals with computed strength + a 3-10 year outlook paragraph.

## forecast — Forecast and outlook

Inputs: `forecasts, signals, gates`

One short paragraph per forecast, ordered by horizon. State the plausibility band and the horizon in words, never as a percentage — the band is computed from corroboration and horizon distance, not estimated. Give each forecast its falsifier in the same paragraph, phrased as what would show it wrong. A SPECULATIVE forecast must be presented as a watch item, not a projection. Close with a table: forecast id, horizon, plausibility, falsifier.

## uae_meaning — What it means for the UAE

Inputs: `evidence, findings, gates`

Split into operational-authority and acquisition-authority implications. Surface every OPEN validation gate verbatim.

## risk — Risk assessment

Inputs: `risks`

Risk table with L x I = score. State scores are working views pending validation.

## actions — Recommended actions and indicators

Inputs: `links, indicators`

Numbered actions with owner + the indicator table (watch / threshold / status).

## references — References

Inputs: `evidence`

[EV-xxx] publisher, title, date - generated mechanically from evidence_sources.
