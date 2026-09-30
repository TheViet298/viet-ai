'use client'
import { useEffect, useRef } from "react";
import { ChatMessage } from "../types";
import { ChatMessageItem } from "./ChatMessageItem";
import { RefreshCw } from "lucide-react";

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

      {loading && (
        <div className="flex items-center gap-2.5 text-[#64748B] text-[13px] py-2 px-3 bg-[#F0FDFA] border border-[#0D9488]/20 rounded-2xl w-fit animate-pulse">
          <RefreshCw className="w-4 h-4 animate-spin text-[#0D9488]" />
          <span className="font-medium text-[#0D9488]">AI đang phân tích mã lỗi và tra cứu cẩm nang kỹ thuật...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
