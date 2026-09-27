import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        vinfast: {
          blue: "#1E40AF",
          "blue-dark": "#1E3A8A",
          "blue-light": "#3B82F6",
          green: "#10B981",
          red: "#EF4444",
          amber: "#F59E0B",
          gray: "#F8FAFC",
        },
      },
    },
  },
  plugins: [],
};

export default config;
