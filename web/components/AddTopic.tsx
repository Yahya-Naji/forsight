"use client";
import { useState } from "react";

type Source = { id: string; publisher: string; tier: number; method: string; pillars: string[] };
type Step = "topic" | "sources" | "done";

// Two steps on purpose: a topic with no sources collects nothing, so the source
// binding is part of creating it rather than a setting somebody may forget.

export default function AddTopic({ pillar, pillarLabel, sources }: {
  pillar: string; pillarLabel: string; sources: Source[];
}) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("topic");
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [rel, setRel] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [made, setMade] = useState<{ id: string; sources: number } | null>(null);
  const [tests, setTests] = useState<Record<string, { ok: boolean; note: string } | "running">>({});

  // Sources already scoped to this pillar first — the rest stay available but
  // are unlikely to be what an analyst wants.
  const mine = sources.filter(s => s.pillars?.includes(pillar));
  const others = sources.filter(s => !s.pillars?.includes(pillar));

  function reset() {
    setOpen(false); setStep("topic"); setName(""); setDesc(""); setRel("");
    setPicked([]); setErr(null); setMade(null); setTests({});
  }

  async function test(id: string) {
    setTests(t => ({ ...t, [id]: "running" }));
    const r = await fetch("/api/sources/test", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ registry_id: id }),
    }).then(r => r.json()).catch(() => ({ ok: false, note: "Request failed" }));
    setTests(t => ({ ...t, [id]: { ok: !!r.ok, note: r.note ?? "" } }));
  }

  async function create() {
    setBusy(true); setErr(null);
    try {
      const r = await fetch("/api/topics", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pillar, name, description: desc, uae_relevance: rel, sources: picked }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(d.error ?? "Could not create the topic."); return; }
      setMade({ id: d.id, sources: d.sources }); setStep("done");
    } finally { setBusy(false); }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} style={{
        fontSize: 12, fontWeight: 600, borderRadius: 999, padding: "7px 14px", cursor: "pointer",
        border: "1px dashed var(--line)", background: "var(--card)", color: "var(--accent-deep)",
      }}>+ Add topic</button>
    );
  }

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(10,15,46,.42)",
                  display: "grid", placeItems: "center", padding: 20 }}
         onClick={e => { if (e.target === e.currentTarget) reset(); }}>
      <div className="card" style={{ width: "min(660px, 96vw)", maxHeight: "88vh", overflowY: "auto", padding: 24 }}>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
          <div>
            <div className="kicker">{pillarLabel}</div>
            <div className="display" style={{ fontWeight: 700, fontSize: 19 }}>
              {step === "topic" ? "New topic" : step === "sources" ? "Where should it read from?" : "Topic created"}
            </div>
          </div>
          <button onClick={reset} aria-label="Close" style={{
            border: 0, background: "none", fontSize: 22, color: "var(--muted)", cursor: "pointer" }}>×</button>
        </div>

        {step === "topic" && (
          <>
            <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55, marginBottom: 16 }}>
              A topic groups evidence inside a pillar and is what the extractor assigns each
              claim to. Name it for the question it answers, not the subject area.
            </p>
            <Field label="Name" required hint="e.g. “Supply-chain firmware exposure in defence systems”">
              <input value={name} onChange={e => setName(e.target.value)} style={inp} autoFocus />
            </Field>
            <Field label="Description" hint="What belongs in this topic and what does not.">
              <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={2} style={{ ...inp, resize: "vertical" }} />
            </Field>
            <Field label="UAE relevance" hint="Why this matters for the UAE specifically — used to judge whether global evidence transfers.">
              <textarea value={rel} onChange={e => setRel(e.target.value)} rows={2} style={{ ...inp, resize: "vertical" }} />
            </Field>
            <div className="row" style={{ justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
              <button onClick={reset} style={ghost}>Cancel</button>
              <button className="pill-btn" disabled={name.trim().length < 4}
                      onClick={() => setStep("sources")}
                      style={{ opacity: name.trim().length < 4 ? .5 : 1 }}>
                Choose sources →
              </button>
            </div>
          </>
        )}

        {step === "sources" && (
          <>
            <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55, marginBottom: 14 }}>
              Pick the sources expected to carry this topic. Test one to see what it returns
              right now — a source that has stopped answering is worth knowing about before
              it silently produces no evidence.
            </p>
            {[["This pillar", mine], ["Other pillars", others]].map(([title, list]: any) => (
              list.length > 0 && (
                <div key={title} style={{ marginBottom: 14 }}>
                  <div className="kicker" style={{ marginBottom: 7 }}>{title}</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                    {list.map((s: Source) => {
                      const on = picked.includes(s.id);
                      const t = tests[s.id];
                      return (
                        <div key={s.id} className="row" style={{
                          gap: 10, padding: "9px 11px", borderRadius: 9,
                          border: `1px solid ${on ? "var(--accent)" : "var(--line)"}`,
                          background: on ? "var(--accent-wash)" : "var(--card)",
                        }}>
                          <input type="checkbox" checked={on} onChange={() =>
                            setPicked(p => on ? p.filter(x => x !== s.id) : [...p, s.id])} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div className="row" style={{ gap: 7 }}>
                              <span style={{ fontSize: 13, fontWeight: 600 }}>{s.publisher}</span>
                              <span className={`chip ${s.tier === 1 ? "chip-tier1" : "chip-tier"}`}>T{s.tier}</span>
                            </div>
                            {t && t !== "running" && (
                              <div style={{ fontSize: 11, marginTop: 3,
                                            color: t.ok ? "var(--green-ink)" : "var(--amber-ink)" }}>
                                {t.ok ? "✓" : "✕"} {t.note}
                              </div>
                            )}
                          </div>
                          <button onClick={() => test(s.id)} disabled={t === "running"} style={{
                            ...ghost, fontSize: 11, padding: "5px 10px" }}>
                            {t === "running" ? "…" : "Test"}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )
            ))}
            {err && <div style={{ fontSize: 12.5, color: "var(--amber-ink)", marginBottom: 10 }}>{err}</div>}
            <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
              <button onClick={() => setStep("topic")} style={ghost}>← Back</button>
              <div className="row" style={{ gap: 10 }}>
                <span style={{ fontSize: 12, color: "var(--muted)", alignSelf: "center" }}>
                  {picked.length} selected
                </span>
                <button className="pill-btn" onClick={create} disabled={busy}>
                  {busy ? "Creating…" : "Create topic"}
                </button>
              </div>
            </div>
          </>
        )}

        {step === "done" && made && (
          <>
            <p style={{ fontSize: 13.5, lineHeight: 1.6, color: "var(--ink-2)", marginTop: 10 }}>
              <b>{made.id}</b> created with {made.sources} source{made.sources === 1 ? "" : "s"} bound to it.
            </p>
            <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55, marginTop: 8 }}>
              Evidence appears against this topic once collection and extraction next run —
              the extractor assigns each claim to one of the pillar&rsquo;s topics.
            </p>
            <div className="row" style={{ justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
              <button className="pill-btn" onClick={() => location.reload()}>Done</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const inp: React.CSSProperties = {
  width: "100%", border: "1px solid var(--line)", borderRadius: 9, padding: "9px 11px",
  fontSize: 13.5, fontFamily: "inherit", background: "var(--paper)", color: "var(--ink)",
};
const ghost: React.CSSProperties = {
  fontSize: 12.5, fontWeight: 600, borderRadius: 999, padding: "8px 14px", cursor: "pointer",
  border: "1px solid var(--line)", background: "var(--card)", color: "var(--muted)",
};

function Field({ label, hint, required, children }: any) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div className="row" style={{ gap: 6, marginBottom: 5 }}>
        <span style={{ fontSize: 12, fontWeight: 600 }}>{label}</span>
        {required && <span style={{ fontSize: 10.5, color: "var(--accent-deep)" }}>required</span>}
      </div>
      {children}
      {hint && <div style={{ fontSize: 11, color: "var(--faint)", marginTop: 4, lineHeight: 1.45 }}>{hint}</div>}
    </div>
  );
}
