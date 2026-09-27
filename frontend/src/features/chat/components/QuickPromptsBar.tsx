import { HelpCircle } from "lucide-react";
import { QuickPrompt, VehicleModel } from "../types";

export const DEFAULT_QUICK_PROMPTS: QuickPrompt[] = [
  {
    label: "Sạc trụ Metropolis lỗi CC01",
    model: "VF8",
    text: "Xe VF8 của tôi không nhận sạc ở trạm Metropolis, trụ báo đèn đỏ và màn hình xe hiện mã CC01.",
  },
  {
    label: "Hỏi cách đặt lịch bảo dưỡng xe",
    model: "VF5",
    text: "Cho tôi hỏi cách đặt lịch bảo dưỡng và theo dõi pin trên app VinFast như thế nào?",
  },
  {
    label: "Cảnh báo khẩn cấp (Rùa vàng cao tốc)",
    model: "VF8",
    text: "Xe VF8 hiện biểu tượng rùa vàng, tụt pin đột ngột và mất lái trên làn 120km/h cao tốc Hải Phòng!",
  },
];

interface QuickPromptsBarProps {
  onSelectPrompt: (prompt: QuickPrompt) => void;
  prompts?: QuickPrompt[];
}

export function QuickPromptsBar({
  onSelectPrompt,
  prompts = DEFAULT_QUICK_PROMPTS,
}: QuickPromptsBarProps) {
  return (
    <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-2 overflow-x-auto text-xs">
      <span className="text-slate-500 shrink-0 font-medium flex items-center gap-1">
        <HelpCircle className="w-3.5 h-3.5" /> Gợi ý nhanh:
      </span>
      {prompts.map((qp, idx) => (
        <button
          key={idx}
          onClick={() => onSelectPrompt(qp)}
          className="shrink-0 px-2.5 py-1 bg-white hover:bg-blue-50 hover:text-blue-700 text-slate-700 border border-slate-200 rounded-md transition-colors text-xs"
        >
          {qp.label}
        </button>
      ))}
    </div>
  );
}
