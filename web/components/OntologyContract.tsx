import { ONTOLOGY, LAYER, type ObjectType } from "@/lib/engine";

// The data model, drawn as what it is: a set of object types with an authority
// split running through every one of them.
//
// Most schema diagrams show boxes and arrows, which says nothing a table listing
// would not. The information worth showing here is WHO MAY WRITE EACH FIELD —
// the model proposes `claim`, and only rules.py may set `class`. That is the
// line the whole architecture rests on, so it is the line the diagram draws.

const COL: { title: string; note: string; keys: string[] }[] = [
  { title: "Retrieved", note: "bound to a publisher", keys: ["document", "figure"] },
  { title: "Claimed", note: "one span of evidence at a time", keys: ["evidence"] },
  { title: "Read across sources", note: "admitted only by rule", keys: ["signal", "trend"] },
  { title: "Interpreted", note: "what it means, and what it costs", keys: ["finding", "risk", "uncertainty"] },
  { title: "Projected", note: "carrying its own falsifier", keys: ["forecast", "gate"] },
];

function Field({ name, layer }: { name: string; layer: "NEURAL" | "SYMBOLIC" }) {
  const l = LAYER[layer];
  return (
    <span style={{
      fontFamily: "var(--mono)", fontSize: 10.5, lineHeight: 1.5, padding: "1.5px 6px",
      borderRadius: 5, color: l.fg, background: l.bg, border: `1px solid ${l.line}`,
      whiteSpace: "nowrap",
    }}>{name}</span>
  );
}

function Card({ o, count }: { o: ObjectType; count?: number }) {
  return (
    <div style={{
      background: "var(--card)", border: "1px solid var(--line)", borderRadius: 11,
      padding: "11px 12px 12px", display: "flex", flexDirection: "column", gap: 7,
    }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
        <span className="display" style={{ fontWeight: 600, fontSize: 13.5 }}>{o.name}</span>
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--faint)" }}>
          {typeof count === "number" ? count : "—"}
        </span>
      </div>
      <div style={{ fontSize: 11.5, lineHeight: 1.45, color: "var(--muted)" }}>{o.gloss}</div>
      {(o.neural.length > 0 || o.symbolic.length > 0) && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 1 }}>
          {o.neural.map((f) => <Field key={f} name={f} layer="NEURAL" />)}
          {o.symbolic.map((f) => <Field key={f} name={f} layer="SYMBOLIC" />)}
        </div>
      )}
    </div>
  );
}

export default function OntologyContract({ counts }: { counts: Record<string, number> }) {
  return (
    <section>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 20, flexWrap: "wrap", marginBottom: 14 }}>
        <div>
          <div className="kicker">The modelled layer</div>
          <h2 className="display" style={{ fontSize: 22, fontWeight: 600, margin: "7px 0 5px" }}>
            Every field has exactly one author
          </h2>
          <div style={{ fontSize: 13.5, color: "var(--muted)", maxWidth: "62ch", lineHeight: 1.5 }}>
            Objects are typed and linked, so a sentence in a brief can be walked back to the
            span it came from. The division below is what stops the model grading its own
            work: it may propose a claim, and it may never set that claim&rsquo;s class,
            confidence, signal strength or plausibility.
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {(["NEURAL", "SYMBOLIC"] as const).map((k) => (
            <div key={k} style={{
              maxWidth: 210, padding: "8px 11px", borderRadius: 10,
              background: LAYER[k].bg, border: `1px solid ${LAYER[k].line}`,
            }}>
              <div style={{ fontSize: 11.5, fontWeight: 700, color: LAYER[k].fg, letterSpacing: .2 }}>
                {LAYER[k].label}
              </div>
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 3, lineHeight: 1.4 }}>
                {LAYER[k].note}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Columns read left to right as the object's distance from the source. The
          arrow gutters carry the flow without a graph library. */}
      <div style={{ display: "flex", gap: 0, alignItems: "stretch", overflowX: "auto", paddingBottom: 4 }}>
        {COL.map((col, ci) => (
          <div key={col.title} style={{ display: "flex", alignItems: "stretch", flexShrink: 0 }}>
            {ci > 0 && (
              <div aria-hidden style={{
                width: 18, display: "flex", alignItems: "center", justifyContent: "center",
                color: "#C2C9DE", fontSize: 15,
              }}>→</div>
            )}
            <div style={{ width: 202, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ paddingLeft: 2 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.1, textTransform: "uppercase", color: "var(--faint)" }}>
                  {col.title}
                </div>
                <div style={{ fontSize: 11, color: "var(--ghost)", marginTop: 2 }}>{col.note}</div>
              </div>
              {col.keys.map((k) => {
                const o = ONTOLOGY.find((x) => x.key === k);
                return o ? <Card key={k} o={o} count={counts[o.table]} /> : null;
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
