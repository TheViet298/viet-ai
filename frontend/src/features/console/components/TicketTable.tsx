"use client";

import { AlertTriangle, Inbox, RotateCcw } from "lucide-react";
import { TicketItem } from "../types";
import { TicketCard } from "./TicketCard";
import { TicketTableSkeleton } from "./TicketSkeleton";

interface TicketTableProps {
  tickets: TicketItem[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onResetFilters?: () => void;
}

export function TicketTable({
  tickets,
  loading = false,
  error = null,
  onRetry,
  onResetFilters,
}: TicketTableProps) {
  // 1. Loading State
  if (loading) {
    return <TicketTableSkeleton />;
  }

  // 2. Error State
  if (error) {
    return (
      <div
        role="alert"
        className="bg-[#FEF2F2] border border-[#DC2626]/30 rounded-2xl p-8 text-center space-y-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
      >
        <div className="w-12 h-12 rounded-full bg-[#FEE2E2] text-[#DC2626] mx-auto flex items-center justify-center">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div>
          <h3 className="text-base font-bold text-[#991B1B]">
            Không thể tải dữ liệu hồ sơ từ máy chủ
          </h3>
          <p className="text-[13px] text-[#B91C1C] mt-1 max-w-md mx-auto">
            {error || "Đã xảy ra sự cố kết nối với hệ thống Backend. Vui lòng kiểm tra dịch vụ và thử lại."}
          </p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#DC2626] hover:bg-[#B91C1C] text-white rounded-xl text-[13px] font-semibold transition-colors shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#DC2626]"
          >
            <RotateCcw className="w-4 h-4" />
            Thử lại kết nối
          </button>
        )}
      </div>
    );
  }

  // 3. Empty State
  if (tickets.length === 0) {
    return (
      <div
        role="region"
        aria-label="Không có kết quả"
        className="bg-white border border-[#E2E8F0] rounded-2xl p-10 sm:p-14 text-center shadow-[0_1px_2px_rgba(0,0,0,0.04)] space-y-4"
      >
        <div className="w-14 h-14 rounded-2xl bg-[#EFF3FC] text-[#1E40AF] mx-auto flex items-center justify-center shadow-inner">
          <Inbox className="w-7 h-7" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-bold text-[#0F172A]">
            Không tìm thấy hồ sơ nào phù hợp
          </h3>
          <p className="text-[13px] text-[#64748B] max-w-md mx-auto">
            Hiện không có hồ sơ nào trùng khớp với từ khóa tìm kiếm hoặc tiêu chí lọc bạn đã chọn.
          </p>
        </div>
        {onResetFilters && (
          <button
            onClick={onResetFilters}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#EFF3FC] hover:bg-[#1E40AF] text-[#1E40AF] hover:text-white rounded-xl text-[13px] font-semibold transition-all shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1E40AF]"
          >
            <RotateCcw className="w-4 h-4" />
            Đặt lại toàn bộ bộ lọc
          </button>
        )}
      </div>
    );
  }

  // 4. Data List
  return (
    <div
      role="feed"
      aria-label="Danh sách hồ sơ sự cố xe điện VinFast"
      className="space-y-3.5"
    >
      {tickets.map((ticket) => (
        <TicketCard key={ticket.id} ticket={ticket} />
      ))}
    </div>
  );
}
