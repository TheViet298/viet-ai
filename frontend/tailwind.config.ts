import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        service: {
          // Neutral
          ink: "#0F1115",             // Dark background / navbar dark
          deep: "#1A1F26",            // Dark hover
          mist: "#F6F7F9",            // Neutral light background
          text: "#0F172A",            // Primary text
          muted: "#64748B",           // Secondary text
          line: "#E2E8F0",            // Border

          // Primary (thương hiệu)
          primary: "#1E40AF",         // Deep Indigo Blue
          "primary-dark": "#1E3A8A",    // hover
          "primary-light": "#EFF3FC",   // nhạt

          // Accent phụ (đang xử lý / AI đang nói)
          teal: "#0D9488",            // Teal
          "teal-dark": "#0F766E",
          "teal-light": "#F0FDFA",    // nhạt

          // Success / Đã duyệt
          mint: "#10B981",            // Emerald
          "mint-dark": "#059669",
          "mint-light": "#ECFDF5",    // nhạt

          // Review (Staff Reviewing)
          review: "#6D5BD0",
          "review-dark": "#4C3A9E",
          "review-light": "#F4F2FF",

          // Warning / Needs Information
          warning: "#D97706",         // Amber
          "warning-dark": "#B45309",
          "warning-light": "#FFFBEB", // nhạt

          // Critical / Khẩn cấp
          critical: "#DC2626",        // Rose Red
          "critical-dark": "#B91C1C",
          "critical-light": "#FEF2F2",// nhạt
        },
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
      borderRadius: {
        card: "16px",
        btn: "10px",
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(0, 0, 0, 0.04)",
      },
      fontSize: {
        caption: ["11px", { lineHeight: "16px", letterSpacing: "0.06em" }],
        body: ["13px", { lineHeight: "20px" }],
      },
    },
  },
  plugins: [],
};

export default config;
