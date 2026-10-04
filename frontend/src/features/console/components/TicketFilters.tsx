"use client";

import { Search, X, RotateCcw, ArrowUpDown } from "lucide-react";
import { SortOption } from "../hooks/useTickets";

interface TicketFiltersProps {
  statusFilter: string;
  onChangeStatusFilter: (status: string) => void;
  priorityFilter: string;
  onChangePriorityFilter: (priority: string) => void;
  searchQuery: string;
  onChangeSearchQuery: (val: string) => void;
  sortBy: SortOption;
  onChangeSortBy: (val: SortOption) => void;
  onResetFilters: () => void;
  stats: {
    total: number;
    reviewing: number;
    critical: number;
    needsInfo: number;
    inProgress: number;
    resolved: number;
  };
  totalFiltered: number;
}

const STATUS_TABS: Array<{ id: string; label: string; key?: keyof TicketFiltersProps["stats"] }> = [
  { id: "ALL", label: "Tất cả", key: "total" },
  { id: "Staff Reviewing", label: "Chờ duyệt", key: "reviewing" },
  { id: "Needs Information", label: "Cần bổ sung", key: "needsInfo" },
  { id: "In Progress", label: "Đang xử lý", key: "inProgress" },
  { id: "Resolved", label: "Đã giải quyết", key: "resolved" },
];

const PRIORITY_OPTIONS = [
  { id: "ALL", label: "Tất cả" },
  { id: "CRITICAL", label: "Khẩn cấp", color: "bg-[#FEF2F2] text-[#DC2626] border-[#DC2626]/30" },
  { id: "HIGH", label: "Cao", color: "bg-[#FFFBEB] text-[#D97706] border-[#D97706]/40" },
  { id: "MEDIUM", label: "Trung bình", color: "bg-[#EFF3FC] text-[#1E40AF] border-[#1E40AF]/30" },
  { id: "LOW", label: "Thấp", color: "bg-[#F6F7F9] text-[#64748B] border-[#E2E8F0]" },
];

export function TicketFilters({
  statusFilter,
  onChangeStatusFilter,
  priorityFilter,
  onChangePriorityFilter,
  searchQuery,
  onChangeSearchQuery,
  sortBy,
  onChangeSortBy,
  onResetFilters,
  stats,
  totalFiltered,
}: TicketFiltersProps) {
  const isFiltered = statusFilter !== "ALL" || priorityFilter !== "ALL" || searchQuery.trim().length > 0;

  return (
    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 sm:p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] space-y-4">
      {/* Top row: Search input & Sort selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Search input */}
        <div className="relative flex-1 max-w-lg">
          <label htmlFor="ticket-search" className="sr-only">
            Tìm kiếm theo Mã hồ sơ, Model xe, Mã khách hoặc Sự cố
          </label>
          <Search className="w-4 h-4 text-[#64748B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="ticket-search"
            type="text"
            value={searchQuery}
            onChange={(e) => onChangeSearchQuery(e.target.value)}
            placeholder="Tìm theo Mã Case, Khách hàng, Dòng xe (VF8, VF5...), Sự cố..."
            className="w-full text-[13px] pl-10 pr-9 py-2 rounded-xl border border-[#E2E8F0] bg-[#F6F7F9] text-[#0F172A] placeholder:text-[#64748B]/70 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20 focus:border-[#1E40AF] transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => onChangeSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#0F172A] p-0.5 rounded-full"
              aria-label="Xóa nội dung tìm kiếm"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Sort & Quick Reset */}
        <div className="flex items-center gap-2.5 self-end sm:self-center">
          <div className="flex items-center gap-1.5 text-[12px] text-[#64748B] bg-[#F6F7F9] border border-[#E2E8F0] px-3 py-1.5 rounded-xl">
            <ArrowUpDown className="w-3.5 h-3.5 text-[#64748B]" />
            <label htmlFor="sort-select" className="sr-only">Sắp xếp theo</label>
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => onChangeSortBy(e.target.value as SortOption)}
              className="bg-transparent text-[12px] font-medium text-[#0F172A] focus:outline-none cursor-pointer"
            >
              <option value="NEWEST">Mới nhất</option>
              <option value="PRIORITY_DESC">Mức ưu tiên cao nhất</option>
              <option value="CONFIDENCE_DESC">Độ tin cậy AI cao nhất</option>
            </select>
          </div>

          {isFiltered && (
            <button
              onClick={onResetFilters}
              className="inline-flex items-center gap-1 text-[12px] text-[#1E40AF] hover:text-[#1E3A8A] font-semibold px-2.5 py-1.5 rounded-xl hover:bg-[#EFF3FC] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1E40AF]"
              title="Đặt lại toàn bộ bộ lọc"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Đặt lại</span>
            </button>
          )}
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[#F1F5F9]" />

      {/* Middle row: Status tabs */}
      <div className="flex items-center justify-between gap-2 overflow-x-auto pb-1 scrollbar-none">
        <div className="flex items-center gap-1.5 flex-nowrap" role="tablist" aria-label="Bộ lọc trạng thái hồ sơ">
          {STATUS_TABS.map((tab) => {
            const count = tab.key ? stats[tab.key] : stats.total;
            const isActive = statusFilter === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => onChangeStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-xl text-[12px] font-medium transition-all whitespace-nowrap flex items-center gap-2 ${
                  isActive
                    ? "bg-[#1E40AF] text-white font-semibold shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                    : "bg-[#F6F7F9] text-[#64748B] hover:text-[#0F172A] hover:bg-[#E2E8F0]/60 border border-transparent"
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    isActive ? "bg-white/20 text-white" : "bg-[#E2E8F0] text-[#64748B]"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="text-[12px] text-[#64748B] shrink-0 font-medium hidden md:block">
          Hiển thị: <strong className="text-[#0F172A]">{totalFiltered}</strong> kết quả
        </div>
      </div>

      {/* Bottom row: Priority chips */}
      <div className="flex items-center gap-2 pt-1 border-t border-[#F1F5F9] flex-wrap text-[12px]">
        <span className="font-semibold text-[#64748B] text-[11px] uppercase tracking-wider shrink-0">
          Mức ưu tiên:
        </span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {PRIORITY_OPTIONS.map((p) => {
            const isActive = priorityFilter === p.id;
            return (
              <button
                key={p.id}
                onClick={() => onChangePriorityFilter(p.id)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold uppercase tracking-wider transition-all border ${
                  isActive
                    ? "bg-[#0F172A] text-white border-[#0F172A] shadow-sm"
                    : "bg-white text-[#64748B] border-[#E2E8F0] hover:bg-[#F6F7F9] hover:text-[#0F172A]"
                }`}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
