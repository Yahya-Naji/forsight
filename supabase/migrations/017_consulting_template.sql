-- ============================================================
-- 017 CONSULTING TEMPLATE — answer first, action titles, so-what
--
-- The existing template is a foresight register: what is changing, signals,
-- risks. Accurate, but it reads as a survey and buries the answer. Top-tier
-- consulting structure inverts it — the governing thought comes first, each
-- heading states a conclusion rather than a subject, and every section closes
-- on the implication rather than the observation.
--
-- The honest section is "What we could not establish". Most consulting decks
-- omit it; here it is the differentiator, because the system can enumerate it.
-- ============================================================

insert into report_templates (id, name, sections) values
('TPL-DECISION-01', 'Decision Brief (consulting structure)', '[
 {"key":"answer","title":"The answer","inputs":["findings","risks","forecasts","gates"],
  "instructions":"THE GOVERNING THOUGHT. Four to six sentences that answer the brief outright, before any supporting argument. Lead with the single most decision-relevant fact in the data, with its citation. State the recommended direction and the one condition that would change it. No throat-clearing, no scene-setting, no restatement of the question."},

 {"key":"situation","title":"Why this matters now","inputs":["evidence","signals"],
  "instructions":"Two short paragraphs. The first states what is stable and accepted; the second states what has changed to make the decision live. This is situation then complication — if the second paragraph does not create tension with the first, rewrite it."},

 {"key":"findings","title":"What we found","inputs":["findings","signals","evidence"],
  "instructions":"The key line: three to five findings, each as its own bolded ACTION TITLE stating the conclusion — not the subject. Write ''Regional intrusion density outpaces published detection coverage'', never ''Threat landscape''. Under each, two to four sentences of evidence with citations, then one sentence beginning ''So what:'' giving the consequence for the reader. Order by decision impact, not by confidence."},

 {"key":"outlook","title":"What could happen","inputs":["forecasts","signals","uncertainties"],
  "instructions":"Each forecast as a short paragraph with its plausibility band in words and its falsifier. Close with the critical uncertainties — the things that would most change the answer if resolved. Never convert a band into a percentage."},

 {"key":"implications","title":"What it means for you","inputs":["findings","risks","evidence","gates"],
  "instructions":"Split by authority: what the operational owner (MoD) must decide, and what the acquisition authority (Tawazun) can shape. Each bullet is a consequence, not a restatement. Surface every OPEN gate verbatim and state plainly what cannot yet be claimed."},

 {"key":"actions","title":"What to do","inputs":["risks","forecasts","indicators","links"],
  "instructions":"Numbered recommendations, each with an owner, a horizon, and the observable trigger that should prompt revisiting it. Actions carry no evidence citations — they are proposals, not findings. Separate the decisions that are robust across every outlook from those contingent on one."},

 {"key":"limits","title":"What we could not establish","inputs":["gates","evidence"],
  "instructions":"State plainly what the evidence base does not support: which claims are blocked by an open gate, which rest on single-source Class C evidence, and what specific evidence would resolve each. This section is not a disclaimer — it is the part that tells the reader how far to trust the rest."},

 {"key":"references","title":"Evidence register","inputs":["evidence"],
  "instructions":"Assembled mechanically from evidence_sources — one entry per document, listing the evidence ids drawn from it."}
]'::jsonb)
on conflict (id) do update set name = excluded.name, sections = excluded.sections;
