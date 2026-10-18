"use client";

import React from "react";
import { PhoneCall, Navigation, Calendar, Wrench, Zap, Store, AlertTriangle } from "lucide-react";
import { ServicePointApiItem, ServicePointSeed } from "../types";

export type AnyServicePoint = ServicePointApiItem | (ServicePointSeed & {
  category?: string;
  category_slug?: string;
  hotline_service?: string | null;
  operating_hours?: string | null;
  hours?: string | null;
  booking_url?: string | null;
  dong_son?: boolean;
  services_offered?: string[];
  note?: string | null;
  distance_km?: number | null;
  distance_from_area_km?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  phone?: string | null;
  verification_status?: string | null;
});

export interface ServicePointCardProps {
  point: AnyServicePoint;
  index: number;
  isSelected?: boolean;
  onSelect?: () => void;
  areaLabel?: string;
  userCoords?: { lat: number; lng: number } | null;
  onSelectDestination?: (point: AnyServicePoint) => void;
}

export function ServicePointCard({
  point,
  index,
  isSelected = false,
  onSelect,
  areaLabel = "khu vực",
  userCoords,
  onSelectDestination,
}: ServicePointCardProps) {
  // Chuẩn hóa category
  const rawCat = (point.category || (point as ServicePointSeed).type || "").toLowerCase();
  const rawSlug = point.category_slug || "";
  const isWorkshop =
    rawCat === "workshop" ||
    rawCat === "service_workshop" ||
    rawSlug.includes("service") ||
    rawCat.includes("xưởng");
  const isCharging =
    rawCat === "charging_station" ||
    rawSlug === "car_charging_station" ||
    rawCat.includes("trụ sạc") ||
    rawCat.includes("trạm sạc");
  const isShowroom =
    rawCat === "showroom" ||
    rawSlug === "showroom_car" ||
    rawCat.includes("showroom");

  const isGsm = rawSlug === "service_gsm" || point.name.toLowerCase().includes("gsm");
  const hasDongSon = Boolean(
    point.dong_son ||
    point.services_offered?.includes("dong_son") ||
    point.name.toLowerCase().includes("đồng sơn")
  );

  // Tọa độ & Link chỉ đường
  const lat = point.latitude ?? (point as ServicePointSeed).coords?.lat;
  const lng = point.longitude ?? (point as ServicePointSeed).coords?.lng;
  const directionsHref =
    lat != null && lng != null
      ? `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}${
          userCoords ? `&origin=${userCoords.lat},${userCoords.lng}` : ""
        }`
      : `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(point.address)}`;

  // Hotline & Giờ mở cửa
  const hotlineVal = point.hotline_service || point.phone || (point as ServicePointSeed).hotline;
  const hoursVal =
    point.operating_hours ||
    point.hours ||
    (isWorkshop ? "08:00 - 18:00" : undefined);

  // Khoảng cách
  const distKm = point.distance_km ?? (point as ServicePointSeed).distanceKm;
  const distAreaKm = point.distance_from_area_km;

  // Nhãn nguồn dữ liệu (chuẩn SNAPSHOT / VinFast thu thập)
  const sourceLabel = (point as ServicePointSeed).demo
    ? "Dữ liệu demo"
    : "VinFast (dữ liệu snapshot thu thập)";

  return (
    <div
      id={`service-point-card-${point.id}`}
      onClick={onSelect}
      className={`p-3.5 rounded-xl border transition text-[12px] space-y-2.5 cursor-pointer ${
        isSelected
          ? "border-blue-600 bg-blue-50/50 shadow-sm ring-2 ring-blue-500/20"
          : "border-slate-200/90 bg-slate-50/60 hover:bg-white hover:border-blue-300"
      }`}
    >
      {/* Header: Số thứ tự + Tên điểm + Badges */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <h4 className="font-semibold text-slate-900 leading-snug flex items-baseline gap-1.5">
            <span className="font-bold text-[#1E40AF] shrink-0">{index + 1}.</span>
            <span className="break-words">{point.name}</span>
          </h4>
          <p className="text-[11.5px] text-slate-500 mt-1 leading-relaxed break-words">
            {point.address}
          </p>
        </div>

        <div className="flex flex-col items-end gap-1 shrink-0">
          {isWorkshop && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
              <Wrench className="w-2.5 h-2.5" />
              <span>Xưởng 2S</span>
            </span>
          )}
          {isCharging && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
              <Zap className="w-2.5 h-2.5" />
              <span>Trạm sạc</span>
            </span>
          )}
          {isShowroom && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
              <Store className="w-2.5 h-2.5" />
              <span>Showroom</span>
            </span>
          )}
          {hasDongSon && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">
              Đồng sơn
            </span>
          )}
          {isGsm && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
              Taxi GSM
            </span>
          )}
        </div>
      </div>

      {/* Thông tin đặc thù theo loại điểm */}
      {isCharging && (
        <div className="text-[11.5px] text-slate-500 italic flex items-center gap-1">
          <Zap className="w-3 h-3 text-emerald-600" />
          <span>Chưa công bố công suất</span>
        </div>
      )}

      {isWorkshop && (
        <div className="space-y-1 text-[11.5px] text-slate-600 bg-white/70 p-2 rounded-lg border border-slate-100">
          {hoursVal && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Giờ mở cửa:</span>
              <span className="font-medium text-slate-700">{hoursVal}</span>
            </div>
          )}
          {hotlineVal && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Hotline dịch vụ:</span>
              <a
                href={`tel:${hotlineVal.replace(/[^0-9]/g, "")}`}
                onClick={(e) => e.stopPropagation()}
                className="font-semibold text-blue-700 hover:underline flex items-center gap-1"
              >
                <PhoneCall className="w-3 h-3" />
                <span>{hotlineVal}</span>
              </a>
            </div>
          )}
        </div>
      )}

      {/* Ghi chú lưu ý nếu có */}
      {point.note && (
        <div className="p-2 rounded-lg bg-amber-50/90 border border-amber-200/80 text-[11px] text-amber-900 leading-snug flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
          <span>{point.note}</span>
        </div>
      )}

      {/* Nguồn dữ liệu */}
      <div className="text-[10.5px] text-slate-400 flex items-center justify-between">
        <span>Nguồn: {sourceLabel}</span>
      </div>

      {/* Khoảng cách & Nút hành động */}
      <div className="pt-1.5 flex flex-wrap items-center justify-between gap-1.5 border-t border-slate-200/70">
        <div>
          {distKm != null ? (
            <span className="text-[11px] text-slate-600 font-mono font-medium">
              Cách Quý khách: {distKm < 5 ? "dưới 5 km" : `${Math.round(distKm)} km`}
            </span>
          ) : distAreaKm != null ? (
            <span className="text-[11px] text-slate-500 font-mono">
              Khoảng {Math.round(distAreaKm) < 5 ? "dưới 5 km" : `${Math.round(distAreaKm)} km`} từ {areaLabel} (đường chim bay, không phải khoảng cách từ vị trí của Quý khách)
            </span>
          ) : null}
        </div>

        <div className="flex items-center gap-1.5">
          {point.booking_url && (
            <a
              href={point.booking_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-[11px] font-semibold transition border border-emerald-200/60"
            >
              <Calendar className="w-3 h-3" />
              <span>Đặt lịch</span>
            </a>
          )}

          <a
            href={directionsHref}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 text-[#1E40AF] hover:bg-blue-100 text-[11px] font-semibold transition border border-blue-200/60"
          >
            <Navigation className="w-3 h-3" />
            <span>Chỉ đường</span>
          </a>

          {onSelectDestination && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelectDestination(point);
              }}
              className="px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium transition"
            >
              Chọn điểm đến
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
