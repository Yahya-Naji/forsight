"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const PILLARS = [
  ["CYBERSECURITY", "Cybersecurity"], ["AI", "AI"],
  ["ELECTRONIC_WARFARE", "Electronic Warfare"], ["PROCUREMENT", "Procurement"],
] as const;

function Item({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link href={href} style={{
      display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 10,
      background: active ? "var(--accent-wash)" : "transparent",
      fontWeight: active ? 600 : 400, fontSize: 13.5, color: active ? "var(--ink)" : "var(--muted)",
    }}>
      <span style={{ width: 7, height: 7, borderRadius: 4, background: active ? "var(--accent)" : "#C9D0E4" }} />
      {label}
    </Link>
  );
}

export default function Sidebar({ onAsk }: { onAsk?: () => void }) {
  const path = usePathname();
  return (
    <aside style={{
      width: 228, flexShrink: 0, background: "var(--card)", borderRight: "1px solid var(--line)",
      display: "flex", flexDirection: "column", padding: "22px 14px", position: "sticky", top: 0, height: "100vh",
    }}>
      <div className="display" style={{ fontWeight: 700, fontSize: 17, letterSpacing: .4, padding: "0 10px 20px" }}>
        FORESIGHT<span style={{ color: "var(--accent)" }}>.</span>
      </div>
      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Item href="/console" label="Overview" active={path === "/console"} />
        <Item href={`/pillars/CYBERSECURITY`} label="Pillars" active={path.startsWith("/pillars")} />
        <div style={{ display: "flex", flexDirection: "column", paddingLeft: 26, fontSize: 12.5 }}>
          {PILLARS.map(([key, name]) => (
            <Link key={key} href={`/pillars/${key}`} style={{
              padding: "5px 8px",
              color: path === `/pillars/${key}` ? "var(--ink)" : "#7A8098",
              fontWeight: path === `/pillars/${key}` ? 600 : 400,
            }}>{name}</Link>
          ))}
        </div>
        <Item href="/sources" label="Sources" active={path.startsWith("/sources")} />
        <Item href="/evidence" label="Evidence" active={path.startsWith("/evidence")} />
        <Item href="/generate" label="Generate" active={path.startsWith("/generate")} />
        <Item href="/engine" label="Engine" active={path.startsWith("/engine")} />
        <Item href="/reports" label="Reports" active={path.startsWith("/reports")} />
        <Item href="/refusals" label="Refusals" active={path.startsWith("/refusals")} />
        <Item href="/scorecard" label="Scorecard" active={path.startsWith("/scorecard")} />
      </nav>
      <div style={{ flexGrow: 1 }} />
      <button aria-label="Ask the graph" onClick={onAsk} style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", padding: "11px 14px",
        borderRadius: 999, border: "1px solid #E0E5F2", background: "#F8F9FD",
        fontFamily: "inherit", fontSize: 13, color: "#3C4258", cursor: "pointer",
      }}>
        <span style={{ fontWeight: 600 }}>Ask the graph</span>
        <span style={{ fontSize: 11, color: "var(--ghost)", background: "#fff", border: "1px solid var(--line)", borderRadius: 6, padding: "2px 7px" }}>⌘K</span>
      </button>
    </aside>
  );
}
