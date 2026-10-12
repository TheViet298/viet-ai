"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Map as MapLibreMap, Marker } from "maplibre-gl";
import type { ServicePointSeed, UserLocationState } from "../types";
import { calculateHaversineDistanceKm, formatDistanceKm, getDirectionsUrl, getOsmDirectionsUrl } from "../utils/distance";
import { getNearbyServicePoints } from "../api/chatApi";

type Category = "ALL" | ServicePointSeed["type"];
const categories: [Category, string][] = [["ALL", "Tất cả"], ["CHARGING_STATION", "Trụ sạc"], ["SHOWROOM", "Showroom"], ["SERVICE_WORKSHOP", "Xưởng kỹ thuật"], ["OTHER", "Loại khác / Cứu hộ"]];
const areas = [
  { names: ["hà nội"], coord: { lat: 21.0285, lng: 105.8542 } },
  { names: ["hồ chí minh", "hcm", "sài gòn"], coord: { lat: 10.8231, lng: 106.6297 } },
  { names: ["đà nẵng"], coord: { lat: 16.0544, lng: 108.2022 } },
  { names: ["long thành", "dầu giây", "đồng nai"], coord: { lat: 10.7712, lng: 106.945 } },
];
function reference(label: string) {
  return areas.find((area) => area.names.some((name) => label.toLocaleLowerCase("vi").includes(name)))?.coord;
}
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
  const lastQuery = useRef<{ coord: { lat: number; lng: number }; time: number; category: Category } | null>(null);
  const origin = locationState.status === "CONSENTED" ? locationState.coords : undefined;
  const center = origin ?? (locationState.status === "MANUAL" ? reference(locationState.label) : undefined);
  const points = nearby ?? servicePoints;
  const filtered = useMemo(() => points.filter((point) => category === "ALL" || point.type === category).map((point) => ({ ...point, km: center ? calculateHaversineDistanceKm(center, point.coords) : null })).filter((point) => point.km === null || point.km <= 50).sort((a, b) => (a.km ?? Infinity) - (b.km ?? Infinity)), [points, category, center?.lat, center?.lng]);
  const selected = filtered.find((point) => point.id === selectedPointId) ?? filtered[0];

  useEffect(() => { setCategory(suggestedCategory); }, [suggestedCategory]);
  useEffect(() => {
    if (!isOpen || !center) { requestId.current++; nearbyAbort.current?.abort(); lastQuery.current = null; setNearby(null); return; }
    const now = Date.now();
    const previous = lastQuery.current;
    if (previous && previous.category === category && calculateHaversineDistanceKm(previous.coord, center) < 0.15 && now - previous.time < 30000) return;
    lastQuery.current = { coord: center, time: now, category };
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
  }, [isOpen, center?.lat, center?.lng, category]);
  useEffect(() => () => { nearbyAbort.current?.abort(); requestId.current++; }, []);

  useEffect(() => {
    if (!isOpen || !mapElement.current || !center) return;
    let cancelled = false;
    import("maplibre-gl").then((maplibre) => {
      if (cancelled || !mapElement.current) return;
      try {
        // Next.js 14 cannot bundle MapLibre v6's ESM worker reliably. Serve
        // the copied worker from /public and configure it before map creation.
        maplibre.setWorkerUrl("/maplibre-gl-worker.mjs");
        const instance = new maplibre.Map({ container: mapElement.current, center: [center.lng, center.lat], zoom: 11, style: { version: 8, sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" } }, layers: [{ id: "osm", type: "raster", source: "osm" }] } });
        map.current = instance;
        instance.addControl(new maplibre.NavigationControl(), "top-right");
        instance.on("error", () => setMapError(true));
        instance.on("style.load", () => { if (!cancelled) { setMapError(false); setMapReady(true); } });
      } catch { setMapError(true); }
    }).catch(() => setMapError(true));
    return () => { cancelled = true; markers.current.forEach((marker) => marker.remove()); markers.current = []; map.current?.remove(); map.current = null; setMapReady(false); };
  }, [isOpen, Boolean(center)]);

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
        const button = document.createElement("button"); button.type = "button"; button.className = "w-4 h-4 rounded-full bg-red-600 border-2 border-white shadow-md"; button.title = `[Demo] ${point.name}`;
        button.onclick = () => onSelectPoint(point.id);
        markers.current.push(new maplibre.Marker({ element: button }).setLngLat([point.coords.lng, point.coords.lat]).addTo(instance));
      });
      instance.jumpTo({ center: [center.lng, center.lat] });
      const source = instance.getSource("accuracy") as import("maplibre-gl").GeoJSONSource | undefined;
      const data = origin && locationState.accuracy ? accuracyPolygon(center.lat, center.lng, locationState.accuracy) : { type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection;
      if (source) source.setData(data);
      else if (instance.isStyleLoaded()) { instance.addSource("accuracy", { type: "geojson", data }); instance.addLayer({ id: "accuracy-fill", type: "fill", source: "accuracy", paint: { "fill-color": "#2563eb", "fill-opacity": 0.16 } }); }
    });
    return () => { disposed = true; };
  }, [center?.lat, center?.lng, filtered, locationState.accuracy, origin, onSelectPoint, mapReady]);

  if (!isOpen) return null;
  return <section className="h-full min-h-[500px] rounded-xl border bg-white overflow-hidden flex flex-col" aria-label="Bản đồ điểm dịch vụ demo">
    <header className="flex items-center justify-between p-3 border-b"><strong>Điểm dịch vụ [Demo]</strong><button type="button" onClick={onClose} aria-label="Đóng bản đồ">Đóng</button></header>
    <div className="flex flex-1 min-h-0">
      <div className="w-1/2 overflow-auto p-3 space-y-3">
        <p className="text-xs text-slate-600">Dữ liệu giả lập, chưa xác minh địa điểm hoặc tình trạng hoạt động.</p>
        {locationState.status === "MANUAL" && <p className="text-xs text-amber-800">{center ? "Tâm khu vực tham chiếu/ước lượng, không phải GPS. Khoảng cách chỉ để tham khảo." : "Chưa nhận diện khu vực. Chọn nhanh Hà Nội, TP.HCM, Đà Nẵng hoặc Long Thành để xem khoảng cách tham khảo."}</p>}
        {locationState.accuracy && locationState.accuracy > 500 && <p className="text-xs text-amber-800">Vị trí ước lượng ±{Math.round(locationState.accuracy)}m</p>}
        <div className="flex flex-wrap gap-1">{categories.map(([value, label]) => <button key={value} type="button" aria-pressed={category === value} className={`px-2 py-1 rounded border text-xs ${category === value ? "bg-blue-700 text-white" : "bg-white"}`} onClick={() => { if (value === category) return; nearbyAbort.current?.abort(); requestId.current++; setNearby(null); setCategory(value); onSelectPoint(""); }}>{label}</button>)}</div>
        {filtered.length === 0 && <div><p>Không có điểm demo phù hợp{center ? " trong bán kính 50 km" : " trong bộ lọc này"}.</p><a href="tel:1900232389" className="text-blue-700 underline">Gọi hỗ trợ 1900-232389</a></div>}
        {filtered.map((point) => <button type="button" key={point.id} onClick={() => onSelectPoint(point.id)} className={`block w-full text-left p-2 rounded border ${selected?.id === point.id ? "border-blue-700" : "border-slate-200"}`}><strong>[Demo] {point.name}</strong><span className="block text-xs">{point.address}</span>{point.km !== null && <span className="text-xs">{formatDistanceKm(point.km)} đường chim bay</span>}</button>)}
        {selected && <div className="border-t pt-2 text-sm"><strong>[Demo] {selected.name}</strong><p>{selected.address}</p><div className="flex flex-wrap gap-3 mt-2"><a target="_blank" rel="noopener noreferrer" href={getDirectionsUrl({ ...selected.coords, address: selected.address }, origin)}>Google Maps{origin ? " chỉ đường" : " tìm địa chỉ"}</a>{origin && <a target="_blank" rel="noopener noreferrer" href={getOsmDirectionsUrl(selected.coords, origin)}>OpenStreetMap chỉ đường</a>}{onSelectDestination && <button type="button" onClick={() => onSelectDestination(selected)}>Chọn làm điểm đến</button>}</div></div>}
      </div>
      <div className="w-1/2 relative bg-slate-100" role="region" aria-label="Bản đồ tương tác">{center ? <div ref={mapElement} className="absolute inset-0" /> : <p className="p-4 text-sm">Nhập hoặc chọn khu vực để mở bản đồ.</p>}{mapError && <p role="alert" className="absolute bottom-2 left-2 bg-white p-2 text-xs">Không tải được bản đồ. Danh sách vẫn sử dụng được.</p>}</div>
    </div>
  </section>;
}
