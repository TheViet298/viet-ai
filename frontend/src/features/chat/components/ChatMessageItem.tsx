import { AlertTriangle, CheckCircle, ExternalLink, FileCheck } from "lucide-react";
import { ChatMessage } from "../types";
import { ClarificationChips } from "./ClarificationChips";

interface ChatMessageItemProps {
  message: ChatMessage;
  onSelectReply: (reply: string) => void;
}

export function ChatMessageItem({
  message,
  onSelectReply,
}: ChatMessageItemProps) {
  const isCustomer = message.sender === "CUSTOMER";

  return (
    <div className={`flex flex-col ${isCustomer ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-[13px] sm:text-[14px] leading-relaxed shadow-[0_1px_2px_rgba(0,0,0,0.04)] ${
          isCustomer
            ? "bg-[#1E40AF] text-white rounded-br-sm"
            : "bg-white text-[#0F172A] rounded-bl-sm border border-[#E2E8F0]"
        }`}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>

        {/* Safe Guidance Alert inside Agent Bubble */}
        {message.safe_guidance && (
          <div className="mt-3 p-2.5 bg-[#FFFBEB] border border-[#D97706]/30 rounded-xl text-[#D97706] text-[12px] flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-[#D97706]" />
            <div>
              <strong className="block font-semibold">Hướng dẫn an toàn:</strong>
              {message.safe_guidance}
            </div>
          </div>
        )}

        {/* Citations Card (RAG Verified Sources) */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#E2E8F0] space-y-1.5">
            <div className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider flex items-center gap-1">
              <FileCheck className="w-3.5 h-3.5 text-[#1E40AF]" />
              Nguồn kiểm chứng cẩm nang:
            </div>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((cite, i) => (
                <a
                  key={i}
                  href={cite.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-[11px] text-[#1E40AF] bg-[#EFF3FC] px-2.5 py-1 rounded-full border border-[#E2E8F0] hover:bg-white transition-colors"
                >
                  <span>{cite.title}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Case Created Badge */}
        {message.case_id && (
          <div className="mt-3 p-2.5 bg-[#ECFDF5] border border-[#10B981]/30 rounded-xl text-[#0F172A] text-[12px] flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-[#10B981]" />
              <span>
                Hồ sơ hỗ trợ: <strong>{message.case_id}</strong>
              </span>
            </div>
            <span className="text-[10px] px-2 py-0.5 bg-[#10B981] text-white rounded-full font-bold">
              Staff Reviewing
            </span>
          </div>
        )}
      </div>

      {/* Clarification Chips (SCR-02) */}
      <ClarificationChips
        chips={message.suggested_replies}
        onSelectChip={onSelectReply}
      />
    </div>
  );
}
