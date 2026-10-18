"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import type { Map as MapLibreMap, Marker } from "maplibre-gl";
import { ServicePointApiItem } from "../types";

export type MiniMapPoint = ServicePointApiItem | (Partial<ServicePointApiItem> & {
  id: string | number;
  name: string;
  latitude?: number | null;
  longitude?: number | null;
  lat?: number;
  lng?: number;
  category?: string;
  category_slug?: string;
});

interface Props {
  points: MiniMapPoint[];
  userLocation?: { lat: number; lng: number } | null;
  lastUpdatedLabel?: string;
  selectedPointId?: string | null;
  onSelectPoint?: (id: string) => void;
}

export function VietmapMiniMap({
  points,
  userLocation,
  lastUpdatedLabel = "10/2026",
  selectedPointId,
  onSelectPoint,
}: Props) {
  const mapElement = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markers = useRef<Marker[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(false);

  // API key đọc từ biến môi trường NEXT_PUBLIC_VIETMAP_API_KEY
  const apiKey = process.env.NEXT_PUBLIC_VIETMAP_API_KEY;

  // Lọc các điểm có tọa độ hợp lệ
  const validPoints = useMemo(
    () =>
      points.filter(
        (p) =>
          typeof p.latitude === "number" &&
          typeof p.longitude === "number" &&
          p.latitude >= 8.0 &&
          p.latitude <= 24.0 &&
          p.longitude >= 102.0 &&
          p.longitude <= 110.0
      ),
    [points]
  );

  const initialCenter = useMemo(() => {
    if (userLocation) return [userLocation.lng, userLocation.lat];
    if (validPoints[0]) return [validPoints[0].longitude!, validPoints[0].latitude!];
    return [105.8542, 21.0285]; // Fallback Hà Nội
  }, [userLocation, validPoints]);

  useEffect(() => {
    if (!apiKey || !apiKey.trim() || !mapElement.current) return;
    let cancelled = false;

    const resizeObserver = new ResizeObserver(() => map.current?.resize());
    resizeObserver.observe(mapElement.current);

    import("maplibre-gl")
      .then((maplibre) => {
        if (cancelled || !mapElement.current) return;

        try {
          maplibre.setWorkerUrl("/maplibre-gl-worker.mjs");

          const tileUrl = `https://maps.vietmap.vn/api/tm/{z}/{x}/{y}@2x.png?apikey=${apiKey}`;
          const attribution = `© Vietmap | Nguồn dữ liệu: VinFast (${lastUpdatedLabel})`;

          const styleSpec: import("maplibre-gl").StyleSpecification = {
            version: 8,
            sources: {
              vietmap: {
                type: "raster",
                tiles: [tileUrl],
                tileSize: 256,
                attribution,
              },
            },
            layers: [
              {
                id: "vietmap-basemap",
                type: "raster",
                source: "vietmap",
              },
            ],
          };

          const instance = new maplibre.Map({
            container: mapElement.current,
            center: [initialCenter[0], initialCenter[1]],
            zoom: 12,
            style: styleSpec,
            attributionControl: false,
          });

          map.current = instance;
          instance.addControl(new maplibre.NavigationControl(), "top-right");

          instance.on("error", () => {
            if (!cancelled) setMapError(true);
          });

          instance.on("style.load", () => {
            if (!cancelled) {
              setMapError(false);
              setMapReady(true);
            }
          });
        } catch {
          setMapError(true);
        }
      })
      .catch(() => {
        if (!cancelled) setMapError(true);
      });

    return () => {
      cancelled = true;
      resizeObserver.disconnect();
      markers.current.forEach((m) => m.remove());
      markers.current = [];
      map.current?.remove();
      map.current = null;
      setMapReady(false);
    };
  }, [apiKey, initialCenter, lastUpdatedLabel]);

  // Cập nhật Markers khi map sẵn sàng hoặc points/userLocation thay đổi
  useEffect(() => {
    const instance = map.current;
    if (!apiKey || !apiKey.trim() || !instance || !mapReady) return;

    let disposed = false;
    import("maplibre-gl").then((maplibre) => {
      if (disposed || map.current !== instance) return;

      markers.current.forEach((m) => m.remove());
      markers.current = [];

      const bounds = new maplibre.LngLatBounds();
      let hasCoords = false;

      // 1. Marker vị trí người dùng (chỉ hiển thị trong trình duyệt client)
      if (userLocation) {
        const userEl = document.createElement("div");
        userEl.className =
          "w-5 h-5 rounded-full bg-blue-600 border-2 border-white shadow-lg ring-4 ring-blue-300/40 animate-pulse";
        userEl.title = "vị trí của Quý khách (chỉ lưu trên thiết bị)";

        markers.current.push(
          new maplibre.Marker({ element: userEl })
            .setLngLat([userLocation.lng, userLocation.lat])
            .addTo(instance)
        );
        bounds.extend([userLocation.lng, userLocation.lat]);
        hasCoords = true;
      }

      // 2. Markers các điểm dịch vụ đề xuất theo loại điểm
      validPoints.forEach((point, index) => {
        const isCharging =
          point.category === "charging_station" ||
          point.category_slug === "car_charging_station";
        const isWorkshop =
          point.category === "workshop" ||
          Boolean(point.category_slug?.includes("service"));
        const isShowroom =
          point.category === "showroom" ||
          point.category_slug === "showroom_car";

        let colorBg = "bg-slate-700 hover:bg-slate-800";
        let ringColor = "ring-slate-400/50";
        if (isCharging) {
          colorBg = "bg-emerald-600 hover:bg-emerald-700";
          ringColor = "ring-emerald-400/60";
        } else if (isWorkshop) {
          colorBg = "bg-blue-600 hover:bg-blue-700";
          ringColor = "ring-blue-400/60";
        } else if (isShowroom) {
          colorBg = "bg-amber-600 hover:bg-amber-700";
          ringColor = "ring-amber-400/60";
        }

        const isSelected = point.id === selectedPointId;
        const pinEl = document.createElement("button");
        pinEl.type = "button";
        pinEl.className = isSelected
          ? `w-7 h-7 rounded-full ${colorBg} border-2 border-white shadow-xl text-white font-bold text-xs ring-4 ring-offset-1 ${ringColor} flex items-center justify-center cursor-pointer transition transform scale-120 z-20`
          : `w-6 h-6 rounded-full ${colorBg} border-2 border-white shadow-md text-white font-bold text-[11px] flex items-center justify-center cursor-pointer transition hover:scale-110`;
        pinEl.textContent = String(index + 1);
        pinEl.title = `${index + 1}. [${isCharging ? "Trạm sạc" : isWorkshop ? "Xưởng 2S" : isShowroom ? "Showroom" : "Điểm dịch vụ"}] ${point.name} (${point.address})`;
        pinEl.onclick = () => {
          if (onSelectPoint) onSelectPoint(point.id);
          const cardEl = document.getElementById(`service-point-card-${point.id}`);
          if (cardEl) {
            cardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        };

        markers.current.push(
          new maplibre.Marker({ element: pinEl })
            .setLngLat([point.longitude!, point.latitude!])
            .addTo(instance)
        );
        bounds.extend([point.longitude!, point.latitude!]);
        hasCoords = true;
      });

      if (hasCoords) {
        instance.resize();
        instance.fitBounds(bounds, { padding: 45, maxZoom: 14, duration: 400 });
      }
    });

    return () => {
      disposed = true;
    };
  }, [apiKey, mapReady, validPoints, userLocation, selectedPointId, onSelectPoint]);

  // Thiếu key hoặc lỗi bản đồ thì ẩn mini map, card vẫn hiện
  if (!apiKey || !apiKey.trim() || mapError) {
    return null;
  }

  return (
    <div className="relative w-full h-52 sm:h-64 rounded-2xl overflow-hidden border border-slate-200/80 shadow-xs my-3 bg-slate-100">
      <div ref={mapElement} className="w-full h-full" />
      <div className="absolute bottom-1.5 right-2 z-10 px-2 py-0.5 rounded bg-white/90 shadow-xs border border-slate-200/60 text-[10px] font-medium text-slate-600 backdrop-blur-xs pointer-events-none select-none">
        © Vietmap
      </div>
    </div>
  );
}
