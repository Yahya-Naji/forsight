// Deterministic checks mirroring pipeline/verify.py, so a conversational edit
// faces the same bar as generated text. pipeline/verify.py remains the
// authority — it also runs entailment, which needs the quote spans. These are
// the checks that can run synchronously while a reader waits.

export const OBJECT_REF =
  /\b(EV-[A-Z0-9-]+|SIG-[A-Z]{2}-\d+|F-[A-Z]{2}-\d+|R-[A-Z]{2}-\d+|TR-[A-Z]{2}-\d+|CU-[A-Z]{2}-\d+|FC-[A-Z]{2}-\d+)\b/g;

const ASSERTIVE =
  /\b(is|are|was|were|has|have|had|shows?|showed|demonstrat(?:es?|ed)|confirms?|confirmed|proves?|proved|increas(?:es?|ed)|decreas(?:es?|ed)|reduc(?:es?|ed)|requires?|required|creat(?:es?|ed)|caus(?:es?|ed)|operates?|operated|target(?:s|ed)|breach(?:es|ed)|compromis(?:es?|ed)|exploit(?:s|ed)|deploys?|deployed|maintains?|maintained|holds?|held|grew|rose|fell|reached|remains?|remained|accounts? for|led to|resulted in)\b/i;

// A standalone bold run is an action title — the template's heading device.
const BOLD_HEADING = /^\*\*[^*]+\*\*:?$/;
// Labels that introduce a condition to watch rather than a present claim.
const CONDITION_LABEL =
  /^\*{0,2}(trigger|watch|falsifier|indicator|threshold|what would refute this)\*{0,2}\s*[:\u2014-]/i;
// Any short bold run followed by a colon is a label, whatever the word is.
const BOLD_LABEL = /^\*\*[^*]{1,60}\*\*\s*:\s*/;
const LIST_NUMBER = /^\d+[.)]\s+/;
const LABEL =
  /^\*{0,2}(so what|trigger|implication|implications|action|owner|why|bottom line|recommendation|watch|horizon|confidence|falsifier|what would refute this|next step)\*{0,2}\s*[:\u2014-]\s*/i;

// A sentence opening on a condition asserts nothing about the present.
const CONDITIONAL_OPENER =
  /^(if|should|unless|were\s+\w+\s+to|in the event|absent|provided that|so long as)\b/i;

// Both halves must match: something naming this document or its evidence base,
// AND a predicate about coverage. "This report shows attackers breached the
// portal" names the document but asserts a fact, so it still needs a citation.
const META_SUBJECT =
  /\b(this (report|brief|section|assessment)|the (evidence base|evidence)|blocked claims?|open gates?|validation gates?|research gaps?|these (claims|findings))\b/i;
const META_PREDICATE =
  /\b(excluded|withheld|blocked|omitted|unverified|insufficient|does not (support|establish|extend|cover)|do not (support|establish)|cannot be (confirmed|verified|established)|could not be established|not established|requires? (customer )?validation|no (uae-specific |direct )?evidence)\b/i;

const isMetaClaim = (s: string) => META_SUBJECT.test(s) && META_PREDICATE.test(s);
const isCondition = (s: string) => CONDITIONAL_OPENER.test(s.trim());

const HEDGES = ["forecast", "speculative", "outlook", "projected", "projection", "may", "might",
  "could", "unproven", "single-source", "not confirmed", "cannot be confirmed", "uncertain",
  "pending", "requires validation", "suggests", "indicates", "appears", "potential", "possible",
  "working view", "hypothesis", "not yet"];

const IMPERATIVE = new Set(["establish","develop","monitor","review","validate","implement",
  "require","strengthen","refine","prioritise","prioritize","define","maintain","expand","adopt",
  "introduce","commission","assess","ensure","conduct","create","build","run","track","acquire",
  "mandate","negotiate","publish","fund","pilot","procure",
  // A closed verb list quietly withholds sections for using a synonym.
  "launch","enforce","embed","extend","integrate","align","audit","map","baseline",
  "formalise","formalize","standardise","standardize","designate","assign","appoint",
  "convene","task","instruct","direct","issue","revise","update","tighten","restrict",
  "verify","test","exercise","rehearse","resource","staff","invest","allocate",
  "escalate","report","record","document","share","brief","consult","engage",
  "contract","certify","accredit","qualify","screen","vet","segment","isolate",
  "patch","harden","instrument","log","add","apply","set","raise","reduce","limit",
  "cap","phase","retire","replace","migrate","consolidate","centralise","centralize"]);
const MODAL = /\b(should|must|ought to|recommends?|recommended|is recommended)\b/i;

const isRecommendation = (s: string) => {
  const stripped = s.trim().replace(/^(\d+[.)]\s*|[-*+]\s*)?(\*\*)?\s*/, "");
  const first = stripped.toLowerCase().split(/[\s,:]+/)[0].replace(/[*_]/g, "");
  return IMPERATIVE.has(first) || MODAL.test(s);
};

const sentences = (text: string) =>
  text.split("\n")
    .map(l => l.trim())
    .filter(l => l && !/^(#|\||---|>)/.test(l))
    .map(l => l.replace(/^[-*+]\s+/, "").replace(LIST_NUMBER, ""))
    .filter(l => !BOLD_HEADING.test(l))
    .flatMap(l => l.split(/(?<=[.!?])\s+(?=[A-Z[])/))
    // Per sentence, not per line: "Mandate clauses. Trigger: rising gaps."
    // splits into two and only the first ever sees a line start.
    .filter(s => !CONDITION_LABEL.test(s.trim()))
    .map(s => s.trim().replace(BOLD_LABEL, "").replace(LABEL, "").trim())
    .filter(s => s.length > 25);

export type Verdict = {
  ok: boolean;
  citations: string[];
  unresolved: string[];
  unsourced: string[];
  gateViolations: string[];
};

/** Check a proposed passage against the graph. Empty problems == publishable. */
export function checkPassage(
  text: string,
  known: Set<string>,
  openGates: { id: string; blocks: string }[]
): Verdict {
  const ss = sentences(text);
  const citations = [...new Set([...text.matchAll(OBJECT_REF)].map(m => m[1]))];
  const unresolved = citations.filter(c => !known.has(c));

  const unsourced = ss.filter(s => {
    if (OBJECT_REF.test(s)) { OBJECT_REF.lastIndex = 0; return false; }
    OBJECT_REF.lastIndex = 0;
    if (!ASSERTIVE.test(s)) return false;
    if (HEDGES.some(h => s.toLowerCase().includes(h))) return false;
    if (isMetaClaim(s) || isCondition(s)) return false;
    return !isRecommendation(s);
  });

  // An open gate is a prohibition. Deliberately over-triggers: a false positive
  // costs a human glance, a false negative ships an unsupported UAE claim.
  const gapLanguage =
    /\b(uae|emirati|tawazun|mod)\b.{0,80}?\b(gap|lacks?|lacking|deficien\w*|shortfall|unable|insufficient|behind|weakness)\b/i;
  const gateViolations = openGates.length
    ? ss.filter(s => gapLanguage.test(s) && !/customer validation|validation required/i.test(s))
    : [];

  return {
    ok: unresolved.length === 0 && unsourced.length === 0 && gateViolations.length === 0,
    citations, unresolved, unsourced, gateViolations,
  };
}
