import { useEffect, useRef } from "react";
import { RefreshCw } from "lucide-react";
import { ChatMessage } from "../types";
import { ChatMessageItem } from "./ChatMessageItem";

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
    <div className="flex-1 p-4 overflow-y-auto space-y-4">
      {messages.map((msg) => (
        <ChatMessageItem
          key={msg.id}
          message={msg}
          onSelectReply={onSelectReply}
        />
      ))}

      {loading && (
        <div className="flex items-center gap-2 text-slate-400 text-xs py-2">
          <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
          <span>AI đang phân tích ngữ cảnh và kiểm tra cẩm nang...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
