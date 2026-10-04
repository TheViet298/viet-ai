"use client";

import { useState } from "react";
import Link from "next/link";
import { ExternalLink, FileText, Check, ChevronDown, ChevronUp } from "lucide-react";
import { ChatMessage } from "../types";
import { ClarificationChips } from "./ClarificationChips";

interface ChatMessageItemProps {
  message: ChatMessage;
  isLastMessage: boolean;
  onSelectReply: (reply: string) => void;
}

export function ChatMessageItem({
  message,
  isLastMessage,
  onSelectReply,
}: ChatMessageItemProps) {
  const isCustomer = message.sender === "CUSTOMER";
  const [showFullDetails, setShowFullDetails] = useState(false);

  // Nếu câu trả lời dài hơn 220 ký tự thì chia phần tóm tắt và phần chi tiết
  const hasLongContent = !isCustomer && message.content.length > 220;
  const mainContent = hasLongContent && !showFullDetails
    ? message.content.slice(0, 190) + "..."
    : message.content;

  return (
    <div className={`flex flex-col ${isCustomer ? "items-end" : "items-start"} space-y-1.5`}>
      {/* Sender Label & Timestamp */}
      <div className="flex items-center gap-1.5 px-1 text-[11px] text-slate-400 font-medium">
        <span>{isCustomer ? "Bạn" : "Trợ lý VinFast"}</span>
        <span>·</span>
        <span>{new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}</span>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          CẤP 1: BONG BÓNG DUY NHẤT (MỘT TIN NHẮN CHỈ MỘT BOX)
          - Khách: Xanh đặc
          - AI: Xám nhạt, KHÔNG VIỀN (Độ sâu bằng khác biệt màu nền)
      ───────────────────────────────────────────────────────────── */}
      <div
        className={`max-w-[88%] sm:max-w-[76%] rounded-2xl p-3 sm:p-3.5 text-[13px] leading-relaxed transition-all ${
          isCustomer
            ? "bg-[#1E40AF] text-white rounded-tr-xs"
            : "bg-slate-100 text-slate-800 rounded-tl-xs"
        }`}
      >
        <div className="whitespace-pre-wrap leading-relaxed">{mainContent}</div>

        {/* Chỉ dẫn an toàn: gộp trực tiếp vào bong bóng dạng chữ đậm, KHÔNG TẠO HỘP VÀNG */}
        {message.safe_guidance && message.priority !== "CRITICAL" && (
          <div className="mt-1.5 text-[12px] text-amber-950 font-medium">
            <strong>Chỉ dẫn: </strong>
            <span>{message.safe_guidance}</span>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────
            CẤP 2: NGUỒN TÀI LIỆU & NÚT CHI TIẾT (KHÔNG CÓ KHUNG TO)
        ───────────────────────────────────────────────────────────── */}
        <div className="mt-2 pt-1 flex items-center justify-between gap-2 text-[11px] text-slate-500">
          {/* Nguồn tài liệu thu gọn thành chip 1 dòng */}
          {message.citations && message.citations.length > 0 ? (
            <div className="flex items-center gap-1.5 min-w-0">
              {message.citations.slice(0, 1).map((cite, i) => (
                <a
                  key={i}
                  href={cite.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[#1E40AF] font-medium truncate"
                  title={cite.title}
                >
                  <FileText className="w-3 h-3 text-[#1E40AF] shrink-0" />
                  <span className="truncate max-w-[200px] sm:max-w-[260px]">
                    {cite.title.replace(/—.*$/, "").trim()}
                  </span>
                  <ExternalLink className="w-2.5 h-2.5 opacity-60 shrink-0" />
                </a>
              ))}
            </div>
          ) : (
            <span />
          )}

          {/* Toggle Xem chi tiết cho tin nhắn dài */}
          {hasLongContent && (
            <button
              type="button"
              onClick={() => setShowFullDetails(!showFullDetails)}
              className="text-[#1E40AF] hover:underline font-semibold flex items-center gap-0.5 shrink-0 ml-auto"
            >
              <span>{showFullDetails ? "Thu gọn" : "Xem chi tiết"}</span>
              {showFullDetails ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          CẤP 3: TRẠNG THÁI HỆ THỐNG ("ĐÃ TIẾP NHẬN CA")
          - 1 dòng nhỏ giữa khung chat, KHÔNG NỀN, KHÔNG BONG BÓNG
      ───────────────────────────────────────────────────────────── */}
      {message.case_id && (
        <div className="my-1 py-0.5 px-1 text-[11.5px] text-slate-500 flex items-center gap-1.5 self-center animate-fadeIn">
          <span className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
            <Check className="w-2.5 h-2.5" />
          </span>
          <span>
            Đã tiếp nhận <strong className="font-mono text-slate-800">{message.case_id}</strong>
          </span>
          <span>·</span>
          <Link
            href="/track-case"
            className="text-[#1E40AF] font-semibold hover:underline"
          >
            Xem tiến trình ›
          </Link>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          CẤP 4: GỢI Ý TRẢ LỜI NHANH
          - CHỈ HIỆN DƯỚI TIN NHẮN CUỐI CÙNG (Tối đa 2-3 chip)
          - Tự động biến mất sau khi khách gửi tin nhắn mới
      ───────────────────────────────────────────────────────────── */}
      {isLastMessage && message.suggested_replies && message.suggested_replies.length > 0 && (
        <ClarificationChips
          chips={message.suggested_replies.slice(0, 3)}
          onSelectChip={onSelectReply}
        />
      )}
    </div>
  );
}
