export const PILLAR_LABEL: Record<string, string> = {
  CYBERSECURITY: "Cybersecurity", AI: "AI",
  ELECTRONIC_WARFARE: "Electronic Warfare", PROCUREMENT: "Procurement",
};
export const label = (s?: string | null) =>
  (s ?? "").split("_").map(w => w ? w[0] + w.slice(1).toLowerCase() : w).join(" ").replace("Uae", "UAE").replace("Ai", "AI");

export function TierChip({ tier }: { tier?: number | null }) {
  if (!tier) return null;
  return <span className={tier === 1 ? "chip chip-tier1" : "chip chip-tier"}>TIER {tier}</span>;
}
export function ClassChip({ c }: { c?: string | null }) {
  if (!c) return null;
  const cls = c === "A" ? "chip-classA" : c === "B" ? "chip-classB" : "chip-classC";
  return <span className={`chip ${cls}`}>CLASS {c}</span>;
}
export function LayerChip({ layer }: { layer?: string | null }) {
  if (!layer) return null;
  const cls = layer === "UAE" ? "chip-uae" : layer === "REGIONAL" ? "chip-regional" : "chip-global";
  return <span className={`chip ${cls}`}>{layer}</span>;
}
export function ConfChip({ c }: { c?: string | null }) {
  if (!c) return null;
  return <span className="chip chip-conf">{c.replace("_", "-")}</span>;
}
