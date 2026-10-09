import type { AttachmentOut } from "./types";

export function getUploadError(attachment: AttachmentOut): string | null {
  const signals = attachment.detected_signals;
  const error = signals?.analysis_error;
  if (error || attachment.analysis_status === "FAILED") {
    if (["routing_uncertain", "image_kind_uncertain"].includes(error || "")) {
      return "Chưa xác định chắc loại ảnh. Vui lòng chọn ảnh rõ hơn hoặc xóa ảnh và mô tả bằng chữ.";
    }
    return "Dịch vụ phân tích ảnh hiện chưa xử lý được yêu cầu. Vui lòng thử tải lại ảnh hoặc xóa ảnh để gửi mô tả bằng chữ.";
  }
  if (!signals || !["dashboard", "charger", "exterior"].includes(signals.image_kind || "")) {
    return "Chưa xác định chắc loại ảnh. Vui lòng chọn ảnh rõ hơn hoặc xóa ảnh và mô tả bằng chữ.";
  }
  return null;
}
