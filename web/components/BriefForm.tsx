"use client";
import { useState } from "react";

// The interview as a form: the same fields the chat asks for, with the usual
// answers ready to pick. Anything can still be typed in "Other".

export type BriefFormValue = {
  title: string; goal: string; decision: string; audience: string;
  pillars: string[]; horizon: string; focus_terms: string[];
  out_of_scope: string; depth: string;
};

const QUESTIONS = [
  "How is the counter-UAS threat to UAE critical sites changing, and what should we field?",
  "Where is GNSS denial and spoofing heading, and how exposed are our platforms?",
  "Which EW capabilities should we prioritise in the next acquisition cycle?",
];
const DECISIONS = [
  "Capability investment priorities",
  "Procurement and vendor selection",
  "Doctrine, policy and spectrum rules",
  "Threat awareness for leadership",
];
const AUDIENCES = [
  "Tawazun Council leadership",
  "Procurement committee",
  "Programme / technical office",
  "Armed forces planners",
];
const PILLARS: [string, string][] = [
  ["ELECTRONIC_WARFARE", "Electronic warfare"],
  ["CYBERSECURITY", "Cyber"],
  ["AI", "AI"],
  ["PROCUREMENT", "Procurement"],
];
const HORIZONS: [string, string][] = [["H0_3", "0–3 years"], ["H3_5", "3–5 years"], ["H5_10", "5–10 years"], ["H7_PLUS", "7+ years"]];
const TERMS = [
  "jamming", "GNSS", "spoofing", "counter-UAS", "drone", "loitering munition", "directed energy",
  "SEAD", "spectrum", "electronic support", "fibre-optic", "software-defined radio",
];
const DEPTHS: [string, string][] = [["BRIEF", "Brief"], ["STANDARD", "Standard"], ["DEEP", "Deep"]];

export default function BriefForm({ busy, onSubmit }: { busy: boolean; onSubmit: (v: BriefFormValue) => void }) {
  const [v, setV] = useState<BriefFormValue>({
    title: "", goal: "", decision: "", audience: "", pillars: ["ELECTRONIC_WARFARE"],
    horizon: "H3_5", focus_terms: ["jamming", "counter-UAS", "drone"], out_of_scope: "", depth: "STANDARD",
  });
  const [term, setTerm] = useState("");
  const set = (k: keyof BriefFormValue, x: any) => setV(o => ({ ...o, [k]: x }));
  const toggle = (k: "pillars" | "focus_terms", x: string) =>
    setV(o => ({ ...o, [k]: o[k].includes(x) ? o[k].filter(y => y !== x) : [...o[k], x] }));
  const ok = v.goal.trim() && v.decision.trim() && v.pillars.length;

  return (
    <form className="flex h-full flex-col" onSubmit={e => { e.preventDefault(); if (ok && !busy) onSubmit(v); }}>
      <div className="flex-1 space-y-6 overflow-y-auto p-5 pb-8">
        <Field label="What should the report answer?" required>
          <textarea value={v.goal} onChange={e => set("goal", e.target.value)} rows={2}
            placeholder="The question, in your own words"
            className="w-full resize-none rounded-xl border border-line bg-paper px-3.5 py-2.5 text-[14px] text-ink outline-none focus:border-accent" />
          <div className="mt-2 flex flex-col gap-1.5">
            {QUESTIONS.map(q => (
              <button key={q} type="button" onClick={() => set("goal", q)}
                className="text-left text-[12.5px] text-accent hover:underline">{q}</button>
            ))}
          </div>
        </Field>

        <Field label="Which decision does it support?" required>
          <Choices options={DECISIONS} value={v.decision} onChange={x => set("decision", x)} other />
        </Field>

        <Field label="Who reads it?">
          <Choices options={AUDIENCES} value={v.audience} onChange={x => set("audience", x)} other />
        </Field>

        <Field label="Pillars" hint="Electronic warfare is the core; the others are lenses on it.">
          <div className="flex flex-wrap gap-2">
            {PILLARS.map(([k, l]) => (
              <Pill key={k} on={v.pillars.includes(k)} onClick={() => toggle("pillars", k)}>{l}</Pill>
            ))}
          </div>
        </Field>

        <div className="grid gap-6 sm:grid-cols-2">
          <Field label="Horizon">
            <div className="flex flex-wrap gap-2">
              {HORIZONS.map(([k, l]) => <Pill key={k} on={v.horizon === k} onClick={() => set("horizon", k)}>{l}</Pill>)}
            </div>
          </Field>
          <Field label="Depth">
            <div className="flex flex-wrap gap-2">
              {DEPTHS.map(([k, l]) => <Pill key={k} on={v.depth === k} onClick={() => set("depth", k)}>{l}</Pill>)}
            </div>
          </Field>
        </div>

        <Field label="Focus terms" hint="Only evidence mentioning these reaches the writer; the rest is counted in the ledger.">
          <div className="flex flex-wrap gap-2">
            {Array.from(new Set([...TERMS, ...v.focus_terms])).map(t => (
              <Pill key={t} on={v.focus_terms.includes(t)} onClick={() => toggle("focus_terms", t)}>{t}</Pill>
            ))}
          </div>
          <input value={term} onChange={e => setTerm(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && term.trim()) { e.preventDefault(); if (!v.focus_terms.includes(term.trim())) toggle("focus_terms", term.trim()); setTerm(""); }
            }}
            placeholder="Add a term and press Enter"
            className="mt-2 w-full rounded-xl border border-line bg-paper px-3.5 py-2 text-[13px] text-ink outline-none focus:border-accent" />
        </Field>

        <div className="grid gap-6 sm:grid-cols-2">
          <Field label="Title" hint="Optional — taken from the question if blank.">
            <input value={v.title} onChange={e => set("title", e.target.value)}
              className="w-full rounded-xl border border-line bg-paper px-3.5 py-2 text-[13.5px] text-ink outline-none focus:border-accent" />
          </Field>
          <Field label="Out of scope" hint="Optional.">
            <input value={v.out_of_scope} onChange={e => set("out_of_scope", e.target.value)}
              className="w-full rounded-xl border border-line bg-paper px-3.5 py-2 text-[13.5px] text-ink outline-none focus:border-accent" />
          </Field>
        </div>
      </div>

      <div className="flex items-center gap-3 border-t border-line p-4">
        <span className="flex-1 text-[12px] text-muted">
          {ok ? "Ready to set the brief." : "Pick a question and the decision it supports."}
        </span>
        <button type="submit" disabled={!ok || busy} className="pill-btn disabled:opacity-40">
          {busy ? "Saving…" : "Set the brief"}
        </button>
      </div>
    </form>
  );
}

function Field({ label, hint, required, children }: { label: string; hint?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-2 text-[13px] font-semibold text-ink">
        {label}{required && <span className="ml-1 text-accent">*</span>}
      </div>
      {children}
      {hint && <div className="mt-1.5 text-[11.5px] leading-snug text-faint">{hint}</div>}
    </div>
  );
}

function Pill({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={`rounded-full border px-3 py-1.5 text-[12.5px] font-medium transition active:scale-[.97]
        ${on ? "border-accent bg-accent text-white" : "border-line bg-white text-ink-2 hover:border-accent/50"}`}>
      {children}
    </button>
  );
}

function Choices({ options, value, onChange, other }: { options: string[]; value: string; onChange: (x: string) => void; other?: boolean }) {
  const custom = value && !options.includes(value);
  const [typing, setTyping] = useState(false);
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(o => <Pill key={o} on={value === o} onClick={() => { setTyping(false); onChange(o); }}>{o}</Pill>)}
      {other && (typing || custom ? (
        <input autoFocus value={custom ? value : ""} onChange={e => onChange(e.target.value)} placeholder="Other…"
          className="min-w-[180px] flex-1 rounded-full border border-accent bg-white px-3 py-1.5 text-[12.5px] text-ink outline-none" />
      ) : (
        <Pill on={false} onClick={() => { setTyping(true); onChange(""); }}>Other…</Pill>
      ))}
    </div>
  );
}
