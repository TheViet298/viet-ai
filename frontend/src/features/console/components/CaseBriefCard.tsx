"use client";

import { Edit3, ShieldCheck, Sparkles, Check, X, FileText, CheckCircle2 } from "lucide-react";
import { CaseBrief } from "../types";

interface CaseBriefCardProps {
  brief: CaseBrief;
  isEditing: boolean;
  onToggleEdit: () => void;
  summary: string;
  onChangeSummary: (val: string) => void;
  onSave?: () => void;
  onCancel?: () => void;
}

const FIELD_LABELS: Record<string, { label: string; icon?: string }> = {
  vehicle_model: { label: "Dòng xe" },
  station_location: { label: "Vị trí trạm sạc" },
  charger_id: { label: "Mã trụ sạc" },
  error_code: { label: "Mã lỗi hiển thị (DTC)" },
  current_soc: { label: "Dung lượng pin (SoC)" },
};

export function CaseBriefCard({
  brief,
  isEditing,
  onToggleEdit,
  summary,
  onChangeSummary,
  onSave,
  onCancel,
}: CaseBriefCardProps) {
  return (
    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 sm:p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)] space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#E2E8F0]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-base sm:text-lg font-bold text-[#0F172A] flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-[#1E40AF]" />
              Hồ Sơ Sự Cố Tóm Tắt (AI Case Brief)
            </h2>
            {brief.is_edited_by_staff && (
              <span className="text-[11px] font-semibold text-[#0D9488] bg-[#F0FDFA] border border-[#0D9488]/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Đã điều chỉnh bởi Staff
              </span>
            )}
          </div>
          <p className="text-[12px] text-[#64748B]">
            Dữ liệu tổng hợp có ngữ cảnh từ AI Agent, chuẩn hóa theo cẩm nang kỹ thuật VinFast.
          </p>
        </div>

        {!isEditing && (
          <button
            onClick={onToggleEdit}
            className="self-start sm:self-center text-xs text-[#1E40AF] hover:text-[#1E3A8A] font-semibold flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#1E40AF]/20 hover:bg-[#EFF3FC] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1E40AF]"
          >
            <Edit3 className="w-3.5 h-3.5" />
            Chỉnh sửa Brief
          </button>
        )}
      </div>

      {/* 1. Incident Summary */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="brief-summary-input"
            className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B]"
          >
            Tóm tắt sự cố & Ngữ cảnh
          </label>
          {isEditing && (
            <span className="text-[11px] text-[#64748B]">
              {summary.length} ký tự
            </span>
          )}
        </div>

        {isEditing ? (
          <div className="space-y-3 bg-[#F6F7F9] p-3.5 sm:p-4 rounded-2xl border border-[#E2E8F0]">
            <textarea
              id="brief-summary-input"
              value={summary}
              onChange={(e) => onChangeSummary(e.target.value)}
              rows={4}
              placeholder="Chỉnh sửa nội dung tóm tắt sự cố..."
              className="w-full text-[13px] p-3 border border-[#CBD5E1] rounded-xl bg-white text-[#0F172A] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20 focus:border-[#1E40AF] transition-all resize-y"
            />
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={onCancel || onToggleEdit}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-semibold text-[#64748B] hover:text-[#0F172A] bg-white border border-[#E2E8F0] rounded-xl hover:bg-[#F6F7F9] transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                Hủy
              </button>
              <button
                type="button"
                onClick={onSave || onToggleEdit}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-[12px] font-semibold text-white bg-[#10B981] hover:bg-[#059669] rounded-xl shadow-sm transition-colors"
              >
                <Check className="w-3.5 h-3.5" />
                Lưu tóm tắt
              </button>
            </div>
          </div>
        ) : (
          <div className="text-[13px] text-[#0F172A] bg-[#F6F7F9] p-4 rounded-2xl border border-[#E2E8F0] leading-relaxed font-medium">
            {summary}
          </div>
        )}
      </div>

      {/* 2. Captured Technical Fields */}
      <div className="space-y-2.5">
        <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
          Dữ kiện bóc tách kỹ thuật (Extracted Technical Fields)
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 sm:gap-3">
          {Object.entries(brief.captured_fields).map(([key, val]) => {
            const meta = FIELD_LABELS[key] || { label: key };
            const isErrorField = key === "error_code";

            return (
              <div
                key={key}
                className={`p-3 rounded-xl border transition-all ${
                  isErrorField
                    ? "bg-[#FEF2F2]/60 border-[#DC2626]/30 text-[#991B1B]"
                    : "bg-[#F6F7F9] border-[#E2E8F0] text-[#0F172A]"
                }`}
              >
                <div className="flex items-center justify-between text-[#64748B]">
                  <span className="text-[11px] font-medium truncate">
                    {meta.label}
                  </span>
                  <span className="font-mono text-[9px] uppercase opacity-70">
                    {key}
                  </span>
                </div>
                <div
                  className={`text-[13px] font-bold mt-1 truncate ${
                    isErrorField ? "text-[#DC2626] font-mono text-[14px]" : "text-[#0F172A]"
                  }`}
                  title={String(val)}
                >
                  {String(val)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Suggested Action */}
      <div className="space-y-2">
        <label className="block text-[11px] font-bold uppercase tracking-wider text-[#1E40AF]">
          Phương án đề xuất cho xưởng dịch vụ (AI Suggested Action)
        </label>
        <div className="text-[13px] text-[#1E40AF] bg-[#EFF3FC] p-4 rounded-2xl border border-[#1E40AF]/20 flex items-start gap-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <div className="w-8 h-8 rounded-xl bg-white flex items-center justify-center text-[#1E40AF] shrink-0 shadow-sm">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="space-y-1 flex-1 min-w-0">
            <div className="text-[11px] font-bold uppercase tracking-wider text-[#1E40AF]">
              Đề xuất xử lý sơ bộ
            </div>
            <p className="font-medium text-[#1E3A8A] leading-relaxed">
              {brief.suggested_action}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
