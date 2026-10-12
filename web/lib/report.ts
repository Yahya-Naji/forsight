import { supabase } from "@/lib/supabase";

// One loader for every way a report is shown: the reading view, the HTML
// download and the Markdown download. A citation is only useful if the reader
// can open it, so every id in the body is resolved here — evidence to its quote,
// publisher and tier; findings, signals, risks and gates to their statements.

export const CITE_ID = /\b(?:EV|F|SIG|R|TR|VG|FC|CU|U|FIG)-[A-Z0-9]+(?:-[A-Z0-9]+)?\b/g;
const HAS_CITE = new RegExp(CITE_ID.source);
// A bracketed group of ids: [EV-1], [EV-1, EV-2], [EV-1; F-EW-02]
export const CITE_GROUP = /\[((?:EV|F|SIG|R|TR|VG|FC|CU|U|FIG)-[A-Z0-9-]+(?:\s*[;,]\s*(?:EV|F|SIG|R|TR|VG|FC|CU|U|FIG)-[A-Z0-9-]+)*)\]/g;

export type Cited = {
  id: string;
  kind: "evidence" | "finding" | "signal" | "risk" | "trend" | "gate" | "forecast" | "other";
  text: string;
  quote?: string | null;
  cls?: string | null;
  publisher?: string | null;
  tier?: number | null;
  url?: string | null;
  docTitle?: string | null;
  published?: string | null;
  strength?: string | null;
  status?: string | null;
};

export type Section = { key: string; title: string; md: string };

export type LoadedReport = {
  id: string; title: string; status: string; pillar: string | null;
  template: string | null; created_at: string; body_md: string;
  sections: Section[]; cited: Record<string, Cited>;
  stats: { sentences: number; cited: number; evidence: number; publishers: number; tier1: number };
};

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function splitSections(md: string): { title: string; sections: Section[] } {
  const lines = md.split("\n");
  let title = "";
  const sections: Section[] = [];
  let cur: Section | null = null;
  for (const line of lines) {
    const h1 = line.match(/^#\s+(.*)/);
    const h2 = line.match(/^##\s+(.*)/);
    if (h1 && !title) { title = h1[1].trim(); continue; }
    if (h2) {
      if (cur) sections.push(cur);
      const t = h2[1].trim();
      cur = { key: slug(t), title: t, md: "" };
      continue;
    }
    if (cur) cur.md += line + "\n";
  }
  if (cur) sections.push(cur);
  // "So what:" is the section's takeaway and is styled as a callout; a model
  // sometimes runs it on at the end of a paragraph, so it is split out here.
  const tidy = (md: string) => md.trim().replace(/([^\n])[ \t]+(So what:)/g, "$1\n\n$2");
  return { title, sections: sections.map(s => ({ ...s, md: tidy(s.md) })) };
}

export function citedIds(md: string): string[] {
  return Array.from(new Set(md.match(CITE_ID) ?? []));
}

export async function loadReport(id: string): Promise<LoadedReport | null> {
  const { data: r } = await supabase.from("reports")
    .select("id,title,status,pillar,template_id,created_at,body_md").eq("id", id).single();
  if (!r) return null;

  const body: string = r.body_md ?? "";
  const { title, sections } = splitSections(body);
  // References are rebuilt from the resolved rows, so the body's own list is
  // dropped from the reading view (the Markdown download keeps it verbatim).
  const prose = sections.filter(s => s.key !== "references");
  const all = citedIds(prose.map(s => s.md).join("\n"));

  // Frozen at issue (migration 034): what each id said when the report was
  // written. Only ids with no frozen row — reports older than the table — are
  // resolved against the live graph, which may since have been rebuilt.
  const { data: frozen } = await supabase.from("report_citations")
    .select("cited_id,kind,text,quote,class,publisher,tier,url,doc_title,published,strength,status")
    .eq("report_id", id);
  const cited: Record<string, Cited> = {};
  for (const f of (frozen ?? []) as any[]) {
    cited[f.cited_id] = {
      id: f.cited_id, kind: f.kind, text: f.text ?? "", quote: f.quote, cls: f.class,
      publisher: f.publisher, tier: f.tier, url: f.url, docTitle: f.doc_title,
      published: f.published, strength: f.strength, status: f.status,
    };
  }
  const ids = all.filter(i => !cited[i]);
  const by = (p: string) => ids.filter(i => i.startsWith(p + "-"));

  const ev = by("EV"), fi = by("F"), sg = by("SIG"), rk = by("R"), tr = by("TR"), vg = by("VG"), fc = by("FC");
  const none = { data: [] as any[] };
  const [evRes, links, fiRes, sgRes, rkRes, trRes, vgRes, fcRes] = await Promise.all([
    ev.length ? supabase.from("evidence").select("id,claim,quote_span,class").in("id", ev) : none,
    ev.length ? supabase.from("evidence_sources")
      .select("evidence_id,documents(title,url,published_on,registry_id)").in("evidence_id", ev) : none,
    fi.length ? supabase.from("findings").select("id,statement").in("id", fi) : none,
    sg.length ? supabase.from("signals").select("id,statement,strength").in("id", sg) : none,
    rk.length ? supabase.from("risks").select("id,statement,score").in("id", rk) : none,
    tr.length ? supabase.from("trends").select("id,name,statement").in("id", tr) : none,
    vg.length ? supabase.from("validation_gates").select("id,gate,status").in("id", vg) : none,
    fc.length ? supabase.from("forecasts").select("id,statement").in("id", fc) : none,
  ]);

  const docOf = new Map<string, any>();
  for (const l of (links.data ?? []) as any[]) if (!docOf.has(l.evidence_id) && l.documents) docOf.set(l.evidence_id, l.documents);
  const regIds = Array.from(new Set(Array.from(docOf.values()).map(d => d.registry_id).filter(Boolean)));
  const { data: regs } = regIds.length
    ? await supabase.from("source_registry").select("id,publisher,tier").in("id", regIds)
    : { data: [] as any[] };
  const regOf = new Map((regs ?? []).map((g: any) => [g.id, g]));

  for (const e of (evRes.data ?? []) as any[]) {
    const d = docOf.get(e.id), g = d ? regOf.get(d.registry_id) : null;
    cited[e.id] = {
      id: e.id, kind: "evidence", text: e.claim, quote: e.quote_span, cls: e.class,
      publisher: g?.publisher ?? null, tier: g?.tier ?? null, url: d?.url ?? null,
      docTitle: d?.title ?? null, published: d?.published_on ?? null,
    };
  }
  for (const f of (fiRes.data ?? []) as any[]) cited[f.id] = { id: f.id, kind: "finding", text: f.statement };
  for (const s of (sgRes.data ?? []) as any[]) cited[s.id] = { id: s.id, kind: "signal", text: s.statement, strength: s.strength };
  for (const x of (rkRes.data ?? []) as any[]) cited[x.id] = { id: x.id, kind: "risk", text: x.statement };
  for (const t of (trRes.data ?? []) as any[]) cited[t.id] = { id: t.id, kind: "trend", text: t.statement ?? t.name };
  for (const g of (vgRes.data ?? []) as any[]) cited[g.id] = { id: g.id, kind: "gate", text: g.gate, status: g.status };
  for (const f of (fcRes.data ?? []) as any[]) cited[f.id] = { id: f.id, kind: "forecast", text: f.statement };

  const text = prose.map(s => s.md).join("\n");
  const sentences = text.replace(/\n+/g, " ").split(/(?<=[.!?])\s+(?=[A-Z])/).filter(s => s.trim().length > 20);
  const evRows = Object.values(cited).filter(c => c.kind === "evidence");
  return {
    id: r.id, title: r.title || title, status: r.status, pillar: r.pillar, template: r.template_id,
    created_at: r.created_at, body_md: body, sections: prose, cited,
    stats: {
      sentences: sentences.length,
      cited: sentences.filter(s => HAS_CITE.test(s)).length,
      evidence: evRows.length,
      publishers: new Set(evRows.map(c => c.publisher).filter(Boolean)).size,
      tier1: evRows.filter(c => c.tier === 1).length,
    },
  };
}
