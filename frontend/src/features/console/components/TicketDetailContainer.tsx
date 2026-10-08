"use client";

import Link from "next/link";
import { ArrowLeft, CheckCircle, Car, Sparkles } from "lucide-react";
import { useTicketDetail } from "../hooks/useTicketDetail";
import { CaseBriefCard } from "./CaseBriefCard";
import { HitlActionBar } from "./HitlActionBar";
import { ConversationTimeline } from "./ConversationTimeline";

interface TicketDetailContainerProps {
  caseId: string;
}

export function TicketDetailContainer({ caseId }: TicketDetailContainerProps) {
  const {
    detail,
    status,
    isEditing,
    setIsEditing,
    editedSummary,
    setEditedSummary,
    notes,
    setNotes,
    actionSuccess,
    executeAction,
  } = useTicketDetail(caseId);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Back button */}
      <Link
        href="/console"
        className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#64748B] hover:text-[#0F172A] transition-colors mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Quay lại Hàng đợi Ticket
      </Link>

      {/* Action Notification Toast */}
      {actionSuccess && (
        <div className="mb-6 p-4 bg-[#ECFDF5] border border-[#10B981]/30 text-[#065F46] rounded-2xl text-[13px] font-medium flex items-center gap-2.5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] animate-in fade-in duration-200">
          <CheckCircle className="w-5 h-5 text-[#10B981] shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Ticket Header Card */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)] mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xl font-bold text-[#0F172A]">
                {caseId}
              </span>
              <span className={`px-3 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider border ${detail.case.priority === "HIGH" || detail.case.priority === "CRITICAL"
                ? "bg-[#FEF2F2] text-[#DC2626] border-[#DC2626]/20"
                : detail.case.priority === "MEDIUM"
                  ? "bg-[#FFFBEB] text-[#D97706] border-[#D97706]/20"
                  : "bg-[#EFF3FC] text-[#1E40AF] border-[#1E40AF]/20"
                }`}>
                {detail.case.priority}
              </span>
              <span className="px-3 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider bg-[#EFF3FC] text-[#1E40AF] border border-[#1E40AF]/20">
                {status}
              </span>
            </div>
            <div className="flex items-center gap-3 text-[13px] text-[#64748B] mt-2 flex-wrap">
              <span className="flex items-center gap-1.5 font-medium text-[#0F172A]">
                <Car className="w-4 h-4 text-[#1E40AF]" />
                {detail.case.vehicle_model} ({detail.case.vehicle_code_mock})
              </span>
              <span>•</span>
              <span>
                {detail.case.customer_name ? (
                  <>Khách: <strong className="text-[#0F172A]">{detail.case.customer_name}</strong> <span className="font-mono text-xs text-[#64748B]">({detail.case.mock_customer_id})</span></>
                ) : (
                  <>Mã khách: <strong className="font-mono text-[#0F172A]">{detail.case.mock_customer_id}</strong></>
                )}
              </span>
              <span>•</span>
              <span>Ý định: <span className="text-[#0F172A] font-medium">{detail.case.intent}</span></span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-[#64748B]">Độ tin cậy trích xuất:</span>
            <span className="px-3 py-1 bg-[#F0FDFA] text-[#0D9488] border border-[#0D9488]/30 rounded-full text-[12px] font-bold flex items-center gap-1.5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
              <Sparkles className="w-3.5 h-3.5" />
              {(detail.case_brief.confidence_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: AI Case Brief & Actions */}
        <div className="lg:col-span-2 space-y-6">
          <CaseBriefCard
            brief={detail.case_brief}
            isEditing={isEditing}
            onToggleEdit={() => setIsEditing(!isEditing)}
            summary={editedSummary}
            onChangeSummary={setEditedSummary}
          />

          <HitlActionBar
            notes={notes}
            onChangeNotes={setNotes}
            onExecuteAction={executeAction}
          />
        </div>

        {/* Right Column: Conversation History */}
        <ConversationTimeline history={detail.conversation_history} />
      </div>
    </div>
  );
}
