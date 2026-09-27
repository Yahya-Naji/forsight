import { supabase } from "@/lib/supabase";
import EvidenceCard from "@/components/EvidenceCard";
import { PILLAR_LABEL } from "@/components/chips";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Evidence() {
  const { data } = await supabase.from("evidence")
    .select("id,claim,class,confidence,env_layer,quote_span,pillar,created_at,evidence_sources(documents(source_registry(publisher,tier)))")
    .order("id");
  const rows = (data ?? []).map((e: any) => {
    const src = e.evidence_sources?.[0]?.documents?.source_registry;
    return { ...e, publisher: src?.publisher, tier: src?.tier,
      date: e.created_at ? new Date(e.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : null };
  });
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <div className="kicker">Register</div>
        <h1 className="display" style={{ fontWeight: 700, fontSize: 30, margin: "4px 0 0", letterSpacing: -0.4 }}>Evidence</h1>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {rows.map(ev => (
          <div key={ev.id}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--faint)", letterSpacing: 1, margin: "0 0 6px 2px" }}>
              {PILLAR_LABEL[ev.pillar] ?? ev.pillar}
            </div>
            <EvidenceCard ev={ev} />
          </div>
        ))}
        {!rows.length && <div className="card" style={{ padding: 18, fontSize: 13, color: "var(--faint)" }}>No evidence yet — run collection, extraction and rules.</div>}
      </div>
    </div>
  );
}
