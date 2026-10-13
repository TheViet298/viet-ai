"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Map as MapLibreMap, Marker } from "maplibre-gl";
import type { ServicePointSeed, UserLocationState } from "../types";
import { calculateHaversineDistanceKm, formatDistanceKm, getDirectionsUrl, getOsmDirectionsUrl } from "../utils/distance";
import { resolveManualArea } from "../constants/manualAreas";
import { createRasterMapStyle } from "../utils/mapTileProvider";
import { getNearbyServicePoints } from "../api/chatApi";

function pointLabel(point: ServicePointSeed) {
  return point.demo ? "[Demo] " : point.verificationStatus === "VERIFIED" ? "" : "[Chưa xác minh] ";
}

type Category = "ALL" | ServicePointSeed["type"];
const categories: [Category, string][] = [["ALL", "Tất cả"], ["CHARGING_STATION", "Trụ sạc"], ["SHOWROOM", "Showroom"], ["SERVICE_WORKSHOP", "Xưởng kỹ thuật"], ["OTHER", "Loại khác / Cứu hộ"]];
function accuracyPolygon(lat: number, lng: number, meters: number): GeoJSON.Feature<GeoJSON.Polygon> {
  const coordinates: [number, number][] = [];
  for (let i = 0; i <= 64; i++) {
    const angle = 2 * Math.PI * i / 64;
    coordinates.push([lng + meters * Math.cos(angle) / (111320 * Math.max(0.01, Math.cos(lat * Math.PI / 180))), lat + meters * Math.sin(angle) / 111320]);
  }
  return { type: "Feature", geometry: { type: "Polygon", coordinates: [coordinates] }, properties: {} };
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  locationState: UserLocationState;
  servicePoints: ServicePointSeed[];
  selectedPointId: string | null;
  onSelectPoint: (id: string) => void;
  onSelectDestination?: (point: ServicePointSeed) => void;
  suggestedCategory?: Category;
}
export function ServiceMapPanel({ isOpen, onClose, locationState, servicePoints, selectedPointId, onSelectPoint, onSelectDestination, suggestedCategory = "ALL" }: Props) {
  const [category, setCategory] = useState<Category>("ALL");
  const [nearby, setNearby] = useState<ServicePointSeed[] | null>(null);
  const [mapError, setMapError] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const mapElement = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markers = useRef<Marker[]>([]);
  const requestId = useRef(0);
  const nearbyAbort = useRef<AbortController | null>(null);
  const lastQuery = useRef<{ coord: { lat: number; lng: number }; time: number; category: Category; mode: UserLocationState["status"] } | null>(null);
  const origin = locationState.status === "CONSENTED" ? locationState.coords : undefined;
  const center = useMemo(() => origin ?? (locationState.status === "MANUAL" ? resolveManualArea(locationState.label)?.coord : undefined), [origin, locationState.status, locationState.label]);
  const hasCenter = Boolean(center);
  const latestCenter = useRef(center);
  latestCenter.current = center;
  const points = nearby ?? servicePoints;
  const filtered = useMemo(() => points.filter((point) => category === "ALL" || point.type === category).map((point) => ({ ...point, km: center ? calculateHaversineDistanceKm(center, point.coords) : null })).filter((point) => point.km === null || point.km <= 50).sort((a, b) => (a.km ?? Infinity) - (b.km ?? Infinity)), [points, category, center]);
  const selected = filtered.find((point) => point.id === selectedPointId) ?? filtered[0];

  useEffect(() => { setCategory(suggestedCategory); }, [suggestedCategory]);
  useEffect(() => {
    if (!isOpen || !center) { requestId.current++; nearbyAbort.current?.abort(); lastQuery.current = null; setNearby(null); return; }
    const now = Date.now();
    const previous = lastQuery.current;
    if (previous && previous.category === category && previous.mode === locationState.status && calculateHaversineDistanceKm(previous.coord, center) < 0.15 && now - previous.time < 30000) return;
    lastQuery.current = { coord: center, time: now, category, mode: locationState.status };
    const id = ++requestId.current;
    nearbyAbort.current?.abort();
    const controller = new AbortController();
    nearbyAbort.current = controller;
    setNearby(null);
    getNearbyServicePoints(center, category, controller.signal).then((result) => {
      if (id === requestId.current) setNearby(result);
    }).catch(() => { if (id === requestId.current) setNearby(null); });
    // Keep an in-flight query across small GPS updates that do not pass the throttle.
    // It is cancelled only by a replacement query, close, or unmount.
  }, [isOpen, center, category, locationState.status]);
  useEffect(() => () => { nearbyAbort.current?.abort(); requestId.current++; }, []);

  useEffect(() => {
    if (!isOpen || !mapElement.current || !hasCenter) return;
    setMapError(false);
    let cancelled = false;
    const resizeObserver = new ResizeObserver(() => map.current?.resize());
    resizeObserver.observe(mapElement.current);
    import("maplibre-gl").then((maplibre) => {
      const initialCenter = latestCenter.current;
      if (cancelled || !mapElement.current || !initialCenter) return;
      try {
        // Next.js 14 cannot bundle MapLibre v6's ESM worker reliably. Serve
        // the copied worker from /public and configure it before map creation.
        maplibre.setWorkerUrl("/maplibre-gl-worker.mjs");
        const instance = new maplibre.Map({ container: mapElement.current, center: [initialCenter.lng, initialCenter.lat], zoom: 11, style: createRasterMapStyle(process.env.NEXT_PUBLIC_MAP_TILE_URL, process.env.NEXT_PUBLIC_MAP_TILE_ATTRIBUTION) });
        map.current = instance;
        instance.addControl(new maplibre.NavigationControl(), "top-right");
        instance.on("error", () => { if (!cancelled) setMapError(true); });
        instance.on("style.load", () => { if (!cancelled) { setMapError(false); setMapReady(true); } });
      } catch { setMapError(true); }
    }).catch(() => { if (!cancelled) setMapError(true); });
    return () => { cancelled = true; resizeObserver.disconnect(); markers.current.forEach((marker) => marker.remove()); markers.current = []; map.current?.remove(); map.current = null; setMapReady(false); };
  }, [isOpen, hasCenter]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !center || !mapReady) return;
    let disposed = false;
    import("maplibre-gl").then((maplibre) => {
      if (disposed || map.current !== instance) return;
      markers.current.forEach((marker) => marker.remove());
      markers.current = [];
      const user = document.createElement("div"); user.className = "w-5 h-5 rounded-full bg-blue-700 border-2 border-white shadow-md";
      user.title = origin ? "Vị trí hiện tại" : "Tâm khu vực tham chiếu";
      markers.current.push(new maplibre.Marker({ element: user }).setLngLat([center.lng, center.lat]).addTo(instance));
      filtered.forEach((point) => {
        const button = document.createElement("button"); button.type = "button"; button.className = "w-4 h-4 rounded-full bg-red-600 border-2 border-white shadow-md"; button.title = `${pointLabel(point)}${point.name}`;
        button.onclick = () => onSelectPoint(point.id);
        markers.current.push(new maplibre.Marker({ element: button }).setLngLat([point.coords.lng, point.coords.lat]).addTo(instance));
      });
      const bounds = new maplibre.LngLatBounds([center.lng, center.lat], [center.lng, center.lat]);
      filtered.forEach((point) => bounds.extend([point.coords.lng, point.coords.lat]));
      instance.fitBounds(bounds, { padding: 32, maxZoom: 13, duration: 0 });
      const source = instance.getSource("accuracy") as import("maplibre-gl").GeoJSONSource | undefined;
      const data = origin && locationState.accuracy ? accuracyPolygon(center.lat, center.lng, locationState.accuracy) : { type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection;
      if (source) source.setData(data);
      else if (instance.isStyleLoaded()) { instance.addSource("accuracy", { type: "geojson", data }); instance.addLayer({ id: "accuracy-fill", type: "fill", source: "accuracy", paint: { "fill-color": "#2563eb", "fill-opacity": 0.16 } }); }
    });
    return () => { disposed = true; };
  }, [center, filtered, locationState.accuracy, origin, onSelectPoint, mapReady]);

  if (!isOpen) return null;
  return <section className="h-full min-h-[500px] rounded-xl border bg-white overflow-hidden flex flex-col" aria-label="Bản đồ điểm dịch vụ">
    <header className="flex items-center justify-between p-3 border-b"><strong>Điểm dịch vụ</strong><button type="button" onClick={onClose} aria-label="Đóng bản đồ">Đóng</button></header>
    <div className="flex flex-1 min-h-[450px]">
      <div className="w-1/2 overflow-auto p-3 space-y-3">
        <p className="text-xs text-slate-600">Điểm demo được gắn nhãn. Danh mục không xác nhận tình trạng hoạt động trực tiếp.</p>
        {locationState.status === "MANUAL" && <p className="text-xs text-amber-800">{center ? "Tâm khu vực tham chiếu/ước lượng, không phải GPS. Khoảng cách chỉ để tham khảo." : "Chưa nhận diện chính xác khu vực. Dùng Đổi lại vị trí để chọn một khu vực gợi ý; chưa có khoảng cách tham khảo."}</p>}
        {locationState.accuracy && locationState.accuracy > 500 && <p className="text-xs text-amber-800">Vị trí ước lượng ±{Math.round(locationState.accuracy)}m</p>}
        <div className="flex flex-wrap gap-1">{categories.map(([value, label]) => <button key={value} type="button" aria-pressed={category === value} className={`px-2 py-1 rounded border text-xs ${category === value ? "bg-blue-700 text-white" : "bg-white"}`} onClick={() => { if (value === category) return; nearbyAbort.current?.abort(); requestId.current++; setNearby(null); setCategory(value); onSelectPoint(""); }}>{label}</button>)}</div>
        {filtered.length === 0 && <div><p>Không có điểm demo phù hợp{center ? " trong bán kính 50 km" : " trong bộ lọc này"}.</p><a href="tel:1900232389" className="text-blue-700 underline">Gọi hỗ trợ 1900-232389</a></div>}
        {filtered.map((point) => <button type="button" key={point.id} onClick={() => onSelectPoint(point.id)} className={`block w-full text-left p-2 rounded border ${selected?.id === point.id ? "border-blue-700" : "border-slate-200"}`}><strong>{pointLabel(point)}{point.name}</strong><span className="block text-xs">{point.address}</span>{point.km !== null && <span className="text-xs">{formatDistanceKm(point.km)} đường chim bay</span>}</button>)}
        {selected && <div className="border-t pt-2 text-sm"><strong>{pointLabel(selected)}{selected.name}</strong><p>{selected.address}</p><p className="text-xs text-slate-600">Nguồn: {selected.source ?? "Chưa có nguồn"} · Cập nhật: {selected.updatedAt ?? "Chưa rõ"} · {selected.verificationStatus === "VERIFIED" && !selected.demo ? "Danh mục đã xác minh" : "Chưa xác minh"}</p>{selected.hotline && <a className="block text-blue-700" href={`tel:${selected.hotline.split(" ")[0].replace(/[^\d+]/g, "")}`}>Hotline: {selected.hotline}</a>}<div className="flex flex-wrap gap-3 mt-2"><a target="_blank" rel="noopener noreferrer" href={getDirectionsUrl({ ...selected.coords, address: selected.address }, origin)}>Google Maps{origin ? " chỉ đường" : " tìm địa chỉ"}</a>{origin && <a target="_blank" rel="noopener noreferrer" href={getOsmDirectionsUrl(selected.coords, origin)}>OpenStreetMap chỉ đường</a>}{onSelectDestination && <button type="button" onClick={() => onSelectDestination(selected)}>Chọn làm điểm đến</button>}</div></div>}
      </div>
      <div className="w-1/2 relative bg-slate-100" role="region" aria-label="Bản đồ tương tác">{center ? <div ref={mapElement} style={{ position: "absolute", inset: 0 }} /> : <p className="p-4 text-sm">Nhập hoặc chọn khu vực để mở bản đồ.</p>}{mapError && <p role="alert" className="absolute bottom-2 left-2 bg-white p-2 text-xs">Không tải được bản đồ. Danh sách vẫn sử dụng được.</p>}</div>
    </div>
  </section>;
}
