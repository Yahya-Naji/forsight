import { notFound } from "next/navigation";
import { loadReport } from "@/lib/report";
import ReportView from "@/components/ReportView";
import ReportChat from "@/components/ReportChat";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Report({ params }: { params: { id: string } }) {
  const r = await loadReport(params.id);
  if (!r) notFound();
  return (
    <>
      <ReportView r={r} />
      <div className="no-print">
        <ReportChat reportId={params.id} bodyMd={r.body_md} />
      </div>
    </>
  );
}
