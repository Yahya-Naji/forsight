import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { citedIds, splitSections } from "@/lib/report";

export const revalidate = 0;
export const dynamic = "force-dynamic";

const PILLAR: Record<string, string> = {
  ELECTRONIC_WARFARE: "Electronic warfare", CYBERSECURITY: "Cybersecurity", AI: "AI", PROCUREMENT: "Procurement",
};

export default async function Reports() {
  const { data } = await supabase.from("reports")
    .select("id,title,status,pillar,created_at,body_md").order("created_at", { ascending: false });
  const rows = (data ?? []).map(r => {
    const { sections } = splitSections(r.body_md ?? "");
    const prose = sections.filter(s => s.key !== "references");
    const ids = citedIds(prose.map(s => s.md).join("\n"));
    const lead = (prose[0]?.md ?? "").replace(/\[[^\]]*\]/g, "").replace(/\s+/g, " ").replace(/\s+([.,;:])/g, "$1").trim();
    return {
      ...r,
      sections: prose.length,
      written: prose.filter(s => s.md).length,
      evidence: ids.filter(i => i.startsWith("EV-")).length,
      lead: lead.length > 220 ? lead.slice(0, 220).replace(/\s\S*$/, "") + "…" : lead,
    };
  });

  return (
    <div className="mx-auto flex max-w-[1100px] flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[30px] font-semibold tracking-[-0.02em] text-ink">Reports</h1>
          <p className="mt-1 text-sm text-muted">Every report opens with its citations resolved, and downloads as HTML, Markdown or PDF.</p>
        </div>
        <Link href="/generate" className="rounded-full bg-accent px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-accent-deep active:scale-[.98]">
          New report
        </Link>
      </div>

      {!rows.length && <div className="rounded-2xl bg-white p-6 text-sm text-muted">No reports yet.</div>}

      <div className="grid gap-4 md:grid-cols-2">
        {rows.map(r => (
          <div key={r.id} className="group flex flex-col rounded-2xl bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,.04)] transition hover:shadow-[0_8px_28px_rgba(0,0,0,.08)]">
            <div className="flex items-center gap-2 text-[12px] text-muted">
              <span className="font-semibold text-accent">{PILLAR[r.pillar] ?? r.pillar}</span>
              <span>·</span>
              <span>{new Date(r.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span>
              <span className={`ml-auto rounded-full px-2 py-0.5 text-[11px] font-semibold ${r.status === "GATES_OPEN" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
                {r.status === "GATES_OPEN" ? "UAE gates open" : r.status.replace(/_/g, " ").toLowerCase()}
              </span>
            </div>
            <Link href={`/reports/${r.id}`} className="mt-2 text-[18px] font-semibold leading-snug tracking-[-0.01em] text-ink group-hover:text-accent">
              {r.title}
            </Link>
            {r.lead && <p className="mt-2 line-clamp-3 text-[13.5px] leading-relaxed text-muted">{r.lead}</p>}
            <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-2 pt-4 text-[12px] text-muted">
              <span><b className="text-ink">{r.written}</b>/{r.sections} sections</span>
              <span><b className="text-ink">{r.evidence}</b> evidence cited</span>
              <span className="ml-auto flex gap-3">
                <a href={`/api/report/${r.id}/export?format=html`} className="font-semibold text-accent hover:underline">HTML</a>
                <a href={`/api/report/${r.id}/export?format=md`} className="font-semibold text-accent hover:underline">MD</a>
                <Link href={`/reports/${r.id}`} className="font-semibold text-ink hover:underline">Open →</Link>
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
