"use client";
import { useState } from "react";
import { TierChip, ClassChip, LayerChip, ConfChip } from "./chips";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import EvidenceDialog from "./EvidenceDialog";

// One evidence row, with everything a reader needs to judge it: the claim, the
// verbatim span it rests on, and the chips the rules assigned. The provenance
// line is last and quiet — it is what you check after deciding the claim
// matters, not before.

export type Evidence = {
  id: string; claim: string; class: string | null; confidence: string | null;
  env_layer: string | null; quote_span?: string | null;
  publisher?: string | null; tier?: number | null; date?: string | null;
  url?: string | null; doc_title?: string | null;
};

export default function EvidenceCard({ ev, compact }: { ev: Evidence; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <>
    <Card onClick={() => setOpen(true)} role="button" tabIndex={0}
          onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setOpen(true); } }}
          className={cn("cursor-pointer transition-colors hover:border-[#C7D2F7] hover:bg-[#FCFCFE]",
                        compact ? "px-[15px] py-[13px]" : "px-[18px] py-4")}>
      <p className={cn("font-semibold leading-snug", compact ? "text-base" : "text-[14.5px]")}>
        {ev.claim}
      </p>
      {!compact && ev.quote_span && <div className="quote">&ldquo;{ev.quote_span}&rdquo;</div>}
      <div className={cn("flex items-center gap-[7px]", compact ? "mt-2.5" : "mt-3")}>
        <TierChip tier={ev.tier} />
        <ClassChip c={ev.class} />
        <ConfChip c={ev.confidence} />
        <LayerChip layer={ev.env_layer} />
        <span className="grow" />
        <span className="text-sm text-faint">
          {[ev.publisher, ev.id, ev.date].filter(Boolean).join(" · ")}
        </span>
      </div>
    </Card>
    {open && <EvidenceDialog ev={ev} onClose={() => setOpen(false)} />}
    </>
  );
}
