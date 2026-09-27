// Deterministic checks mirroring pipeline/verify.py, so a conversational edit
// faces the same bar as generated text. pipeline/verify.py remains the
// authority — it also runs entailment, which needs the quote spans. These are
// the checks that can run synchronously while a reader waits.

export const OBJECT_REF =
  /\b(EV-[A-Z0-9-]+|SIG-[A-Z]{2}-\d+|F-[A-Z]{2}-\d+|R-[A-Z]{2}-\d+|TR-[A-Z]{2}-\d+|CU-[A-Z]{2}-\d+|FC-[A-Z]{2}-\d+|FIG-\d+|S\d{1,2}|OPT-[A-Z]|IMP-[A-Z]{3}-\d+|DRV-\d+|CI-\d+|INIT-\d+|ACT-\d+|PDC-\d+|IND-[A-Z]{2}-\d+|O\d{1,2}|[A-Z]{2}-T\d+|[A-Z]{2}-\d{2})\b/g;

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
// A discourse marker in front of a conditional does not make it an assertion.
const CONDITIONAL_OPENER =
  /^(?:(?:however|conversely|moreover|furthermore|yet|but|thus|therefore|equally|by contrast|on the other hand|that said)[,:]?\s+)?(if|should|unless|were\s+\w+\s+to|in the event|absent|provided that|so long as)\b/i;

// A falsifier states what would refute a forecast — required on every forecast
// in this system, so the report must state them, and they assert nothing about
// the present. The copula must follow immediately: matching "the falsifier"
// alone exempted a sentence that named one and then asserted a breach.
const FALSIFIER_CLAUSE =
  /^(the |its )?(falsifier|falsifying (observation|evidence)|refuting (observation|evidence)|disconfirming (observation|evidence))\s*(is|are|would be|:|\u2014|-)\s|^what would (refute|falsify|disconfirm)\b|\bwould (refute|falsify|disconfirm) (this|it|the forecast)\b/i;

// Both halves must match: something naming this document or its evidence base,
// AND a predicate about coverage. "This report shows attackers breached the
// portal" names the document but asserts a fact, so it still needs a citation.
const META_SUBJECT =
  /\b(this (report|brief|section|assessment)|the (evidence base|evidence)|blocked claims?|open gates?|validation gates?|research gaps?|these (claims|findings))\b/i;
const META_PREDICATE =
  /\b(excluded|withheld|blocked|omitted|unverified|insufficient|does not (support|establish|extend|cover)|do not (support|establish)|cannot be (confirmed|verified|established)|could not be established|not established|requires? (customer )?validation|no (uae-specific |direct )?evidence)\b/i;

const isMetaClaim = (s: string) => META_SUBJECT.test(s) && META_PREDICATE.test(s);
const isCondition = (s: string) =>
  CONDITIONAL_OPENER.test(s.trim()) || FALSIFIER_CLAUSE.test(s.trim());

const HEDGES = ["forecast", "speculative", "outlook", "projected", "projection", "may", "might",
  "could", "unproven", "single-source", "not confirmed", "cannot be confirmed", "uncertain",
  "pending", "requires validation", "suggests", "indicates", "appears", "potential", "possible",
  "working view", "hypothesis", "not yet"];

const IMPERATIVE = new Set([
  // Generated from pipeline/verify.py IMPERATIVE_VERBS. tests/test_parity.py fails if
  // the two drift: telling a reader an edit is fine and then withholding the section
  // is worse than running no check at all.
  "accredit","acquire","add","adopt","alert","align","allocate","amend","apply","appoint",
  "appraise","approve","assess","assign","audit","authenticate","authorise",
  "authorise-access","authorize","baseline","benchmark","brief","budget","build","build-out",
  "cap","catalog","catalogue","centralise","centralize","certify","challenge","choose",
  "circulate","clarify","classify","codify","commission","communicate","compare",
  "compartmentalise","compartmentalize","conduct","confirm","consolidate","consult","contest",
  "contract","contract-for","convene","coordinate","cost","create","decide","decommission",
  "define","delegate","designate","determine","develop","direct","disseminate","document",
  "drill","embed","embed-in","empower","encourage","encrypt","enforce","engage","ensure",
  "escalate","establish","establish-with","evaluate","exercise","expand","extend","finalise",
  "finalize","flag","formalise","formalize","fund","harden","harmonise","harmonize","hold",
  "implement","inspect","instruct","instrument","instrument-for","integrate","interview",
  "introduce","inventory","invest","investigate","isolate","issue","label","launch","license",
  "limit","log","maintain","mandate","map","measure","migrate","model","modernise",
  "modernize","monitor","monitor-for","negotiate","notify","oblige","obtain","offboard",
  "onboard","patch","pen-test","phase","pilot","pilot-test","press","prioritise","prioritize",
  "procure","procure-through","publish","push","qualify","quantify","raise","reassess",
  "recertify","reconcile","record","red-team","reduce","refine","refresh","rehearse","reject",
  "release","renegotiate","renew","replace","report","require","require-of","resource",
  "restrict","retire","revalidate","review","revise","revoke","ringfence","rotate","run",
  "sample","scale","schedule","screen","secure","seek","segment","segregate","select",
  "sequence","set","share","sign","simulate","specify","staff","stage","standardise",
  "standardize","stipulate","strengthen","stress-test","subscribe","sunset","surface",
  "survey","suspend","synchronise","synchronize","tabletop","tag","task","terminate","test",
  "tighten","track","train","transition","update","upgrade","upskill","validate","verify",
  "vet","wargame","warn","withhold"]);
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
