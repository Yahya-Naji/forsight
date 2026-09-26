import { PILLAR_LABEL, label } from "./chips";

// Gate text comes from the database. rules.py now writes reader-facing pillar
// names, but a legacy row must never surface a raw enum in the console.
const humanise = (t: string) =>
  Object.entries(PILLAR_LABEL).reduce((acc, [k, v]) => acc.replaceAll(k, v), t ?? "");

export default function GateCard({ id, status, blocks }: { id: string; status: string; blocks: string }) {
  const open = status === "OPEN";
  return (
    <div style={{
      background: open ? "var(--amber-bg)" : "var(--green-bg)",
      border: `1px solid ${open ? "var(--amber-line)" : "var(--green-line)"}`,
      borderRadius: "var(--radius)", padding: "14px 16px",
    }}>
      <span className={`chip ${open ? "chip-open" : "chip-passed"}`}>{id} · {label(status)}</span>
      <div style={{ fontSize: 13, color: open ? "#4A4633" : "#35513F", marginTop: 8, lineHeight: 1.45 }}>{humanise(blocks)}</div>
    </div>
  );
}
