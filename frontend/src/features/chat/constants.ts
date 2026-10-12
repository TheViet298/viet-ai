import { ServicePointSeed } from "./types";

export const CHAT_SEED_SERVICE_POINTS: ServicePointSeed[] = [
  {
    id: "sp-04",
    name: "Đội Cứu hộ Phản ứng nhanh Cao Tốc Long Thành",
    type: "OTHER",
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

