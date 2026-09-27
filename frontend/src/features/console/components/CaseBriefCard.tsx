import { Edit3, ShieldCheck, Sparkles } from "lucide-react";
import { CaseBrief } from "../types";

interface CaseBriefCardProps {
  brief: CaseBrief;
  isEditing: boolean;
  onToggleEdit: () => void;
  summary: string;
  onChangeSummary: (val: string) => void;
}

export function CaseBriefCard({
  brief,
  isEditing,
  onToggleEdit,
  summary,
  onChangeSummary,
}: CaseBriefCardProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-blue-600" />
          Hồ Sơ Sự Cố Tóm Tắt (Case Brief)
        </h2>
        <button
          onClick={onToggleEdit}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
        >
          <Edit3 className="w-3.5 h-3.5" />
          {isEditing ? "Hủy sửa" : "Chỉnh sửa Brief"}
        </button>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
            Tóm Tắt Sự Cố
          </label>
          {isEditing ? (
            <textarea
              value={summary}
              onChange={(e) => onChangeSummary(e.target.value)}
              rows={3}
              className="w-full text-sm p-3 border border-slate-300 rounded-xl focus:outline-none focus:border-blue-600"
            />
          ) : (
            <div className="text-sm text-slate-800 bg-slate-50 p-3.5 rounded-xl border border-slate-200 leading-relaxed font-medium">
              {summary}
            </div>
          )}
        </div>

        {/* Captured Fields */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
            Dữ Kiện Bóc Tách (Captured Technical Fields)
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(brief.captured_fields).map(([key, val]) => (
              <div
                key={key}
                className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs"
              >
                <span className="text-slate-400 block text-[10px] uppercase font-mono">
                  {key}
                </span>
                <strong className="text-slate-800 font-semibold">
                  {String(val)}
                </strong>
              </div>
            ))}
          </div>
        </div>

        {/* Suggested Action */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
            Phương Án Gợi Ý Cho Kỹ Thuật (Suggested Action)
          </label>
          <div className="text-xs sm:text-sm text-blue-900 bg-blue-50 p-3 rounded-xl border border-blue-200 flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>{brief.suggested_action}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
