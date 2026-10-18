"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { PhoneCall, X, MapPin } from "lucide-react";
import type { ServicePointSeed, UserLocationState, ServicePointApiItem, ServicePointsApiResponse } from "../types";
import { calculateHaversineDistanceKm } from "../utils/distance";
import { resolveManualArea } from "../constants/manualAreas";
import { getNearbyServicePoints, getCaseServicePoints } from "../api/chatApi";
import { VietmapMiniMap } from "./VietmapMiniMap";
import { ServicePointCard, AnyServicePoint } from "./ServicePointCard";

export type Category = "ALL" | "CHARGING_STATION" | "SHOWROOM" | "SERVICE_WORKSHOP" | "OTHER";
export type ServiceMapCategory = Category;
const categories: [Category, string][] = [
  ["ALL", "Tất cả"],
  ["CHARGING_STATION", "Trụ sạc"],
  ["SHOWROOM", "Showroom"],
  ["SERVICE_WORKSHOP", "Xưởng dịch vụ 2S"],
  ["OTHER", "Loại khác"],
];

interface Props {
  caseId?: string | null;
  providedPoints?: ServicePointSeed[];
  isOpen: boolean;
  onClose: () => void;
  locationState: UserLocationState;
  servicePoints: ServicePointSeed[];
  selectedPointId: string | null;
  onSelectPoint: (id: string) => void;
  onSelectDestination?: (point: AnyServicePoint) => void;
  suggestedCategory?: Category;
}

export function ServiceMapPanel({
  caseId,
  providedPoints,
  isOpen,
  onClose,
  locationState,
  servicePoints,
  selectedPointId,
  onSelectPoint,
  onSelectDestination,
  suggestedCategory = "ALL",
}: Props) {
  const [category, setCategory] = useState<Category>("ALL");
  const [nearby, setNearby] = useState<ServicePointSeed[] | null>(null);
  const [caseServiceData, setCaseServiceData] = useState<ServicePointsApiResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(selectedPointId);
  const requestId = useRef(0);
  const nearbyAbort = useRef<AbortController | null>(null);

  const origin = locationState.status === "CONSENTED" ? locationState.coords : undefined;
  const center = useMemo(
    () => origin ?? (locationState.status === "MANUAL" ? resolveManualArea(locationState.label)?.coord : undefined),
    [origin, locationState.status, locationState.label]
  );

  useEffect(() => {
    setSelectedId(selectedPointId);
  }, [selectedPointId]);

  useEffect(() => {
    setCategory(suggestedCategory);
  }, [suggestedCategory]);

  // Nếu có caseId thì lấy điểm dịch vụ từ /cases/{id}/service-points
  useEffect(() => {
    if (!isOpen || !caseId || providedPoints) return;
    let cancelled = false;
    getCaseServicePoints(caseId).then((res) => {
      if (!cancelled && res?.success && res.data) {
        setCaseServiceData(res.data);
      }
    }).catch(() => null);
    return () => {
      cancelled = true;
    };
  }, [isOpen, caseId, providedPoints]);

  // Nếu không có caseId hoặc không có caseServiceData, lấy từ /customer/service-points/nearby
  useEffect(() => {
    if (providedPoints || caseId) return;
    if (!isOpen || !center) {
      requestId.current++;
      nearbyAbort.current?.abort();
      setNearby(null);
      return;
    }

    const id = ++requestId.current;
    nearbyAbort.current?.abort();
    const controller = new AbortController();
    nearbyAbort.current = controller;
    setNearby(null);

    getNearbyServicePoints(center, category, controller.signal)
      .then((result) => {
        if (id === requestId.current) setNearby(result);
      })
      .catch(() => {
        if (id === requestId.current) setNearby(null);
      });

    return () => {
      controller.abort();
    };
  }, [providedPoints, caseId, isOpen, center, category]);

  // Danh sách điểm hiển thị
  const displayPoints: (ServicePointApiItem | ServicePointSeed)[] = useMemo(() => {
    if (providedPoints) {
      return providedPoints
        .filter((point) => category === "ALL" || point.type === category)
        .map((point) => ({ ...point, latitude: point.coords.lat, longitude: point.coords.lng }));
    }
    if (caseServiceData?.recommended_points && caseServiceData.recommended_points.length > 0) {
      return caseServiceData.recommended_points;
    }
    const base = providedPoints ?? nearby ?? servicePoints;
    return base
      .filter((point) => category === "ALL" || point.type === category)
      .map((point) => ({
        ...point,
        latitude: point.coords.lat,
        longitude: point.coords.lng,
        distance_km: center ? calculateHaversineDistanceKm(center, point.coords) : undefined,
      }))
      .filter((point) => point.distance_km === undefined || point.distance_km <= 50)
      .sort((a, b) => (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity));
  }, [caseServiceData, providedPoints, nearby, servicePoints, category, center]);

  const rescueHotline = caseServiceData?.rescue_hotline;
  const noPointsNearby = caseServiceData?.no_points_nearby || (displayPoints.length === 0 && !caseId);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    onSelectPoint(id);
    const cardEl = document.getElementById(`service-point-card-${id}`);
    cardEl?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  if (!isOpen) return null;

  return (
    <section
      aria-label="Bản đồ điểm dịch vụ"
      className="min-w-0 rounded-2xl border border-slate-200/90 bg-white overflow-hidden flex flex-col shadow-lg my-3"
    >
      <header className="flex items-center justify-between p-3.5 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-[#1E40AF]" />
          <strong className="text-sm font-bold text-slate-900">Điểm hỗ trợ VinFast</strong>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Đóng bản đồ"
          className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/70 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </header>

      <div className="p-3.5 space-y-3">
        {/* Banner Hotline Cứu Hộ Khẩn Cấp hiển thị đầu tiên nếu có */}
        {rescueHotline && (
          <div className="rounded-xl border-2 border-red-500 bg-red-50 p-3 shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-red-900 font-bold text-xs uppercase">
                <PhoneCall className="w-4 h-4 text-red-600 animate-pulse" />
                <span>Hotline Cứu hộ Khẩn cấp 24/7</span>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-red-600 text-white text-[10px] font-bold">
                ƯU TIÊN
              </span>
            </div>
            <p className="text-[11.5px] text-red-800 leading-relaxed">
              Hồ sơ được xác định thuộc tình trạng cần cứu hộ khẩn cấp hoặc không thể di chuyển an toàn:
            </p>
            <a
              href={`tel:${rescueHotline.replace(/[^0-9]/g, "")}`}
              className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-xs transition"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>☎ {rescueHotline}</span>
            </a>
          </div>
        )}

        {/* Bộ lọc danh mục (khi không lấy theo hồ sơ sự cố cố định) */}
        {!caseId && (
          <div className="flex flex-wrap gap-1.5">
            {categories.map(([val, label]) => (
              <button
                key={val}
                type="button"
                aria-pressed={category === val}
                className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition ${
                  category === val
                    ? "bg-[#1E40AF] text-white border-[#1E40AF]"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
                onClick={() => {
                  setCategory(val);
                  setSelectedId(null);
                }}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {/* Bản đồ Vietmap (Tự động ẩn nếu thiếu key, danh sách card vẫn hiện) */}
        <VietmapMiniMap
          points={displayPoints}
          userLocation={origin}
          selectedPointId={selectedId}
          onSelectPoint={handleSelect}
        />

        {/* Danh sách các card điểm dịch vụ */}
        <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
          {displayPoints.length === 0 ? (
            noPointsNearby ? (
              <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-2 text-center">
                <p className="font-semibold leading-relaxed">
                  {caseServiceData?.message ||
                    "Chưa có điểm dịch vụ trong 150 km quanh vị trí của Quý khách; vui lòng gọi hotline"}
                </p>
                <a
                  href="tel:1900232389"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs transition"
                >
                  <PhoneCall className="w-3.5 h-3.5" />
                  <span>Hotline VinFast: 1900-232389</span>
                </a>
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-3 text-center">
                Không có điểm dịch vụ phù hợp trong bộ lọc này.
              </p>
            )
          ) : (
            displayPoints.map((point, idx) => (
              <ServicePointCard
                key={point.id || idx}
                point={point}
                index={idx}
                isSelected={selectedId === point.id}
                onSelect={() => handleSelect(point.id)}
                areaLabel={caseServiceData?.area_reference?.label || locationState.label || "khu vực"}
                userCoords={origin}
                onSelectDestination={onSelectDestination}
              />
            ))
          )}
        </div>
      </div>
    </section>
  );
}
