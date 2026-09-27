import Link from "next/link";
import { supabase } from "@/lib/supabase";
import Skyline from "@/components/Skyline";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// The chain on the right is assembled from a real row. A landing page that
// mocks the product's central claim would be the one dishonest surface in a
// system built to be checkable.
async function chain() {
  const { data: ev } = await supabase
    .from("evidence")
    .select("id,claim,quote_span,class,env_layer")
    .in("class", ["A", "B"]).not("quote_span", "is", null)
    .order("id").limit(1);
  const e = ev?.[0];
  if (!e) return null;

  const { data: src } = await supabase
    .from("evidence_sources").select("documents(title,url,published_on,registry_id)")
    .eq("evidence_id", e.id).limit(1);
  const doc: any = src?.[0]?.documents;
  const { data: reg } = doc?.registry_id
    ? await supabase.from("source_registry").select("publisher,tier").eq("id", doc.registry_id).single()
    : { data: null };

  return { e, doc, reg };
}

export default async function Landing() {
  const [c, counts, gates] = await Promise.all([
    chain(),
    (async () => {
      const [d, s, g] = await Promise.all([
        supabase.from("documents").select("id", { count: "exact", head: true }),
        supabase.from("source_registry").select("id", { count: "exact", head: true }),
        supabase.from("evidence").select("id", { count: "exact", head: true }),
      ]);
      return { docs: d.count ?? 0, sources: s.count ?? 0, evidence: g.count ?? 0 };
    })(),
    supabase.from("validation_gates").select("id", { count: "exact", head: true }).eq("status", "OPEN"),
  ]);

  return (
    <div style={{ minHeight: "100vh", background: "var(--aurora)", color: "#fff", position: "relative", overflow: "hidden" }}>
      <Skyline />

      <div style={{ position: "relative", zIndex: 2, maxWidth: 1240, margin: "0 auto", padding: "0 28px" }}>
        <header className="row" style={{ justifyContent: "space-between", padding: "22px 0" }}>
          <div className="display" style={{ fontWeight: 700, fontSize: 17, letterSpacing: -0.3 }}>
            FORESIGHT<span style={{ color: "var(--accent)" }}>.</span>
          </div>
          <nav className="row" style={{ gap: 26, fontSize: 13.5 }}>
            <Link href="/reports" style={{ color: "#C6CFF2", textDecoration: "none" }}>Sample brief</Link>
            <Link href="/evidence" style={{ color: "#C6CFF2", textDecoration: "none" }}>Evidence</Link>
            <Link href="/console" className="pill-btn" style={{ textDecoration: "none", padding: "9px 17px" }}>
              Open the console
            </Link>
          </nav>
        </header>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", gap: 48, alignItems: "center", minHeight: "calc(100vh - 110px)", paddingBottom: 60 }}>
          {/* ── the claim ── */}
          <div style={{ border: "1px solid rgba(91,124,240,.55)", borderRadius: 16, padding: "38px 34px", background: "rgba(10,15,46,.42)", backdropFilter: "blur(3px)" }}>
            <div style={{ fontFamily: "'Space Grotesk'", fontSize: 11, letterSpacing: 2, color: "#8FA3E8", textTransform: "uppercase" }}>
              Strategic foresight · UAE defence
            </div>
            <h1 className="display" style={{ fontSize: 46, lineHeight: 1.08, letterSpacing: -1.1, margin: "18px 0 0", fontWeight: 700 }}>
              Every sentence can prove where it came from.
            </h1>
            <p style={{ marginTop: 18, fontSize: 15, lineHeight: 1.62, color: "#C6CFF2", maxWidth: "46ch" }}>
              Briefs assembled from a governed evidence graph — {counts.sources} tiered sources,
              refreshed daily. Follow any claim down to the exact words of its source.
            </p>

            <div className="row" style={{ gap: 14, marginTop: 26 }}>
              <Link href="/console" className="pill-btn" style={{ textDecoration: "none" }}>Open the console</Link>
              <Link href="/reports" style={{ color: "#fff", textDecoration: "none", fontSize: 13.5, fontWeight: 600 }}>
                Read the sample brief →
              </Link>
            </div>

            <div style={{ marginTop: 28, border: "1px solid rgba(255,183,77,.34)", background: "rgba(255,183,77,.07)", borderRadius: 12, padding: "14px 16px" }}>
              <div style={{ fontFamily: "'Space Grotesk'", fontSize: 10.5, letterSpacing: 1.6, color: "#FFC96B", textTransform: "uppercase" }}>
                And when the evidence doesn&rsquo;t exist
              </div>
              <p style={{ marginTop: 7, fontSize: 13, lineHeight: 1.55, color: "#E4E9FA" }}>
                The brief prints <b>&ldquo;Customer Validation Required&rdquo;</b> instead of a guess.
                A rule blocks the claim — no prompt, no exceptions.
                {(gates.count ?? 0) > 0 && <> {gates.count} gate{(gates.count ?? 0) > 1 ? "s are" : " is"} open right now.</>}
              </p>
            </div>
          </div>

          {/* ── the proof ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {c ? (
              <>
                <Card label="A sentence from the brief">
                  <p style={{ fontSize: 14.5, lineHeight: 1.6, color: "var(--ink)" }}>
                    {c.e.claim}{" "}
                    <span className="chip" style={{ background: "var(--accent-wash)", color: "var(--accent-deep)", border: "1px solid rgba(91,124,240,.3)" }}>
                      {c.e.id}
                    </span>
                  </p>
                </Card>
                <Connector text="traces to" />
                <Card label="The source's exact words" inset>
                  <p className="quote" style={{ fontSize: 13, lineHeight: 1.62 }}>
                    &ldquo;{(c.e.quote_span ?? "").slice(0, 210)}&rdquo;
                  </p>
                </Card>
                <Connector text="published by" />
                <Card inset>
                  <div className="row" style={{ justifyContent: "space-between", gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>
                        {c.reg?.publisher ?? c.doc?.title ?? "Source"}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>
                        {c.doc?.published_on ?? "retrieved"} · {(c.doc?.url ?? "").replace(/^https?:\/\//, "").split("/")[0]}
                      </div>
                    </div>
                    {c.reg?.tier && (
                      <span className={`chip ${c.reg.tier === 1 ? "chip-tier1" : "chip-tier"}`}>TIER {c.reg.tier}</span>
                    )}
                  </div>
                </Card>
                <p style={{
                  marginTop: 16, fontSize: 12, color: "#B6C4EE", lineHeight: 1.55,
                  background: "rgba(8,12,34,.62)", borderRadius: 8, padding: "8px 11px",
                  backdropFilter: "blur(2px)", alignSelf: "flex-start",
                }}>
                  Every claim in every brief carries this chain — {counts.evidence} rows across {counts.docs} documents.
                  Open a report and click any citation to walk it.
                </p>
              </>
            ) : (
              <Card label="Nothing to show yet">
                <p style={{ fontSize: 13.5, color: "var(--muted)" }}>
                  The graph is empty. Run collection and extraction, and the chain appears here.
                </p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Card({ label, children, inset }: { label?: string; children: React.ReactNode; inset?: boolean }) {
  return (
    <div style={{
      background: "var(--card)", borderRadius: 14, padding: "16px 18px",
      marginLeft: inset ? 34 : 0, boxShadow: "0 18px 44px rgba(4,8,28,.34)",
    }}>
      {label && <div className="kicker" style={{ marginBottom: 8 }}>{label}</div>}
      {children}
    </div>
  );
}

function Connector({ text }: { text: string }) {
  return (
    <div className="row" style={{ gap: 10, padding: "10px 0 10px 16px" }}>
      <span style={{ width: 9, height: 9, borderRadius: 5, background: "var(--accent)", flexShrink: 0 }} />
      <span style={{ fontFamily: "'Space Grotesk'", fontSize: 10, letterSpacing: 1.6, textTransform: "uppercase", color: "#8FA3E8" }}>
        {text}
      </span>
      <span style={{ flex: 1, height: 1, background: "linear-gradient(90deg, rgba(91,124,240,.5), transparent)" }} />
    </div>
  );
}
