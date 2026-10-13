import { ServicePointSeed } from "../types";

/**
 * Fallback mirrors fixtures/nearby_service_points.demo.json (separate from agent fixture).
 * Mỗi điểm có đầy đủ tọa độ, hotline chính thức 1900-232389 và cờ demo định hướng.
 */
export const SEED_SERVICE_POINTS: ServicePointSeed[] = [
  {
    id: "SP-HN-001",
    name: "Trạm sạc VinFast Vincom Metropolis",
    type: "CHARGING_STATION",
    address: "29 Liễu Giai, Ngọc Khánh, Ba Đình, Hà Nội",
    demo: true,
    source: "ServiceFlow demo catalog (not an official directory)",
    updatedAt: "2026-10-13",
    verificationStatus: "UNVERIFIED",
    hotline: "1900-232389",
    coords: { lat: 21.0315, lng: 105.8145 },
  },
  {
    id: "SP-HCM-001",
    name: "Trạm sạc & Dịch vụ VinFast Landmark 81",
    type: "CHARGING_STATION",
    address: "720A Điện Biên Phủ, Phường 22, Bình Thạnh, TP.HCM",
    demo: true,
    source: "ServiceFlow demo catalog (not an official directory)",
    updatedAt: "2026-10-13",
    verificationStatus: "UNVERIFIED",
    hotline: "1900-232389",
    coords: { lat: 10.795, lng: 106.7218 },
  },
  {
    id: "SP-DN-001",
    name: "Trạm Cứu hộ Cao tốc Long Thành - Dầu Giây",
    type: "OTHER",
    address: "Km 28 Cao tốc TP.HCM - Long Thành - Dầu Giây",
    demo: true,
    source: "ServiceFlow demo catalog (not an official directory)",
    updatedAt: "2026-10-13",
    verificationStatus: "UNVERIFIED",
    hotline: "1900-232389",
    coords: { lat: 10.7712, lng: 106.945 },
  },
  {
    id: "SP-HCM-002",
    name: "Xưởng Dịch vụ VinFast Thảo Điền",
    type: "SERVICE_WORKSHOP",
    address: "159 Xa Lộ Hà Nội, Thảo Điền, TP. Thủ Đức, TP.HCM",
    demo: true,
    source: "ServiceFlow demo catalog (not an official directory)",
    updatedAt: "2026-10-13",
    verificationStatus: "UNVERIFIED",
    hotline: "1900-232389",
    coords: { lat: 10.803, lng: 106.735 },
  },
  {
    id: "SP-HN-002",
    name: "VinFast Showroom & Service Smart City",
    type: "SHOWROOM",
    address: "Khu đô thị Vinhomes Smart City, Tây Mỗ, Nam Từ Liêm, Hà Nội",
    demo: true,
    source: "ServiceFlow demo catalog (not an official directory)",
    updatedAt: "2026-10-13",
    verificationStatus: "UNVERIFIED",
    hotline: "1900-232389",
    coords: { lat: 20.9982, lng: 105.742 },
  },
];

export function getSeedServicePoints(): ServicePointSeed[] {
  return [...SEED_SERVICE_POINTS];
}
