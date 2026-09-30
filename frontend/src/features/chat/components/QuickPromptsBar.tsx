import { HelpCircle } from "lucide-react";
import { QuickPrompt, VehicleModel } from "../types";

interface QuickPromptsBarProps {
  onSelectPrompt: (prompt: QuickPrompt) => void;
  prompts?: QuickPrompt[];
}

const DEFAULT_QUICK_PROMPTS: QuickPrompt[] = [
  {
    label: "Sạc không vào điện",
    text: "Xe cắm súng sạc nhưng trụ báo đèn đỏ không sạc được.",
    model: "VF8",
  },
  {
    label: "Cảnh báo rùa vàng",
    text: "Màn hình xe hiện biểu tượng con rùa vàng, xe bị giới hạn công suất.",
    model: "VF5",
  },
  {
    label: "Kẹt cần số",
    text: "Xe đã khởi động nhưng không gạt được sang số D.",
    model: "VF5",
  },
  {
    label: "Lịch bảo dưỡng",
    text: "Bảo dưỡng định kỳ 12.000km xe VF8 gồm những hạng mục gì?",
    model: "VF8",
  },
];

export function QuickPromptsBar({
  onSelectPrompt,
  prompts = DEFAULT_QUICK_PROMPTS,
}: QuickPromptsBarProps) {
  return (
    <div className="px-3.5 py-2 bg-[#F6F7F9] border-b border-[#E2E8F0] flex items-center gap-2 overflow-x-auto text-[12px]">
      <span className="text-[#64748B] shrink-0 font-medium flex items-center gap-1 text-[11px] uppercase tracking-wider font-semibold">
        <HelpCircle className="w-3.5 h-3.5 text-[#0D9488]" /> Gợi ý:
      </span>
      <div className="flex items-center gap-1.5 flex-nowrap">
        {prompts.map((qp, idx) => (
          <button
            key={idx}
            onClick={() => onSelectPrompt(qp)}
            className="shrink-0 px-3 py-1 bg-white hover:bg-[#EFF3FC] hover:text-[#1E40AF] hover:border-[#1E40AF] text-[#0F172A] border border-[#E2E8F0] rounded-full transition-colors text-[12px] shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
          >
            {qp.label}
          </button>
        ))}
      </div>
    </div>
  );
}
