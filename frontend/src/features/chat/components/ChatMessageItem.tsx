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
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-sm ${
          isCustomer
            ? "bg-blue-600 text-white rounded-br-none shadow-sm"
            : "bg-slate-100 text-slate-900 rounded-bl-none border border-slate-200"
        }`}
      >
        <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>

        {/* Safe Guidance Alert inside Agent Bubble */}
        {message.safe_guidance && (
          <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong className="block font-semibold">Hướng dẫn an toàn:</strong>
              {message.safe_guidance}
            </div>
          </div>
        )}

        {/* Citations Card (RAG Verified Sources) */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-200 space-y-1.5">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
              <FileCheck className="w-3.5 h-3.5 text-blue-600" />
              Nguồn kiểm chứng chính thức:
            </div>
            {message.citations.map((cite, i) => (
              <a
                key={i}
                href={cite.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-blue-700 bg-white px-2.5 py-1 rounded border border-blue-200 hover:bg-blue-50 transition-colors"
              >
                <span>{cite.title}</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            ))}
          </div>
        )}

        {/* Case Created Badge */}
        {message.case_id && (
          <div className="mt-3 p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span>
                Hồ sơ hỗ trợ: <strong>{message.case_id}</strong>
              </span>
            </div>
            <span className="text-[10px] px-2 py-0.5 bg-emerald-200 rounded font-semibold text-emerald-900">
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
