import Link from "next/link";
import { supabase } from "@/lib/supabase";
import Skyline from "@/components/Skyline";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// The chain on the right is assembled from a real row. A landing page that
// mocks the product's central claim would be the one dishonest surface in a
// system built to be checkable.
//
// It prefers a Class A row from an Electronic Warfare topic whose claim is a
// paraphrase rather than a copy of its quote, so the chain visibly does work:
// a sentence, the different words it rests on, and who published them.
async function chain() {
  const { data } = await supabase
    .from("evidence")
    .select("id,claim,quote_span,class,env_layer,topic_id")
    .is("archived_at", null).eq("class", "A").like("topic_id", "EW-%")
    .not("quote_span", "is", null)
    .order("created_at", { ascending: false }).limit(60);
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const rows = data ?? [];
  const e = rows.find(r => r.quote_span.length >= 90 && r.quote_span.length <= 240
                         && norm(r.claim) !== norm(r.quote_span)) ?? rows[0];
  if (!e) return null;

  const [{ data: src }, { data: topic }] = await Promise.all([
    supabase.from("evidence_sources").select("documents(title,url,published_on,registry_id)")
      .eq("evidence_id", e.id).limit(1),
    supabase.from("topics").select("name").eq("id", e.topic_id).single(),
  ]);
  const doc: any = src?.[0]?.documents;
  const { data: reg } = doc?.registry_id
    ? await supabase.from("source_registry").select("publisher,tier").eq("id", doc.registry_id).single()
    : { data: null };
  return { e, doc, reg, topic: topic?.name as string | undefined };
}

export default async function Landing() {
  const [c, ev, classA, sources, topics, gates] = await Promise.all([
    chain(),
    supabase.from("evidence").select("id", { count: "exact", head: true }).is("archived_at", null),
    supabase.from("evidence").select("id", { count: "exact", head: true }).is("archived_at", null).eq("class", "A"),
    supabase.from("source_registry").select("id", { count: "exact", head: true }).is("archived_at", null),
    supabase.from("topics").select("id", { count: "exact", head: true }).is("retired_at", null),
    supabase.from("validation_gates").select("id", { count: "exact", head: true }).eq("status", "OPEN"),
  ]);
  const openGates = gates.count ?? 0;
  const stats = [
    { value: ev.count ?? 0, label: "sourced evidence rows" },
    { value: classA.count ?? 0, label: "Class A rows from Tier-1 publishers" },
    { value: sources.count ?? 0, label: "tiered sources, collected daily" },
    { value: topics.count ?? 0, label: "EW topics across 8 sub-pillars" },
  ];

  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      <Skyline />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-[1200px] flex-col px-6 md:px-10">
        <header className="flex items-center justify-between py-6">
          <div className="text-[17px] font-semibold tracking-tight">
            Foresight<span className="text-accent">.</span>
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/tree" className="hidden text-white/70 transition hover:text-white sm:inline">EW tree</Link>
            <Link href="/reports" className="hidden text-white/70 transition hover:text-white sm:inline">Sample brief</Link>
            <Link href="/overview"
                  className="rounded-full bg-white px-4 py-2 font-semibold text-black transition hover:bg-white/90 active:scale-[.98]">
              Open the console
            </Link>
          </nav>
        </header>

        <main className="grid flex-1 items-center gap-12 py-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
          {/* the claim */}
          <section>
            <p className="text-sm font-medium text-white/60">Electronic warfare foresight · Tawazun Council</p>
            <h1 className="mt-4 text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] md:text-[60px]">
              Every sentence can prove where it came from.
            </h1>
            <p className="mt-6 max-w-[46ch] text-lg leading-relaxed text-white/70">
              Strategic briefs on electronic warfare — and the cyber, AI and procurement forces acting on
              it — assembled from a governed evidence graph. Follow any claim down to the exact words of
              its source.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-5">
              <Link href="/overview"
                    className="rounded-full bg-accent px-6 py-3 text-[15px] font-semibold text-white transition hover:bg-accent-deep active:scale-[.98]">
                Open the console
              </Link>
              <Link href="/tree" className="text-[15px] font-semibold text-white/90 transition hover:text-white">
                Explore the EW tree →
              </Link>
            </div>

            <div className="mt-10 max-w-[52ch] rounded-2xl border border-white/10 bg-white/[.06] p-5 backdrop-blur-md">
              <p className="text-sm font-semibold text-[#FFC96B]">And when the evidence doesn&rsquo;t exist</p>
              <p className="mt-1.5 text-[15px] leading-relaxed text-white/75">
                The brief prints <b className="text-white">&ldquo;Customer Validation Required&rdquo;</b> instead
                of a guess. A rule blocks the claim — no prompt, no exceptions.
                {openGates > 0 && <> {openGates} UAE gate{openGates > 1 ? "s are" : " is"} open right now.</>}
              </p>
            </div>
          </section>

          {/* the proof */}
          <section className="flex flex-col">
            {c ? (
              <>
                <Card label={c.topic ? `A claim in the graph · ${c.topic}` : "A claim in the graph"}>
                  <p className="text-[15px] leading-relaxed text-ink">
                    {c.e.claim}{" "}
                    <span className="ml-1 rounded-md bg-accent-wash px-1.5 py-0.5 font-mono text-[11px] font-semibold text-accent-deep">
                      {c.e.id}
                    </span>
                  </p>
                </Card>
                <Connector text="rests on" />
                <Card label="The source's exact words" inset>
                  <p className="border-l-2 border-accent/40 pl-3 text-sm italic leading-relaxed text-muted">
                    &ldquo;{c.e.quote_span}&rdquo;
                  </p>
                </Card>
                <Connector text="published by" />
                <Card inset>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-[15px] font-semibold text-ink">{c.reg?.publisher ?? c.doc?.title ?? "Source"}</div>
                      <div className="mt-0.5 truncate text-xs text-muted">
                        {c.doc?.published_on ?? "undated"} · {(c.doc?.url ?? "").replace(/^https?:\/\//, "").split("/")[0]}
                      </div>
                    </div>
                    {c.reg?.tier && (
                      <span className={`shrink-0 rounded-md px-2 py-1 text-[11px] font-bold ${c.reg.tier === 1 ? "bg-ink text-white" : "bg-line-soft text-muted"}`}>
                        Tier {c.reg.tier}
                      </span>
                    )}
                  </div>
                </Card>
              </>
            ) : (
              <Card label="Nothing to show yet">
                <p className="text-sm text-muted">The graph is empty. Run collection and extraction, and the chain appears here.</p>
              </Card>
            )}
          </section>
        </main>

        <section className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 mb-10 md:grid-cols-4">
          {stats.map(s => (
            <div key={s.label} className="bg-black/50 px-5 py-4 backdrop-blur-md">
              <div className="text-[28px] font-semibold tracking-tight">{s.value}</div>
              <div className="text-sm text-white/60">{s.label}</div>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

function Card({ label, children, inset }: { label?: string; children: React.ReactNode; inset?: boolean }) {
  return (
    <div className={`rounded-2xl bg-white px-5 py-4 shadow-[0_24px_60px_rgba(0,0,0,.35)] ${inset ? "ml-8" : ""}`}>
      {label && <div className="mb-2 text-xs font-medium text-muted">{label}</div>}
      {children}
    </div>
  );
}

function Connector({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2.5 py-2.5 pl-4">
      <span className="h-2 w-2 shrink-0 rounded-full bg-accent" />
      <span className="text-xs font-medium text-white/60">{text}</span>
      <span className="h-px flex-1 bg-gradient-to-r from-white/25 to-transparent" />
    </div>
  );
}
