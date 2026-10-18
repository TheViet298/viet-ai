"use client";

import { ShieldCheck, RefreshCw, AlertCircle, Clock, CheckCircle2, Flame } from "lucide-react";
import { useTickets } from "../hooks/useTickets";
import { TicketFilters } from "./TicketFilters";
import { TicketTable } from "./TicketTable";

export function TicketQueueContainer() {
  const {
    filteredTickets,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    searchQuery,
    setSearchQuery,
    sortBy,
    setSortBy,
    loading,
    error,
    isLiveApi,
    refreshTickets,
    resetFilters,
    stats,
  } = useTickets();

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:py-8 sm:px-6 lg:px-8 space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#E2E8F0]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-[#1E40AF] bg-[#EFF3FC] px-2.5 py-0.5 rounded-full border border-[#1E40AF]/20">
              <ShieldCheck className="w-3.5 h-3.5 text-[#1E40AF]" />
              Bàn Điều Phối Dịch Vụ (HITL Console)
            </span>
            <span
              className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ${
                isLiveApi
                  ? "bg-[#ECFDF5] text-[#065F46] border border-[#10B981]/30"
                  : "bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isLiveApi ? "bg-[#10B981] animate-pulse" : "bg-[#94A3B8]"}`} />
              {isLiveApi ? "Kết nối API Trực tiếp" : "Chế độ Thử nghiệm Ngoại tuyến"}
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold text-[#0F172A] tracking-tight">
            Hàng Đợi Xử Lý Hồ Sơ Sự Cố
          </h1>
          <p className="text-[13px] text-[#64748B] max-w-2xl leading-relaxed">
            Xem xét các Case Brief do AI Agent trích xuất, xác nhận mức độ ưu tiên và chuyển giao kỹ thuật viên xưởng dịch vụ VinFast.
          </p>
        </div>

        {/* Action button */}
        <div className="flex items-center gap-2.5 self-start md:self-center">
          <button
            onClick={() => refreshTickets()}
            disabled={loading}
            aria-label="Làm mới danh sách hồ sơ sự cố"
            className="inline-flex items-center gap-2 px-3.5 py-2 text-[12px] font-semibold text-[#0F172A] bg-white border border-[#E2E8F0] hover:bg-[#F6F7F9] hover:border-[#CBD5E1] rounded-xl transition-all shadow-[0_1px_2px_rgba(0,0,0,0.04)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1E40AF] disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#64748B] ${loading ? "animate-spin text-[#1E40AF]" : ""}`} />
            <span>{loading ? "Đang đồng bộ..." : "Làm mới"}</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        {/* Total Tickets */}
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:border-[#CBD5E1] transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-[#64748B] font-semibold uppercase tracking-wider">
              Tổng hồ sơ
            </span>
            <div className="w-7 h-7 rounded-lg bg-[#F6F7F9] flex items-center justify-center text-[#64748B]">
              <Clock className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] mt-2">
            {stats.total}
          </div>
          <div className="text-[11px] text-[#64748B] mt-0.5">
            Phiếu trong ca trực
          </div>
        </div>

        {/* Reviewing (Staff Reviewing) */}
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:border-[#D97706]/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-[#D97706] font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#D97706] animate-ping" />
              Chờ duyệt
            </span>
            <div className="w-7 h-7 rounded-lg bg-[#FFFBEB] flex items-center justify-center text-[#D97706]">
              <AlertCircle className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#D97706] mt-2">
            {stats.reviewing}
          </div>
          <div className="text-[11px] text-[#64748B] mt-0.5">
            Cần HITL phản hồi
          </div>
        </div>

        {/* Critical */}
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:border-[#DC2626]/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-[#DC2626] font-bold uppercase tracking-wider flex items-center gap-1">
              <Flame className="w-3.5 h-3.5 text-[#DC2626]" />
              Khẩn cấp
            </span>
            <div className="w-7 h-7 rounded-lg bg-[#FEF2F2] flex items-center justify-center text-[#DC2626]">
              <AlertCircle className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#DC2626] mt-2">
            {stats.critical}
          </div>
          <div className="text-[11px] text-[#DC2626] font-medium mt-0.5">
            Ưu tiên cứu hộ / trạm sạc
          </div>
        </div>

        {/* In Progress / Resolved */}
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:border-[#10B981]/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-[#1E40AF] font-semibold uppercase tracking-wider">
              Xử lý / Hoàn tất
            </span>
            <div className="w-7 h-7 rounded-lg bg-[#ECFDF5] flex items-center justify-center text-[#10B981]">
              <CheckCircle2 className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#1E40AF] mt-2 flex items-baseline gap-1.5">
            <span>{stats.inProgress}</span>
            <span className="text-sm font-normal text-[#64748B]">/ {stats.resolved} xong</span>
          </div>
          <div className="text-[11px] text-[#64748B] mt-0.5">
            Đã chuyển giao xưởng
          </div>
        </div>
      </div>

      {/* Filters Command Bar */}
      <TicketFilters
        statusFilter={statusFilter}
        onChangeStatusFilter={setStatusFilter}
        priorityFilter={priorityFilter}
        onChangePriorityFilter={setPriorityFilter}
        searchQuery={searchQuery}
        onChangeSearchQuery={setSearchQuery}
        sortBy={sortBy}
        onChangeSortBy={setSortBy}
        onResetFilters={resetFilters}
        stats={stats}
        totalFiltered={filteredTickets.length}
      />

      {/* Main Ticket Feed */}
      <section aria-label="Danh sách hồ sơ sự cố">
        <TicketTable
          tickets={filteredTickets}
          loading={loading}
          error={error}
          onRetry={refreshTickets}
          onResetFilters={resetFilters}
        />
      </section>
    </div>
  );
}
