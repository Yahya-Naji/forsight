"use client";
import { useEffect, useMemo, useState } from "react";

/**
 * Rendered UAE skylines, crossfading.
 *
 * Drawn rather than photographed: a stock photo of Dubai on a defence brief is
 * both a licensing question and a cliché, and a rendered skyline can carry the
 * product's own palette. Drop licensed photography into /public and swap the
 * <svg> for an <img> if you'd rather.
 *
 * Window lights come from a seeded generator, not Math.random — the server and
 * the client must produce identical markup or React throws a hydration error.
 */

const rng = (seed: number) => () => {
  seed = (seed * 1664525 + 1013904223) % 4294967296;
  return seed / 4294967296;
};

const W = 1600, H = 900, BASE = 742;   // hero aspect; waterline at BASE
type Tower = { x: number; w: number; h: number; kind: "flat" | "spire" | "dome" | "taper" };

/** Lay a skyline across the full width from a compact height profile. */
function span(seed: number, heights: number[], kinds: Tower["kind"][]): Tower[] {
  const r = rng(seed);
  const towers: Tower[] = [];
  let x = -30;
  for (let i = 0; x < W + 40; i++) {
    const h = heights[i % heights.length] * 1.9 * (0.86 + r() * 0.32);
    const w = 52 + r() * 66;
    towers.push({ x, w, h, kind: kinds[i % kinds.length] });
    x += w + 6 + r() * 20;
  }
  return towers;
}

function scene(seed: number, spec: Tower[]) {
  const r = rng(seed);
  return spec.map(t => {
    const lights: { x: number; y: number; on: boolean }[] = [];
    const cols = Math.max(2, Math.floor(t.w / 14));
    const rows = Math.max(3, Math.floor(t.h / 18));
    for (let c = 0; c < cols; c++)
      for (let k = 0; k < rows; k++)
        lights.push({
          x: t.x + 7 + c * ((t.w - 14) / Math.max(cols - 1, 1)),
          y: BASE - t.h + 18 + k * ((t.h - 30) / Math.max(rows - 1, 1)),
          on: r() > 0.34,
        });
    return { ...t, lights };
  });
}


// Three silhouettes across the full hero width. Dubai leads with a supertall
// taper; Abu Dhabi's Corniche is lower and broader; the marina is spikier.
const SCENES = [
  { name: "Dubai", seed: 7, sky: ["#070B24", "#141C46", "#2A3768"],
    towers: span(7, [150, 92, 210, 128, 340, 176, 104, 248, 136, 190],
                 ["flat", "dome", "spire", "flat", "taper", "spire", "flat", "taper", "dome", "flat"]) },
  { name: "Abu Dhabi", seed: 23, sky: ["#060A20", "#15204A", "#353C6E"],
    towers: span(23, [126, 188, 96, 236, 150, 108, 268, 142, 196, 118],
                 ["dome", "taper", "flat", "spire", "dome", "flat", "taper", "flat", "spire", "dome"]) },
  { name: "Marina", seed: 41, sky: ["#080C28", "#18224F", "#2E3C72"],
    towers: span(41, [196, 118, 252, 140, 96, 288, 160, 206, 124, 172],
                 ["spire", "flat", "taper", "dome", "flat", "spire", "flat", "taper", "dome", "spire"]) },
];

function towerPath(t: Tower) {
  const base = BASE, top = BASE - t.h, x = t.x, w = t.w;
  if (t.kind === "spire")
    return `M${x} ${base} L${x} ${top + 18} L${x + w / 2} ${top} L${x + w} ${top + 18} L${x + w} ${base} Z`;
  if (t.kind === "taper")
    return `M${x} ${base} L${x + w * 0.16} ${top + 10} L${x + w / 2} ${top - 26} L${x + w * 0.84} ${top + 10} L${x + w} ${base} Z`;
  if (t.kind === "dome")
    return `M${x} ${base} L${x} ${top + 12} Q${x + w / 2} ${top - 14} ${x + w} ${top + 12} L${x + w} ${base} Z`;
  return `M${x} ${base} L${x} ${top} L${x + w} ${top} L${x + w} ${base} Z`;
}

export default function Skyline() {
  const [i, setI] = useState(0);
  const scenes = useMemo(() => SCENES.map(s => ({ ...s, built: scene(s.seed, s.towers) })), []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => setI(n => (n + 1) % scenes.length), 7000);
    return () => clearInterval(t);
  }, [scenes.length]);

  return (
    <div aria-hidden style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      {scenes.map((s, n) => (
        <svg key={s.name} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMax slice"
          style={{
            position: "absolute", inset: 0, width: "100%", height: "100%",
            opacity: n === i ? 1 : 0, transition: "opacity 2.4s ease-in-out",
          }}>
          <defs>
            <linearGradient id={`sky-${n}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.sky[0]} />
              <stop offset="58%" stopColor={s.sky[1]} />
              <stop offset="100%" stopColor={s.sky[2]} />
            </linearGradient>
            <linearGradient id={`water-${n}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.sky[2]} stopOpacity="0.95" />
              <stop offset="100%" stopColor="#060A1E" />
            </linearGradient>
            <radialGradient id={`glow-${n}`} cx="50%" cy="82%" r="55%">
              <stop offset="0%" stopColor="#5B7CF0" stopOpacity="0.30" />
              <stop offset="100%" stopColor="#5B7CF0" stopOpacity="0" />
            </radialGradient>
          </defs>

          <rect width={W} height={H} fill={`url(#sky-${n})`} />
          {[...Array(90)].map((_, k) => {
            const r = rng(s.seed * 100 + k);
            return <circle key={k} cx={r() * W} cy={r() * 430} r={r() * 1.1 + 0.3}
              fill="#DCE6FF" opacity={r() * 0.5 + 0.12} />;
          })}
          <circle cx={W * 0.78} cy="140" r="52" fill="#A8B8F5" opacity="0.09" />
          <rect width={W} height={H} fill={`url(#glow-${n})`} />

          {/* far layer, flattened and dimmed for depth */}
          <g opacity="0.38" transform={`translate(-40 ${BASE * 0.2}) scale(1.05 0.78)`}>
            {s.built.map((t, k) => <path key={k} d={towerPath(t)} fill="#0B1233" />)}
          </g>

          <g>
            {s.built.map((t, k) => (
              <g key={k}>
                <path d={towerPath(t)} fill="#080D24" />
                {t.lights.filter(l => l.on).map((l, j) => (
                  <rect key={j} x={l.x} y={l.y} width="3" height="4.2" rx="0.6"
                    fill="#FFE0AC" opacity={0.5 + ((j * 37) % 45) / 100} />
                ))}
              </g>
            ))}
          </g>

          {/* waterfront */}
          <rect y={BASE} width={W} height={H - BASE} fill={`url(#water-${n})`} />
          <g opacity="0.30">
            {s.built.map((t, k) => (
              <path key={k} d={towerPath(t)} fill="#5B7CF0"
                transform={`translate(0 ${BASE * 2}) scale(1 -0.30)`} />
            ))}
          </g>
        </svg>
      ))}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(90deg, rgba(8,12,34,.92) 0%, rgba(8,12,34,.58) 42%, rgba(8,12,34,.12) 78%, rgba(8,12,34,.05) 100%)",
      }} />
    </div>
  );
}
