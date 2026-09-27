import Link from "next/link";

// The audit, measured against the human-written report it is trying to beat.
//
// Absolute numbers here would be unreadable — "0 unsourced assertions" is only
// meaningful next to what the comparison document does on the same measure. So
// each metric is shown as a pair, and the losing side is not hidden: findings
// recall against the benchmark is low, and that belongs on this page as much as
// the citation density does.

type Text = {
  words: number; sentences: number; unsourced: number;
  unsourced_rate: number; cited_sentences: number; citations_per_1k_words: number;
};

function Pair({ label, ours, theirs, unit, betterIsLow }: {
  label: string; ours: number; theirs: number; unit?: string; betterIsLow: boolean;
}) {
  const win = betterIsLow ? ours <= theirs : ours >= theirs;
  return (
    <div style={{ border: "1px solid var(--line)", borderRadius: 10, padding: "10px 13px", background: "#FCFCFE", minWidth: 172 }}>
      <div style={{ fontSize: 10.5, letterSpacing: .6, textTransform: "uppercase", color: "var(--faint)", fontWeight: 700 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 6 }}>
        <span style={{
          fontFamily: "var(--mono)", fontSize: 19, fontWeight: 700,
          fontVariantNumeric: "tabular-nums",
          color: win ? "var(--green-ink)" : "var(--amber-ink)",
        }}>{ours}{unit}</span>
        <span style={{ fontSize: 11.5, color: "var(--ghost)" }}>vs</span>
        <span style={{
          fontFamily: "var(--mono)", fontSize: 14, fontVariantNumeric: "tabular-nums",
          color: "var(--muted)",
        }}>{theirs}{unit}</span>
      </div>
      <div style={{ fontSize: 10.5, color: "var(--ghost)", marginTop: 3 }}>ours · the human report</div>
    </div>
  );
}

export default function ScorecardStrip({ card }: { card: any }) {
  const ours = card.ours_text as Text | null;
  const theirs = card.benchmark_text as Text | null;
  const chain = card.chain_completeness as { rate: number; complete: number; findings: number } | null;
  const recall = (card.recall ?? {}) as Record<string, { in_scope: number; in_scope_matched: number }>;

  return (
    <div style={{ marginTop: 13 }}>
      {card.benchmark_label && (
        <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>
          Scored against{" "}
          <span style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--ink-2)" }}>
            {card.benchmark_label}
          </span>{" "}
          — the human-written report this system exists to beat.
        </div>
      )}

      {ours && theirs && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Pair label="unsourced assertions" ours={ours.unsourced} theirs={theirs.unsourced} betterIsLow />
          <Pair label="citations / 1k words" ours={ours.citations_per_1k_words} theirs={theirs.citations_per_1k_words} betterIsLow={false} />
          <Pair label="sentences cited" ours={ours.cited_sentences} theirs={theirs.cited_sentences} betterIsLow={false} />
          {chain && (
            <div style={{ border: "1px solid var(--line)", borderRadius: 10, padding: "10px 13px", background: "#FCFCFE", minWidth: 172 }}>
              <div style={{ fontSize: 10.5, letterSpacing: .6, textTransform: "uppercase", color: "var(--faint)", fontWeight: 700 }}>
                chain completeness
              </div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 19, fontWeight: 700, marginTop: 6, color: "var(--green-ink)" }}>
                {Math.round(chain.rate * 100)}%
              </div>
              <div style={{ fontSize: 10.5, color: "var(--ghost)", marginTop: 3 }}>
                findings tracing to evidence
              </div>
            </div>
          )}
        </div>
      )}

      {/* The unflattering half. Recall against the benchmark is where this system
          is weakest, and hiding it would make every number above less credible. */}
      {Object.keys(recall).length > 0 && (
        <div style={{ marginTop: 10, fontSize: 12, color: "var(--muted)", lineHeight: 1.6 }}>
          <span style={{ fontWeight: 600, color: "var(--ink-2)" }}>Where it is behind: </span>
          of the benchmark&rsquo;s in-scope items, this run matched{" "}
          {Object.entries(recall)
            .map(([k, v]) => `${v.in_scope_matched}/${v.in_scope} ${k}`)
            .join(" · ")}
          . Recall is the open weakness — the pipeline is stricter than the human
          author, and strictness costs coverage.{" "}
          <Link href="/scorecard" style={{ fontSize: 12 }}>Full scorecard →</Link>
        </div>
      )}
    </div>
  );
}
