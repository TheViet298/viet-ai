"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  User,
  Car,
  Lock,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  ArrowLeft,
} from "lucide-react";
import { useAuth, ProductMark } from "@/features/shared";

const VEHICLES = ["VF8", "VF5", "VF3", "VF6", "VF7", "VF9", "e34"];

export default function RegisterPage() {
  const router = useRouter();
  const { registerCustomer } = useAuth();
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [vehicleModel, setVehicleModel] = useState("VF8");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const [submitting, setSubmitting] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !username.trim() || !password) {
      setErrorMessage("Vui lòng điền đầy đủ các thông tin bắt buộc.");
      return;
    }
    if (password.length < 8) {
      setErrorMessage("Mật khẩu cần có ít nhất 8 ký tự.");
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage("Mật khẩu xác nhận không khớp.");
      return;
    }

    setSubmitting(true);
    setErrorMessage("");

    try {
      await registerCustomer(username.trim(), password, {
        name: name.trim(),
        phone: username.trim(),
        vehicleModel,
      });
      router.push("/chat");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Không thể tạo tài khoản. Vui lòng thử lại.");
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
              Đăng ký tài khoản Khách hàng
            </h1>
            <p className="mt-1 text-[13px] text-[#64748B]">
              Tiếp nhận hỗ trợ kỹ thuật và theo dõi tiến độ hồ sơ xe của bạn
            </p>
          </div>

          {/* No-PII Safe Notice */}
          <div className="mt-4 rounded-xl border border-[#10B981]/30 bg-[#ECFDF5] p-3 text-[12px] text-[#0F172A]">
            <div className="flex items-center gap-1.5 font-bold text-[#0F172A]">
              <ShieldCheck className="h-4 w-4 text-[#10B981]" /> Cam kết bảo vệ quyền riêng tư &amp; No-PII
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-[#64748B]">
              Hệ thống chỉ sử dụng tên và số điện thoại để hỗ trợ kỹ thuật và xưng hô. Tuyệt đối không thu thập CCCD, giấy phép lái xe, số khung VIN thật hay biển số xe.
            </p>
          </div>

          {/* Error notice */}
          {errorMessage && (
            <div className="mt-3 flex items-center gap-2 rounded-xl bg-[#FEF2F2] p-2.5 text-[12px] text-[#DC2626] border border-[#DC2626]/20">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleRegister} className="mt-4 space-y-3">
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-1">
                Tên của bạn / Biệt danh xưng hô <span className="text-[#DC2626]">*</span>
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                  <User className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ví dụ: Anh Tuấn, Chị Mai"
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-3 text-[13px] text-[#0F172A] placeholder-[#64748B] focus:border-[#1E40AF] focus:outline-none"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-1">
                Số điện thoại / Tên đăng nhập <span className="text-[#DC2626]">*</span>
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                  <User className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="09xxxxxxxx hoặc tên tài khoản"
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-3 text-[13px] text-[#0F172A] placeholder-[#64748B] focus:border-[#1E40AF] focus:outline-none"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-1">
                Dòng xe VinFast bạn đang sử dụng
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                  <Car className="h-4 w-4" />
                </div>
                <select
                  value={vehicleModel}
                  onChange={(e) => setVehicleModel(e.target.value)}
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-3 text-[13px] text-[#0F172A] focus:border-[#1E40AF] focus:outline-none cursor-pointer"
                >
                  {VEHICLES.map((v) => (
                    <option key={v} value={v}>
                      VinFast {v}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-1">
                Mật khẩu <span className="text-[#DC2626]">*</span>
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Tối thiểu 8 ký tự"
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-3 text-[13px] text-[#0F172A] placeholder-[#64748B] focus:border-[#1E40AF] focus:outline-none"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-1">
                Xác nhận mật khẩu <span className="text-[#DC2626]">*</span>
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Nhập lại mật khẩu"
                  className="w-full rounded-[10px] border border-[#E2E8F0] bg-white py-2 pl-9 pr-3 text-[13px] text-[#0F172A] placeholder-[#64748B] focus:border-[#1E40AF] focus:outline-none"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] py-2 text-[13px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition"
            >
              <span>{submitting ? "Đang tạo tài khoản…" : "Hoàn tất đăng ký"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </form>

          {/* Footer link */}
          <div className="mt-5 border-t border-[#E2E8F0] pt-3 text-center text-[12px] text-[#64748B]">
            Đã có tài khoản?{" "}
            <Link href="/login" className="font-semibold text-[#1E40AF] hover:underline">
              Đăng nhập tại đây
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
