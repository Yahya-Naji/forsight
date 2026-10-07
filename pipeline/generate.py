"""STEP 5 — Generator (NEURAL layer, bounded).

The model receives the template instruction and the graph rows linked to one
section — nothing else. It cannot reach the rest of the register, the web, or
its own memory of the subject.

Three disciplines are enforced here rather than hoped for:
  · citations belong on factual claims, never on imperatives;
  · Class C is unproven and must be hedged, Class D marked as proposed;
  · an OPEN gate is stated once and never contradicted.

Every section writes a row to `generation_ledger` recording what was passed and
what was withheld, so "bounded generation" is auditable instead of asserted.

Usage: python generate.py --pillar CYBERSECURITY --title "..."
"""
import argparse
import hashlib
import json
import os
import re
from concurrent import futures

import labels
import llm
import verify
import config
from config import db

CITATION = re.compile(r"\[(EV-[A-Z0-9-]+)\]")
# The reference list must survive a model that drops the brackets.
ANY_EV = re.compile(r"\b(EV-[A-Z0-9-]+)\b")

SECTION_PROMPT = """You draft ONE section of a strategic foresight brief for the
Tawazun Council (UAE). Write ONLY from the JSON data below — no outside
knowledge, no remembered examples, no invented facts.

CITATION RULES
- Cite ONLY ids that appear in the data below. Inventing an id is the worst
  failure this system can produce.
- EVIDENCE is cited in SQUARE BRACKETS, always: [EV-004], [EV-NVD-001].
  Never (EV-004), never a bare EV-004. The brackets are what the reference
  builder and the citation audit read.
- Findings, risks, signals, trends and forecasts are referenced by BARE id —
  F-CS-01, R-CS-02, SIG-CS-03, FC-CS-01 — with no brackets. Every sentence
  about a forecast names its FC- id.
- Where the data below contains no evidence rows, cite findings and risks only.
  Do not write [EV-...] for an evidence row that was not supplied.
- A sentence that recommends, instructs, or proposes an ACTION must carry NO
  evidence citation. An action is a proposal, not a finding; citing evidence on
  an imperative is an error.
- Cite an id only when that row's own claim supports that sentence. Never cite to
  decorate, and never cite an id absent from the data below.
- Refer to signals, risks and findings by bare id (SIG-CS-01, R-CS-01) — brackets
  are for evidence only.

FIGURE RULES
- The data may include a `figures` list: charts, diagrams, timelines and
  screenshots published in the sources, each with an id and a description.
- Cite a figure in BRACKETS exactly like evidence: [FIG-004]. The figure is then
  placed into the report automatically, with its caption and publisher.
- NEVER write an image link, a file name or a URL. You are given descriptions,
  not files, and inventing a path produces a broken image under a real
  publisher's name. The id is the only thing you control.
- Cite a figure only where it shows what the sentence says. A figure is
  illustration OF a claim, not a substitute for one: the sentence still needs its
  own [EV-xxx] citation.
- Do not describe a figure the reader can see. Say what it means.

FORECAST RULES
- Plausibility bands (Likely / Possible / Uncertain / Speculative) are computed
  from corroboration breadth and horizon distance. Report the band in words.
  Never convert one into a percentage, odds or "high probability".
- A Speculative forecast is a watch item. Do not write it as a projection.
- Every forecast is stated with its falsifier in the same paragraph.

EVIDENCE CLASS RULES
- Class A and B may be stated as fact.
- Class C is UNPROVEN and SINGLE-SOURCE. Any sentence resting only on Class C
  must be hedged in its own words — "may", "could", "single-source and unproven",
  "not yet corroborated". Never state Class C as established fact.
- Class D is a proposed construct, not current policy. Say so.

VALIDATION GATES
- If validation_gates lists OPEN gates, state ONCE in a single sentence that the
  blocked claims require customer validation, naming what is blocked.
- Never repeat that statement. Never assert anything a gate blocks, in any wording.

OPENING RULE — enforced automatically; a generic opener is rejected and redrafted
- The first sentence must lead with a CONCRETE FACT from the data: a number, a
  named actor, a named standard or a named system, plus its citation.
- GOOD: "Thirty-six of 176 catalogued intrusion sets reference Middle East, Gulf
  or UAE targeting [EV-001]."
- REJECTED: "Enhanced cybersecurity measures are critical...", "In today's
  landscape...", "It is imperative that...", "Organisations must...".
  If your first sentence would still read sensibly with all the data deleted,
  it is the wrong sentence.

SENTENCE DISCIPLINE — this is what gets sections rejected, so read it twice
Every sentence you write must be ONE of these four kinds. There is no fifth
kind, and a sentence that is none of them will be rejected:
  1. A CITED CLAIM — a fact drawn from the data, carrying the id it came from.
  2. A RECOMMENDATION — an imperative ("Mandate cyber-assurance clauses in
     tier-one contracts"). Starts with a verb. Carries no evidence citation.
  3. A LABELLED CONDITION — "Trigger: ...", "Falsifier: ...", "Watch: ...".
     A condition to monitor, not a claim about the present.
  4. A STATEMENT ABOUT THIS EVIDENCE BASE — "The evidence base does not
     establish a UAE-specific rate", "Two claims are blocked by an open gate".
THE "SO WHAT" LINE — where drafts fail most often
A "So what:" line must do ONE of two things, and boosting is neither:
  · name a CONSEQUENCE that follows from the cited finding, or
  · name the DECISION the reader now faces.
The failure mode is the booster sentence: "X is/are essential/critical/vital to
Y". It asserts an evaluation no row supports, so it is rejected every time.
  REJECTED: "Enhanced supplier assessments are essential to address systemic
            vulnerabilities."  (asserts importance; cites nothing)
  GOOD:     "So what: the exposure sits with tier-two suppliers, who fall
            outside current contractual assurance [EV-014]."
  GOOD:     "So what: Tawazun must decide whether assurance clauses apply at
            contract award or at renewal."
Never write that something is important. Say what follows from it.

THE FIRST SENTENCE UNDER A HEADING CARRIES ITS OWN CITATIONS
The sentence that introduces a point is where drafts fail most often. It is
written as a framing summary — "Threat actors are increasingly leveraging AI to
enhance impersonation" — and it is an assertion about the world with nothing
attached, so it is rejected, even when the three cited sentences below it are
exactly what it summarises. A summary does not inherit the citations of the
sentences under it.
So put the ids on it: "Threat actors are increasingly using AI to enhance
impersonation and phishing [SIG-CS-12; SIG-CS-25]". If a claim summarises several
rows, cite several. If no row supports the summary as written, narrow it until
one does, or delete it and open on the cited specific instead.

COVERAGE — do not confuse concision with omission
Write densely WITHIN each point, and still cover every point the section asks
for. Where the instructions ask for three to five findings or advances, produce
three to five, each with its own action title, its own cited evidence and its
own "So what:" line. One well-cited paragraph is not a section. If the data
supports fewer than the instructions ask for, produce what it supports and say
in one sentence which asked-for element the evidence base does not cover.

Editorial connective tissue is the fifth kind, and it is the reason drafts fail.
  REJECTED: "Proactive assurance measures are crucial to prevent exploitation."
  REJECTED: "Failure to address these vulnerabilities leaves infrastructure
            exposed." (asserts a consequence no row states)
  REJECTED: "The environment is shifting due to emerging dynamics."
  REJECTED: "Enhanced protective measures are needed to mitigate disruption."
Each of those asserts something with no source. Delete the sentence, or convert
it into kind 2 by naming the action you actually mean. Cutting padding is not a
reason to cover less ground — see COVERAGE above.

LABELS
- The data is already written in reader-facing labels. Reproduce them exactly.
  Never write an underscored or all-capitals enum such as STRONG_EMERGING,
  ELECTRONIC_WARFARE or MEDIUM_HIGH.

{brief_block}Section: {title}
Instructions: {instructions}
Data:
{data}

Return clean markdown for the section body only — no heading."""


RETRY_SUFFIX = """

YOUR PREVIOUS DRAFT FAILED VERIFICATION. Fix exactly these problems:
{failures}

READ THE DIRECTION OF EACH PROBLEM. Some ask you to REMOVE or NARROW something —
an uncited claim, a citation whose quote does not support it. Others ask you to
ADD something — more action titles, a figure citation, more cited sentences.
A problem asking for more material is never solved by rewording what is already
there, and never by cutting elsewhere: take the missing items from the data
above. Keep everything that passed.

Cite ONLY evidence ids that appear in the data above. Do not invent ids.

Where a citation is reported as not supporting its sentence, the quote behind
that id does not say what you wrote. Do not swap in a different id and do not
soften the wording — narrow the sentence to what the quote actually states, or
drop the claim.

For each sentence named above, choose one of four exits — do not simply reword it:
  (a) attach the id from the data that actually supports it;
  (b) delete it (usually right — it was connective padding);
  (c) rewrite it as an imperative action, which needs no citation;
  (d) rewrite it as a labelled condition ("Trigger: ...").
A reworded assertion with no source fails again for the same reason."""

# Three checks now act on each draft — unsourced, entailment and citation
# density — and they interact: fixing a citation that does not entail can break
# the density floor, and vice versa. Two attempts was enough for one check and
# withholds well-formed sections under three, so the budget is a flag.
DEFAULT_RETRIES = 3

# Sections whose subject is NOT the world.
#
# "Confirming this would require data on exploitation rates" is a statement
# about what is missing; demanding a citation for it asks the writer to cite an
# absence. The same holds for four other kinds of section, and treating them as
# evidence-bearing withheld seven of twenty-three on the first full run:
#
#   the document itself   purpose, scope, the question the report answers
#   the method            how evidence was tiered, classed and gated
#   what is unknown       the critical uncertainties
#   hypothetical futures  a scenario describes a world that does not exist, so
#                         its paragraphs cannot cite evidence for it
#   decision reasoning    why one decision comes before another
#
# The exemption is not silent: verify.py counts these sentences separately and
# the scorecard reports how many were exempt, so the headline "0 unsourced
# assertions" is still read against a stated denominator.
EPISTEMIC_SECTIONS = {
    "limits", "purpose_scope", "methodology", "question_architecture",
    "uncertainties", "scenarios", "decisions",
    # The stress test reasons over futures that do not exist, and the
    # opportunity register reports that it is empty — both were withheld for
    # describing exactly what they are for.
    "stress_test", "opportunities",
}

BANNED_OPENERS = (
    "enhanced", "in today", "it is imperative", "organisations must",
    "organizations must", "in an era", "as the world", "increasingly",
    "is critical to", "are critical to", "plays a vital role", "in recent years",
)


def opener_failures(markdown: str, section_key: str):
    """The executive summary must open on a fact, not a platitude.

    Instructed in the prompt and enforced here, because instruction alone did
    not hold: the model reliably opened with "Enhanced cybersecurity measures
    are critical..." until this check started rejecting it.
    """
    if section_key != "exec_summary":
        return []
    lines = [l.strip() for l in markdown.splitlines() if l.strip()
             and not l.strip().startswith(("#", "|", "-", "*", ">"))]
    if not lines:
        return []
    first = lines[0]
    low = first.lower()
    out = []
    if any(low.startswith(b) or b in low[:60] for b in BANNED_OPENERS):
        out.append("The opening sentence is generic (\"%s\"). Open with a concrete "
                   "fact from the data — a number, named actor or named standard — "
                   "and cite it." % first[:90])
    if not re.search(r"\d|\[EV-|\bF-[A-Z]{2}-\d|\bR-[A-Z]{2}-\d|\bSIG-[A-Z]{2}-\d", first):
        out.append("The opening sentence contains no specific fact or citation.")
    return out


# One citation per this many assertive sentences, in sections that were given
# evidence to work from.
MIN_SENTENCES_PER_CITATION = 3


def density_failures(body_md: str, sec) -> list:
    """Reject a section that answered a citation problem by deleting citations.

    Adding the entailment check to the generation loop produced exactly the wrong
    adaptation: rather than narrowing a sentence to what its quote supported, the
    model dropped the citation and hedged the sentence. Faithfulness went to
    1.00 while the report fell from thirteen cited sentences to three — a
    strictly worse brief that scored better on every check.

    So citation density has a floor wherever evidence was supplied. A section can
    still say little, but it cannot make claims anonymously.
    """
    inputs = sec.get("inputs") or []
    if "evidence" not in inputs:
        return []                      # actions and similar carry no citations
    sentences = verify.sentences_of(body_md)
    assertive = [x for x in sentences if verify.ASSERTIVE.search(x)]
    # A section HANDED evidence must cite evidence. Counting any object
    # reference let the horizon-scanning section satisfy the floor with ten
    # SIG- ids and zero [EV-] citations, from 63 evidence rows — derived objects
    # are a step further from the source, and the whole claim of this system is
    # that a sentence can be walked back to a quote span.
    cited = [x for x in sentences if ANY_EV.search(x)]
    if len(assertive) < MIN_SENTENCES_PER_CITATION:
        return []
    need = max(1, len(assertive) // MIN_SENTENCES_PER_CITATION)
    if len(cited) >= need:
        return []
    return ["This section carries %d EVIDENCE citation(s) across %d assertive "
            "sentences; it needs at least %d. You were given evidence rows — cite "
            "them as [EV-xxx]. A SIG-, F- or R- id is a derived object, not a "
            "source, and does not satisfy this. Do not answer a citation problem "
            "by removing the citation: cite the evidence that supports the "
            "sentence, narrow the sentence to what a quote states, or cut it."
            % (len(cited), len(assertive), need)]


# The model writes both [FIG-002] and [FIG-002, FIG-005]. Matching only the
# single-id form reported "you cited no figures" at a draft that cited two, and
# then withheld the section for complying — findall over the whole bracket keeps
# both forms working, the way the exporter's evidence pattern already did.
FIG_CITE = re.compile(r"\[\s*(FIG-\d+(?:\s*,\s*FIG-\d+)*)\s*\]")
FIG_ID = re.compile(r"FIG-\d+")


def cited_figures(text: str) -> list:
    """Figure ids in citation brackets, in order, de-duplicated."""
    return list(dict.fromkeys(
        fid for group in FIG_CITE.findall(text) for fid in FIG_ID.findall(group)))
BOLD_TITLE = re.compile(r"^\s*\*\*[^*]{12,}\*\*\s*$", re.M)

# The section stating what it could not cover, which satisfies the floor below.
NAMES_A_GAP = re.compile(
    r"\b(the evidence base does not|no evidence (was|is) (found|available)|"
    r"the data does not (cover|support|establish)|not covered by the evidence|"
    r"no (admitted|cited) evidence (for|on)|could not be established)\b", re.I)
MIN_ACTION_TITLES = 3


def structure_failures(body_md: str, sec, data) -> list:
    """Floors on what a section must contain, not just what it must avoid.

    Every other check in the loop removes things. Under that pressure the model
    converges on a short, safe section: the advances section came back with one
    action title where the template asks for three to five, and cited none of
    the seven figures it was given. A brief that passes every prohibition and
    says almost nothing is not the goal, so the shape the template asks for is
    checked too.
    """
    out = []
    instructions = sec.get("instructions") or ""

    if "ACTION TITLE" in instructions:
        found = len(BOLD_TITLE.findall(body_md))
        # The floor is "meet the count OR name the shortfall". Demanding the count
        # unconditionally pushed the model to stretch citations over advances the
        # evidence does not carry — four entailment failures in one draft — which
        # is the opposite of the intent. A stated gap is an acceptable answer here
        # for the same reason it is everywhere else in this system.
        if found < MIN_ACTION_TITLES and not NAMES_A_GAP.search(body_md):
            out.append("This section has %d bolded action title(s); the template "
                       "asks for at least %d, each stating a conclusion with its "
                       "own cited evidence and one 'So what:' line. Either add the "
                       "missing ones from the data, or state in one sentence which "
                       "area the evidence base does not cover — do not stretch a "
                       "citation to reach the count."
                       % (found, MIN_ACTION_TITLES))
    return out


def figure_notes(body_md: str, data) -> list:
    """Advisory, not blocking.

    Every figure available comes from one vendor report on invoice fraud. In a
    section about post-quantum deadlines there is nothing for it to illustrate,
    and the figure rules say to cite a figure only where it shows what the
    sentence says. Withholding the section for obeying that rule was wrong, so an
    uncited figure is now reported and the draft stands.
    """
    figures = data.get("figures") or []
    if figures and not cited_figures(body_md):
        return ["%d figure(s) available, none cited: %s"
                % (len(figures), ", ".join(f["id"] for f in figures))]
    return []


SECTION_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", ".cache", "sections")


# Bump when a verification check changes. The cache key is the prompt plus this,
# because a stricter check must not be satisfied by a draft that was only ever
# judged against the looser one.
CHECKS_VERSION = "2"


def _cache_key(prompt: str) -> str:
    return hashlib.sha256((CHECKS_VERSION + "\x00" + prompt).encode("utf-8")).hexdigest()[:32]


def cache_get(prompt: str):
    path = os.path.join(SECTION_CACHE, _cache_key(prompt) + ".json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def cache_put(prompt: str, result: dict) -> None:
    """Keyed on the whole prompt, so any change to the data or the template
    misses the cache. Identical inputs therefore reproduce the same section."""
    try:
        os.makedirs(SECTION_CACHE, exist_ok=True)
        with open(os.path.join(SECTION_CACHE, _cache_key(prompt) + ".json"),
                  "w", encoding="utf-8") as fh:
            json.dump(result, fh)
    except OSError:
        pass                       # a cache that cannot be written is not fatal


def _dedupe_gates(rows):
    """Four identical gates printed in a row reads as a broken template. One
    entry per distinct blocked claim, with the ids it covers."""
    seen = {}
    for g in rows:
        seen.setdefault(g["blocks"], []).append(g["id"])
    return [{"gate_ids": ids, "blocks": blocks} for blocks, ids in seen.items()]


def load_brief(sb, brief_id):
    rows = sb.table("report_briefs").select("*").eq("id", brief_id).execute().data
    if not rows:
        raise SystemExit("brief %s not found" % brief_id)
    return rows[0]


STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "their",
        "risk", "risks", "uae", "defence", "defense"}

# Below this many genuinely matching rows, the graph does not hold the subject
# the brief asked about and the section is blocked rather than filled with the
# nearest thing available.
MIN_ON_TOPIC = 3


def _relevant(rows, terms, fields=("claim", "statement", "question", "name"),
              keep_at_least=6):
    """Rows scored against the brief's focus terms.

    Matching whole phrases fails: a brief asks about "cyber-assurance clauses"
    and no source sentence contains that string. Terms are broken into their
    significant words and rows are scored by how many distinct ones they carry,
    so a row touching several parts of the brief outranks one that clips a
    single common word.

    Dropped rows are counted in the ledger rather than vanishing, and a filter
    that would empty the section keeps the highest-scoring rows instead — an
    empty section is worse than a loosely scoped one.
    """
    if not terms:
        return rows, 0
    tokens = {w for t in terms for w in str(t).lower().replace("-", " ").split()
              if len(w) > 3 and w not in STOP}
    if not tokens:
        return rows, 0

    scored = []
    for r in rows:
        blob = " ".join(str(r.get(f) or "") for f in fields).lower()
        scored.append((sum(1 for w in tokens if w in blob), r))
    hits = [r for n, r in scored if n > 0]

    # A brief whose subject the graph does not hold must be REFUSED, not
    # back-filled. Keeping the highest-scoring rows is right when a brief sits
    # slightly off its evidence; it is wrong when almost nothing matches, and it
    # produced a Counter-UAS report written entirely from the cybersecurity
    # graph — no jamming, no interceptors, no sensors, under a Counter-UAS
    # heading. Substituting evidence is worse than having none, because the
    # reader cannot see it happened.
    if len(hits) < keep_at_least:
        matched = len(hits)
        if matched < MIN_ON_TOPIC:
            return [], len(rows)          # caller turns this into a refusal
        scored.sort(key=lambda x: -x[0])
        hits = [r for _, r in scored[:keep_at_least]]
    return hits, len(rows) - len(hits)


def _linked_ids(sb, section_key):
    """Rows explicitly linked to this section, if any links exist."""
    rows = (sb.table("links").select("to_id,to_type")
            .eq("from_id", section_key).eq("from_type", "report_section")
            .execute().data)
    return {r["to_id"] for r in rows}


def fetch_inputs(sb, pillar, wanted, section_key, brief=None):
    """Return (data, ledger). Section-scoped when links exist, and honest in the
    ledger when they do not — the previous version passed every pillar row to
    every section while claiming to be bounded."""
    scope = _linked_ids(sb, section_key)
    scoped = bool(scope)
    terms = (brief or {}).get("focus_terms") or []
    data, passed, withheld, off_topic = {}, {}, {}, []

    def take(key, rows, has_id=True):
        available = len(rows)
        if scoped and has_id:
            rows = [r for r in rows if r.get("id") in scope]
        # With a brief, rows unrelated to what was asked for are withheld —
        # which is what finally makes the ledger's withheld count meaningful.
        if terms and key in ("evidence", "signals", "findings", "risks",
                             "forecasts", "uncertainties"):
            rows, _ = _relevant(rows, terms)
        if terms and not rows and available:
            off_topic.append(key)
        data[key] = rows
        passed[key] = len(rows)
        # One subtraction, counted once. Adding the scope drop and the relevance
        # drop separately reported more rows withheld than were ever available.
        if available > len(rows):
            withheld[key] = available - len(rows)

    pillars = (brief or {}).get("pillars") or [pillar]

    def rows_for(table, cols):
        q = sb.table(table).select(cols)
        if table == "evidence":             # archived rows are out of scope
            q = q.is_("archived_at", "null")
        return (q.in_("pillar", pillars) if len(pillars) > 1
                else q.eq("pillar", pillars[0])).execute().data

    if "evidence" in wanted:
        take("evidence", rows_for("evidence",
             "id,claim,class,confidence,env_layer,quote_span"))
    if "signals" in wanted:
        take("signals", rows_for("signals", "*"))
    if "findings" in wanted:
        take("findings", rows_for("findings", "*"))
    if "uncertainties" in wanted:
        take("uncertainties", rows_for("uncertainties", "id,question,why_it_matters"))
    if "risks" in wanted:
        take("risks", sb.table("risks").select("*").execute().data)
    if "forecasts" in wanted:
        take("forecasts", sorted(rows_for("forecasts",
             "id,statement,horizon,env_layer,plausibility,confidence,"
             "falsifier,assumptions,rationale,basis"),
             key=lambda r: r.get("horizon") or ""))
    if "indicators" in wanted:
        rows = sb.table("indicators").select("*").execute().data
        # An indicator with no threshold cannot be monitored; rendering "TBD"
        # in a leadership brief presents a gap as if it were a control.
        usable = [r for r in rows if (r.get("threshold") or "").strip()
                  and (r.get("threshold") or "").strip().upper() not in ("TBD", "N/A", "-")]
        for r in rows:
            if r not in usable:
                sb.table("research_gaps").insert({
                    "pillar": pillar,
                    "gap": f"Indicator {r['id']} has no concrete threshold and was "
                           f"omitted from the report: {r.get('watch', '')[:180]}",
                    "raised_by": "generate.indicator_threshold"}).execute()
        take("indicators", usable)
        if len(rows) - len(usable):
            withheld["indicators"] = len(rows) - len(usable)
    if "figures" in wanted:
        # Only what rules.py admitted and reachability confirmed. The model is
        # given the description, never the URL — see embed_figures.
        figs = [f for f in rows_for("figures",
                "id,kind,describes,caption,document_id,informative,reachable")
                if f.get("informative") and f.get("reachable")]
        for f in figs:
            f.pop("informative", None)
            f.pop("reachable", None)
        take("figures", figs)
    # ---- the back half of the methodology (report §9-§21) ------------------
    # These are global rather than per-pillar in the schema, so they are taken
    # whole; the relevance filter still scopes them against a brief.
    if "trends" in wanted:
        take("trends", rows_for("trends", "id,name,statement,direction,horizon"))
    if "drivers" in wanted:
        take("drivers", rows_for("drivers", "id,name,description"))
    if "cross_impacts" in wanted:
        take("cross_impacts", sb.table("cross_impacts")
             .select("id,from_trend,to_trend,statement,severity").execute().data)
    if "scenarios" in wanted:
        scen = sb.table("scenarios").select(
            "id,name,one_sentence,dimensions,horizon").order("id").execute().data
        for sc in scen:
            sc["driven_by"] = [r["uncertainty_id"] for r in
                               sb.table("scenario_uncertainties").select("uncertainty_id")
                               .eq("scenario_id", sc["id"]).execute().data]
        take("scenarios", scen)
    if "implications" in wanted:
        take("implications", rows_for("implications", "id,actor,statement,finding_id"))
    if "opportunities" in wanted:
        take("opportunities", rows_for("opportunities",
             "id,statement,attractiveness,feasibility,score"))
    if "options" in wanted:
        take("options", sb.table("options")
             .select("id,name,description,is_working_hypothesis").order("id").execute().data)
    if "stress_tests" in wanted:
        take("stress_tests", sb.table("stress_tests")
             .select("option_id,scenario_id,result,note").execute().data, has_id=False)
    if "initiatives" in wanted:
        take("initiatives", sb.table("initiatives")
             .select("id,name,objective,class,owner,horizon").order("id").execute().data)
    if "actions_planned" in wanted:
        take("actions_planned", sb.table("actions")
             .select("id,initiative_id,statement,owner,horizon,sequence")
             .order("sequence").execute().data)
    if "decisions" in wanted:
        take("decisions", sb.table("decision_requirements")
             .select("id,title,decision,why_first,data_needed,priority")
             .order("priority").execute().data)
    if "questions" in wanted:
        take("questions", rows_for("questions", "id,text,stage,topic_id"))
    if "topics" in wanted:
        take("topics", rows_for("topics", "id,name,description"))
    if "sources" in wanted:
        take("sources", sb.table("source_registry")
             .select("id,tier,publisher,method,notes").order("id").execute().data)
    if "gaps" in wanted:
        take("gaps", rows_for("research_gaps", "id,gap,raised_by"), has_id=False)

    if "links" in wanted:
        take("links", sb.table("links").select("*").execute().data, has_id=False)
    if "gates" in wanted:
        gates = sb.table("validation_gates").select("*").eq("status", "OPEN").execute().data
        # A cybersecurity brief has no business quoting the procurement gate.
        mine = [g for g in gates if pillar in (g.get("blocks") or "")
                or g["id"].startswith(f"VG-{pillar[:2]}-")]
        data["validation_gates"] = _dedupe_gates(mine)
        passed["gates"] = len(data["validation_gates"])
        if len(gates) - len(mine):
            withheld["gates"] = len(gates) - len(mine)

    return data, {"scoped": scoped, "passed": passed, "withheld": withheld,
                  "off_topic": off_topic}


def embed_figures(sb, markdown: str, pillars):
    """Replace figure citations with the figure, rendered from the database.

    The model cites [FIG-004]; it is never shown the file URL and never writes
    one. An invented URL would render as a broken image carrying a real
    publisher's name, which is worse than a missing figure — so the id is the
    only thing the model controls, and this resolves it.

    Returns (markdown, ids_rendered).
    """
    cited = set(cited_figures(markdown))
    if not cited:
        return markdown, []

    rows = {r["id"]: r for r in sb.table("figures")
            .select("id,url,kind,describes,caption,credit,document_id,"
                    "informative,reachable").in_("id", sorted(cited)).execute().data}
    pubs = {r["id"]: r["publisher"] for r in
            sb.table("source_registry").select("id,publisher").execute().data}

    out, rendered = [], []
    for para in markdown.split("\n\n"):
        out.append(para)
        for fid in cited_figures(para):
            row = rows.get(fid)
            # Refused or unreachable figures never reach here — load_graph keeps
            # them out of the graph, so citing one fails verification first.
            if not row or not row.get("informative") or not row.get("reachable"):
                continue
            doc = sb.table("documents").select("title,url,published_on,registry_id") \
                    .eq("id", row["document_id"]).execute().data
            doc = doc[0] if doc else {}
            pub = pubs.get(doc.get("registry_id") or "", "")
            date = (" %s" % doc["published_on"]) if doc.get("published_on") else ""
            caption = (row.get("caption") or row.get("describes") or "").strip().rstrip(".")
            alt = (row.get("describes") or caption or fid).replace("]", ")")
            credit = " — ".join(x for x in [pub + date, row.get("credit") or ""] if x.strip())
            out.append("![%s](%s)" % (alt[:300], row["url"]))
            out.append("*%s — %s. %s* <%s>" % (fid, caption[:300], credit, doc.get("url", "")))
            rendered.append(fid)
    return "\n\n".join(out), rendered


def build_references(sb, pillar, cited=None):
    """One entry per DOCUMENT, listing every evidence id drawn from it.

    Keyed by evidence id, a single article appeared four times as four near
    identical lines. A reference list names sources, not rows.
    """
    by_doc = {}
    for ev in sb.table("evidence").select("id").eq("pillar", pillar).order("id").execute().data:
        if cited is not None and ev["id"] not in cited:
            continue
        srcs = (sb.table("evidence_sources")
                .select("documents(title,url,published_on,registry_id)")
                .eq("evidence_id", ev["id"]).execute().data)
        for s in srcs:
            d = s["documents"]
            rec = by_doc.setdefault(d["url"], {"doc": d, "ids": []})
            if ev["id"] not in rec["ids"]:
                rec["ids"].append(ev["id"])

    pubs = {r["id"]: r["publisher"] for r in
            sb.table("source_registry").select("id,publisher").execute().data}
    lines = []
    for url, rec in sorted(by_doc.items(), key=lambda kv: min(kv[1]["ids"])):
        d = rec["doc"]
        ids = ", ".join(sorted(rec["ids"]))
        pub = pubs.get(d.get("registry_id") or "", "")
        date = f", {d['published_on']}" if d.get("published_on") else ""
        lines.append(f"[{ids}] {d['title']} — {pub}{date}. {url}")
    return "\n\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--pillar", help="required unless --brief supplies pillars")
    ap.add_argument("--title")
    ap.add_argument("--template", default="TPL-BRIEF-01")
    ap.add_argument("--brief", help="report_briefs id — generate against a reader's brief")
    ap.add_argument("--workers", type=int, default=3,
                    help="sections drafted concurrently (they are independent)")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore cached section drafts and redraft everything")
    ap.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                    help="redraft attempts per section before withholding it")
    ap.add_argument("--no-entail", action="store_true",
                    help="skip the in-loop entailment check (faster, publishes "
                         "over-attributed citations the final audit will catch)")
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="generate", status="RUNNING")
    sb = db()
    if not a.pillar and not a.brief:
        ap.error("--pillar is required unless --brief supplies one")
    if not a.title and not a.brief:
        ap.error("--title is required unless --brief supplies one")
    max_retries = a.retries
    tpl = sb.table("report_templates").select("*").eq("id", a.template).execute().data[0]

    brief = load_brief(sb, a.brief) if a.brief else None
    if brief:
        pillars = brief.get("pillars") or [a.pillar]
        brief_block = (
            "THE READER'S BRIEF — everything you write serves this:\n"
            "  Question: %s\n  Decision it supports: %s\n  Audience: %s\n"
            "  In scope: %s\n  Out of scope: %s\n\n"
            % (brief.get("goal") or "—", brief.get("decision") or "—",
               brief.get("audience") or "—", brief.get("in_scope") or "—",
               brief.get("out_of_scope") or "—"))
        print("brief: %s" % (brief.get("title") or brief["id"]))
        print("  focus: %s" % ", ".join(brief.get("focus_terms") or []) or "—")
    else:
        pillars = [a.pillar]
        brief_block = ""

    graph = verify.load_graph(sb, pillars)
    title = a.title or (brief or {}).get("title") or "Strategic brief"

    # ---- phase 1: gather inputs and build prompts --------------------------
    # Every database read happens here, on one thread, so phase 2 can run wide
    # without sharing a Supabase client across threads.
    jobs = []
    for sec in tpl["sections"]:
        if sec["key"] == "references":
            continue
        data, ledger = fetch_inputs(sb, pillars[0], sec["inputs"], sec["key"], brief)
        # Raw enums never reach the model, so they cannot reach the page.
        payload = json.dumps(labels.humanise(data), default=str, indent=1)
        if len(payload) > 120000:
            raise SystemExit(
                f"section {sec['key']}: {len(payload)} chars of input exceeds the "
                "context budget. Link rows to sections rather than truncating — "
                "silent truncation would drop evidence without telling anyone.")
        base = SECTION_PROMPT.format(
            title=sec["title"], instructions=sec["instructions"], data=payload,
            brief_block=brief_block)
        jobs.append({"sec": sec, "data": data, "ledger": ledger,
                     "payload": payload, "base": base,
                     "off_topic": ledger.get("off_topic") or []})

    # ---- phase 2: draft and verify, concurrently ---------------------------
    # Sections are independent — only the reference list depends on the others,
    # and that is assembled mechanically afterwards. Run sequentially, seven
    # sections at up to six attempts of two model calls each is ~80 round trips
    # in series, which made a single report a twenty-minute wait.
    def run_section(job):
        try:
            return _draft_section(job)
        except Exception as exc:
            # One section failing must not discard the six that succeeded. A
            # dropped connection used to abort the whole report after twenty
            # minutes of work; now the section is withheld and named, and the
            # rest of the brief still assembles.
            return {"body": "", "failures": ["Drafting failed: %s" % str(exc)[:200]],
                    "attempt": 0, "notes": [],
                    "log": ["  ✗ %s: drafting failed — %s"
                            % (job["sec"]["key"], str(exc)[:110])]}

    def _draft_section(job):
        sec, data = job["sec"], job["data"]
        if job["off_topic"]:
            # Named, not silent: the reader sees which inputs the brief's subject
            # found no evidence for.
            miss = ", ".join(job["off_topic"])
            return {"body": "", "attempt": 0, "notes": [],
                    "failures": ["The evidence base does not cover this brief's "
                                 "subject for: %s. Section blocked rather than "
                                 "written from unrelated rows." % miss],
                    "log": ["  ⊘ %s: no on-topic %s — section blocked"
                            % (sec["key"], miss)]}
        base, log = job["base"], []
        cached = cache_get(base) if not a.fresh else None
        if cached:
            log.append("  ⤿ %s: reusing the passed draft from an earlier run" % sec["key"])
            return dict(cached, log=log, notes=[])

        body_md, failures, attempt = "", [], 0
        notes = []
        while attempt <= max_retries:
            prompt = base if not failures else base + RETRY_SUFFIX.format(
                failures="\n".join("- " + f for f in failures))
            body_md = llm.text(prompt, effort="high", max_output_tokens=8000)
            failures = (verify.check_section(
                            body_md, graph,
                            allow_unsourced=sec["key"] in EPISTEMIC_SECTIONS,
                            entail=not a.no_entail)
                        + opener_failures(body_md, sec["key"])
                        + density_failures(body_md, sec)
                        + structure_failures(body_md, sec, data))
            notes = figure_notes(body_md, data)
            if not failures:
                break
            attempt += 1
            if attempt <= max_retries:
                log.append("  ! %s: %d verification failure(s), retry %d/%d"
                           % (sec["key"], len(failures), attempt, max_retries))
                for f in failures[:3]:
                    log.append("      %s" % f[:110])

        result = {"body": body_md, "failures": failures, "attempt": attempt}
        if not failures:
            # Only passed drafts are cached. Caching a failed one would skip the
            # retries that were supposed to fix it — and a dropped connection
            # part-way through used to throw away every section already done.
            cache_put(base, result)
        return dict(result, log=log, notes=notes)

    workers = max(1, min(a.workers, len(jobs)))
    print("drafting %d sections, %d at a time\n" % (len(jobs), workers))
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run_section, jobs))   # order preserved

    # ---- phase 3: assemble in template order ------------------------------
    parts = [f"# {title}\n"]
    ledgers = []
    done = {job["sec"]["key"]: (job, res) for job, res in zip(jobs, results)}
    for sec in tpl["sections"]:
        if sec["key"] == "references":
            cited = {c for led in ledgers for c in led["citations"]}
            refs = "\n\n".join(build_references(sb, p, cited) for p in pillars)
            parts.append(f"## {sec['title']}\n\n{refs}")
            continue

        job, res = done[sec["key"]]
        ledger, payload = job["ledger"], job["payload"]
        body_md, failures, attempt = res["body"], res["failures"], res["attempt"]
        for line in res["log"]:
            print(line)
        for note in res["notes"]:
            print("      note: %s" % note[:110])

        withheld_section = bool(failures)
        if withheld_section:
            openers = verify.unmatched_openers(verify.sentences_of(body_md))
            # Better a visible hole than a plausible paragraph on a citation
            # that does not exist.
            body_md = ("_Section withheld: failed verification after "
                       f"{max_retries} retries (see generation ledger)._")
            print(f"  ✗ {sec['key']}: WITHHELD after {max_retries} retries")
            # Name the words that defeated the imperative check. A recommendation
            # rejected for opening on a verb the list does not know is a gap in
            # verify.py, not a defect in the draft, and it should be readable.
            if openers:
                print("      unmatched sentence openers: %s" % ", ".join(openers[:12]))

        parts.append(f"## {sec['title']}\n\n{body_md}")
        ledger.update({"key": sec["key"], "title": sec["title"],
                       "inputs": sec["inputs"], "instructions": sec["instructions"],
                       "chars": len(payload), "retries": attempt,
                       "section_withheld": withheld_section, "failures": failures,
                       "citations": sorted(set(ANY_EV.findall(body_md)))})
        ledgers.append(ledger)
        flag = "WITHHELD" if withheld_section else ("scoped" if ledger["scoped"] else "UNSCOPED")
        if ledger["withheld"]:
            flag += " −%d" % sum(ledger["withheld"].values())
        print(f"drafted: {sec['title']:<38} {ledger['passed']} {flag}"
              + (f" (retries {attempt})" if attempt else ""))

    body = "\n\n".join(parts)
    body, figs_rendered = embed_figures(sb, body, pillars)
    if figs_rendered:
        print("figures rendered: %s" % ", ".join(dict.fromkeys(figs_rendered)))
    gates_open = sb.table("validation_gates").select("id").eq("status", "OPEN").execute().data
    status = "GATES_OPEN" if gates_open else "DRAFT"
    rep = sb.table("reports").insert({
        "template_id": a.template, "pillar": pillars[0], "title": title,
        "status": status, "body_md": body,
        "brief_id": brief["id"] if brief else None}).execute().data[0]
    if brief:
        sb.table("report_briefs").update({"status": "USED"}).eq("id", brief["id"]).execute()

    for led in ledgers:
        sb.table("generation_ledger").insert({
            "report_id": rep["id"], "section_key": led["key"],
            "section_title": led["title"], "inputs_declared": led["inputs"],
            "rows_passed": led["passed"], "rows_withheld": led["withheld"],
            # `withheld` is the per-input row counts; `section_withheld` is the
            # verification verdict. They shared a key and the flag won, which is
            # why rows_withheld was false on every row ever written.
            "scoped": led["scoped"], "instructions": led["instructions"],
            "citations_emitted": led["citations"], "chars_sent": led["chars"],
            "retries": led["retries"], "withheld": led["section_withheld"],
            "failures": led["failures"]}).execute()

    config.update_run(getattr(a, "run_id", None), report_id=rep["id"],
                      counts={"generate": len([l for l in ledgers
                                               if not l.get("section_withheld")])})
    print(f"\nreport {rep['id']} saved (status={status}, {len(body)} chars, "
          f"{len(ledgers)} ledger rows)")


if __name__ == "__main__":
    main()
