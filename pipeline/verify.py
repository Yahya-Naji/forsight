"""STEP 6 — Verifier: checks a generated report AGAINST the graph it came from.

This is the step that turns "the model cited EV-004" into "EV-004 exists, is
Class A, belongs to this pillar, and its quote span actually supports the
sentence that cited it".

Four checks run deterministically in Python — no model involved, so they cannot
themselves hallucinate:

  1. CITATION     every [EV-xxx] / [SIG-xx] / [R-xx] resolves to a real row of
                  the right pillar
  2. UNSOURCED    no sentence asserts a fact with no citation
  3. CLASS        Class C evidence is hedged; Class D is marked as a proposed
                  construct rather than current policy
  4. GATE         nothing asserts what an OPEN validation gate blocks

The fifth is the expensive one and is the only place a model is used:

  5. ENTAILMENT   does the cited evidence's quote span actually support the
                  sentence? (the faithfulness gap: a claim can be true, and its
                  citation still not support it)

Exits non-zero when violations are found, so it can gate a release.

  python verify.py --report <uuid>
  python verify.py --report <uuid> --json violations.json --skip-entailment
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

import llm
import config
from config import db

CITATION = re.compile(
    r"\[(EV-[A-Z0-9-]+|SIG-[A-Z0-9-]+|R-[A-Z0-9-]+|F-[A-Z0-9-]+|FIG-[A-Z0-9-]+)\]")

# Sections that receive findings and risks rather than evidence cite them by
# bare id (F-CS-01, R-CS-02). That is sourcing too — demanding [EV-xxx] where no
# evidence row was supplied is what drove the model to invent ids.
OBJECT_REF = re.compile(
    r"\b(EV-[A-Z0-9-]+|SIG-[A-Z]{2}-\d+|F-[A-Z]{2}-\d+|R-[A-Z]{2}-\d+"
    r"|TR-[A-Z]{2}-\d+|CU-[A-Z]{2}-\d+|FC-[A-Z]{2}-\d+|FIG-\d+"
    # The back half of the methodology (report §9-§21). Without these an
    # object type the pipeline admitted by rule reads as an uncited
    # assertion: "Option OPT-A is fragile under S2" was scored as a bare
    # claim, and eleven sections were withheld for citing the graph.
    r"|S\d{1,2}|OPT-[A-Z]|IMP-[A-Z]{3}-\d+|DRV-\d+|CI-\d+"
    r"|INIT-\d+|ACT-\d+|PDC-\d+|IND-[A-Z]{2}-\d+|O\d{1,2}"
    r"|[A-Z]{2}-T\d+|[A-Z]{2}-\d{2})\b")

# A sentence that states a fact but carries no citation. Headings, table rows,
# list scaffolding and hedged/meta sentences are not assertions.
SKIP_PREFIXES = ("#", "|", "---", ">", "*Status", "Customer Validation")

# A line that is nothing but bold text is an action title — the consulting
# template's heading device. Scoring it as a claim asks the writer to cite a
# heading, which is why the findings section was withheld for being well-formed.
BOLD_HEADING = re.compile(r"^\*\*[^*]+\*\*:?$")

# Labels the template puts in front of content. They must come off before the
# sentence is judged, or "So what: Ensure suppliers ..." reads as an assertion
# beginning with the word "So" rather than as the imperative it is.
# Labels that introduce a condition to watch rather than a present claim.
# "Trigger: observed increase in supplier gaps" states what would prompt
# action; it asserts nothing yet, so there is nothing to cite.
CONDITION_LABEL = re.compile(
    r"^\*{0,2}(trigger|watch|falsifier|indicator|threshold|"
    r"what would refute this)\*{0,2}\s*[:\u2014-]", re.I)

# Ordered list markers. "4. **Enhance readiness**: Address the gap" is an
# action item; without stripping the "4. " the bold label survives and the
# sentence reads as an assertion instead of the imperative it is.
LIST_NUMBER = re.compile(r"^\d+[.)]\s+")

# Any short bold run followed by a colon is a label, whatever the word is.
# Enumerating labels meant "**Revisit**:" failed while "**Trigger**:" passed,
# which is a distinction the reader cannot see and the writer cannot guess.
BOLD_LABEL = re.compile(r"^\*\*[^*]{1,60}\*\*\s*:\s*")

LABEL = re.compile(
    r"^\*{0,2}(so what|trigger|implication|implications|action|owner|why|"
    r"bottom line|recommendation|watch|horizon|confidence|falsifier|"
    r"what would refute this|next step)\*{0,2}\s*[:\u2014-]\s*", re.I)

# Sentences about the report and its evidence base rather than about the world.
# "Two claims are blocked by an open gate" describes this document; there is no
# external source to cite for it, and demanding one withholds the honesty.
# Both halves must be present: something that names this document or its
# evidence base, AND a predicate about coverage. "This report shows attackers
# breached the portal" names the document but asserts a fact about the world,
# so it stays subject to citation.
META_SUBJECT = re.compile(
    r"\b(this (report|brief|section|assessment)|the (evidence base|evidence)|"
    r"blocked claims?|open gates?|validation gates?|research gaps?|"
    r"these (claims|findings))\b", re.I)
META_PREDICATE = re.compile(
    r"\b(excluded|withheld|blocked|omitted|unverified|insufficient|"
    r"does not (support|establish|extend|cover)|do not (support|establish)|"
    r"cannot be (confirmed|verified|established)|could not be established|"
    r"not established|requires? (customer )?validation|"
    r"no (uae-specific |direct )?evidence)\b", re.I)


# A sentence that opens on a condition asserts nothing about the present:
# "If vulnerabilities prove incapable of contractual mitigation" states when to
# act, not that anything has happened. Narrow by design — the opener must be the
# first word, so a claim cannot hide behind a conditional clause mid-sentence.
# A discourse marker in front of a conditional does not make it an assertion:
# "However, if migration slips, the exposure falls on X" is still a conditional,
# and it was being rejected for the comma.
DISCOURSE = r"(?:however|conversely|moreover|furthermore|yet|but|thus|therefore|"\
            r"equally|by contrast|on the other hand|that said)[,:]?\s+"
CONDITIONAL_OPENER = re.compile(
    r"^(?:" + DISCOURSE + r")?"
    r"(if|should|unless|were\s+\w+\s+to|in the event|absent|"
    r"provided that|so long as)\b", re.I)


# A falsifier states what would refute a forecast. Every forecast in this system
# is required to carry one, so the report is required to state them — and a
# statement of what would refute a claim asserts nothing about the present. The
# labelled form ("Falsifier: ...") was already handled; this is the prose form
# the model writes when the falsifier is folded into a paragraph.
# The copula must follow immediately. Matching "the falsifier" alone exempted
# "The falsifier was triggered and two UAE primes were breached last quarter" —
# a sentence that names a falsifier and then asserts a breach.
FALSIFIER_CLAUSE = re.compile(
    r"^(the |its )?(falsifier|falsifying (observation|evidence)|refuting "
    r"(observation|evidence)|disconfirming (observation|evidence))\s*"
    r"(is|are|would be|:|\u2014|-)\s"
    r"|^what would (refute|falsify|disconfirm)\b"
    r"|\bwould (refute|falsify|disconfirm) (this|it|the forecast)\b", re.I)


def is_condition(sentence: str) -> bool:
    stripped = sentence.strip()
    return bool(CONDITIONAL_OPENER.match(stripped)
                or FALSIFIER_CLAUSE.search(stripped))


def is_meta_claim(sentence: str) -> bool:
    return bool(META_SUBJECT.search(sentence) and META_PREDICATE.search(sentence))

HEDGES = ("forecast", "speculative", "outlook", "projected", "projection",
          "may", "might", "could", "unproven", "single-source", "not confirmed",
          "cannot be confirmed", "uncertain", "pending", "requires validation",
          "suggests", "indicates", "appears", "potential", "possible",
          "working view", "hypothesis", "not yet")

CONSTRUCT_MARKERS = ("proposed", "for consideration", "not current", "class d",
                     "candidate", "option")

# Words that make a sentence a factual assertion rather than framing.
ASSERTIVE = re.compile(
    r"\b(is|are|was|were|has|have|had|shows?|showed|demonstrat(?:es?|ed)|"
    r"confirms?|confirmed|proves?|proved|increas(?:es?|ed)|decreas(?:es?|ed)|"
    r"reduc(?:es?|ed)|requires?|required|creat(?:es?|ed)|caus(?:es?|ed)|"
    r"operates?|operated|target(?:s|ed)|breach(?:es|ed)|compromis(?:es?|ed)|"
    r"exploit(?:s|ed)|deploys?|deployed|maintains?|maintained|holds?|held|"
    r"grew|rose|fell|reached|remains?|remained|accounts? for|"
    r"led to|resulted in)\b", re.I)

# Recommendations are proposals, not claims about the world, so they carry no
# evidence citation by design — the generator is explicitly instructed not to
# cite them. Flagging them as "unsourced facts" would make the Actions section
# impossible to write and would withhold it every time.
IMPERATIVE_VERBS = (
    "establish", "develop", "monitor", "review", "validate", "implement",
    "require", "strengthen", "refine", "prioritise", "prioritize", "define",
    "maintain", "expand", "adopt", "introduce", "commission", "assess",
    "ensure", "conduct", "create", "build", "run", "track", "acquire",
    "mandate", "negotiate", "publish", "fund", "pilot", "procure",
    # A closed verb list quietly withholds sections for using a synonym: the
    # actions section was rejected for "Launch supplier training programmes".
    "launch", "enforce", "embed", "extend", "integrate", "align", "audit",
    "map", "baseline", "formalise", "formalize", "standardise", "standardize",
    "designate", "assign", "appoint", "convene", "task", "instruct", "direct",
    "issue", "revise", "update", "tighten", "restrict", "verify", "test",
    "exercise", "rehearse", "resource", "staff", "invest", "allocate",
    "escalate", "report", "record", "document", "share", "brief", "consult",
    "engage", "contract", "certify", "accredit", "qualify", "screen", "vet",
    "segment", "isolate", "patch", "harden", "instrument", "log", "add",
    "apply", "set", "raise", "reduce", "limit", "cap", "phase", "retire",
    "replace", "migrate", "consolidate", "centralise", "centralize",
    # Third round of the same failure: a section of well-formed recommendations
    # was withheld for opening on "Finalize", "Investigate" and "Reassess". The
    # list is curated rather than inferred because the alternative — guessing
    # whether a capitalised word is a verb — risks exempting real claims, which
    # is the failure that matters. So it is long, and `unmatched_openers` below
    # makes the next gap visible instead of silent.
    "finalise", "finalize", "investigate", "reassess", "revalidate", "recertify",
    "encourage", "decide", "determine", "select", "choose", "approve", "reject",
    "authorise", "authorize", "delegate", "empower", "mandate", "oblige",
    "stipulate", "specify", "codify", "publish", "circulate", "disseminate",
    "communicate", "notify", "alert", "warn", "flag", "surface", "quantify",
    "measure", "benchmark", "compare", "evaluate", "appraise", "inspect",
    "sample", "survey", "interview", "consult", "coordinate", "synchronise",
    "synchronize", "harmonise", "harmonize", "reconcile", "clarify", "confirm",
    "challenge", "contest", "renegotiate", "amend", "extend", "renew",
    "terminate", "suspend", "withhold", "release", "transition", "modernise",
    "modernize", "upgrade", "refresh", "rotate", "revoke", "decommission",
    "sunset", "ringfence", "prioritise", "sequence", "stage", "schedule",
    "budget", "cost", "model", "simulate", "wargame", "stress-test", "pen-test",
    "red-team", "tabletop", "drill", "train", "upskill", "certify", "license",
    "onboard", "offboard", "inventory", "catalogue", "catalog", "classify",
    "tag", "label", "encrypt", "sign", "authenticate", "authorise-access",
    "segregate", "compartmentalise", "compartmentalize", "monitor-for",
    "instrument-for", "subscribe", "procure-through", "contract-for",
    "require-of", "hold", "press", "push", "seek", "obtain", "secure",
    "establish-with", "embed-in", "build-out", "scale", "pilot-test",
)
_LIST_PREFIX = re.compile(r"^(\d+[\.\)]\s*|[-*+]\s*)?(\*\*)?\s*")
MODAL_RECOMMENDATION = re.compile(
    r"\b(should|must|ought to|recommend(s|ed)?|is recommended)\b", re.I)


def is_recommendation(sentence: str) -> bool:
    """True for imperatives and modal recommendations."""
    stripped = _LIST_PREFIX.sub("", sentence.strip())
    first = re.split(r"[\s,:]+", stripped.lower(), 1)[0].strip("*_")
    if first in IMPERATIVE_VERBS:
        return True
    return bool(MODAL_RECOMMENDATION.search(sentence))


class Violation(BaseModel):
    check: str
    severity: str                 # BLOCKER | WARNING
    sentence: str
    detail: str


class EntailmentVerdict(BaseModel):
    index: int
    supported: bool
    reason: str = Field(max_length=300)


class EntailmentBatch(BaseModel):
    verdicts: List[EntailmentVerdict] = Field(default_factory=list)


# --------------------------------------------------------------------------
# text handling
# --------------------------------------------------------------------------
def sentences_of(markdown: str) -> List[str]:
    """Split the body into candidate assertions, skipping markdown scaffolding.

    The References section is excluded: a bibliography line is a pointer, not a
    claim, and scoring "[EV-002] Title — URL" for entailment against its own
    quote span produces guaranteed false failures that swamp the real ones.
    """
    out = []
    in_refs = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            in_refs = "reference" in stripped.lower()
        if in_refs or not stripped or stripped.startswith(SKIP_PREFIXES):
            continue
        if "http://" in stripped or "https://" in stripped:
            continue                       # reference-style line outside the section
        stripped = LIST_NUMBER.sub("", re.sub(r"^[-*+]\s+", "", stripped))
        if BOLD_HEADING.match(stripped):
            continue
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z\[])", stripped):
            part = part.strip()
            # Per part, not per line: "Mandate clauses. Trigger: rising gaps."
            # splits into two sentences and only the first sees a line start.
            if CONDITION_LABEL.match(part):
                continue
            part = LABEL.sub("", BOLD_LABEL.sub("", part)).strip()
            if len(part) > 25:
                out.append(part)
    return out


# --------------------------------------------------------------------------
# deterministic checks
# --------------------------------------------------------------------------
def load_graph(sb, pillar) -> Dict[str, dict]:
    """`pillar` may be one name or several.

    A brief spanning two pillars cites objects from both. Loading one pillar's
    graph would report every citation into the other as an unknown id, and the
    section would be withheld for being correct.
    """
    pillars = [pillar] if isinstance(pillar, str) else list(pillar)

    def scoped(table, cols):
        q = sb.table(table).select(cols)
        return (q.in_("pillar", pillars) if len(pillars) > 1
                else q.eq("pillar", pillars[0])).execute().data

    graph = {}
    for row in scoped("evidence", "id,claim,class,confidence,env_layer,quote_span,pillar"):
        graph[row["id"]] = dict(row, kind="evidence")
    for row in scoped("signals", "id,statement,pillar"):
        graph[row["id"]] = dict(row, kind="signal")
    for row in scoped("findings", "id,statement,pillar"):
        graph[row["id"]] = dict(row, kind="finding")
    for row in sb.table("risks").select("id,statement").execute().data:
        graph[row["id"]] = dict(row, kind="risk")
    for row in scoped("trends", "id,statement"):
        graph[row["id"]] = dict(row, kind="trend")
    for row in scoped("uncertainties", "id,question"):
        graph[row["id"]] = dict(row, kind="uncertainty")
    for row in scoped("forecasts", "id,statement"):
        graph[row["id"]] = dict(row, kind="forecast")
    # Only admitted, reachable figures enter the graph. A figure refused as
    # decoration, or one that no longer loads, must fail citation like an
    # invented id would — a brief that renders a broken image has published a
    # citation it cannot honour.
    # Objects admitted by strategize.py. Some are global rather than per-pillar,
    # which is how the schema models them — a scenario is a future for the whole
    # analysis, not for one pillar.
    def plain(table, cols, kind, label):
        try:
            for row in sb.table(table).select(cols).execute().data:
                graph[row["id"]] = dict(row, kind=kind, statement=row.get(label) or "")
        except Exception:
            pass                       # table absent in an older database

    plain("scenarios", "id,name,one_sentence", "scenario", "one_sentence")
    plain("options", "id,name,description", "option", "description")
    plain("drivers", "id,name,description", "driver", "description")
    plain("cross_impacts", "id,statement", "cross_impact", "statement")
    plain("initiatives", "id,name,objective", "initiative", "objective")
    plain("actions", "id,statement", "action", "statement")
    plain("decision_requirements", "id,title,decision", "decision", "decision")
    plain("indicators", "id,watch,threshold", "indicator", "watch")
    plain("opportunities", "id,statement", "opportunity", "statement")
    plain("implications", "id,statement", "implication", "statement")
    plain("questions", "id,text", "question", "text")
    plain("topics", "id,name", "topic", "name")

    for row in scoped("figures", "id,describes,caption,kind,informative,reachable"):
        if row.get("informative") and row.get("reachable"):
            graph[row["id"]] = dict(row, kind="figure",
                                    statement=row.get("describes") or row.get("caption") or "")
    return graph


def check_citations(sentences, graph) -> List[Violation]:
    """Bracketed citations and bare object references must both resolve."""
    out = []
    for sentence in sentences:
        for cite in set(CITATION.findall(sentence)) | set(OBJECT_REF.findall(sentence)):
            if cite not in graph:
                out.append(Violation(
                    check="CITATION", severity="BLOCKER", sentence=sentence,
                    detail="cites %s, which does not exist in this pillar's graph" % cite))
    return out


def check_unsourced(sentences) -> List[Violation]:
    out = []
    for sentence in sentences:
        if CITATION.search(sentence) or OBJECT_REF.search(sentence):
            continue
        if not ASSERTIVE.search(sentence):
            continue
        if any(h in sentence.lower() for h in HEDGES):
            continue
        if is_recommendation(sentence):
            continue
        if is_meta_claim(sentence) or is_condition(sentence):
            continue
        out.append(Violation(
            check="UNSOURCED", severity="BLOCKER", sentence=sentence,
            detail="asserts a fact with no [EV-xxx] citation"))
    return out


def check_class_discipline(sentences, graph) -> List[Violation]:
    """Class C is a hypothesis and must read like one; Class D is a proposed
    construct and must not be presented as existing policy."""
    out = []
    for sentence in sentences:
        cites = [c for c in CITATION.findall(sentence) if c in graph]
        ev = [graph[c] for c in cites if graph[c]["kind"] == "evidence"]
        if not ev:
            continue
        lowered = sentence.lower()

        if all(e["class"] == "C" for e in ev) and not any(h in lowered for h in HEDGES):
            out.append(Violation(
                check="CLASS_C", severity="BLOCKER", sentence=sentence,
                detail="rests only on Class C (unproven, single-source) evidence "
                       "%s but is stated as fact" % [e["id"] for e in ev]))

        if any(e["class"] == "D" for e in ev) and not any(m in lowered for m in CONSTRUCT_MARKERS):
            out.append(Violation(
                check="CLASS_D", severity="WARNING", sentence=sentence,
                detail="cites a Class D policy construct without marking it as proposed"))
    return out


def check_gates(sb, sentences, pillar=None) -> List[Violation]:
    """An OPEN gate is a prohibition, not a footnote. The guard is keyword-based
    and deliberately over-triggers: a false positive costs a human glance, a
    false negative ships an unsupported UAE claim."""
    gates = sb.table("validation_gates").select("*").eq("status", "OPEN").execute().data
    if pillar:
        gates = [g for g in gates if pillar in (g.get("blocks") or "")
                 or g["id"].startswith("VG-%s-" % pillar[:2])]
    if not gates:
        return []

    out = []
    gap_language = re.compile(
        r"\b(uae|emirati|tawazun|mod)\b.{0,80}?\b(gap|lacks?|lacking|deficien\w*|"
        r"shortfall|unable|insufficient|behind|weakness)\b", re.I)
    for sentence in sentences:
        lowered = sentence.lower()
        if "customer validation" in lowered or "validation required" in lowered:
            continue                      # the sentence IS the gate disclosure
        if gap_language.search(sentence):
            for gate in gates:
                out.append(Violation(
                    check="GATE", severity="BLOCKER", sentence=sentence,
                    detail="asserts a UAE gap while %s is OPEN: %s"
                           % (gate["id"], gate["blocks"])))
                break
    return out


def unmatched_openers(sentences) -> List[str]:
    """Sentence-initial words on unsourced sentences that are not known verbs.

    The imperative list is curated, so it will always lag the vocabulary a model
    reaches for. When a section is withheld, this reports the words that failed
    to match, so a missing verb shows up as a line to read rather than as a
    section that silently disappeared from the brief.
    """
    out = []
    for v in check_unsourced(sentences):
        first = re.split(r"[\s,:;]+", _LIST_PREFIX.sub("", v.sentence.strip()).lower(), 1)[0]
        first = first.strip("*_.()\"'")
        if first and first not in IMPERATIVE_VERBS and first.isalpha():
            out.append(first)
    return sorted(set(out))


def check_section(markdown: str, graph, allow_unsourced: bool = False,
                  entail: bool = False) -> List[str]:
    """Blocking failures for ONE freshly drafted section.

    The deterministic checks are free. `entail` adds the one model-assisted
    check — does the cited quote actually support the sentence — which was
    previously only run in the final audit. That was too late: three sentences
    citing quotes that did not support them were published, and the audit could
    only report them after the fact. Run in the loop, the same three become a
    retry. It costs roughly one batched call per section per attempt.

    Returns human-readable failure lines, fed straight back into the retry prompt.
    """
    sentences = sentences_of(markdown)
    out = []
    for v in check_citations(sentences, graph):
        out.append(v.detail[0].upper() + v.detail[1:] +
                   " — remove it or cite an id from the data.")
    if not allow_unsourced:
        for v in check_unsourced(sentences):
            out.append("This sentence states a fact with no citation: \"%s\""
                       % v.sentence[:140])
    if entail:
        try:
            violations, _ = check_entailment(sentences, graph)
            for v in violations:
                out.append("The citation does not support this sentence — %s: \"%s\""
                           % (v.detail.split(": ", 1)[-1], v.sentence[:120]))
        except Exception as exc:
            # A failed entailment call must not withhold a section that the
            # deterministic checks passed. Surfaced, not swallowed.
            print("      ! entailment check unavailable (%s)" % str(exc)[:70])

    seen, uniq = set(), []
    for line in out:
        if line not in seen:
            seen.add(line)
            uniq.append(line)
    return uniq


# --------------------------------------------------------------------------
# entailment (the only model-assisted check)
# --------------------------------------------------------------------------
ENTAIL_PROMPT = """You are a citation auditor. For each numbered item below, decide
whether the SOURCE QUOTE actually supports the SENTENCE.

Judge support only. A sentence can be true in the world and still be unsupported
by the quote attached to it — that counts as NOT supported. Paraphrase is fine;
new facts, added numbers, added causation or broadened scope are not.

Be precise, not merely strict. If the quote states the substance of the sentence
in different words, it SUPPORTS it — restating "tools designed to withstand the
attack of a quantum computer" as "protects against quantum cryptanalysis" is
paraphrase, not a new claim. Mark NOT supported when the sentence adds something
the quote does not contain: a figure, a date, a causal link, a wider population,
or a stronger degree of certainty.

Return one verdict per item, using the item's index.

{items}
"""


def check_entailment(sentences, graph, batch_size=20, fast=False):
    """Returns (violations, n_claims_checked).

    Judged on the reasoning deployment, not the cheap one. This check now gates
    publication rather than only reporting afterwards, which inverts the cost of
    its two errors: a missed over-attribution is one bad citation, but a false
    "not supported" withholds a whole correct section. The cheap judge produced
    exactly that — it rejected a sentence about post-quantum standards whose
    quote span read "encryption tools designed to withstand the attack of a
    quantum computer", which is the claim verbatim.
    """
    items, meta = [], []
    for sentence in sentences:
        ev = [graph[c] for c in CITATION.findall(sentence)
              if c in graph and graph[c]["kind"] == "evidence" and graph[c].get("quote_span")]
        if not ev:
            continue
        quotes = " | ".join("%s: \"%s\"" % (e["id"], e["quote_span"]) for e in ev)
        meta.append((sentence, [e["id"] for e in ev]))
        items.append((len(meta) - 1, sentence, quotes))

    if not items:
        return [], 0

    out = []
    for start in range(0, len(items), batch_size):
        chunk = items[start:start + batch_size]
        rendered = "\n\n".join(
            "[%d]\nSENTENCE: %s\nSOURCE QUOTE(S): %s" % (i, s, q) for i, s, q in chunk)
        result = llm.structured(ENTAIL_PROMPT.format(items=rendered),
                                EntailmentBatch, fast=fast, effort="high")

        for verdict in result.verdicts:
            if verdict.supported or verdict.index >= len(meta):
                continue
            sentence, ev_ids = meta[verdict.index]
            out.append(Violation(
                check="ENTAILMENT", severity="BLOCKER", sentence=sentence,
                detail="cited %s does not support this sentence: %s"
                       % (ev_ids, verdict.reason)))
    return out, len(items)


# --------------------------------------------------------------------------
# Sections whose subject is the evidence base itself. Mirrors
# generate.EPISTEMIC_SECTIONS: the generation loop already exempts these, and an
# audit that does not know which section a sentence came from reported three
# "unsourced assertions" for sentences the pipeline deliberately allowed —
# penalising the brief for being honest about its own gaps.
# Mirrors generate.EPISTEMIC_SECTIONS — sections whose subject is the document,
# the method, what is unknown, a hypothetical future, or a decision rationale.
EPISTEMIC_SECTIONS = {
    "limits", "purpose_scope", "methodology", "question_architecture",
    "uncertainties", "scenarios", "decisions",
    # The stress test reasons over futures that do not exist, and the
    # opportunity register reports that it is empty — both were withheld for
    # describing exactly what they are for.
    "stress_test", "opportunities",
}


def split_sections(body: str, template_sections) -> List[tuple]:
    """[(section_key, markdown)] by matching '## ' headings to template titles.

    Falls back to a single None-keyed block when the headings do not match, so a
    hand-edited report is still audited — just without section awareness.
    """
    titles = {(s.get("title") or "").strip().lower(): s.get("key")
              for s in (template_sections or [])}
    out, key, buf = [], None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if buf:
                out.append((key, "\n".join(buf)))
            key = titles.get(line[3:].strip().lower())
            buf = []
        else:
            buf.append(line)
    if buf:
        out.append((key, "\n".join(buf)))
    return out or [(None, body)]


def main():
    ap = argparse.ArgumentParser(description="Verify a generated report against the graph")
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--report", required=True, help="reports.id (uuid)")
    ap.add_argument("--json", help="write the violation list to this path")
    ap.add_argument("--skip-entailment", action="store_true",
                    help="run only the deterministic checks (no model calls)")
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="verify", status="RUNNING")
    sb = db()

    rows = sb.table("reports").select("*").eq("id", a.report).execute().data
    if not rows:
        sys.exit("report %s not found" % a.report)
    report = rows[0]
    body, pillar = report.get("body_md") or "", report.get("pillar")

    graph = load_graph(sb, pillar)
    sentences = sentences_of(body)
    cited = sum(1 for s in sentences if CITATION.search(s))
    print("Verifying %r\n  %d sentences, %d carrying citations, %d graph objects\n"
          % (report.get("title"), len(sentences), cited, len(graph)))

    tpl = sb.table("report_templates").select("sections") \
            .eq("id", report.get("template_id")).execute().data
    tpl_sections = tpl[0]["sections"] if tpl else []

    violations = []
    violations += check_citations(sentences, graph)

    # Unsourced is scored per section, so the epistemic sections are exempt here
    # exactly as they are during generation.
    exempt = 0
    for key, chunk in split_sections(body, tpl_sections):
        chunk_sentences = sentences_of(chunk)
        if key in EPISTEMIC_SECTIONS:
            exempt += len(check_unsourced(chunk_sentences))
            continue
        violations += check_unsourced(chunk_sentences)

    violations += check_class_discipline(sentences, graph)
    violations += check_gates(sb, sentences, pillar)

    n_checked = 0
    if not a.skip_entailment:
        entail, n_checked = check_entailment(sentences, graph)
        violations += entail

    by_check: Dict[str, int] = {}
    for v in violations:
        by_check[v.check] = by_check.get(v.check, 0) + 1

    for v in violations:
        print("[%s] %s\n    %s\n    \"%s\"\n"
              % (v.severity, v.check, v.detail, v.sentence[:150]))

    blockers = [v for v in violations if v.severity == "BLOCKER"]
    print("-" * 70)
    print("checks: %s" % (by_check or "all clean"))
    if exempt:
        print("%d sentence(s) in epistemic sections exempt from the citation "
              "requirement (statements about what the evidence does not show)" % exempt)
    if n_checked:
        supported = n_checked - by_check.get("ENTAILMENT", 0)
        print("citation faithfulness: %d/%d = %.2f"
              % (supported, n_checked, supported / n_checked))
    print("unsourced assertions : %d" % by_check.get("UNSOURCED", 0))
    print("gate violations      : %d" % by_check.get("GATE", 0))
    print("%d blocker(s), %d warning(s)" % (len(blockers), len(violations) - len(blockers)))

    config.update_run(getattr(a, "run_id", None),
                      status="FAILED" if blockers else "DONE",
                      counts={"verify": len(violations)},
                      error=(f"{len(blockers)} blocking verification failure(s)"
                             if blockers else None))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump([v.model_dump() for v in violations], fh, indent=2)
        print("violations written to %s" % a.json)

    sys.exit(1 if blockers else 0)


if __name__ == "__main__":
    main()
