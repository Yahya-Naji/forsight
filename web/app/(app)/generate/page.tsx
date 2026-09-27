import { supabase } from "@/lib/supabase";
import { PILLAR_LABEL } from "@/components/chips";

export const revalidate = 0;
export const dynamic = "force-dynamic";

// The first element is the contract with the Python pipeline: update_run()
// writes one of these keys into pipeline_runs.stage and the checklist lights
// up to it.
const STAGES = [
  ["collect", "Collect", "documents from lanes A, B, C with source tiers"],
  ["gate1", "Gate 1 · relevance", "cheap typed triage — irrelevant documents stop here"],
  ["extract", "Extract", "LLM emits claims, schema-checked"],
  ["gate2", "Gate 2 · quote check", "claims must be entailed by their verbatim quote"],
  ["rules", "Rules & gates", "class, confidence, signal strength, UAE guard"],
  ["synthesize", "Synthesize", "signals, findings and risks admitted by rule"],
  ["forecast", "Forecast", "outlook with computed plausibility and a falsifier"],
  ["generate", "Generate", "section-scoped inputs, per-claim citations"],
  ["verify", "Verify", "citations resolve · gates honoured · entailment"],
] as const;

const RUN_STATUS: Record<string, { text: string; fg: string; bg: string; bd: string }> = {
  QUEUED:  { text: "Queued",  fg: "#C6CFF2", bg: "rgba(198,207,242,.10)", bd: "rgba(198,207,242,.30)" },
  RUNNING: { text: "Running", fg: "#FFC96B", bg: "rgba(255,183,77,.12)",  bd: "rgba(255,183,77,.35)" },
  DONE:    { text: "Done",    fg: "#7EE0A9", bg: "rgba(74,222,128,.12)",  bd: "rgba(74,222,128,.30)" },
  FAILED:  { text: "Failed",  fg: "#FF9A9A", bg: "rgba(255,120,120,.12)", bd: "rgba(255,120,120,.35)" },
};

export default async function Generate({ searchParams }: { searchParams?: { run?: string; error?: string } }) {
  const latest = await supabase.from("reports").select("id,title,status,created_at").order("created_at", { ascending: false }).limit(1);
  const report = latest.data?.[0];

  const runs = await supabase
    .from("pipeline_runs")
    .select("id,pillar,status,stage,counts,error,requested_at")
    .order("requested_at", { ascending: false })
    .limit(1);
  const run = runs.data?.[0];

  const reached = run?.stage ? STAGES.findIndex((s) => s[0] === run.stage) : -1;
  const done = run?.status === "DONE";
  const failed = run?.status === "FAILED";
  const badge = RUN_STATUS[run?.status ?? ""] ?? null;
  const counts = (run?.counts ?? {}) as Record<string, number>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 22, alignItems: "start" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <div className="kicker">New report</div>
          <h1 className="display" style={{ fontWeight: 700, fontSize: 26, margin: "4px 0 0", letterSpacing: -0.4 }}>Generate a brief</h1>
        </div>
        <form className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }} action="/api/generate" method="post">
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)" }}>Pillar</div>
            <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
              {Object.entries(PILLAR_LABEL).map(([key, name], i) => (
                <label key={key} style={{
                  fontSize: 12, fontWeight: 600, borderRadius: 999, padding: "7px 14px", cursor: "pointer",
                  color: i === 0 ? "#fff" : "var(--muted)",
                  background: i === 0 ? "var(--navy)" : "var(--paper)",
                  border: i === 0 ? "1px solid var(--navy)" : "1px solid var(--line)",
                }}>
                  <input type="radio" name="pillar" value={key} defaultChecked={i === 0} style={{ display: "none" }} />
                  {name}
                </label>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)" }}>Template</div>
            <div className="row" style={{ justifyContent: "space-between", border: "1px solid var(--line)", borderRadius: 10, padding: "11px 14px", marginTop: 8, fontSize: 13.5 }}>
              <span style={{ fontWeight: 600 }}>Strategic Foresight Brief</span>
              <span style={{ color: "var(--ghost)", fontSize: 11 }}>7 sections</span>
            </div>
          </div>
          <button className="pill-btn" type="submit">Run the pipeline</button>
          <div style={{ fontSize: 11.5, color: "var(--faint)", lineHeight: 1.5 }}>
            Sections that fail verification are withheld, never shipped. Open gates render as &ldquo;Customer Validation Required&rdquo;.
          </div>
        </form>
      </div>

      <div className="aurora" style={{ padding: "28px 32px", minHeight: 560, display: "flex", flexDirection: "column" }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="display" style={{ fontWeight: 600, fontSize: 18 }}>
            {run ? `${PILLAR_LABEL[run.pillar] ?? run.pillar} run` : report ? report.title : "No run yet"}
          </div>
          {badge && (
            <span style={{
              fontSize: 11, fontWeight: 700, letterSpacing: 1, borderRadius: 999, padding: "5px 12px",
              color: badge.fg, background: badge.bg, border: `1px solid ${badge.bd}`,
            }}>{badge.text}</span>
          )}
        </div>
        {searchParams?.error && (
          <div style={{ marginTop: 12, fontSize: 12.5, color: "#FF9A9A" }}>
            {searchParams.error === "no-service-key"
              ? "Set SUPABASE_SERVICE_KEY to record runs — the browser key cannot write."
              : `Could not queue the run: ${searchParams.error}`}
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", marginTop: 22 }}>
          {STAGES.map(([key, name, sub], i) => {
            const complete = done || (reached > -1 && i < reached);
            const active = !done && !failed && reached === i;
            const stalled = failed && reached === i;
            const n = counts[key];
            return (
              <div key={key} className="row" style={{ gap: 14, padding: "9px 0", opacity: complete || active || stalled ? 1 : 0.45 }}>
                <span style={{
                  width: 22, height: 22, borderRadius: 11, flexShrink: 0, display: "flex", alignItems: "center",
                  justifyContent: "center", fontSize: 12, fontWeight: 700,
                  background: stalled ? "#FF7878" : complete ? "#4ADE80" : active ? "#FFC96B" : "transparent",
                  color: "#0A0F2E",
                  border: complete || active || stalled ? "none" : "1.5px solid #5A6698",
                }}>{stalled ? "!" : complete ? "✓" : active ? "•" : ""}</span>
                <span style={{ fontSize: 14, fontWeight: 600, width: 160 }}>{name}</span>
                <span style={{ fontSize: 12.5, color: "#9FB0E6" }}>{sub}</span>
                {typeof n === "number" && (
                  <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 700, color: "#C6CFF2" }}>{n}</span>
                )}
              </div>
            );
          })}
        </div>
        <div style={{ flexGrow: 1 }} />
        <div style={{ borderTop: "1px solid rgba(255,255,255,.12)", paddingTop: 16, fontSize: 12.5, color: "#C6CFF2" }}>
          {run?.error
            ? run.error
            : run?.status === "QUEUED"
            ? "Queued. The pipeline picks this up from the repo or the GitHub Action — no stage is marked until it actually runs."
            : "The pipeline runs from the repo or the daily GitHub Action; this screen reflects the latest stored run."}
        </div>
      </div>
    </div>
  );
}
