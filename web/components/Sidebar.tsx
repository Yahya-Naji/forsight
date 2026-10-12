"use client";
import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// Navigation follows the pipeline, not the database: a reader moves from where
// evidence comes from, through what it became, to what was written and how it
// scored. Ordering these by table name would put Evidence next to Engine and
// hide the argument the console is making.
const NAV = [
  { href: "/overview", label: "Overview" },
  { href: "/tree", label: "Tree" },
  { href: "/console", label: "System" },
  { href: "/pillars/EW", label: "Pillars", match: "/pillars", children: true },
  { href: "/sources", label: "Sources" },
  { href: "/evidence", label: "Evidence" },
  { href: "/generate", label: "Generate" },
  { href: "/engine", label: "Engine" },
  { href: "/reports", label: "Reports" },
  { href: "/refusals", label: "Refusals" },
  { href: "/scorecard", label: "Scorecard" },
] as const;

// The EW tree's sub-pillars (migration 031), so the menu renders before the
// live list arrives; the database is the source of truth once it loads.
const SUB_PILLARS = [
  ["EA", "Electronic Attack"], ["EP", "Electronic Protection"], ["ES", "Electronic Support"],
  ["EMSO", "Spectrum Operations"], ["CUAS", "Counter-UAS"], ["CYBER", "Cybersecurity"],
  ["AI", "Artificial Intelligence"], ["PROCUREMENT", "Procurement"],
].map(([id, name]) => ({ id, name }));
const LEGACY: Record<string, string> = {
  ELECTRONIC_WARFARE: "EW", CYBERSECURITY: "CYBER", AI: "AI", PROCUREMENT: "PROCUREMENT",
};

type Topic = { id: string; name: string; node_id: string | null };
export type PillarTreeData = { branches: { id: string; name: string }[]; topics: Topic[] };

function PillarTree({ path, tree }: { path: string; tree?: PillarTreeData }) {
  const branches = tree?.branches.length ? tree.branches : SUB_PILLARS;
  const topics = tree?.topics ?? [];
  const seg = decodeURIComponent(path.split("/")[2] ?? "").toUpperCase();
  const current = LEGACY[seg] ?? seg;
  const link = (on: boolean) => cn("block truncate py-[4px] transition-colors hover:text-ink",
    on ? "font-semibold text-ink" : "text-[#86868B]");
  return (
    <div className="flex flex-col pl-[26px] text-sm">
      <Link href="/pillars/EW" className={cn(link(current === "EW"), "px-2")}>Electronic Warfare</Link>
      <div className="ml-2.5 flex flex-col border-l border-line pl-2.5">
        {branches.map(b => (
          <div key={b.id}>
            <Link href={`/pillars/${b.id}`} className={link(current === b.id)}>{b.name}</Link>
            {current === b.id && (
              <div className="mb-1 ml-1 flex flex-col border-l border-line-soft pl-2.5 text-[12.5px]">
                {topics.filter(t => t.node_id === b.id).map(t => (
                  <Link key={t.id} href={`/pillars/${b.id}?topic=${t.id}`} title={t.name}
                        className="block truncate py-[3px] text-[#86868B] transition-colors hover:text-ink">
                    {t.name}
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Sidebar({ onAsk, tree }: { onAsk?: () => void; tree?: PillarTreeData }) {
  const path = usePathname();
  const active = (href: string, match?: string) =>
    match ? path.startsWith(match) : path === href;

  return (
    <aside className="sticky top-0 flex h-screen w-[228px] shrink-0 flex-col
                      border-r border-line bg-card px-3.5 py-[22px]">
      <div className="display px-2.5 pb-5 text-[17px] font-bold tracking-[.4px]">
        FORESIGHT<span className="text-accent">.</span>
      </div>

      <nav className="flex flex-col gap-0.5">
        {NAV.map(item => (
          <div key={item.href}>
            <Link href={item.href} className={cn(
              "flex items-center gap-2.5 rounded-[10px] px-2.5 py-[9px] text-base transition-colors",
              active(item.href, (item as any).match)
                ? "bg-accent-wash font-semibold text-ink"
                : "text-muted hover:bg-line-soft hover:text-ink")}>
              <span className={cn("h-[7px] w-[7px] rounded-full",
                active(item.href, (item as any).match) ? "bg-accent" : "bg-[#D1D1D6]")} />
              {item.label}
            </Link>

            {(item as any).children && <PillarTree path={path} tree={tree} />}
          </div>
        ))}
      </nav>

      <div className="grow" />

      <Button variant="quiet" onClick={onAsk} aria-label="Ask the graph"
              className="h-auto w-full justify-between px-3.5 py-[11px] text-[13px] font-normal">
        <span className="font-semibold">Ask the graph</span>
        <span className="rounded-[6px] border border-line bg-card px-[7px] py-0.5 text-[11px] text-ghost">
          ⌘K
        </span>
      </Button>
    </aside>
  );
}
