"use client";
import { useEffect, useRef, useState } from "react";

type Verdict = { ok: boolean; citations: string[]; unresolved: string[]; unsourced: string[]; gateViolations: string[] };
type Turn = { role: "user" | "assistant"; content: string; proposed?: string | null; edit_id?: string | null; verdict?: Verdict | null };

export default function ReportChat({ reportId, bodyMd }: { reportId: string; bodyMd: string }) {
  const [selection, setSelection] = useState("");
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [applied, setApplied] = useState<Record<string, string>>({});
  const bottom = useRef<HTMLDivElement>(null);

  // A selection inside the article opens the panel with that passage attached.
  useEffect(() => {
    const onUp = () => {
      const s = window.getSelection();
      const text = s?.toString().trim() ?? "";
      if (text.length < 12) return;
      const node = s?.anchorNode?.parentElement;
      if (!node?.closest("[data-report-body]")) return;
      setSelection(text);
      setOpen(true);
    };
    document.addEventListener("mouseup", onUp);
    return () => document.removeEventListener("mouseup", onUp);
  }, []);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, busy]);

  async function ask() {
    const question = q.trim();
    if (!question || busy) return;
    setQ(""); setBusy(true);
    setTurns(t => [...t, { role: "user", content: question }]);
    try {
      const r = await fetch("/api/report/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_id: reportId, selection, question }),
      });
      const d = await r.json();
      setTurns(t => [...t, {
        role: "assistant",
        content: d.error ?? d.answer ?? "No answer.",
        proposed: d.proposed, edit_id: d.edit_id, verdict: d.verdict,
      }]);
    } catch {
      setTurns(t => [...t, { role: "assistant", content: "The request failed." }]);
    } finally { setBusy(false); }
  }

  async function apply(editId: string, i: number) {
    setBusy(true);
    try {
      const r = await fetch("/api/report/apply", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ edit_id: editId }),
      });
      const d = await r.json();
      if (d.ok) { setApplied(a => ({ ...a, [editId]: "applied" })); location.reload(); }
      else setTurns(t => [...t, { role: "assistant", content: d.error ?? "Could not apply." }]);
    } finally { setBusy(false); }
  }

  if (!open) {
    return (
      <div style={{ position: "fixed", right: 22, bottom: 22, zIndex: 40 }}>
        <button className="pill-btn" onClick={() => setOpen(true)}>Discuss this report</button>
      </div>
    );
  }

  return (
    <aside style={{
      position: "fixed", top: 0, right: 0, bottom: 0, width: 420, zIndex: 50,
      background: "var(--card)", borderLeft: "1px solid var(--line)",
      display: "flex", flexDirection: "column", boxShadow: "-18px 0 44px rgba(18,22,46,.09)",
    }}>
      <div className="row" style={{ justifyContent: "space-between", padding: "14px 18px", borderBottom: "1px solid var(--line)" }}>
        <div>
          <div className="kicker">Discuss</div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>Ask about this passage</div>
        </div>
        <button onClick={() => setOpen(false)} aria-label="Close"
          style={{ border: 0, background: "none", fontSize: 20, color: "var(--muted)", cursor: "pointer" }}>×</button>
      </div>

      {selection && (
        <div style={{ padding: "12px 18px", borderBottom: "1px solid var(--line-soft)" }}>
          <div className="kicker" style={{ marginBottom: 6 }}>Highlighted</div>
          <div className="quote" style={{ fontSize: 12.5, maxHeight: 108, overflow: "auto" }}>{selection}</div>
          <button onClick={() => setSelection("")}
            style={{ marginTop: 8, border: 0, background: "none", color: "var(--accent)", fontSize: 11.5, cursor: "pointer", padding: 0 }}>
            Clear selection
          </button>
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
        {turns.length === 0 && (
          <div style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.6 }}>
            Highlight a passage in the report, then ask about it — why it says what it says,
            what evidence sits behind it, or how it should be rewritten. Answers come only
            from the graph, and a rewrite is checked before you can apply it.
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i}>
            <div className="kicker" style={{ marginBottom: 4 }}>{t.role === "user" ? "You" : "Analyst"}</div>
            <div style={{
              fontSize: 13.5, lineHeight: 1.62, whiteSpace: "pre-wrap",
              color: t.role === "user" ? "var(--ink)" : "var(--ink-2)",
              background: t.role === "user" ? "var(--accent-wash)" : "transparent",
              padding: t.role === "user" ? "9px 12px" : 0,
              borderRadius: t.role === "user" ? 10 : 0,
            }}>{t.content}</div>

            {t.proposed && (
              <div style={{
                marginTop: 10, border: `1px solid ${t.verdict?.ok ? "var(--green-line)" : "var(--amber-line)"}`,
                background: t.verdict?.ok ? "var(--green-bg)" : "var(--amber-bg)",
                borderRadius: 10, padding: 12,
              }}>
                <div className="kicker" style={{ marginBottom: 6 }}>
                  {t.verdict?.ok ? "Proposed rewrite · verified" : "Proposed rewrite · failed verification"}
                </div>
                <div style={{ fontSize: 12.5, lineHeight: 1.6, whiteSpace: "pre-wrap", color: "var(--ink-2)" }}>{t.proposed}</div>

                {t.verdict && !t.verdict.ok && (
                  <ul style={{ margin: "9px 0 0", paddingLeft: 16, fontSize: 11.5, color: "var(--amber-ink)" }}>
                    {t.verdict.unresolved.length > 0 && <li>Cites {t.verdict.unresolved.join(", ")} — no such row exists.</li>}
                    {t.verdict.unsourced.length > 0 && <li>{t.verdict.unsourced.length} sentence(s) assert a fact with no citation.</li>}
                    {t.verdict.gateViolations.length > 0 && <li>Contradicts an open validation gate.</li>}
                  </ul>
                )}

                {t.verdict?.ok && t.edit_id && !applied[t.edit_id] && (
                  <button className="pill-btn" style={{ marginTop: 10, fontSize: 12, padding: "7px 14px" }}
                    disabled={busy} onClick={() => apply(t.edit_id!, i)}>
                    Apply to the report
                  </button>
                )}
                {t.edit_id && applied[t.edit_id] && (
                  <div style={{ marginTop: 8, fontSize: 11.5, color: "var(--green-ink)" }}>Applied.</div>
                )}
              </div>
            )}
          </div>
        ))}
        {busy && <div style={{ fontSize: 12.5, color: "var(--faint)" }}>Working…</div>}
        <div ref={bottom} />
      </div>

      <div style={{ borderTop: "1px solid var(--line)", padding: 14, display: "flex", gap: 8 }}>
        <input
          value={q} onChange={e => setQ(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } }}
          placeholder={selection ? "Ask about the highlighted passage…" : "Ask about this report…"}
          style={{
            flex: 1, border: "1px solid var(--line)", borderRadius: 10, padding: "10px 12px",
            fontSize: 13, fontFamily: "inherit", background: "var(--paper)", color: "var(--ink)",
          }} />
        <button className="pill-btn" onClick={ask} disabled={busy || !q.trim()}
          style={{ fontSize: 12, padding: "9px 16px" }}>Ask</button>
      </div>
    </aside>
  );
}
