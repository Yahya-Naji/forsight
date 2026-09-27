import { PILLAR_LABEL, label } from "./chips";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Gate text comes from the database. rules.py now writes reader-facing pillar
// names, but a legacy row must never surface a raw enum in the console.
const humanise = (t: string) =>
  Object.entries(PILLAR_LABEL).reduce((acc, [k, v]) => acc.replaceAll(k, v), t ?? "");

export default function GateCard({ id, status, blocks }:
  { id: string; status: string; blocks: string }) {
  const open = status === "OPEN";
  return (
    <div className={cn("rounded-lg border px-4 py-3.5",
      open ? "border-amber-line bg-amber-bg" : "border-green-line bg-green-bg")}>
      <Badge variant={open ? "open" : "passed"}>{id} · {label(status)}</Badge>
      <p className={cn("mt-2 text-base leading-snug", open ? "text-[#4A4633]" : "text-[#35513F]")}>
        {humanise(blocks)}
      </p>
    </div>
  );
}
