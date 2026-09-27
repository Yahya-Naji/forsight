import { LAYER, type Stage } from "@/lib/engine";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionHead } from "@/components/ui/section";
import { cn } from "@/lib/utils";

// The pipeline drawn as attrition rather than as progress.
//
// A row of green ticks says the run finished, which is the least interesting
// thing about it. What a reader needs is how much was dropped and by which rule
// — 85 candidate images admitted 7, and a checklist shows that as one tick. So
// the spine's width encodes how many objects are still carried at each stage,
// and everything refused leaves it as a labelled chip.
//
// The taper is drawn in a normalised 0–100 viewBox with preserveAspectRatio
// switched off, so one SVG fills whatever height the band's prose needs. The
// layer colours stay inline because they are data from lib/engine, not classes.

export type StageRow = {
  stage: Stage;
  flowing: number | null;
  refusals: { rule: string; count: number; sample?: string }[];
  state?: "done" | "active" | "failed" | "idle";
  detail?: React.ReactNode;
};

const MAX_W = 46;   // spine half-width at its widest, in viewBox units

/** Square root, so an order-of-magnitude drop stays legible instead of vanishing. */
function halfWidth(n: number | null, peak: number) {
  if (!n || n <= 0 || peak <= 0) return 3;
  return Math.max(3, Math.sqrt(n / peak) * MAX_W);
}

function Dot({ state = "idle" }: { state?: StageRow["state"] }) {
  return (
    <span aria-hidden className={cn(
      "absolute left-1/2 top-4 z-[2] h-[13px] w-[13px] -translate-x-1/2 rounded-full",
      state === "idle"
        ? "border-[1.5px] border-[#C9D0E4] bg-card"
        : "border-2 border-card shadow-[0_0_0_3px_rgba(255,255,255,.9)]",
      state === "failed" && "bg-[#FF7878]",
      state === "done" && "bg-[#4ADE80]",
      state === "active" && "bg-[#FFC96B]")} />
  );
}

export default function StageTrace({ rows }: { rows: StageRow[] }) {
  const peak = Math.max(1, ...rows.map(r => r.flowing ?? 0));

  return (
    <section>
      <SectionHead kicker="The run, stage by stage"
                   title="What each stage refused, and which rule refused it">
        The band narrows as objects are dropped. Everything leaving it is written to the
        refusal ledger with the rule that decided, because what a brief leaves out is
        part of what it reports.
      </SectionHead>

      <Card className="overflow-hidden p-0">
        {rows.map((row, i) => {
          const { stage } = row;
          const l = LAYER[stage.layer];
          const inW = halfWidth(i === 0 ? row.flowing : rows[i - 1].flowing ?? row.flowing, peak);
          const outW = halfWidth(row.flowing, peak);
          const dropped = row.refusals.reduce((a, r) => a + r.count, 0);

          return (
            <div key={stage.key}
                 className={cn("grid grid-cols-[96px_1fr]", i > 0 && "border-t border-line-soft")}>
              <div className="relative border-r border-line-soft bg-[#FBFCFE]">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden
                     className="absolute inset-0 h-full w-full">
                  <polygon
                    points={`${50 - inW},0 ${50 + inW},0 ${50 + outW},100 ${50 - outW},100`}
                    fill={l.spine} fillOpacity="0.85"
                    stroke={l.fg} strokeWidth="0.5" strokeOpacity="0.45" />
                  {i === 0 && <line x1={50 - inW} y1="0" x2={50 + inW} y2="0"
                                    stroke={l.fg} strokeWidth="1.2" />}
                  {i === rows.length - 1 && <line x1={50 - outW} y1="100" x2={50 + outW} y2="100"
                                                  stroke={l.fg} strokeWidth="1.2" />}
                </svg>
                <Dot state={row.state} />
                {typeof row.flowing === "number" && (
                  <span className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded
                                   border bg-white/95 px-[5px] py-px font-mono text-xs font-bold"
                        style={{ color: l.fg, borderColor: l.line }}>
                    {row.flowing}
                  </span>
                )}
              </div>

              <div className="min-w-0 px-4 pb-[15px] pt-[13px]">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-mono text-2xs text-ghost">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="font-display text-[15px] font-semibold">{stage.name}</span>
                  <span className="rounded-[5px] border px-[7px] py-0.5 text-[10px]
                                   font-bold uppercase tracking-wide"
                        style={{ color: l.fg, background: l.bg, borderColor: l.line }}>
                    {l.label}
                  </span>
                  <span className="ml-auto font-mono text-2xs text-ghost">{stage.decidedIn}</span>
                </div>

                <p className="mt-1.5 max-w-[76ch] text-base text-ink-2">{stage.sub}</p>
                <p className="mt-1.5 max-w-[76ch] text-sm leading-relaxed text-muted">
                  {stage.refuses}
                </p>

                {dropped > 0 && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                    <span className="text-2xs font-bold uppercase tracking-wide text-amber-ink">
                      ↳ refused {dropped}
                    </span>
                    {row.refusals.map(r => (
                      <Badge key={r.rule} variant="classC" title={r.sample ?? undefined}
                             className="font-mono font-normal">
                        {r.rule} · {r.count}
                      </Badge>
                    ))}
                  </div>
                )}

                {row.detail}
              </div>
            </div>
          );
        })}
      </Card>
    </section>
  );
}
