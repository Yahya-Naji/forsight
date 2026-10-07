---
agent: section-drafter
team: drafting
source: report_templates.TPL-FETC-23 (Postgres)
---

# Strategic Foresight Report (full 23-section deliverable) — section instructions

Each block is substituted into `{instructions}` of the section-drafter prompt. Generated from the database by `pipeline/export_prompts.py`.

## exec_summary — 1. Executive Summary

Inputs: `findings, risks, forecasts, options, decisions, gates`

Open on the single most decision-relevant fact in the evidence, with its citation. Then: what is changing, what it means for the UAE, the strategic options on the table, the working decision hypothesis and what leadership must decide. Six to ten sentences of prose followed by a short bulleted key-judgement list. No scene-setting, no restatement of the brief, and never a sentence that would read the same with the data deleted.

## purpose_scope — 2. Purpose, Scope & Primary Strategic Question

Inputs: `topics, questions`

State the purpose of the report, what is in and out of scope, the planning horizons used (0-3, 3-5, 5-10 and beyond 7 years), and the primary strategic question the analysis answers. Derive the scope from the topics and questions in the data — do not invent a remit. Close by naming the question the rest of the report is organised around.

## definitions — 3. Definitions & Terminology

Inputs: `evidence, signals`

Define the technical terms this report actually uses, drawn from the evidence and signals below — not a generic glossary. One short paragraph per term, alphabetical, as a markdown table with columns Term and Definition. Include only terms that appear in the material; a definition of something the report never mentions is padding. Where a term is used in the sources with more than one meaning, say so and state which meaning this report uses.

## alignment — 4. Tawazun Strategic Alignment

Inputs: `implications, findings, gates`

State what makes this analysis relevant to Tawazun specifically: which areas of its mandate the findings touch, and where the UAE defence interest and the Tawazun acquisition interest are the same question and where they diverge. Name the validation still required from the customer. Keep the two authorities distinct — this section sets up §12 and §13 and must not pre-empt either.

## methodology — 5. Methodology & Evidence Framework

Inputs: `sources, gates, gaps`

Describe the method AS IT ACTUALLY RAN, from the data below. Cover: the nine-step analytical process; the four source tiers with the registered publishers actually used; how evidence class and confidence are assigned by rule rather than asserted; that corroboration is counted in DISTINCT PUBLISHERS so several claims from one article remain one source; claim traceability from every sentence to a verbatim quote span; the human validation gates and which are currently open; and the treatment of uncertainty in plausibility bands rather than percentages. State plainly that refusals are recorded as analytical output — cite the refusal counts in the data. Do not describe a step the data does not evidence.

## question_architecture — 6. Strategic Question Architecture

Inputs: `questions, topics`

Present the question hierarchy: the primary strategic question, the four framing questions (what is changing, what could change, what it means for the UAE, what Tawazun should do), and the research questions grouped by topic. Render the question bank as a markdown table with columns Id, Topic, Stage and Question, using the ids from the data. State the research depth applied and what remains pending customer approval.

## baseline — 7. Current Baseline / Current State

Inputs: `evidence, signals, gates`

What is true today, before any projection. Structure it as: the threat baseline, the defensive and technology baseline, and the UAE public baseline. Every statement carries its citation. Close with a subsection naming the baseline gaps that require customer validation — what the public evidence cannot establish about UAE holdings, posture or programmes. Never infer a UAE-specific fact that an open gate blocks.

## horizon_scanning — 8. Horizon Scanning & Signals

Inputs: `signals, evidence, figures`

What is changing, read across sources. Group the signals into threat-side, defence-side and acquisition/industrial. For each, state the signal, its strength in words, and the evidence behind it. Where a figure shows a signal, cite it as [FIG-xxx] in the sentence it illustrates — never write a URL. Close with the combined signal: the thing all of them together say that none of them says alone. That closing paragraph is the point of the section.

## trends — 9. Trends, Drivers & Cross-Impacts

Inputs: `trends, drivers, cross_impacts, signals`

One numbered subsection per trend, each with a title stating the direction of travel ('From X to Y'), the signals behind it and its horizon. Then the drivers underneath the trends. Then the cross-impacts — two trends that are individually manageable and jointly are not; these are the highest-value paragraphs in the section, so state the interaction rather than the sum, and name both trend ids. Close with the strategic interpretation.

## uncertainties — 10. Critical Uncertainties

Inputs: `uncertainties, signals`

The things the evidence genuinely does not settle and that would most change the assessment if resolved. One short paragraph each, naming the CU- id, what is unknown, why it matters, and which way the answer would push the analysis. These are the axes the scenarios in §11 turn on, so order them by how much they would move the conclusion.

## scenarios — 11. Future Scenarios

Inputs: `scenarios, uncertainties, forecasts`

Open with one paragraph on how to read the scenarios: they are not forecasts and not best/worst cases, but materially different futures used to test decisions. Then one subsection per scenario, naming its S- id and the uncertainties it turns on, with its one-sentence summary followed by short paragraphs on the threat picture, the technology picture, what it means for MoD and what it means for Tawazun. Close with what the set tells you together — what is common to all of them, which is where the robust decisions live.

## mod_implications — 12. UAE Defence / MoD Strategic Implications

Inputs: `implications, findings, risks, gates`

ONLY the implications whose actor is MoD — readiness, training, mission assurance, operational command. Use only implications from the data marked with that authority; do not restate Tawazun implications here, they are §13. Each as a short subsection with a conclusion-stating title, the finding it follows from, and what MoD would have to do differently. Close by naming the customer validation required before any of it can be acted on.

## tawazun_implications — 13. Tawazun Strategic Implications

Inputs: `implications, findings, risks, gates`

ONLY the implications whose actor is Tawazun — acquisition, contracting, industrial capability, sovereignty, technology transfer, test and evaluation. Use only implications from the data marked with that authority. Each as a short subsection with a conclusion-stating title, the finding it follows from, and what Tawazun can shape that MoD cannot. This section is about the enabling environment, not about operations.

## risks — 14. Strategic Risk Assessment

Inputs: `risks, findings, evidence`

Open with one paragraph on how to read the scores — likelihood and impact are computed from corroboration breadth and topic coverage, not asserted. Then a markdown table with columns Id, Risk, Likelihood, Impact, Score, ordered by score descending. Then a short paragraph on the highest-scoring risks and what drives them. Never convert a score into a probability.

## opportunities — 15. Strategic Opportunity Assessment

Inputs: `opportunities, findings, evidence`

The upside peer of §14, scored the same way — attractiveness and feasibility are computed, not asserted. A markdown table with columns Id, Opportunity, Attractiveness, Feasibility, Score, then a short paragraph on where the strongest opportunities sit. If the data contains few or no admitted opportunities, say so plainly and state what evidence would be needed to identify them — an empty opportunity register is a finding about the evidence base, not a section to pad.

## options — 16. Strategic Options

Inputs: `options, findings, risks, forecasts`

One subsection per option, using its OPT- id and name: what the posture is, what it assumes, what it costs and what it forecloses. These are genuinely different postures, not increments — if two read as versions of one another, say so. Close with the working decision hypothesis and state that it was selected by counting the stress-test matrix in §17, not asserted here.

## stress_test — 17. Scenario Stress Test

Inputs: `stress_tests, options, scenarios`

Open with what the stress test asks: not which option is best, but which survives futures we cannot choose between. Then a markdown table with the options as rows and the scenarios as columns, each cell showing Robust, Conditional or Fragile. Then one short paragraph per scenario on what it does to the options. Close with what remains useful in EVERY scenario — that is the no-regrets set, and it is the most actionable paragraph in the report. If the matrix is incomplete, say which cells are missing and that the comparison is correspondingly limited.

## initiatives — 18. Strategic Actions & Recommended Initiatives

Inputs: `initiatives, actions_planned, risks, options`

One subsection per initiative, using its INIT- id: objective, owner, horizon and the actions under it. Every initiative is a PROPOSAL for consideration, never a description of existing policy — say so once at the top of the section and do not present any of them as current commitments. Actions carry no evidence citations; they are proposals, not findings. Close with how the portfolio fits together and which initiatives are prerequisites for others.

## roadmap — 19. Action Roadmap

Inputs: `actions_planned, initiatives, indicators`

The actions sequenced by horizon under four headings: first 90 days, 0-24 months, 3-5 years, and 7+ years. Each entry names its action id, its owner and the initiative it belongs to, as a markdown table per horizon with columns Id, Action, Owner, Initiative. Close with the sequencing rule — what must happen before what, and why the order matters.

## indicators — 20. Indicators, Triggers & Signposts

Inputs: `indicators, forecasts, uncertainties`

How the watch system works, then a markdown table with columns Id, What to watch, Threshold, Response. Every threshold in the data is concrete by rule — an indicator without an observable trigger was refused, because it is not a control. Link the indicators to the forecasts and uncertainties they would resolve. If few indicators survived admission, state how many were refused and why that matters for the watch function.

## decisions — 21. Leadership Decision Requirements

Inputs: `decisions, options, gates, gaps`

What leadership is actually being asked to decide. One subsection per priority decision candidate, using its PDC- id: the decision, why it comes first, and — the part that matters most — WHAT DATA IS STILL NEEDED from Tawazun or MoD before it can be taken. Close with the additional decisions that follow once these are made, and restate every open validation gate as a blocker on the decisions it touches.

## limits — 22. Assumptions, Limitations & Evidence Gaps

Inputs: `gates, evidence, uncertainties, gaps`

Split into what this report can say with confidence and what it cannot confirm from public sources. Name the open gates and exactly which claims they block. State which conclusions rest on single-source Class C evidence. Report the refusal counts from the data and what they mean — what the analysis declined to assert, and on what grounds. Close with the evidence rule the report held throughout. This section is not a disclaimer; it tells the reader how far to trust the other twenty-one.

## conclusion — 23. Conclusion

Inputs: `findings, forecasts, options, decisions`

Four to six sentences. What the evidence establishes, what follows from it, which option survives the stress test, and what must now be decided. No new claims, no new citations, and no summary of the structure of the report — the reader has just read it.

## references — Evidence Register

Inputs: `evidence`

Assembled mechanically from evidence_sources — one entry per document, listing the evidence ids drawn from it.
