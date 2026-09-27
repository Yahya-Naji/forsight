import { cn } from "@/lib/utils";

/** Signal strength as four discrete steps — a strength is an ordinal the rules
 *  computed, not a percentage, so it is never drawn as a continuous bar. */
export function Meter({ filled, of = 4, className }: { filled: number; of?: number; className?: string }) {
  return (
    <span className={cn("inline-flex gap-[3px]", className)} role="img"
          aria-label={`${filled} of ${of}`}>
      {Array.from({ length: of }, (_, i) => (
        <i key={i} className={cn("h-[5px] w-3.5 rounded-[3px]",
                                 i < filled ? "bg-accent" : "bg-[#E3E7F3]")} />
      ))}
    </span>
  );
}
