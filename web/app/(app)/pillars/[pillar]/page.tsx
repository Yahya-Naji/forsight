import Link from "next/link";
import { supabase } from "@/lib/supabase";
import EvidenceCard from "@/components/EvidenceCard";
import SignalMeter from "@/components/SignalMeter";
import { PILLAR_LABEL } from "@/components/chips";
import AddTopic from "@/components/AddTopic";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Pillar({ params, searchParams }: {
  params: { pillar: string }; searchParams: { topic?: string };
}) {
  const pillar = params.pillar.toUpperCase();
  const name = PILLAR_LABEL[pillar] ?? pillar;

  const [topicsQ, evidenceQ, signalsQ, gateQ, srcQ, tsQ] = await Promise.all([
    supabase.from("topics").select("id,name").eq("pillar", pillar).order("id"),
    supabase.from("evidence")
      .select("id,claim,class,confidence,env_layer,quote_span,topic_id,created_at,evidence_sources(documents(url,title,published_on,source_registry(publisher,tier)))")
      .eq("pillar", pillar).order("class").order("created_at", { ascending: false }).limit(40),
    supabase.from("signals").select("*").eq("pillar", pillar),
    supabase.from("validation_gates").select("*").ilike("id", `%${pillar.slice(0, 2)}%`),
    supabase.from("source_registry").select("id,publisher,tier,method,pillars").order("tier").order("id"),
    supabase.from("topic_sources").select("topic_id,registry_id"),
  ]);

  const topics = topicsQ.data ?? [];
  const allSources = srcQ.data ?? [];
  const pubById = new Map(allSources.map(s => [s.id, s]));
  // which sources feed each topic, so an empty topic reads as unconfigured
  // rather than as an absence of news
  const srcByTopic = new Map<string, any[]>();
  for (const t of tsQ.data ?? []) {
    srcByTopic.set(t.topic_id, [...(srcByTopic.get(t.topic_id) ?? []), pubById.get(t.registry_id)].filter(Boolean));
  }
  const allEv = (evidenceQ.data ?? []).map((e: any) => {
    const src = e.evidence_sources?.[0]?.documents;
    return { ...e, publisher: src?.source_registry?.publisher, tier: src?.source_registry?.tier,
      url: src?.url ?? null, doc_title: src?.title ?? null,
      date: e.created_at ? new Date(e.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : null };
  });
  const counts: Record<string, number> = {};
  for (const e of allEv) counts[e.topic_id] = (counts[e.topic_id] ?? 0) + 1;
  const active = searchParams.topic ?? topics.find(t => counts[t.id])?.id ?? topics[0]?.id;
  const shown = allEv.filter(e => e.topic_id === active);
  const gate = (gateQ.data ?? [])[0];
  const layers: Record<string, number> = {};
  for (const e of allEv) layers[e.env_layer] = (layers[e.env_layer] ?? 0) + 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
        <div>
          <div className="kicker">Pillar</div>
          <h1 className="display" style={{ fontWeight: 700, fontSize: 30, margin: "4px 0 0", letterSpacing: -0.4 }}>{name}</h1>
        </div>
        <div className="row" style={{ gap: 8 }}>
          {gate && (
            <span className={`chip ${gate.status === "OPEN" ? "chip-open" : "chip-passed"}`} style={{ borderRadius: 999, padding: "6px 13px", fontSize: 11.5 }}>
              Gate {gate.id} · {gate.status}
            </span>
          )}
          <span className="chip chip-conf" style={{ borderRadius: 999, padding: "6px 13px", fontSize: 11.5 }}>
            UAE {layers.UAE ?? 0} · Regional {layers.REGIONAL ?? 0} · Global {layers.GLOBAL ?? 0}
          </span>
          <Link href="/generate"><button className="pill-btn">Generate brief</button></Link>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "290px 1fr 260px", gap: 20 }}>
        <div>
          <div className="row" style={{ justifyContent: "space-between", paddingBottom: 10 }}>
            <span className="kicker">Topics</span>
            <AddTopic pillar={pillar} pillarLabel={name} sources={allSources as any} />
          </div>
          {topics.map(t => {
            const on = t.id === active;
            const feeds = srcByTopic.get(t.id) ?? [];
            return (
              <Link key={t.id} href={`/pillars/${pillar}?topic=${t.id}`} style={{
                display: "block", borderTop: "1px solid #E3E7F3", padding: "13px 2px",
              }}>
                <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
                  <span className="display" style={{ fontSize: 15, fontWeight: on ? 600 : 500, color: on ? "var(--ink)" : "#A6ACC4" }}>{t.name}</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: on ? "var(--accent)" : "#A6ACC4" }}>{counts[t.id] ?? 0}</span>
                </div>
                {/* Unbound is not silent: Lane A still sweeps at pillar level. It
                    means collection is not aimed at this topic specifically. */}
                <div style={{ fontSize: 11, color: feeds.length ? "var(--faint)" : "var(--amber-ink)", marginTop: 4 }}>
                  {feeds.length
                    ? `${feeds.length} source${feeds.length > 1 ? "s" : ""} · ${feeds.slice(0, 2).map((f: any) => f.publisher).join(", ")}${feeds.length > 2 ? "…" : ""}`
                    : "no sources bound — collected at pillar level only"}
                </div>
              </Link>
            );
          })}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, minWidth: 0 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h2 className="section-title">Evidence · {topics.find(t => t.id === active)?.name ?? "—"}</h2>
            <span style={{ fontSize: 12, color: "var(--faint)" }}>sorted by class, then recency</span>
          </div>
          {shown.map(ev => <EvidenceCard key={ev.id} ev={ev} />)}
          {!shown.length && <div className="card" style={{ padding: 18, fontSize: 13, color: "var(--faint)" }}>No evidence for this topic yet — run collection and extraction.</div>}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="kicker" style={{ paddingTop: 6 }}>Signals in this pillar</div>
          {(signalsQ.data ?? []).map(s => (
            <div key={s.id} className="card" style={{ padding: "14px 16px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--accent)" }}>{s.id}</div>
              <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 6, lineHeight: 1.45 }}>{s.statement}</div>
              <div className="row" style={{ gap: 8, marginTop: 10 }}>
                <SignalMeter strength={s.strength} />
                <span style={{ fontSize: 11, color: "var(--faint)" }}>{(s.strength ?? "").replace("_", "-").toLowerCase()}</span>
              </div>
            </div>
          ))}
          <div style={{ background: "#F8F9FD", border: "1px dashed #D5DCEF", borderRadius: "var(--radius)", padding: "14px 16px", fontSize: 12, color: "#7A8098", lineHeight: 1.5 }}>
            Strength is computed from independent publishers, never from row counts. A single-source signal stays weak until corroborated.
          </div>
        </div>
      </div>
    </div>
  );
}
