"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ScanLine,
  MessageSquare,
  ShieldCheck,
  Search,
  LogOut,
  ChevronDown,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const pathname = usePathname();
  const { user, role, loginAs, logout } = useAuth();
  const [showRoleMenu, setShowRoleMenu] = useState(false);

  const navItems = [
    {
      name: "Trang chủ",
      href: "/",
      exact: true,
    },
    {
      name: "Trợ lý Chat",
      href: "/chat",
      icon: MessageSquare,
    },
    {
      name: "Tra cứu sự cố",
      href: "/track-case",
      icon: Search,
    },
    {
      name: "Bàn điều phối",
      href: "/console",
      icon: ShieldCheck,
      badge: "Staff",
    },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#1A1F26] bg-[#0F1115] text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo Brand */}
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2 group">
              <div className="w-8 h-8 rounded-[10px] bg-[#1E40AF] flex items-center justify-center text-[#10B981] shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-transform group-hover:scale-105">
                <ScanLine className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="font-bold text-[15px] tracking-tight flex items-center gap-1.5 font-display text-white">
                  ServiceFlow <span className="text-[#0D9488] font-medium">AI</span>
                </div>
                <div className="text-[10px] text-[#64748B] tracking-wider font-mono uppercase">
                  EV Support Hub
                </div>
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = item.exact
                ? pathname === item.href
                : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[10px] text-[13px] font-medium transition-colors ${
                    isActive
                      ? "bg-[#1E40AF] text-white font-semibold"
                      : "text-[#94A3B8] hover:bg-white/5 hover:text-white"
                  }`}
                >
                  {Icon && <Icon className="w-3.5 h-3.5" />}
                  <span>{item.name}</span>
                  {item.badge && (
                    <span className="rounded-full bg-[#6D5BD0]/20 px-1.5 py-0.2 text-[10px] font-bold text-[#A78BFA] border border-[#6D5BD0]/30">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Right Action: Role Switcher & Auth */}
          <div className="flex items-center gap-2">
            {/* Quick Demo Switcher Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowRoleMenu(!showRoleMenu)}
                className="flex items-center gap-1.5 rounded-[10px] border border-white/10 bg-white/5 px-2.5 py-1.5 text-[12px] font-medium text-slate-200 hover:bg-white/10 hover:text-white transition"
                title="Chuyển vai trò thử nghiệm demo"
              >
                <Sparkles className="w-3 h-3 text-[#0D9488]" />
                <span className="hidden sm:inline text-[#64748B]">Role:</span>
                <span className="font-semibold text-white">
                  {role === "STAFF"
                    ? "Staff KTV"
                    : role === "CUSTOMER"
                    ? "Chủ xe"
                    : "Guest"}
                </span>
                <ChevronDown className="w-3 h-3 opacity-60" />
              </button>

              {showRoleMenu && (
                <div
                  className="absolute right-0 mt-2 w-52 rounded-2xl border border-[#1A1F26] bg-[#0F1115] p-2 shadow-[0_1px_2px_rgba(0,0,0,0.04)] text-[12px] z-50"
                  onMouseLeave={() => setShowRoleMenu(false)}
                >
                  <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-[#64748B] border-b border-[#1A1F26]">
                    Chuyển vai trò (Demo)
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      loginAs("CUSTOMER");
                      setShowRoleMenu(false);
                    }}
                    className={`mt-1 flex w-full items-center justify-between rounded-[10px] px-2 py-1.5 text-left transition ${
                      role === "CUSTOMER"
                        ? "bg-[#1E40AF] text-white font-semibold"
                        : "text-[#94A3B8] hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <span>Khách hàng (VF8)</span>
                    {role === "CUSTOMER" && <span className="h-1.5 w-1.5 rounded-full bg-[#10B981]" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      loginAs("STAFF");
                      setShowRoleMenu(false);
                    }}
                    className={`flex w-full items-center justify-between rounded-[10px] px-2 py-1.5 text-left transition ${
                      role === "STAFF"
                        ? "bg-[#1E40AF] text-white font-semibold"
                        : "text-[#94A3B8] hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <span>Kỹ thuật viên (Staff)</span>
                    {role === "STAFF" && <span className="h-1.5 w-1.5 rounded-full bg-[#6D5BD0]" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      setShowRoleMenu(false);
                    }}
                    className={`flex w-full items-center justify-between rounded-[10px] px-2 py-1.5 text-left transition ${
                      role === "GUEST"
                        ? "bg-[#1E40AF] text-white font-semibold"
                        : "text-[#64748B] hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <span>Khách vãng lai (Guest)</span>
                  </button>
                </div>
              )}
            </div>

            {/* Auth Buttons */}
            {user ? (
              <div className="flex items-center gap-2">
                <div className="hidden lg:flex flex-col text-right">
                  <span className="text-[12px] font-semibold leading-tight text-white">{user.name}</span>
                  <span className="text-[11px] text-[#64748B] font-mono">
                    {user.role === "CUSTOMER" ? `${user.vehicleModel || "VF8"}` : "Reviewer"}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-[10px] p-1.5 text-[#64748B] hover:bg-white/5 hover:text-[#DC2626] transition"
                  title="Đăng xuất"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5">
                <Link
                  href="/login"
                  className="rounded-[10px] px-3 py-1.5 text-[12px] font-medium text-[#94A3B8] hover:bg-white/5 hover:text-white transition"
                >
                  Đăng nhập
                </Link>
                <Link
                  href="/register"
                  className="hidden sm:inline-flex rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] px-3 py-1.5 text-[12px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition"
                >
                  Đăng ký
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
