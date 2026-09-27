// The engine contract, in one place.
//
// Two screens depend on these definitions — the creation tab, which queues a run
// and lights a checklist, and the engine tab, which explains what each stage
// did. They were drifting apart while describing the same pipeline, so the stage
// keys (the contract with Python's update_run()) and the ontology below are
// declared once and imported by both.
//
// The part worth reading is AUTHORITY. Every field on every object is owned by
// exactly one layer: the model may propose a claim but may never set its class,
// and no rule invents a sentence. That division is the whole architecture, and
// it is data here rather than prose so the UI can render it and a reader can
// check it against pipeline/rules.py.

export type Layer = "SOURCE" | "NEURAL" | "SYMBOLIC";

export const LAYER: Record<Layer, {
  label: string; note: string; fg: string; bg: string; line: string;
  /** Fill for the attrition rail — the page tints are too pale to show a taper. */
  spine: string;
}> = {
  SOURCE: {
    label: "Collected",
    note: "Retrieved from a registered publisher. Nothing is inferred here.",
    fg: "var(--global)", bg: "var(--global-bg)", line: "#BCDDE5", spine: "#9ECFDA",
  },
  NEURAL: {
    label: "Model proposes",
    note: "A language model drafts candidates. It decides nothing that reaches the page.",
    fg: "var(--accent-deep)", bg: "var(--accent-wash)", line: "#C7D2F7", spine: "#A9BCF7",
  },
  SYMBOLIC: {
    label: "Rule decides",
    note: "Deterministic code in pipeline/rules.py. Reproducible, and auditable without a model.",
    fg: "#3A4468", bg: "#EDEFF6", line: "#D6DBEA", spine: "#AEB6CE",
  },
};

// ---------------------------------------------------------------------------
// stages — the keys are the contract with pipeline/config.py update_run()
// ---------------------------------------------------------------------------
export type Stage = {
  key: string;
  name: string;
  sub: string;
  layer: Layer;
  /** The module that holds the decision. Shown so a claim can be traced to code. */
  decidedIn: string;
  /** What this stage refuses, and why refusing is the point. */
  refuses: string;
  /** Table whose rows this stage produces, for the live count. */
  produces?: string;
};

export const STAGES: Stage[] = [
  {
    key: "collect", name: "Collect", layer: "SOURCE",
    sub: "Documents from lanes A, B and C, each bound to a registered publisher and tier",
    decidedIn: "collectors/registry.py · map_domain",
    refuses: "Pages blocked by robots.txt, paywall stubs, and anything under the length floor. A publisher missing from the registry falls back to the aggregator id and is scored Tier 4 — which is why the registry is the tier-integrity surface.",
    produces: "documents",
  },
  {
    key: "gate1", name: "Gate 1 · relevance", layer: "NEURAL",
    sub: "Cheap typed triage before anything expensive runs",
    decidedIn: "decisions.py · Jev gate 1",
    refuses: "Documents with no bearing on any live question, so extraction is never paid for twice.",
  },
  {
    key: "extract", name: "Extract", layer: "NEURAL",
    sub: "The model emits claims, each bound to a verbatim quote span",
    decidedIn: "extract.py",
    refuses: "Anything that fails the typed schema. A claim with no quote span cannot be checked later, so it never enters.",
    produces: "evidence",
  },
  {
    key: "gate2", name: "Gate 2 · quote check", layer: "NEURAL",
    sub: "Each claim must be entailed by the quote it cites",
    decidedIn: "decisions.py · Jev gate 2",
    refuses: "Claims their own source does not support. This is where a plausible paraphrase is separated from a supported one.",
  },
  {
    key: "rules", name: "Rules & gates", layer: "SYMBOLIC",
    sub: "Evidence class, confidence, signal strength and the UAE inference guard",
    decidedIn: "rules.py",
    refuses: "Nothing outright — it downgrades. Corroboration is counted in DISTINCT PUBLISHERS, so four claims from one article are one source, and a UAE-specific claim without two independent UAE-layer rows opens a gate that blocks assertion.",
  },
  {
    key: "synthesize", name: "Synthesize", layer: "SYMBOLIC",
    sub: "Signals, trends, findings and risks admitted only against the rules",
    decidedIn: "synthesize.py · rules.py",
    refuses: "Proposals with too little corroboration behind them, and findings that assert importance instead of stating what is true. Refusals are written to research_gaps as analytical output, not discarded as errors.",
    produces: "signals",
  },
  {
    key: "forecast", name: "Forecast", layer: "SYMBOLIC",
    sub: "Plausibility computed from corroboration and horizon, never asserted",
    decidedIn: "forecast.py · calibrate()",
    refuses: "Forecasts with no admitted signal behind them, UAE-layer forecasts while the gate is open, and statements left with an unfilled placeholder.",
    produces: "forecasts",
  },
  {
    key: "generate", name: "Generate", layer: "NEURAL",
    sub: "Section-scoped inputs, one citation per claim, redrafted until it passes",
    decidedIn: "generate.py",
    refuses: "Its own drafts. A section that still fails after its retries is withheld and the hole is left visible, because a plausible paragraph on a citation that does not exist is worse than a gap.",
  },
  {
    key: "verify", name: "Verify", layer: "SYMBOLIC",
    sub: "Citations resolve · gates honoured · quotes entail the sentences citing them",
    decidedIn: "verify.py",
    refuses: "Publication. The audit runs after assembly and its findings are the scorecard, whether or not they are flattering.",
  },
];

export const STAGE_KEYS = STAGES.map((s) => s.key);

// ---------------------------------------------------------------------------
// the ontology — object types, and who owns each field
// ---------------------------------------------------------------------------
export type ObjectType = {
  key: string;
  name: string;
  table: string;
  /** Column 0 of the model: what the object IS. */
  gloss: string;
  /** Fields a model may propose. */
  neural: string[];
  /** Fields only deterministic code may set. Listing these is the point. */
  symbolic: string[];
  /** Object types this one points at, by key. */
  to: string[];
};

export const ONTOLOGY: ObjectType[] = [
  {
    key: "document", name: "Document", table: "documents",
    gloss: "A retrieved page or PDF, bound to the publisher that issued it.",
    neural: [], symbolic: ["registry_id", "tier", "published_on", "retrieved_at"],
    to: ["evidence", "figure"],
  },
  {
    key: "figure", name: "Figure", table: "figures",
    gloss: "A published chart, diagram or screenshot that carries information.",
    neural: ["kind", "describes"],
    symbolic: ["informative", "refused_reason", "reachable"],
    to: ["evidence"],
  },
  {
    key: "evidence", name: "Evidence", table: "evidence",
    gloss: "One sourced claim with the verbatim span it rests on. The atom of the system.",
    neural: ["claim", "quote_span", "steep"],
    symbolic: ["class", "confidence", "env_layer"],
    to: ["signal"],
  },
  {
    key: "signal", name: "Signal", table: "signals",
    gloss: "A change several independent sources point at.",
    neural: ["statement"],
    symbolic: ["strength", "direction", "horizon"],
    to: ["trend", "finding", "forecast"],
  },
  {
    key: "trend", name: "Trend", table: "trends",
    gloss: "A direction of travel across signals.",
    neural: ["statement"], symbolic: ["admitted_from"],
    to: [],
  },
  {
    key: "finding", name: "Finding", table: "findings",
    gloss: "What the signals mean. Must say X rather than Y, not that X matters.",
    neural: ["statement"], symbolic: ["admitted_from", "substance_test"],
    to: ["risk"],
  },
  {
    key: "risk", name: "Risk", table: "risks",
    gloss: "A consequence with a scored likelihood and impact.",
    neural: ["statement"], symbolic: ["likelihood", "impact", "score"],
    to: [],
  },
  {
    key: "uncertainty", name: "Uncertainty", table: "uncertainties",
    gloss: "A question whose answer would move the assessment.",
    neural: ["question", "why_it_matters"], symbolic: [],
    to: ["forecast"],
  },
  {
    key: "forecast", name: "Forecast", table: "forecasts",
    gloss: "An outlook carrying its own falsifier. No falsifier, no forecast.",
    neural: ["statement", "falsifier", "assumptions", "rationale"],
    symbolic: ["plausibility", "confidence", "horizon", "basis"],
    to: ["gate"],
  },
  {
    key: "gate", name: "Validation gate", table: "validation_gates",
    gloss: "A prohibition. While it is open, the claims it names cannot be asserted.",
    neural: [], symbolic: ["status", "blocks", "gate_type"],
    to: [],
  },
];

export const ONTOLOGY_BY_KEY: Record<string, ObjectType> =
  Object.fromEntries(ONTOLOGY.map((o) => [o.key, o]));

// ---------------------------------------------------------------------------
// forecast calibration — mirrors forecast.py so the arithmetic can be shown
// ---------------------------------------------------------------------------
export const BAND_AT = [
  { min: 4, band: "LIKELY" },
  { min: 2, band: "POSSIBLE" },
  { min: 1, band: "UNCERTAIN" },
  { min: -99, band: "SPECULATIVE" },
];

export const BAND_COLOR: Record<string, { fg: string; bg: string }> = {
  LIKELY: { fg: "var(--green-ink)", bg: "var(--green-chip)" },
  POSSIBLE: { fg: "var(--accent-deep)", bg: "var(--accent-wash)" },
  UNCERTAIN: { fg: "var(--amber-ink)", bg: "var(--amber-chip)" },
  SPECULATIVE: { fg: "#7A4A6A", bg: "#F6E9F1" },
};

/** The calibration terms, in the order forecast.py adds them. */
export function calibrationTerms(basis: Record<string, any> | null) {
  if (!basis) return [];
  const t: { label: string; value: number; note: string }[] = [];
  if (typeof basis.signal_points === "number")
    t.push({
      label: "signal strength", value: basis.signal_points,
      note: (basis.strengths ?? []).join(" + ") || "strongest admitted signal",
    });
  if (typeof basis.publisher_points === "number")
    t.push({
      label: "independent publishers", value: basis.publisher_points,
      note: `${basis.publishers ?? "?"} distinct publishers behind it`,
    });
  if (typeof basis.horizon_penalty === "number")
    t.push({
      label: "horizon distance", value: basis.horizon_penalty,
      note: "the further out, the weaker the claim",
    });
  if (typeof basis.uncertainty_penalty === "number")
    t.push({
      label: "open uncertainties", value: basis.uncertainty_penalty,
      note: "each unresolved question costs a point",
    });
  return t;
}
