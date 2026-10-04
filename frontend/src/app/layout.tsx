import type { Metadata } from "next";
import { Navbar, Footer, AuthProvider } from "@/features/shared";
import "./globals.css";

export const metadata: Metadata = {
  title: "VF Serv — Dịch vụ & Điều phối Kỹ thuật Xe điện VinFast",
  description:
    "Hệ thống tiếp nhận, xử lý sự cố kỹ thuật và điều phối dịch vụ xe điện VinFast thông minh (VF Serv).",
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
