import { supabase } from "@/lib/supabase";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Aurora, Kicker, Stat } from "@/components/ui/section";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableNum,
} from "@/components/ui/table";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// The consultant's view of the EW tree (migration 031): one row per branch, so
// before writing a report they can see which branches can carry claims, how
// firmly to word them, what came in since last time, and which way the
// signals are moving.

const READY_PUBLISHERS = 3;                          // the seed's 3-publisher target
const LIVE_STRENGTHS = ["EMERGING", "STRONG_EMERGING", "STRONG"];
const STRENGTH_RANK: Record<string, number> = { WEAK: 0, EMERGING: 1, STRONG_EMERGING: 2, STRONG: 3 };
const AGGREGATOR = "SRC-API-001";                    // not a publisher; never counted as one
const DAY = 86_400_000;

// Ordinal blue ramp for A → C, validated (dataviz --ordinal). D is a policy
// construct, not a weaker C, so it sits outside the ramp in neutral grey.
const CLASS_FILL: Record<string, string> = { A: "#184f95", B: "#2a78d6", C: "#86b6ef", D: "#c9cdd8" };
const CLASS_LABEL: Record<string, string> = {
  A: "Class A · fact", B: "Class B · corroborated", C: "Class C · hypothesis", D: "Class D · policy",
};
// Diverging pair for signal direction, validated; uncertain is the grey midpoint.
const DIR_FILL = { STRENGTHENING: "#2a78d6", UNCERTAIN: "#d9d8d4", WEAKENING: "#e34948" };

type Status = "Ready" | "Thin" | "Empty";

async function all<T>(build: () => any): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; ; from += 1000) {
    const { data } = await build().range(from, from + 999);
    out.push(...(data ?? []));
    if (!data || data.length < 1000) return out;
  }
}

/** A focusable mark whose value appears on hover or focus. Every value it
 *  shows is also in the table, so the tooltip never gates anything. */
function Tip({ label, children, className, style }: {
  label: string; children?: React.ReactNode; className?: string; style?: React.CSSProperties;
}) {
  return (
    <span tabIndex={0} aria-label={label} className={`group relative outline-none ${className ?? ""}`}
          style={style}>
      {children}
      <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5
            -translate-x-1/2 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-xs text-white
            opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus:opacity-100">
        {label}
      </span>
    </span>
  );
}

function StatusChip({ status }: { status: Status }) {
  const look = {
    Ready: { icon: "✓", cls: "bg-green-chip text-green-ink" },
    Thin:  { icon: "!", cls: "bg-amber-chip text-amber-ink" },
    Empty: { icon: "○", cls: "bg-line-soft text-muted" },
  }[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-[6px] px-2 py-[3px] text-2xs font-bold ${look.cls}`}>
      <span aria-hidden>{look.icon}</span>{status}
    </span>
  );
}

/** Stacked bar of evidence by class; 2px surface gaps between segments. */
function TrustBar({ counts, total }: { counts: Record<string, number>; total: number }) {
  if (!total) return <span className="text-xs text-faint">—</span>;
  const present = ["A", "B", "C", "D"].filter(k => counts[k]);
  return (
    <div className="flex h-3 w-[160px] gap-[2px]">
      {present.map((k, i) => (
        <Tip key={k} label={`${CLASS_LABEL[k]}: ${counts[k]} of ${total}`}
             className={`h-full hover:brightness-110 focus:brightness-110
                         ${i === 0 ? "rounded-l-[4px]" : ""} ${i === present.length - 1 ? "rounded-r-[4px]" : ""}`}
             style={{ width: `${(counts[k] / total) * 100}%`, background: CLASS_FILL[k], minWidth: 3 }} />
      ))}
    </div>
  );
}

/** Weakening to the left of a centre line, strengthening to the right. */
function Momentum({ up, flat, down, max }: { up: number; flat: number; down: number; max: number }) {
  const w = (n: number) => `${max ? (n / max) * 50 : 0}%`;
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-3 w-[120px]">
        <span className="absolute left-1/2 top-[-2px] h-4 w-px bg-line" />
        {down > 0 && (
          <Tip label={`Weakening: ${down}`} className="absolute right-1/2 top-0 h-full rounded-l-[4px] mr-[2px]"
               style={{ width: w(down), background: DIR_FILL.WEAKENING }} />
        )}
        {up > 0 && (
          <Tip label={`Strengthening: ${up}`} className="absolute left-1/2 top-0 h-full rounded-r-[4px] ml-[2px]"
               style={{ width: w(up), background: DIR_FILL.STRENGTHENING }} />
        )}
      </div>
      <span className="font-mono text-xs tabular-nums text-muted">
        ↑{up} ↓{down}{flat ? ` · ${flat}?` : ""}
      </span>
    </div>
  );
}

function Legend({ items }: { items: [string, string][] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      {items.map(([fill, label]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-[2px]" style={{ background: fill }} />{label}
        </span>
      ))}
    </div>
  );
}

const fmtDate = (d?: string | null) =>
  d ? new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : null;

export default async function EWOverview() {
  const [branchRes, topicRes, evidence, links, docs, sigLinks, signals, gates] = await Promise.all([
    supabase.from("nodes").select("id,name,sort").eq("kind", "branch").order("sort"),
    supabase.from("topics").select("id,name,node_id").is("retired_at", null),
    all<any>(() => supabase.from("evidence").select("id,topic_id,class,env_layer").is("archived_at", null)),
    all<any>(() => supabase.from("evidence_sources").select("evidence_id,document_id")),
    all<any>(() => supabase.from("documents")
      .select("id,title,url,published_on,retrieved_at,registry_id,source_registry(publisher,tier)")),
    all<any>(() => supabase.from("signal_evidence").select("signal_id,evidence_id")),
    all<any>(() => supabase.from("signals").select("id,statement,strength,direction")),
    supabase.from("validation_gates").select("id,status"),
  ]);
  const branches = branchRes.data ?? [];
  const topicHome = new Map((topicRes.data ?? []).map((t: any) => [t.id, t.node_id]));

  // Which topics each branch reaches: homed there, or cross-linked through its
  // functions. node_topics() is the one definition, shared with node_rollup.
  const reach = await Promise.all(branches.map((b: any) =>
    supabase.rpc("node_topics", { root: b.id }).then(r => new Set((r.data ?? []).map((x: any) => x.topic_id)))));

  const docById = new Map(docs.map(d => [d.id, d]));
  const docsOfEv = new Map<string, string[]>();
  for (const l of links) docsOfEv.set(l.evidence_id, [...(docsOfEv.get(l.evidence_id) ?? []), l.document_id]);
  const sigsOfEv = new Map<string, string[]>();
  for (const l of sigLinks) sigsOfEv.set(l.evidence_id, [...(sigsOfEv.get(l.evidence_id) ?? []), l.signal_id]);
  const signalById = new Map(signals.map(s => [s.id, s]));
  const now = Date.now();

  const rows = branches.map((b: any, i: number) => {
    const topics = reach[i];
    const ev = evidence.filter(e => topics.has(e.topic_id));
    const classes: Record<string, number> = {};
    const docIds = new Set<string>(), pubs = new Set<string>(), sigIds = new Set<string>();
    let uae = 0;
    for (const e of ev) {
      classes[e.class] = (classes[e.class] ?? 0) + 1;
      if (e.env_layer === "UAE") uae++;
      for (const d of docsOfEv.get(e.id) ?? []) {
        docIds.add(d);
        const reg = docById.get(d)?.registry_id;
        if (reg && reg !== AGGREGATOR) pubs.add(reg);
      }
      for (const s of sigsOfEv.get(e.id) ?? []) sigIds.add(s);
    }
    const sigs = [...sigIds].map(id => signalById.get(id)).filter(Boolean);
    const collected = (days: number) => [...docIds].filter(d => {
      const at = docById.get(d)?.retrieved_at;
      return at && now - new Date(at).getTime() <= days * DAY;
    }).length;
    const live = sigs.filter((s: any) => LIVE_STRENGTHS.includes(s.strength)).length;
    const status: Status = !ev.length ? "Empty"
      : pubs.size >= READY_PUBLISHERS && live >= 1 ? "Ready" : "Thin";
    return {
      id: b.id, name: b.name, topics: topics.size, evidence: ev.length, classes, uae,
      publishers: pubs.size, signals: sigs.length, live, status,
      week: collected(7), month: collected(30),
      up: sigs.filter((s: any) => s.direction === "STRENGTHENING").length,
      flat: sigs.filter((s: any) => s.direction === "UNCERTAIN").length,
      down: sigs.filter((s: any) => s.direction === "WEAKENING").length,
    };
  });
  const maxDir = Math.max(1, ...rows.map(r => Math.max(r.up, r.down)));
  const ready = rows.filter(r => r.status === "Ready").length;
  const openGates = (gates.data ?? []).filter((g: any) => g.status === "OPEN").length;

  // A signal is shown under the branch that homes most of its evidence.
  const branchName = new Map(branches.map((b: any) => [b.id, b.name]));
  const homeOfSignal = (sid: string) => {
    const tally = new Map<string, number>();
    for (const l of sigLinks) if (l.signal_id === sid) {
      const e = evidence.find(x => x.id === l.evidence_id);
      const home = e && topicHome.get(e.topic_id);
      if (home) tally.set(home, (tally.get(home) ?? 0) + 1);
    }
    const top = [...tally.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
    return top ? branchName.get(top) : undefined;
  };
  const liveEvidence = new Set(evidence.map(e => e.id));
  const strongest = signals
    .filter(s => sigLinks.some(l => l.signal_id === s.id && liveEvidence.has(l.evidence_id)))
    .sort((a, b) => STRENGTH_RANK[b.strength] - STRENGTH_RANK[a.strength]
      || (a.direction === "STRENGTHENING" ? -1 : 0) - (b.direction === "STRENGTHENING" ? -1 : 0))
    .slice(0, 5);

  // Newest documents behind live evidence, by when we collected them.
  const evTopicsOfDoc = new Map<string, Set<string>>();
  for (const l of links) if (liveEvidence.has(l.evidence_id)) {
    const e = evidence.find(x => x.id === l.evidence_id);
    if (!evTopicsOfDoc.has(l.document_id)) evTopicsOfDoc.set(l.document_id, new Set());
    if (e) evTopicsOfDoc.get(l.document_id)!.add(e.topic_id);
  }
  const latest = [...evTopicsOfDoc.keys()].map(id => docById.get(id)).filter(Boolean)
    .sort((a: any, b: any) => +new Date(b.retrieved_at) - +new Date(a.retrieved_at))
    .slice(0, 6)
    .map((d: any) => ({
      ...d,
      branches: [...new Set([...evTopicsOfDoc.get(d.id)!]
        .map(t => branchName.get(topicHome.get(t))).filter(Boolean))],
    }));

  return (
    <div className="flex flex-col gap-5">
      <Aurora className="px-[38px] pb-[26px] pt-[34px]">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <Kicker className="text-[#A1A1A6]">Electronic warfare · consultant overview</Kicker>
            <div className="mt-3 flex items-baseline gap-3">
              <span className="text-[56px] font-bold leading-none">{ready}</span>
              <span className="text-[18px] text-[#D2D2D7]">of {rows.length} branches ready to write on</span>
            </div>
            <p className="mt-2 max-w-[60ch] text-[14px] text-[#D2D2D7]">
              Ready means at least {READY_PUBLISHERS} independent publishers and at least one
              emerging or stronger signal. Thin branches need sources before they carry a claim.
            </p>
          </div>
          <div className="flex flex-wrap gap-2.5">
            <Stat value={evidence.length} label="live evidence" />
            <Stat value={rows.reduce((n, r) => n + r.week, 0)} label="collected · 7 days" />
            <Stat value={openGates} label="gates open" tone="warn" />
          </div>
        </div>
      </Aurora>

      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="section-title">Branches</h2>
          <Legend items={[
            [CLASS_FILL.A, CLASS_LABEL.A], [CLASS_FILL.B, CLASS_LABEL.B], [CLASS_FILL.C, CLASS_LABEL.C],
            [DIR_FILL.STRENGTHENING, "Signals strengthening"], [DIR_FILL.WEAKENING, "Signals weakening"],
          ]} />
        </div>
        <Card className="px-4 pb-2 pt-3">
          <Table>
            <TableHeader>
              <tr>
                <TableHead>Branch</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Evidence</TableHead>
                <TableHead>Trust mix</TableHead>
                <TableHead className="text-right">Publishers</TableHead>
                <TableHead className="text-right">UAE</TableHead>
                <TableHead className="text-right">New · 7d / 30d</TableHead>
                <TableHead>Signal momentum</TableHead>
              </tr>
            </TableHeader>
            <TableBody>
              {rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell>
                    <div className="font-semibold text-ink">{r.name}</div>
                    <div className="text-xs text-faint">{r.topics} topics</div>
                  </TableCell>
                  <TableCell><StatusChip status={r.status} /></TableCell>
                  <TableNum>{r.evidence}</TableNum>
                  <TableCell className="align-middle"><TrustBar counts={r.classes} total={r.evidence} /></TableCell>
                  <TableNum>{r.publishers}</TableNum>
                  <TableNum>{r.evidence ? `${Math.round((r.uae / r.evidence) * 100)}%` : "—"}</TableNum>
                  <TableNum>{r.week} / {r.month}</TableNum>
                  <TableCell className="align-middle">
                    <Momentum up={r.up} flat={r.flat} down={r.down} max={maxDir} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="pt-2 text-xs text-faint">
            A branch counts the topics it homes and the topics linked to its functions, so one topic
            can appear under two branches. "New" is when we collected a document, not when it was published.
          </p>
        </Card>
      </section>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <section className="flex flex-col gap-3">
          <h2 className="section-title">Latest intake</h2>
          <Card className="px-4 py-1">
            <div className="[&>*]:border-t [&>*]:border-line-soft [&>*:first-child]:border-t-0">
              {latest.map((d: any) => (
                <div key={d.id} className="flex flex-col gap-1 py-3">
                  <a href={d.url} target="_blank" rel="noreferrer"
                     className="text-base font-semibold text-ink hover:text-accent-deep">
                    {d.title || d.url}
                  </a>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                    <Badge variant={d.source_registry?.tier === 1 ? "tier1" : "tier"}>
                      Tier {d.source_registry?.tier ?? "?"}
                    </Badge>
                    <span>{d.source_registry?.publisher ?? "unknown publisher"}</span>
                    <span>·</span>
                    <span>{fmtDate(d.published_on) ? `published ${fmtDate(d.published_on)}` : "undated"}</span>
                    <span>·</span>
                    <span>collected {fmtDate(d.retrieved_at)}</span>
                    {d.branches.map((b: string) => <Badge key={b}>{b}</Badge>)}
                  </div>
                </div>
              ))}
              {!latest.length && <div className="p-4 text-base text-faint">No evidence-bearing documents yet.</div>}
            </div>
          </Card>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="section-title">Strongest signals</h2>
          <Card className="px-4 py-1">
            <div className="[&>*]:border-t [&>*]:border-line-soft [&>*:first-child]:border-t-0">
              {strongest.map(s => (
                <div key={s.id} className="flex flex-col gap-1 py-3">
                  <span className="text-base text-ink-2">{s.statement}</span>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                    <span className="font-bold text-accent">{s.id}</span>
                    <span>{s.strength.replace("_", " ").toLowerCase()}</span>
                    <span className="inline-flex items-center gap-1">
                      <span className="h-[2px] w-3" style={{ background: DIR_FILL[s.direction as keyof typeof DIR_FILL] }} />
                      {s.direction.toLowerCase()}
                    </span>
                    {homeOfSignal(s.id) && <Badge>{homeOfSignal(s.id)}</Badge>}
                  </div>
                </div>
              ))}
              {!strongest.length && <div className="p-4 text-base text-faint">No signals on live evidence yet.</div>}
            </div>
          </Card>
        </section>
      </div>
    </div>
  );
}
