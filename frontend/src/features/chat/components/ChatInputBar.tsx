import { ImagePlus, Send, X, Sparkles } from "lucide-react";

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
    <div className="p-3 sm:p-3.5 border-t border-slate-200/80 bg-white">
      {/* Image Preview attachment badge */}
      {imagePreview && (
        <div className="mb-2.5 flex items-center gap-2.5 rounded-xl border border-blue-200 bg-blue-50/50 p-2 animate-fadeIn">
          <img
            src={imagePreview}
            alt="Ảnh cảnh báo đã chọn"
            className="h-10 w-14 rounded-lg object-cover border border-blue-200"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] font-semibold text-slate-800">
              {imageName || "Ảnh cảnh báo táp-lô"}
            </p>
            <p className="text-[11px] text-[#1E40AF] flex items-center gap-1 font-medium">
              <Sparkles className="w-3 h-3" />
              <span>Sẵn sàng để AI phân tích triệu chứng</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClearImage}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-red-600 transition shadow-2xs"
            aria-label="Xóa ảnh"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Input row */}
      <div className="flex items-center gap-2">
        <label
          className="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50 hover:border-blue-300 text-slate-500 hover:text-[#1E40AF] transition shadow-2xs"
          title="Tải ảnh cảnh báo táp-lô hoặc trụ sạc"
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
          placeholder={`Hỏi về vận hành, cẩm nang hoặc báo sự cố xe ${vehicleModel}...`}
          className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200/90 bg-slate-50/50 hover:bg-white focus:bg-white text-[13px] sm:text-[13.5px] text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#1E40AF] focus:ring-2 focus:ring-[#1E40AF]/15 transition"
        />

        <button
          onClick={onSend}
          disabled={(!input.trim() && !imagePreview) || disabled}
          className="h-10 px-4 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-1.5 text-[12.5px] shadow-2xs shrink-0 active:scale-[0.98]"
        >
          <span>Gửi</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
