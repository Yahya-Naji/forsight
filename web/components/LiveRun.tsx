"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

// Refresh the page while a run is in flight.
//
// The stage indicators are server-rendered from pipeline_runs, so without this
// the rail only moves when someone reloads — which during a live demo is
// indistinguishable from the run being stuck. Polling stops the moment the run
// reaches a terminal state, so an idle console is not re-fetching every few
// seconds forever.

export default function LiveRun({ status }: { status?: string | null }) {
  const router = useRouter();
  const live = status === "QUEUED" || status === "RUNNING";
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!live) return;
    const tick = setInterval(() => setElapsed(s => s + 1), 1000);
    const poll = setInterval(() => router.refresh(), 3000);
    return () => { clearInterval(tick); clearInterval(poll); };
  }, [live, router]);

  if (!live) return null;
  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <span className="ml-2 inline-flex items-center gap-2 rounded-full border
                     border-[rgba(255,183,77,.35)] bg-[rgba(255,183,77,.12)]
                     px-3 py-1 text-xs font-semibold text-[#FFC96B]">
      <span className="h-[7px] w-[7px] animate-pulse rounded-full bg-[#FFC96B]" />
      {status === "QUEUED" ? "waiting for the runner" : "running"} · {mm}:{ss}
    </span>
  );
}
