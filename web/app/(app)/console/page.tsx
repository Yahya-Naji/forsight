import Link from "next/link";
import { supabase } from "@/lib/supabase";
import GateCard from "@/components/GateCard";
import SignalMeter from "@/components/SignalMeter";
import { PILLAR_LABEL } from "@/components/chips";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Overview() {
  const [ev, docs, srcs, gates, signals, reports, recentDocs] = await Promise.all([
    supabase.from("evidence").select("id", { count: "exact", head: true }),
    supabase.from("documents").select("id", { count: "exact", head: true }),
    supabase.from("source_registry").select("id", { count: "exact", head: true }),
    supabase.from("validation_gates").select("*").order("id"),
    supabase.from("signals").select("*").in("strength", ["STRONG", "STRONG_EMERGING", "EMERGING"]).limit(5),
    supabase.from("reports").select("id,title,status,created_at").order("created_at", { ascending: false }).limit(5),
    supabase.from("documents").select("title,retrieved_at,registry_id,source_registry(publisher,tier)").order("retrieved_at", { ascending: false }).limit(8),
  ]);
  const openGates = (gates.data ?? []).filter(g => g.status === "OPEN");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <section className="aurora" style={{ padding: "34px 38px 26px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 24, flexWrap: "wrap" }}>
          <div>
            <div className="kicker" style={{ color: "#93A7E8" }}>Strategic foresight · UAE defence</div>
            <h1 className="display" style={{ fontWeight: 700, fontSize: 40, margin: "10px 0 0", letterSpacing: -0.5 }}>Intelligence, with receipts.</h1>
            <div style={{ fontSize: 14, color: "#B8C4EE", marginTop: 8 }}>Every claim below traces to a source. Nothing here is generated from a prompt.</div>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {[["evidence", ev.count], ["documents", docs.count], ["sources", srcs.count]].map(([k, v]) => (
              <div key={String(k)} style={{ textAlign: "center", background: "rgba(255,255,255,.06)", border: "1px solid rgba(255,255,255,.12)", borderRadius: 14, padding: "14px 22px" }}>
                <div className="display" style={{ fontWeight: 700, fontSize: 28 }}>{v ?? 0}</div>
                <div style={{ fontSize: 11, color: "#9FB0E6", marginTop: 2 }}>{k}</div>
              </div>
            ))}
            <div style={{ textAlign: "center", background: "rgba(255,183,77,.12)", border: "1px solid rgba(255,183,77,.35)", borderRadius: 14, padding: "14px 22px" }}>
              <div className="display" style={{ fontWeight: 700, fontSize: 28, color: "#FFC96B" }}>{openGates.length}</div>
              <div style={{ fontSize: 11, color: "#E8BE85", marginTop: 2 }}>gates open</div>
            </div>
          </div>
        </div>
        <div style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 14, background: "rgba(10,14,40,.55)", border: "1px solid rgba(255,255,255,.1)", borderRadius: 12, padding: "10px 16px", overflow: "hidden" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 7, color: "#7EE0A9", fontWeight: 600, fontSize: 12.5, flexShrink: 0 }}>
            <span style={{ width: 7, height: 7, borderRadius: 4, background: "#4ADE80" }} />DAILY RUN
          </span>
          <div className="ticker">
            <div className="ticker-track">
              {(recentDocs.data ?? []).map((d: any, i: number) => (
                <span key={i}>{d.source_registry?.publisher ?? "unknown"} · <b style={{ color: "#fff" }}>Tier {d.source_registry?.tier ?? "?"}</b></span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.4fr", gap: 20 }}>
        <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h2 className="section-title">Validation gates</h2>
          </div>
          {(gates.data ?? []).map(g => (
            <GateCard key={g.id} id={g.id} status={g.status}
              blocks={g.status === "OPEN" ? `${g.blocks} — no UAE-layer Class A/B evidence yet.` : g.blocks} />
          ))}
          {!gates.data?.length && <div className="card" style={{ padding: 16, fontSize: 13, color: "var(--faint)" }}>No gates yet — run the rules engine.</div>}
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <h2 className="section-title">Signals</h2>
          <div className="card" style={{ padding: "4px 16px" }}>
            {(signals.data ?? []).map((s, i, arr) => (
              <div key={s.id} className="row" style={{ gap: 14, padding: "13px 0", borderBottom: i < arr.length - 1 ? "1px solid var(--line-soft)" : "none" }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--accent)", width: 84, flexShrink: 0 }}>{s.id}</span>
                <span style={{ fontSize: 13, color: "var(--ink-2)", flexGrow: 1 }}>{s.statement}</span>
                <SignalMeter strength={s.strength} />
              </div>
            ))}
            {!signals.data?.length && <div style={{ padding: 16, fontSize: 13, color: "var(--faint)" }}>No admitted signals yet.</div>}
          </div>
          <h2 className="section-title" style={{ marginTop: 6 }}>Recent reports</h2>
          <div className="card" style={{ padding: "4px 16px" }}>
            {(reports.data ?? []).map((r, i, arr) => (
              <div key={r.id} className="row" style={{ padding: "13px 0", borderBottom: i < arr.length - 1 ? "1px solid var(--line-soft)" : "none" }}>
                <Link href={`/reports/${r.id}`} style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)", flexGrow: 1 }}>{r.title}</Link>
                <span className={`chip ${r.status === "GATES_OPEN" ? "chip-open" : "chip-conf"}`}>{r.status.replace("_", " ")}</span>
                <span style={{ fontSize: 12, color: "var(--ghost)" }}>{new Date(r.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span>
              </div>
            ))}
            {!reports.data?.length && <div style={{ padding: 16, fontSize: 13, color: "var(--faint)" }}>No reports generated yet.</div>}
          </div>
        </section>
      </div>
    </div>
  );
}
