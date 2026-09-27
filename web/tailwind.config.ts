import type { Config } from "tailwindcss";

// The theme is the existing design system, not shadcn's default.
//
// shadcn ships a slate/zinc palette with generous radii that reads as the house
// style of every AI-built dashboard — which is the look this console was
// explicitly redesigned away from. So the tokens below are the ones already in
// globals.css: the same paper, ink, accent and semantic colours the exported
// reports and the engine screen use. Components are shadcn; the identity stays
// ours, and a report and the console still look like one product.

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // --- the console palette (hsl vars declared in globals.css) ---
        paper: "hsl(var(--paper-hsl))",
        card: { DEFAULT: "hsl(var(--card-hsl))", foreground: "hsl(var(--ink-hsl))" },
        line: { DEFAULT: "hsl(var(--line-hsl))", soft: "hsl(var(--line-soft-hsl))" },
        ink: { DEFAULT: "hsl(var(--ink-hsl))", 2: "hsl(var(--ink-2-hsl))" },
        muted: { DEFAULT: "hsl(var(--muted-hsl))", foreground: "hsl(var(--muted-hsl))" },
        faint: "hsl(var(--faint-hsl))",
        ghost: "hsl(var(--ghost-hsl))",
        accent: {
          DEFAULT: "hsl(var(--accent-hsl))",
          deep: "hsl(var(--accent-deep-hsl))",
          wash: "hsl(var(--accent-wash-hsl))",
          foreground: "hsl(var(--card-hsl))",
        },
        navy: "hsl(var(--navy-hsl))",
        aurora: "hsl(var(--aurora-hsl))",

        // Semantic, and deliberately separate from the accent: evidence class,
        // gate status and signal strength must never be read as brand colour.
        amber: { ink: "hsl(var(--amber-ink-hsl))", bg: "hsl(var(--amber-bg-hsl))",
                 line: "hsl(var(--amber-line-hsl))", chip: "hsl(var(--amber-chip-hsl))" },
        green: { ink: "hsl(var(--green-ink-hsl))", bg: "hsl(var(--green-bg-hsl))",
                 line: "hsl(var(--green-line-hsl))", chip: "hsl(var(--green-chip-hsl))" },
        uae:    { DEFAULT: "hsl(var(--uae-hsl))", bg: "hsl(var(--uae-bg-hsl))" },
        global: { DEFAULT: "hsl(var(--global-hsl))", bg: "hsl(var(--global-bg-hsl))" },

        // shadcn's own contract, mapped onto the same surfaces
        background: "hsl(var(--paper-hsl))",
        foreground: "hsl(var(--ink-hsl))",
        border: "hsl(var(--line-hsl))",
        input: "hsl(var(--line-hsl))",
        ring: "hsl(var(--accent-hsl))",
        primary: { DEFAULT: "hsl(var(--accent-hsl))", foreground: "hsl(var(--card-hsl))" },
        secondary: { DEFAULT: "hsl(var(--line-soft-hsl))", foreground: "hsl(var(--ink-2-hsl))" },
        destructive: { DEFAULT: "hsl(var(--bad-hsl))", foreground: "hsl(var(--card-hsl))" },
        popover: { DEFAULT: "hsl(var(--card-hsl))", foreground: "hsl(var(--ink-hsl))" },
      },
      borderRadius: {
        // 14px is the console's card radius; shadcn's default 0.5rem is the
        // tell-tale of the stock theme.
        lg: "var(--radius)",
        md: "calc(var(--radius) - 4px)",
        sm: "calc(var(--radius) - 8px)",
      },
      fontFamily: {
        sans: ["'Instrument Sans'", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "'Instrument Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        // The console reads at 12–14px; Tailwind's defaults are a step larger
        // and would reflow every table.
        "2xs": ["10.5px", { lineHeight: "1.45" }],
        xs: ["11.5px", { lineHeight: "1.5" }],
        sm: ["12.5px", { lineHeight: "1.55" }],
        base: ["13.5px", { lineHeight: "1.6" }],
      },
      keyframes: {
        tick: { "0%": { transform: "translateX(0)" }, "100%": { transform: "translateX(-50%)" } },
      },
      animation: { tick: "tick 40s linear infinite" },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
