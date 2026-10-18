"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { ChatMessage } from "../types";
import { ChatMessageItem } from "./ChatMessageItem";
import { Sparkles, ArrowDown } from "lucide-react";

interface ChatFeedProps {
  messages: ChatMessage[];
  loading: boolean;
  onSelectReply: (reply: string) => void;
  isMapOpen?: boolean;
  showLocationCard?: boolean;
  children?: React.ReactNode;
}

export function ChatFeed({
  messages,
  loading,
  onSelectReply,
  isMapOpen,
  showLocationCard,
  children,
}: ChatFeedProps) {
  const { t } = useLocale();
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState(false);
  const isNearBottomRef = useRef(true);
  const lastSeenMsgCountRef = useRef(messages.length);

  // Kiểm tra vị trí cuộn của người dùng
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const distanceFromBottom = scrollHeight - (scrollTop + clientHeight);

    // Nếu cách đáy dưới 180px thì coi là đang ở đáy
    const nearBottom = distanceFromBottom < 180;
    isNearBottomRef.current = nearBottom;

    if (nearBottom) {
      lastSeenMsgCountRef.current = messages.length;
      setShowScrollBottomBtn(false);
    } else {
      // Chỉ hiện nút khi người dùng đã cuộn lên trên VÀ có tin nhắn mới tới
      const hasUnseenMessages = messages.length > lastSeenMsgCountRef.current;
      setShowScrollBottomBtn(hasUnseenMessages);
    }
  }, [messages.length]);

  // Cuộn xuống đáy một cách an toàn
  const scrollToBottom = useCallback((smooth = true) => {
    if (!containerRef.current) return;
    containerRef.current.scrollTo({
      top: containerRef.current.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
    setShowScrollBottomBtn(false);
    lastSeenMsgCountRef.current = messages.length;
  }, [messages.length]);

  // Tự động cuộn khi tin nhắn mới, mở bản đồ hoặc thanh vị trí xuất hiện
  useEffect(() => {
    if (isNearBottomRef.current) {
      const timer = setTimeout(() => {
        scrollToBottom(true);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      if (messages.length > lastSeenMsgCountRef.current) {
        setShowScrollBottomBtn(true);
      }
    }
  }, [messages.length, loading, isMapOpen, showLocationCard, scrollToBottom]);

  // Lắng nghe thay đổi kích thước khung chat khi trượt mở bản đồ (tránh chip bị cắt cụt)
  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver(() => {
      if (isNearBottomRef.current) {
        scrollToBottom(false);
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, [scrollToBottom]);

  // Xác định tin nhắn AI duy nhất vừa tạo case để hiển thị thẻ "Đã tiếp nhận CASE-..." (tránh lặp 3 lần)
  const caseCreatedMessageId = useMemo(() => {
    const agentMsg = messages.find((m) => m.sender === "AGENT" && Boolean(m.case_id));
    if (agentMsg) return agentMsg.id;
    const lastWithCase = [...messages].reverse().find((m) => Boolean(m.case_id));
    return lastWithCase?.id || null;
  }, [messages]);

  return (
    <div className="relative flex-1 min-h-0 flex flex-col">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 p-3.5 sm:p-4 pb-8 sm:pb-10 overflow-y-auto space-y-3.5"
      >
        {messages.map((msg, idx) => (
          <ChatMessageItem
            key={msg.id}
            message={msg}
            isLastMessage={idx === messages.length - 1}
            showCaseBadge={msg.id === caseCreatedMessageId}
            onSelectReply={onSelectReply}
          />
        ))}

        {/* AI Suy nghĩ và Tra cứu cẩm nang kỹ thuật */}
        {loading && (
          <div className="flex items-start gap-2 animate-fadeIn">
            <div className="w-6 h-6 rounded-lg bg-[#1E40AF] flex items-center justify-center shrink-0 mt-0.5">
              <Sparkles className="w-3 h-3 text-white animate-pulse" />
            </div>

            <div className="rounded-2xl rounded-tl-xs bg-slate-100 p-2.5 max-w-[85%] sm:max-w-[70%] space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[11.5px] font-bold text-[#1E40AF]">Serv</span>
                <span className="text-[10.5px] text-slate-400 flex items-center gap-1 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping inline-block" />
                  <span>{t("Đang xử lý")}</span>
                </span>
              </div>

              <div className="flex items-center gap-2 py-0.5">
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#1E40AF] animate-bounce [animation-delay:-0.3s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-[#0284C7] animate-bounce [animation-delay:-0.15s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-bounce" />
                </div>
                <span className="text-[11.5px] text-slate-500 italic">
                  {t("Đang tra cứu cẩm nang kỹ thuật & đối chiếu an toàn...")}</span>
              </div>
            </div>
          </div>
        )}

        <div className="h-3 shrink-0" aria-hidden="true" />
      </div>

      {/* Nút nổi "↓ Tin mới" khi người dùng cuộn ngược lên trên */}
      {showScrollBottomBtn && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 animate-fadeIn">
          <button
            type="button"
            onClick={() => scrollToBottom(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900/90 hover:bg-slate-900 text-white text-[11px] font-semibold shadow-md active:scale-95 transition"
          >
            <ArrowDown className="w-3 h-3" />
            <span>{t("Tin mới")}</span>
          </button>
        </div>
      )}

      {/* Slot thanh vị trí ngoài luồng chat (nếu có) */}
      {children}
    </div>
  );
}
