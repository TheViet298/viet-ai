"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  User,
  ShieldCheck,
  Lock,
  ArrowRight,
  Sparkles,
  Mail,
  AlertCircle,
  ArrowLeft,
  Eye,
  EyeOff,
} from "lucide-react";
import { useAuth, ProductMark, UserRole } from "@/features/shared";

export default function LoginPage() {
  const router = useRouter();
  const { login, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<"CUSTOMER" | "STAFF">("CUSTOMER");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [demoLoadingRole, setDemoLoadingRole] = useState<"STAFF" | "CUSTOMER" | null>(null);

  const goToRoleHome = (role: UserRole) => {
    router.push(role === "STAFF" ? "/console" : "/chat");
  };

  const handleQuickDemoLogin = async (username: string, role: "CUSTOMER" | "STAFF") => {
    setDemoLoadingRole(role);
    setActiveTab(role);
    setErrorMessage("");
    try {
      const demoPassword = process.env.NEXT_PUBLIC_DEMO_PASSWORD || "DemoSecret@2026!Sec";
      const authenticated = await login(username, demoPassword);
      goToRoleHome(authenticated.role);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Không thể đăng nhập bằng tài khoản Demo. Vui lòng kiểm tra lại backend/database."
      );
    } finally {
      setDemoLoadingRole(null);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setErrorMessage("Vui lòng nhập tên đăng nhập và mật khẩu.");
      return;
    }

    setSubmitting(true);
    setErrorMessage("");
    try {
      const authenticated = await login(identifier, password);
      if (authenticated.role !== activeTab) {
        logout();
        throw new Error(`Tài khoản này không thuộc vai trò ${activeTab === "STAFF" ? "Staff" : "Customer"}.`);
      }
      goToRoleHome(authenticated.role);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Không thể đăng nhập. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[#F6F7F9] px-4 py-12">
      {/* Nút quay lại trang chủ tiện lợi */}
      <Link
        href="/"
        className="absolute top-5 left-5 sm:top-6 sm:left-6 inline-flex items-center gap-1.5 text-[13px] font-medium text-slate-500 hover:text-slate-900 bg-white/90 hover:bg-white border border-slate-200/90 hover:border-slate-300 px-3.5 py-1.5 rounded-full shadow-2xs transition-all duration-200 hover:-translate-x-0.5 group z-10"
      >
        <ArrowLeft className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-700 transition-colors" />
        <span>Về trang chủ</span>
      </Link>

      <div className="w-full max-w-md">
        {/* Brand Card - Bo góc 16px, shadow rất nhẹ */}
        <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 sm:p-7 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          {/* Logo */}
          <div className="text-center">
            <Link href="/" className="inline-flex items-center gap-2 group">
              <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[#1E40AF] text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                <ProductMark className="h-5 w-5 text-white" />
              </div>
              <span className="text-[19px] font-bold tracking-tight text-[#0F172A] font-display">
                VF <span className="text-[#1E40AF]">Serv</span>
              </span>
            </Link>
            <h1 className="mt-3 text-[20px] font-bold text-[#0F172A]">
              Đăng nhập hệ thống
            </h1>
            <p className="mt-1 text-[13px] text-[#64748B]">
              Chọn vai trò phù hợp để bắt đầu phiên tiếp nhận hoặc điều phối
            </p>
          </div>

          {/* Role Tab Selector - pill buttons */}
          <div className="mt-5 grid grid-cols-2 gap-1 rounded-full bg-[#F6F7F9] p-1 text-[12px] font-semibold border border-[#E2E8F0]">
            <button
              type="button"
              onClick={() => {
                setActiveTab("CUSTOMER");
                setErrorMessage("");
              }}
              className={`flex items-center justify-center gap-1.5 rounded-full py-1.5 transition ${activeTab === "CUSTOMER"
                ? "bg-white text-[#1E40AF] shadow-[0_1px_2px_rgba(0,0,0,0.04)] font-bold"
                : "text-[#64748B] hover:text-[#0F172A]"
                }`}
            >
              <User className="h-3.5 w-3.5" />
              <span>Khách hàng</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setActiveTab("STAFF");
                setErrorMessage("");
              }}
              className={`flex items-center justify-center gap-1.5 rounded-full py-1.5 transition ${activeTab === "STAFF"
                ? "bg-white text-[#6D5BD0] shadow-[0_1px_2px_rgba(0,0,0,0.04)] font-bold"
                : "text-[#64748B] hover:text-[#0F172A]"
                }`}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Kỹ thuật viên (Staff)</span>
            </button>
          </div>

          {/* 1-Click Demo Quick Access cho Giám khảo / Thẩm định viên */}
          <div className="mt-4 rounded-xl border border-amber-200/90 bg-gradient-to-b from-amber-50/90 to-amber-50/30 p-3.5 shadow-2xs">
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-1.5 text-[12px] font-bold text-amber-900">
                <Sparkles className="h-4 w-4 text-amber-600 shrink-0" />
                <span>Trải nghiệm nhanh Demo Giám khảo</span>
              </div>
              <span className="text-[10px] font-semibold bg-amber-200/80 text-amber-900 px-2 py-0.5 rounded-full uppercase tracking-wider">
                1-Click
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {/* Nút vào vai Staff Demo */}
              <button
                type="button"
                disabled={submitting || demoLoadingRole !== null}
                onClick={() => handleQuickDemoLogin("demo.staff@vinfast.vn", "STAFF")}
                className="flex items-center justify-between gap-2 rounded-lg border border-purple-200/80 bg-white hover:bg-purple-50/70 p-2 text-left shadow-2xs transition-all hover:border-purple-300 hover:shadow-xs group cursor-pointer disabled:opacity-60"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-purple-100 text-purple-700 group-hover:bg-[#6D5BD0] group-hover:text-white transition-colors">
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[11.5px] font-bold text-slate-800 group-hover:text-purple-900 truncate">
                      Vào vai Staff Demo
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      Console điều phối 9 ca
                    </div>
                  </div>
                </div>
                {demoLoadingRole === "STAFF" ? (
                  <span className="text-[10px] text-purple-600 font-bold animate-pulse">…</span>
                ) : (
                  <ArrowRight className="h-3.5 w-3.5 text-purple-400 group-hover:text-[#6D5BD0] group-hover:translate-x-0.5 transition-all shrink-0" />
                )}
              </button>

              {/* Nút vào vai Khách hàng Demo */}
              <button
                type="button"
                disabled={submitting || demoLoadingRole !== null}
                onClick={() => handleQuickDemoLogin("demo.customer@vinfast.vn", "CUSTOMER")}
                className="flex items-center justify-between gap-2 rounded-lg border border-blue-200/80 bg-white hover:bg-blue-50/70 p-2 text-left shadow-2xs transition-all hover:border-blue-300 hover:shadow-xs group cursor-pointer disabled:opacity-60"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-100 text-blue-700 group-hover:bg-[#1E40AF] group-hover:text-white transition-colors">
                    <User className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[11.5px] font-bold text-slate-800 group-hover:text-blue-900 truncate">
                      Vào vai Khách Demo
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      Chat & Tra cứu hồ sơ
                    </div>
                  </div>
                </div>
                {demoLoadingRole === "CUSTOMER" ? (
                  <span className="text-[10px] text-blue-600 font-bold animate-pulse">…</span>
                ) : (
                  <ArrowRight className="h-3.5 w-3.5 text-blue-400 group-hover:text-[#1E40AF] group-hover:translate-x-0.5 transition-all shrink-0" />
                )}
              </button>
            </div>
          </div>

          {/* Divider */}
          <div className="relative my-4 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200"></div>
            </div>
            <span className="relative bg-white px-2.5 text-[10.5px] font-semibold text-slate-400 uppercase tracking-wider">
              Hoặc đăng nhập thủ công
            </span>
          </div>

          {/* Error notice */}
          {errorMessage && (
            <div className="mt-3 mb-1 flex items-center gap-2 rounded-xl bg-[#FEF2F2] p-2.5 text-[12px] text-[#DC2626] border border-[#DC2626]/20">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="mt-4 space-y-3.5">
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-1">
                {activeTab === "STAFF" ? "Tài khoản Staff nội bộ" : "Số điện thoại / Tên đăng nhập"}
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                  {activeTab === "STAFF" ? <Mail className="h-4 w-4" /> : <User className="h-4 w-4" />}
                </div>
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-3 text-[13px] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#1E40AF] focus:outline-none"
                  autoComplete="username"
                  placeholder={
                    activeTab === "STAFF"
                      ? "staff_service"
                      : "Nhập số điện thoại hoặc usernam"
                  }
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-1">
                Mật khẩu
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-10 text-[13px] text-[#0F172A] placeholder-[#64748B] focus:border-[#1E40AF] focus:outline-none"
                  placeholder="Nhập mật khẩu"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-[#64748B] hover:text-[#0F172A] transition-colors focus:outline-none"
                  title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] py-2 text-[13px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition"
            >
              <span>{submitting ? "Đang xác thực…" : "Đăng nhập"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </form>

          {/* Footer note */}
          <div className="mt-5 border-t border-[#E2E8F0] pt-3 text-center text-[12px] text-[#64748B]">
            {activeTab === "CUSTOMER" ? (
              <p>
                Chưa có tài khoản?{" "}
                <Link href="/register" className="font-semibold text-[#1E40AF] hover:underline">
                  Đăng ký khách hàng mới
                </Link>
              </p>
            ) : (
              <p className="text-[11px] text-[#64748B]">
                Tài khoản Staff do quản trị viên nội bộ cấp. Không mở đăng ký công khai.
              </p>
            )}
          </div>
        </div>

        {/* Safe notice */}
        <div className="mt-3 text-center text-[11px] text-[#64748B]">
          Chế độ No-PII Safe Mode • Không lưu thông tin CCCD hay tài khoản ngân hàng.
        </div>
      </div>
    </div>
  );
}
