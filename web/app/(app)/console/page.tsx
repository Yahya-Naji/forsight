import Link from "next/link";
import { supabase } from "@/lib/supabase";
import GateCard from "@/components/GateCard";
import SignalMeter from "@/components/SignalMeter";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Aurora, Stat, Kicker } from "@/components/ui/section";

export const revalidate = 0;
export const dynamic = "force-dynamic";

/** A list whose rows are separated by rules rather than by wrapping each row in
 *  its own card — the console shows registers, and a card per row reads as five
 *  unrelated things rather than one list. */
function Rows({ children, empty }: { children: React.ReactNode; empty: string }) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children;
  const any = Array.isArray(items) ? items.length > 0 : Boolean(items);
  return (
    <Card className="px-4 py-1">
      {any ? (
        <div className="[&>*]:border-t [&>*]:border-line-soft [&>*:first-child]:border-t-0">
          {items}
        </div>
      ) : (
        <div className="p-4 text-base text-faint">{empty}</div>
      )}
    </Card>
  );
}

export default async function Overview() {
  const [ev, docs, srcs, gates, signals, reports, recentDocs] = await Promise.all([
    supabase.from("evidence").select("id", { count: "exact", head: true }),
    supabase.from("documents").select("id", { count: "exact", head: true }),
    supabase.from("source_registry").select("id", { count: "exact", head: true }),
    supabase.from("validation_gates").select("*").order("id"),
    supabase.from("signals").select("*")
      .in("strength", ["STRONG", "STRONG_EMERGING", "EMERGING"]).limit(5),
    supabase.from("reports").select("id,title,status,created_at")
      .order("created_at", { ascending: false }).limit(5),
    supabase.from("documents")
      .select("title,retrieved_at,registry_id,source_registry(publisher,tier)")
      .order("retrieved_at", { ascending: false }).limit(8),
  ]);
  const openGates = (gates.data ?? []).filter(g => g.status === "OPEN");

  return (
    <div className="flex flex-col gap-5">
      <Aurora className="px-[38px] pb-[26px] pt-[34px]">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <Kicker className="text-[#93A7E8]">Strategic foresight · UAE defence</Kicker>
            <h1 className="display mt-2.5 text-[40px] font-bold tracking-tight">
              Intelligence, with receipts.
            </h1>
            <p className="mt-2 text-[14px] text-[#B8C4EE]">
              Every claim below traces to a source. Nothing here is generated from a prompt.
            </p>
          </div>
          <div className="flex flex-wrap gap-2.5">
            <Stat value={ev.count ?? 0} label="evidence" />
            <Stat value={docs.count ?? 0} label="documents" />
            <Stat value={srcs.count ?? 0} label="sources" />
            <Stat value={openGates.length} label="gates open" tone="warn" />
          </div>
        </div>

        {/* What ran most recently, by publisher and tier — the console's claim is
            that collection is continuous and tiered, so it is shown rather than
            asserted. */}
        <div className="mt-6 flex items-center gap-3.5 overflow-hidden rounded-xl
                        border border-white/10 bg-[rgba(10,14,40,.55)] px-4 py-2.5">
          <span className="flex shrink-0 items-center gap-[7px] text-sm font-semibold text-[#7EE0A9]">
            <span className="h-[7px] w-[7px] rounded-full bg-[#4ADE80]" />
            DAILY RUN
          </span>
          <div className="ticker">
            <div className="ticker-track">
              {(recentDocs.data ?? []).map((d: any, i: number) => (
                <span key={i}>
                  {d.source_registry?.publisher ?? "unknown"} ·{" "}
                  <b className="text-white">Tier {d.source_registry?.tier ?? "?"}</b>
                </span>
              ))}
            </div>
          </div>
        </div>
      </Aurora>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.1fr_1.4fr]">
        <section className="flex flex-col gap-3">
          <h2 className="section-title">Validation gates</h2>
          {(gates.data ?? []).map(g => (
            <GateCard key={g.id} id={g.id} status={g.status}
              blocks={g.status === "OPEN"
                ? `${g.blocks} — no UAE-layer Class A/B evidence yet.`
                : g.blocks} />
          ))}
          {!gates.data?.length && (
            <Card className="p-4 text-base text-faint">No gates yet — run the rules engine.</Card>
          )}
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="section-title">Signals</h2>
          <Rows empty="No admitted signals yet.">
            {(signals.data ?? []).map(s => (
              <div key={s.id} className="flex items-center gap-3.5 py-3">
                <span className="w-[84px] shrink-0 text-xs font-bold text-accent">{s.id}</span>
                <span className="grow text-base text-ink-2">{s.statement}</span>
                <SignalMeter strength={s.strength} />
              </div>
            ))}
          </Rows>

          <h2 className="section-title mt-1.5">Recent reports</h2>
          <Rows empty="No reports generated yet.">
            {(reports.data ?? []).map(r => (
              <div key={r.id} className="flex items-center gap-3 py-3">
                <Link href={`/reports/${r.id}`}
                      className="grow text-base font-semibold text-ink hover:text-accent-deep">
                  {r.title}
                </Link>
                <Badge variant={r.status === "GATES_OPEN" ? "open" : "default"}>
                  {r.status.replace("_", " ")}
                </Badge>
                <span className="text-sm text-ghost">
                  {new Date(r.created_at).toLocaleDateString("en-GB",
                    { day: "numeric", month: "short" })}
                </span>
              </div>
            ))}
          </Rows>
        </section>
      </div>
    </div>
  );
}
