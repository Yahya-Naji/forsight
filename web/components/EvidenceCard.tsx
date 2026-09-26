import { TierChip, ClassChip, LayerChip, ConfChip } from "./chips";

export type Evidence = {
  id: string; claim: string; class: string | null; confidence: string | null;
  env_layer: string | null; quote_span?: string | null;
  publisher?: string | null; tier?: number | null; date?: string | null;
};

export default function EvidenceCard({ ev, compact }: { ev: Evidence; compact?: boolean }) {
  return (
    <div className="card" style={{ padding: compact ? "13px 15px" : "16px 18px" }}>
      <div style={{ fontSize: compact ? 13.5 : 14.5, fontWeight: 600, lineHeight: 1.45 }}>{ev.claim}</div>
      {!compact && ev.quote_span && <div className="quote">&ldquo;{ev.quote_span}&rdquo;</div>}
      <div className="row" style={{ gap: 7, marginTop: compact ? 9 : 12 }}>
        <TierChip tier={ev.tier} />
        <ClassChip c={ev.class} />
        <ConfChip c={ev.confidence} />
        <LayerChip layer={ev.env_layer} />
        <span style={{ flexGrow: 1 }} />
        <span style={{ fontSize: 12, color: "var(--faint)" }}>
          {[ev.publisher, ev.id, ev.date].filter(Boolean).join(" · ")}
        </span>
      </div>
    </div>
  );
}
