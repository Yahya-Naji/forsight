"use client";
import * as React from "react";
import { motion } from "motion/react";

// Radial tree of the EW structure (migration 031). Layout is computed here —
// no layout library — because the tree is fixed at three levels: root, eight
// branches, and each branch's leaves (manual functions + topics homed there).

export type TreeNode = { id: string; parent_id: string | null; kind: string; name: string; sort: number };
export type TreeTopic = {
  id: string; name: string; nodeId: string | null; functions: string[]; pillar: string;
  impact: string | null; evidence: number; classA: number; publishers: number;
  signals: number; liveSignals: number; status: "Ready" | "Thin" | "Empty";
};
export type TreeData = { nodes: TreeNode[]; topics: TreeTopic[] };

type Leaf =
  | { kind: "topic"; id: string; branch: string; angle: number; topic: TreeTopic }
  | { kind: "function"; id: string; branch: string; angle: number; name: string };

const R_BRANCH = 150, R_LEAF = 330, SIZE = 1240;   // half-width leaves ~270px for leaf labels
const STATUS_FILL = { Ready: "#1E7B34", Thin: "#C27A00", Empty: "#AEAEB2" } as const;
const ACCENT = "#0071E3";
const EASE = [0.22, 1, 0.36, 1] as const;          // one easing for the whole console

const polar = (angle: number, r: number) => [Math.cos(angle) * r, Math.sin(angle) * r] as const;
const radialLink = (a1: number, r1: number, a2: number, r2: number) => {
  const m = (r1 + r2) / 2;
  const [x1, y1] = polar(a1, r1), [c1x, c1y] = polar(a1, m), [c2x, c2y] = polar(a2, m), [x2, y2] = polar(a2, r2);
  return `M${x1},${y1} C${c1x},${c1y} ${c2x},${c2y} ${x2},${y2}`;
};
const crossLink = (a1: number, a2: number) => {
  const [x1, y1] = polar(a1, R_LEAF - 8), [x2, y2] = polar(a2, R_LEAF - 8);
  return `M${x1},${y1} Q${(x1 + x2) * 0.18},${(y1 + y2) * 0.18} ${x2},${y2}`;
};
const short = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const useIsoLayoutEffect = typeof window === "undefined" ? React.useEffect : React.useLayoutEffect;

export default function EwTree({ data }: { data: TreeData }) {
  // The server renders the finished tree, so it shows without JavaScript and
  // for reduced-motion visitors. Before first paint the client re-mounts it
  // with the draw-in animation, only when motion is allowed.
  const [play, setPlay] = React.useState(false);
  useIsoLayoutEffect(() => {
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) setPlay(true);
  }, []);
  const reduce = !play;
  const [hover, setHover] = React.useState<string | null>(null);
  const [selected, setSelected] = React.useState<string | null>(null);

  const { branches, leaves, branchAngle, leafById, nameOf } = React.useMemo(() => {
    const root = data.nodes.find(n => n.kind === "root");
    const branches = data.nodes.filter(n => n.parent_id === root?.id).sort((a, b) => a.sort - b.sort);
    const groups = branches.map(b => [
      ...data.topics.filter(t => t.nodeId === b.id).sort((x, y) => y.evidence - x.evidence)
        .map(t => ({ kind: "topic" as const, id: t.id, branch: b.id, topic: t })),
      ...data.nodes.filter(n => n.parent_id === b.id && n.kind === "function")
        .map(n => ({ kind: "function" as const, id: n.id, branch: b.id, name: n.name })),
    ]);
    const slots = groups.reduce((n, g) => n + g.length, 0) + branches.length;   // one empty slot between branches
    const leaves: Leaf[] = [];
    const branchAngle = new Map<string, number>();
    let i = 0;
    groups.forEach((g, gi) => {
      const start = i;
      for (const leaf of g) leaves.push({ ...leaf, angle: (i++ / slots) * Math.PI * 2 - Math.PI / 2 } as Leaf);
      const mid = start + (g.length - 1) / 2;
      branchAngle.set(branches[gi].id, (mid / slots) * Math.PI * 2 - Math.PI / 2);
      i++;
    });
    const nameOf = new Map(data.nodes.map(n => [n.id, n.name]));
    return { branches, leaves, branchAngle, leafById: new Map(leaves.map(l => [l.id, l])), nameOf };
  }, [data]);

  const focus = hover ?? selected;
  const focusLeaf = focus ? leafById.get(focus) : undefined;
  const focusBranch = focusLeaf?.branch ?? (focus && branchAngle.has(focus) ? focus : null);

  // Cross-links: a selected topic reaches its functions; a selected function is reached by topics.
  const cross = React.useMemo(() => {
    if (!focus) return [] as [Leaf, Leaf][];
    const f = leafById.get(focus);
    if (f?.kind === "topic")
      return f.topic.functions.map(id => leafById.get(id)).filter(Boolean).map(l => [f, l!] as [Leaf, Leaf]);
    if (f?.kind === "function")
      return leaves.filter(l => l.kind === "topic" && l.topic.functions.includes(f.id)).map(l => [l, f] as [Leaf, Leaf]);
    return [];
  }, [focus, leafById, leaves]);
  const crossIds = new Set(cross.flat().map(l => l.id));
  const lit = (leaf: Leaf) => !focus || leaf.id === focus || crossIds.has(leaf.id) || leaf.branch === focusBranch;

  const sel = selected ? leafById.get(selected) : undefined;
  const selBranch = selected && branchAngle.has(selected) ? selected : null;
  const draw = (delay: number) => reduce ? {} : {
    initial: { pathLength: 0, opacity: 0 }, animate: { pathLength: 1, opacity: 1 },
    transition: { duration: 0.7, delay, ease: EASE },
  };
  const appear = (delay: number) => reduce ? {} : {
    initial: { opacity: 0, scale: 0.6 }, animate: { opacity: 1, scale: 1 },
    transition: { duration: 0.45, delay, ease: EASE },
  };
  const keyed = (id: string) => ({
    tabIndex: 0, role: "button", "aria-pressed": selected === id,
    onMouseEnter: () => setHover(id), onMouseLeave: () => setHover(null),
    onFocus: () => setHover(id), onBlur: () => setHover(null),
    onClick: () => setSelected(s => (s === id ? null : id)),
    onKeyDown: (e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(s => (s === id ? null : id)); } },
    style: { cursor: "pointer", outline: "none" },
  });

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="rounded-[20px] border border-line bg-card p-2">
        <svg key={play ? "animated" : "static"} viewBox={`${-SIZE / 2} ${-SIZE / 2} ${SIZE} ${SIZE}`} className="h-auto w-full select-none"
             role="img" aria-label="Radial tree of electronic warfare branches, functions and topics">
          {/* root → branch */}
          {branches.map((b, i) => {
            const [x, y] = polar(branchAngle.get(b.id)!, R_BRANCH);
            return <motion.path key={b.id} d={`M0,0 L${x},${y}`} fill="none" strokeWidth={2}
              stroke={focusBranch && focusBranch !== b.id ? "#E5E5EA" : "#C7C7CC"} {...draw(i * 0.05)} />;
          })}
          {/* branch → leaf */}
          {leaves.map((l, i) => (
            <motion.path key={"l" + l.id} d={radialLink(branchAngle.get(l.branch)!, R_BRANCH, l.angle, R_LEAF)}
              fill="none" strokeWidth={l.kind === "topic" ? 1.6 : 1}
              stroke={lit(l) ? (l.id === focus ? ACCENT : "#C7C7CC") : "#EFEFF4"} {...draw(0.3 + i * 0.008)} />
          ))}
          {/* cross-links for the focused leaf */}
          {cross.map(([a, b]) => (
            <motion.path key={`x${a.id}-${b.id}`} d={crossLink(a.angle, b.angle)} fill="none"
              stroke={ACCENT} strokeOpacity={0.55} strokeWidth={1.5} strokeDasharray="0"
              {...(reduce ? {} : { initial: { pathLength: 0 }, animate: { pathLength: 1 }, transition: { duration: 0.5, ease: EASE } })} />
          ))}

          {/* leaves */}
          {leaves.map((l, i) => {
            const [x, y] = polar(l.angle, R_LEAF);
            const deg = (l.angle * 180) / Math.PI, flip = Math.cos(l.angle) < 0;
            const on = lit(l);
            const r = l.kind === "topic" ? 4 + Math.sqrt(l.topic.evidence) * 1.05 : 3.5;
            const label = l.kind === "topic" ? `${l.id} · ${short(l.topic.name, 28)}` : short(l.name, 30);
            return (
              <g key={"n" + l.id} {...keyed(l.id)} opacity={on ? 1 : 0.28}>
                <motion.circle cx={x} cy={y} r={r + 6} fill="transparent" />
                <motion.circle cx={x} cy={y} r={r} strokeWidth={l.kind === "topic" ? 2 : 1.5}
                  stroke={l.id === focus || l.id === selected ? ACCENT : "#FFFFFF"}
                  fill={l.kind === "topic" ? STATUS_FILL[l.topic.status] : "#FFFFFF"}
                  {...(l.kind === "function" ? { stroke: l.id === focus ? ACCENT : "#86868B" } : {})}
                  {...appear(0.5 + i * 0.008)} />
                <text transform={`rotate(${flip ? deg + 180 : deg}) translate(${flip ? -(R_LEAF + r + 7) : R_LEAF + r + 7},0)`}
                      textAnchor={flip ? "end" : "start"} dominantBaseline="middle"
                      fontSize={l.kind === "topic" ? 12 : 11} fontWeight={l.kind === "topic" ? 600 : 400}
                      fill={l.kind === "topic" ? "#1D1D1F" : "#6E6E73"}>{label}</text>
              </g>
            );
          })}

          {/* branches */}
          {branches.map((b, i) => {
            const a = branchAngle.get(b.id)!, [x, y] = polar(a, R_BRANCH);
            // Labels sit just outside the dot, anchored away from the centre.
            const side = Math.cos(a) > 0.35 ? "start" : Math.cos(a) < -0.35 ? "end" : "middle";
            const [lx, ly] = polar(a, R_BRANCH + (side === "middle" ? 30 : 18));
            const dim = focusBranch && focusBranch !== b.id;
            return (
              <g key={"b" + b.id} {...keyed(b.id)} opacity={dim ? 0.35 : 1}>
                <motion.circle cx={x} cy={y} r={11} fill={selected === b.id ? ACCENT : "#1D1D1F"}
                  stroke="#FFFFFF" strokeWidth={3} {...appear(0.15 + i * 0.04)} />
                <text x={lx} y={ly} textAnchor={side} dominantBaseline="middle" fontSize={13} fontWeight={600}
                      fill="#1D1D1F" stroke="#FFFFFF" strokeWidth={4} paintOrder="stroke">{b.name}</text>
              </g>
            );
          })}

          {/* root */}
          <motion.g {...appear(0)} style={{ cursor: "pointer" }} onClick={() => setSelected(null)}>
            <circle r={30} fill="#000000" />
            <text textAnchor="middle" dominantBaseline="middle" fontSize={17} fontWeight={700} fill="#FFFFFF">EW</text>
          </motion.g>
        </svg>
      </div>

      <aside className="flex flex-col gap-4">
        <div className="rounded-[20px] border border-line bg-card p-5">
          {sel?.kind === "topic" ? <TopicPanel t={sel.topic} nameOf={nameOf} branchOf={(id) => leafById.get(id)?.branch} />
            : sel?.kind === "function" ? (
              <div className="flex flex-col gap-2">
                <span className="text-xs font-medium text-muted">Manual function · {nameOf.get(sel.branch)}</span>
                <h2 className="text-xl font-semibold tracking-tight">{sel.name}</h2>
                <p className="text-sm text-muted">{cross.length} topic{cross.length === 1 ? "" : "s"} reach this function:</p>
                <ul className="flex flex-col gap-1 text-sm">
                  {cross.map(([t]) => t.kind === "topic" && (
                    <li key={t.id}><button className="text-left text-accent hover:underline" onClick={() => setSelected(t.id)}>
                      {t.id} · {t.topic.name}</button></li>))}
                </ul>
              </div>
            ) : selBranch ? <BranchPanel id={selBranch} name={nameOf.get(selBranch) ?? selBranch}
                                         topics={data.topics} leaves={leaves} onPick={setSelected} />
            : (
              <div className="flex flex-col gap-2">
                <h2 className="text-xl font-semibold tracking-tight">Read the tree</h2>
                <p className="text-sm text-muted">Select a branch, topic or function. Topics show the functions
                  they reach in other branches as blue arcs.</p>
              </div>
            )}
        </div>
        <div className="rounded-[20px] border border-line bg-card p-5 text-sm">
          <h3 className="mb-3 text-xs font-medium text-muted">Legend</h3>
          <ul className="flex flex-col gap-2">
            {(["Ready", "Thin", "Empty"] as const).map(s => (
              <li key={s} className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full" style={{ background: STATUS_FILL[s] }} />
                <span className="text-ink-2">{s} topic</span>
                <span className="text-xs text-faint">
                  {s === "Ready" ? "≥3 publishers and an emerging signal" : s === "Thin" ? "evidence, below that bar" : "no evidence yet"}
                </span>
              </li>))}
            <li className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full border-[1.5px] border-faint bg-card" />
              <span className="text-ink-2">Manual function</span>
            </li>
            <li className="text-xs text-faint">Topic dot size grows with its evidence.</li>
          </ul>
        </div>
      </aside>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-paper px-3 py-2">
      <div className="text-[11px] text-muted">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function TopicPanel({ t, nameOf, branchOf }: {
  t: TreeTopic; nameOf: Map<string, string>; branchOf: (id: string) => string | undefined;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <span className="text-xs font-medium text-muted">{t.id} · {t.pillar.replace("_", " ").toLowerCase()}</span>
        <h2 className="mt-0.5 text-xl font-semibold leading-snug tracking-tight">{t.name}</h2>
        <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold"
              style={{ background: STATUS_FILL[t.status] + "1F", color: STATUS_FILL[t.status] }}>
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: STATUS_FILL[t.status] }} />{t.status}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Evidence" value={t.evidence} />
        <Stat label="Class A" value={t.classA} />
        <Stat label="Publishers" value={t.publishers} />
        <Stat label="Signals" value={`${t.liveSignals}/${t.signals}`} />
      </div>
      {t.impact && <p className="text-sm text-ink-2"><span className="font-semibold">EW impact. </span>{t.impact}</p>}
      <div>
        <h3 className="mb-1.5 text-xs font-medium text-muted">Reaches these functions</h3>
        <ul className="flex flex-col gap-1 text-sm">
          {t.functions.map(f => (
            <li key={f} className="flex justify-between gap-2">
              <span className="text-ink-2">{nameOf.get(f) ?? f}</span>
              <span className="text-xs text-faint">{nameOf.get(branchOf(f) ?? "") ?? ""}</span>
            </li>))}
        </ul>
      </div>
    </div>
  );
}

function BranchPanel({ id, name, topics, leaves, onPick }: {
  id: string; name: string; topics: TreeTopic[]; leaves: Leaf[]; onPick: (id: string) => void;
}) {
  const fnIds = new Set(leaves.filter(l => l.kind === "function" && l.branch === id).map(l => l.id));
  const home = topics.filter(t => t.nodeId === id);
  const linked = topics.filter(t => t.nodeId !== id && t.functions.some(f => fnIds.has(f)));
  const ev = [...home, ...linked].reduce((n, t) => n + t.evidence, 0);
  return (
    <div className="flex flex-col gap-3">
      <div>
        <span className="text-xs font-medium text-muted">Branch</span>
        <h2 className="mt-0.5 text-xl font-semibold tracking-tight">{name}</h2>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Own topics" value={home.length} />
        <Stat label="Linked topics" value={linked.length} />
        <Stat label="Functions" value={fnIds.size} />
        <Stat label="Evidence reached" value={ev} />
      </div>
      {[["Topics homed here", home], ["Topics from other branches", linked]].map(([title, list]) => (
        (list as TreeTopic[]).length > 0 && (
          <div key={title as string}>
            <h3 className="mb-1.5 text-xs font-medium text-muted">{title as string}</h3>
            <ul className="flex flex-col gap-1 text-sm">
              {(list as TreeTopic[]).map(t => (
                <li key={t.id} className="flex items-center gap-2">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: STATUS_FILL[t.status] }} />
                  <button className="truncate text-left text-ink-2 hover:text-accent" onClick={() => onPick(t.id)}>
                    {t.id} · {t.name}</button>
                </li>))}
            </ul>
          </div>)))}
    </div>
  );
}
