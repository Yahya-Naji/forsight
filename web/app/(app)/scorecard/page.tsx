import { supabase } from "@/lib/supabase";
import { PILLAR_LABEL } from "@/components/chips";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// The comparison against a human-written report. Written by evaluate.py, which
// runs the same text checks over both documents so the two columns mean the
// same thing.

const REGISTERS = ["signals", "findings", "risks", "uncertainties"] as const;

export default async function Scorecard() {
  const { data } = await supabase.from("scorecards").select("*")
    .order("created_at", { ascending: false }).limit(1);
  const s = data?.[0];

  if (!s) {
    return (
      <Frame>
        <div className="card" style={{ padding: 22 }}>
          <p style={{ fontSize: 13.5, color: "var(--muted)", lineHeight: 1.6 }}>
            No evaluation yet. Run <code style={{ fontFamily: "'Space Grotesk'" }}>
            make evaluate BENCHMARK=&lt;document&gt;</code> against any .docx, .pdf,
            .txt, .md or .html, and the comparison appears here.
          </p>
        </div>
      </Frame>
    );
  }

  const ours = s.ours_text ?? {}, bench = s.benchmark_text ?? {};
  const chain = s.chain_completeness ?? {};
  const better = (a: number, b: number, lowerWins = false) =>
    lowerWins ? a < b : a > b;

  return (
    <Frame label={s.benchmark_label} pillar={s.pillar} when={s.created_at}>
      {/* ── discipline: deterministic, same code both sides ── */}
      <section className="card" style={{ padding: 20, marginBottom: 14 }}>
        <div className="section-title" style={{ marginBottom: 4 }}>Discipline</div>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14 }}>
          Measured by identical code over both documents — no model involved, so these
          numbers do not move between runs.
        </p>
        <Row head a="This system" b={s.benchmark_label ?? "Benchmark"} />
        <Row k="Unsourced assertions" a={ours.unsourced} b={bench.unsourced}
             win={better(bench.unsourced ?? 0, ours.unsourced ?? 0)} />
        <Row k="Unsourced rate" a={ours.unsourced_rate} b={bench.unsourced_rate}
             win={better(bench.unsourced_rate ?? 0, ours.unsourced_rate ?? 0)} />
        <Row k="Citations per 1,000 words" a={ours.citations_per_1k_words} b={bench.citations_per_1k_words}
             win={better(ours.citations_per_1k_words ?? 0, bench.citations_per_1k_words ?? 0)} />
        <Row k="Sentences analysed" a={ours.sentences} b={bench.sentences} />
        <Row k="Chain completeness"
             a={chain.rate != null ? `${Math.round(chain.rate * 100)}%` : "—"}
             b="not machine-readable" win />
        <Row k="Citation entailment" a="audited per report" b="not measurable — sources absent" />
      </section>

      {/* ── recall: model-matched, scoped ── */}
      <section className="card" style={{ padding: 20, marginBottom: 14 }}>
        <div className="section-title" style={{ marginBottom: 4 }}>Coverage of the benchmark</div>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14, maxWidth: "70ch", lineHeight: 1.55 }}>
          Recall is reported <b>in scope</b>: each benchmark item is classified by pillar first,
          because a benchmark may cover ground this pillar does not and a flat number would be
          near zero by construction. Matching is semantic, so these figures vary a little between runs.
        </p>
        <div className="tw" style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
            <thead>
              <tr>{["Register", "In benchmark", "In scope", "Matched", "Recall"].map(h => (
                <th key={h} style={{ textAlign: h === "Register" ? "left" : "right",
                  fontFamily: "'Space Grotesk'", fontSize: 10, letterSpacing: 1.2,
                  textTransform: "uppercase", color: "var(--muted)", fontWeight: 500,
                  padding: "0 12px 8px 0", borderBottom: "1px solid var(--line)" }}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {REGISTERS.map(r => {
                const v = (s.recall ?? {})[r] ?? {};
                const rate = v.in_scope ? v.in_scope_matched / v.in_scope : null;
                return (
                  <tr key={r}>
                    <td style={{ padding: "10px 12px 10px 0", borderBottom: "1px solid var(--line-soft)",
                                 textTransform: "capitalize", fontWeight: 600 }}>{r}</td>
                    <Num v={v.benchmark_total} /><Num v={v.in_scope} /><Num v={v.in_scope_matched} />
                    <td style={{ padding: "10px 0", borderBottom: "1px solid var(--line-soft)",
                                 textAlign: "right", fontWeight: 700,
                                 color: rate == null ? "var(--faint)"
                                   : rate >= 0.5 ? "var(--green-ink)"
                                   : rate > 0 ? "var(--amber-ink)" : "var(--muted)" }}>
                      {rate == null ? "n/a" : `${Math.round(rate * 100)}%`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card" style={{ padding: 20 }}>
        <div className="section-title" style={{ marginBottom: 4 }}>Found that the benchmark does not contain</div>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
          Items in our graph with no counterpart in the benchmark — new ground, not overlap.
        </p>
        <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
          {REGISTERS.map(r => (
            <div key={r} className="card" style={{ padding: "11px 15px", minWidth: 104, background: "var(--paper)" }}>
              <div style={{ fontSize: 21, fontWeight: 700, color: "var(--accent-deep)" }}>
                {((s.novel ?? {})[r] ?? []).length}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--muted)", textTransform: "capitalize" }}>{r}</div>
            </div>
          ))}
        </div>
      </section>
    </Frame>
  );
}

function Frame({ children, label, pillar, when }: any) {
  return (
    <div>
      <div className="kicker">Evaluation</div>
      <h1 className="display" style={{ fontWeight: 700, fontSize: 26, margin: "4px 0 8px", letterSpacing: -0.4 }}>
        Scored against a human report
      </h1>
      {label && (
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
          {PILLAR_LABEL[pillar] ?? pillar} · benchmark <b style={{ color: "var(--ink-2)" }}>{label}</b>
          {when && <> · {new Date(when).toLocaleDateString()}</>}
        </p>
      )}
      {children}
    </div>
  );
}

function Row({ k, a, b, head, win }: any) {
  return (
    <div className="row" style={{
      justifyContent: "space-between", gap: 16, padding: "9px 0",
      borderBottom: "1px solid var(--line-soft)",
      fontFamily: head ? "'Space Grotesk'" : undefined,
      fontSize: head ? 10 : 13, letterSpacing: head ? 1.2 : undefined,
      textTransform: head ? "uppercase" : undefined,
      color: head ? "var(--muted)" : "var(--ink-2)",
    }}>
      <span style={{ flex: 1, fontWeight: head ? 500 : 600 }}>{k ?? ""}</span>
      <span style={{ width: 150, textAlign: "right", fontWeight: head ? 500 : 700,
                     color: head ? "var(--muted)" : win ? "var(--green-ink)" : "var(--ink)" }}>{a}</span>
      <span style={{ width: 170, textAlign: "right", fontWeight: 500,
                     color: "var(--muted)" }}>{b}</span>
    </div>
  );
}

function Num({ v }: { v: any }) {
  return <td style={{ padding: "10px 12px 10px 0", borderBottom: "1px solid var(--line-soft)",
                      textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{v ?? "—"}</td>;
}
