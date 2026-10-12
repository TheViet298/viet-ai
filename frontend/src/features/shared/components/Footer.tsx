"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PhoneCall } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { ProductMark } from "./ProductMark";

export function Footer() {
  const pathname = usePathname();
  const { role } = useAuth();

  // Ẩn Footer khi Staff đang ở màn /console hoặc màn đăng nhập/đăng ký
  if (
    (pathname?.startsWith("/console") && role === "STAFF") ||
    pathname === "/login" ||
    pathname === "/register"
  ) {
    return null;
  }
  return (
    <footer className="border-t border-slate-200/80 bg-white text-slate-500 py-4 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-3 text-[12px]">
        {/* Left: Brand & Copyright */}
        <div className="flex items-center gap-2">
          <Link href="/" className="inline-flex items-center gap-1.5 font-bold text-slate-900 font-display">
            <div className="flex h-5 w-5 items-center justify-center rounded-md bg-[#1E40AF] text-white">
              <ProductMark className="h-3.5 w-3.5 text-white" />
            </div>
            <span>VF<span className="text-[#1E40AF]">Serv</span></span>
          </Link>
          <span className="text-slate-300">|</span>
          <span className="text-slate-400">© 2026 VinFast EV Support</span>
        </div>

        {/* Center: Policy & Quick Links */}
        <div className="flex items-center gap-4 text-slate-500 flex-wrap justify-center">
          <Link href="/chat" className="hover:text-[#1E40AF] transition">
            Trợ lý Chat
          </Link>
          <Link href="/track-case" className="hover:text-[#1E40AF] transition">
            Yêu cầu của tôi
          </Link>
          <Link href="/#knowledge-hub" className="hover:text-[#1E40AF] transition">
            Cẩm nang kỹ thuật
          </Link>
          <a
            href="https://vinfastauto.com/vn_vi/chinh-sach-bao-mat-thong-tin"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[#1E40AF] transition"
          >
            Chính sách bảo mật
          </a>
        </div>

        {/* Right: Hotline */}
        <div className="flex items-center gap-2">
          <span className="text-slate-400 hidden md:inline">Cứu hộ khẩn cấp:</span>
          <a
            href="tel:1900232389"
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 hover:bg-red-100 text-red-700 px-2.5 py-1 text-[11.5px] font-semibold transition"
          >
            <PhoneCall className="h-3 w-3 text-red-600" />
            <span>1900-232389</span>
          </a>
        </div>
      </div>
    </footer>
  );
}
