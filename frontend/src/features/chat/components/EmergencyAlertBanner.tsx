import { PhoneCall, ShieldAlert } from "lucide-react";

interface EmergencyAlertBannerProps {
  visible: boolean;
}

export function EmergencyAlertBanner({ visible }: EmergencyAlertBannerProps) {
  if (!visible) return null;

  return (
    <div className="sticky top-[56px] z-40 w-full bg-[#DC2626] text-white shadow-md border-b border-red-700 animate-fadeIn">
      <div className="max-w-5xl mx-auto px-4 py-2 sm:py-2.5 flex items-center justify-between gap-3 min-h-[46px]">
        <div className="flex items-center gap-2.5 min-w-0">
          <ShieldAlert className="w-4 h-4 text-white shrink-0" />
          <div className="text-[12px] sm:text-[12.5px] leading-snug truncate">
            <strong className="font-bold text-white mr-1.5">Xe đang trên đường?</strong>
            <span className="text-red-100">
              Bật hazard, tấp lề an toàn, rời khỏi xe và đứng sau hộ lan.
            </span>
          </div>
        </div>

        <a
          href="tel:1900232389"
          className="shrink-0 flex items-center gap-1.5 px-3 py-1 bg-white text-[#DC2626] hover:bg-red-50 font-bold rounded-lg text-[11.5px] sm:text-[12px] transition active:scale-95 shadow-2xs whitespace-nowrap"
        >
          <PhoneCall className="w-3.5 h-3.5" />
          <span>1900-232389</span>
        </a>
      </div>
    </div>
  );
}
