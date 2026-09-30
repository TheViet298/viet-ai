import { ImagePlus, Send, X } from "lucide-react";

interface ChatInputBarProps {
  input: string;
  onChangeInput: (val: string) => void;
  onSend: () => void;
  disabled?: boolean;
  vehicleModel: string;
  imagePreview?: string | null;
  imageName?: string | null;
  onSelectImage?: (file: File) => void;
  onClearImage?: () => void;
}

export function ChatInputBar({
  input,
  onChangeInput,
  onSend,
  disabled,
  vehicleModel,
  imagePreview,
  imageName,
  onSelectImage,
  onClearImage,
}: ChatInputBarProps) {
  return (
    <div className="p-3 border-t border-[#E2E8F0] bg-white">
      {imagePreview && (
        <div className="mb-2.5 flex items-center gap-2.5 rounded-xl border border-[#0D9488]/30 bg-[#F0FDFA] p-2">
          {/* Preview is local UI state until attachment upload API is connected. */}
          <img src={imagePreview} alt="Ảnh cảnh báo đã chọn" className="h-11 w-14 rounded-lg object-cover border border-[#E2E8F0]" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] font-semibold text-[#0F172A]">{imageName || "Ảnh cảnh báo táp-lô"}</p>
            <p className="text-[11px] text-[#64748B]">Sẵn sàng để Agent phân tích sơ bộ</p>
          </div>
          <button
            type="button"
            onClick={onClearImage}
            className="rounded-[10px] p-1.5 text-[#64748B] hover:bg-white hover:text-[#DC2626] transition"
            aria-label="Xóa ảnh"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      <div className="flex items-center gap-2">
        <label
          className="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-[10px] border border-[#E2E8F0] bg-[#F6F7F9] text-[#0D9488] transition hover:bg-white hover:border-[#1E40AF]"
          title="Tải ảnh cảnh báo táp-lô"
        >
          <ImagePlus className="h-4 w-4" />
          <input
            type="file"
            accept="image/*"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onSelectImage?.(file);
              event.currentTarget.value = "";
            }}
          />
        </label>
        <input
          type="text"
          value={input}
          onChange={(e) => onChangeInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
          placeholder={`Mô tả vấn đề hoặc câu hỏi về xe ${vehicleModel}...`}
          className="flex-1 px-3.5 py-2 rounded-[10px] border border-[#E2E8F0] bg-white text-[13px] sm:text-[14px] text-[#0F172A] placeholder-[#64748B] focus:outline-none focus:border-[#1E40AF]"
        />
        <button
          onClick={onSend}
          disabled={(!input.trim() && !imagePreview) || disabled}
          className="px-4 py-2 rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5 text-[13px] shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
        >
          <span>Gửi</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
