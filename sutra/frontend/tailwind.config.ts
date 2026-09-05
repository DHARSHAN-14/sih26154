import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0f172a",
          raised:  "#1e293b",
          overlay: "#162032",
        },
        accent: {
          DEFAULT: "#3b82f6",
          bright:  "#60a5fa",
          dim:     "#1d4ed8",
          muted:   "#1e3a8a",
        },
        verified: {
          DEFAULT: "#10b981",
          dim:     "#064e3b",
        },
        lock: {
          DEFAULT: "#f59e0b",
          dim:     "#78350f",
        },
        classify: {
          unclassified: "#16a34a",
          restricted:   "#ca8a04",
          confidential: "#ea580c",
          secret:       "#dc2626",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow":  "spin 2s linear infinite",
        "fade-in":    "fadeIn 0.25s ease-out",
        "slide-in":   "slideIn 0.2s ease-out",
        "slide-up":   "slideUp 0.25s ease-out",
        "shimmer":    "shimmer 1.6s linear infinite",
        "toast-in":   "toastIn 0.3s cubic-bezier(0.21,1.02,0.73,1)",
        "toast-out":  "toastOut 0.2s ease-in forwards",
        "scale-in":   "scaleIn 0.15s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%":   { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        toastIn: {
          "0%":   { opacity: "0", transform: "translateX(calc(100% + 16px))" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        toastOut: {
          "0%":   { opacity: "1", transform: "translateX(0)" },
          "100%": { opacity: "0", transform: "translateX(calc(100% + 16px))" },
        },
        scaleIn: {
          "0%":   { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.175, 0.885, 0.32, 1.275)",
      },
    },
  },
  plugins: [],
} satisfies Config;
