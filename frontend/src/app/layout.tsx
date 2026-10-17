import type { Metadata } from "next";
import { Navbar, Footer, AuthProvider } from "@/features/shared";
import "./globals.css";
import "./theme.css";
import { LocaleProvider } from "@/features/shared/context/LocaleContext";

import { ThemeProvider } from "@/features/shared/context/ThemeContext";

import { THEME_INIT } from "@/features/shared/utils/theme-init";

export const metadata: Metadata = {
  title: "VFServ — Dịch vụ & Điều phối Kỹ thuật Xe điện VinFast",
  description:
    "Hệ thống tiếp nhận, xử lý sự cố kỹ thuật và điều phối dịch vụ xe điện VinFast thông minh (VFServ).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{__html: THEME_INIT}} /></head>
      <body className="bg-[#F6F7F9] text-[#0F172A] flex flex-col min-h-screen antialiased">
        <LocaleProvider><ThemeProvider><AuthProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </AuthProvider></ThemeProvider></LocaleProvider>
      </body>
    </html>
  );
}
