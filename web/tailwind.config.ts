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
        paper: "hsl(var(--paper))",
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--ink))" },
        line: { DEFAULT: "hsl(var(--line))", soft: "hsl(var(--line-soft))" },
        ink: { DEFAULT: "hsl(var(--ink))", 2: "hsl(var(--ink-2))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted))" },
        faint: "hsl(var(--faint))",
        ghost: "hsl(var(--ghost))",
        accent: {
          DEFAULT: "hsl(var(--accent))",
          deep: "hsl(var(--accent-deep))",
          wash: "hsl(var(--accent-wash))",
          foreground: "hsl(var(--card))",
        },
        navy: "hsl(var(--navy))",
        aurora: "hsl(var(--aurora))",

        // Semantic, and deliberately separate from the accent: evidence class,
        // gate status and signal strength must never be read as brand colour.
        amber: { ink: "hsl(var(--amber-ink))", bg: "hsl(var(--amber-bg))",
                 line: "hsl(var(--amber-line))", chip: "hsl(var(--amber-chip))" },
        green: { ink: "hsl(var(--green-ink))", bg: "hsl(var(--green-bg))",
                 line: "hsl(var(--green-line))", chip: "hsl(var(--green-chip))" },
        uae:    { DEFAULT: "hsl(var(--uae))", bg: "hsl(var(--uae-bg))" },
        global: { DEFAULT: "hsl(var(--global))", bg: "hsl(var(--global-bg))" },

        // shadcn's own contract, mapped onto the same surfaces
        background: "hsl(var(--paper))",
        foreground: "hsl(var(--ink))",
        border: "hsl(var(--line))",
        input: "hsl(var(--line))",
        ring: "hsl(var(--accent))",
        primary: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--card))" },
        secondary: { DEFAULT: "hsl(var(--line-soft))", foreground: "hsl(var(--ink-2))" },
        destructive: { DEFAULT: "hsl(var(--bad))", foreground: "hsl(var(--card))" },
        popover: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--ink))" },
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
