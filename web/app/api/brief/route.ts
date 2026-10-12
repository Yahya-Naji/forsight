import { NextResponse } from "next/server";
import { supabaseAdmin, hasServiceKey } from "@/lib/supabase-admin";
import { complete, hasModel } from "@/lib/azure";

// Conversational intake. The agent interviews the reader until it has enough to
// write against, then emits a structured brief. It asks one question at a time
// — a form disguised as a chat is worse than a form.

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const PILLARS = ["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"];

const SYSTEM = `You are a strategic-foresight lead taking a brief from a client at
the Tawazun Council before writing a decision report.

Your job in this conversation is to find out what report would actually be
useful. Ask ONE question at a time, in plain language, and build on what they
have already said. Never present a list of fields to fill in.

What you need before you can write:
  · the question the report must answer, in their words
  · the decision it supports — a report with no decision behind it is a summary
  · who reads it, and what they can act on
  · which of the four pillars it touches: Cybersecurity, Artificial Intelligence,
    Electronic Warfare, Procurement
  · the time horizon
  · what is explicitly out of scope

Rules:
  · Three to five questions, no more. Infer what you reasonably can rather than
    interrogating them.
  · If they give you a vague goal, ask what decision it informs — that single
    question is usually what turns a survey into a brief.
  · Reflect back what you understood before you finish, in two lines.

When you have enough, end your message with this block exactly once:

<<<BRIEF>>>
{"title":"short report title","goal":"the question it answers","decision":"the decision it supports","audience":"who reads it","pillars":["CYBERSECURITY"],"horizon":"H0_3|H3_5|H5_10|H7_PLUS","focus_terms":["six","to","ten","keywords","for","scoping"],"in_scope":"...","out_of_scope":"...","depth":"BRIEF|STANDARD|DEEP"}
<<<END>>>

focus_terms decides which evidence reaches the writer, so choose the words that
would actually appear in relevant source text — not abstractions.
Until you emit that block, just keep asking.`;

export async function POST(req: Request) {
  if (!hasServiceKey()) {
    return NextResponse.json({ error: "Server is not configured to store briefs." }, { status: 503 });
  }
  const body = (await req.json()) as { brief_id?: string; message?: string; form?: Record<string, any> };
  const sb = supabaseAdmin;

  // ---- the form path: the reader picked the answers the interview would ask
  // for, so the brief is stored READY without a model call.
  if (body.form) {
    const f = body.form;
    const str = (v: any, n = 600) => (typeof v === "string" && v.trim() ? v.trim().slice(0, n) : null);
    const goal = str(f.goal);
    const decision = str(f.decision);
    if (!goal || !decision) {
      return NextResponse.json({ error: "A question and the decision it supports are both required." }, { status: 400 });
    }
    const pillars = (Array.isArray(f.pillars) ? f.pillars : [])
      .map((p: string) => String(p).toUpperCase()).filter((p: string) => PILLARS.includes(p));
    // A question makes a poor title. With no title given, ask for a short one;
    // if the model is unavailable, fall back to the question's first words.
    let title = str(f.title, 160);
    if (!title && hasModel()) {
      try {
        const t = await complete([
          { role: "system", content: "Write a report title of 4 to 8 words for this question. Title case. No quotes, no trailing punctuation, no date." },
          { role: "user", content: goal },
        ], { maxTokens: 40 });
        title = t?.trim().replace(/^["'“]+|["'”.]+$/g, "").slice(0, 120) || null;
      } catch { /* fall through */ }
    }
    title = title ?? (goal.length > 80 ? goal.slice(0, 80).replace(/\s\S*$/, "") + "…" : goal);
    const row = {
      title,
      goal, decision, audience: str(f.audience),
      pillars: pillars.length ? pillars : ["ELECTRONIC_WARFARE"],
      horizon: ["H0_3", "H3_5", "H5_10", "H7_PLUS"].includes(f.horizon) ? f.horizon : null,
      focus_terms: (Array.isArray(f.focus_terms) ? f.focus_terms : [])
        .map((t: any) => String(t).trim()).filter(Boolean).slice(0, 12),
      in_scope: str(f.in_scope), out_of_scope: str(f.out_of_scope),
      depth: ["BRIEF", "STANDARD", "DEEP"].includes(f.depth) ? f.depth : "STANDARD",
      status: "READY",
    };
    const { data, error } = await sb.from("report_briefs").insert(row).select("*").single();
    if (error || !data) return NextResponse.json({ error: error?.message ?? "Could not store the brief." }, { status: 500 });
    return NextResponse.json({ brief_id: data.id, reply: "", ready: true, brief: data });
  }

  if (!hasModel()) {
    return NextResponse.json({ error: "No model deployment is configured." }, { status: 503 });
  }
  const { brief_id, message } = body as { brief_id?: string; message: string };
  if (!message?.trim()) return NextResponse.json({ error: "Say what the report should answer." }, { status: 400 });

  let id = brief_id;
  if (!id) {
    const { data } = await sb.from("report_briefs").insert({ status: "DRAFTING" }).select("id").single();
    id = data?.id;
  }
  if (!id) return NextResponse.json({ error: "Could not start a brief." }, { status: 500 });

  const { data: prior } = await sb.from("brief_messages")
    .select("role,content").eq("brief_id", id).order("created_at").limit(24);

  const history = (prior ?? []).map(m => ({ role: m.role as "user" | "assistant", content: m.content }));
  const raw = await complete(
    [{ role: "system", content: SYSTEM }, ...history, { role: "user", content: message }],
    { maxTokens: 1400 }
  );
  if (!raw) return NextResponse.json({ error: "The agent did not respond." }, { status: 502 });

  // ---- split the reply from the structured brief -----------------------
  let reply = raw, ready = false;
  const m = raw.match(/<<<BRIEF>>>([\s\S]*?)<<<END>>>/);
  if (m) {
    reply = raw.replace(m[0], "").trim();
    try {
      const b = JSON.parse(m[1].trim());
      const pillars = (Array.isArray(b.pillars) ? b.pillars : [])
        .map((p: string) => String(p).toUpperCase()).filter((p: string) => PILLARS.includes(p));
      await sb.from("report_briefs").update({
        title: b.title ?? null, goal: b.goal ?? null, decision: b.decision ?? null,
        audience: b.audience ?? null,
        pillars: pillars.length ? pillars : ["CYBERSECURITY"],
        horizon: ["H0_3", "H3_5", "H5_10", "H7_PLUS"].includes(b.horizon) ? b.horizon : null,
        focus_terms: Array.isArray(b.focus_terms) ? b.focus_terms.slice(0, 12) : [],
        in_scope: b.in_scope ?? null, out_of_scope: b.out_of_scope ?? null,
        depth: ["BRIEF", "STANDARD", "DEEP"].includes(b.depth) ? b.depth : "STANDARD",
        status: "READY",
      }).eq("id", id);
      ready = true;
    } catch {
      // A malformed block means the interview continues rather than storing junk.
      ready = false;
    }
  }

  await sb.from("brief_messages").insert([
    { brief_id: id, role: "user", content: message },
    { brief_id: id, role: "assistant", content: reply },
  ]);

  const { data: brief } = await sb.from("report_briefs").select("*").eq("id", id).single();
  return NextResponse.json({ brief_id: id, reply, ready, brief });
}
