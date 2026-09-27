import { NextResponse } from "next/server";
import { supabaseAdmin, hasServiceKey } from "@/lib/supabase-admin";

// The heavy pipeline runs in Python (repo /pipeline). This endpoint records the
// request and, when a dispatch channel is configured, asks GitHub Actions to
// run it. It never generates content itself, and it never marks a run as
// happening when nothing was dispatched — a QUEUED row is the honest state.

const PILLARS = ["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"];

export async function POST(req: Request) {
  const back = (params: string) =>
    NextResponse.redirect(new URL(`/generate?${params}`, req.url), 303);

  let pillar = "CYBERSECURITY";
  let title: string | null = null;
  let briefId: string | null = null;
  let template = "TPL-BRIEF-01";
  try {
    const form = await req.formData();
    const p = String(form.get("pillar") ?? "");
    if (PILLARS.includes(p)) pillar = p;
    const t = String(form.get("title") ?? "").trim();
    if (t) title = t;
    const b = String(form.get("brief_id") ?? "").trim();
    if (b) briefId = b;
    const tpl = String(form.get("template") ?? "").trim();
    if (tpl) template = tpl;
  } catch {
    /* no body — fall through with defaults */
  }

  if (!hasServiceKey()) {
    return back("error=no-service-key");
  }

  const { data, error } = await supabaseAdmin
    .from("pipeline_runs")
    .insert({ pillar, title, template_id: template, status: "QUEUED" })
    .select("id")
    .single();

  if (error || !data) {
    return back(`error=${encodeURIComponent(error?.message ?? "insert failed")}`);
  }

  // Dispatch is optional. Without GH_TOKEN/GH_REPO the row simply stays QUEUED
  // and an operator runs the pipeline from the repo — no fake progress.
  const token = process.env.GH_TOKEN;
  const repo = process.env.GH_REPO;
  const workflow = process.env.GH_WORKFLOW ?? "pipeline.yml";
  if (token && repo) {
    try {
      const res = await fetch(
        `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ref: process.env.GH_REF ?? "main",
            inputs: { pillar, run_id: data.id, title: title ?? "", brief_id: briefId ?? "" },
          }),
        }
      );
      if (!res.ok) {
        const detail = (await res.text()).slice(0, 200);
        await supabaseAdmin.from("pipeline_runs")
          .update({ error: `dispatch failed (${res.status}): ${detail}` })
          .eq("id", data.id);
      }
    } catch (e) {
      await supabaseAdmin.from("pipeline_runs")
        .update({ error: `dispatch error: ${String(e).slice(0, 200)}` })
        .eq("id", data.id);
    }
  }

  return back(`run=${data.id}`);
}
