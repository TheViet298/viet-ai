"use client";

import { ShieldCheck } from "lucide-react";
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
    reviewingCount,
    criticalCount,
  } = useTickets();

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-600">
            <ShieldCheck className="w-4 h-4" /> Bàn Điều Phối Dịch Vụ (HITL Console)
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            Hàng Đợi Xử Lý Hồ Sơ Sự Cố (Ticket Queue)
          </h1>
          <p className="text-xs sm:text-sm text-slate-500">
            Xem xét các Case Brief do AI Agent trích xuất, xác nhận mức ưu tiên và điều phối.
          </p>
        </div>

        {/* Counter Summary */}
        <div className="flex items-center gap-3">
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-2 text-center shadow-sm">
            <div className="text-xs text-slate-500 font-medium">Chờ duyệt</div>
            <div className="text-lg font-bold text-purple-700">{reviewingCount}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-2 text-center shadow-sm">
            <div className="text-xs text-slate-500 font-medium">Khẩn cấp</div>
            <div className="text-lg font-bold text-rose-600">{criticalCount}</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <TicketFilters
        statusFilter={statusFilter}
        onChangeStatusFilter={setStatusFilter}
        priorityFilter={priorityFilter}
        onChangePriorityFilter={setPriorityFilter}
      />

      {/* Ticket List */}
      <TicketTable tickets={filteredTickets} />
    </div>
  );
}
