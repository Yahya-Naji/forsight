import Link from "next/link";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

// The audit, measured against the human-written report it is trying to beat.
//
// Absolute numbers would be unreadable — "0 unsourced assertions" is only
// meaningful next to what the comparison document does on the same measure. So
// each metric is a pair, and the losing side is not hidden: findings recall
// against the benchmark is low, and that belongs on this page as much as the
// citation density does.

type Text = {
  words: number; sentences: number; unsourced: number; unsourced_rate: number;
  cited_sentences: number; citations_per_1k_words: number;
};

function Pair({ label, ours, theirs, betterIsLow }: {
  label: string; ours: number; theirs: number; betterIsLow: boolean;
}) {
  const win = betterIsLow ? ours <= theirs : ours >= theirs;
  return (
    <div className="min-w-[172px] rounded-[10px] border border-line bg-[#FCFCFE] px-3 py-2.5">
      <div className="text-2xs font-bold uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className={cn("font-mono text-[19px] font-bold tabular-nums",
                            win ? "text-green-ink" : "text-amber-ink")}>{ours}</span>
        <span className="text-xs text-ghost">vs</span>
        <span className="font-mono tabular-nums text-muted">{theirs}</span>
      </div>
      <div className="mt-[3px] text-2xs text-ghost">ours · the human report</div>
    </div>
  );
}

export default function ScorecardStrip({ card }: { card: any }) {
  const ours = card.ours_text as Text | null;
  const theirs = card.benchmark_text as Text | null;
  const chain = card.chain_completeness as { rate: number } | null;
  const recall = (card.recall ?? {}) as
    Record<string, { in_scope: number; in_scope_matched: number }>;

  return (
    <div className="mt-3">
      {card.benchmark_label && (
        <p className="mb-2 text-sm text-muted">
          Scored against <Badge variant="mono">{card.benchmark_label}</Badge> — the
          human-written report this system exists to beat.
        </p>
      )}

      {ours && theirs && (
        <div className="flex flex-wrap gap-2">
          <Pair label="unsourced assertions" ours={ours.unsourced} theirs={theirs.unsourced} betterIsLow />
          <Pair label="citations / 1k words" ours={ours.citations_per_1k_words}
                theirs={theirs.citations_per_1k_words} betterIsLow={false} />
          <Pair label="sentences cited" ours={ours.cited_sentences}
                theirs={theirs.cited_sentences} betterIsLow={false} />
          {chain && (
            <div className="min-w-[172px] rounded-[10px] border border-line bg-[#FCFCFE] px-3 py-2.5">
              <div className="text-2xs font-bold uppercase tracking-wide text-faint">
                chain completeness
              </div>
              <div className="mt-1.5 font-mono text-[19px] font-bold text-green-ink">
                {Math.round(chain.rate * 100)}%
              </div>
              <div className="mt-[3px] text-2xs text-ghost">findings tracing to evidence</div>
            </div>
          )}
        </div>
      )}

      {/* The unflattering half. Recall is where this system is weakest, and
          hiding it would make every number above less credible. */}
      {Object.keys(recall).length > 0 && (
        <p className="mt-2.5 text-sm leading-relaxed text-muted">
          <span className="font-semibold text-ink-2">Where it is behind: </span>
          of the benchmark&rsquo;s in-scope items, this run matched{" "}
          {Object.entries(recall)
            .map(([k, v]) => `${v.in_scope_matched}/${v.in_scope} ${k}`)
            .join(" · ")}
          . Recall is the open weakness — the pipeline is stricter than the human
          author, and strictness costs coverage.{" "}
          <Link href="/scorecard" className="text-sm">Full scorecard →</Link>
        </p>
      )}
    </div>
  );
}
