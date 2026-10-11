"use client";

import { useState } from "react";
import {
  MapPin,
  RotateCcw,
  AlertTriangle,
  AlertCircle,
  X,
} from "lucide-react";
import { UserLocationState } from "../types";

interface LocationConsentCardProps {
  locationState: UserLocationState;
  isLocating: boolean;
  isMapOpen: boolean;
  onConsentGps: () => void;
  onManualLocation: (areaText: string) => void;
  onSkip: () => void;
  onToggleMap: () => void;
  onResetLocation: () => void;
}

export function LocationConsentCard({
  locationState,
  isLocating,
  isMapOpen,
  onConsentGps,
  onManualLocation,
  onSkip,
  onToggleMap,
  onResetLocation,
}: LocationConsentCardProps) {
  const [isManualInputMode, setIsManualInputMode] = useState(false);
  const [manualText, setManualText] = useState("");

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualText.trim()) return;
    onManualLocation(manualText.trim());
    setIsManualInputMode(false);
  };

  // 1. Khi ĐÃ CÓ VỊ TRÍ (GPS hoặc Nhập tay): Thanh mỏng 1 dòng dính trên ô nhập
  if (locationState.status === "CONSENTED" || locationState.status === "MANUAL") {
    const isLowAccuracy =
      locationState.status === "CONSENTED" &&
      typeof locationState.accuracy === "number" &&
      locationState.accuracy > 500;

    return (
      <div className="px-3.5 py-1.5 bg-blue-50/80 border-t border-blue-100 flex items-center justify-between text-[11.5px] animate-fadeIn">
        <div className="flex items-center gap-1.5 min-w-0">
          <MapPin className="w-3.5 h-3.5 text-[#1E40AF] shrink-0" />
          <span className="text-slate-700 truncate">
            {locationState.source === "BROWSER_GPS"
              ? "Đã ghi nhận vị trí (GPS)"
              : `Khu vực: ${locationState.label}`}
          </span>
          {isLowAccuracy && (
            <span
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-semibold shrink-0 cursor-help"
              title={`Độ chính xác ước lượng sai số ±${Math.round(locationState.accuracy!)}m. Anh/chị có thể nhập tay để chính xác hơn.`}
            >
              <AlertTriangle className="w-3 h-3 text-amber-600" />
              <span>Ước lượng ±{Math.round(locationState.accuracy!)}m</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onToggleMap}
            className="text-[#1E40AF] font-bold hover:underline"
          >
            {isMapOpen ? "Ẩn bản đồ" : "Xem bản đồ ›"}
          </button>
          <button
            type="button"
            onClick={onResetLocation}
            className="text-slate-400 hover:text-slate-600 p-0.5 rounded transition"
            title="Đổi lại vị trí"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>
    );
  }

  // 2. Khi BỎ QUA: Thu nhỏ thành chip "Chia sẻ vị trí" ở góc, không biến mất hẳn
  if (locationState.status === "NOT_SHARED") {
    return (
      <div className="px-3.5 py-1 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between text-[11px] animate-fadeIn">
        <span className="text-slate-400">Chưa chia sẻ vị trí</span>
        <button
          type="button"
          onClick={onResetLocation}
          className="text-[#1E40AF] font-semibold hover:underline flex items-center gap-1"
        >
          <MapPin className="w-3 h-3" />
          <span>Chia sẻ vị trí</span>
        </button>
      </div>
    );
  }

  // 3. Khi CÓ LỖI TỪ CHỐI / TIMEOUT / SIGNAL: Hiện thông báo lỗi cụ thể kèm form nhập tay
  const hasGeoError = Boolean(locationState.errorCode && locationState.errorCode !== "ACCURACY_LOW");

  return (
    <div className="px-3.5 py-2 bg-blue-50/90 border-t border-blue-200/70 text-[12px] animate-fadeIn space-y-1.5">
      {hasGeoError && (
        <div className="flex items-start gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-[11px]">
          <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">
              {locationState.errorCode === "PERMISSION_DENIED"
                ? "Trình duyệt đã chặn quyền vị trí."
                : locationState.errorCode === "TIMEOUT"
                ? "Quá thời gian chờ tín hiệu GPS (> 8s)."
                : locationState.errorCode === "UNSUPPORTED"
                ? "Thiết bị hoặc kết nối không hỗ trợ GPS."
                : "Tín hiệu GPS không khả dụng (vùng sóng yếu/trong hầm)."}
            </span>{" "}
            <span>Vui lòng nhập tên khu vực hoặc trạm sạc bên dưới:</span>
          </div>
        </div>
      )}

      {isManualInputMode || hasGeoError ? (
        <form onSubmit={handleManualSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            placeholder="Nhập km cao tốc, trạm sạc hoặc khu vực..."
            className="flex-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-[11.5px] text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1E40AF]"
            autoFocus
          />
          <button
            type="submit"
            disabled={!manualText.trim()}
            className="px-3 py-1 rounded-lg bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[11px] font-semibold disabled:opacity-50 transition active:scale-95 shrink-0"
          >
            Xác nhận
          </button>
          {!hasGeoError && (
            <button
              type="button"
              onClick={() => setIsManualInputMode(false)}
              className="text-slate-500 hover:text-slate-700 text-[11px] px-1 shrink-0"
            >
              Hủy
            </button>
          )}
          {hasGeoError && (
            <button
              type="button"
              onClick={onSkip}
              className="text-slate-400 hover:text-slate-600 text-[11px] px-1 shrink-0"
              title="Bỏ qua"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-slate-800 text-[12px]">
            <MapPin className="w-3.5 h-3.5 text-[#1E40AF] shrink-0" />
            <span className="font-medium">Chia sẻ vị trí để tìm điểm hỗ trợ gần nhất</span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={isLocating}
              onClick={onConsentGps}
              className="px-2.5 py-1 rounded-lg bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[11px] font-semibold transition active:scale-95 disabled:opacity-50 shadow-2xs"
            >
              {isLocating ? "Đang định vị..." : "Dùng vị trí hiện tại"}
            </button>
            <button
              type="button"
              disabled={isLocating}
              onClick={() => setIsManualInputMode(true)}
              className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-medium transition active:scale-95 shadow-2xs"
            >
              Nhập khu vực
            </button>
            <button
              type="button"
              disabled={isLocating}
              onClick={onSkip}
              className="text-slate-400 hover:text-slate-600 text-[11px] px-1 transition"
              title="Bỏ qua"
            >
              Bỏ qua ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
