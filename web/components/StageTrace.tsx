import { LAYER, type Stage } from "@/lib/engine";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionHead } from "@/components/ui/section";
import { cn } from "@/lib/utils";

// The pipeline as a list, with the attrition stated rather than drawn.
//
// This carried a tapering funnel for three revisions. The geometry was correct
// — symmetric about the centre, equal counts at equal widths — and it still
// read wrong at every size, because the width change across a tall band is a
// slope too shallow to see, and the eye reports the straighter side as the
// truth. A picture that needs explaining is not doing the job of a picture.
//
// So the drop is a number now: 132 carried, then 63 with a -69 beside it. That
// is the same fact the funnel was trying to convey, it is exact rather than
// suggestive, and it survives any band height. The rail keeps only what it was
// always good at — marking where each stage sits and how far a run has reached.

export type StageRow = {
  stage: Stage;
  flowing: number | null;
  refusals: { rule: string; count: number; sample?: string }[];
  state?: "done" | "active" | "failed" | "idle";
  detail?: React.ReactNode;
};

function Dot({ state = "idle" }: { state?: StageRow["state"] }) {
  return (
    <span aria-hidden className={cn(
      "relative z-[2] h-[13px] w-[13px] shrink-0 rounded-full",
      state === "idle"
        ? "border-[1.5px] border-[#C9D0E4] bg-card"
        : "border-2 border-card shadow-[0_0_0_3px_rgba(255,255,255,.9)]",
      state === "failed" && "bg-[#FF7878]",
      state === "done" && "bg-[#4ADE80]",
      state === "active" && "bg-[#FFC96B]")} />
  );
}

export default function StageTrace({ rows }: { rows: StageRow[] }) {

  return (
    <section>
      <SectionHead kicker="The run, stage by stage"
                   title="What each stage refused, and which rule refused it">
        Each stage shows what it carried forward and, beside it, how many objects it
        dropped. Everything that left is written to the refusal ledger with the rule
        that decided, because what a brief leaves out is part of what it reports.
      </SectionHead>

      <Card className="overflow-hidden p-0">
        {rows.map((row, i) => {
          const { stage } = row;
          const l = LAYER[stage.layer];
          const prev = i > 0 ? rows[i - 1].flowing : null;
          const drop = (prev != null && row.flowing != null && prev > row.flowing)
            ? prev - row.flowing : 0;
          const dropped = row.refusals.reduce((a, r) => a + r.count, 0);

          return (
            <div key={stage.key} className="grid grid-cols-[104px_1fr]">
              <div className="relative flex flex-col items-center border-r border-line-soft
                              bg-[#FBFCFE] px-2 pt-[15px]">
                {/* one continuous line through every stage, so the rail reads as
                    a single run rather than a column of unrelated markers */}
                <span aria-hidden className={cn("absolute left-1/2 w-px -translate-x-1/2 bg-line",
                  i === 0 ? "top-[22px] bottom-0" : i === rows.length - 1 ? "top-0 h-[22px]" : "inset-y-0")} />
                <Dot state={row.state} />
                {typeof row.flowing === "number" && (
                  <span className="relative mt-[22px] flex flex-col items-center gap-0.5">
                    <span className="rounded border bg-card px-[6px] py-px font-mono text-xs
                                     font-bold tabular-nums"
                          style={{ color: l.fg, borderColor: l.line }}>
                      {row.flowing}
                    </span>
                    {drop > 0 && (
                      <span className="font-mono text-2xs tabular-nums text-amber-ink">
                        −{drop}
                      </span>
                    )}
                  </span>
                )}
              </div>

              <div className={cn("min-w-0 px-4 pb-[15px] pt-[13px]",
                                 i > 0 && "border-t border-line-soft")}>
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
