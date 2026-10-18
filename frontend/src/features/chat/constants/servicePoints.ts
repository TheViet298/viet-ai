import { ServicePointSeed } from "../types";

/**
 * Đã loại bỏ SEED_SERVICE_POINTS cố định theo BƯỚC 4 để chuyển sang gọi API động
 * /api/v1/cases/{id}/service-points từ cơ sở dữ liệu thật.
 */
export function getSeedServicePoints(): ServicePointSeed[] {
  return [];
}
