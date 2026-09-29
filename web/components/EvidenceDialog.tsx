"use client";
import { useEffect, useState } from "react";
import { TierChip, ClassChip, LayerChip, ConfChip } from "./chips";
import { Badge } from "@/components/ui/badge";
import type { Evidence } from "./EvidenceCard";

// The full record behind one claim, including the way out to the source.
//
// A card shows the claim and the chips the rules assigned. What it cannot show
// is the thing that makes the claim checkable: the verbatim span it rests on and
// the page that span came from. Those are the whole promise of this system, and
// they were one join away from the reader with no way to reach them — so the
// card opens.
//
// The link is the point. A reader who cannot get from a sentence in a brief to
// the publisher's own page has to take the citation on trust, which is the
// posture this pipeline exists to make unnecessary.

export default function EvidenceDialog({ ev, onClose }:
  { ev: Evidence & { url?: string | null; doc_title?: string | null }; onClose: () => void }) {

  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  // Escape closes, and the body must not scroll behind the dialog.
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", key);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", key); document.body.style.overflow = prev; };
  }, [onClose]);

  if (!mounted) return null;

  return (
    <div role="dialog" aria-modal="true" aria-label={`Evidence ${ev.id}`}
         onClick={onClose}
         className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto
                    bg-[rgba(10,15,46,.45)] p-6 backdrop-blur-[2px]">
      <div onClick={e => e.stopPropagation()}
           className="my-auto w-full max-w-[680px] rounded-lg border border-line bg-card shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-line-soft px-5 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="mono">{ev.id}</Badge>
            <TierChip tier={ev.tier} />
            <ClassChip c={ev.class} />
            <ConfChip c={ev.confidence} />
            <LayerChip layer={ev.env_layer} />
          </div>
          <button onClick={onClose} aria-label="Close"
                  className="-mr-1 -mt-1 rounded p-1 text-xl leading-none text-ghost
                             hover:bg-line-soft hover:text-ink">×</button>
        </div>

        <div className="px-5 py-4">
          <p className="text-[15px] font-semibold leading-snug">{ev.claim}</p>

          {ev.quote_span && (
            <div className="mt-3">
              <div className="text-2xs font-bold uppercase tracking-wide text-faint">
                The span it rests on
              </div>
              <blockquote className="mt-1.5 border-l-2 border-[#C7D2F7] bg-paper px-3.5 py-2.5
                                     text-sm italic leading-relaxed text-muted">
                &ldquo;{ev.quote_span}&rdquo;
              </blockquote>
            </div>
          )}

          <div className="mt-4 border-t border-line-soft pt-3">
            <div className="text-2xs font-bold uppercase tracking-wide text-faint">Source</div>
            <div className="mt-1.5 text-sm text-ink-2">
              {ev.doc_title || ev.publisher || "unattributed"}
            </div>
            <div className="mt-0.5 text-xs text-ghost">
              {[ev.publisher, ev.date].filter(Boolean).join(" · ")}
            </div>
            {ev.url ? (
              <a href={ev.url} target="_blank" rel="noopener noreferrer"
                 className="mt-2.5 inline-flex items-center gap-1.5 rounded-full bg-accent
                            px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-accent-deep">
                Open the source ↗
              </a>
            ) : (
              // Said plainly rather than shown as a dead link: an evidence row
              // whose document has no URL cannot be checked, and that is worth
              // knowing about the row.
              <p className="mt-2 text-xs text-amber-ink">
                No source URL recorded for this row — it cannot be opened from here.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
