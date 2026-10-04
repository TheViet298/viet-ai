"use client";

import { AlertTriangle, CheckCircle2, XCircle, Send, Loader2, ShieldAlert } from "lucide-react";
import { TicketStatus, StaffActionType } from "../types";

interface HitlActionBarProps {
  notes: string;
  onChangeNotes: (val: string) => void;
  onExecuteAction: (
    actionName: string,
    actionType: StaffActionType,
    newStatus: TicketStatus
  ) => void;
  isSubmitting?: boolean;
}

export function HitlActionBar({
  notes,
  onChangeNotes,
  onExecuteAction,
  isSubmitting = false,
}: HitlActionBarProps) {
  return (
    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 sm:p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)] space-y-5">
      {/* Title & Info */}
      <div className="space-y-1 pb-4 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-2">
          <h3 className="text-base sm:text-lg font-bold text-[#0F172A] flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#1E40AF]" />
            Thao Tác Điều Phối Của Chuyên Viên (HITL Actions)
          </h3>
          <span className="text-[10px] uppercase tracking-wider font-bold bg-[#EFF3FC] text-[#1E40AF] px-2 py-0.5 rounded-full border border-[#1E40AF]/20">
            Quyền quyết định cuối
          </span>
        </div>
        <p className="text-[13px] text-[#64748B] leading-relaxed">
          AI chỉ đóng vai trò phân tích & gợi ý; Chuyên viên dịch vụ giữ toàn quyền phê duyệt, chỉnh sửa hoặc yêu cầu khách hàng bổ sung dữ liệu.
        </p>
      </div>

      {/* Dispatcher Notes Input */}
      <div className="space-y-1.5">
        <label
          htmlFor="dispatch-notes"
          className="block text-[11px] uppercase tracking-wider font-bold text-[#64748B]"
        >
          Ghi chú điều phối nội bộ / Hướng dẫn kỹ thuật viên xưởng:
        </label>
        <textarea
          id="dispatch-notes"
          rows={2}
          value={notes}
          onChange={(e) => onChangeNotes(e.target.value)}
          disabled={isSubmitting}
          placeholder="Nhập hướng dẫn cho xưởng (VD: Chuẩn bị máy chẩn đoán CAN-bus, trạm Liễu Giai kiểm tra điện áp trụ P02, cử xe cứu hộ...)"
          className="w-full text-[13px] px-3.5 py-2.5 rounded-xl border border-[#CBD5E1] bg-[#F6F7F9] text-[#0F172A] placeholder:text-[#64748B]/60 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20 focus:border-[#1E40AF] transition-all resize-none disabled:opacity-50"
        />
        <div className="text-[11px] text-[#64748B] flex items-center justify-between">
          <span>* Ghi chú này sẽ được lưu vào lịch sử tiếp nhận và chuyển tiếp đến hệ thống DMS xưởng.</span>
          <span>{notes.length} ký tự</span>
        </div>
      </div>

      {/* Action Buttons Matrix */}
      <div className="flex flex-wrap items-center gap-2.5 pt-2">
        {/* 1. Primary: Approve Proposal */}
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() => onExecuteAction("Duyệt Phương Án & Chuyển Xưởng", "APPROVE", "In Progress")}
          className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-[#10B981] hover:bg-[#059669] text-white rounded-xl text-[13px] font-semibold transition-all shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#10B981] disabled:opacity-50"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          <span>Duyệt Phương Án & Điều Phối</span>
        </button>

        {/* 2. Secondary: Request More Info */}
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() => onExecuteAction("Yêu Cầu Thêm Thông Tin Từ Khách", "REQUEST_INFO", "Needs Information")}
          className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-[#FFFBEB] hover:bg-[#FEF3C7] text-[#B45309] border border-[#D97706]/40 rounded-xl text-[13px] font-semibold transition-all shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97706] disabled:opacity-50"
        >
          <AlertTriangle className="w-4 h-4 text-[#D97706]" />
          <span>Yêu Cầu Bổ Sung Tin</span>
        </button>

        {/* 3. Tertiary: Reroute Ticket */}
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() => onExecuteAction("Điều Phối Tuyến Khác", "REROUTE", "In Progress")}
          className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-[#EFF3FC] hover:bg-[#DBEAFE] text-[#1E40AF] border border-[#1E40AF]/20 rounded-xl text-[13px] font-semibold transition-all shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1E40AF] disabled:opacity-50"
        >
          <Send className="w-4 h-4 text-[#1E40AF]" />
          <span>Chuyển Tuyến Xưởng</span>
        </button>

        {/* 4. Ghost: Close Ticket */}
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() => onExecuteAction("Đóng Hồ Sơ Sự Cố", "CLOSE", "Closed")}
          className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-3.5 py-2.5 bg-white hover:bg-[#F6F7F9] text-[#64748B] hover:text-[#0F172A] border border-[#E2E8F0] rounded-xl text-[13px] font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[#64748B] disabled:opacity-50 ml-auto"
        >
          <XCircle className="w-4 h-4 text-[#94A3B8]" />
          <span>Đóng Hồ Sơ</span>
        </button>
      </div>
    </div>
  );
}
