"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";

import { useState, useRef, useEffect } from "react";
import {
  MapPin,
  RotateCcw,
  AlertTriangle,
  AlertCircle,
  X,
} from "lucide-react";
import { searchManualAreas, resolveManualArea } from "../constants/manualAreas";
import { UserLocationState } from "../types";

interface LocationConsentCardProps {
  reason?: string;
  modal?: boolean;
  locationState: UserLocationState;
  isLocating: boolean;
  isMapOpen: boolean;
  onConsentGps: () => void;
  onManualLocation: (areaText: string) => void;
  onSkip: () => void;
  onToggleMap: () => void;
  onResetLocation: () => void;
  onStopSharing: () => void;
}

export function LocationConsentCard({
  reason = "Tìm điểm dịch vụ gần bạn.",
  modal = false,
  locationState,
  isLocating,
  isMapOpen,
  onConsentGps,
  onManualLocation,
  onSkip,
  onToggleMap,
  onResetLocation,
  onStopSharing,
}: LocationConsentCardProps) {
  const { t } = useLocale();
  const dialogRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement | null;
    dialogRef.current?.querySelector<HTMLElement>("button, input")?.focus();
    return () => previous?.focus();
  }, [modal]);
  const [isManualInputMode, setIsManualInputMode] = useState(false);
  const [manualText, setManualText] = useState("");

  const matchingAreas = searchManualAreas(manualText);

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualText.trim()) return;
    onManualLocation(manualText.trim());
    setIsManualInputMode(false);
  };

  // 1. Khi ĐÃ CÓ VỊ TRÍ (GPS hoặc Nhập tay): Thanh mỏng 1 dòng dính trên ô nhập
  if (locationState.status === "CONSENTED" || (locationState.status === "MANUAL" && !locationState.errorCode)) {
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
              ? t("Đã ghi nhận vị trí (GPS)")
              : `${t("Khu vực:")} ${locationState.label}`}
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
            {isMapOpen ? t("Ẩn bản đồ") : t("Xem bản đồ ›")}
          </button>
          {locationState.status === "CONSENTED" && <><button type="button" onClick={() => { onResetLocation(); setIsManualInputMode(true); }} className="text-blue-700 font-semibold">Nhập khu vực</button><button type="button" onClick={onStopSharing} className="text-red-700 font-semibold">Dừng chia sẻ</button></>}
          <button
            type="button"
            onClick={onResetLocation}
            className="text-slate-400 hover:text-slate-600 p-0.5 rounded transition"
            title={t("Đổi lại vị trí")}
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
        <span className="text-slate-400">{t("Chưa chia sẻ vị trí")}</span>
        <button
          type="button"
          onClick={onResetLocation}
          className="text-[#1E40AF] font-semibold hover:underline flex items-center gap-1"
        >
          <MapPin className="w-3 h-3" />
          <span>{t("Chia sẻ vị trí")}</span>
        </button>
      </div>
    );
  }

  // 3. Khi CÓ LỖI TỪ CHỐI / TIMEOUT / SIGNAL: Hiện thông báo lỗi cụ thể kèm form nhập tay
  const hasGeoError = Boolean(locationState.errorCode && locationState.errorCode !== "ACCURACY_LOW");

  return (
    <div className={modal ? "fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" : ""}>
    <div ref={dialogRef} role={modal ? "dialog" : undefined} aria-modal={modal || undefined} aria-label="Chọn vị trí để tìm địa điểm"
      onKeyDown={(event) => {
        if (event.key === "Escape") onSkip();
        if (event.key === "Tab" && modal) {
          const nodes = dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])');
          if (!nodes?.length) return;
          const first = nodes[0], last = nodes[nodes.length - 1];
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
      }}
      className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 text-sm space-y-3">
      <h2 className="font-semibold text-slate-900">{reason}</h2>
      <p className="text-slate-600">Quý khách muốn dùng vị trí hiện tại hay nhập khu vực? Chỉ dùng để tìm kiếm; chưa chia sẻ với hồ sơ.</p>
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
        <div className="space-y-1.5">
          <form onSubmit={handleManualSubmit} className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              aria-label="Khu vực hoặc địa chỉ nhập tay"
              autoComplete="off"
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              placeholder="Nhập km cao tốc, trạm sạc hoặc khu vực..."
              className="min-h-10 min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-2.5 py-1 text-[11.5px] text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1E40AF]"
              autoFocus
            />
            <button
              type="submit"
              disabled={!manualText.trim()}
              className="min-h-10 px-3 py-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[11px] font-semibold disabled:opacity-50 transition active:scale-95 shrink-0"
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
                aria-label="Bỏ qua"
              title="Bỏ qua"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </form>
          {manualText.trim() && !resolveManualArea(manualText) && <p className="text-[11px] text-slate-600">Vẫn có thể xác nhận địa chỉ này bằng chữ. Chọn khu vực gợi ý để có tâm tham chiếu, không phải GPS.</p>}
          <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
            <span className="text-[10.5px] text-slate-400">Gợi ý nhanh:</span>
            {matchingAreas.map(({ id, label: area }) => (
              <button
                key={id}
                type="button"
                onClick={() => {
                  setManualText(area);
                  onManualLocation(area);
                  setIsManualInputMode(false);
                }}
                className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-600 hover:border-blue-300 hover:text-[#1E40AF] text-[10.5px] transition"
              >
                {area}
              </button>
            ))}
          </div>
        </div>

      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-slate-800 text-[12px]">
            <MapPin className="w-3.5 h-3.5 text-[#1E40AF] shrink-0" />
            <span className="font-medium">{t("Chia sẻ vị trí để tìm điểm hỗ trợ gần nhất")}</span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={isLocating}
              onClick={onConsentGps}
              className="min-h-10 px-3 py-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[11px] font-semibold transition active:scale-95 disabled:opacity-50 shadow-2xs"
            >
              {isLocating ? t("Đang định vị...") : t("Dùng vị trí hiện tại")}
            </button>
            <button
              type="button"
              onClick={() => { onResetLocation(); setIsManualInputMode(true); }}
              className="min-h-10 px-3 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-medium transition active:scale-95 shadow-2xs"
            >
              {t("Nhập khu vực")}</button>
            <button
              type="button"
              onClick={onSkip}
              className="min-h-10 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
              aria-label={t("Bỏ qua")}
              title={t("Bỏ qua")}
            >
              {t("Bỏ qua ✕")}</button>
          </div>
        </div>
      )}
    </div>
    </div>
  );
}
