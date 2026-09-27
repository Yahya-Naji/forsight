-- ============================================================
-- 021 ADVANCE → FORECAST → DECISION
--
-- TPL-DECISION-01 answers "what should we do about X". This template answers a
-- harder question: "something has changed — does it force a decision, and why?"
--
-- The difference is the argument, not the layout. A foresight register lists
-- conditions; a decision rationale has to carry the reader along a chain where
-- each link is checkable and the conclusion does not survive if a link breaks:
--
--   1. WHAT CHANGED     a dated, cited advance — offensive, defensive or
--                       regulatory. Not a standing condition. If it was equally
--                       true three years ago it is not an advance.
--   2. WHY IT MATTERS   the mechanism. Which control, assumption or timetable
--                       the advance invalidates. This is the link most briefs
--                       skip, and skipping it is what makes a recommendation
--                       feel arbitrary.
--   3. WHAT FOLLOWS     the forecast, in plausibility bands, each with its
--                       falsifier.
--   4. WHY ACT NOW      the decision, and the cost of being wrong in each
--                       direction — including the cost of acting too early.
--   5. WHAT WOULD CHANGE OUR MIND
--
-- The reader's question is never "is this interesting". It is "why must I do
-- something, and why now" — so the rationale section is required to state the
-- because-chain explicitly and to name what the reader loses by waiting.
--
-- Figures are admitted here for the first time: threat reports publish the
-- charts their conclusions rest on, and an advance that can be shown should be.
-- ============================================================

insert into report_templates (id, name, sections) values
('TPL-ADVANCE-01', 'Advance → Forecast → Decision', '[
 {"key":"answer","title":"The decision, up front","inputs":["findings","forecasts","risks","gates"],
  "instructions":"Five to seven sentences, in this order and no other. (1) The single most decision-relevant thing that has CHANGED, with its citation and its date. (2) What that change invalidates — a control, an assumption or a timetable. (3) What follows from it, with the plausibility band in words. (4) The decision now required, and of whom. (5) The cost of waiting one more planning cycle. Do not open by restating the question, do not describe the report, and do not write that cybersecurity is important."},

 {"key":"advances","title":"What has actually changed","inputs":["evidence","signals","figures"],
  "instructions":"The heart of the brief. Produce THREE TO FIVE SEPARATE ADVANCES, each under its own bolded ACTION TITLE stating what changed — ''AI-assisted impersonation has replaced credential theft as the opening move'', never ''AI and cyber''. Under each title: two to four sentences of dated, cited evidence, then one sentence beginning ''So what:'' naming the consequence or the decision it forces. THE ADVANCES MUST BE DISTINCT. Do not split one theme across three titles, and do not return a single advance because one theme has the most evidence — scan the data for separate areas of change. The evidence base covers, among others: attacker use of AI and its measured cost and speed; post-quantum cryptography standards and their migration deadlines; operational-technology and edge-device vulnerabilities moving from theoretical to actively exploited; supply-chain and supplier dependency compromise; and changes to mandated standards or certification. Take one advance from each area the data actually supports. Order them by how much each moves the decision. THE TEST FOR INCLUSION: if the statement was equally true three years ago it is a standing condition, not an advance — cut it. Prefer advances carrying a number, a date or a named standard. FIGURES: the data includes published figures with ids and descriptions. Cite the ones that show what you are asserting, as [FIG-xxx] or [FIG-xxx, FIG-yyy], inside the sentence they illustrate — the image and its caption are placed into the report automatically, and you must never write a file name or URL. These figures all come from one vendor investigation into AI-assisted executive impersonation and invoice fraud, so cite them on the advance about attacker use of AI, where they are direct evidence, and do not attach them to the post-quantum or supply-chain advances, where they show nothing. Do not describe a figure the reader can see; say what it means. The sentence still needs its own evidence citation."},

 {"key":"mechanism","title":"Why this changes the risk","inputs":["evidence","signals","findings","risks"],
  "instructions":"The link most briefs omit. For each significant advance, state the MECHANISM by which it changes exposure: which specific control it defeats, which assumption in current practice it falsifies, or which timetable it compresses. Write it as a chain the reader can break — ''Because X is now observed [EV-xxx], the assumption that Y provides sufficient assurance no longer holds, which means Z''. Two to four such chains. If you cannot name what an advance defeats, say so plainly instead of asserting significance."},

 {"key":"forecast","title":"What follows from here","inputs":["forecasts","signals","uncertainties","evidence"],
  "instructions":"Each forecast as a short paragraph naming its FC- id, its horizon in words, its plausibility band in words, and its falsifier in the same paragraph. State the reasoning from the advances above to the forecast — a forecast that does not follow from a documented advance should be marked as resting on weaker ground. Never convert a band into a percentage or odds. Close with the two or three uncertainties that would most change the picture if resolved, and say which way each would push it."},

 {"key":"rationale","title":"Why you have to act, and why now","inputs":["findings","risks","forecasts","gates","evidence"],
  "instructions":"THE ARGUMENT FOR ACTING. Not a list of recommendations — the case for why inaction is itself a decision. Structure it as: (1) the because-chain, stated in full, from observed advance through mechanism to consequence, naming the id at each link; (2) what the reader loses by deferring one planning cycle; (3) the cost of being wrong in BOTH directions, and which error is recoverable. TWO RULES DECIDE WHETHER THIS SECTION SURVIVES. First, every EMPIRICAL premise needs its id — a lead time, a deadline, a cost, a rate. If the evidence base does not give you one, write ''the evidence base does not establish the procurement lead time here'' and reason from what it does give you; do not assert a number or a duration you cannot cite. Second, write the two-directional cost as CONDITIONALS, because that is what they are: ''If the advance stalls, the wasted effort falls on X rather than Y'' and ''If it continues and the migration has not started, Z''. A conditional claims nothing about the present and needs no citation; the same thought written as a flat assertion (''these costs are recoverable'') asserts a fact about the world with nothing behind it and will be rejected. Distinguish what is robust across every outlook from what depends on one. Where an OPEN gate blocks a claim, state that the decision rests on the unblocked part."},

 {"key":"actions","title":"What to do","inputs":["risks","forecasts","indicators","links"],
  "instructions":"Numbered actions. Each is ONE imperative sentence starting with a verb, followed only by its owner, its horizon and the observable trigger that should prompt revisiting it — written as ''Trigger: ...''. Actions carry no evidence citations because a proposal is not a finding. THEREFORE DO NOT JUSTIFY THEM HERE. A sentence explaining why an action matters (''such planning is necessary given the long lead time'', ''this is crucial because...'') asserts a fact with nothing behind it and will be rejected — the justification belongs in the rationale section, where it can cite its premise. Group the actions under three headings: act now regardless of how the forecasts resolve; act now because the lead time exceeds the horizon; hold and monitor. If you need to state a lead time to place an action in the second group, cite the id that establishes it, or write the claim as a conditional (''If the migration deadline holds, work started later than ... does not complete in time''). Never assert a duration you cannot cite."},

 {"key":"limits","title":"What would change our mind","inputs":["gates","evidence","uncertainties"],
  "instructions":"State plainly what this evidence base does not support: which claims are blocked by an open gate, which rest on single-source Class C evidence, where the figures come from one publisher rather than several, and what specific evidence would resolve each. Then state what observation would falsify the central argument. This is not a disclaimer — it tells the reader how far to trust the rest, and a reader who cannot see this section cannot act on the brief."},

 {"key":"references","title":"Evidence register","inputs":["evidence"],
  "instructions":"Assembled mechanically from evidence_sources — one entry per document, listing the evidence ids drawn from it."}
]'::jsonb)
on conflict (id) do update set name = excluded.name, sections = excluded.sections;
