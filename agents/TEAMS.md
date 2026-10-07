# From stages to teams

How the pipeline would run if each stage were a team of agents rather than one
prompt. The prompts themselves are in [`prompts/`](prompts/README.md).

## Where we are

Fourteen prompts, each called once per unit of work, in a fixed order. Between
every neural step sits a symbolic one that the model cannot argue with:

```
brief ─► collect ─► extract ─► gate 3 ─► rules ─► synthesise ─► forecast ─► strategise ─► draft ⇄ verify ─► release
 LLM      code       LLM       LLM(Jev)   code      LLM + rule     LLM + rule   LLM + rule    LLM     code+LLM
```

This is already a team in all but name — it just has one member per role, and
the hand-off is "write rows, exit". Only drafting has a real feedback loop
(`RETRY_SUFFIX` feeds verifier failures back to the drafter). Everywhere else a
rejection is final: a bad extraction goes to `research_gaps` and nobody tries
again.

## The teams

Each team owns one kind of object, reads from the team before it, and may write
only its own tables. **No team — and no agent — sets class, confidence, strength
or a score.** That stays in `rules.py`, whatever the org chart looks like.

| Team | Owns | Members | Reviewer | May never |
|---|---|---|---|---|
| **Intake** | `report_briefs` | brief-interviewer | human client | pick sources or evidence |
| **Collection** | `documents` | lane A/B/C collectors; *new:* source scout that turns a `research_gap` into a search | registry tier rules | invent a source outside the registry |
| **Extraction** | candidate `evidence`, `entities`, `figures` | evidence-extractor ×N (one per document), figure-classifier | Validation | assign class or confidence |
| **Validation** (= Jev layer) | the *verdicts* on evidence | G1 relevance triage, G2 quote-supports-claim, G3 same-fact merge, G4 forecast support | `rules.py` thresholds | edit a claim — only admit, reject, merge |
| **Analysis** | `signals`, `findings`, `risks`, `forecasts`, `trends`, `scenarios`, `options` | synthesiser, forecaster, strategist | G4 + corroboration rules | cite evidence that did not pass Validation |
| **Drafting** | `reports` sections | section-drafter ×N (already concurrent) | Audit | cite outside the graph |
| **Audit** | violations, release decision | deterministic checks + citation-entailment | none — it is the last word | rewrite a section itself |
| **Evaluation** | `scorecards` | benchmark-extractor, benchmark-matcher | the human benchmark | feed anything back into a live run |

Evaluation stays outside the loop on purpose: if its scores steered generation,
the benchmark would stop measuring anything.

## Five rules that make it a team rather than a crowd

**1. The lead is code, not a model.** Routing, retries, thresholds and the
decision to stop are in Python. An LLM "manager" that decides which agent runs
next makes every run a different run and breaks the audit story — the whole
pitch is that a reviewer can replay why a sentence exists. Agents do judgement;
the orchestrator does control flow.

**2. Nobody validates their own work.** The validator gets a different prompt,
sees the quote and the claim but *not* the extractor's reasoning, and where the
budget allows runs on the other deployment. Same model, same prompt, same
context means correlated errors — two agents agreeing is then worth one.

**3. Rejections carry a reason and go back once.** Today a rejected extraction
dies. In a team, Validation returns `{evidence_id, gate, reason}` to
Extraction, which gets one retry on that document with the reasons appended —
the pattern `generate.py` already uses with `RETRY_SUFFIX`. Bounded: one retry,
then `research_gaps`, then Collection may pick the gap up as a search task.

**4. Disagreement escalates; it is never voted away.** If two extractors pull
contradictory claims from sources, both survive as evidence and the contradiction
becomes a signal for Analysis. If an agent and a rule disagree, the rule wins
and the disagreement is logged. Majority voting between agents is not a gate.

**5. The database is the only channel.** Agents do not message each other.
Every hand-off is a row with a state, so the console's ledger shows the team's
work without any extra logging, and a crashed worker loses nothing.

## What the database needs for that

Evidence currently lands in its final table the moment extraction writes it —
there is no "proposed, not yet checked" state. A team needs one:

```
evidence.stage:  EXTRACTED → TRIAGED (G1) → ENTAILED (G2) → MERGED (G3) → CLASSED (rules) → ADMITTED
                      └──────────── REJECTED {gate, reason, attempt} ─────────────┘
```

plus a small work queue so N workers can share one stage safely:

```sql
create table work_items (
  id          bigserial primary key,
  run_id      uuid references pipeline_runs,
  team        text not null,          -- extraction | validation | drafting ...
  object_id   text not null,          -- document id, evidence id, section key
  state       text not null default 'READY',   -- READY | CLAIMED | DONE | FAILED
  attempt     int  not null default 0,
  reason      text,                   -- why the last attempt was sent back
  claimed_at  timestamptz
);
-- a worker takes the next item without two workers taking the same one
select * from work_items where team = $1 and state = 'READY'
order by id for update skip locked limit 1;
```

Analysis reads only `stage = 'ADMITTED'`, which makes "Analysis may not cite
unvalidated evidence" a query, not a promise.

## Where parallelism pays

| Team | Fan-out unit | Why |
|---|---|---|
| Extraction | document | independent; the biggest volume, on the fast deployment |
| Validation G1/G2 | batch of ~20 evidence rows | independent per row |
| Validation G3 | pairs within one document | must see siblings, so per document |
| Analysis | pillar | synthesis needs the whole pillar's evidence at once — keep serial |
| Drafting | section | already concurrent in `generate.py` |
| Audit | section | entailment batches are independent |

## Cost

A team roughly doubles model calls on the hot path (every extraction is checked
once more). Keep that affordable by putting workers on `FAST` at low effort and
spending the strong deployment only on reviewers, and only on what a rule marks
as borderline — e.g. G2 re-checks with the strong model only when the fast
verdict sits between 0.60 and 0.85.

## Per-team numbers the console should show

- **Extraction**: claims per document, share rejected by Validation, retry yield
- **Validation**: reject rate per gate, fast-vs-strong disagreement rate
- **Analysis**: signals admitted vs proposed, forecasts withheld by G4
- **Drafting**: retries per section, sections withheld
- **Audit**: violations by check type
- **Evaluation**: recall against SIG/F/R/CU registers of the FETC benchmark

## Order of work

1. `evidence.stage` + `work_items` migration; extract writes `EXTRACTED`.
   Nothing else changes yet — `rules.py` treats `EXTRACTED` as today.
2. Gates 1 and 2 in the Jev layer (`decisions.py`, the decision-layer workstream) move rows
   through `TRIAGED` / `ENTAILED`.
3. Rejection-with-reason retry loop for Extraction.
4. Workers claim from `work_items`, so extraction and validation run N-wide.
5. Collection picks up `research_gaps` as search tasks — the first loop that
   closes back to the start of the pipeline.

Steps 1, 3, 4 and 5 are pipeline work; step 2 is the decision layer.
