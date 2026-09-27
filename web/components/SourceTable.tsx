"use client";
import { useState } from "react";
import { PILLAR_LABEL } from "./chips";

type Row = {
  id: string; publisher: string; url: string; method: string; tier: number;
  pillars: string[]; notes: string | null;
  docs: number; last: string | null;
  last_test_ok: boolean | null; last_test_note: string | null; last_tested_at: string | null;
  topics: string[];
};
type Result = { ok: boolean; status: number | null; note: string; ms: number; chars?: number };

const LANE: Record<string, { label: string; hint: string }> = {
  rss: { label: "Lane A", hint: "scheduled feed" },
  scrape: { label: "Lane A", hint: "scheduled scrape" },
  search: { label: "Lane B", hint: "question-driven search" },
  api: { label: "Lane C", hint: "structured API" },
};

export default function SourceTable({ rows }: { rows: Row[] }) {
  const [res, setRes] = useState<Record<string, Result | "running">>({});
  const [filter, setFilter] = useState<string>("");

  async function test(id: string) {
    setRes(r => ({ ...r, [id]: "running" }));
    try {
      const out = await fetch("/api/sources/test", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ registry_id: id }),
      }).then(r => r.json());
      setRes(r => ({ ...r, [id]: out }));
    } catch {
      setRes(r => ({ ...r, [id]: { ok: false, status: null, note: "Request failed", ms: 0 } }));
    }
  }

  async function testAll() {
    for (const r of shown) { await test(r.id); }
  }

  const shown = rows.filter(r =>
    !filter || r.method === filter || String(r.tier) === filter ||
    (filter === "untested" && !r.last_tested_at) ||
    (filter === "failing" && r.last_test_ok === false));

  return (
    <>
      <div className="row" style={{ gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        {[["", "All"], ["rss", "Feeds"], ["scrape", "Scrapes"], ["search", "Search"],
          ["api", "APIs"], ["1", "Tier 1"], ["failing", "Failing"], ["untested", "Untested"]].map(([v, l]) => (
          <button key={v} onClick={() => setFilter(v)} style={{
            fontSize: 12, fontWeight: 600, borderRadius: 999, padding: "6px 13px", cursor: "pointer",
            border: `1px solid ${filter === v ? "var(--navy)" : "var(--line)"}`,
            background: filter === v ? "var(--navy)" : "var(--card)",
            color: filter === v ? "#fff" : "var(--muted)",
          }}>{l}</button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="pill-btn" style={{ fontSize: 12, padding: "7px 14px" }} onClick={testAll}>
          Test all shown
        </button>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {shown.map((r, i) => {
          const t = res[r.id];
          const live = t && t !== "running" ? t : null;
          const ok = live ? live.ok : r.last_test_ok;
          const note = live ? live.note : r.last_test_note;
          return (
            <div key={r.id} style={{
              display: "grid", gridTemplateColumns: "minmax(0,1fr) 96px 92px 110px 108px",
              gap: 14, alignItems: "center", padding: "13px 16px",
              borderTop: i ? "1px solid var(--line-soft)" : 0,
            }}>
              <div style={{ minWidth: 0 }}>
                <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 13.5, fontWeight: 600 }}>{r.publisher}</span>
                  <span className={`chip ${r.tier === 1 ? "chip-tier1" : "chip-tier"}`}>TIER {r.tier}</span>
                  {r.topics.length > 0 && (
                    <span className="chip chip-tier">{r.topics.length} topic{r.topics.length > 1 ? "s" : ""}</span>
                  )}
                </div>
                <div style={{ fontSize: 11.5, color: "var(--faint)", marginTop: 3,
                              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {r.url.replace(/^https?:\/\//, "")}
                </div>
                {note && (
                  <div style={{ fontSize: 11.5, marginTop: 4,
                                color: ok ? "var(--green-ink)" : "var(--amber-ink)" }}>
                    {ok ? "✓" : "✕"} {note}{live ? ` · ${live.ms}ms` : ""}
                  </div>
                )}
              </div>

              <div>
                <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--accent-deep)" }}>
                  {LANE[r.method]?.label ?? r.method}
                </div>
                <div style={{ fontSize: 10.5, color: "var(--faint)" }}>{LANE[r.method]?.hint}</div>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 16, fontWeight: 700,
                              color: r.docs ? "var(--ink)" : "var(--faint)" }}>{r.docs}</div>
                <div style={{ fontSize: 10.5, color: "var(--faint)" }}>documents</div>
              </div>

              <div style={{ fontSize: 11.5, color: "var(--muted)", textAlign: "right" }}>
                {r.last ? new Date(r.last).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "never"}
              </div>

              <button onClick={() => test(r.id)} disabled={t === "running"} style={{
                fontSize: 11.5, fontWeight: 600, borderRadius: 999, padding: "7px 12px",
                cursor: t === "running" ? "wait" : "pointer",
                border: "1px solid var(--line)", background: "var(--paper)", color: "var(--ink-2)",
              }}>{t === "running" ? "Testing…" : "Test scrape"}</button>
            </div>
          );
        })}
        {shown.length === 0 && (
          <div style={{ padding: 20, fontSize: 13, color: "var(--muted)" }}>No sources match that filter.</div>
        )}
      </div>
    </>
  );
}
