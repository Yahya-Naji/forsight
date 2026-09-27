import { Badge } from "@/components/ui/badge";

// Ontology chips. These render an enum the RULES assigned — evidence class,
// source tier, environment layer, confidence — so each keeps a distinct,
// non-brand colour and none of them is free to drift: a reader has to be able
// to tell Class A from Tier 1 from a UAE-layer row at a glance.

export const PILLAR_LABEL: Record<string, string> = {
  CYBERSECURITY: "Cybersecurity", AI: "AI",
  ELECTRONIC_WARFARE: "Electronic Warfare", PROCUREMENT: "Procurement",
};

export const label = (s?: string | null) =>
  (s ?? "").split("_").map(w => (w ? w[0] + w.slice(1).toLowerCase() : w)).join(" ")
    .replace("Uae", "UAE").replace("Ai", "AI");

export function TierChip({ tier }: { tier?: number | null }) {
  if (!tier) return null;
  return <Badge variant={tier === 1 ? "tier1" : "tier"}>TIER {tier}</Badge>;
}

const CLASS_VARIANT = { A: "classA", B: "classB", C: "classC", D: "classD" } as const;

export function ClassChip({ c }: { c?: string | null }) {
  if (!c) return null;
  return <Badge variant={CLASS_VARIANT[c as keyof typeof CLASS_VARIANT] ?? "classC"}>CLASS {c}</Badge>;
}

const LAYER_VARIANT = { UAE: "uae", REGIONAL: "regional", GLOBAL: "global" } as const;

export function LayerChip({ layer }: { layer?: string | null }) {
  if (!layer) return null;
  return <Badge variant={LAYER_VARIANT[layer as keyof typeof LAYER_VARIANT] ?? "global"}>{layer}</Badge>;
}

export function ConfChip({ c }: { c?: string | null }) {
  if (!c) return null;
  return <Badge variant="default" className="text-[#3C4258]">{c.replace("_", "-")}</Badge>;
}

export function GateChip({ status }: { status?: string | null }) {
  if (!status) return null;
  return <Badge variant={status === "OPEN" ? "open" : "passed"}>{status}</Badge>;
}

/** An object id — always monospace, because it is a token to be matched, not read. */
export function IdChip({ id }: { id?: string | null }) {
  if (!id) return null;
  return <Badge variant="mono">{id}</Badge>;
}
