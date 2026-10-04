import { ServicePointSeed } from "./types";

export const CHAT_SEED_SERVICE_POINTS: ServicePointSeed[] = [
  {
    id: "sp-04",
    name: "Đội Cứu hộ Phản ứng nhanh Cao Tốc Long Thành",
    type: "EXPRESSWAY_RESCUE",
    address: "Trạm điều hành nút giao Km 20, Cao tốc Long Thành - Dầu Giây",
    distance: "4.5 km",
    hotline: "1900-232389",
    coords: { lat: 10.7821, lng: 106.8423 },
  },
  {
    id: "sp-03",
    name: "Trạm sạc Siêu Nhanh Vincom Metropolis (250kW)",
    type: "CHARGING_STATION",
    address: "29 Liễu Giai, Ngọc Khánh, Ba Đình, Hà Nội",
    distance: "1.2 km",
    hotline: "1900-232389",
    coords: { lat: 21.0315, lng: 105.8155 },
  },
  {
    id: "sp-01",
    name: "Xưởng Dịch vụ VinFast Times City",
    type: "SERVICE_WORKSHOP",
    address: "Tầng B2, Vincom Mega Mall Times City, Hai Bà Trưng, Hà Nội",
    distance: "2.8 km",
    hotline: "1900-232389",
    coords: { lat: 20.9951, lng: 105.8675 },
  },
  {
    id: "sp-02",
    name: "Xưởng Dịch vụ VinFast Trần Duy Hưng",
    type: "SERVICE_WORKSHOP",
    address: "Số 1 Trần Duy Hưng, Trung Hòa, Cầu Giấy, Hà Nội",
    distance: "3.5 km",
    hotline: "1900-232389",
    coords: { lat: 21.0094, lng: 105.7981 },
  },
];

export function stripAccents(str: string): string {
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D");
}

export const HARD_EMERGENCY_PATTERNS = [
  // Cháy & Khói & Chập
  /\b(cháy|cháy xe|xe bốc lửa|bốc lửa|bốc khói|mùi khét|lửa|xì khói|chập điện|chay|chay xe|xe boc lua|boc lua|boc khoi|mui khet|chap dien)\b/i,
  // Phanh
  /\b(mất phanh|liệt phanh|phanh không ăn|không phanh được|không ăn phanh|hẫng phanh|đạp phanh không ăn|mat phanh|liet phanh|phanh khong an|khong phanh duoc|hang phanh)\b/i,
  // Kẹt chân ga
  /\b(kẹt chân ga|kẹt ga|dính ga|chân ga bị kẹt|ket chan ga|ket ga)\b/i,
  // Nổ lốp
  /\b(nổ lốp|rách lốp|nổ vỏ|bể bánh|no lop|rach lop|be banh)\b/i,
  // Tai nạn, lật xe
  /\b(tai nạn|lật xe|đâm va mạnh|va chạm mạnh|tai nan|lat xe)\b/i,
  // Ngập nước
  /\b(ngập nước đến sàn|nước tràn vào sàn|ngập sàn xe|ngập đến sàn|ngap nuoc den san|ngap san xe)\b/i,
];

export const TURTLE_EMERGENCY_PATTERN = /\b(rùa vàng|con rùa|biểu tượng con rùa|báo rùa|rua vang|con rua)\b/i;
export const TURTLE_DANGER_CONDITIONS_PATTERN = /\b(cao tốc|mất kiểm soát|giảm công suất|dừng giữa đường|không thể tăng tốc|giật mạnh|mất lái|đang chạy|trên cầu|cao toc|mat kiem soat|giam cong suat|dung giua duong|giat manh|mat lai|dang chay|tren cau)\b/i;

export function checkHardEmergency(text: string): boolean {
  if (!text) return false;
  const lower = text.toLowerCase();
  const unaccented = stripAccents(lower);

  // Kiểm tra rủi ro độc lập
  for (const pattern of HARD_EMERGENCY_PATTERNS) {
    if (pattern.test(lower) || pattern.test(unaccented)) {
      const isPureInquiry = /\b(nghĩa là gì|là gì|ý nghĩa|tại sao lại không có|có khói không)\b/i.test(lower);
      const hasEmergencyPresence = /\b(xe tôi|xe của tôi|đang bị|vừa bị|đang|vừa|thấy|bốc|khét|cứu)\b/i.test(lower);
      if (isPureInquiry && !hasEmergencyPresence) {
        continue;
      }
      return true;
    }
  }

  // Kiểm tra tổ hợp rùa vàng + cao tốc/nguy hiểm
  const hasTurtle = TURTLE_EMERGENCY_PATTERN.test(lower) || TURTLE_EMERGENCY_PATTERN.test(unaccented);
  if (hasTurtle) {
    const hasDanger = TURTLE_DANGER_CONDITIONS_PATTERN.test(lower) || TURTLE_DANGER_CONDITIONS_PATTERN.test(unaccented);
    if (hasDanger) return true;
  }

  return false;
}

