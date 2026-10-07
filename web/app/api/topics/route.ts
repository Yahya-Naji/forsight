import { NextResponse } from "next/server";
import { supabaseAdmin, hasServiceKey } from "@/lib/supabase-admin";

// Create a topic and bind the sources expected to feed it. A topic with no
// sources collects nothing, so the two are created together.

export const dynamic = "force-dynamic";

const PILLARS = ["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"];
const CODE: Record<string, string> = {
  CYBERSECURITY: "CS", AI: "AI", ELECTRONIC_WARFARE: "EW", PROCUREMENT: "PR",
};

export async function POST(req: Request) {
  if (!hasServiceKey()) {
    return NextResponse.json({ error: "Server is not configured to write topics." }, { status: 503 });
  }
  const body = await req.json() as {
    pillar: string; name: string; description?: string;
    uae_relevance?: string; sources?: string[];
    ew_functions?: string[]; ew_impact?: string;
  };

  const pillar = (body.pillar ?? "").toUpperCase();
  const name = (body.name ?? "").trim();
  if (!PILLARS.includes(pillar)) return NextResponse.json({ error: "Unknown pillar." }, { status: 400 });
  if (name.length < 4) return NextResponse.json({ error: "Give the topic a name." }, { status: 400 });

  // Electronic Warfare is the core pillar: every topic names the EW functions it
  // touches, and outside EW says how. The database enforces this too (025);
  // checking here turns a constraint error into a sentence.
  const ewFunctions = (body.ew_functions ?? []).filter(Boolean);
  const ewImpact = body.ew_impact?.trim() || null;
  if (!ewFunctions.length) {
    return NextResponse.json({ error: "Pick at least one EW function this topic affects." }, { status: 400 });
  }
  if (pillar !== "ELECTRONIC_WARFARE" && !ewImpact) {
    return NextResponse.json({ error: "Say in one sentence what this topic does to electronic warfare." }, { status: 400 });
  }

  // Ids follow the seeded scheme (CS-T07) so console-created topics are
  // indistinguishable from the ones the migration laid down.
  const { data: existing } = await supabaseAdmin
    .from("topics").select("id").eq("pillar", pillar);
  const used = (existing ?? [])
    .map(t => parseInt(String(t.id).split("-T")[1] ?? "", 10))
    .filter(n => !Number.isNaN(n));
  const id = `${CODE[pillar]}-T${String((used.length ? Math.max(...used) : 0) + 1).padStart(2, "0")}`;

  const { error } = await supabaseAdmin.from("topics").insert({
    id, pillar, name,
    description: body.description?.trim() || null,
    uae_relevance: body.uae_relevance?.trim() || null,
    ew_functions: ewFunctions, ew_impact: ewImpact,
  });
  if (error) return NextResponse.json({ error: error.message }, { status: 400 });

  const sources = (body.sources ?? []).filter(Boolean);
  if (sources.length) {
    await supabaseAdmin.from("topic_sources")
      .insert(sources.map(registry_id => ({ topic_id: id, registry_id })));
  }

  return NextResponse.json({ ok: true, id, sources: sources.length });
}

export async function PATCH(req: Request) {
  if (!hasServiceKey()) {
    return NextResponse.json({ error: "Server is not configured to write topics." }, { status: 503 });
  }
  const { topic_id, sources } = await req.json() as { topic_id: string; sources: string[] };
  if (!topic_id) return NextResponse.json({ error: "A topic is required." }, { status: 400 });

  await supabaseAdmin.from("topic_sources").delete().eq("topic_id", topic_id);
  if (sources?.length) {
    await supabaseAdmin.from("topic_sources")
      .insert(sources.map(registry_id => ({ topic_id, registry_id })));
  }
  return NextResponse.json({ ok: true, sources: sources?.length ?? 0 });
}
