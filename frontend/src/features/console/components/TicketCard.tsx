"use client";

import Link from "next/link";
import { Car, Clock, AlertCircle, Sparkles, ChevronRight, User } from "lucide-react";
import { TicketItem, TicketPriority, TicketStatus } from "../types";

export function getPriorityBadge(p: TicketPriority) {
  switch (p) {
    case "CRITICAL":
      return "bg-[#FEF2F2] text-[#DC2626] border-[#DC2626]/30";
    case "HIGH":
      return "bg-[#FFFBEB] text-[#D97706] border-[#D97706]/40";
    case "MEDIUM":
      return "bg-[#EFF3FC] text-[#1E40AF] border-[#1E40AF]/30";
    default:
      return "bg-[#F6F7F9] text-[#64748B] border-[#E2E8F0]";
  }
}

export function getStatusBadge(s: TicketStatus) {
  switch (s) {
    case "Staff Reviewing":
      return "bg-[#6D5BD0]/10 text-[#6D5BD0] border-[#6D5BD0]/30";
    case "Needs Information":
      return "bg-[#FFFBEB] text-[#D97706] border-[#D97706]/40";
    case "In Progress":
      return "bg-[#EFF3FC] text-[#1E40AF] border-[#1E40AF]/30";
    case "Resolved":
      return "bg-[#ECFDF5] text-[#10B981] border-[#10B981]/30";
    case "Closed":
      return "bg-[#F6F7F9] text-[#64748B] border-[#E2E8F0]";
    default:
      return "bg-[#F6F7F9] text-[#64748B] border-[#E2E8F0]";
  }
}

interface TicketCardProps {
  ticket: TicketItem;
}

export function TicketCard({ ticket }: TicketCardProps) {
  const isCritical = ticket.priority === "CRITICAL";

  return (
    <Link
      href={`/console/${ticket.id}`}
      aria-label={`Xem chi tiết hồ sơ ${ticket.id}, xe ${ticket.vehicle_model}, ưu tiên ${ticket.priority}, trạng thái ${ticket.status}`}
      className={`group block bg-white rounded-2xl p-4 sm:p-5 border transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1E40AF] shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:shadow-md ${
        isCritical
          ? "border-[#DC2626]/40 hover:border-[#DC2626] bg-gradient-to-r from-[#FEF2F2]/30 via-white to-white"
          : "border-[#E2E8F0] hover:border-[#1E40AF]/60"
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left: Case Info & Metadata */}
        <div className="space-y-2.5 flex-1 min-w-0">
          {/* Badge row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-bold text-[15px] text-[#0F172A] group-hover:text-[#1E40AF] transition-colors">
              {ticket.id}
            </span>

            <span
              className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border flex items-center gap-1 ${getPriorityBadge(
                ticket.priority
              )} ${isCritical ? "animate-pulse font-extrabold" : ""}`}
            >
              {isCritical && <span className="w-1.5 h-1.5 rounded-full bg-[#DC2626]" />}
              {ticket.priority}
            </span>

            <span
              className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${getStatusBadge(
                ticket.status
              )}`}
            >
              {ticket.status}
            </span>

            {ticket.missing_info_flag && (
              <span className="text-[11px] bg-[#FFFBEB] text-[#D97706] border border-[#D97706]/40 px-2 py-0.5 rounded-full flex items-center gap-1 font-semibold">
                <AlertCircle className="w-3 h-3 text-[#D97706]" />
                Thiếu dữ kiện
              </span>
            )}
          </div>

          {/* Details row */}
          <div className="flex items-center gap-3 text-[12px] text-[#64748B] flex-wrap">
            <span className="flex items-center gap-1.5 font-medium text-[#0F172A]">
              <Car className="w-3.5 h-3.5 text-[#1E40AF] shrink-0" />
              <span>{ticket.vehicle_model}</span>
              {ticket.vehicle_source === "inferred" && (
                <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-300 px-1.5 py-0.5 rounded font-medium">
                  Cần xác minh
                </span>
              )}
              {ticket.vehicle_code_mock && (
                <span className="text-[#64748B] font-mono text-[11px]">
                  ({ticket.vehicle_code_mock})
                </span>
              )}
            </span>

            <span>•</span>

            <span className="flex items-center gap-1 text-[11px]">
              <User className="w-3 h-3 text-[#64748B]" />
              {ticket.customer_name ? (
                <span className="font-medium text-[#0F172A]">
                  {ticket.customer_name}
                  <span className="text-[#64748B] font-mono text-[10px] ml-1">
                    ({ticket.mock_customer_id})
                  </span>
                </span>
              ) : (
                <span className="font-mono">{ticket.mock_customer_id}</span>
              )}
            </span>

            <span>•</span>

            <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#475569] text-[11px] font-medium">
              {ticket.intent}
            </span>

            <span>•</span>

            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-[#64748B]" />
              {new Date(ticket.created_at).toLocaleTimeString("vi-VN", {
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              <span className="text-[11px] text-[#64748B]/80">
                ({new Date(ticket.created_at).toLocaleDateString("vi-VN", {
                  day: "2-digit",
                  month: "2-digit",
                })})
              </span>
            </span>
          </div>
        </div>

        {/* Right: AI Score & Action button */}
        <div className="flex items-center justify-between sm:justify-end gap-4 pt-3 sm:pt-0 border-t sm:border-t-0 border-[#F1F5F9]">
          <div className="text-left sm:text-right">
            <div className="text-[10px] text-[#64748B] uppercase tracking-wider font-semibold">
              Độ tin cậy AI
            </div>
            <div
              className={`text-[13px] font-bold flex items-center gap-1 sm:justify-end ${
                ticket.confidence_score >= 0.9
                  ? "text-[#10B981]"
                  : ticket.confidence_score >= 0.7
                  ? "text-[#1E40AF]"
                  : "text-[#D97706]"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {(ticket.confidence_score * 100).toFixed(0)}%
            </div>
          </div>

          <div className="inline-flex items-center gap-1 text-[12px] font-semibold text-[#1E40AF] group-hover:text-[#1E3A8A] bg-[#EFF3FC] group-hover:bg-[#1E40AF] group-hover:text-white px-3 py-2 rounded-xl transition-all shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <span className="hidden sm:inline">Xem hồ sơ</span>
            <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </div>
        </div>
      </div>
    </Link>
  );
}
