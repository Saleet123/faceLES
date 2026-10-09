import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#1769D2",
        bright: "#2688F0",
        deep: "#124B9B",
        navy: "#102347",
        muted: "#6880A3",
        page: "#F7FAFF",
        card: "#FFFFFF",
        soft: "#EDF5FF",
        line: "#DCE8F8",
        ok: "#20BD83",
        danger: "#EF5260",
        orange: "#C47A38",
        purple: "#7868EE",
      },
      fontFamily: {
        sans: ["Ubuntu", "Noto Sans", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
