import { HelpCircle, ChevronRight } from "lucide-react";
import { QuickPrompt, VehicleModel } from "../types";

interface QuickPromptsBarProps {
  onSelectPrompt: (prompt: QuickPrompt) => void;
  prompts?: QuickPrompt[];
}

const DEFAULT_QUICK_PROMPTS: QuickPrompt[] = [
  {
    label: "Sạc không vào điện (CC01)",
    text: "Xe cắm súng sạc nhưng trụ báo đèn đỏ không sạc được.",
    model: "VF8",
  },
  {
    label: "Cảnh báo rùa vàng",
    text: "Màn hình xe hiện biểu tượng con rùa vàng, xe bị giới hạn công suất.",
    model: "VF5",
  },
  {
    label: "Kẹt cần số điện tử",
    text: "Xe đã khởi động nhưng không gạt được sang số D.",
    model: "VF5",
  },
  {
    label: "Bảo dưỡng 12.000km",
    text: "Bảo dưỡng định kỳ 12.000km xe VF8 gồm những hạng mục gì?",
    model: "VF8",
  },
];

export function QuickPromptsBar({
  onSelectPrompt,
  prompts = DEFAULT_QUICK_PROMPTS,
}: QuickPromptsBarProps) {
  return (
    <div className="px-4 py-2 bg-slate-50/70 border-b border-slate-100 flex items-center gap-2 overflow-x-auto text-[12px] scrollbar-none">
      <span className="text-slate-400 shrink-0 flex items-center gap-1 text-[11px] uppercase tracking-wider font-semibold">
        <HelpCircle className="w-3.5 h-3.5 text-[#1E40AF]" />
        <span className="hidden sm:inline">Gợi ý:</span>
      </span>

      <div className="flex items-center gap-1.5 flex-nowrap">
        {prompts.map((qp, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectPrompt(qp)}
            className="shrink-0 px-3 py-1 bg-white hover:bg-blue-50 text-slate-700 hover:text-[#1E40AF] border border-slate-200/80 hover:border-blue-300 rounded-full transition-all text-[11.5px] font-medium shadow-2xs active:scale-[0.98]"
          >
            {qp.label}
          </button>
        ))}
      </div>
    </div>
  );
}
