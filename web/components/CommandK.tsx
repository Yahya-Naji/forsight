"use client";
import { useEffect, useRef, useState } from "react";
import EvidenceCard, { Evidence } from "./EvidenceCard";

type Answer = { text: string; evidence: Evidence[]; gates: { id: string; blocks: string }[] };

export default function CommandK() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen(v => !v); }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);

  async function ask() {
    if (!q.trim() || busy) return;
    setBusy(true); setAnswer(null);
    try {
      const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) });
      setAnswer(await r.json());
    } catch { setAnswer({ text: "The graph could not be reached.", evidence: [], gates: [] }); }
    setBusy(false);
  }

  if (!open) return null;
  return (
    <div onClick={() => setOpen(false)} style={{ position: "fixed", inset: 0, background: "rgba(14,19,48,.35)", zIndex: 50, display: "flex", justifyContent: "center" }}>
      <div onClick={e => e.stopPropagation()} style={{ marginTop: 110, width: 740, maxWidth: "92vw", height: "fit-content", maxHeight: "72vh", overflowY: "auto", background: "#fff", borderRadius: 20, boxShadow: "0 30px 80px rgba(10,15,46,.35)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "18px 22px", borderBottom: "1px solid var(--line-soft)" }}>
          <span style={{ width: 8, height: 8, borderRadius: 4, background: "var(--accent)", flexShrink: 0 }} />
          <input ref={inputRef} value={q} onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key === "Enter" && ask()}
            placeholder="Ask the graph — answers come only from stored evidence"
            aria-label="Ask the graph"
            style={{ flexGrow: 1, border: "none", outline: "none", fontFamily: "inherit", fontSize: 16, background: "transparent", color: "var(--ink)" }} />
          <span style={{ fontSize: 11, color: "var(--ghost)", background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 6, padding: "3px 8px" }}>esc</span>
        </div>
        <div style={{ padding: "20px 22px", display: "flex", flexDirection: "column", gap: 14 }}>
          {busy && <div style={{ fontSize: 13, color: "var(--faint)" }}>Querying the knowledge graph…</div>}
          {answer && (
            <>
              <div style={{ fontSize: 14, color: "var(--ink-2)", lineHeight: 1.65, whiteSpace: "pre-wrap" }}>{answer.text}</div>
              {answer.evidence.map(ev => <EvidenceCard key={ev.id} ev={ev} compact />)}
              {answer.gates.map(g => (
                <div key={g.id} style={{ display: "flex", gap: 10, alignItems: "flex-start", background: "var(--amber-bg)", border: "1px solid var(--amber-line)", borderRadius: 12, padding: "13px 15px" }}>
                  <span className="chip chip-open" style={{ flexShrink: 0, marginTop: 1 }}>{g.id} · OPEN</span>
                  <div style={{ fontSize: 12.5, color: "#4A4633", lineHeight: 1.55 }}>{g.blocks}</div>
                </div>
              ))}
            </>
          )}
          <div style={{ fontSize: 12, color: "var(--ghost)", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 6, height: 6, borderRadius: 3, background: "#4ADE80" }} />
            Answers come only from the knowledge graph. Nothing is generated from model memory.
          </div>
        </div>
      </div>
    </div>
  );
}
