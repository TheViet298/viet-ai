import { AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { TicketStatus } from "../types";

interface HitlActionBarProps {
  notes: string;
  onChangeNotes: (val: string) => void;
  onExecuteAction: (actionName: string, newStatus: TicketStatus) => void;
}

export function HitlActionBar({
  notes,
  onChangeNotes,
  onExecuteAction,
}: HitlActionBarProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      <h3 className="text-sm font-bold text-slate-900 mb-2">
        Thao Tác Phê Duyệt Của Cố Vấn Dịch Vụ (HITL Actions)
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        Agent chỉ đề xuất; Reviewer là người ra quyết định điều phối chính thức.
      </p>

      <div className="mb-4">
        <label className="block text-xs text-slate-600 font-medium mb-1">
          Ghi chú điều phối / hướng dẫn kỹ thuật viên:
        </label>
        <input
          type="text"
          value={notes}
          onChange={(e) => onChangeNotes(e.target.value)}
          placeholder="Nhập ghi chú cho bộ phận kỹ thuật xưởng..."
          className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:border-blue-600"
        />
      </div>

      <div className="flex flex-wrap gap-2.5">
        <button
          onClick={() => onExecuteAction("Duyệt Phương Án", "In Progress")}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <CheckCircle className="w-4 h-4" /> Duyệt Phương Án & Điều Phối
        </button>
        <button
          onClick={() => onExecuteAction("Yêu Cầu Thêm Thông Tin", "Needs Information")}
          className="px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <AlertTriangle className="w-4 h-4" /> Yêu Cầu Thêm Thông Tin
        </button>
        <button
          onClick={() => onExecuteAction("Đóng Hồ Sơ", "Closed")}
          className="px-3.5 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
        >
          <XCircle className="w-4 h-4" /> Đóng Hồ Sơ
        </button>
      </div>
    </div>
  );
}
