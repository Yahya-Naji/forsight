"use client";
import { useEffect, useRef, useState } from "react";
import { PILLAR_LABEL, label } from "./chips";

type Brief = {
  id: string; title: string | null; goal: string | null; decision: string | null;
  audience: string | null; pillars: string[]; horizon: string | null;
  focus_terms: string[]; in_scope: string | null; out_of_scope: string | null; depth: string;
};
type Turn = { role: "user" | "assistant"; content: string };

const OPENERS = [
  "A cyber threat baseline for the UAE",
  "How procurement should change as technology cycles shorten",
  "What AI autonomy means for our decision timelines",
];

export default function BriefChat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [briefId, setBriefId] = useState<string | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [ready, setReady] = useState(false);
  const [queued, setQueued] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, busy, ready]);

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setQ(""); setBusy(true);
    setTurns(t => [...t, { role: "user", content: text }]);
    try {
      const d = await fetch("/api/brief", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief_id: briefId, message: text }),
      }).then(r => r.json());
      if (d.error) { setTurns(t => [...t, { role: "assistant", content: d.error }]); return; }
      setBriefId(d.brief_id); setBrief(d.brief); setReady(!!d.ready);
      setTurns(t => [...t, { role: "assistant", content: d.reply }]);
    } catch {
      setTurns(t => [...t, { role: "assistant", content: "That request failed." }]);
    } finally { setBusy(false); }
  }

  async function run() {
    if (!briefId) return;
    setBusy(true);
    try {
      const body = new URLSearchParams({
        pillar: brief?.pillars?.[0] ?? "CYBERSECURITY",
        brief_id: briefId,
        template: "TPL-DECISION-01",
        title: brief?.title ?? "Strategic brief",
      });
      const r = await fetch("/api/generate", { method: "POST", body });
      setQueued(r.url.includes("run=") ? new URL(r.url).searchParams.get("run") : "queued");
    } finally { setBusy(false); }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 330px", gap: 20, alignItems: "start" }}>
      {/* ── the interview ── */}
      <div className="card" style={{ padding: 0, display: "flex", flexDirection: "column", height: "calc(100vh - 190px)", minHeight: 460 }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)" }}>
          <div className="kicker">New report</div>
          <div className="display" style={{ fontWeight: 700, fontSize: 18 }}>Tell me what you need</div>
          <p style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 5, lineHeight: 1.5 }}>
            Describe the report you want. I&rsquo;ll ask a few questions until I know what decision
            it has to support, then write it from the evidence graph.
          </p>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          {turns.length === 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ fontSize: 12.5, color: "var(--muted)" }}>For example:</div>
              {OPENERS.map(o => (
                <button key={o} onClick={() => send(o)} style={{
                  textAlign: "left", fontSize: 13, padding: "11px 14px", borderRadius: 10,
                  border: "1px solid var(--line)", background: "var(--paper)",
                  color: "var(--ink-2)", cursor: "pointer",
                }}>{o}</button>
              ))}
            </div>
          )}

          {turns.map((t, i) => (
            <div key={i}>
              <div className="kicker" style={{ marginBottom: 4 }}>{t.role === "user" ? "You" : "Analyst"}</div>
              <div style={{
                fontSize: 13.5, lineHeight: 1.65, whiteSpace: "pre-wrap",
                color: t.role === "user" ? "var(--ink)" : "var(--ink-2)",
                background: t.role === "user" ? "var(--accent-wash)" : "transparent",
                padding: t.role === "user" ? "10px 13px" : 0,
                borderRadius: t.role === "user" ? 10 : 0,
              }}>{t.content}</div>
            </div>
          ))}
          {busy && <div style={{ fontSize: 12.5, color: "var(--faint)" }}>Thinking…</div>}
          <div ref={bottom} />
        </div>

        <div style={{ borderTop: "1px solid var(--line)", padding: 14, display: "flex", gap: 8 }}>
          <input value={q} onChange={e => setQ(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(q); } }}
            placeholder="What should this report answer?" style={{
              flex: 1, border: "1px solid var(--line)", borderRadius: 10, padding: "11px 13px",
              fontSize: 13.5, fontFamily: "inherit", background: "var(--paper)", color: "var(--ink)",
            }} />
          <button className="pill-btn" onClick={() => send(q)} disabled={busy || !q.trim()}>Send</button>
        </div>
      </div>

      {/* ── the brief as it forms ── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="card" style={{ padding: 18 }}>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
            <span className="section-title" style={{ fontSize: 14 }}>The brief</span>
            <span className={`chip ${ready ? "chip-passed" : "chip-tier"}`}>
              {ready ? "Ready" : "Taking shape"}
            </span>
          </div>

          {!brief?.goal ? (
            <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55 }}>
              Fills in as we talk. Nothing is written until the brief says what decision
              the report supports — without that, a report is only a summary.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
              <F k="Question" v={brief.goal} />
              <F k="Decision it supports" v={brief.decision} />
              <F k="Audience" v={brief.audience} />
              <F k="Pillars" v={(brief.pillars ?? []).map(p => PILLAR_LABEL[p] ?? p).join(", ")} />
              {brief.horizon && <F k="Horizon" v={label(brief.horizon).replace("H", "").replace("_", "–") + " years"} />}
              <F k="Out of scope" v={brief.out_of_scope} />
              {brief.focus_terms?.length > 0 && (
                <div>
                  <div className="kicker" style={{ marginBottom: 5 }}>Scoping terms</div>
                  <div className="row" style={{ gap: 5, flexWrap: "wrap" }}>
                    {brief.focus_terms.map(t => <span key={t} className="chip chip-tier">{t}</span>)}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--faint)", marginTop: 6, lineHeight: 1.45 }}>
                    Evidence not matching these is withheld from the writer and counted in the ledger.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {ready && !queued && (
          <div className="card" style={{ padding: 18 }}>
            <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55, marginBottom: 12 }}>
              Written in decision-brief structure: the answer first, findings as conclusions
              rather than headings, and a closing section on what could not be established.
            </p>
            <button className="pill-btn" style={{ width: "100%" }} onClick={run} disabled={busy}>
              {busy ? "Queueing…" : "Write this report"}
            </button>
          </div>
        )}

        {queued && (
          <div className="card" style={{ padding: 18, borderLeft: "3px solid var(--accent)" }}>
            <div className="section-title" style={{ fontSize: 14, marginBottom: 6 }}>Queued</div>
            <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55 }}>
              The pipeline picks this up from the repo or the scheduled action. Progress appears
              on this page as each stage reports in — no stage is marked until it actually runs.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function F({ k, v }: { k: string; v: string | null }) {
  if (!v) return null;
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 3 }}>{k}</div>
      <div style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.5 }}>{v}</div>
    </div>
  );
}
