-- ============================================================
-- 022 THE FULL DELIVERABLE — all 23 sections
--
-- The earlier templates are 8-section briefs. The committed deliverable is 23
-- numbered sections plus references, and the methodology deck promises nine
-- named analytical outputs across horizons 0-3 / 3-5 / 5-10.
--
-- Two things make this template different from the briefs:
--
--   MoD and Tawazun implications are SEPARATE sections (§12, §13). They are two
--   authorities with different levers — MoD owns readiness and mission
--   assurance, Tawazun owns acquisition, contracts and industrial capability.
--   Merging them produces advice nobody owns.
--
--   Scenarios are a spine, not a chapter. §11 defines them, §16 proposes
--   options, and §17 tests every option against every scenario. That triad is
--   what lets a recommendation say "robust across all five futures" rather than
--   "advisable" — and strategize.py counts the matrix rather than letting the
--   model nominate its own favourite.
--
-- §5 is the section no consultancy can write this way: the methodology is
-- rendered from the live system — the source registry, the gates that are open,
-- the refusal ledger — rather than described from memory.
-- ============================================================

insert into report_templates (id, name, sections) values
('TPL-FETC-23', 'Strategic Foresight Report (full 23-section deliverable)', '[
 {"key":"exec_summary","title":"1. Executive Summary","inputs":["findings","risks","forecasts","options","decisions","gates"],
  "instructions":"Open on the single most decision-relevant fact in the evidence, with its citation. Then: what is changing, what it means for the UAE, the strategic options on the table, the working decision hypothesis and what leadership must decide. Six to ten sentences of prose followed by a short bulleted key-judgement list. No scene-setting, no restatement of the brief, and never a sentence that would read the same with the data deleted."},

 {"key":"purpose_scope","title":"2. Purpose, Scope & Primary Strategic Question","inputs":["topics","questions"],
  "instructions":"State the purpose of the report, what is in and out of scope, the planning horizons used (0-3, 3-5, 5-10 and beyond 7 years), and the primary strategic question the analysis answers. Derive the scope from the topics and questions in the data — do not invent a remit. Close by naming the question the rest of the report is organised around."},

 {"key":"definitions","title":"3. Definitions & Terminology","inputs":["evidence","signals"],
  "instructions":"Define the technical terms this report actually uses, drawn from the evidence and signals below — not a generic glossary. One short paragraph per term, alphabetical, as a markdown table with columns Term and Definition. Include only terms that appear in the material; a definition of something the report never mentions is padding. Where a term is used in the sources with more than one meaning, say so and state which meaning this report uses."},

 {"key":"alignment","title":"4. Tawazun Strategic Alignment","inputs":["implications","findings","gates"],
  "instructions":"State what makes this analysis relevant to Tawazun specifically: which areas of its mandate the findings touch, and where the UAE defence interest and the Tawazun acquisition interest are the same question and where they diverge. Name the validation still required from the customer. Keep the two authorities distinct — this section sets up §12 and §13 and must not pre-empt either."},

 {"key":"methodology","title":"5. Methodology & Evidence Framework","inputs":["sources","gates","gaps"],
  "instructions":"Describe the method AS IT ACTUALLY RAN, from the data below. Cover: the nine-step analytical process; the four source tiers with the registered publishers actually used; how evidence class and confidence are assigned by rule rather than asserted; that corroboration is counted in DISTINCT PUBLISHERS so several claims from one article remain one source; claim traceability from every sentence to a verbatim quote span; the human validation gates and which are currently open; and the treatment of uncertainty in plausibility bands rather than percentages. State plainly that refusals are recorded as analytical output — cite the refusal counts in the data. Do not describe a step the data does not evidence."},

 {"key":"question_architecture","title":"6. Strategic Question Architecture","inputs":["questions","topics"],
  "instructions":"Present the question hierarchy: the primary strategic question, the four framing questions (what is changing, what could change, what it means for the UAE, what Tawazun should do), and the research questions grouped by topic. Render the question bank as a markdown table with columns Id, Topic, Stage and Question, using the ids from the data. State the research depth applied and what remains pending customer approval."},

 {"key":"baseline","title":"7. Current Baseline / Current State","inputs":["evidence","signals","gates"],
  "instructions":"What is true today, before any projection. Structure it as: the threat baseline, the defensive and technology baseline, and the UAE public baseline. Every statement carries its citation. Close with a subsection naming the baseline gaps that require customer validation — what the public evidence cannot establish about UAE holdings, posture or programmes. Never infer a UAE-specific fact that an open gate blocks."},

 {"key":"horizon_scanning","title":"8. Horizon Scanning & Signals","inputs":["signals","evidence","figures"],
  "instructions":"What is changing, read across sources. Group the signals into threat-side, defence-side and acquisition/industrial. For each, state the signal, its strength in words, and the evidence behind it. Where a figure shows a signal, cite it as [FIG-xxx] in the sentence it illustrates — never write a URL. Close with the combined signal: the thing all of them together say that none of them says alone. That closing paragraph is the point of the section."},

 {"key":"trends","title":"9. Trends, Drivers & Cross-Impacts","inputs":["trends","drivers","cross_impacts","signals"],
  "instructions":"One numbered subsection per trend, each with a title stating the direction of travel (''From X to Y''), the signals behind it and its horizon. Then the drivers underneath the trends. Then the cross-impacts — two trends that are individually manageable and jointly are not; these are the highest-value paragraphs in the section, so state the interaction rather than the sum, and name both trend ids. Close with the strategic interpretation."},

 {"key":"uncertainties","title":"10. Critical Uncertainties","inputs":["uncertainties","signals"],
  "instructions":"The things the evidence genuinely does not settle and that would most change the assessment if resolved. One short paragraph each, naming the CU- id, what is unknown, why it matters, and which way the answer would push the analysis. These are the axes the scenarios in §11 turn on, so order them by how much they would move the conclusion."},

 {"key":"scenarios","title":"11. Future Scenarios","inputs":["scenarios","uncertainties","forecasts"],
  "instructions":"Open with one paragraph on how to read the scenarios: they are not forecasts and not best/worst cases, but materially different futures used to test decisions. Then one subsection per scenario, naming its S- id and the uncertainties it turns on, with its one-sentence summary followed by short paragraphs on the threat picture, the technology picture, what it means for MoD and what it means for Tawazun. Close with what the set tells you together — what is common to all of them, which is where the robust decisions live."},

 {"key":"mod_implications","title":"12. UAE Defence / MoD Strategic Implications","inputs":["implications","findings","risks","gates"],
  "instructions":"ONLY the implications whose actor is MoD — readiness, training, mission assurance, operational command. Use only implications from the data marked with that authority; do not restate Tawazun implications here, they are §13. Each as a short subsection with a conclusion-stating title, the finding it follows from, and what MoD would have to do differently. Close by naming the customer validation required before any of it can be acted on."},

 {"key":"tawazun_implications","title":"13. Tawazun Strategic Implications","inputs":["implications","findings","risks","gates"],
  "instructions":"ONLY the implications whose actor is Tawazun — acquisition, contracting, industrial capability, sovereignty, technology transfer, test and evaluation. Use only implications from the data marked with that authority. Each as a short subsection with a conclusion-stating title, the finding it follows from, and what Tawazun can shape that MoD cannot. This section is about the enabling environment, not about operations."},

 {"key":"risks","title":"14. Strategic Risk Assessment","inputs":["risks","findings","evidence"],
  "instructions":"Open with one paragraph on how to read the scores — likelihood and impact are computed from corroboration breadth and topic coverage, not asserted. Then a markdown table with columns Id, Risk, Likelihood, Impact, Score, ordered by score descending. Then a short paragraph on the highest-scoring risks and what drives them. Never convert a score into a probability."},

 {"key":"opportunities","title":"15. Strategic Opportunity Assessment","inputs":["opportunities","findings","evidence"],
  "instructions":"The upside peer of §14, scored the same way — attractiveness and feasibility are computed, not asserted. A markdown table with columns Id, Opportunity, Attractiveness, Feasibility, Score, then a short paragraph on where the strongest opportunities sit. If the data contains few or no admitted opportunities, say so plainly and state what evidence would be needed to identify them — an empty opportunity register is a finding about the evidence base, not a section to pad."},

 {"key":"options","title":"16. Strategic Options","inputs":["options","findings","risks","forecasts"],
  "instructions":"One subsection per option, using its OPT- id and name: what the posture is, what it assumes, what it costs and what it forecloses. These are genuinely different postures, not increments — if two read as versions of one another, say so. Close with the working decision hypothesis and state that it was selected by counting the stress-test matrix in §17, not asserted here."},

 {"key":"stress_test","title":"17. Scenario Stress Test","inputs":["stress_tests","options","scenarios"],
  "instructions":"Open with what the stress test asks: not which option is best, but which survives futures we cannot choose between. Then a markdown table with the options as rows and the scenarios as columns, each cell showing Robust, Conditional or Fragile. Then one short paragraph per scenario on what it does to the options. Close with what remains useful in EVERY scenario — that is the no-regrets set, and it is the most actionable paragraph in the report. If the matrix is incomplete, say which cells are missing and that the comparison is correspondingly limited."},

 {"key":"initiatives","title":"18. Strategic Actions & Recommended Initiatives","inputs":["initiatives","actions_planned","risks","options"],
  "instructions":"One subsection per initiative, using its INIT- id: objective, owner, horizon and the actions under it. Every initiative is a PROPOSAL for consideration, never a description of existing policy — say so once at the top of the section and do not present any of them as current commitments. Actions carry no evidence citations; they are proposals, not findings. Close with how the portfolio fits together and which initiatives are prerequisites for others."},

 {"key":"roadmap","title":"19. Action Roadmap","inputs":["actions_planned","initiatives","indicators"],
  "instructions":"The actions sequenced by horizon under four headings: first 90 days, 0-24 months, 3-5 years, and 7+ years. Each entry names its action id, its owner and the initiative it belongs to, as a markdown table per horizon with columns Id, Action, Owner, Initiative. Close with the sequencing rule — what must happen before what, and why the order matters."},

 {"key":"indicators","title":"20. Indicators, Triggers & Signposts","inputs":["indicators","forecasts","uncertainties"],
  "instructions":"How the watch system works, then a markdown table with columns Id, What to watch, Threshold, Response. Every threshold in the data is concrete by rule — an indicator without an observable trigger was refused, because it is not a control. Link the indicators to the forecasts and uncertainties they would resolve. If few indicators survived admission, state how many were refused and why that matters for the watch function."},

 {"key":"decisions","title":"21. Leadership Decision Requirements","inputs":["decisions","options","gates","gaps"],
  "instructions":"What leadership is actually being asked to decide. One subsection per priority decision candidate, using its PDC- id: the decision, why it comes first, and — the part that matters most — WHAT DATA IS STILL NEEDED from Tawazun or MoD before it can be taken. Close with the additional decisions that follow once these are made, and restate every open validation gate as a blocker on the decisions it touches."},

 {"key":"limits","title":"22. Assumptions, Limitations & Evidence Gaps","inputs":["gates","evidence","uncertainties","gaps"],
  "instructions":"Split into what this report can say with confidence and what it cannot confirm from public sources. Name the open gates and exactly which claims they block. State which conclusions rest on single-source Class C evidence. Report the refusal counts from the data and what they mean — what the analysis declined to assert, and on what grounds. Close with the evidence rule the report held throughout. This section is not a disclaimer; it tells the reader how far to trust the other twenty-one."},

 {"key":"conclusion","title":"23. Conclusion","inputs":["findings","forecasts","options","decisions"],
  "instructions":"Four to six sentences. What the evidence establishes, what follows from it, which option survives the stress test, and what must now be decided. No new claims, no new citations, and no summary of the structure of the report — the reader has just read it."},

 {"key":"references","title":"Evidence Register","inputs":["evidence"],
  "instructions":"Assembled mechanically from evidence_sources — one entry per document, listing the evidence ids drawn from it."}
]'::jsonb)
on conflict (id) do update set name = excluded.name, sections = excluded.sections;
