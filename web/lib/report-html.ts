import { CITE_GROUP, type Cited, type LoadedReport } from "@/lib/report";

// A report as one self-contained HTML file: no scripts, no external assets, so
// it opens offline, attaches to an email and prints cleanly. Every citation is
// a link into the source appendix, where the quote it rests on is printed.

const esc = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const KIND_LABEL: Record<Cited["kind"], string> = {
  evidence: "Evidence", finding: "Finding", signal: "Signal", risk: "Risk",
  trend: "Trend", gate: "Validation gate", forecast: "Forecast", other: "Reference",
};

function inline(s: string, cited: Record<string, Cited>, order: Map<string, number>): string {
  let out = esc(s);
  out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*(?!\s)(.+?)\*/g, "$1<em>$2</em>");
  out = out.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2">$1</a>');
  out = out.replace(CITE_GROUP, (_m, group: string) => {
    const ids = group.split(/\s*[;,]\s*/);
    return '<sup class="cite">' + ids.map(id => {
      if (!order.has(id)) order.set(id, order.size + 1);
      const c = cited[id];
      const tip = c ? esc(c.text).slice(0, 220) : "unresolved";
      return `<a href="#src-${id}" title="${tip}">${id}</a>`;
    }).join(" ") + "</sup>";
  });
  return out;
}

function block(md: string, cited: Record<string, Cited>, order: Map<string, number>): string {
  const out: string[] = [];
  let list: "ul" | "ol" | null = null, table = false, para: string[] = [];
  const flush = () => {
    if (para.length) { out.push(`<p>${inline(para.join(" "), cited, order)}</p>`); para = []; }
  };
  const close = () => {
    if (list) { out.push(`</${list}>`); list = null; }
    if (table) { out.push("</table></div>"); table = false; }
  };
  for (const raw of md.split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) { flush(); close(); continue; }
    if (line.startsWith("|")) {
      flush();
      const cells = line.replace(/^\||\|$/g, "").split("|").map(c => c.trim());
      if (cells.every(c => /^:?-+:?$/.test(c))) continue;
      if (!table) { close(); out.push('<div class="tw"><table>'); table = true;
        out.push("<tr>" + cells.map(c => `<th>${inline(c, cited, order)}</th>`).join("") + "</tr>"); continue; }
      out.push("<tr>" + cells.map(c => `<td>${inline(c, cited, order)}</td>`).join("") + "</tr>");
      continue;
    }
    const h = line.match(/^(#{3,6})\s+(.*)/);
    if (h) { flush(); close(); out.push(`<h3>${inline(h[2], cited, order)}</h3>`); continue; }
    const ul = line.match(/^\s*[-*•]\s+(.*)/), ol = line.match(/^\s*\d+[.)]\s+(.*)/);
    if (ul || ol) {
      flush();
      const want = ul ? "ul" : "ol";
      if (list !== want) { close(); out.push(`<${want}>`); list = want; }
      out.push(`<li>${inline((ul ?? ol)![1], cited, order)}</li>`);
      continue;
    }
    if (/^so what:/i.test(line.trim())) {
      flush(); close();
      out.push(`<p class="sowhat"><b>So what</b> ${inline(line.trim().replace(/^so what:\s*/i, ""), cited, order)}</p>`);
      continue;
    }
    if (list) close();
    para.push(line.trim());
  }
  flush(); close();
  return out.join("\n");
}

export function reportHtml(r: LoadedReport): string {
  const order = new Map<string, number>();
  const date = new Date(r.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const body = r.sections.map(s =>
    `<section id="${s.key}"><h2>${esc(s.title)}</h2>\n${block(s.md, r.cited, order)}</section>`).join("\n");

  const sources = Array.from(order.keys()).map(id => {
    const c = r.cited[id];
    if (!c) return `<li id="src-${id}"><span class="sid">${id}</span> <span class="muted">Not found in the graph.</span></li>`;
    const meta = c.kind === "evidence"
      ? [c.publisher, c.tier ? `Tier ${c.tier}` : null, c.cls ? `Class ${c.cls}` : null, c.published].filter(Boolean).join(" · ")
      : [KIND_LABEL[c.kind], c.strength, c.status].filter(Boolean).join(" · ");
    return `<li id="src-${id}"><span class="sid">${id}</span> ${esc(c.text)}
      <div class="meta">${esc(meta)}</div>
      ${c.quote ? `<blockquote>“${esc(c.quote)}”</blockquote>` : ""}
      ${c.url ? `<a class="url" href="${esc(c.url)}">${esc(c.docTitle ?? c.url)}</a>` : ""}</li>`;
  }).join("\n");

  const toc = r.sections.map(s => `<li><a href="#${s.key}">${esc(s.title)}</a></li>`).join("");
  const st = r.stats;

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(r.title)}</title>
<style>
:root{--ink:#1d1d1f;--ink2:#424245;--muted:#6e6e73;--line:#e5e5ea;--paper:#f5f5f7;--accent:#0071e3;--wash:#e8f1fc}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:820px;margin:0 auto;padding:48px 24px 80px}
header{border-bottom:1px solid var(--line);padding-bottom:28px;margin-bottom:28px}
.kicker{font-size:13px;font-weight:600;color:var(--accent);letter-spacing:.02em}
h1{font-size:40px;line-height:1.08;letter-spacing:-.03em;margin:8px 0 10px}
.sub{color:var(--muted);font-size:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-top:22px}
.stats div{background:#fff;padding:12px 14px}.stats b{display:block;font-size:22px;letter-spacing:-.02em}.stats span{font-size:12px;color:var(--muted)}
nav ol{margin:0;padding-left:20px;columns:2;font-size:14px}nav a{color:var(--ink2);text-decoration:none}
section{background:#fff;border-radius:18px;padding:28px 32px;margin:18px 0;box-shadow:0 1px 2px rgba(0,0,0,.04)}
h2{font-size:24px;letter-spacing:-.02em;margin:0 0 14px}h3{font-size:17px;margin:20px 0 8px}
p{color:var(--ink2);margin:0 0 14px}li{color:var(--ink2);margin:4px 0}
.sowhat{background:var(--wash);border-radius:12px;padding:12px 16px;color:var(--ink)}.sowhat b{color:var(--accent);margin-right:6px}
sup.cite{font-size:11px;line-height:0;margin-left:2px}sup.cite a{color:var(--accent);text-decoration:none;font-weight:600;background:var(--wash);border-radius:5px;padding:1px 5px;margin-left:2px;font-family:ui-monospace,Menlo,monospace}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0 16px}th,td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}th{font-weight:600;background:var(--paper)}
.sources ol{padding-left:0;list-style:none}.sources li{border-top:1px solid var(--line);padding:14px 0;font-size:14px}
.sid{font-family:ui-monospace,Menlo,monospace;font-size:12px;font-weight:600;color:var(--accent);background:var(--wash);border-radius:5px;padding:1px 6px;margin-right:6px}
.meta{font-size:12px;color:var(--muted);margin-top:4px}blockquote{margin:8px 0 6px;border-left:2px solid var(--accent);padding-left:12px;font-style:italic;color:var(--muted)}
.url{font-size:12px;color:var(--accent);word-break:break-all}.muted{color:var(--muted)}
footer{font-size:12px;color:var(--muted);margin-top:28px}
@media(max-width:640px){h1{font-size:30px}.stats{grid-template-columns:repeat(2,1fr)}nav ol{columns:1}section{padding:22px 18px}}
@media print{body{background:#fff}.wrap{padding:0}section{box-shadow:none;padding:0;border-radius:0;break-inside:auto}h2{break-after:avoid}.sources li{break-inside:avoid}}
</style></head><body><div class="wrap">
<header>
  <div class="kicker">Strategic foresight · ${esc((r.pillar ?? "").replace(/_/g, " ").toLowerCase())}</div>
  <h1>${esc(r.title)}</h1>
  <div class="sub">${date} · ${r.status === "GATES_OPEN" ? "UAE validation gates open — UAE-specific gap claims withheld" : esc(r.status.replace(/_/g, " ").toLowerCase())}</div>
  <div class="stats">
    <div><b>${st.cited}/${st.sentences}</b><span>sentences cited</span></div>
    <div><b>${st.evidence}</b><span>evidence rows</span></div>
    <div><b>${st.publishers}</b><span>publishers</span></div>
    <div><b>${st.tier1}</b><span>Tier-1 rows</span></div>
  </div>
</header>
<nav><ol>${toc}<li><a href="#sources">Sources</a></li></ol></nav>
${body}
<section id="sources" class="sources"><h2>Sources</h2><ol>${sources}</ol></section>
<footer>Every citation resolves to a row in the evidence graph. Generated ${new Date().toISOString().slice(0, 10)} · report ${r.id}</footer>
</div></body></html>`;
}
