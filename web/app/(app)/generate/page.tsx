import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { PILLAR_LABEL } from "@/components/chips";
import BriefChat from "@/components/BriefChat";
import LiveRun from "@/components/LiveRun";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// A request runs three stages (pipeline/request.py). Collection, extraction,
// synthesis and forecasting are the daily analysis: they rebuild the shared
// graph every report draws from, so they are not repeated per request.
const REQUEST_STAGES: [string, string, string][] = [
  ["rules", "Rules", "Re-score today's evidence: classes, corroboration, UAE gates"],
  ["generate", "Draft", "Each section written against the brief and verified as it is written"],
  ["verify", "Audit", "Every sentence checked against its source; failing sentences removed"],
];

const RUN_STATUS: Record<string, { text: string; cls: string }> = {
  QUEUED:  { text: "Queued",  cls: "bg-amber-100 text-amber-800" },
  RUNNING: { text: "Running", cls: "bg-blue-100 text-blue-800" },
  DONE:    { text: "Done",    cls: "bg-emerald-100 text-emerald-800" },
  FAILED:  { text: "Failed",  cls: "bg-red-100 text-red-800" },
};

export default async function Generate({ searchParams }: { searchParams?: { run?: string; error?: string } }) {
  const [runs, daily] = await Promise.all([
    searchParams?.run
      ? supabase.from("pipeline_runs").select("id,pillar,title,status,stage,counts,error,report_id,requested_at,finished_at").eq("id", searchParams.run).limit(1)
      : supabase.from("pipeline_runs").select("id,pillar,title,status,stage,counts,error,report_id,requested_at,finished_at").order("requested_at", { ascending: false }).limit(1),
    supabase.from("signals").select("created_at").order("created_at", { ascending: false }).limit(1),
  ]);
  const run = runs.data?.[0];
  const lastAnalysis = daily.data?.[0]?.created_at;

  const reached = run?.stage ? REQUEST_STAGES.findIndex(s => s[0] === run.stage) : -1;
  const done = run?.status === "DONE";
  const failed = run?.status === "FAILED";
  const badge = RUN_STATUS[run?.status ?? ""];

  return (
    <div className="flex flex-col gap-6">
      <BriefChat />

      <section className="rounded-2xl bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,.04)]">
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <div className="text-[12px] font-medium text-muted">Latest request</div>
            <div className="truncate text-[17px] font-semibold text-ink">
              {run ? (run.title || `${PILLAR_LABEL[run.pillar] ?? run.pillar} report`) : "No request yet"}
            </div>
          </div>
          {badge && <span className={`rounded-full px-3 py-1 text-[12px] font-semibold ${badge.cls}`}>{badge.text}</span>}
          {run && <LiveRun status={run.status} />}
        </div>

        {searchParams?.error && (
          <p className="mt-3 text-[13px] text-red-700">
            {searchParams.error === "no-service-key"
              ? "Set SUPABASE_SERVICE_KEY to record runs — the browser key cannot write."
              : `Could not queue the run: ${searchParams.error}`}
          </p>
        )}

        {run && (
          <ol className="mt-5 flex flex-col">
            {REQUEST_STAGES.map(([key, name, sub], i) => {
              const complete = done || (reached > -1 && i < reached) || (failed && reached > i);
              const active = !done && !failed && reached === i;
              const stalled = failed && reached === i;
              return (
                <li key={key} className={`flex items-center gap-4 py-2.5 ${complete || active || stalled ? "" : "opacity-45"}`}>
                  <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[12px] font-bold
                    ${stalled ? "bg-red-500 text-white" : complete ? "bg-emerald-500 text-white" : active ? "animate-pulse bg-accent text-white" : "border-[1.5px] border-line"}`}>
                    {stalled ? "!" : complete ? "✓" : active ? "•" : ""}
                  </span>
                  <span className="w-20 text-[14px] font-semibold text-ink">{name}</span>
                  <span className="text-[13px] text-muted">{sub}</span>
                </li>
              );
            })}
          </ol>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-4">
          <p className="flex-1 text-[12.5px] leading-relaxed text-muted">
            {run?.error
              ? run.error
              : `Drafted from the evidence graph as it stands. Evidence, signals and forecasts come from the daily analysis${lastAnalysis ? ` (last updated ${new Date(lastAnalysis).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })})` : ""}.`}
          </p>
          {run?.report_id && (
            <Link href={`/reports/${run.report_id}`}
              className="rounded-full bg-accent px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-accent-deep active:scale-[.98]">
              {done ? "Open the report" : "Open the draft"}
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}
