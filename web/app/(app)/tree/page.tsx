import { supabase } from "@/lib/supabase";
import { Kicker } from "@/components/ui/section";
import EwTree, { type TreeData, type TreeTopic } from "@/components/EwTree";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// The EW tree (migration 031) drawn as a radial tree: EW at the centre, the
// eight branches around it, and each branch's manual functions and homed
// topics on the outer ring. A topic's cross-links to functions in other
// branches are drawn when it is selected.

const AGGREGATOR = "SRC-API-001";
const READY_PUBLISHERS = 3;
const LIVE_STRENGTHS = ["EMERGING", "STRONG_EMERGING", "STRONG"];

async function all<T>(build: () => any): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; ; from += 1000) {
    const { data } = await build().range(from, from + 999);
    out.push(...(data ?? []));
    if (!data || data.length < 1000) return out;
  }
}

export default async function TreePage() {
  const [nodesRes, topicsRes, evidence, links, docs, sigLinks, signals] = await Promise.all([
    supabase.from("nodes").select("id,parent_id,kind,name,sort"),
    supabase.from("topics").select("id,name,node_id,ew_functions,pillar,ew_impact").is("retired_at", null),
    all<any>(() => supabase.from("evidence").select("id,topic_id,class").is("archived_at", null)),
    all<any>(() => supabase.from("evidence_sources").select("evidence_id,document_id")),
    all<any>(() => supabase.from("documents").select("id,registry_id")),
    all<any>(() => supabase.from("signal_evidence").select("signal_id,evidence_id")),
    all<any>(() => supabase.from("signals").select("id,strength")),
  ]);

  const regOf = new Map(docs.map(d => [d.id, d.registry_id]));
  const pubsOfEv = new Map<string, Set<string>>();
  for (const l of links) {
    const reg = regOf.get(l.document_id);
    if (!reg || reg === AGGREGATOR) continue;
    if (!pubsOfEv.has(l.evidence_id)) pubsOfEv.set(l.evidence_id, new Set());
    pubsOfEv.get(l.evidence_id)!.add(reg);
  }
  const strengthOf = new Map(signals.map(s => [s.id, s.strength]));
  const sigsOfEv = new Map<string, string[]>();
  for (const l of sigLinks) sigsOfEv.set(l.evidence_id, [...(sigsOfEv.get(l.evidence_id) ?? []), l.signal_id]);

  const topics = (topicsRes.data ?? []).map((t: any) => {
    const ev = evidence.filter(e => e.topic_id === t.id);
    const pubs = new Set<string>(), sigs = new Set<string>();
    for (const e of ev) {
      pubsOfEv.get(e.id)?.forEach(p => pubs.add(p));
      sigsOfEv.get(e.id)?.forEach(s => sigs.add(s));
    }
    const live = [...sigs].filter(s => LIVE_STRENGTHS.includes(strengthOf.get(s) ?? "")).length;
    const status: TreeTopic["status"] = !ev.length ? "Empty" : pubs.size >= READY_PUBLISHERS && live >= 1 ? "Ready" : "Thin";
    return {
      id: t.id, name: t.name, nodeId: t.node_id, functions: t.ew_functions ?? [], pillar: t.pillar,
      impact: t.ew_impact, evidence: ev.length, classA: ev.filter(e => e.class === "A").length,
      publishers: pubs.size, signals: sigs.size, liveSignals: live, status,
    };
  });

  const data: TreeData = { nodes: nodesRes.data ?? [], topics };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Kicker>Electronic warfare · structure</Kicker>
        <h1 className="display mt-2 text-[32px] font-semibold tracking-tight">The EW tree</h1>
        <p className="mt-1 max-w-[70ch] text-base text-muted">
          Electronic Warfare at the centre, its eight branches around it, and each branch&apos;s manual
          functions and topics on the outer ring. Select a topic to see the functions it reaches in
          other branches, and the evidence behind it.
        </p>
      </div>
      <EwTree data={data} />
    </div>
  );
}
