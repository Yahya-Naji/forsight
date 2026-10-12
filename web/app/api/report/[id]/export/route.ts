import { loadReport } from "@/lib/report";
import { reportHtml } from "@/lib/report-html";

// GET /api/report/<id>/export?format=html|md — the report as a file to send.
export const dynamic = "force-dynamic";

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const r = await loadReport(params.id);
  if (!r) return new Response("Not found", { status: 404 });
  const format = new URL(req.url).searchParams.get("format") === "md" ? "md" : "html";
  const name = r.title.replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "-") || "report";
  const inline = new URL(req.url).searchParams.get("view") === "1";
  return new Response(format === "md" ? r.body_md : reportHtml(r), {
    headers: {
      "Content-Type": format === "md" ? "text/markdown; charset=utf-8" : "text/html; charset=utf-8",
      "Content-Disposition": `${inline ? "inline" : "attachment"}; filename="${name}.${format}"`,
    },
  });
}
