"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ScanLine,
  MessageSquare,
  Search,
  BookOpen,
  LogOut,
  User,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { ProductMark } from "./ProductMark";
import { UserProfileModal } from "./UserProfileModal";

export function Navbar() {
  const pathname = usePathname();
  const { user, role, logout } = useAuth();
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  // Khi Staff đang ở màn /console -> Ẩn Navbar Customer để nhường toàn bộ giao diện cho Staff Console Shell
  if (pathname?.startsWith("/console") && role === "STAFF") {
    return null;
  }

  // Cấu hình Menu linh hoạt theo vai trò (Role-Based Navigation)
  // GUEST: Trang chủ | Trợ lý Chat | Knowledge Hub | Đăng nhập | Đăng ký
  // CUSTOMER: Trang chủ | Trợ lý Chat | Trung tâm hỗ trợ | Knowledge Hub | Hồ sơ
  const navItems =
    role === "CUSTOMER"
      ? [
          { name: "Trang chủ", href: "/", exact: true },
          { name: "Trợ lý Chat", href: "/chat", icon: MessageSquare },
          { name: "Trung tâm hỗ trợ", href: "/track-case", icon: Search },
          { name: "Knowledge Hub", href: "/#knowledge-hub", icon: BookOpen },
        ]
      : [
          { name: "Trang chủ", href: "/", exact: true },
          { name: "Trợ lý Chat", href: "/chat", icon: MessageSquare },
          { name: "Knowledge Hub", href: "/#knowledge-hub", icon: BookOpen },
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
              Bạn đang duyệt giao diện với tư cách xem trước (Staff Preview Mode).
            </span>
            <Link
              href="/console"
              className="inline-flex items-center gap-1 font-bold underline hover:text-[#1D4ED8]"
            >
              Quay lại Bàn Điều Phối <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo Brand */}
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2.5 group">
              <div className="w-8 h-8 rounded-[10px] bg-[#1E40AF] flex items-center justify-center text-white shadow-xs transition-transform group-hover:scale-105">
                <ProductMark className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="font-bold text-[16px] tracking-tight flex items-center gap-1 font-display text-[#0F172A]">
                  VF <span className="text-[#1E40AF] font-bold">Serv</span>
                </div>
                <div className="text-[9.5px] text-[#64748B] tracking-wider font-mono uppercase font-semibold">
                  VinFast EV Hub
                </div>
              </div>
            </Link>
          </div>

          {/* Navigation Links theo Role (Guest hoặc Customer) */}
          <nav className="hidden md:flex items-center space-x-1">
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
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Action: Auth / User Profile */}
          <div className="flex items-center gap-2">
            {user && role === "CUSTOMER" ? (
              /* Hồ sơ Customer */
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsProfileOpen(true)}
                  className="flex items-center gap-2 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] hover:border-slate-300 px-3 py-1 rounded-xl transition group text-left cursor-pointer"
                  title="Xem và chỉnh sửa hồ sơ xe & tài khoản"
                >
                  <div className="w-6 h-6 rounded-full bg-[#1E40AF] text-white flex items-center justify-center text-[11px] font-bold group-hover:scale-105 transition shrink-0">
                    <User className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex flex-col text-left">
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
                  title="Đăng xuất"
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
                  <span>Bàn điều phối (Console)</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ) : (
              /* Guest Actions */
              <div className="flex items-center gap-1.5">
                <Link
                  href="/login"
                  className="rounded-[10px] px-3 py-1.5 text-[12px] font-medium text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition"
                >
                  Đăng nhập
                </Link>
                <Link
                  href="/register"
                  className="inline-flex rounded-[10px] bg-[#1E40AF] hover:bg-[#1D4ED8] px-3 py-1.5 text-[12px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition"
                >
                  Đăng ký
                </Link>
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
