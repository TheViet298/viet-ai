"use client";

import { useLocale } from "@/features/shared/context/LocaleContext";

import { useAuth } from "@/features/shared";
import { StaffGuardGate, StaffConsoleShell } from "@/features/console";
import { Loader2 } from "lucide-react";

export default function ConsolePage() {
  const { t } = useLocale();
  const { role, isReady } = useAuth();

  // Đang tải phiên đăng nhập từ localStorage -> Hiển thị skeleton nhẹ tránh giật lag UI
  if (!isReady) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3 text-[#64748B]">
        <Loader2 className="w-6 h-6 animate-spin text-[#1E40AF]" />
        <span className="text-[13px] font-medium">{t("Đang xác thực cổng nghiệp vụ...")}</span>
      </div>
    );
  }

  // Khách vãng lai (Guest) hoặc Khách hàng (Customer) tự gõ /console -> Hiện Staff Guard Gate / Access Denied
  if (role !== "STAFF") {
    return <StaffGuardGate />;
  }

  // Staff đã xác thực thành công -> Mở toàn bộ Staff Console Shell riêng biệt
  return <StaffConsoleShell />;
}
