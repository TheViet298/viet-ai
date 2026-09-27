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
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Quay lại Hàng đợi Ticket
      </Link>

      {/* Action Notification Toast */}
      {actionSuccess && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm font-medium flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Ticket Header Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xl font-bold text-slate-900">
                {caseId}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                {detail.case.priority}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                {status}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500 mt-2">
              <span className="flex items-center gap-1 font-medium text-slate-700">
                <Car className="w-3.5 h-3.5 text-blue-600" />
                {detail.case.vehicle_model} ({detail.case.vehicle_code_mock})
              </span>
              <span>•</span>
              <span>Khách: {detail.case.mock_customer_id} (No-PII Mock)</span>
              <span>•</span>
              <span>Phân loại: {detail.case.intent}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Độ tin cậy trích xuất:</span>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg text-xs font-bold flex items-center gap-1">
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
