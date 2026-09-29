import { Filter } from "lucide-react";

interface TicketFiltersProps {
  statusFilter: string;
  onChangeStatusFilter: (status: string) => void;
  priorityFilter: string;
  onChangePriorityFilter: (priority: string) => void;
}

const STATUS_OPTIONS = ["ALL", "Staff Reviewing", "Needs Information", "In Progress"];
const PRIORITY_OPTIONS = ["ALL", "CRITICAL", "HIGH", "MEDIUM"];

export function TicketFilters({
  statusFilter,
  onChangeStatusFilter,
  priorityFilter,
  onChangePriorityFilter,
}: TicketFiltersProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-4">
      {/* Status filter buttons */}
      <div className="flex items-center gap-2 text-xs text-slate-600">
        <Filter className="w-4 h-4 text-slate-400" />
        <span className="font-medium">Lọc Trạng Thái:</span>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onChangeStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              statusFilter === s
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {s === "ALL" ? "Tất cả" : s}
          </button>
        ))}
      </div>

      {/* Priority filter buttons */}
      <div className="flex items-center gap-2 text-xs text-slate-600">
        <span className="font-medium">Mức Ưu Tiên:</span>
        {PRIORITY_OPTIONS.map((p) => (
          <button
            key={p}
            onClick={() => onChangePriorityFilter(p)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
              priorityFilter === p
                ? "bg-blue-600 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
