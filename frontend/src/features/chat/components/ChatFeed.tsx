'use client'
import { useEffect, useRef } from "react";
import { ChatMessage } from "../types";
import { ChatMessageItem } from "./ChatMessageItem";
import { Sparkles } from "lucide-react";

interface ChatFeedProps {
  messages: ChatMessage[];
  loading: boolean;
  onSelectReply: (reply: string) => void;
}

export function ChatFeed({ messages, loading, onSelectReply }: ChatFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex-1 p-4 sm:p-5 overflow-y-auto space-y-4">
      {messages.map((msg) => (
        <ChatMessageItem
          key={msg.id}
          message={msg}
          onSelectReply={onSelectReply}
        />
      ))}

      {/* AI Suy nghĩ và Tra cứu tri thức */}
      {loading && (
        <div className="flex items-start gap-2.5 animate-in fade-in duration-300">
          <div className="w-8 h-8 rounded-[10px] bg-[#1E40AF] text-[#10B981] flex items-center justify-center shrink-0 shadow-sm mt-0.5">
            <Sparkles className="w-4 h-4 text-white animate-pulse" />
          </div>

          <div className="rounded-2xl rounded-bl-sm border border-[#E2E8F0] bg-white p-3.5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] max-w-[85%] sm:max-w-[75%] space-y-1.5">
            <div className="flex items-center gap-1.5">
              <span className="text-[12px] font-bold text-[#1E40AF]">Trợ lý VinFast AI</span>
              <span className="text-[11px] text-[#64748B] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-ping inline-block"></span>
                <span>Đang suy nghĩ...</span>
              </span>
            </div>

            <div className="flex items-center gap-2 py-0.5">
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#1E40AF] animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-2 h-2 rounded-full bg-[#0D9488] animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-2 h-2 rounded-full bg-[#10B981] animate-bounce"></span>
              </div>
              <span className="text-[12px] text-[#64748B] italic">
                Đang đối soát cẩm nang kỹ thuật & chuẩn hóa dữ kiện...
              </span>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

