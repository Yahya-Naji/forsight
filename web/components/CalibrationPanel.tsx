import { BAND_COLOR, calibrationTerms } from "@/lib/engine";

// Why a forecast carries the band it carries.
//
// A plausibility label on its own is indistinguishable from a guess, and asking a
// model for a percentage produces a confident number with nothing under it. So
// the band is arithmetic: corroboration breadth earns points, distance and
// unresolved questions cost them, and the total lands in a band. The sum is
// stored on the row in `basis`, which means it can be shown rather than claimed —
// and a reader who disagrees with the band can see exactly which term to argue
// with.

export type ForecastRow = {
  id: string;
  statement: string;
  horizon: string;
  plausibility: string;
  falsifier: string | null;
  basis: Record<string, any> | null;
};

const HORIZON_LABEL: Record<string, string> = {
  H0_3: "0–3 years", H3_5: "3–5 years", H5_10: "5–10 years", H7_PLUS: "7+ years",
};

function Term({ label, value, note }: { label: string; value: number; note: string }) {
  const neg = value < 0;
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 8, fontSize: 12 }}>
      <span style={{
        fontFamily: "var(--mono)", fontWeight: 700, minWidth: 26, textAlign: "right",
        color: neg ? "var(--amber-ink)" : "var(--green-ink)",
      }}>{neg ? value : `+${value}`}</span>
      <span style={{ color: "var(--ink-2)", minWidth: 132 }}>{label}</span>
      <span style={{ color: "var(--ghost)", fontSize: 11.5 }}>{note}</span>
    </div>
  );
}

export default function CalibrationPanel({ forecasts }: { forecasts: ForecastRow[] }) {
  if (forecasts.length === 0) {
    return (
      <div style={{ marginTop: 12, fontSize: 12.5, color: "var(--muted)" }}>
        No admitted forecast for this pillar yet — every proposal was refused for having
        no admitted signal behind it.
      </div>
    );
  }

  return (
    <div style={{ marginTop: 13, display: "flex", flexDirection: "column", gap: 9 }}>
      {forecasts.map((f) => {
        const terms = calibrationTerms(f.basis);
        const score = f.basis?.score;
        const c = BAND_COLOR[f.plausibility] ?? BAND_COLOR.SPECULATIVE;
        return (
          <div key={f.id} style={{
            border: "1px solid var(--line)", borderRadius: 10, padding: "11px 13px",
            background: "#FCFCFE",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--faint)" }}>{f.id}</span>
              <span style={{ fontSize: 11.5, color: "var(--muted)" }}>{HORIZON_LABEL[f.horizon] ?? f.horizon}</span>
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 7 }}>
                {typeof score === "number" && (
                  <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ghost)" }}>
                    score {score}
                  </span>
                )}
                <span className="chip" style={{ color: c.fg, background: c.bg, letterSpacing: 1 }}>
                  {f.plausibility}
                </span>
              </span>
            </div>

            <div style={{ fontSize: 13, color: "var(--ink)", marginTop: 7, lineHeight: 1.5, maxWidth: "74ch" }}>
              {f.statement}
            </div>

            {terms.length > 0 && (
              <div style={{
                marginTop: 9, paddingTop: 9, borderTop: "1px dashed var(--line)",
                display: "flex", flexDirection: "column", gap: 3,
              }}>
                {terms.map((t) => <Term key={t.label} {...t} />)}
                <div style={{
                  display: "flex", alignItems: "baseline", gap: 8, fontSize: 12,
                  marginTop: 3, paddingTop: 4, borderTop: "1px solid var(--line-soft)",
                }}>
                  <span style={{ fontFamily: "var(--mono)", fontWeight: 700, minWidth: 26, textAlign: "right" }}>
                    {score}
                  </span>
                  <span style={{ color: "var(--ink-2)", minWidth: 132, fontWeight: 600 }}>lands in</span>
                  <span style={{ color: c.fg, fontWeight: 700, fontSize: 11.5, letterSpacing: .6 }}>
                    {f.plausibility}
                  </span>
                </div>
              </div>
            )}

            {f.falsifier && (
              <div className="quote" style={{ marginTop: 9, fontStyle: "normal" }}>
                <span style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: .8, textTransform: "uppercase",
                  color: "var(--faint)", display: "block", marginBottom: 3,
                }}>What would refute this</span>
                {f.falsifier}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
