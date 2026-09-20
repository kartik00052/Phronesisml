import type { Config } from "tailwindcss";

/**
 * Tailwind config for PhronesisML frontend.
 *
 * Theming is driven by CSS variables in `src/index.css` (Tailwind v4
 * `@theme`). This file exists for explicit content globs, safelisting and
 * legacy-tooling compatibility; no color values live here.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter Variable",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono Variable",
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
    },
  },
} satisfies Config;