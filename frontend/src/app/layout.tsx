import type { Metadata } from "next";
import { Navbar, Footer, AuthProvider } from "@/features/shared";
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
      <body className="bg-[#F6F7F9] text-[#0F172A] flex flex-col min-h-screen antialiased">
        <AuthProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
