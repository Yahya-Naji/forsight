import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// `pill` is the console's primary action shape and predates shadcn here — the
// generate and run controls are full-radius. It stays the default so the
// migration does not silently restyle every button on the site.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-sans font-semibold " +
  "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring " +
  "focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        pill: "rounded-full bg-accent text-white hover:bg-accent-deep",
        default: "rounded-md bg-accent text-white hover:bg-accent-deep",
        outline: "rounded-md border border-line bg-card text-ink-2 hover:bg-line-soft",
        ghost: "rounded-md text-muted hover:bg-line-soft hover:text-ink",
        quiet: "rounded-full border border-line bg-[#F8F9FD] text-ink-2 hover:bg-line-soft",
        destructive: "rounded-md bg-destructive text-white hover:opacity-90",
      },
      size: {
        default: "h-9 px-4 text-[13.5px]",
        sm: "h-8 px-3 text-sm",
        lg: "h-11 px-5 text-[14px]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "pill", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  });
Button.displayName = "Button";

export { Button, buttonVariants };
