"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { NearbyAction, ServicePointSeed, UserLocationState } from "../types";
import { getNearbyServicePoints } from "../api/chatApi";
import { resolveManualArea } from "../constants/manualAreas";
import { formatDistanceKm, getDirectionsUrl } from "../utils/distance";
import { ServiceMapPanel } from "./ServiceMapPanel";

interface Props {
  action: NearbyAction | null;
  locationState: UserLocationState;
  onChangeLocation: () => void;
  onStopSharing: () => void;
  onChooseCategory: (category: string) => void;
}

export function NearbyResults({ action, locationState, onChangeLocation, onStopSharing, onChooseCategory }: Props) {
  const [points, setPoints] = useState<ServicePointSeed[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [radius, setRadius] = useState(50);
  const [mapOpen, setMapOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const generation = useRef(0);
  const resultsRef = useRef<HTMLElement>(null);
  const origin = locationState.status === "CONSENTED" ? locationState.coords : undefined;
  const center = useMemo(() => origin ?? (locationState.status === "MANUAL" ? resolveManualArea(locationState.label)?.coord : undefined),
    [origin, locationState.status, locationState.label]);

  useEffect(() => { setRadius(50); setMapOpen(false); }, [action?.request_id]);
  useEffect(() => {
    const id = ++generation.current;
    const controller = new AbortController();
    setPoints([]); setError(false); setLoading(false);
    if (action && action.category !== "ALL" && center) {
      setLoading(true);
      getNearbyServicePoints(center, action.category, controller.signal, { vehicleType: action.vehicle_type, radiusKm: radius })
        .then((result) => { if (generation.current === id && !controller.signal.aborted) setPoints(result.slice(0, 5)); })
        .catch(() => { if (generation.current === id && !controller.signal.aborted) setError(true); })
        .finally(() => { if (generation.current === id && !controller.signal.aborted) setLoading(false); });
    }
    return () => controller.abort();
  }, [action, center, radius, retry]);

  useEffect(() => {
    if (!action || loading || !center) return;
    const frame = window.requestAnimationFrame(() => {
      const result = resultsRef.current;
      const feed = result?.closest<HTMLElement>("[data-chat-feed]");
      const target = mapOpen ? result?.querySelector<HTMLElement>('[aria-label="Bản đồ điểm dịch vụ"]') : result;
      if (target && feed) feed.scrollTo({ top: feed.scrollTop + target.getBoundingClientRect().top - feed.getBoundingClientRect().top - 8, behavior: "auto" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [action, loading, center, points, error, mapOpen]);

  if (!action) return null;
  if (action.category === "ALL") return <section aria-label="Chọn loại địa điểm" className="space-y-2 rounded-xl border p-3 text-sm">
    <p>Bạn muốn tìm loại địa điểm nào gần đây?</p>
    <button className="min-h-10 rounded-xl border px-3" onClick={() => onChooseCategory("CHARGING_STATION")}>Trạm sạc</button>{" "}
    <button className="min-h-10 rounded-xl border px-3" onClick={() => onChooseCategory("SHOWROOM")}>Showroom</button>{" "}
    <button className="min-h-10 rounded-xl border px-3" onClick={() => onChooseCategory("SERVICE_WORKSHOP")}>Xưởng dịch vụ</button>
  </section>;
  if (!center) return locationState.status === "MANUAL" && locationState.label ? <section aria-label="Kết quả gần đây" className="rounded-xl border p-3 text-sm">
    <p>Khu vực: {locationState.label}. Chưa xác định được tâm tham chiếu nên chưa thể xếp hạng khoảng cách.</p>
    <button className="mt-2 min-h-10 rounded-xl border px-3" onClick={onChangeLocation}>Chọn khu vực gợi ý</button>
  </section> : locationState.status === "NOT_SHARED" ? <p className="text-sm text-slate-600">Chưa chia sẻ vị trí. Bạn có thể tiếp tục chat.</p> : null;

  return <section ref={resultsRef} aria-label="Kết quả gần đây" aria-busy={loading} className="min-w-0 space-y-3 rounded-xl border border-slate-200 bg-white p-3 text-sm">
    <h2 className="font-semibold text-slate-900">{action.reason}</h2>
    <p className="text-xs text-slate-600">{origin ? "Từ vị trí bạn cho phép dùng" : `Từ tâm khu vực tham chiếu ${locationState.label}, không phải GPS`} · Trong {radius} km. Khoảng cách đường chim bay, tham khảo.</p>
    {locationState.accuracy && locationState.accuracy > 500 && <p className="text-xs text-amber-900">Vị trí ước lượng ±{Math.round(locationState.accuracy)} m.</p>}
    {loading && <p role="status">Đang tìm địa điểm phù hợp…</p>}
    {error && <div role="alert"><p>Không tải được danh mục địa điểm. Bạn có thể thử lại hoặc đổi khu vực.</p><button className="mt-2 min-h-10 rounded-xl border px-3" onClick={() => setRetry(retry + 1)}>Thử lại tìm kiếm</button></div>}
    {!loading && !error && points.length === 0 && <p>Không có địa điểm phù hợp trong phạm vi này.{action.category === "SERVICE_WORKSHOP" && " Danh mục xưởng hiện chưa có dữ liệu đủ tin cậy."}</p>}
    <ol className="space-y-3">
      {points.map((point, index) => <li key={point.id} className="min-w-0 rounded-xl border border-slate-200 p-3">
        <p className="break-words font-semibold">{index + 1}. {point.name}</p>
        <p className="break-words text-slate-600">{point.address}</p>
        <p className="my-1 text-xs text-slate-600">{point.distanceKm !== undefined ? `${formatDistanceKm(point.distanceKm)} đường chim bay` : "Chưa có khoảng cách"}{index === 0 ? " · Gần nhất trong kết quả" : ""}</p>
        <p className="mb-2 text-xs text-slate-600">{point.demo ? "Dữ liệu demo" : "Dữ liệu snapshot"} · Chưa xác minh hoạt động hiện tại · {point.updatedAt ? `Cập nhật nguồn ${point.updatedAt}` : "Ngày cập nhật nguồn chưa rõ"}</p>
        <a className="inline-flex min-h-10 max-w-full items-center justify-center rounded-xl bg-blue-800 px-4 py-2 text-center font-medium text-white hover:bg-blue-900"
          href={getDirectionsUrl({ ...point.coords, address: point.address }, origin)} target="_blank" rel="noopener noreferrer">Chỉ đường Google Maps</a>
      </li>)}
    </ol>
    <p className="text-xs text-slate-600">Nhấn Chỉ đường để mở Google Maps; tọa độ điểm đến{origin ? " và vị trí hiện tại" : ""} được chuyển sang dịch vụ đó. Không có thông tin cổng trống hoặc ETA trực tiếp.</p>
    <div className="flex flex-wrap gap-2">
      {!loading && !error && points.length < 5 && radius < 200 && <button className="min-h-10 rounded-xl border px-3" onClick={() => setRadius(radius * 2)}>Mở rộng tới {radius * 2} km</button>}
      {points.length > 0 && <button className="min-h-10 rounded-xl border px-3" onClick={() => setMapOpen(!mapOpen)}>{mapOpen ? "Ẩn bản đồ" : "Xem bản đồ"}</button>}
      <button className="min-h-10 rounded-xl border px-3" onClick={onChangeLocation}>Đổi vị trí</button>
      <button className="min-h-10 rounded-xl bg-rose-50 px-3 text-rose-700" onClick={onStopSharing}>Dừng chia sẻ</button>
    </div>
    {mapOpen && <ServiceMapPanel isOpen onClose={() => setMapOpen(false)} locationState={locationState}
      servicePoints={points} providedPoints={points} selectedPointId={selected} onSelectPoint={setSelected} suggestedCategory={action.category} />}
  </section>;
}
