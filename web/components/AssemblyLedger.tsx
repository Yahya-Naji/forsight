import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableNum }
  from "@/components/ui/table";

// How the brief was assembled, section by section, from generation_ledger.
//
// This is the row that makes the generation step auditable: what each section
// was given, what was held back, how many redrafts it took before it passed,
// and how many citations it emitted. The redraft column is the honest part — a
// section that took four attempts had three drafts rejected for citing
// something its source did not support, and that is visible here rather than
// smoothed away.

export type LedgerRow = {
  section_key: string;
  section_title: string;
  rows_passed: Record<string, number> | null;
  rows_withheld: Record<string, number> | null;
  retries: number | null;
  withheld: boolean | null;
  citations_emitted: string[] | null;
};

function Counts({ map, held }: { map: Record<string, number> | null; held?: boolean }) {
  const entries = Object.entries(map ?? {}).filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);
  if (!entries.length) return <span className="text-xs text-ghost">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {entries.map(([k, v]) => (
        <Badge key={k} variant={held ? "classC" : "mono"} className="font-normal">{k} {v}</Badge>
      ))}
    </span>
  );
}

export default function AssemblyLedger({ rows, reportTitle }:
  { rows: LedgerRow[]; reportTitle?: string }) {
  if (!rows.length) {
    return <p className="mt-3 text-sm text-muted">No generation ledger yet — run the engine to record one.</p>;
  }
  const retries = rows.reduce((a, r) => a + (r.retries ?? 0), 0);
  const withheld = rows.filter(r => r.withheld).length;

  return (
    <div className="mt-3">
      <p className="mb-2 text-sm text-muted">
        {reportTitle && <span className="font-semibold text-ink-2">{reportTitle} · </span>}
        {`${rows.length} sections · ${retries} redraft${retries === 1 ? "" : "s"} rejected before `}
        {`publication · ${withheld === 0 ? "none withheld" : `${withheld} withheld`}`}
      </p>
      <Table>
        <TableHeader>
          <TableRow className="border-t-0">
            <TableHead>Section</TableHead>
            <TableHead>Given</TableHead>
            <TableHead>Held back</TableHead>
            <TableHead className="text-right">Redrafts</TableHead>
            <TableHead className="pr-0 text-right">Citations</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(r => (
            <TableRow key={r.section_key}>
              <TableCell>
                <div className="font-semibold text-ink">{r.section_title}</div>
                <div className="font-mono text-2xs text-ghost">
                  {r.section_key}
                  {r.withheld && <span className="font-bold text-amber-ink"> · withheld</span>}
                </div>
              </TableCell>
              <TableCell><Counts map={r.rows_passed} /></TableCell>
              <TableCell><Counts map={r.rows_withheld} held /></TableCell>
              <TableNum className={(r.retries ?? 0) > 0 ? "font-bold text-amber-ink" : "text-ghost"}>
                {r.retries ?? 0}
              </TableNum>
              <TableNum className="pr-0 text-ink-2">{(r.citations_emitted ?? []).length}</TableNum>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
