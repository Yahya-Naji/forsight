import { supabase } from "@/lib/supabase";
import { label, PILLAR_LABEL } from "@/components/chips";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// What the system declined to say, and the rule that stopped it. Every tool
// shows what it produced; the refusals are the part a defence customer cannot
// get anywhere else.

const RULE: Record<string, string> = {
  uae_inference_guard: "UAE inference guard",
  corroboration_admission: "Needs two independent publishers",
  finding_admission: "Finding needs a signal",
  finding_substance: "Finding must assert something falsifiable",
  trend_admission: "Trend needs a signal",
  risk_admission: "Risk needs a finding",
  "forecast.admission": "Forecast admission",
  "collect.lane_a": "Source unreachable",
  "extract.schema": "Extraction rejected",
  "generate.indicator_threshold": "Indicator has no threshold",
};

export default async function Refusals() {
  const [gaps, gates, withheld, edits] = await Promise.all([
    supabase.from("research_gaps").select("id,pillar,gap,raised_by")
      .order("created_at", { ascending: false }).limit(50),
    supabase.from("validation_gates").select("*").eq("status", "OPEN"),
    supabase.from("generation_ledger").select("section_title,retries,failures")
      .eq("withheld", true).order("id", { ascending: false }).limit(10),
    supabase.from("report_edits").select("id,rejected_reason,proposed_text")
      .eq("status", "REJECTED").order("created_at", { ascending: false }).limit(10),
  ]);

  const G = gaps.data ?? [], GT = gates.data ?? [], W = withheld.data ?? [], E = edits.data ?? [];
  const byRule = new Map<string, number>();
  for (const g of G) byRule.set(g.raised_by ?? "—", (byRule.get(g.raised_by ?? "—") ?? 0) + 1);

  return (
    <div>
      <div className="kicker">Governance</div>
      <h1 className="display" style={{ fontWeight: 700, fontSize: 26, margin: "4px 0 8px", letterSpacing: -0.4 }}>
        What the system refused to say
      </h1>
      <p style={{ fontSize: 13.5, color: "var(--muted)", maxWidth: "66ch", lineHeight: 1.62 }}>
        Each item below was proposed and then blocked by a rule — not by a prompt, and not by
        a person. A refusal is analytical output in its own right: it records what the evidence
        could not support, which is as much a finding as anything the brief does say.
      </p>

      <div className="row" style={{ gap: 10, margin: "20px 0 22px", flexWrap: "wrap" }}>
        <Stat n={G.length + GT.length + W.length + E.length} k="blocked in total" />
        <Stat n={GT.length} k="open gates" amber />
        <Stat n={G.length} k="research gaps" />
        <Stat n={W.length} k="sections withheld" />
        <Stat n={E.length} k="edits rejected" />
      </div>

      {GT.length > 0 && (
        <section className="card" style={{ padding: 18, marginBottom: 14 }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Open validation gates</div>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
            While a gate is open, generation cannot assert what it blocks — in any wording.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {GT.map(g => (
              <div key={g.id} style={{
                background: "var(--amber-bg)", border: "1px solid var(--amber-line)",
                borderLeft: "3px solid var(--amber-ink)", borderRadius: 10, padding: "12px 14px",
              }}>
                <div className="row" style={{ justifyContent: "space-between", gap: 10 }}>
                  <span className="chip chip-open">{g.id}</span>
                  <span style={{ fontSize: 11, color: "var(--amber-ink)" }}>
                    {RULE[g.raised_by] ?? g.raised_by}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 8, lineHeight: 1.5 }}>{g.blocks}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {W.length > 0 && (
        <section className="card" style={{ padding: 18, marginBottom: 14 }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Sections withheld from a brief</div>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
            Drafted, failed verification twice, then left out rather than published with broken citations.
          </p>
          {W.map((l, i) => (
            <div key={i} style={{ borderTop: i ? "1px solid var(--line-soft)" : 0, padding: "10px 0" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span style={{ fontSize: 13.5, fontWeight: 600 }}>{l.section_title}</span>
                <span style={{ fontSize: 11, color: "var(--faint)" }}>{l.retries} retries</span>
              </div>
              {Array.isArray(l.failures) && l.failures.length > 0 && (
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 5, lineHeight: 1.5 }}>
                  {(l.failures as string[])[0]}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {E.length > 0 && (
        <section className="card" style={{ padding: 18, marginBottom: 14 }}>
          <div className="section-title" style={{ marginBottom: 10 }}>Conversational edits rejected</div>
          {E.map((e, i) => (
            <div key={e.id} style={{ borderTop: i ? "1px solid var(--line-soft)" : 0, padding: "10px 0" }}>
              <div style={{ fontSize: 12, color: "var(--amber-ink)", fontWeight: 600 }}>{e.rejected_reason}</div>
              <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4, lineHeight: 1.5 }}>
                {(e.proposed_text ?? "").slice(0, 170)}…
              </div>
            </div>
          ))}
        </section>
      )}

      <section className="card" style={{ padding: 18 }}>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
          <div className="section-title">Research gaps</div>
          <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
            {[...byRule.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([r, n]) => (
              <span key={r} className="chip chip-tier">{RULE[r] ?? r} · {n}</span>
            ))}
          </div>
        </div>
        {G.length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--muted)" }}>
            Nothing refused yet — run the pipeline and rejections appear here.
          </p>
        ) : G.map((g, i) => (
          <div key={g.id} style={{ borderTop: i ? "1px solid var(--line-soft)" : 0, padding: "11px 0" }}>
            <div className="row" style={{ gap: 8, marginBottom: 5, flexWrap: "wrap" }}>
              {g.pillar && <span className="chip chip-tier">{PILLAR_LABEL[g.pillar] ?? label(g.pillar)}</span>}
              <span style={{ fontSize: 10.5, fontFamily: "'Space Grotesk'", letterSpacing: 1,
                             textTransform: "uppercase", color: "var(--accent-deep)" }}>
                {RULE[g.raised_by] ?? g.raised_by}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.55 }}>{g.gap}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

function Stat({ n, k, amber }: { n: number; k: string; amber?: boolean }) {
  return (
    <div className="card" style={{ padding: "12px 16px", minWidth: 118 }}>
      <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.5,
                    color: amber ? "var(--amber-ink)" : "var(--ink)" }}>{n}</div>
      <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>{k}</div>
    </div>
  );
}
