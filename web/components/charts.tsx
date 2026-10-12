import * as React from "react";

// Small server-rendered charts for the console. Palettes are validated with the
// dataviz checker: an ordinal blue ramp for ordered categories (class, tier,
// strength) and the first three categorical slots for unordered ones. Every
// value a tooltip shows is also printed beside the mark, so hover never gates.

export const ORDINAL_4 = ["#184f95", "#2a78d6", "#5598e7", "#86b6ef"];   // dark → light
export const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a"];

/** A focusable mark whose value appears on hover or keyboard focus. */
export function Tip({ label, children, className, style }: {
  label: string; children?: React.ReactNode; className?: string; style?: React.CSSProperties;
}) {
  return (
    <span tabIndex={0} aria-label={label} className={`group relative outline-none ${className ?? ""}`}
          style={style}>
      {children}
      <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5
            -translate-x-1/2 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-xs text-white
            opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus:opacity-100">
        {label}
      </span>
    </span>
  );
}

export type Segment = { label: string; value: number; fill: string };

/** One horizontal 100% bar with a legend row underneath that carries the values. */
export function StackBar({ segments, height = 14 }: { segments: Segment[]; height?: number }) {
  const total = segments.reduce((n, s) => n + s.value, 0);
  const shown = segments.filter(s => s.value > 0);
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex w-full gap-[2px]" style={{ height }}>
        {total === 0 && <div className="h-full w-full rounded-[4px] bg-line-soft" />}
        {shown.map((s, i) => (
          <Tip key={s.label} label={`${s.label}: ${s.value} (${Math.round((s.value / total) * 100)}%)`}
               className={`h-full transition-[filter] hover:brightness-110 focus:brightness-110
                 ${i === 0 ? "rounded-l-[4px]" : ""} ${i === shown.length - 1 ? "rounded-r-[4px]" : ""}`}
               style={{ width: `${(s.value / total) * 100}%`, background: s.fill, minWidth: 3 }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {segments.map(s => (
          <span key={s.label} className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-[2px]" style={{ background: s.fill }} />
            {s.label}
            <span className="font-semibold text-ink-2">
              {s.value}{total ? ` · ${Math.round((s.value / total) * 100)}%` : ""}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

/** Ranked horizontal bars, one hue, value at the tip. */
export function BarList({ rows, fill = ORDINAL_4[1], max }: {
  rows: { label: string; value: number; hint?: string }[]; fill?: string; max?: number;
}) {
  const top = max ?? Math.max(1, ...rows.map(r => r.value));
  return (
    <div className="flex flex-col gap-2">
      {rows.map(r => (
        <div key={r.label} className="grid grid-cols-[minmax(0,180px)_1fr] items-center gap-3 text-sm">
          <span className="truncate text-ink-2" title={r.label}>{r.label}</span>
          <div className="flex items-center gap-2">
            <Tip label={`${r.label}: ${r.value}${r.hint ? ` · ${r.hint}` : ""}`}
                 className="h-2.5 rounded-r-[4px] transition-[filter] hover:brightness-110 focus:brightness-110"
                 style={{ width: `${Math.max(2, (r.value / top) * 100)}%`, background: fill }} />
            <span className="font-mono text-xs tabular-nums text-muted">{r.value}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Daily columns with a hairline baseline; the latest and the peak are labelled. */
export function Columns({ points, height = 120, fill = ORDINAL_4[1] }: {
  points: { label: string; value: number }[]; height?: number; fill?: string;
}) {
  const max = Math.max(1, ...points.map(p => p.value));
  const peak = points.reduce((b, p, i) => (p.value > points[b].value ? i : b), 0);
  return (
    <div>
      <div className="flex items-end gap-[3px] border-b border-line" style={{ height }}>
        {points.map((p, i) => (
          <div key={p.label} className="relative flex h-full flex-1 flex-col justify-end">
            {(i === peak || i === points.length - 1) && p.value > 0 && (
              <span className="mb-1 text-center font-mono text-[10px] tabular-nums text-muted">{p.value}</span>
            )}
            <Tip label={`${p.label}: ${p.value}`}
                 className="block w-full rounded-t-[3px] transition-[filter] hover:brightness-110 focus:brightness-110"
                 style={{ height: `${(p.value / max) * (height - 18)}px`, minHeight: p.value ? 2 : 0,
                          background: fill }} />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[10.5px] text-faint">
        <span>{points[0]?.label}</span><span>{points[points.length - 1]?.label}</span>
      </div>
    </div>
  );
}

/** A metric card: label, value, optional one-line context underneath. */
export function MetricCard({ label, value, sub, tone }: {
  label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: "warn" | "good";
}) {
  return (
    <div className="flex flex-col gap-1 rounded-[14px] border border-line bg-card px-4 py-3.5">
      <span className="text-xs font-medium text-muted">{label}</span>
      <span className={`text-[26px] font-semibold leading-tight tracking-tight
        ${tone === "warn" ? "text-amber-ink" : tone === "good" ? "text-green-ink" : "text-ink"}`}>{value}</span>
      {sub && <span className="text-xs text-faint">{sub}</span>}
    </div>
  );
}
