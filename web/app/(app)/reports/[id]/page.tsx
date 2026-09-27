import { supabase } from "@/lib/supabase";
import ReactMarkdown from "react-markdown";
import { label } from "@/components/chips";
import ReportChat from "@/components/ReportChat";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Report({ params }: { params: { id: string } }) {
  const { data } = await supabase.from("reports").select("*").eq("id", params.id).single();
  if (!data) return <p>Not found.</p>;

  const { data: edits } = await supabase
    .from("report_edits").select("id,status,created_at")
    .eq("report_id", params.id).eq("status", "APPLIED");

  return (
    <>
      <article className="card" style={{ padding: 30, maxWidth: 760 }}>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
          <span className={`chip ${data.status === "GATES_OPEN" ? "chip-open" : "chip-passed"}`}>
            {label(data.status)}
          </span>
          {edits && edits.length > 0 && (
            <span style={{ fontSize: 11.5, color: "var(--muted)" }}>
              {edits.length} applied edit{edits.length > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div data-report-body style={{ fontSize: 14.5, lineHeight: 1.7, color: "var(--ink-2)" }}>
          <ReactMarkdown>{data.body_md ?? ""}</ReactMarkdown>
        </div>
        <p style={{ marginTop: 22, fontSize: 11.5, color: "var(--faint)", lineHeight: 1.6 }}>
          Highlight any passage to discuss it. Rewrites are checked against the graph
          before they can be applied — citations must resolve and open gates are honoured.
        </p>
      </article>
      <ReportChat reportId={params.id} bodyMd={data.body_md ?? ""} />
    </>
  );
}
