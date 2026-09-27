import { NextResponse } from "next/server";
import { supabaseAdmin, hasServiceKey } from "@/lib/supabase-admin";
import { checkPassage } from "@/lib/verify";

// Applying an edit rewrites a verified document, so the checks run again here
// rather than trusting the verdict stored at proposal time — the graph may have
// moved since, and a stale pass is not a pass.

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  if (!hasServiceKey()) {
    return NextResponse.json({ error: "Server is not configured to apply edits." }, { status: 503 });
  }
  const { edit_id } = (await req.json()) as { edit_id: string };
  const sb = supabaseAdmin;

  const { data: edit } = await sb.from("report_edits").select("*").eq("id", edit_id).single();
  if (!edit) return NextResponse.json({ error: "Edit not found." }, { status: 404 });
  if (edit.status === "APPLIED") return NextResponse.json({ error: "Already applied." }, { status: 409 });
  if (!edit.proposed_text) return NextResponse.json({ error: "This edit has no replacement text." }, { status: 400 });

  const { data: report } = await sb.from("reports").select("id,pillar,body_md").eq("id", edit.report_id).single();
  if (!report) return NextResponse.json({ error: "Report not found." }, { status: 404 });

  const [ev, sig, fc, gates] = await Promise.all([
    sb.from("evidence").select("id").eq("pillar", report.pillar),
    sb.from("signals").select("id").eq("pillar", report.pillar),
    sb.from("forecasts").select("id").eq("pillar", report.pillar),
    sb.from("validation_gates").select("id,blocks").eq("status", "OPEN"),
  ]);
  const known = new Set<string>([
    ...(ev.data ?? []).map(r => r.id), ...(sig.data ?? []).map(r => r.id), ...(fc.data ?? []).map(r => r.id),
  ]);
  const openGates = (gates.data ?? []).filter(
    g => (g.blocks ?? "").toLowerCase().includes(report.pillar.toLowerCase().split("_")[0]) ||
         g.id.startsWith(`VG-${report.pillar.slice(0, 2)}-`)
  );

  const verdict = checkPassage(edit.proposed_text, known, openGates);
  if (!verdict.ok) {
    await sb.from("report_edits").update({
      status: "REJECTED", verification: verdict,
      rejected_reason: "re-check on apply failed",
    }).eq("id", edit_id);
    return NextResponse.json({ error: "This edit no longer passes verification.", verdict }, { status: 422 });
  }

  const body = report.body_md ?? "";
  if (!edit.original_text || !body.includes(edit.original_text)) {
    // The passage moved or was already changed; replacing blind would corrupt
    // the document or silently edit the wrong paragraph.
    await sb.from("report_edits").update({
      status: "SUPERSEDED",
      rejected_reason: "the highlighted passage is no longer present in the report",
    }).eq("id", edit_id);
    return NextResponse.json({ error: "The highlighted passage is no longer in the report — it may have been edited already." }, { status: 409 });
  }

  const updated = body.replace(edit.original_text, edit.proposed_text);
  await sb.from("reports").update({ body_md: updated }).eq("id", report.id);
  await sb.from("report_edits").update({
    status: "APPLIED", verification: verdict, applied_at: new Date().toISOString(),
  }).eq("id", edit_id);

  return NextResponse.json({ ok: true, verdict });
}
