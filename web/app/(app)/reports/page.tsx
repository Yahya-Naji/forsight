import Link from "next/link";
import { supabase } from "@/lib/supabase";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Reports() {
  const { data } = await supabase.from("reports").select("id,title,status,pillar,created_at").order("created_at", { ascending: false });
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <div className="kicker">Library</div>
        <h1 className="display" style={{ fontWeight: 700, fontSize: 30, margin: "4px 0 0", letterSpacing: -0.4 }}>Reports</h1>
      </div>
      <div className="card" style={{ padding: "4px 18px" }}>
        {(data ?? []).map((r, i, arr) => (
          <div key={r.id} className="row" style={{ padding: "14px 0", borderBottom: i < arr.length - 1 ? "1px solid var(--line-soft)" : "none" }}>
            <Link href={`/reports/${r.id}`} style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", flexGrow: 1 }}>{r.title}</Link>
            <span className={`chip ${r.status === "GATES_OPEN" ? "chip-open" : "chip-conf"}`}>{r.status.replace("_", " ")}</span>
            <span style={{ fontSize: 12, color: "var(--ghost)", width: 70, textAlign: "right" }}>{new Date(r.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span>
          </div>
        ))}
        {!data?.length && <div style={{ padding: 18, fontSize: 13, color: "var(--faint)" }}>No reports yet.</div>}
      </div>
    </div>
  );
}
