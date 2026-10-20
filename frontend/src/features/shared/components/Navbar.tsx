"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ScanLine,
  MessageSquare,
  Search,
  BookOpen,
  LayoutDashboard,
  LogOut,
  User,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { ProductMark } from "./ProductMark";
import { UserProfileModal } from "./UserProfileModal";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageSwitch } from "./LanguageSwitch";

export function Navbar() {
  const { t } = useLocale();
  const pathname = usePathname();
  const { user, role, logout } = useAuth();
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  // Trang giới thiệu có header riêng; Staff Console dùng shell riêng.
  if (pathname === "/project-overview" || (pathname?.startsWith("/console") && role === "STAFF")) {
    return null;
  }

  // Cấu hình Menu linh hoạt theo vai trò (Role-Based Navigation)
  // GUEST: Trang chủ | Trợ lý Chat | Knowledge Hub | Đăng nhập | Đăng ký
  // CUSTOMER: Trang chủ | Trợ lý Chat | Trung tâm hỗ trợ | Knowledge Hub | Hồ sơ
  const navItems =
    role === "CUSTOMER"
      ? [
          { name: t("Trang chủ"), href: "/", exact: true },
          { name: t("Trợ lý Chat"), href: "/chat", icon: MessageSquare },
          { name: t("Trung tâm hỗ trợ"), href: "/track-case", icon: Search },
          { name: t("Cẩm nang"), href: "/#knowledge-hub", icon: BookOpen },
          { name: t("Tổng quan"), href: "/project-overview", icon: LayoutDashboard },
        ]
      : [
          { name: t("Trang chủ"), href: "/", exact: true },
          { name: t("Trợ lý Chat"), href: "/chat", icon: MessageSquare },
          { name: t("Cẩm nang"), href: "/#knowledge-hub", icon: BookOpen },
          { name: t("Tổng quan"), href: "/project-overview", icon: LayoutDashboard },
        ];

  const isAuthPage = pathname === "/login" || pathname === "/register";

  return (
    <header
      className={`sticky top-0 z-50 w-full border-b border-[#E2E8F0] bg-white/95 backdrop-blur-md text-[#0F172A] shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-all duration-300 ease-in-out ${
        isAuthPage
          ? "-translate-y-full opacity-0 pointer-events-none h-0 overflow-hidden border-b-0"
          : "translate-y-0 opacity-100 h-14"
      }`}
    >
      {/* Banner nhỏ thông báo khi Staff đang ở chế độ Customer Preview */}
      {role === "STAFF" && (
        <div className="bg-[#EFF3FC] border-b border-[#1E40AF]/20 px-4 py-1 text-[11px] font-medium text-[#1E40AF] flex items-center justify-between">
          <div className="mx-auto max-w-6xl w-full flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-[#1E40AF]" />
              {t("Bạn đang duyệt giao diện với tư cách xem trước (Staff Preview Mode).")}</span>
            <Link
              href="/console"
              className="inline-flex items-center gap-1 font-bold underline hover:text-[#1D4ED8]"
            >
              {t("Quay lại Bàn Điều Phối")}<ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo Brand */}
          <div className="flex items-center space-x-3">
            <Link href="/" aria-label="VFServ" className="flex items-center space-x-2.5 group">
              <div className="w-8 h-8 rounded-[10px] bg-[#1E40AF] flex items-center justify-center text-white shadow-xs transition-transform group-hover:scale-105">
                <ProductMark className="w-4 h-4 text-white" />
              </div>
              <div className="hidden sm:block">
                <div className="font-bold text-[16px] tracking-tight flex items-center font-display text-[#0F172A] gap-2">
                  <span>VF<span className="text-[#1E40AF] font-bold">Serv</span></span>
                  {user?.isDemo && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-700 border border-amber-500/30 tracking-normal">
                      DEMO
                    </span>
                  )}
                </div>
                <div className="hidden sm:block whitespace-nowrap text-[9.5px] text-[#64748B] tracking-wider font-mono uppercase font-semibold">
                  VinFast EV Hub
                </div>
              </div>
            </Link>
          </div>

          {/* Navigation Links theo Role (Guest hoặc Customer) */}
          <nav className="hidden lg:flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = item.exact
                ? pathname === item.href
                : pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[10px] text-[13px] font-medium transition-colors ${
                    isActive
                      ? "bg-[#EFF3FC] text-[#1E40AF] font-semibold border border-[#1E40AF]/20"
                      : "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
                  }`}
                >
                  {Icon && <Icon className="w-3.5 h-3.5" />}
                  <span className="whitespace-nowrap">{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Action: Auth / User Profile */}
          <div className="flex items-center gap-1 sm:gap-2">
            <LanguageSwitch /><ThemeToggle />
            {user && role === "CUSTOMER" ? (
              /* Hồ sơ Customer */
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsProfileOpen(true)}
                  className="flex items-center gap-2 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] hover:border-slate-300 px-2 sm:px-3 py-1 rounded-xl transition group text-left cursor-pointer"
                  aria-label={t("Xem và chỉnh sửa hồ sơ xe & tài khoản")}
                  title={t("Xem và chỉnh sửa hồ sơ xe & tài khoản")}
                >
                  <div className="w-6 h-6 rounded-full bg-[#1E40AF] text-white flex items-center justify-center text-[11px] font-bold group-hover:scale-105 transition shrink-0">
                    <User className="w-3.5 h-3.5" />
                  </div>
                  <div className="hidden sm:flex flex-col text-left">
                    <span className="text-[12px] font-semibold leading-tight text-[#0F172A] group-hover:text-[#1E40AF] transition">
                      {user.name}
                    </span>
                    <span className="text-[10px] text-[#1E40AF] font-mono font-medium">
                      {user.vehicleModel || "VF8"}
                    </span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={logout}
                  className="rounded-[10px] p-1.5 text-[#64748B] hover:bg-[#FEE2E2] hover:text-[#DC2626] transition"
                  title={t("Đăng xuất")}
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : role === "STAFF" ? (
              /* Staff đang xem Customer Preview */
              <div className="flex items-center gap-2">
                <Link
                  href="/console"
                  className="inline-flex items-center gap-1.5 rounded-[10px] bg-[#1E40AF] hover:bg-[#1D4ED8] px-3 py-1.5 text-[12px] font-semibold text-white transition shadow-sm"
                >
                  <span>{t("Bàn điều phối (Console)")}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ) : (
              /* Guest Actions */
              <div className="flex items-center gap-1.5">
                <Link
                  href="/login"
                  className="whitespace-nowrap rounded-[10px] px-2 sm:px-3 py-1.5 text-[12px] font-medium text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition"
                >
                  {t("Đăng nhập")}</Link>
                <Link
                  href="/register"
                  className="inline-flex whitespace-nowrap rounded-[10px] bg-[#1E40AF] hover:bg-[#1D4ED8] px-2 sm:px-3 py-1.5 text-[12px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition"
                >
                  {t("Đăng ký")}</Link>
              </div>
            )}
          </div>
        </div>
      </div>

      <UserProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
      />
    </header>
  );
}
