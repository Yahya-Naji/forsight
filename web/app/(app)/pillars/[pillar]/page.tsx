import Link from "next/link";
import { supabase } from "@/lib/supabase";
import EvidenceCard from "@/components/EvidenceCard";
import SignalMeter from "@/components/SignalMeter";
import AddTopic from "@/components/AddTopic";
import { Card } from "@/components/ui/card";
import { Kicker } from "@/components/ui/section";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// A pillar is a node of the EW tree (migration 031): Electronic Warfare at the
// root, its eight sub-pillars (five EW branches plus the Cybersecurity, AI and
// Procurement lenses), and their topics. Old flat-pillar URLs still resolve.

const LEGACY: Record<string, string> = {
  ELECTRONIC_WARFARE: "EW", CYBERSECURITY: "CYBER", AI: "AI", PROCUREMENT: "PROCUREMENT",
};
const PILLAR_OF: Record<string, string> = { CYBER: "CYBERSECURITY", AI: "AI", PROCUREMENT: "PROCUREMENT" };
const STRENGTH_RANK: Record<string, number> = { STRONG: 0, STRONG_EMERGING: 1, EMERGING: 2, WEAK: 3 };

async function all<T>(build: () => any): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; ; from += 1000) {
    const { data } = await build().range(from, from + 999);
    out.push(...(data ?? []));
    if (!data || data.length < 1000) return out;
  }
}

export default async function Pillar({ params, searchParams }: {
  params: { pillar: string }; searchParams: { topic?: string };
}) {
  const raw = decodeURIComponent(params.pillar).toUpperCase();
  const nodeId = LEGACY[raw] ?? raw;

  const [nodesQ, reachQ, topicsQ, fnQ, srcQ, tsQ, gatesQ] = await Promise.all([
    supabase.from("nodes").select("id,parent_id,kind,name,sort").order("sort"),
    supabase.rpc("node_topics", { root: nodeId }),
    supabase.from("topics").select("id,name,ew_impact,node_id,pillar,ew_functions").is("retired_at", null).order("id"),
    supabase.from("ew_functions").select("id,division,name").order("division").order("id"),
    supabase.from("source_registry").select("id,publisher,tier,method,pillars").is("archived_at", null).order("tier").order("id"),
    supabase.from("topic_sources").select("topic_id,registry_id"),
    supabase.from("validation_gates").select("id,status,blocks").order("id"),
  ]);
  const nodes = nodesQ.data ?? [];
  const node = nodes.find(n => n.id === nodeId);
  if (!node) {
    return <Card className="p-6 text-base text-muted">No pillar called “{raw}”. <Link href="/pillars/EW" className="text-accent">Open Electronic Warfare</Link>.</Card>;
  }
  const nameOf = new Map(nodes.map(n => [n.id, n.name]));
  const parent = nodes.find(n => n.id === node.parent_id);
  const subPillars = nodes.filter(n => n.parent_id === node.id && n.kind === "branch");
  const functions = nodes.filter(n => n.parent_id === node.id && n.kind === "function");

  const via = new Map<string, string>((reachQ.data ?? []).map((r: any) => [r.topic_id, r.via]));
  const topics = (topicsQ.data ?? []).filter(t => via.has(t.id));
  const topicIds = topics.map(t => t.id);

  // Light rows for counts across the whole branch; full rows only for the open topic.
  const evLite = topicIds.length ? await all<any>(() => supabase.from("evidence")
    .select("id,topic_id,env_layer,class").in("topic_id", topicIds).is("archived_at", null)) : [];
  const counts: Record<string, number> = {}, layers: Record<string, number> = {};
  for (const e of evLite) {
    counts[e.topic_id] = (counts[e.topic_id] ?? 0) + 1;
    layers[e.env_layer] = (layers[e.env_layer] ?? 0) + 1;
  }
  const active = searchParams.topic && via.has(searchParams.topic)
    ? searchParams.topic : [...topics].sort((a, b) => (counts[b.id] ?? 0) - (counts[a.id] ?? 0))[0]?.id;
  const [shownQ, sigLinks] = await Promise.all([
    active ? supabase.from("evidence")
      .select("id,claim,class,confidence,env_layer,quote_span,topic_id,created_at,evidence_sources(documents(url,title,published_on,source_registry(publisher,tier)))")
      .eq("topic_id", active).is("archived_at", null).order("class").order("created_at", { ascending: false }).limit(40)
      : Promise.resolve({ data: [] as any[] }),
    evLite.length ? all<any>(() => supabase.from("signal_evidence").select("signal_id,evidence_id")
      .in("evidence_id", evLite.map(e => e.id).slice(0, 900))) : Promise.resolve([] as any[]),
  ]);
  const sigIds = [...new Set(sigLinks.map(l => l.signal_id))];
  const signals = sigIds.length
    ? ((await supabase.from("signals").select("id,statement,strength,direction").in("id", sigIds)).data ?? [])
        .sort((a, b) => STRENGTH_RANK[a.strength] - STRENGTH_RANK[b.strength]).slice(0, 8)
    : [];
  const shown = (shownQ.data ?? []).map((e: any) => {
    const src = e.evidence_sources?.[0]?.documents;
    return { ...e, publisher: src?.source_registry?.publisher, tier: src?.source_registry?.tier,
      url: src?.url ?? null, doc_title: src?.title ?? null,
      date: e.created_at ? new Date(e.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : null };
  });

  // Topics grouped by the sub-pillar that homes them.
  const groups = new Map<string, typeof topics>();
  for (const t of topics) {
    const key = node.kind === "root" ? t.node_id ?? "?" : via.get(t.id) === "home" ? node.id : t.node_id ?? "?";
    groups.set(key, [...(groups.get(key) ?? []), t]);
  }
  const groupOrder = node.kind === "root"
    ? subPillars.map(b => b.id).filter(id => groups.has(id))
    : [node.id, ...[...groups.keys()].filter(k => k !== node.id)].filter(k => groups.has(k));

  const allSources = srcQ.data ?? [];
  const pubById = new Map(allSources.map(s => [s.id, s]));
  const srcByTopic = new Map<string, any[]>();
  for (const t of tsQ.data ?? [])
    srcByTopic.set(t.topic_id, [...(srcByTopic.get(t.topic_id) ?? []), pubById.get(t.registry_id)].filter(Boolean));

  const pillarEnum = PILLAR_OF[node.id] ?? "ELECTRONIC_WARFARE";
  const gates = (gatesQ.data ?? []).filter(g => node.kind === "root" || g.id === `VG-${pillarEnum.slice(0, 2)}-01`);
  const openGates = gates.filter(g => g.status === "OPEN").length;
  const href = (topic?: string) => `/pillars/${node.id}${topic ? `?topic=${topic}` : ""}`;
  const activeTopic = topics.find(t => t.id === active);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-muted">
            {parent && <><Link href={`/pillars/${parent.id}`} className="hover:text-accent">{parent.name}</Link><span>›</span></>}
            <span>{node.kind === "root" ? "Core pillar" : "Sub-pillar"}</span>
          </nav>
          <h1 className="display mt-1 text-[32px] font-semibold tracking-tight">{node.name}</h1>
          <p className="mt-1 text-sm text-muted">
            {topics.length} topics · {evLite.length} live evidence rows
            {node.kind !== "root" && ` · ${topics.filter(t => via.get(t.id) === "link").length} linked from other sub-pillars`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${openGates ? "bg-amber-chip text-amber-ink" : "bg-green-chip text-green-ink"}`}>
            {openGates ? `${openGates} UAE gate${openGates > 1 ? "s" : ""} open` : "UAE gate passed"}
          </span>
          <span className="rounded-full bg-line-soft px-3 py-1.5 text-xs font-semibold text-ink-2">
            UAE {layers.UAE ?? 0} · Regional {layers.REGIONAL ?? 0} · Global {layers.GLOBAL ?? 0}
          </span>
          <Link href="/generate" className="pill-btn">Generate brief</Link>
        </div>
      </div>

      {node.kind === "root" && (
        <section className="flex flex-col gap-3">
          <Kicker>Sub-pillars</Kicker>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {subPillars.map(b => {
              const home = topics.filter(t => t.node_id === b.id);
              const ev = home.reduce((n, t) => n + (counts[t.id] ?? 0), 0);
              return (
                <Link key={b.id} href={`/pillars/${b.id}`}
                      className="group flex flex-col gap-1 rounded-[14px] border border-line bg-card px-4 py-3.5 transition
                                 hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md">
                  <span className="text-sm font-semibold text-ink">{b.name}</span>
                  <span className="text-xs text-muted">{home.length} topics · {ev} evidence</span>
                  <span className="text-xs text-accent opacity-0 transition group-hover:opacity-100">Open →</span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {functions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <Kicker className="mr-1">Manual functions</Kicker>
          {functions.map(f => (
            <span key={f.id} className="rounded-full border border-line bg-card px-2.5 py-1 text-xs text-ink-2">{f.name}</span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[300px_minmax(0,1fr)_280px]">
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <Kicker>Topics</Kicker>
            <AddTopic pillar={pillarEnum} pillarLabel={node.name} sources={allSources as any}
                      ewFunctions={fnQ.data ?? []} nodeId={node.kind === "branch" ? node.id : undefined} />
          </div>
          {groupOrder.map(g => (
            <div key={g} className="flex flex-col">
              <div className="flex items-center justify-between pb-1.5">
                <span className="text-xs font-semibold text-ink-2">
                  {g === node.id ? `In ${node.name}` : node.kind === "root" ? nameOf.get(g) : `Linked from ${nameOf.get(g) ?? "another pillar"}`}
                </span>
                {node.kind === "root" && <Link href={`/pillars/${g}`} className="text-xs text-accent">Open</Link>}
              </div>
              <Card className="px-3 py-1">
                <div className="[&>*]:border-t [&>*]:border-line-soft [&>*:first-child]:border-t-0">
                  {groups.get(g)!.map(t => {
                    const on = t.id === active, feeds = srcByTopic.get(t.id) ?? [];
                    return (
                      <Link key={t.id} href={href(t.id)} className="block py-2.5">
                        <div className="flex items-start justify-between gap-2">
                          <span className={`text-sm leading-snug ${on ? "font-semibold text-ink" : "text-muted"}`}>{t.name}</span>
                          <span className={`font-mono text-xs tabular-nums ${on ? "text-accent" : "text-faint"}`}>{counts[t.id] ?? 0}</span>
                        </div>
                        {on && t.ew_impact && (
                          <p className="mt-1 text-xs leading-relaxed text-ink-2"><b className="text-accent-deep">EW impact · </b>{t.ew_impact}</p>
                        )}
                        <p className={`mt-0.5 text-[11px] ${feeds.length ? "text-faint" : "text-amber-ink"}`}>
                          {t.id} · {feeds.length ? `${feeds.length} source${feeds.length > 1 ? "s" : ""} bound` : "no sources bound"}
                        </p>
                      </Link>
                    );
                  })}
                </div>
              </Card>
            </div>
          ))}
          {!topics.length && <Card className="p-4 text-sm text-faint">No topics reach this pillar yet.</Card>}
        </div>

        <div className="flex min-w-0 flex-col gap-3">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="section-title">Evidence · {activeTopic?.name ?? "—"}</h2>
            <span className="shrink-0 text-xs text-faint">by class, then recency</span>
          </div>
          {shown.map((ev: any) => <EvidenceCard key={ev.id} ev={ev} />)}
          {!shown.length && <Card className="p-5 text-sm text-faint">No evidence for this topic yet.</Card>}
        </div>

        <div className="flex flex-col gap-3">
          <Kicker className="pt-1.5">Strongest signals in {node.name}</Kicker>
          {signals.map(s => (
            <Card key={s.id} className="px-4 py-3.5">
              <div className="text-[11px] font-bold text-accent">{s.id}</div>
              <div className="mt-1.5 text-sm leading-snug text-ink-2">{s.statement}</div>
              <div className="mt-2.5 flex items-center gap-2">
                <SignalMeter strength={s.strength} />
                <span className="text-[11px] text-faint">{(s.strength ?? "").replace("_", "-").toLowerCase()}</span>
              </div>
            </Card>
          ))}
          {!signals.length && <Card className="p-4 text-sm text-faint">No signals yet.</Card>}
          <div className="rounded-[14px] border border-dashed border-line bg-paper px-4 py-3.5 text-xs leading-relaxed text-muted">
            Strength is computed from independent publishers, never from row counts. A single-source
            signal stays weak until corroborated.
          </div>
        </div>
      </div>
    </div>
  );
}
