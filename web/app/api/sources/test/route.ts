import { NextResponse } from "next/server";
import { supabaseAdmin, hasServiceKey } from "@/lib/supabase-admin";

// Fetch a source the way the collector does and report what came back, so a
// dead scrape is visible in the console instead of surfacing weeks later as an
// unexplained absence of evidence.
//
// Mirrors pipeline/collectors: a block page answers 200 with a body, and a
// nav stub clears the status check while carrying no content — neither is a
// working source.

export const dynamic = "force-dynamic";
export const maxDuration = 30;

const UA = "foresight-poc/0.2 (strategic-foresight research collector)";
const MIN_TEXT = 300;
const BLOCK = ["access denied", "you don't have permission", "403 forbidden",
  "are you a robot", "enable javascript", "checking your browser",
  "request unsuccessful", "captcha"];
const NOTFOUND = ["404", "page not found", "page cannot be found", "no longer available"];

function textFrom(html: string) {
  const stripped = html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z]+;/gi, " ");
  const title = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.trim();
  return { title, text: stripped.split(/\s+/).filter(Boolean).join(" ") };
}

export async function POST(req: Request) {
  const { registry_id, url } = (await req.json()) as { registry_id?: string; url?: string };

  let target = url;
  let row: any = null;
  if (registry_id && hasServiceKey()) {
    const { data } = await supabaseAdmin
      .from("source_registry").select("id,url,publisher,method,tier").eq("id", registry_id).single();
    row = data; target = target ?? data?.url;
  }
  if (!target) return NextResponse.json({ error: "No URL to test." }, { status: 400 });

  const started = Date.now();
  let verdict: { ok: boolean; status: number | null; note: string; title?: string; chars?: number };

  try {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 20000);
    const res = await fetch(target, {
      headers: { "User-Agent": UA, "Accept-Language": "en" },
      redirect: "follow", signal: ctl.signal,
    });
    clearTimeout(timer);

    const ctype = res.headers.get("content-type") ?? "";
    if (!res.ok) {
      verdict = { ok: false, status: res.status, note: `HTTP ${res.status}` };
    } else if (/pdf/i.test(ctype)) {
      verdict = { ok: true, status: res.status, note: "PDF — parsed by the collector, not here", chars: 0 };
    } else {
      const body = await res.text();
      const { title, text } = textFrom(body);
      const head = text.slice(0, 600).toLowerCase();
      const probe = ((title ?? "") + " " + head.slice(0, 180)).toLowerCase();
      if (BLOCK.some(m => head.includes(m)))
        verdict = { ok: false, status: res.status, note: "Served a block page (HTTP 200)", title, chars: text.length };
      else if (NOTFOUND.some(m => probe.includes(m)))
        verdict = { ok: false, status: res.status, note: "Served an error page (soft 404)", title, chars: text.length };
      else if (text.length < MIN_TEXT)
        verdict = { ok: false, status: res.status, note: `Only ${text.length} characters — a nav stub or JS-only page`, title, chars: text.length };
      else
        verdict = { ok: true, status: res.status, note: `${text.length.toLocaleString()} characters of text`, title, chars: text.length };
    }
  } catch (e: any) {
    const msg = String(e?.name === "AbortError" ? "Timed out after 20s" : e?.cause?.code ?? e?.message ?? e);
    verdict = { ok: false, status: null, note: msg.slice(0, 140) };
  }

  const ms = Date.now() - started;
  if (row && hasServiceKey()) {
    await supabaseAdmin.from("source_registry").update({
      last_tested_at: new Date().toISOString(),
      last_test_ok: verdict.ok,
      last_test_note: verdict.note,
    }).eq("id", row.id);
  }

  return NextResponse.json({ ...verdict, ms, url: target, publisher: row?.publisher, method: row?.method });
}
