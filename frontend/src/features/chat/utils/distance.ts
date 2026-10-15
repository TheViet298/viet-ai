/**
 * Tiện ích tính toán khoảng cách thực tế theo tọa độ địa lý (Công thức Haversine chuẩn)
 * Tuân thủ ADR-005: Tính toán chính xác từ tọa độ thiết bị khách hàng đến các điểm hỗ trợ.
 */

export interface Coordinates {
  lat: number;
  lng: number;
}

/**
 * Bán kính Trái Đất trung bình (km)
 */
const EARTH_RADIUS_KM = 6371;

/**
 * Tính khoảng cách đường chim bay giữa 2 tọa độ (km)
 */
export function calculateHaversineDistanceKm(
  coord1: Coordinates,
  coord2: Coordinates
): number {
  const dLat = ((coord2.lat - coord1.lat) * Math.PI) / 180;
  const dLng = ((coord2.lng - coord1.lng) * Math.PI) / 180;

  const lat1Rad = (coord1.lat * Math.PI) / 180;
  const lat2Rad = (coord2.lat * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a)));
  return EARTH_RADIUS_KM * c;
}

/**
 * Định dạng khoảng cách thân thiện với người dùng:
 * - < 1 km: hiển thị mét (VD: "850 m")
 * - 1 - 10 km: hiển thị 1 số thập phân (VD: "2.8 km")
 * - > 10 km: hiển thị làm tròn (VD: "14 km", "1.139 km")
 */
export function formatDistanceKm(distanceKm: number): string {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)} m`;
  }
  if (distanceKm < 10) {
    return `${distanceKm.toFixed(1)} km`;
  }
  return `${Math.round(distanceKm).toLocaleString("vi-VN")} km`;
}

/**
 * Ngưỡng khoảng cách tối đa để coi là "trong khu vực hỗ trợ" (km).
 * Nếu điểm gần nhất cách xa hơn ngưỡng này, thông báo cho khách gọi Hotline 1900-232389 thay vì gán nhãn "gần nhất".
 */
export const MAX_SUPPORT_RADIUS_KM = 50;

/**
 * Tạo URL chỉ đường mở trực tiếp ứng dụng bản đồ bên ngoài (Google Maps / Apple Maps / Web).
 * Khi có tọa độ origin (GPS), truyền chính xác origin và destination để mở chế độ lái xe (driving).
 * Khi không có origin, fallback tìm kiếm theo địa chỉ đích.
 */
export function getDirectionsUrl(
  destination: { lat: number; lng: number; address: string },
  origin?: Coordinates
): string {
  const valid = (coord: Coordinates) => Number.isFinite(coord.lat) && Number.isFinite(coord.lng) && Math.abs(coord.lat) <= 90 && Math.abs(coord.lng) <= 180;
  if (!valid(destination) || (origin && !valid(origin))) throw new Error("Tọa độ chỉ đường không hợp lệ");
  const query = new URLSearchParams({ api: "1", destination: `${destination.lat},${destination.lng}`, travelmode: "driving" });
  if (origin) query.set("origin", `${origin.lat},${origin.lng}`);
  return `https://www.google.com/maps/dir/?${query}`;
}

/**
 * Tạo URL chỉ đường mã nguồn mở OpenStreetMap Directions (FOSSGIS OSRM Car).
 */
export function getOsmDirectionsUrl(
  destination: Coordinates,
  origin: Coordinates
): string {
  return `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${origin.lat}%2C${origin.lng}%3B${destination.lat}%2C${destination.lng}`;
}
