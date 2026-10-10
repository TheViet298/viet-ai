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
} from "lucide-react";
import { useAuth, ProductMark, UserRole } from "@/features/shared";

export default function LoginPage() {
  const router = useRouter();
  const { login, loginDemo, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<"CUSTOMER" | "STAFF">("CUSTOMER");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const goToRoleHome = (role: UserRole) => {
    router.push(role === "STAFF" ? "/console" : "/chat");
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

  const handleQuickDemoLogin = async (role: "CUSTOMER" | "STAFF") => {
    setSubmitting(true);
    setErrorMessage("");
    try {
      const authenticated = await loginDemo(role);
      goToRoleHome(authenticated.role);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Tài khoản demo không khả dụng.");
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
                setIdentifier("staff@vinfast.vn");
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

          {/* Quick 1-Click Demo Box */}
          <div className="mt-4 rounded-xl border border-[#0D9488]/30 bg-[#F0FDFA] p-3 text-[12px]">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-[#0F172A] flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-[#0D9488]" /> Thử nghiệm nhanh (Demo):
              </span>
              <span className="text-[10px] text-[#64748B] uppercase tracking-wider font-semibold">1-click login</span>
            </div>
            <p className="mt-1 text-[11px] text-[#64748B]">
              Đăng nhập tài khoản mẫu để vào thẳng {activeTab === "STAFF" ? "Bàn điều phối (Console)" : "Trợ lý Chat"}:
            </p>
            <button
              type="button"
              onClick={() => handleQuickDemoLogin(activeTab)}
              disabled={submitting}
              className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] px-3 py-1.5 font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] text-[12px] transition"
            >
              <span>Vào ngay với vai trò {activeTab === "STAFF" ? "Kỹ thuật viên (Staff)" : "Chủ xe (Khách hàng)"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Divider */}
          <div className="my-4 flex items-center gap-3">
            <div className="h-px flex-1 bg-[#E2E8F0]" />
            <span className="text-[11px] uppercase tracking-wider text-[#64748B]">hoặc đăng nhập thủ công</span>
            <div className="h-px flex-1 bg-[#E2E8F0]" />
          </div>

          {/* Error notice */}
          {errorMessage && (
            <div className="mb-3 flex items-center gap-2 rounded-xl bg-[#FEF2F2] p-2.5 text-[12px] text-[#DC2626] border border-[#DC2626]/20">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-3">
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
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-3 text-[13px] text-[#0F172A] placeholder-[#64748B] focus:border-[#1E40AF] focus:outline-none"
                  placeholder="Nhập mật khẩu"
                />
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
