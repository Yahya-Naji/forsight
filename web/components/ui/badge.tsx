import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// Semantic first. Evidence class, tier, environment layer and gate status each
// mean something specific, and none of them is a brand colour — a reader must
// be able to tell Class A from Tier 1 from an open gate at a glance, so the
// variants below are the ontology rather than a generic set of greys.
const badgeVariants = cva(
  "inline-flex items-center rounded-[6px] px-2 py-[3px] text-2xs font-bold tracking-wide " +
  "whitespace-nowrap",
  {
    variants: {
      variant: {
        default:  "bg-line-soft text-ink-2",
        tier1:    "bg-navy text-white",
        tier:     "bg-line-soft text-muted",
        classA:   "bg-green-chip text-green-ink",
        classB:   "bg-accent-wash text-accent-deep",
        classC:   "bg-amber-chip text-amber-ink",
        classD:   "bg-line-soft text-muted",
        uae:      "bg-uae-bg text-uae",
        regional: "bg-[#FBEBDD] text-[#874A18]",
        global:   "bg-global-bg text-global",
        open:     "bg-amber-chip text-amber-ink tracking-[1px]",
        passed:   "bg-green-chip text-green-ink tracking-[1px]",
        neural:   "border border-[#C7D2F7] bg-accent-wash text-accent-deep font-mono font-normal",
        symbolic: "border border-[#D6DBEA] bg-[#EDEFF6] text-[#3A4468] font-mono font-normal",
        mono:     "border border-line bg-line-soft text-ink-2 font-mono font-normal",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
