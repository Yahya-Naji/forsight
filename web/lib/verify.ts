// Deterministic checks mirroring pipeline/verify.py, so a conversational edit
// faces the same bar as generated text. pipeline/verify.py remains the
// authority — it also runs entailment, which needs the quote spans. These are
// the checks that can run synchronously while a reader waits.

export const OBJECT_REF =
  /\b(EV-[A-Z0-9-]+|SIG-[A-Z]{2}-\d+|F-[A-Z]{2}-\d+|R-[A-Z]{2}-\d+|TR-[A-Z]{2}-\d+|CU-[A-Z]{2}-\d+|FC-[A-Z]{2}-\d+)\b/g;

const ASSERTIVE =
  /\b(is|are|was|were|has|have|shows?|demonstrates?|confirms?|proves?|increases?|decreases?|reduces?|requires?|creates?|causes?)\b/i;

const HEDGES = ["forecast", "speculative", "outlook", "projected", "projection", "may", "might",
  "could", "unproven", "single-source", "not confirmed", "cannot be confirmed", "uncertain",
  "pending", "requires validation", "suggests", "indicates", "appears", "potential", "possible",
  "working view", "hypothesis", "not yet"];

const IMPERATIVE = new Set(["establish","develop","monitor","review","validate","implement",
  "require","strengthen","refine","prioritise","prioritize","define","maintain","expand","adopt",
  "introduce","commission","assess","ensure","conduct","create","build","run","track","acquire",
  "mandate","negotiate","publish","fund","pilot","procure"]);
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
    .flatMap(l => l.replace(/^[-*+]\s+/, "").split(/(?<=[.!?])\s+(?=[A-Z[])/))
    .map(s => s.trim())
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
