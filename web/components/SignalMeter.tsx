const LEVELS: Record<string, number> = { WEAK: 1, EMERGING: 2, STRONG_EMERGING: 3, STRONG: 4 };
export default function SignalMeter({ strength }: { strength?: string | null }) {
  const n = LEVELS[strength ?? ""] ?? 0;
  return (
    <span className="meter" aria-label={`strength ${strength ?? "unknown"}`}>
      {[0, 1, 2, 3].map(i => <i key={i} className={i < n ? "on" : ""} />)}
    </span>
  );
}
