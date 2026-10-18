"use client";

import { useLocale } from "@/features/shared/context/LocaleContext";

import Link from "next/link";
import { ShieldAlert, ArrowLeft, KeyRound, Lock } from "lucide-react";
import { useAuth } from "@/features/shared";

export function StaffGuardGate() {
<<<<<<< HEAD
  const { t } = useLocale();
  const router = useRouter();
=======
>>>>>>> backup-gps-local-final
  const { role } = useAuth();

  const returnHref = role === "CUSTOMER" ? "/track-case" : "/";
  const returnLabel = role === "CUSTOMER" ? "Quay lại Trung tâm hỗ trợ" : "Quay lại Trang chủ";

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="max-w-md w-full bg-white border border-[#E2E8F0] rounded-3xl p-6 sm:p-8 shadow-xl text-center space-y-6 animate-in fade-in zoom-in-95 duration-200">
        {/* Icon Lock Badge */}
        <div className="mx-auto w-16 h-16 rounded-2xl bg-[#FEF2F2] border border-[#DC2626]/20 flex items-center justify-center text-[#DC2626] shadow-sm">
          <ShieldAlert className="w-8 h-8" />
        </div>

        {/* Header Text */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]">
            <Lock className="w-3 h-3 text-[#64748B]" /> {t("Cổng Nghiệp Vụ Giới Hạn")}
          </div>
          <h1 className="text-xl font-semibold text-[#0F172A] tracking-tight">
            {t("Khu Vực Bàn Điều Phối (Staff Portal)")}
          </h1>
          <p className="text-[13px] text-[#64748B] leading-relaxed">
            {t("Hàng đợi kỹ thuật và thông tin hồ sơ sự cố chỉ dành riêng cho Cố vấn Dịch vụ và Kỹ thuật viên VinFast được phân quyền.")}
          </p>
        </div>

        {/* Current Role Notice */}
        <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-2xl p-3.5 text-[12px] text-[#475569] flex items-center justify-center gap-2">
          <span>{t("Vai trò hiện tại của bạn:")}</span>
          <span className="font-semibold text-[#0F172A] px-2 py-0.5 rounded-lg bg-white border border-[#CBD5E1]">
            {t(role === "CUSTOMER" ? "Chủ xe (Customer)" : "Guest")}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3 pt-2">
          <Link
            href="/login"
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-4 py-3 text-[13px] font-semibold text-white shadow-md transition-all group"
          >
            <KeyRound className="w-4 h-4 text-[#A5B4FC] group-hover:rotate-12 transition-transform" />
            <span>{t("Đăng nhập Tài khoản Điều phối (Staff)")}</span>
          </Link>

          {/* Nút 2: Quay lại trang phù hợp */}
          <Link
            href={returnHref}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F8FAFC] px-4 py-2.5 text-[13px] font-medium text-[#475569] transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>{t(returnLabel)}</span>
          </Link>
        </div>

        {/* Secondary note */}
        <div className="pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
          {t("Liên hệ quản trị viên nội bộ VinFast nếu bạn chưa được cấp quyền truy cập.")}
        </div>
      </div>
    </div>
  );
}
