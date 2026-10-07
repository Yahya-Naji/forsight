---
agent: section-drafter
team: drafting
source: report_templates.TPL-DECISION-01 (Postgres)
---

# Decision Brief (consulting structure) — section instructions

Each block is substituted into `{instructions}` of the section-drafter prompt. Generated from the database by `pipeline/export_prompts.py`.

## answer — The answer

Inputs: `findings, risks, forecasts, gates`

THE GOVERNING THOUGHT. Four to six sentences that answer the brief outright, before any supporting argument. Lead with the single most decision-relevant fact in the data, with its citation. State the recommended direction and the one condition that would change it. No throat-clearing, no scene-setting, no restatement of the question.

## situation — Why this matters now

Inputs: `evidence, signals`

Two short paragraphs. The first states what is stable and accepted; the second states what has changed to make the decision live. This is situation then complication — if the second paragraph does not create tension with the first, rewrite it.

## findings — What we found

Inputs: `findings, signals, evidence`

The key line: three to five findings, each as its own bolded ACTION TITLE stating the conclusion — not the subject. Write 'Regional intrusion density outpaces published detection coverage', never 'Threat landscape'. Under each, two to four sentences of evidence with citations, then one sentence beginning 'So what:' giving the consequence for the reader. Order by decision impact, not by confidence.

## outlook — What could happen

Inputs: `forecasts, signals, uncertainties`

Each forecast as a short paragraph with its plausibility band in words and its falsifier. Close with the critical uncertainties — the things that would most change the answer if resolved. Never convert a band into a percentage.

## implications — What it means for you

Inputs: `findings, risks, evidence, gates`

Split by authority: what the operational owner (MoD) must decide, and what the acquisition authority (Tawazun) can shape. Each bullet is a consequence, not a restatement. Surface every OPEN gate verbatim and state plainly what cannot yet be claimed.

## actions — What to do

Inputs: `risks, forecasts, indicators, links`

Numbered recommendations, each with an owner, a horizon, and the observable trigger that should prompt revisiting it. Actions carry no evidence citations — they are proposals, not findings. Separate the decisions that are robust across every outlook from those contingent on one.

## limits — What we could not establish

Inputs: `gates, evidence`

State plainly what the evidence base does not support: which claims are blocked by an open gate, which rest on single-source Class C evidence, and what specific evidence would resolve each. This section is not a disclaimer — it is the part that tells the reader how far to trust the rest.

## references — Evidence register

Inputs: `evidence`

Assembled mechanically from evidence_sources — one entry per document, listing the evidence ids drawn from it.
