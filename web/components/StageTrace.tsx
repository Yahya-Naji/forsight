import { LAYER, type Stage } from "@/lib/engine";

// The pipeline drawn as attrition rather than as progress.
//
// A row of green ticks says the run finished, which is the least interesting
// thing about it. What a reader needs to see is how much was dropped and by
// which rule — 85 candidate images admitted 7, and a checklist would show that
// as one tick. So the spine's width encodes how many objects are still carried
// at each stage, and everything refused leaves it as a labelled wedge.
//
// The taper is drawn in a normalised 0–100 viewBox with preserveAspectRatio
// switched off, so one SVG fills whatever height the band's prose needs.

export type StageRow = {
  stage: Stage;
  /** Objects still carried leaving this stage. */
  flowing: number | null;
  /** Objects this stage dropped, by the rule that dropped them. */
  refusals: { rule: string; count: number; sample?: string }[];
  /** Live run state, when a run is in flight. */
  state?: "done" | "active" | "failed" | "idle";
  /** Stage-specific panel — the forecast arithmetic, the section ledger. */
  detail?: React.ReactNode;
};

const RAIL = 96;
const MAX_W = 46;     // spine half-width at the widest point, in viewBox units

/** Square-root so an order-of-magnitude drop stays legible instead of vanishing. */
function halfWidth(n: number | null, peak: number) {
  if (!n || n <= 0 || peak <= 0) return 3;
  return Math.max(3, Math.sqrt(n / peak) * MAX_W);
}

function Spine({ inW, outW, fill, line, first, last }: {
  inW: number; outW: number; fill: string; line: string; first: boolean; last: boolean;
}) {
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden
         style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
      <polygon points={`${50 - inW},0 ${50 + inW},0 ${50 + outW},100 ${50 - outW},100`}
               fill={fill} fillOpacity="0.85" stroke={line} strokeWidth="0.5" strokeOpacity="0.45" />
      {first && <line x1={50 - inW} y1="0" x2={50 + inW} y2="0" stroke={line} strokeWidth="1.2" />}
      {last && <line x1={50 - outW} y1="100" x2={50 + outW} y2="100" stroke={line} strokeWidth="1.2" />}
    </svg>
  );
}

function Dot({ state }: { state: StageRow["state"] }) {
  const s = state ?? "idle";
  const bg = s === "failed" ? "#FF7878" : s === "done" ? "#4ADE80"
           : s === "active" ? "#FFC96B" : "var(--card)";
  return (
    <span aria-hidden style={{
      position: "absolute", top: 16, left: "50%", transform: "translateX(-50%)",
      width: 13, height: 13, borderRadius: 7, background: bg,
      border: s === "idle" ? "1.5px solid #C9D0E4" : "2px solid var(--card)",
      boxShadow: s === "idle" ? "none" : "0 0 0 3px rgba(255,255,255,.9)", zIndex: 2,
    }} />
  );
}

export default function StageTrace({ rows }: { rows: StageRow[] }) {
  const peak = Math.max(1, ...rows.map((r) => r.flowing ?? 0));

  return (
    <section>
      <div style={{ marginBottom: 14 }}>
        <div className="kicker">The run, stage by stage</div>
        <h2 className="display" style={{ fontSize: 22, fontWeight: 600, margin: "7px 0 5px" }}>
          What each stage refused, and which rule refused it
        </h2>
        <div style={{ fontSize: 13.5, color: "var(--muted)", maxWidth: "64ch", lineHeight: 1.5 }}>
          The band narrows as objects are dropped. Everything leaving it is written to
          the refusal ledger with the rule that decided, because what a brief leaves
          out is part of what it reports.
        </div>
      </div>

      <div style={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: "var(--radius)", overflow: "hidden" }}>
        {rows.map((row, i) => {
          const { stage } = row;
          const l = LAYER[stage.layer];
          const inW = halfWidth(i === 0 ? row.flowing : rows[i - 1].flowing ?? row.flowing, peak);
          const outW = halfWidth(row.flowing, peak);
          const dropped = row.refusals.reduce((a, r) => a + r.count, 0);

          return (
            <div key={stage.key} style={{
              display: "grid", gridTemplateColumns: `${RAIL}px 1fr`,
              borderTop: i === 0 ? "none" : "1px solid var(--line-soft)",
            }}>
              {/* the spine */}
              <div style={{ position: "relative", background: "#FBFCFE", borderRight: "1px solid var(--line-soft)" }}>
                <Spine inW={inW} outW={outW} fill={l.spine} line={l.fg}
                       first={i === 0} last={i === rows.length - 1} />
                <Dot state={row.state} />
                {typeof row.flowing === "number" && (
                  <span style={{
                    position: "absolute", bottom: 8, left: "50%", transform: "translateX(-50%)",
                    fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700, color: l.fg,
                    background: "rgba(255,255,255,.94)", borderRadius: 4, padding: "1px 5px",
                    border: `1px solid ${l.line}`,
                  }}>{row.flowing}</span>
                )}
              </div>

              {/* the stage */}
              <div style={{ padding: "13px 16px 15px", minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--ghost)" }}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="display" style={{ fontWeight: 600, fontSize: 15 }}>{stage.name}</span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, letterSpacing: .7, textTransform: "uppercase",
                    color: l.fg, background: l.bg, border: `1px solid ${l.line}`,
                    borderRadius: 5, padding: "2px 7px",
                  }}>{l.label}</span>
                  <span style={{ marginLeft: "auto", fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--ghost)" }}>
                    {stage.decidedIn}
                  </span>
                </div>

                <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 6, lineHeight: 1.5, maxWidth: "76ch" }}>
                  {stage.sub}
                </div>
                <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 6, lineHeight: 1.55, maxWidth: "76ch" }}>
                  {stage.refuses}
                </div>

                {dropped > 0 && (
                  <div style={{
                    marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center",
                  }}>
                    <span style={{
                      fontSize: 10.5, fontWeight: 700, letterSpacing: .7, textTransform: "uppercase",
                      color: "var(--amber-ink)",
                    }}>↳ refused {dropped}</span>
                    {row.refusals.map((r) => (
                      <span key={r.rule} title={r.sample ?? undefined} style={{
                        fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--amber-ink)",
                        background: "var(--amber-bg)", border: "1px solid var(--amber-line)",
                        borderRadius: 5, padding: "2px 7px",
                      }}>{r.rule} · {r.count}</span>
                    ))}
                  </div>
                )}

                {row.detail}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
