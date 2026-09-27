import { Bot, Clock, User } from "lucide-react";

interface ConversationTimelineProps {
  history: Array<{
    sender: "CUSTOMER" | "AGENT" | "STAFF" | "SYSTEM";
    content: string;
    created_at: string;
  }>;
}

export function ConversationTimeline({ history }: ConversationTimelineProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col h-[650px]">
      <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-500" />
          Lịch Sử Hội Thoại
        </h3>
        <span className="text-[11px] text-slate-400">
          {history.length} tin nhắn
        </span>
      </div>

      <div className="flex-1 overflow-y-auto py-4 space-y-3 pr-1">
        {history.map((chat, idx) => (
          <div
            key={idx}
            className={`p-3 rounded-xl text-xs space-y-1 ${
              chat.sender === "CUSTOMER"
                ? "bg-blue-50 border border-blue-100 ml-4"
                : "bg-slate-50 border border-slate-200 mr-4"
            }`}
          >
            <div className="flex items-center justify-between font-semibold text-[10px] text-slate-500">
              <span className="flex items-center gap-1">
                {chat.sender === "CUSTOMER" ? (
                  <User className="w-3 h-3 text-blue-600" />
                ) : (
                  <Bot className="w-3 h-3 text-slate-600" />
                )}
                {chat.sender === "CUSTOMER" ? "Khách hàng" : "AI Agent"}
              </span>
              <span>
                {new Date(chat.created_at).toLocaleTimeString("vi-VN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>
            <div className="text-slate-800 whitespace-pre-wrap leading-relaxed">
              {chat.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
