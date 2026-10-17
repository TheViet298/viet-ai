"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";

import { useState, useMemo, useEffect } from "react";
import {
  MapPin,
  Navigation,
  PhoneCall,
  X,
  Maximize2,
  Minimize2,
  ExternalLink,
  ShieldAlert,
  BatteryCharging,
  Wrench,
  Car,
  Compass,
  CheckCircle2,
  Info,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from "lucide-react";
import { ServicePointSeed, UserLocationState } from "../types";
import {
  calculateHaversineDistanceKm,
  formatDistanceKm,
  MAX_SUPPORT_RADIUS_KM,
} from "../utils/distance";

interface ServiceMapPanelProps {
  isOpen: boolean;
  onClose: () => void;
  locationState: UserLocationState;
  servicePoints: ServicePointSeed[];
  selectedPointId: string | null;
  onSelectPoint: (id: string) => void;
  suggestedCategory?: "ALL" | "EXPRESSWAY_RESCUE" | "CHARGING_STATION" | "SERVICE_WORKSHOP";
  isMobileModal?: boolean;
}

interface EnrichedServicePoint extends ServicePointSeed {
  distKm: number;
  distText: string;
}

export function ServiceMapPanel({
  isOpen,
  onClose,
  locationState,
  servicePoints,
  selectedPointId,
  onSelectPoint,
  suggestedCategory = "ALL",
  isMobileModal = false,
}: ServiceMapPanelProps) {
  const { t, language } = useLocale();
  const [filterType, setFilterType] = useState<string>("ALL");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showMorePoints, setShowMorePoints] = useState(false);
  const [activePopoverId, setActivePopoverId] = useState<string | null>(null);

  // Tự động chọn chip lọc theo ngữ cảnh sự cố (khi chat phát hiện loại lỗi)
  useEffect(() => {
    if (suggestedCategory && suggestedCategory !== "ALL") {
      setFilterType(suggestedCategory);
    }
  }, [suggestedCategory]);

  // Vị trí khách hàng (GPS thật hoặc vị trí tham chiếu)
  const userCoord = useMemo(() => {
    if (locationState.coords) {
      return locationState.coords;
    }
    // Vị trí tham chiếu mặc định nếu khách chưa chia sẻ GPS
    return { lat: 20.9889, lng: 105.9449 };
  }, [locationState.coords]);

  const hasRealGps = locationState.status === "CONSENTED" && Boolean(locationState.coords);

  // 1. Tính khoảng cách thực tế bằng công thức Haversine và sắp xếp điểm gần nhất lên đầu
  const enrichedPoints: EnrichedServicePoint[] = useMemo(() => {
    return servicePoints
      .map((sp) => {
        const distKm = calculateHaversineDistanceKm(userCoord, sp.coords);
        return {
          ...sp,
          distKm,
          distText: formatDistanceKm(distKm),
        };
      })
      .sort((a, b) => a.distKm - b.distKm);
  }, [servicePoints, userCoord]);

  // 2. Lọc theo danh mục chip được chọn
  const filteredPoints = useMemo(() => {
    if (filterType === "ALL") return enrichedPoints;
    return enrichedPoints.filter((sp) => sp.type === filterType);
  }, [filterType, enrichedPoints]);

  // Điểm gần nhất trong danh mục đang chọn
  const nearestPoint = filteredPoints[0] || null;

  // Kiểm tra ngưỡng "quá xa" (> 50 km) theo yêu cầu
  const isNearestTooFar = Boolean(
    hasRealGps && nearestPoint && nearestPoint.distKm > MAX_SUPPORT_RADIUS_KM
  );

  // Điểm đang được chọn hiển thị chi tiết (hoặc điểm gần nhất)
  const activePoint = useMemo(() => {
    if (selectedPointId) {
      return enrichedPoints.find((sp) => sp.id === selectedPointId) || nearestPoint;
    }
    return nearestPoint;
  }, [selectedPointId, enrichedPoints, nearestPoint]);

  // Điểm còn lại khi hiển thị 1 điểm gần nhất
  const remainingPoints = useMemo(() => {
    if (!nearestPoint) return [];
    return filteredPoints.filter((p) => p.id !== nearestPoint.id);
  }, [filteredPoints, nearestPoint]);

  // 3. Tính toán Bounding Box chính xác để bản đồ vừa khít vị trí khách và điểm gần nhất
  const mapBounds = useMemo(() => {
    // Các điểm nằm trong bán kính gần để đưa vào khung nhìn bản đồ
    const nearbyPoints = enrichedPoints.filter((p) => p.distKm <= MAX_SUPPORT_RADIUS_KM);

    let lats = [userCoord.lat];
    let lngs = [userCoord.lng];

    if (!isNearestTooFar && nearbyPoints.length > 0) {
      nearbyPoints.forEach((p) => {
        lats.push(p.coords.lat);
        lngs.push(p.coords.lng);
      });
    }

    let minLat = Math.min(...lats);
    let maxLat = Math.max(...lats);
    let minLng = Math.min(...lngs);
    let maxLng = Math.max(...lngs);

    // Bổ sung padding tỷ lệ để các ghim không bị tràn sát viền mép bản đồ
    const latSpan = Math.max(maxLat - minLat, 0.035);
    const lngSpan = Math.max(maxLng - minLng, 0.045);

    const padLat = latSpan * 0.28;
    const padLng = lngSpan * 0.28;

    return {
      minLat: minLat - padLat,
      maxLat: maxLat + padLat,
      minLng: minLng - padLng,
      maxLng: maxLng + padLng,
    };
  }, [userCoord, enrichedPoints, isNearestTooFar]);

  // URL nhúng OpenStreetMap căn vừa Bounding Box thực tế (không dùng marker tĩnh mặc định của OSM)
  const osmEmbedUrl = useMemo(() => {
    const { minLat, maxLat, minLng, maxLng } = mapBounds;
    return `https://www.openstreetmap.org/export/embed.html?bbox=${minLng}%2C${minLat}%2C${maxLng}%2C${maxLat}&layer=mapnik`;
  }, [mapBounds]);

  // Tính phần trăm tọa độ để cắm Ghim tương tác trực tiếp lên bản đồ
  const getMarkerPosition = (lat: number, lng: number) => {
    const { minLat, maxLat, minLng, maxLng } = mapBounds;
    const x = ((lng - minLng) / (maxLng - minLng)) * 100;
    const y = (1 - (lat - minLat) / (maxLat - minLat)) * 100;
    return {
      left: `${Math.min(Math.max(x, 8), 92)}%`,
      top: `${Math.min(Math.max(y, 10), 90)}%`,
    };
  };

  if (!isOpen) return null;

  const renderContent = () => (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden animate-fadeIn">
      {/* ─────────────────────────────────────────────────────────────
          1. HEADER THANH ĐIỀU KHIỂN BẢN ĐỒ (RÕ RÀNG, KHÔNG BỊ CHE)
      ───────────────────────────────────────────────────────────── */}
      <div className="px-4 py-3 bg-slate-50/95 border-b border-slate-200/80 flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-[#1E40AF] text-white flex items-center justify-center shrink-0 shadow-2xs">
            <Compass className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <h3 className="font-bold text-[13.5px] text-slate-900 truncate">
              {t("Bản đồ Điểm hỗ trợ & Trạm dịch vụ")}</h3>
            <p className="text-[11px] text-slate-500 truncate">
              {locationState.source === "BROWSER_GPS"
                ? t("📍 Đã ghi nhận vị trí của bạn (GPS)")
                : locationState.status === "MANUAL"
                ? `📍 ${t("Khu vực:")} ${locationState.label}`
                : t("Chưa chia sẻ vị trí")}
            </p>
          </div>
        </div>

        {/* Right Window Controls */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-200/60 transition hidden sm:inline-flex"
            title={isFullscreen ? t("Thu nhỏ lại cạnh chat") : t("Toàn màn hình")}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
            title={t("Đóng bản đồ")}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. VÙNG BẢN ĐỒ TƯƠNG TÁC (~45% CHIỀU CAO PANEL ĐỂ THẺ ĐẦU HIỆN ĐỦ NÚT)
      ───────────────────────────────────────────────────────────── */}
      <div className="relative w-full h-[45%] min-h-[240px] shrink-0 bg-slate-100 border-b border-slate-200 overflow-hidden">
        {/* OpenStreetMap Tile Layer Canvas */}
        {hasRealGps && <iframe
          title="OpenStreetMap Viewport"
          src={osmEmbedUrl}
          className="w-full h-full border-none opacity-90 filter contrast-[1.05]"
          loading="lazy"
        />}
        {!hasRealGps && <p className="p-6 text-sm text-slate-600">{t("Anh/chị có thể chia sẻ GPS hoặc tra cứu khu vực đã nhập trên ứng dụng VinFast.")}</p>}

        {/* ─────────────────────────────────────────────────────────────
            LỚP GHIM TƯƠNG TÁC (INTERACTIVE CAR-WEB PINS)
        ───────────────────────────────────────────────────────────── */}
        <div className="absolute inset-0 pointer-events-none">
          {/* A. GHIM VỊ TRÍ XE KHÁCH HÀNG (USER GPS BEACON) */}
          {hasRealGps && (
            <div
              className="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-auto z-20"
              style={getMarkerPosition(userCoord.lat, userCoord.lng)}
            >
              <div className="relative flex flex-col items-center group cursor-pointer">
                {/* Sóng radar tỏa nhẹ (tuân thủ prefers-reduced-motion) */}
                <span className="absolute -inset-2 rounded-full bg-blue-500/30 animate-ping motion-reduce:animate-none" />

                {/* Vòng tròn ghim trung tâm */}
                <div className="relative w-7 h-7 rounded-full bg-[#1E40AF] text-white flex items-center justify-center border-2 border-white shadow-md">
                  <Car className="w-3.5 h-3.5 text-white" />
                </div>

                {/* Nhãn gắn trực tiếp vào ghim */}
                <div className="mt-1 px-2 py-0.5 rounded-md bg-slate-900/85 backdrop-blur-xs text-white text-[10px] font-semibold whitespace-nowrap shadow-xs">
                  {t("Xe của bạn")}</div>
              </div>
            </div>
          )}

          {/* B. GHIM CÁC ĐIỂM HỖ TRỢ TRONG KHU VỰC */}
          {enrichedPoints
            .filter((p) => p.distKm <= MAX_SUPPORT_RADIUS_KM)
            .map((point) => {
              const isSelected = activePoint?.id === point.id;
              const isNearest = nearestPoint?.id === point.id;
              const isRescue = point.type === "EXPRESSWAY_RESCUE";
              const isCharging = point.type === "CHARGING_STATION";
              const isFilteredOut = filterType !== "ALL" && point.type !== filterType;

              return (
                <div
                  key={point.id}
                  className={`absolute -translate-x-1/2 -translate-y-1/2 transition-all duration-300 ${
                    isFilteredOut
                      ? "opacity-25 grayscale scale-90 pointer-events-none z-10"
                      : "opacity-100 pointer-events-auto z-20"
                  }`}
                  style={getMarkerPosition(point.coords.lat, point.coords.lng)}
                >
                  <div
                    onClick={() => {
                      if (!isFilteredOut) {
                        onSelectPoint(point.id);
                        setActivePopoverId(point.id);
                      }
                    }}
                    className={`relative flex flex-col items-center group cursor-pointer transition-transform ${
                      !isFilteredOut ? "hover:scale-110" : ""
                    }`}
                  >
                    {/* Viền sáng nổi bật nếu là điểm phù hợp nhất thuộc nhóm lọc hoặc đang chọn */}
                    {!isFilteredOut && (isSelected || isNearest) && (
                      <span className="absolute -inset-1.5 rounded-full bg-[#1E40AF]/25 ring-2 ring-[#1E40AF] shadow-sm animate-pulse" />
                    )}

                    {/* Icon Ghim theo loại chuẩn Automotive */}
                    <div
                      className={`relative w-8 h-8 rounded-full text-white flex items-center justify-center border-2 border-white shadow-md transition ${
                        isRescue
                          ? "bg-red-600"
                          : isCharging
                          ? "bg-sky-600"
                          : "bg-emerald-600"
                      }`}
                    >
                      {isRescue ? (
                        <ShieldAlert className="w-4 h-4 text-white" />
                      ) : isCharging ? (
                        <BatteryCharging className="w-4 h-4 text-white" />
                      ) : (
                        <Wrench className="w-4 h-4 text-white" />
                      )}
                    </div>

                    {/* Tag tên & khoảng cách gắn với ghim */}
                    <div className="mt-1 px-2 py-0.5 rounded-md bg-white/95 border border-slate-200/90 text-slate-800 text-[10px] font-bold whitespace-nowrap shadow-xs flex items-center gap-1">
                      <span>{point.distText}</span>
                    </div>
                  </div>
                </div>
              );
            })}
        </div>

        {/* ─────────────────────────────────────────────────────────────
            POPOVER CARD KHI BẤM VÀO GHIM (HOẶC ĐIỂM ĐANG CHỌN)
        ───────────────────────────────────────────────────────────── */}
        {activePoint && activePopoverId === activePoint.id && (
          <div className="absolute top-3 left-3 right-3 sm:right-auto sm:max-w-sm z-30 animate-fadeIn">
            <div className="p-3 bg-white/95 backdrop-blur-md rounded-2xl border border-slate-200/90 shadow-lg text-[12px] space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  {activePoint.type === "EXPRESSWAY_RESCUE" ? (
                    <span className="px-2 py-0.5 rounded-md font-bold text-[10px] bg-red-100 text-red-700 uppercase">
                      {t("🚨 Cứu hộ 24/7")}</span>
                  ) : activePoint.type === "CHARGING_STATION" ? (
                    <span className="px-2 py-0.5 rounded-md font-bold text-[10px] bg-blue-100 text-[#1E40AF] uppercase">
                      {t("⚡ Trạm sạc Siêu Nhanh")}</span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-md font-bold text-[10px] bg-emerald-100 text-emerald-800 uppercase">
                      {t("🔧 Xưởng dịch vụ 3S")}</span>
                  )}
                  <span className="font-mono text-[11px] font-bold text-slate-700">
                    {activePoint.distText}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => setActivePopoverId(null)}
                  className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <div>
                <h4 className="font-bold text-[13px] text-slate-900 leading-snug">
                  {activePoint.name}
                </h4>
                <p className="text-[11.5px] text-slate-500 mt-0.5 leading-relaxed line-clamp-2">
                  {activePoint.address}
                </p>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                <a
                  href={`https://maps.google.com/?q=${encodeURIComponent(activePoint.address)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-[#1E40AF] hover:underline"
                >
                  <Navigation className="w-3.5 h-3.5" />
                  <span>{t("Chỉ đường Maps")}</span>
                </a>

                <a
                  href={`tel:${activePoint.hotline.replace(/-/g, "")}`}
                  className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-[11px] font-bold text-white transition ${
                    activePoint.type === "EXPRESSWAY_RESCUE"
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-[#1E40AF] hover:bg-[#1D4ED8]"
                  }`}
                >
                  <PhoneCall className="w-3 h-3" />
                  <span>{activePoint.hotline}</span>
                </a>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. DANH SÁCH BÊN DƯỚI: 1 ĐIỂM GẦN NHẤT + NÚT XEM THÊM
      ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-h-0 bg-slate-50/60">
        {/* Thanh Bộ Lọc Phân Loại (Semantic Filter Pills) */}
        <div className="p-2.5 border-b border-slate-200/80 bg-white flex items-center gap-1.5 overflow-x-auto shrink-0">
          <button
            type="button"
            onClick={() => setFilterType("ALL")}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition shrink-0 ${
              filterType === "ALL"
                ? "bg-[#1E40AF] text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {t("Tất cả (")}{enrichedPoints.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType("CHARGING_STATION")}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition shrink-0 flex items-center gap-1 ${
              filterType === "CHARGING_STATION"
                ? "bg-sky-700 text-white"
                : "bg-sky-50 text-sky-700 hover:bg-sky-100"
            }`}
          >
            <span>{t("⚡ Trạm sạc")}</span>
          </button>
          <button
            type="button"
            onClick={() => setFilterType("SERVICE_WORKSHOP")}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition shrink-0 flex items-center gap-1 ${
              filterType === "SERVICE_WORKSHOP"
                ? "bg-emerald-700 text-white"
                : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
            }`}
          >
            <span>{t("🔧 Xưởng DV")}</span>
          </button>
          <button
            type="button"
            onClick={() => setFilterType("EXPRESSWAY_RESCUE")}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition shrink-0 flex items-center gap-1 ${
              filterType === "EXPRESSWAY_RESCUE"
                ? "bg-red-600 text-white"
                : "bg-red-50 text-red-700 hover:bg-red-100"
            }`}
          >
            <span>{t("🚨 Cứu hộ 24/7")}</span>
          </button>
        </div>

        {/* Nội dung danh sách */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
          {/* TRƯỜNG HỢP A: ĐIỂM GẦN NHẤT QUÁ XA (> 50 KM) THEO YÊU CẦU */}
          {isNearestTooFar ? (
            <div className="p-3.5 rounded-2xl border border-amber-200 bg-amber-50/90 text-[12px] space-y-2.5 animate-fadeIn">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="font-bold text-[13px] text-amber-950">
                    {t("Chưa có điểm hỗ trợ trong khu vực của bạn")}</h4>
                  <p className="text-amber-900 leading-relaxed text-[11.5px]">
                    {t("Điểm gần nhất thuộc phân loại này cách vị trí của bạn")}{" "}
                    <strong>{nearestPoint ? nearestPoint.distText : "> 50 km"}</strong>{t(". Vui lòng liên hệ Tổng đài Toàn quốc để được hỗ trợ điều phối:")}</p>
                </div>
              </div>

              <a
                href="tel:1900232389"
                className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-[12px] shadow-2xs transition"
              >
                <PhoneCall className="w-3.5 h-3.5" />
                <span>{t("Gọi Tổng đài Cứu hộ: 1900-232389 (24/7)")}</span>
              </a>
            </div>
          ) : nearestPoint ? (
            /* TRƯỜNG HỢP B: HIỂN THỊ ĐÚNG 1 ĐIỂM GẦN NHẤT (FEATURED CARD) */
            <div className="space-y-2">
              <div
                onClick={() => {
                  onSelectPoint(nearestPoint.id);
                  setActivePopoverId(nearestPoint.id);
                }}
                className="p-3.5 rounded-2xl border-2 border-[#1E40AF] bg-blue-50/50 shadow-xs cursor-pointer transition relative"
              >
                {/* Huy hiệu điểm gần nhất */}
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5 min-w-0">
                    {nearestPoint.type === "EXPRESSWAY_RESCUE" ? (
                      <span className="px-2 py-0.5 rounded-md font-bold text-[10px] bg-red-100 text-red-700 uppercase">
                        {t("🚨 Cứu hộ 24/7")}</span>
                    ) : nearestPoint.type === "CHARGING_STATION" ? (
                      <span className="px-2 py-0.5 rounded-md font-bold text-[10px] bg-blue-100 text-[#1E40AF] uppercase">
                        {t("⚡ Trạm sạc Siêu Nhanh")}</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-md font-bold text-[10px] bg-emerald-100 text-emerald-800 uppercase">
                        {t("🔧 Xưởng dịch vụ 3S")}</span>
                    )}
                    <span className="text-[10px] font-bold text-[#1E40AF] bg-white px-2 py-0.5 rounded-full border border-blue-200">
                      {t("Gần bạn nhất")}</span>
                  </div>

                  <span className="font-mono text-[12px] font-bold text-[#1E40AF] shrink-0">
                    {nearestPoint.distText}
                  </span>
                </div>

                <h4 className="font-bold text-[13px] text-slate-900 leading-snug">
                  {nearestPoint.name}
                </h4>
                <p className="text-[11.5px] text-slate-600 mt-1 leading-relaxed">
                  {nearestPoint.address}
                </p>

                {/* Nút hành động */}
                <div className="mt-2.5 pt-2 border-t border-blue-100 flex items-center justify-between gap-2">
                  <a
                    href={`https://maps.google.com/?q=${encodeURIComponent(nearestPoint.address)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-[#1E40AF] hover:underline"
                  >
                    <Navigation className="w-3.5 h-3.5" />
                    <span>{t("Chỉ đường Maps")}</span>
                  </a>

                  <a
                    href={`tel:${nearestPoint.hotline.replace(/-/g, "")}`}
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[11px] font-bold transition shadow-2xs"
                  >
                    <PhoneCall className="w-3 h-3" />
                    <span>{nearestPoint.hotline}</span>
                  </a>
                </div>
              </div>

              {/* Nút "Xem thêm các điểm khác" dạng accordion */}
              {remainingPoints.length > 0 && (
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={() => setShowMorePoints(!showMorePoints)}
                    className="w-full py-2 px-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-[11.5px] font-semibold text-slate-700 flex items-center justify-between transition shadow-2xs"
                  >
                    <span>
                      {showMorePoints
                        ? t("Thu gọn danh sách")
                        : (language === "en" ? `Show ${remainingPoints.length} more support points` : `Xem thêm ${remainingPoints.length} điểm hỗ trợ khác trong hệ thống`)}
                    </span>
                    {showMorePoints ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </button>

                  {/* Danh sách mở rộng */}
                  {showMorePoints && (
                    <div className="space-y-2 pt-2 animate-fadeIn">
                      {remainingPoints.map((point) => (
                        <div
                          key={point.id}
                          onClick={() => {
                            onSelectPoint(point.id);
                            setActivePopoverId(point.id);
                          }}
                          className="p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-[12px] cursor-pointer transition shadow-2xs"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h5 className="font-bold text-[12.5px] text-slate-900 leading-snug">
                              {point.name}
                            </h5>
                            <span className="font-mono text-[11px] font-bold text-slate-500 shrink-0">
                              {point.distText}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed line-clamp-1">
                            {point.address}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 text-center text-slate-500 text-[12px]">
              {t("Chưa có dữ liệu điểm hỗ trợ được xác thực cho khu vực này. Anh/chị vui lòng tra cứu trên ứng dụng VinFast hoặc liên hệ hotline.")}</div>
          )}
        </div>

        {/* ─────────────────────────────────────────────────────────────
            4. DISCLAIMER PHẠM VI HỖ TRỢ
        ───────────────────────────────────────────────────────────── */}
        <div className="p-2.5 bg-slate-100/80 border-t border-slate-200 text-[10.5px] text-slate-500 leading-relaxed shrink-0">
          <p className="flex items-start gap-1">
            <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
            <span>
              {t("Điểm hỗ trợ gợi ý theo dữ liệu hệ thống, không phải điều phối hay theo dõi xe cứu hộ trực tiếp.")}</span>
          </p>
        </div>
      </div>
    </div>
  );

  // Desktop Fullscreen Modal
  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 animate-fadeIn">
        <div className="w-full max-w-5xl h-[88vh]">
          {renderContent()}
        </div>
      </div>
    );
  }

  // Mobile Bottom-Sheet Modal
  if (isMobileModal) {
    return (
      <div className="fixed inset-0 z-50 lg:hidden bg-slate-900/50 backdrop-blur-2xs flex flex-col justify-end animate-fadeIn">
        <div className="w-full h-[85vh] bg-white rounded-t-3xl overflow-hidden shadow-2xl animate-slideUp flex flex-col">
          <div
            className="w-full py-2.5 flex justify-center bg-slate-100 border-b border-slate-200 cursor-pointer"
            onClick={onClose}
          >
            <div className="w-12 h-1 rounded-full bg-slate-300" />
          </div>
          <div className="flex-1 min-h-0">{renderContent()}</div>
        </div>
      </div>
    );
  }

  // Desktop Side Panel (55/45)
  return (
    <aside className="h-[calc(100vh-165px)] min-h-[580px] max-h-[780px] w-full">
      {renderContent()}
    </aside>
  );
}
