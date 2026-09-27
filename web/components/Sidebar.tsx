"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { PILLAR_LABEL } from "@/components/chips";

// Navigation follows the pipeline, not the database: a reader moves from where
// evidence comes from, through what it became, to what was written and how it
// scored. Ordering these by table name would put Evidence next to Engine and
// hide the argument the console is making.
const NAV = [
  { href: "/console", label: "Overview" },
  { href: "/pillars/CYBERSECURITY", label: "Pillars", match: "/pillars", children: true },
  { href: "/sources", label: "Sources" },
  { href: "/evidence", label: "Evidence" },
  { href: "/generate", label: "Generate" },
  { href: "/engine", label: "Engine" },
  { href: "/reports", label: "Reports" },
  { href: "/refusals", label: "Refusals" },
  { href: "/scorecard", label: "Scorecard" },
] as const;

const PILLARS = Object.keys(PILLAR_LABEL);

export default function Sidebar({ onAsk }: { onAsk?: () => void }) {
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
                active(item.href, (item as any).match) ? "bg-accent" : "bg-[#C9D0E4]")} />
              {item.label}
            </Link>

            {(item as any).children && (
              <div className="flex flex-col pl-[26px] text-sm">
                {PILLARS.map(p => (
                  <Link key={p} href={`/pillars/${p}`} className={cn(
                    "px-2 py-[5px] transition-colors hover:text-ink",
                    path === `/pillars/${p}` ? "font-semibold text-ink" : "text-[#7A8098]")}>
                    {PILLAR_LABEL[p]}
                  </Link>
                ))}
              </div>
            )}
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
