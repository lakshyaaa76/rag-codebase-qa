import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Terminal palette
        terminal: {
          bg:       "#050A0E",   // matte black base
          panel:    "#0A1628",   // slightly lighter panel
          border:   "#1A2F4A",   // subtle border
          dim:      "#1E3A5F",   // dimmer border / hover
          cyan:     "#00D9FF",   // neon cyan — primary accent
          "cyan-dim": "#00A3C4", // dimmer cyan for hover states
          green:    "#39FF14",   // neon green — ready / success
          amber:    "#FFB800",   // amber — pending / warning
          red:      "#FF3B3B",   // red — failed / error
          text:     "#E2EBF0",   // primary text
          muted:    "#5A7A94",   // muted / secondary text
          code:     "#A8C8E8",   // code text
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Fira Code'", "Consolas", "monospace"],
      },
      animation: {
        "fade-in":    "fadeIn 0.3s ease forwards",
        "fade-up":    "fadeUp 0.35s ease forwards",
        "pulse-slow": "pulse 2.5s cubic-bezier(0.4,0,0.6,1) infinite",
        "blink":      "blink 1.2s step-end infinite",
        "scan":       "scan 3s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeUp: {
          "0%":   { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0" },
        },
        scan: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;