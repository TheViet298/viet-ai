import Link from "next/link";
import { Car, Clock, AlertCircle, Sparkles, ChevronRight } from "lucide-react";
import { TicketItem, TicketPriority, TicketStatus } from "../types";

export function getPriorityBadge(p: TicketPriority) {
  switch (p) {
    case "CRITICAL":
      return "bg-rose-100 text-rose-800 border-rose-300 animate-pulse";
    case "HIGH":
      return "bg-amber-100 text-amber-800 border-amber-300";
    case "MEDIUM":
      return "bg-blue-100 text-blue-800 border-blue-300";
    default:
      return "bg-slate-100 text-slate-700 border-slate-300";
  }
}

export function getStatusBadge(s: TicketStatus) {
  switch (s) {
    case "Staff Reviewing":
      return "bg-purple-100 text-purple-800 border-purple-200";
    case "Needs Information":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "In Progress":
      return "bg-blue-50 text-blue-700 border-blue-200";
    case "Resolved":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    default:
      return "bg-slate-100 text-slate-600 border-slate-200";
  }
}

interface TicketCardProps {
  ticket: TicketItem;
}

export function TicketCard({ ticket }: TicketCardProps) {
  return (
    <Link
      href={`/console/${ticket.id}`}
      className="block bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-sm hover:shadow-md hover:border-blue-400 transition-all group"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-bold text-sm text-slate-900 group-hover:text-blue-600 transition-colors">
              {ticket.id}
            </span>
            <span
              className={`text-[11px] font-bold px-2 py-0.5 rounded border ${getPriorityBadge(
                ticket.priority
              )}`}
            >
              {ticket.priority}
            </span>
            <span
              className={`text-[11px] font-medium px-2 py-0.5 rounded border ${getStatusBadge(
                ticket.status
              )}`}
            >
              {ticket.status}
            </span>
            {ticket.missing_info_flag && (
              <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> Thiếu dữ kiện
              </span>
            )}
          </div>

          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1 font-medium text-slate-700">
              <Car className="w-3.5 h-3.5 text-blue-600" />
              {ticket.vehicle_model} ({ticket.vehicle_code_mock})
            </span>
            <span>•</span>
            <span className="text-slate-600 font-medium">
              Nhóm: {ticket.intent}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {new Date(ticket.created_at).toLocaleTimeString("vi-VN", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
          <div className="text-right">
            <div className="text-[10px] text-slate-400">AI Confidence</div>
            <div className="text-xs font-bold text-emerald-600 flex items-center gap-1 justify-end">
              <Sparkles className="w-3 h-3" />
              {(ticket.confidence_score * 100).toFixed(0)}%
            </div>
          </div>
          <div className="p-2 rounded-lg bg-slate-100 text-slate-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
            <ChevronRight className="w-4 h-4" />
          </div>
        </div>
      </div>
    </Link>
  );
}
