import type { Metadata } from "next";
import { Navbar } from "@/features/shared";
import "./globals.css";

export const metadata: Metadata = {
  title: "VinFast ServiceFlow AI — Hệ thống Tiếp nhận & Điều phối Dịch vụ",
  description:
    "AI Agent tiếp nhận, làm rõ dữ kiện có ngữ cảnh, tra cứu cẩm nang kỹ thuật VinFast và hỗ trợ Reviewer điều phối sự cố xe điện.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="bg-slate-50 text-slate-900 flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
          Dự án VinFast ServiceFlow AI (VFO2O-18) — AI20K Build Phase Cohort 4
        </footer>
      </body>
    </html>
  );
}
