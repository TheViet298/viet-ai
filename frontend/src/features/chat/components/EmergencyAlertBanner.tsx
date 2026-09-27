import { ShieldAlert, PhoneCall } from "lucide-react";

interface EmergencyAlertBannerProps {
  visible: boolean;
}

export function EmergencyAlertBanner({ visible }: EmergencyAlertBannerProps) {
  if (!visible) return null;

  return (
    <div className="mb-4 bg-rose-600 text-white rounded-xl p-4 shadow-lg flex items-center justify-between animate-pulse">
      <div className="flex items-center gap-3">
        <ShieldAlert className="w-7 h-7 shrink-0 text-yellow-300" />
        <div>
          <div className="font-bold text-sm sm:text-base">
            CẢNH BÁO AN TOÀN KHẨN CẤP (CRITICAL)
          </div>
          <div className="text-xs sm:text-sm text-rose-100">
            Nếu xe đang trên cao tốc: Bật đèn khẩn cấp, tấp vào làn dừng khẩn cấp và rời khỏi xe đứng sau hộ lan an toàn!
          </div>
        </div>
      </div>
      <a
        href="tel:1900232389"
        className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-white text-rose-700 font-bold rounded-lg text-xs sm:text-sm hover:bg-rose-50 transition-colors shadow"
      >
        <PhoneCall className="w-4 h-4" /> 1900-232389
      </a>
    </div>
  );
}
