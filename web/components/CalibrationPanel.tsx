import { BAND_COLOR, calibrationTerms } from "@/lib/engine";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Why a forecast carries the band it carries.
//
// A plausibility label on its own is indistinguishable from a guess, and asking
// a model for a percentage produces a confident number with nothing under it.
// So the band is arithmetic: corroboration breadth earns points, distance and
// unresolved questions cost them. The sum is stored on the row in `basis`,
// which means it can be shown rather than claimed — and a reader who disagrees
// with the band can see exactly which term to argue with.

export type ForecastRow = {
  id: string; statement: string; horizon: string;
  plausibility: string; falsifier: string | null;
  basis: Record<string, any> | null;
};

const HORIZON_LABEL: Record<string, string> = {
  H0_3: "0–3 years", H3_5: "3–5 years", H5_10: "5–10 years", H7_PLUS: "7+ years",
};

function Term({ label, value, note }: { label: string; value: number; note: string }) {
  return (
    <div className="flex items-baseline gap-2 text-sm">
      <span className={cn("min-w-[26px] text-right font-mono font-bold tabular-nums",
                          value < 0 ? "text-amber-ink" : "text-green-ink")}>
        {value < 0 ? value : `+${value}`}
      </span>
      <span className="min-w-[132px] text-ink-2">{label}</span>
      <span className="text-xs text-ghost">{note}</span>
    </div>
  );
}

export default function CalibrationPanel({ forecasts }: { forecasts: ForecastRow[] }) {
  if (!forecasts.length) {
    return (
      <p className="mt-3 text-sm text-muted">
        No admitted forecast for this pillar yet — every proposal was refused for having
        no admitted signal behind it.
      </p>
    );
  }

  return (
    <div className="mt-3 flex flex-col gap-2.5">
      {forecasts.map(f => {
        const terms = calibrationTerms(f.basis);
        const score = f.basis?.score;
        const c = BAND_COLOR[f.plausibility] ?? BAND_COLOR.SPECULATIVE;
        return (
          <div key={f.id} className="rounded-[10px] border border-line bg-[#FCFCFE] px-3 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-faint">{f.id}</span>
              <span className="text-xs text-muted">{HORIZON_LABEL[f.horizon] ?? f.horizon}</span>
              <span className="ml-auto flex items-center gap-[7px]">
                {typeof score === "number" && (
                  <span className="font-mono text-xs text-ghost">score {score}</span>
                )}
                <Badge className="tracking-[1px]"
                       style={{ color: c.fg, background: c.bg }}>{f.plausibility}</Badge>
              </span>
            </div>

            <p className="mt-[7px] max-w-[74ch] text-base text-ink">{f.statement}</p>

            {terms.length > 0 && (
              <div className="mt-2.5 flex flex-col gap-[3px] border-t border-dashed border-line pt-2.5">
                {terms.map(t => <Term key={t.label} {...t} />)}
                <div className="mt-[3px] flex items-baseline gap-2 border-t border-line-soft pt-1 text-sm">
                  <span className="min-w-[26px] text-right font-mono font-bold tabular-nums">
                    {score}
                  </span>
                  <span className="min-w-[132px] font-semibold text-ink-2">lands in</span>
                  <span className="text-xs font-bold tracking-wide" style={{ color: c.fg }}>
                    {f.plausibility}
                  </span>
                </div>
              </div>
            )}

            {f.falsifier && (
              <div className="quote mt-2.5 not-italic">
                <span className="mb-[3px] block text-2xs font-bold uppercase tracking-wide text-faint">
                  What would refute this
                </span>
                {f.falsifier}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
