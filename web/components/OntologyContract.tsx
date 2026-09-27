import { ONTOLOGY, LAYER, type ObjectType } from "@/lib/engine";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionHead } from "@/components/ui/section";

// The data model, drawn as what it is: a set of object types with an authority
// split running through every one of them.
//
// Most schema diagrams show boxes and arrows, which says nothing a table
// listing would not. The information worth showing is WHO MAY WRITE EACH FIELD
// — the model proposes `claim`, and only rules.py may set `class`. That is the
// line the architecture rests on, so it is the line the diagram draws.

const COL: { title: string; note: string; keys: string[] }[] = [
  { title: "Retrieved", note: "bound to a publisher", keys: ["document", "figure"] },
  { title: "Claimed", note: "one span of evidence at a time", keys: ["evidence"] },
  { title: "Read across sources", note: "admitted only by rule", keys: ["signal", "trend"] },
  { title: "Interpreted", note: "what it means, and what it costs",
    keys: ["finding", "risk", "uncertainty"] },
  { title: "Projected", note: "carrying its own falsifier", keys: ["forecast", "gate"] },
];

function ObjectCard({ o, count }: { o: ObjectType; count?: number }) {
  return (
    <Card className="flex flex-col gap-[7px] rounded-[11px] px-3 pb-3 pt-[11px]">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-display text-[13.5px] font-semibold">{o.name}</span>
        <span className="font-mono text-xs text-faint">
          {typeof count === "number" ? count : "—"}
        </span>
      </div>
      <p className="text-xs leading-snug text-muted">{o.gloss}</p>
      {(o.neural.length > 0 || o.symbolic.length > 0) && (
        <div className="flex flex-wrap gap-1">
          {o.neural.map(f => <Badge key={f} variant="neural">{f}</Badge>)}
          {o.symbolic.map(f => <Badge key={f} variant="symbolic">{f}</Badge>)}
        </div>
      )}
    </Card>
  );
}

export default function OntologyContract({ counts }: { counts: Record<string, number> }) {
  return (
    <section>
      <div className="mb-3.5 flex flex-wrap items-end justify-between gap-5">
        <SectionHead kicker="The modelled layer" title="Every field has exactly one author">
          Objects are typed and linked, so a sentence in a brief can be walked back to the
          span it came from. The division below is what stops the model grading its own
          work: it may propose a claim, and it may never set that claim&rsquo;s class,
          confidence, signal strength or plausibility.
        </SectionHead>
        <div className="flex gap-2">
          {(["NEURAL", "SYMBOLIC"] as const).map(k => (
            <div key={k} className="max-w-[210px] rounded-[10px] border px-[11px] py-2"
                 style={{ background: LAYER[k].bg, borderColor: LAYER[k].line }}>
              <div className="text-xs font-bold" style={{ color: LAYER[k].fg }}>
                {LAYER[k].label}
              </div>
              <p className="mt-[3px] text-2xs leading-snug text-muted">{LAYER[k].note}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Left to right is the object's distance from the source. */}
      <div className="flex items-stretch overflow-x-auto pb-1">
        {COL.map((col, ci) => (
          <div key={col.title} className="flex shrink-0 items-stretch">
            {ci > 0 && (
              <div aria-hidden className="flex w-[18px] items-center justify-center
                                          text-[15px] text-[#C2C9DE]">→</div>
            )}
            <div className="flex w-[202px] flex-col gap-2">
              <div className="pl-0.5">
                <div className="text-2xs font-bold uppercase tracking-[1.1px] text-faint">
                  {col.title}
                </div>
                <div className="mt-0.5 text-2xs text-ghost">{col.note}</div>
              </div>
              {col.keys.map(k => {
                const o = ONTOLOGY.find(x => x.key === k);
                return o ? <ObjectCard key={k} o={o} count={counts[o.table]} /> : null;
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
