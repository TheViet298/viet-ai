import { Send } from "lucide-react";

interface ChatInputBarProps {
  input: string;
  onChangeInput: (val: string) => void;
  onSend: () => void;
  disabled?: boolean;
  vehicleModel: string;
}

export function ChatInputBar({
  input,
  onChangeInput,
  onSend,
  disabled,
  vehicleModel,
}: ChatInputBarProps) {
  return (
    <div className="p-3 border-t border-slate-200 bg-white flex items-center gap-2">
      <input
        type="text"
        value={input}
        onChange={(e) => onChangeInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSend()}
        placeholder={`Mô tả vấn đề hoặc câu hỏi về xe ${vehicleModel}...`}
        className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600"
      />
      <button
        onClick={onSend}
        disabled={!input.trim() || disabled}
        className="px-4 py-2.5 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5 text-sm"
      >
        <span>Gửi</span>
        <Send className="w-4 h-4" />
      </button>
    </div>
  );
}
