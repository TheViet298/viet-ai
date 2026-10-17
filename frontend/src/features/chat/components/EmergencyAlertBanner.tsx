"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";

import { CheckCircle2, ChevronRight, PhoneCall, ShieldAlert } from "lucide-react";

interface EmergencyAlertBannerProps {
  visible: boolean;
  isDismissed?: boolean;
  onDismiss?: () => void;
  onRestore?: () => void;
  pending?: boolean;
  error?: string | null;
  canAcknowledge?: boolean;
}

export function EmergencyAlertBanner({
  visible,
  isDismissed = false,
  onDismiss,
  onRestore,
  pending = false,
  error,
  canAcknowledge = true,
}: EmergencyAlertBannerProps) {
  const { t } = useLocale();

  if (!visible) return null;

  const dismissed = isDismissed;

  const handleDismiss = () => {
    onDismiss?.();
  };

  const handleRestore = () => {
    onRestore?.();
  };

  // Trạng thái thu gọn nhỏ gọn (Compact Ribbon) sau khi khách đã an toàn
  if (dismissed) {
    return (
      <div className="sticky top-[56px] z-40 w-full bg-slate-900/95 backdrop-blur-md text-white shadow-sm border-b border-slate-800 transition-all duration-300 animate-fadeIn">
        <div className="max-w-5xl mx-auto px-4 py-1.5 flex items-center justify-between gap-3 text-[11.5px]">
          <div className="flex items-center gap-2 min-w-0">
            <span className="inline-flex items-center gap-1 font-semibold text-emerald-400 shrink-0">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {t("Đã xác nhận an toàn")}</span>
            <span className="text-slate-400 hidden sm:inline">•</span>
            <span className="text-slate-300 truncate hidden sm:inline">
              {t("Hồ sơ khẩn cấp vẫn đang được Cố vấn VinFast ưu tiên xử lý")}</span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleRestore}
              className="text-slate-400 hover:text-white text-[11px] underline underline-offset-2 transition"
            >
              {t("Xem hướng dẫn an toàn")}</button>
            <a
              href="tel:1900232389"
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-600/90 hover:bg-red-600 text-white rounded font-medium text-[11px] transition"
            >
              <PhoneCall className="w-3 h-3" />
              <span>1900-232389</span>
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Trạng thái khẩn cấp nổi bật đầy đủ (Full Emergency Banner)
  return (
    <div className="sticky top-[56px] z-40 w-full bg-[#DC2626] text-white shadow-md border-b border-red-700 animate-fadeIn">
      <div className="max-w-5xl mx-auto px-4 py-2 sm:py-2.5 flex items-center justify-between gap-3 min-h-[46px]">
        <div className="flex items-center gap-2.5 min-w-0">
          <ShieldAlert className="w-4 h-4 text-white shrink-0 animate-pulse" />
          <div className="text-[12px] sm:text-[12.5px] leading-snug truncate">
            <strong className="font-bold text-white mr-1.5">{t("Xe đang gặp sự cố?")}</strong>
            <span className="text-red-100">
              {t("Ưu tiên tới khu vực an toàn nếu có thể và gọi hotline cứu hộ.")}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            disabled={pending || !canAcknowledge}
            onClick={handleDismiss}
            className="flex items-center gap-1 px-2.5 py-1 bg-red-700/80 hover:bg-red-800 text-white rounded-lg text-[11px] font-medium border border-red-500/50 transition active:scale-95 whitespace-nowrap"
            title={t("Thu gọn cảnh báo nếu bạn đã ở vị trí an toàn")}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-red-200" />
            <span>{pending ? t("Đang lưu...") : t("Đã an toàn")}</span>
          </button>

          <a
            href="tel:1900232389"
            className="flex items-center gap-1.5 px-3 py-1 bg-white text-[#DC2626] hover:bg-red-50 font-bold rounded-lg text-[11.5px] sm:text-[12px] transition active:scale-95 shadow-2xs whitespace-nowrap"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>1900-232389</span>
          </a>
        </div>
      </div>
      {error && <p role="alert" className="px-4 pb-2 text-xs">{error}</p>}
    </div>
  );
}
