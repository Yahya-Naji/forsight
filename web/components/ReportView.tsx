"use client";
import { Children, cloneElement, isValidElement, useEffect, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { Cited, LoadedReport } from "@/lib/report";

// The reading view of a report. Three columns: contents, the report, and a
// source panel that opens whatever citation was last clicked — so a reader can
// check any sentence without leaving the page.

const GROUP = /\[((?:EV|F|SIG|R|TR|VG|FC|CU|U|FIG)-[A-Z0-9-]+(?:\s*[;,]\s*(?:EV|F|SIG|R|TR|VG|FC|CU|U|FIG)-[A-Z0-9-]+)*)\]/g;

const KIND: Record<Cited["kind"], string> = {
  evidence: "Evidence", finding: "Finding", signal: "Signal", risk: "Risk",
  trend: "Trend", gate: "Validation gate", forecast: "Forecast", other: "Reference",
};

export default function ReportView({ r }: { r: LoadedReport }) {
  const [active, setActive] = useState<string | null>(null);
  const [current, setCurrent] = useState<string>(r.sections[0]?.key ?? "");

  // Highlight the section being read in the contents rail.
  useEffect(() => {
    const els = r.sections.map(s => document.getElementById(s.key)).filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver(entries => {
      const top = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (top) setCurrent(top.target.id);
    }, { rootMargin: "-80px 0px -60% 0px" });
    els.forEach(e => io.observe(e));
    return () => io.disconnect();
  }, [r.sections]);

  const cite = (text: string): ReactNode[] => {
    const out: ReactNode[] = [];
    let last = 0;
    for (const m of Array.from(text.matchAll(GROUP))) {
      if (m.index! > last) out.push(text.slice(last, m.index));
      const ids = m[1].split(/\s*[;,]\s*/);
      out.push(
        <span key={m.index} className="whitespace-nowrap">
          {ids.map(id => {
            const c = r.cited[id];
            return (
              <button key={id} type="button" onClick={() => setActive(id)}
                title={c?.text ?? "Not found in the graph"}
                className={`ml-1 rounded-md px-1.5 py-px align-[1px] font-mono text-[11px] font-semibold transition
                  ${active === id ? "bg-accent text-white" : c ? "bg-accent-wash text-accent-deep hover:bg-accent hover:text-white" : "bg-red-50 text-red-700"}`}>
                {id}
              </button>
            );
          })}
        </span>,
      );
      last = m.index! + m[0].length;
    }
    if (last < text.length) out.push(text.slice(last));
    return out;
  };

  const walk = (children: ReactNode): ReactNode =>
    Children.map(children, ch =>
      typeof ch === "string" ? cite(ch)
        : isValidElement(ch) && (ch.props as any).children
          ? cloneElement(ch as any, {}, walk((ch.props as any).children)) : ch);

  const md = {
    p: ({ children }: any) => {
      const first = Children.toArray(children)[0];
      if (typeof first === "string" && /^so what:/i.test(first.trim())) {
        const rest = Children.toArray(children);
        rest[0] = (first as string).replace(/^\s*so what:\s*/i, "");
        return (
          <div className="my-5 rounded-xl bg-accent-wash px-4 py-3 text-[15px] leading-relaxed text-ink">
            <span className="mr-2 text-[12px] font-semibold uppercase tracking-wide text-accent-deep">So what</span>
            {walk(rest)}
          </div>
        );
      }
      return <p className="mb-4 text-[15.5px] leading-[1.75] text-ink-2">{walk(children)}</p>;
    },
    li: ({ children }: any) => <li className="mb-2 pl-1 text-[15.5px] leading-[1.7] text-ink-2">{walk(children)}</li>,
    ol: ({ children }: any) => <ol className="mb-4 list-decimal pl-6 marker:font-semibold marker:text-muted">{children}</ol>,
    ul: ({ children }: any) => <ul className="mb-4 list-disc pl-6 marker:text-muted">{children}</ul>,
    h3: ({ children }: any) => <h3 className="mb-2 mt-6 text-[17px] font-semibold text-ink">{walk(children)}</h3>,
    strong: ({ children }: any) => <strong className="font-semibold text-ink">{children}</strong>,
    table: ({ children }: any) => <div className="my-4 overflow-x-auto"><table className="w-full border-collapse text-[14px]">{children}</table></div>,
    th: ({ children }: any) => <th className="border-b border-line bg-paper px-3 py-2 text-left font-semibold">{walk(children)}</th>,
    td: ({ children }: any) => <td className="border-b border-line px-3 py-2 align-top text-ink-2">{walk(children)}</td>,
    a: ({ href, children }: any) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">{children}</a>,
  };

  const date = new Date(r.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const st = r.stats;
  const cited = active ? r.cited[active] : null;

  return (
    <div className="mx-auto grid max-w-[1320px] gap-8 xl:grid-cols-[190px_minmax(0,1fr)_320px] lg:grid-cols-[minmax(0,1fr)_320px]">
      {/* contents */}
      <nav className="no-print sticky top-6 hidden self-start xl:block">
        <div className="mb-3 text-xs font-medium text-muted">Contents</div>
        <ol className="space-y-1 border-l border-line">
          {r.sections.map((s, i) => (
            <li key={s.key}>
              <a href={`#${s.key}`}
                className={`-ml-px block border-l-2 py-1 pl-3 text-[13px] leading-snug transition
                  ${current === s.key ? "border-accent font-semibold text-ink" : "border-transparent text-muted hover:text-ink"}`}>
                <span className="mr-1.5 tabular-nums text-faint">{i + 1}</span>{s.title}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      {/* the report */}
      <article className="min-w-0">
        <header className="mb-6">
          <div className="text-[13px] font-semibold text-accent">
            Strategic foresight · {(r.pillar ?? "").replace(/_/g, " ").toLowerCase().replace(/^\w/, c => c.toUpperCase())}
          </div>
          <h1 className="mt-2 text-[34px] font-semibold leading-[1.08] tracking-[-0.03em] text-ink md:text-[42px]">{r.title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-muted">
            <span>{date}</span>
            <span className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${r.status === "GATES_OPEN" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
              {r.status === "GATES_OPEN" ? "UAE gates open" : r.status.replace(/_/g, " ").toLowerCase()}
            </span>
            {r.template && <span>{r.template}</span>}
          </div>

          <div className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-4">
            {[
              [`${st.cited}/${st.sentences}`, "sentences cited"],
              [st.evidence, "evidence rows"],
              [st.publishers, "publishers"],
              [st.tier1, "Tier-1 rows"],
            ].map(([v, l]) => (
              <div key={String(l)} className="bg-white px-4 py-3">
                <div className="text-[22px] font-semibold tracking-tight text-ink">{v}</div>
                <div className="text-[12px] text-muted">{l}</div>
              </div>
            ))}
          </div>

          <div className="no-print mt-4 flex flex-wrap gap-2">
            <a href={`/api/report/${r.id}/export?format=html`} className="rounded-full bg-ink px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-black active:scale-[.98]">Download HTML</a>
            <a href={`/api/report/${r.id}/export?format=md`} className="rounded-full border border-line bg-white px-4 py-2 text-[13px] font-semibold text-ink transition hover:bg-paper active:scale-[.98]">Download Markdown</a>
            <button type="button" onClick={() => window.print()} className="rounded-full border border-line bg-white px-4 py-2 text-[13px] font-semibold text-ink transition hover:bg-paper active:scale-[.98]">Save as PDF</button>
            <a href={`/api/report/${r.id}/export?format=html&view=1`} target="_blank" rel="noopener noreferrer" className="px-2 py-2 text-[13px] font-semibold text-accent hover:underline">Open standalone ↗</a>
          </div>
        </header>

        <div data-report-body className="flex flex-col gap-4">
          {r.sections.map((s, i) => (
            <section key={s.key} id={s.key} className="scroll-mt-6 rounded-2xl bg-white px-6 py-6 shadow-[0_1px_2px_rgba(0,0,0,.04)] md:px-8">
              <div className="mb-1 text-[12px] font-semibold tabular-nums text-faint">{String(i + 1).padStart(2, "0")}</div>
              <h2 className="mb-4 text-[22px] font-semibold tracking-[-0.02em] text-ink">{s.title}</h2>
              {s.md
                ? <ReactMarkdown components={md as any}>{s.md}</ReactMarkdown>
                : <p className="text-[14px] italic text-muted">Withheld — this section could not be verified against the evidence graph.</p>}
            </section>
          ))}
        </div>
      </article>

      {/* the source panel */}
      <aside className="no-print sticky top-6 hidden self-start lg:block">
        <div className="rounded-2xl bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,.04)]">
          {!cited ? (
            <>
              <div className="text-[14px] font-semibold text-ink">Check any sentence</div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
                Click a citation like <span className="rounded bg-accent-wash px-1 font-mono text-[11px] font-semibold text-accent-deep">EV-370</span> to
                see the claim, the source&rsquo;s exact words, and who published it.
              </p>
              <div className="mt-4 text-[12px] text-faint">{Object.keys(r.cited).length} citations resolved in this report</div>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="rounded-md bg-accent-wash px-2 py-0.5 font-mono text-[12px] font-semibold text-accent-deep">{cited.id}</span>
                <span className="text-[12px] font-medium text-muted">{KIND[cited.kind]}</span>
              </div>
              <p className="mt-3 text-[14px] leading-relaxed text-ink">{cited.text}</p>
              {cited.quote && (
                <>
                  <div className="mt-4 text-[11px] font-medium uppercase tracking-wide text-faint">Source&rsquo;s exact words</div>
                  <blockquote className="mt-1.5 border-l-2 border-accent/40 pl-3 text-[13px] italic leading-relaxed text-muted">&ldquo;{cited.quote}&rdquo;</blockquote>
                </>
              )}
              <div className="mt-4 flex flex-wrap gap-1.5">
                {cited.tier && <span className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${cited.tier === 1 ? "bg-ink text-white" : "bg-paper text-muted"}`}>Tier {cited.tier}</span>}
                {cited.cls && <span className="rounded-md bg-paper px-2 py-0.5 text-[11px] font-semibold text-muted">Class {cited.cls}</span>}
                {cited.strength && <span className="rounded-md bg-paper px-2 py-0.5 text-[11px] font-semibold text-muted">{cited.strength.replace(/_/g, " ").toLowerCase()}</span>}
                {cited.status && <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">{cited.status}</span>}
              </div>
              {cited.publisher && <div className="mt-3 text-[13px] font-semibold text-ink">{cited.publisher}</div>}
              {cited.published && <div className="text-[12px] text-muted">{cited.published}</div>}
              {cited.url && (
                <a href={cited.url} target="_blank" rel="noopener noreferrer" className="mt-2 block break-words text-[12px] text-accent hover:underline">
                  {cited.docTitle ?? cited.url} ↗
                </a>
              )}
              <button type="button" onClick={() => setActive(null)} className="mt-4 text-[12px] font-medium text-muted hover:text-ink">Close</button>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
