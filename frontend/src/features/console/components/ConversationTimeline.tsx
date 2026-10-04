"use client";

import { Bot, Clock, User, ShieldCheck, MessageSquare } from "lucide-react";

interface ConversationTimelineProps {
  history: Array<{
    sender: "CUSTOMER" | "AGENT" | "STAFF" | "SYSTEM";
    content: string;
    created_at: string;
  }>;
}

export function ConversationTimeline({ history }: ConversationTimelineProps) {
  return (
    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] flex flex-col h-[520px] lg:h-[600px]">
      {/* Timeline Header */}
      <div className="pb-3 border-b border-[#E2E8F0] flex items-center justify-between shrink-0">
        <h3 className="text-sm sm:text-base font-bold text-[#0F172A] flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#1E40AF]" />
          Nhật Ký Hội Thoại Khách Hàng
        </h3>
        <span className="text-[11px] font-bold uppercase tracking-wider text-[#1E40AF] bg-[#EFF3FC] px-2 py-0.5 rounded-full border border-[#1E40AF]/20">
          {history.length} tương tác
        </span>
      </div>

      {/* Messages Scroll Area */}
      {history.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-[#64748B] space-y-2">
          <MessageSquare className="w-8 h-8 text-[#CBD5E1]" />
          <p className="text-[13px]">Chưa có lịch sử tin nhắn trong hồ sơ này.</p>
        </div>
      ) : (
        <div
          tabIndex={0}
          role="log"
          aria-label="Lịch sử đối thoại giữa khách hàng và trợ lý AI"
          className="flex-1 overflow-y-auto py-4 space-y-3.5 pr-1 focus:outline-none"
        >
          {history.map((chat, idx) => {
            const isCustomer = chat.sender === "CUSTOMER";
            const isStaff = chat.sender === "STAFF";

            return (
              <div
                key={idx}
                className={`p-3.5 rounded-2xl text-[13px] space-y-1.5 shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-all ${
                  isCustomer
                    ? "bg-[#EFF3FC] border border-[#1E40AF]/20 ml-3 sm:ml-5"
                    : isStaff
                    ? "bg-[#F4F2FF] border border-[#6D5BD0]/30 mr-3 sm:mr-5"
                    : "bg-[#F6F7F9] border border-[#E2E8F0] mr-3 sm:mr-5"
                }`}
              >
                {/* Header row */}
                <div className="flex items-center justify-between font-semibold text-[11px]">
                  <span className="flex items-center gap-1.5">
                    {isCustomer ? (
                      <div className="w-5 h-5 rounded-full bg-[#1E40AF] text-white flex items-center justify-center">
                        <User className="w-3 h-3" />
                      </div>
                    ) : isStaff ? (
                      <div className="w-5 h-5 rounded-full bg-[#6D5BD0] text-white flex items-center justify-center">
                        <ShieldCheck className="w-3 h-3" />
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-[#0D9488] text-white flex items-center justify-center">
                        <Bot className="w-3 h-3" />
                      </div>
                    )}

                    <span
                      className={
                        isCustomer
                          ? "text-[#1E40AF] font-bold"
                          : isStaff
                          ? "text-[#6D5BD0] font-bold"
                          : "text-[#0F172A] font-bold"
                      }
                    >
                      {isCustomer ? "Khách hàng" : isStaff ? "Cố vấn Dịch vụ" : "AI Agent tiếp nhận"}
                    </span>
                  </span>

                  <span className="font-mono text-[10px] text-[#64748B]">
                    {new Date(chat.created_at).toLocaleTimeString("vi-VN", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                </div>

                {/* Content */}
                <div className="text-[#0F172A] whitespace-pre-wrap leading-relaxed text-[13px] pl-6.5">
                  {chat.content}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
