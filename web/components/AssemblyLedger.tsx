// How the brief was assembled, section by section, from generation_ledger.
//
// This is the row that makes the generation step auditable: what each section was
// given, what was held back from it, how many redrafts it took before it passed,
// and how many citations it emitted. The retries column is the honest part — a
// section that took four attempts had three drafts rejected for citing something
// its source did not support, and that is visible here rather than smoothed away.

export type LedgerRow = {
  section_key: string;
  section_title: string;
  rows_passed: Record<string, number> | null;
  rows_withheld: Record<string, number> | null;
  retries: number | null;
  withheld: boolean | null;
  citations_emitted: string[] | null;
};

function Counts({ map, tone }: { map: Record<string, number> | null; tone: "pass" | "hold" }) {
  const entries = Object.entries(map ?? {}).filter(([, v]) => v > 0);
  if (entries.length === 0) return <span style={{ color: "var(--ghost)", fontSize: 11.5 }}>—</span>;
  return (
    <span style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {entries.sort((a, b) => b[1] - a[1]).map(([k, v]) => (
        <span key={k} style={{
          fontFamily: "var(--mono)", fontSize: 10.5, borderRadius: 5, padding: "1.5px 6px",
          color: tone === "pass" ? "#3A4468" : "var(--amber-ink)",
          background: tone === "pass" ? "#EDEFF6" : "var(--amber-bg)",
          border: `1px solid ${tone === "pass" ? "#D6DBEA" : "var(--amber-line)"}`,
        }}>{k} {v}</span>
      ))}
    </span>
  );
}

export default function AssemblyLedger({ rows, reportTitle }: { rows: LedgerRow[]; reportTitle?: string }) {
  if (rows.length === 0) {
    return (
      <div style={{ marginTop: 12, fontSize: 12.5, color: "var(--muted)" }}>
        No generation ledger yet — run the engine to record one.
      </div>
    );
  }
  const totalRetries = rows.reduce((a, r) => a + (r.retries ?? 0), 0);
  const withheld = rows.filter((r) => r.withheld).length;

  return (
    <div style={{ marginTop: 13 }}>
      <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>
        {reportTitle && <span style={{ color: "var(--ink-2)", fontWeight: 600 }}>{reportTitle} · </span>}
        {`${rows.length} sections · ${totalRetries} redraft${totalRetries === 1 ? "" : "s"} rejected `}
        {`before publication · ${withheld === 0 ? "none withheld" : `${withheld} withheld`}`}
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr>
              {["Section", "Given", "Held back", "Redrafts", "Citations"].map((h, i) => (
                <th key={h} style={{
                  textAlign: i > 2 ? "right" : "left", fontFamily: "var(--mono)", fontSize: 9.5,
                  letterSpacing: 1, textTransform: "uppercase", color: "var(--faint)",
                  fontWeight: 600, padding: "0 10px 7px 0", whiteSpace: "nowrap",
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.section_key} style={{ borderTop: "1px solid var(--line-soft)" }}>
                <td style={{ padding: "8px 10px 8px 0", verticalAlign: "top" }}>
                  <div style={{ fontWeight: 600, color: "var(--ink)" }}>{r.section_title}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--ghost)" }}>
                    {r.section_key}
                    {r.withheld && (
                      <span style={{ color: "var(--amber-ink)", fontWeight: 700 }}> · withheld</span>
                    )}
                  </div>
                </td>
                <td style={{ padding: "8px 10px 8px 0", verticalAlign: "top" }}>
                  <Counts map={r.rows_passed} tone="pass" />
                </td>
                <td style={{ padding: "8px 10px 8px 0", verticalAlign: "top" }}>
                  <Counts map={r.rows_withheld} tone="hold" />
                </td>
                <td style={{
                  padding: "8px 10px 8px 0", textAlign: "right", verticalAlign: "top",
                  fontFamily: "var(--mono)", fontVariantNumeric: "tabular-nums",
                  color: (r.retries ?? 0) > 0 ? "var(--amber-ink)" : "var(--ghost)",
                  fontWeight: (r.retries ?? 0) > 0 ? 700 : 400,
                }}>{r.retries ?? 0}</td>
                <td style={{
                  padding: "8px 0", textAlign: "right", verticalAlign: "top",
                  fontFamily: "var(--mono)", fontVariantNumeric: "tabular-nums", color: "var(--ink-2)",
                }}>{(r.citations_emitted ?? []).length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
