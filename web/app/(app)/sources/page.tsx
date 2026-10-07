import { supabase } from "@/lib/supabase";
import SourceTable from "@/components/SourceTable";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Sources() {
  const [regQ, docQ, tsQ] = await Promise.all([
    supabase.from("source_registry").select("*").order("tier").order("id"),
    supabase.from("documents").select("registry_id,retrieved_at"),
    supabase.from("topic_sources").select("registry_id,topic_id"),
  ]);

  const reg = regQ.data ?? [];
  const byReg = new Map<string, { n: number; last: string | null }>();
  for (const d of docQ.data ?? []) {
    const cur = byReg.get(d.registry_id) ?? { n: 0, last: null };
    cur.n++;
    if (!cur.last || (d.retrieved_at && d.retrieved_at > cur.last)) cur.last = d.retrieved_at;
    byReg.set(d.registry_id, cur);
  }
  const topicsByReg = new Map<string, string[]>();
  for (const t of tsQ.data ?? []) {
    topicsByReg.set(t.registry_id, [...(topicsByReg.get(t.registry_id) ?? []), t.topic_id]);
  }

  const all = reg.map(r => ({
    ...r,
    docs: byReg.get(r.id)?.n ?? 0,
    last: byReg.get(r.id)?.last ?? null,
    topics: topicsByReg.get(r.id) ?? [],
  }));

  // Archived (026): kept so collected documents keep their publisher and tier,
  // but no longer collected because they carry no EW coverage.
  const rows = all.filter(r => !r.archived_at);
  const archived = all.filter(r => r.archived_at);
  const silent = rows.filter(r => r.docs === 0).length;
  const tiers = [1, 2, 3, 4].map(t => ({ t, n: rows.filter(r => r.tier === t).length }));

  return (
    <div>
      <div className="kicker">Collection</div>
      <h1 className="display" style={{ fontWeight: 700, fontSize: 26, margin: "4px 0 8px", letterSpacing: -0.4 }}>
        Where the evidence comes from
      </h1>
      <p style={{ fontSize: 13.5, color: "var(--muted)", maxWidth: "68ch", lineHeight: 1.6 }}>
        Every source the system is allowed to read, and what each has actually returned.
        Tier decides how much weight a claim carries downstream, so a source that stops
        answering quietly weakens the evidence base — test one to see what it returns right now.
      </p>

      <div className="row" style={{ gap: 10, margin: "20px 0 20px", flexWrap: "wrap" }}>
        <Stat n={rows.length} k="registered sources" />
        {tiers.map(({ t, n }) => <Stat key={t} n={n} k={`tier ${t}`} />)}
        <Stat n={silent} k="never returned a document" amber={silent > 0} />
      </div>

      <SourceTable rows={rows as any} />

      {archived.length > 0 && (
        <details className="card" style={{ marginTop: 20, padding: "14px 18px" }}>
          <summary style={{ cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
            {archived.length} archived sources · no longer collected
          </summary>
          <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.55, margin: "8px 0 10px" }}>
            Electronic Warfare is the core pillar, so sources with no EW coverage are no longer
            read. Documents already collected from them keep their publisher and tier.
          </p>
          {archived.map(r => (
            <div key={r.id} className="row" style={{ gap: 10, padding: "7px 0", borderTop: "1px solid var(--line)", fontSize: 12.5 }}>
              <span style={{ fontWeight: 600, minWidth: 220 }}>{r.publisher}</span>
              <span className={`chip ${r.tier === 1 ? "chip-tier1" : "chip-tier"}`}>T{r.tier}</span>
              <span style={{ color: "var(--muted)", flex: 1 }}>{r.archived_reason}</span>
              <span style={{ color: "var(--faint)" }}>{r.docs} docs</span>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}

function Stat({ n, k, amber }: { n: number; k: string; amber?: boolean }) {
  return (
    <div className="card" style={{ padding: "12px 16px", minWidth: 108 }}>
      <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.4,
                    color: amber ? "var(--amber-ink)" : "var(--ink)" }}>{n}</div>
      <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>{k}</div>
    </div>
  );
}
