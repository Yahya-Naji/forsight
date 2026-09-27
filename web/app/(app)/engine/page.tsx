import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { LAYER, STAGES, STAGE_KEYS } from "@/lib/engine";
import OntologyContract from "@/components/OntologyContract";
import StageTrace, { type StageRow } from "@/components/StageTrace";
import CalibrationPanel, { type ForecastRow } from "@/components/CalibrationPanel";
import AssemblyLedger, { type LedgerRow } from "@/components/AssemblyLedger";
import ScorecardStrip from "@/components/ScorecardStrip";
import { PILLAR_LABEL } from "@/components/chips";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// Which stage owns each refusal. research_gaps.raised_by names the rule that
// refused; this maps the rule back to the stage it belongs to, so the ledger can
// be shown against the step that produced it rather than as one undifferentiated
// pile.
const REFUSAL_STAGE: Record<string, string> = {
  "collect.lane_a": "collect",
  "collect.lane_b": "collect",
  "collect.lane_c": "collect",
  "extract.schema": "extract",
  "extract.quote": "gate2",
  corroboration_admission: "synthesize",
  trend_admission: "synthesize",
  finding_admission: "synthesize",
  finding_substance: "synthesize",
  risk_admission: "synthesize",
  "forecast.admission": "forecast",
  "forecast.placeholder": "forecast",
  "generate.indicator_threshold": "generate",
};

const PILLARS = ["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"] as const;

export default async function Engine({
  searchParams,
}: {
  searchParams?: { pillar?: string; run?: string; error?: string };
}) {
  const pillar = PILLARS.includes(searchParams?.pillar as any)
    ? (searchParams!.pillar as string)
    : "CYBERSECURITY";

  const head = (t: string) => supabase.from(t).select("id", { count: "exact", head: true });
  const headP = (t: string) =>
    supabase.from(t).select("id", { count: "exact", head: true }).eq("pillar", pillar);

  const [
    documents, figures, evidence, signals, trends, findings, risks,
    uncertainties, forecastsCount, gates, gaps, forecastRows, report, run, scorecard,
  ] = await Promise.all([
    head("documents"), headP("figures"), headP("evidence"), headP("signals"),
    headP("trends"), headP("findings"), head("risks"), headP("uncertainties"),
    headP("forecasts"),
    supabase.from("validation_gates").select("id,status"),
    supabase.from("research_gaps").select("raised_by,gap").eq("pillar", pillar),
    supabase.from("forecasts")
      .select("id,statement,horizon,plausibility,falsifier,basis")
      .eq("pillar", pillar).order("id"),
    supabase.from("reports").select("id,title,created_at")
      .eq("pillar", pillar).order("created_at", { ascending: false }).limit(1),
    supabase.from("pipeline_runs").select("id,pillar,status,stage,counts,error,requested_at")
      .order("requested_at", { ascending: false }).limit(1),
    supabase.from("scorecards").select("*").order("created_at", { ascending: false }).limit(1),
  ]);

  const counts: Record<string, number> = {
    documents: documents.count ?? 0, figures: figures.count ?? 0,
    evidence: evidence.count ?? 0, signals: signals.count ?? 0,
    trends: trends.count ?? 0, findings: findings.count ?? 0,
    risks: risks.count ?? 0, uncertainties: uncertainties.count ?? 0,
    forecasts: forecastsCount.count ?? 0,
    validation_gates: (gates.data ?? []).length,
  };
  const openGates = (gates.data ?? []).filter((g: any) => g.status === "OPEN").length;

  // Refusals, grouped by rule then attributed to a stage.
  const byRule = new Map<string, { count: number; sample?: string }>();
  for (const g of gaps.data ?? []) {
    const k = g.raised_by ?? "unattributed";
    const cur = byRule.get(k) ?? { count: 0, sample: g.gap ?? undefined };
    byRule.set(k, { count: cur.count + 1, sample: cur.sample });
  }
  const refusalsFor = (stageKey: string) =>
    [...byRule.entries()]
      .filter(([rule]) => (REFUSAL_STAGE[rule] ?? "synthesize") === stageKey)
      .map(([rule, v]) => ({ rule, count: v.count, sample: v.sample }))
      .sort((a, b) => b.count - a.count);

  const reportRow = report.data?.[0];
  const ledger: LedgerRow[] = reportRow
    ? ((await supabase.from("generation_ledger")
        .select("section_key,section_title,rows_passed,rows_withheld,retries,withheld,citations_emitted")
        .eq("report_id", reportRow.id)).data ?? []) as LedgerRow[]
    : [];

  // Objects carried out of each stage. Where a stage transforms rather than
  // produces (the gates, the rules pass), the count it inherits is the honest
  // number — nothing new was created, and nothing is invented for the chart.
  const flowing: Record<string, number | null> = {
    collect: counts.documents,
    gate1: counts.documents,
    extract: counts.evidence,
    gate2: counts.evidence,
    rules: counts.evidence,
    synthesize: counts.signals + counts.trends + counts.findings + counts.risks,
    forecast: counts.forecasts,
    generate: ledger.length || null,
    verify: ledger.filter((r) => !r.withheld).length || null,
  };

  const reached = run.data?.[0]?.stage ? STAGE_KEYS.indexOf(run.data[0].stage) : -1;
  const runStatus = run.data?.[0]?.status;
  const stateFor = (i: number): StageRow["state"] => {
    if (!runStatus) return "idle";
    if (runStatus === "DONE") return "done";
    if (runStatus === "FAILED" && reached === i) return "failed";
    if (reached > -1 && i < reached) return "done";
    if (reached === i) return "active";
    return "idle";
  };

  const sc = scorecard.data?.[0] as any;

  const rows: StageRow[] = STAGES.map((stage, i) => ({
    stage,
    flowing: flowing[stage.key] ?? null,
    refusals: refusalsFor(stage.key),
    state: stateFor(i),
    detail:
      stage.key === "forecast" ? (
        <CalibrationPanel forecasts={(forecastRows.data ?? []) as ForecastRow[]} />
      ) : stage.key === "generate" ? (
        <AssemblyLedger rows={ledger} reportTitle={reportRow?.title} />
      ) : stage.key === "rules" && openGates > 0 ? (
        <div style={{
          marginTop: 11, padding: "9px 12px", borderRadius: 9,
          background: "var(--amber-bg)", border: "1px solid var(--amber-line)",
          fontSize: 12.5, color: "var(--amber-ink)", lineHeight: 1.5,
        }}>
          {`${openGates} gate${openGates === 1 ? "" : "s"} open. While a gate is open the claims `}
          it names cannot be asserted anywhere downstream — not in a finding, not in a
          forecast, not in a sentence of the brief.{" "}
          <Link href="/refusals" style={{ color: "var(--amber-ink)", textDecoration: "underline" }}>
            See what is blocked
          </Link>
        </div>
      ) : stage.key === "verify" && sc ? (
        <ScorecardStrip card={sc} />
      ) : undefined,
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 30 }}>
      {/* ---------------------------------------------------------------- hero */}
      <section className="aurora" style={{ padding: "32px 36px 28px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 26, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div style={{ maxWidth: "60ch" }}>
            <div className="kicker" style={{ color: "#93A7E8" }}>The engine · {PILLAR_LABEL[pillar] ?? pillar}</div>
            <h1 className="display" style={{ fontWeight: 700, fontSize: 36, margin: "10px 0 0", letterSpacing: -0.5, lineHeight: 1.12 }}>
              A model drafts. The rules decide.
            </h1>
            <div style={{ fontSize: 14, color: "#B8C4EE", marginTop: 10, lineHeight: 1.55 }}>
              This is the same engine that writes the briefs — not a diagram of it. Every
              number below is read live from the graph, and every refusal names the rule
              that made it.
            </div>
          </div>
          <form action="/api/generate" method="post" style={{ display: "flex", flexDirection: "column", gap: 9, minWidth: 236 }}>
            <input type="hidden" name="template" value="TPL-ADVANCE-01" />
            <input type="hidden" name="pillar" value={pillar} />
            <label style={{ fontSize: 11, color: "#9FB0E6", letterSpacing: .4 }}>Run it on a question</label>
            <input name="title" defaultValue="What changed, what follows, what to decide"
                   style={{
                     fontFamily: "inherit", fontSize: 13, padding: "9px 12px", borderRadius: 10,
                     border: "1px solid rgba(255,255,255,.18)", background: "rgba(255,255,255,.07)", color: "#fff",
                   }} />
            <button className="pill-btn" type="submit" style={{ background: "#5B7CF0" }}>
              Run this engine
            </button>
            <div style={{ fontSize: 11, color: "#8493C8", lineHeight: 1.45 }}>
              Queues the same pipeline the Generate tab uses. Nothing is marked done until
              it actually runs.
            </div>
          </form>
        </div>

        {/* the authority legend — the one thing to understand before reading on */}
        <div style={{ display: "flex", gap: 10, marginTop: 24, flexWrap: "wrap" }}>
          {(["SOURCE", "NEURAL", "SYMBOLIC"] as const).map((k) => (
            <div key={k} style={{
              flex: "1 1 240px", background: "rgba(255,255,255,.055)",
              border: "1px solid rgba(255,255,255,.13)", borderRadius: 12, padding: "12px 15px",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <span style={{ width: 8, height: 8, borderRadius: 5, background: k === "SOURCE" ? "#5FD0DE" : k === "NEURAL" ? "#8AA4FF" : "#C3CBE6" }} />
                <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: .5, textTransform: "uppercase", color: "#E6EBFF" }}>
                  {LAYER[k].label}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "#A9B6E4", marginTop: 5, lineHeight: 1.45 }}>{LAYER[k].note}</div>
            </div>
          ))}
        </div>

        {searchParams?.error && (
          <div style={{ marginTop: 14, fontSize: 12.5, color: "#FF9A9A" }}>
            {searchParams.error === "no-service-key"
              ? "Set SUPABASE_SERVICE_KEY to record runs — the browser key cannot write."
              : `Could not queue the run: ${searchParams.error}`}
          </div>
        )}
        {run.data?.[0] && (
          <div style={{ marginTop: 14, fontSize: 12.5, color: "#C6CFF2" }}>
            Latest run · {run.data[0].status}
            {run.data[0].stage ? ` at ${run.data[0].stage}` : ""}
            {run.data[0].error ? ` — ${run.data[0].error}` : ""}
          </div>
        )}
      </section>

      {/* pillar switch — the engine is the same for each, the graph is not */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span className="kicker" style={{ marginRight: 4 }}>Graph</span>
        {PILLARS.map((p) => (
          <Link key={p} href={`/engine?pillar=${p}`} className="chip" style={{
            fontSize: 11.5, padding: "5px 11px",
            color: p === pillar ? "#fff" : "var(--muted)",
            background: p === pillar ? "var(--accent)" : "var(--line-soft)",
          }}>{PILLAR_LABEL[p] ?? p}</Link>
        ))}
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--faint)" }}>
          {counts.evidence} evidence · {counts.signals} signals · {counts.forecasts} forecasts ·{" "}
          {[...byRule.values()].reduce((a, v) => a + v.count, 0)} refusals recorded
        </span>
      </div>

      <OntologyContract counts={counts} />
      <StageTrace rows={rows} />

      <section style={{
        border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: "18px 20px",
        background: "var(--card)",
      }}>
        <div className="kicker">Why it is built this way</div>
        <div style={{ fontSize: 13.5, color: "var(--ink-2)", marginTop: 8, lineHeight: 1.6, maxWidth: "76ch" }}>
          A language model asked to assess evidence will also grade its own assessment, and
          it will do so fluently. Splitting the work removes that: the model is used where
          judgement about language is needed — reading a page, drafting a claim, writing a
          paragraph — and every decision that changes what a reader is told is made by code
          that can be read, rerun and disagreed with.{" "}
          <span style={{ color: "var(--ink)", fontWeight: 600 }}>
            That is why the refusal count is on this page.
          </span>{" "}
          A system that never refuses is not being careful, and the only way to show care is
          to show what was turned down and on what grounds.
        </div>
      </section>
    </div>
  );
}
