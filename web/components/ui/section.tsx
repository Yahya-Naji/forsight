import * as React from "react";
import { cn } from "@/lib/utils";

// The console's recurring page furniture, which was being re-typed inline on
// every screen: an uppercase kicker, a display heading and a measure-limited
// lede. Repeating it by hand is how six pages ended up with five different
// heading sizes.

export function Kicker({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("text-[11.5px] font-semibold uppercase tracking-[2px] text-faint",
                            className)} {...props} />;
}

export function SectionHeading({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("font-display text-[22px] font-semibold tracking-tight mt-[7px] mb-[5px]",
                           className)} {...props} />;
}

export function Lede({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("max-w-[64ch] text-base leading-relaxed text-muted", className)} {...props} />;
}

export function SectionHead({ kicker, title, children, className }: {
  kicker?: React.ReactNode; title: React.ReactNode;
  children?: React.ReactNode; className?: string;
}) {
  return (
    <div className={cn("mb-3.5", className)}>
      {kicker && <Kicker>{kicker}</Kicker>}
      <SectionHeading>{title}</SectionHeading>
      {children && <Lede>{children}</Lede>}
    </div>
  );
}

/** The dark hero panel used on the overview, generate and engine screens. */
export function Aurora({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={cn("rounded-[20px] bg-aurora text-white", className)}
      style={{
        backgroundImage:
          "radial-gradient(900px 420px at 50% 130%,rgba(84,116,255,.55),rgba(84,116,255,0) 65%)," +
          "radial-gradient(500px 260px at 82% 120%,rgba(128,196,255,.35),rgba(128,196,255,0) 60%)",
      }}
      {...props}
    />
  );
}

/** A number with its label — the overview's stat tiles, on the dark panel. */
export function Stat({ value, label, tone = "default" }: {
  value: React.ReactNode; label: React.ReactNode; tone?: "default" | "warn";
}) {
  const warn = tone === "warn";
  return (
    <div className={cn("rounded-[14px] border px-[22px] py-3.5 text-center",
      warn ? "border-[rgba(255,183,77,.35)] bg-[rgba(255,183,77,.12)]"
           : "border-white/10 bg-white/[.06]")}>
      <div className={cn("font-display text-[28px] font-bold", warn && "text-[#FFC96B]")}>{value}</div>
      <div className={cn("mt-0.5 text-[11px]", warn ? "text-[#E8BE85]" : "text-[#9FB0E6]")}>{label}</div>
    </div>
  );
}
