/** Present legacy evidence without treating structured routing metadata as text. */
export function toCustomerWarningText(captured: Record<string, unknown>): string | undefined {
  const values = [captured.warning_symbol, captured.warning_light, captured.warning, captured.visual_signals];
  let structured = false;
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (Array.isArray(value)) {
      if (!value.length) continue;
      if (value.every(item => typeof item === "string")) {
        const text = value.map(item => item.trim()).filter(Boolean).join("; ");
        if (text) return text;
      } else structured = true;
    } else if (value != null && typeof value !== "string") structured = true;
  }
  return structured ? "Đã nhận bằng chứng ảnh; cần đối chiếu hiện tượng." : undefined;
}
