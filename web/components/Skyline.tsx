"use client";
import { useEffect, useState } from "react";

/**
 * UAE skyline hero — a slow crossfade between night photographs.
 *
 * Self-hosted from /public rather than hot-linked: an external image request on
 * every page load is a third-party dependency on the first thing a client sees.
 *
 * Photographs are Unsplash-licensed (free for commercial use, attribution not
 * required — credited below anyway). Swap the files in public/skyline and
 * update SHOTS to use your own or licensed stock.
 */
const SHOTS = [
  { src: "/skyline/lRCWtOEPwiY.jpg", place: "Downtown Dubai", credit: "Unsplash" },
  { src: "/skyline/S5SQzWdUhoE.jpg", place: "Abu Dhabi Corniche", credit: "Unsplash" },
  { src: "/skyline/yFKBh1sC1ng.jpg", place: "Dubai", credit: "Unsplash" },
];

const HOLD = 7000;

export default function Skyline() {
  const [i, setI] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => setI(n => (n + 1) % SHOTS.length), HOLD);
    return () => clearInterval(t);
  }, []);

  return (
    <div aria-hidden style={{ position: "absolute", inset: 0, overflow: "hidden", background: "var(--aurora)" }}>
      {SHOTS.map((s, n) => (
        <img
          key={s.src}
          src={s.src}
          alt=""
          loading={n === 0 ? "eager" : "lazy"}
          // fetchPriority keeps the first frame from queuing behind the others
          {...(n === 0 ? { fetchPriority: "high" as const } : {})}
          style={{
            position: "absolute", inset: 0, width: "100%", height: "100%",
            objectFit: "cover", objectPosition: "center 42%",
            opacity: ready && n === i ? 1 : n === 0 && !ready ? 1 : 0,
            transition: "opacity 2.2s ease-in-out, transform 9s linear",
            transform: n === i ? "scale(1.05)" : "scale(1)",
          }}
        />
      ))}

      {/* Readability scrim: the headline sits on the left, so the gradient is
          heaviest there and lifts towards the skyline on the right. */}
      <div style={{
        position: "absolute", inset: 0,
        background:
          "linear-gradient(90deg, rgba(6,10,30,.95) 0%, rgba(6,10,30,.80) 34%, rgba(6,10,30,.42) 66%, rgba(6,10,30,.26) 100%)",
      }} />
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(180deg, rgba(6,10,30,.72) 0%, rgba(6,10,30,.10) 26%, rgba(6,10,30,.34) 78%, rgba(6,10,30,.80) 100%)",
      }} />

      <div style={{
        position: "absolute", right: 18, bottom: 14, display: "flex", alignItems: "center", gap: 10,
        fontSize: 10.5, color: "rgba(214,223,250,.62)", fontFamily: "'Space Grotesk'", letterSpacing: .6,
      }}>
        <span>{SHOTS[i].place} · {SHOTS[i].credit}</span>
        <span style={{ display: "flex", gap: 5 }}>
          {SHOTS.map((_, n) => (
            <span key={n} style={{
              width: n === i ? 16 : 5, height: 5, borderRadius: 3,
              background: n === i ? "var(--accent)" : "rgba(214,223,250,.34)",
              transition: "width .4s ease, background .4s ease",
            }} />
          ))}
        </span>
      </div>
    </div>
  );
}
