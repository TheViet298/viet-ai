import { ShieldAlert, PhoneCall } from "lucide-react";

interface EmergencyAlertBannerProps {
  visible: boolean;
}

export function EmergencyAlertBanner({ visible }: EmergencyAlertBannerProps) {
  if (!visible) return null;

  return (
    <div className="mb-4 bg-[#DC2626] text-white rounded-2xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] flex items-center justify-between animate-pulse">
      <div className="flex items-center gap-3">
        <ShieldAlert className="w-6 h-6 shrink-0 text-white" />
        <div>
          <div className="font-bold text-[14px]">
            CẢNH BÁO AN TOÀN KHẨN CẤP (CRITICAL)
          </div>
          <div className="text-[12px] sm:text-[13px] text-white/90">
            Nếu xe đang trên đường: Bật đèn khẩn cấp hazard, tấp vào lề an toàn và rời khỏi xe đứng sau hộ lan!
          </div>
        </div>
      </div>
      <a
        href="tel:1900232389"
        className="shrink-0 flex items-center gap-1.5 px-3.5 py-1.5 bg-white text-[#DC2626] font-bold rounded-[10px] text-[12px] sm:text-[13px] hover:bg-[#FEF2F2] transition-colors shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
      >
        <PhoneCall className="w-3.5 h-3.5" /> 1900-232389
      </a>
    </div>
  );
}
